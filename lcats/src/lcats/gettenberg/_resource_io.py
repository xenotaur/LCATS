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


def local_call(operation, *args, **kwargs):
    """Translate one local I/O boundary before an enclosing network handler.

    Do not wrap response reads: network timeouts must remain transport failures,
    while filesystem TimeoutError/ConnectionError must never cause another GET.
    """
    with translated_errors():
        return operation(*args, **kwargs)


def _hash(value):
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        raise _resource_types.ResourceIntegrityError(
            "cache_schema", "invalid content identity"
        )
    return value


def _stored_headers(headers):
    """Validate selected persisted headers from retrieval or validation evidence."""
    if not isinstance(headers, list) or len(headers) > len(_HEADERS):
        raise ValueError("invalid headers")
    seen = set()
    for pair in headers:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError("invalid header pair")
        key, val = pair
        if (
            not isinstance(key, str)
            or key not in _HEADERS
            or key in seen
            or not isinstance(val, str)
            or len(val) > 8192
            or any(ord(c) < 32 and c != "\t" for c in val)
        ):
            raise ValueError("invalid stored header")
        seen.add(key)
    return tuple(tuple(pair) for pair in headers)


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
            version = value.get("schema_version")
            if type(version) is not int or version not in (1, 2):
                raise ValueError("unsupported receipt schema")
            fields = {
                field.name
                for field in dataclasses.fields(_resource_types.RetrievalReceipt)
            }
            if version == 1:
                fields -= {
                    "validated_at",
                    "previous_receipt_sha256",
                    "validation_headers",
                }
            if set(value) != fields:
                raise ValueError("receipt fields differ from schema")
            if (
                value["transport_version"] != "urllib-get-v1"
                or type(value["status"]) is not int
                or value["status"] not in ((200,) if version == 1 else (200, 304))
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
            if version == 2:
                previous = value["previous_receipt_sha256"]
                if previous is not None:
                    _hash(previous)
                validated = value["validated_at"]
                if value["status"] == 304:
                    if previous is None or not isinstance(validated, str):
                        raise ValueError(
                            "validation needs a previous receipt and timestamp"
                        )
                    validation_stamp = datetime.datetime.fromisoformat(validated)
                    if (
                        validation_stamp.tzinfo is None
                        or validation_stamp.utcoffset() != datetime.timedelta(0)
                    ):
                        raise ValueError("validation timestamp must be UTC")
                elif validated is not None:
                    raise ValueError(
                        "200 acquisition cannot claim a 304 validation time"
                    )
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
            headers = _stored_headers(value["headers"])
            validation_headers = _stored_headers(value.get("validation_headers", []))
            if value["status"] == 200 and validation_headers:
                raise ValueError("200 acquisition cannot claim 304 headers")
            if any(dict(headers).get(key) != val for key, val in validation_headers):
                raise ValueError("validation headers disagree with effective headers")
            value = dict(value, redirects=tuple(redirects), headers=headers)
            if version == 2:
                value["validation_headers"] = validation_headers
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

    def discard(self, temporary, kind, lock_timeout):
        """Best-effort cleanup; never unlink a shared archive outside its lock."""
        try:
            with translated_errors():
                if not temporary.exists() and not temporary.is_symlink():
                    return
                lock = (
                    _lifecycle_io.archive_publication_lock(self.archives, lock_timeout)
                    if kind == "archive"
                    else contextlib.nullcontext()
                )
                with lock:
                    if kind == "archive" and temporary.lstat().st_nlink > 1:
                        # Original publication already left its critical section.
                        # A catalog verifier may now read without the leaf lock.
                        # Retain linked orphans rather than changing its inode.
                        return
                    temporary.unlink(missing_ok=True)
        except _resource_types.ResourceError:
            # A leftover link is safer than racing a published archive reader.
            # Do not replace the acquisition/publication failure with cleanup.
            pass

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

    def publish(self, temporary, receipt, max_bytes, lock_timeout=10.0):
        """Commit body, receipt, then reference; partial publication is never a hit."""
        archive_lock = (
            _lifecycle_io.archive_publication_lock(self.archives, lock_timeout)
            if receipt.kind == "archive"
            else contextlib.nullcontext()
        )
        with archive_lock:
            try:
                self._immutable(
                    temporary,
                    self.body_path(receipt.kind, receipt.sha256),
                    (receipt.sha256, receipt.size),
                    max_bytes,
                )
            finally:
                # Cleanup is inside the leaf lock even when directory fsync
                # failed after link publication. Later retries take it again.
                temporary.unlink(missing_ok=True)
                _lifecycle_io.sync_directory(temporary.parent)
        return self.publish_receipt(receipt)

    def revalidate(self, artifact, receipt, max_bytes, lock_timeout):
        """Verify unchanged bytes and publish validation without touching their inode.

        The archive leaf lock excludes retention while checking/publishing; the
        outer network lock is already held. Readers keep stable immutable files.
        """
        lock = (
            _lifecycle_io.archive_publication_lock(self.archives, lock_timeout)
            if receipt.kind == "archive"
            else contextlib.nullcontext()
        )
        with lock:
            if _lifecycle_io.hash_file(artifact.path, max_bytes) != (
                receipt.sha256,
                receipt.size,
            ):
                raise _resource_types.ResourceIntegrityError(
                    "body_hash", "cached original bytes changed during validation"
                )
            return self.publish_receipt(receipt)

    def publish_receipt(self, receipt):
        """Durably append receipt evidence, then atomically select it for the request."""
        payload = _resource_types.canonical_json(_resource_types.receipt_value(receipt))
        if len(payload) > _METADATA_LIMIT:
            raise _resource_types.ResourceIntegrityError(
                "metadata_limit", "receipt exceeds byte budget"
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
            receipt_temp.unlink()
            _lifecycle_io.sync_directory(receipt_temp.parent)
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
