"""Original-byte cache publication using the catalog's qualified local I/O primitives.

Only this adapter translates catalog-specific I/O failures. Resource consumers do
not need a catalog and never acquire its writer lock. Filesystem protection has
the same trusted-local-cache boundary as CatalogManager, not hostile-user isolation.
"""

import contextlib
import dataclasses
import datetime
import hashlib
import os
import pathlib
import re
import uuid

from lcats.gettenberg import _lifecycle_io
from lcats.gettenberg import _resource_types
from lcats.gettenberg import errors

_HASH = re.compile(r"[0-9a-f]{64}")
_METADATA_LIMIT = 65536
_HEADERS = {"content-type", "content-encoding", "etag", "last-modified"}


@contextlib.contextmanager
def translated_errors():
    """Keep shared I/O implementation details out of the public error contract."""
    try:
        yield
    except errors.CatalogLockError as exc:
        raise _resource_types.ResourceLockError("lock_timeout", str(exc)) from exc
    except (errors.CatalogError, OSError) as exc:
        raise _resource_types.ResourceIntegrityError("cache_io", str(exc)) from exc


def _hash(value):
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        raise _resource_types.ResourceIntegrityError(
            "cache_schema", "invalid content identity"
        )
    return value


class Cache:
    """Read-only until prepare/publication; all paths derive from validated hashes."""

    def __init__(self, cache_dir):
        self.parent = pathlib.Path(cache_dir).expanduser().resolve() / "gettenberg"
        self.root = self.parent / "resources"
        self.archives = self.parent / "archives"

    def directories(self, *, create=False):
        """Reject symlinked managed directories and optionally make them durable."""
        paths = [self.parent, self.root, self.archives]
        paths.extend(
            self.root / name for name in ("objects", "receipts", "refs", "tmp")
        )
        for path in paths:
            if path.is_symlink() or (path.exists() and not path.is_dir()):
                raise _resource_types.ResourceIntegrityError(
                    "cache_path", f"invalid directory: {path}"
                )
            if create:
                path.mkdir(parents=True, exist_ok=True)
        if create:
            for path in dict.fromkeys([*reversed(paths), *self.parent.parents]):
                _lifecycle_io.sync_directory(path)

    def body_path(self, kind, digest):
        """Archive storage is shared with offline lifecycle retention."""
        _hash(digest)
        if kind == "archive":
            return self.archives / f"{digest}.tar.bz2"
        return self.root / "objects" / digest

    def lookup(self, request, max_bytes):
        """Return verified evidence, or None for a genuinely absent reference."""
        self.directories()
        reference = self.root / "refs" / (request.key + ".json")
        if not reference.exists() and not reference.is_symlink():
            return None
        ref = _lifecycle_io.read_json(reference, 1024)
        if (
            set(ref) != {"schema_version", "receipt"}
            or type(ref["schema_version"]) is not int
            or ref["schema_version"] != 1
        ):
            raise _resource_types.ResourceIntegrityError(
                "cache_schema", "invalid request reference"
            )
        receipt_hash = _hash(ref["receipt"])
        path = self.root / "receipts" / (receipt_hash + ".json")
        digest, _ = _lifecycle_io.hash_file(path, _METADATA_LIMIT)
        if digest != receipt_hash:
            raise _resource_types.ResourceIntegrityError(
                "receipt_hash", "receipt bytes changed"
            )
        value = _lifecycle_io.read_json(path, _METADATA_LIMIT)
        receipt = self._receipt(value, request)
        body = self.body_path(request.kind, receipt.sha256)
        actual = _lifecycle_io.hash_file(body, max_bytes)
        if actual != (receipt.sha256, receipt.size):
            raise _resource_types.ResourceIntegrityError(
                "body_hash", "cached original bytes changed"
            )
        return _resource_types.SourceArtifact(body, *actual, receipt_hash, receipt)

    @staticmethod
    def _receipt(value, request):
        """Validate persisted untrusted metadata before constructing public records."""
        try:
            if set(value) != {
                field.name
                for field in dataclasses.fields(_resource_types.RetrievalReceipt)
            }:
                raise ValueError("receipt fields differ from schema")
            if type(value["schema_version"]) is not int or value["schema_version"] != 1:
                raise ValueError("unsupported receipt schema")
            if (
                value["transport_version"] != "urllib-get-v1"
                or type(value["status"]) is not int
                or value["status"] != 200
            ):
                raise ValueError("unsupported transport/status")
            original = _resource_types.SourceRequest(
                value["source_uri"],
                value["request_url"],
                value["kind"],
                value["route_policy"],
            )
            if original.key != request.key or value["request_key"] != request.key:
                raise ValueError("receipt does not belong to request")
            _hash(value["sha256"])
            if type(value["size"]) is not int or value["size"] < 0:
                raise ValueError("invalid body size")
            stamp = datetime.datetime.fromisoformat(value["retrieved_at"])
            if stamp.tzinfo is None or stamp.utcoffset() != datetime.timedelta(0):
                raise ValueError("retrieval timestamp must be UTC")
            redirects = value["redirects"]
            if not isinstance(redirects, list) or len(redirects) > 256:
                raise ValueError("invalid redirect evidence")
            for url in [value["final_url"], *redirects]:
                if _resource_types.canonical_url(url) != url:
                    raise ValueError("noncanonical route evidence")
            if value["final_url"] != (
                redirects[-1] if redirects else request.request_url
            ):
                raise ValueError("final URL does not match route")
            headers = value["headers"]
            if not isinstance(headers, list) or len(headers) > len(_HEADERS):
                raise ValueError("invalid headers")
            seen = set()
            for pair in headers:
                if not isinstance(pair, list) or len(pair) != 2:
                    raise ValueError("invalid header pair")
                key, val = pair
                if (
                    key not in _HEADERS
                    or key in seen
                    or not isinstance(val, str)
                    or len(val) > 8192
                    or any(ord(c) < 32 and c != "\t" for c in val)
                ):
                    raise ValueError("invalid stored header")
                seen.add(key)
            value = dict(
                value,
                redirects=tuple(redirects),
                headers=tuple(tuple(pair) for pair in headers),
            )
            return _resource_types.RetrievalReceipt(**value)
        except (
            ValueError,
            TypeError,
            KeyError,
            _resource_types.ResourceInputError,
        ) as exc:
            raise _resource_types.ResourceIntegrityError(
                "cache_schema", str(exc)
            ) from exc

    def temporary(self):
        """Return an unpredictable exclusive-write path, never a cache hit."""
        return self.root / "tmp" / (uuid.uuid4().hex + ".part")

    def _immutable(self, temporary, target, expected, limit):
        """Publish without overwriting; verify an existing object before reusing it."""
        try:
            os.link(temporary, target)
        except FileExistsError:
            if _lifecycle_io.hash_file(target, limit) != expected:
                raise _resource_types.ResourceIntegrityError(
                    "object_collision", "existing immutable object is corrupt"
                )
        _lifecycle_io.sync_directory(target.parent)

    def publish(self, temporary, receipt, max_bytes):
        """Commit body, receipt, then reference; partial publication is never a hit."""
        payload = _resource_types.canonical_json(dataclasses.asdict(receipt))
        if len(payload) > _METADATA_LIMIT:
            raise _resource_types.ResourceIntegrityError(
                "metadata_limit", "receipt exceeds byte budget"
            )
        self._immutable(
            temporary,
            self.body_path(receipt.kind, receipt.sha256),
            (receipt.sha256, receipt.size),
            max_bytes,
        )
        digest = hashlib.sha256(payload).hexdigest()
        receipt_temp = self.temporary()
        try:
            with receipt_temp.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            self._immutable(
                receipt_temp,
                self.root / "receipts" / (digest + ".json"),
                (digest, len(payload)),
                _METADATA_LIMIT,
            )
            # Hard-link removal changes inode ctime. Finish it before making
            # the reference visible, so concurrent integrity checks see stable
            # immutable objects throughout their reads.
            temporary.unlink()
            receipt_temp.unlink()
            _lifecycle_io.sync_directory(temporary.parent)
            try:
                _lifecycle_io.atomic_json(
                    self.root / "refs" / (receipt.request_key + ".json"),
                    {"schema_version": 1, "receipt": digest},
                )
            except errors.CatalogPublicationError as exc:
                # Only reference replacement makes a resource publicly visible;
                # a pacing-state durability failure must not claim publication.
                raise _resource_types.ResourcePublicationError(
                    "publication_uncertain", str(exc)
                ) from exc
        finally:
            try:
                receipt_temp.unlink(missing_ok=True)
            except OSError:
                # Preserve a more useful publication failure/uncertainty signal.
                # Unreferenced temporary files are never considered cache hits.
                pass
        return _resource_types.SourceArtifact(
            self.body_path(receipt.kind, receipt.sha256),
            receipt.sha256,
            receipt.size,
            digest,
            receipt,
        )
