"""Validated immutable request and result records for original-byte acquisition."""

import dataclasses
import hashlib
import json
import math
import pathlib
import re
from urllib import parse

from lcats.gettenberg import errors


class ResourceError(errors.GettenbergError):
    """An acquisition operation failed with a stable diagnostic code."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


class ResourceInputError(ResourceError, ValueError):
    """A request or policy is invalid; no network access was attempted."""


class ResourcePolicyError(ResourceError):
    """Network authority does not permit the requested operation."""


class ResourceIntegrityError(ResourceError):
    """Cached evidence or a received representation failed validation."""


class ResourceTransportError(ResourceError):
    """An HTTP operation failed without publishing a usable cache entry."""


class ResourceDeferredError(ResourceError):
    """A permitted request must wait beyond the remaining operation budget."""

    def __init__(self, message: str, next_eligible_at: float):
        self.next_eligible_at = next_eligible_at
        super().__init__("deferred", message)


class ResourcePublicationError(ResourceError):
    """The cache reference changed but its durability could not be confirmed."""

    published = True


class ResourceLockError(ResourceError):
    """Another acquisition did not release the shared cache lock in time."""


def canonical_url(value: str) -> str:
    """Normalize HTTP(S) authority only, retaining path escaping/query order.

    URL text must be ASCII with non-ASCII path characters percent-encoded.
    Fragments do not identify an HTTP representation and are discarded.
    Credentials and malformed escapes are rejected before urllib can repair them.
    """
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 8192
        or any(ord(c) <= 32 or ord(c) >= 127 for c in value)
        or "\\" in value
        or re.search(r"%(?![0-9a-fA-F]{2})", value)
    ):
        raise ResourceInputError("invalid_url", "URL must be bounded escaped ASCII")
    try:
        parts = parse.urlsplit(value)
        if (
            parts.scheme not in ("http", "https")
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or "%" in parts.netloc
            or parts.netloc.endswith(":")
        ):
            raise ValueError("HTTP(S) host without credentials is required")
        port = parts.port
        if port == 0:
            raise ValueError("port zero is invalid")
        host = parts.hostname.lower()
        if ":" in host:
            host = f"[{host}]"
        if port is not None and port != (443 if parts.scheme == "https" else 80):
            host += f":{port}"
        return parse.urlunsplit(
            (parts.scheme, host, parts.path or "/", parts.query, "")
        )
    except ValueError as exc:
        raise ResourceInputError("invalid_url", str(exc)) from exc


def origin(url: str) -> str:
    """Return a canonical scheme/host/port origin, without a trailing slash."""
    parts = parse.urlsplit(canonical_url(url))
    return f"{parts.scheme}://{parts.netloc}"


def canonical_json(value) -> bytes:
    """Encode the versioned cache identities and immutable receipts consistently."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _number(value, name, minimum, *, integer=False):
    expected = (int,) if integer else (int, float)
    try:
        valid = type(value) in expected and value >= minimum
        if not integer:
            valid = valid and math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        valid = False
    if not valid:
        raise ResourceInputError("invalid_policy", f"invalid {name}")


@dataclasses.dataclass(frozen=True, slots=True)
class SourceRequest:
    """Explicit route, retaining source identity separately from the request URL.

    No URL patterns are guessed. ``archive`` means a retained catalog archive;
    bytes still require offline catalog validation before activation.
    """

    source_uri: str
    request_url: str
    kind: str = "resource"
    route_policy: str = "explicit-url-v1"

    def __post_init__(self):
        if (
            not isinstance(self.source_uri, str)
            or not self.source_uri
            or len(self.source_uri) > 8192
            or any(ord(c) < 32 or ord(c) == 127 for c in self.source_uri)
            or self.kind not in ("resource", "archive")
            or not isinstance(self.route_policy, str)
            or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,128}", self.route_policy)
        ):
            raise ResourceInputError(
                "invalid_request", "invalid source/kind/route policy"
            )
        # Source evidence is an identifier, but credentials must not enter receipts.
        if "://" in self.source_uri:
            try:
                if parse.urlsplit(self.source_uri).username is not None:
                    raise ValueError("source URI contains credentials")
            except ValueError as exc:
                raise ResourceInputError("invalid_request", str(exc)) from exc
        object.__setattr__(self, "request_url", canonical_url(self.request_url))

    @classmethod
    def from_url(cls, url: str, *, kind: str = "resource"):
        """Construct an explicit request without losing the caller's source URI."""
        return cls(url, url, kind=kind)

    @property
    def key(self) -> str:
        """Versioned GET representation identity, separated by storage namespace."""
        return hashlib.sha256(
            canonical_json(
                {
                    "version": 1,
                    "method": "GET",
                    "url": self.request_url,
                    "kind": self.kind,
                    "accept_encoding": "identity",
                }
            )
        ).hexdigest()


@dataclasses.dataclass(frozen=True, slots=True)
class NetworkPolicy:
    """Explicit network authority and finite acquisition budgets.

    An HTTP origin in allowed_origins explicitly permits that insecure origin;
    HTTPS-to-HTTP redirects remain forbidden. Pacing is at least two seconds for
    every request, including redirects and retries. Limits also apply to cache reads.
    """

    online: bool = False
    allowed_origins: tuple[str, ...] = ()
    max_resource_bytes: int = 32 * 1024**2
    max_archive_bytes: int = 256 * 1024**2
    io_timeout: float = 30.0
    operation_seconds: float = 180.0
    archive_seconds: float = 900.0
    lock_timeout: float = 10.0
    min_interval: float = 2.0
    max_retries: int = 2
    max_redirects: int = 5

    def __post_init__(self):
        if type(self.online) is not bool or not isinstance(self.allowed_origins, tuple):
            raise ResourceInputError("invalid_policy", "online/allowed_origins invalid")
        for name in ("max_resource_bytes", "max_archive_bytes"):
            _number(getattr(self, name), name, 1, integer=True)
        for name in ("io_timeout", "operation_seconds", "archive_seconds"):
            _number(getattr(self, name), name, 0.001)
        if self.io_timeout > 86400:
            # Avoid platform time_t overflow before socket.create_connection can
            # return ownership of a socket for deterministic cleanup.
            raise ResourceInputError(
                "invalid_policy", "io_timeout exceeds 86400 seconds"
            )
        _number(self.lock_timeout, "lock_timeout", 0)
        if self.lock_timeout > 60:
            raise ResourceInputError(
                "invalid_policy", "lock_timeout exceeds 60 seconds"
            )
        _number(self.min_interval, "min_interval", 2)
        for name in ("max_retries", "max_redirects"):
            _number(getattr(self, name), name, 0, integer=True)
        normalized = []
        for item in self.allowed_origins:
            url = canonical_url(item)
            parts = parse.urlsplit(url)
            if parts.path != "/" or parts.query or "#" in item:
                raise ResourceInputError(
                    "invalid_policy", "allow origins, not URL paths"
                )
            normalized.append(origin(url))
        object.__setattr__(self, "allowed_origins", tuple(dict.fromkeys(normalized)))

    def permits(self, url: str) -> bool:
        """Check authority without contacting the origin or changing local state."""
        return self.online and origin(url) in self.allowed_origins

    def byte_limit(self, request: SourceRequest) -> int:
        """Return the request-kind-specific raw-body byte bound."""
        return (
            self.max_archive_bytes
            if request.kind == "archive"
            else self.max_resource_bytes
        )

    def seconds(self, request: SourceRequest) -> float:
        """Return the cooperative overall time budget for this request kind."""
        return (
            self.archive_seconds
            if request.kind == "archive"
            else self.operation_seconds
        )


@dataclasses.dataclass(frozen=True, slots=True)
class RetrievalReceipt:
    """Immutable provenance for original HTTP body bytes, before decoding."""

    schema_version: int
    request_key: str
    source_uri: str
    request_url: str
    kind: str
    route_policy: str
    final_url: str
    redirects: tuple[str, ...]
    sha256: str
    size: int
    retrieved_at: str
    headers: tuple[tuple[str, str], ...]
    transport_version: str = "urllib-get-v1"
    status: int = 200


@dataclasses.dataclass(frozen=True, slots=True)
class SourceArtifact:
    """Verified immutable local bytes and the receipt that originally acquired them."""

    path: pathlib.Path
    sha256: str
    size: int
    receipt_sha256: str
    receipt: RetrievalReceipt


@dataclasses.dataclass(frozen=True, slots=True)
class AcquisitionPlan:
    """Read-only action description; a plan never grants execution authority."""

    request: SourceRequest
    action: str
    reason: str
    artifact: SourceArtifact | None = None
