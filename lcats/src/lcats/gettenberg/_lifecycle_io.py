"""Bounded local I/O and process-safe coordination for catalog generations.

Directory fsync provides the POSIX publication durability barrier. On Windows,
where Python cannot portably fsync a directory, atomic replacement protects
against process crashes; power-loss durability is not guaranteed.
"""

import contextlib
import hashlib
import json
import math
import os
import pathlib
import sqlite3
import stat
import time
import uuid

from lcats.gettenberg import errors

_CHUNK_BYTES = 128 * 1024


def _limit(max_bytes):
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 0:
        raise errors.CatalogInputError("max_bytes must be a nonnegative integer")


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _regular(path, missing_ok=False):
    try:
        info = path.lstat()
    except FileNotFoundError:
        if missing_ok:
            return None
        raise
    if not stat.S_ISREG(info.st_mode):
        raise errors.CatalogLifecycleError(f"Not a regular nonsymlink file: {path}")
    return info


@contextlib.contextmanager
def _source(path, *, replaceable=False):
    """Open a regular file without following its final symlink component."""
    before = _regular(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or (
            not replaceable and _identity(before) != _identity(opened)
        ):
            raise errors.CatalogLifecycleError(f"Source changed while opening: {path}")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None
            yield stream, opened
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _stable(path, stream, before, *, replaceable=False):
    if replaceable:
        # Atomic replacement can unlink this opened inode, changing ctime but
        # not its bytes. Readers own this descriptor snapshot, not the pathname.
        after = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise errors.CatalogLifecycleError(
                f"Opened JSON changed while reading: {path}"
            )
        return
    if _identity(before) != _identity(os.fstat(stream.fileno())) or _identity(
        before
    ) != _identity(_regular(path)):
        raise errors.CatalogLifecycleError(f"Source changed while reading: {path}")


@contextlib.contextmanager
def writer_lock(path: pathlib.Path, timeout: float = 10.0):
    """Hold a persistent SQLite writer lock, released automatically on death.

    The caller creates the parent directory. The coordination inode is never
    deleted. A busy lock has a monotonic timeout between zero and 60 seconds.
    """
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not 0 <= timeout <= 60
        or not math.isfinite(timeout)
    ):
        raise errors.CatalogInputError("timeout must be finite and between 0 and 60")
    path = pathlib.Path(path)
    connection = None
    try:
        _regular(path, missing_ok=True)
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags, 0o600)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode):
                raise errors.CatalogLifecycleError(f"Invalid lock file: {path}")
        finally:
            os.close(descriptor)
        connection = sqlite3.connect(path, timeout=0, isolation_level=None)
        current = _regular(path)
        if (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino):
            raise errors.CatalogLifecycleError(f"Lock file changed: {path}")
        deadline = time.monotonic() + timeout
        while True:
            try:
                connection.execute("BEGIN IMMEDIATE")
                break
            except sqlite3.OperationalError as exc:
                code = getattr(exc, "sqlite_errorcode", 0) & 0xFF
                if code not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                    raise
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise errors.CatalogLockError(
                        f"Writer lock timed out: {path}"
                    ) from exc
                time.sleep(min(0.05, remaining))
    except (OSError, sqlite3.Error) as exc:
        if connection is not None:
            _close_lock(connection, path)
        raise errors.CatalogLifecycleError(
            f"Cannot acquire writer lock {path}: {exc}"
        ) from exc
    except BaseException:
        if connection is not None:
            _close_lock(connection, path)
        raise
    try:
        yield
    finally:
        _close_lock(connection, path)


def _close_lock(connection, path):
    try:
        connection.close()
    except sqlite3.Error as exc:
        raise errors.CatalogLifecycleError(
            f"Cannot release writer lock: {path}"
        ) from exc


def read_json(path: pathlib.Path, max_bytes=65536) -> dict:
    """Read a bounded UTF-8 JSON object from a regular nonsymlink file."""
    _limit(max_bytes)
    path = pathlib.Path(path)
    try:
        with _source(path, replaceable=True) as (stream, before):
            if before.st_size > max_bytes:
                raise errors.CatalogLifecycleError(f"JSON exceeds size limit: {path}")
            payload = stream.read(max_bytes + 1)
            _stable(path, stream, before, replaceable=True)
        if len(payload) > max_bytes:
            raise errors.CatalogLifecycleError(f"JSON exceeds size limit: {path}")
        value = json.loads(payload.decode("utf-8"), parse_constant=_invalid_constant)
        if not isinstance(value, dict):
            raise errors.CatalogLifecycleError(f"JSON must contain an object: {path}")
        return value
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise errors.CatalogLifecycleError(f"Cannot read JSON {path}: {exc}") from exc


def _invalid_constant(value):
    raise ValueError(f"Invalid JSON constant: {value}")


def sync_directory(path: pathlib.Path):
    """Persist POSIX directory changes; Windows offers process-crash safety only."""
    if os.name == "nt":
        return
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise errors.CatalogLifecycleError(
            f"Cannot sync directory {path}: {exc}"
        ) from exc


def _discard(path):
    try:
        path.unlink(missing_ok=True)
    except OSError:
        # Preserve the original failure; cleanup recognizes these generated names.
        pass


def atomic_json(path: pathlib.Path, value) -> None:
    """Atomically publish canonical JSON and report post-publication sync errors."""
    path = pathlib.Path(path)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise errors.CatalogInputError(
            f"Value is not JSON serializable: {exc}"
        ) from exc
    try:
        _regular(path, missing_ok=True)
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        _regular(path, missing_ok=True)
        os.replace(temporary, path)
        try:
            sync_directory(path.parent)
        except (OSError, errors.CatalogLifecycleError) as exc:
            raise errors.CatalogPublicationError(
                f"JSON was published but directory sync failed: {path}", published=True
            ) from exc
    except OSError as exc:
        raise errors.CatalogLifecycleError(
            f"Cannot publish JSON {path}: {exc}"
        ) from exc
    finally:
        _discard(temporary)


def _transfer(path, max_bytes, check, destination=None):
    digest = hashlib.sha256()
    size = 0
    with _source(path) as (stream, before):
        if before.st_size > max_bytes:
            raise errors.CatalogLifecycleError(f"File exceeds size limit: {path}")
        while True:
            if check is not None:
                check()
            chunk = stream.read(min(_CHUNK_BYTES, max_bytes - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                raise errors.CatalogLifecycleError(f"File exceeds size limit: {path}")
            digest.update(chunk)
            if destination is not None:
                destination.write(chunk)
        _stable(path, stream, before)
    return digest.hexdigest(), size


def hash_file(path: pathlib.Path, max_bytes, check=None) -> tuple[str, int]:
    """Hash a bounded stable regular file, checking cancellation each chunk."""
    _limit(max_bytes)
    path = pathlib.Path(path)
    try:
        return _transfer(path, max_bytes, check)
    except OSError as exc:
        raise errors.CatalogLifecycleError(f"Cannot hash file {path}: {exc}") from exc


@contextlib.contextmanager
def archive_publication_lock(archives, timeout=10.0):
    """Coordinate archive publishers without weakening content stability checks.

    Catalog writers and resource downloaders have separate outer locks. Both
    take this leaf lock for publication/verification and temporary-link cleanup;
    neither acquires an outer lock while holding it. Cache hits need no lock.
    Keep the persistent lock outside the immutable archive namespace.
    """
    with writer_lock(
        pathlib.Path(archives).parent / "archive-publication.sqlite", timeout
    ):
        yield


def retain_archive(
    source, archives, max_bytes, check=None, *, expected=None, lock_timeout=10.0
):
    """Retain verified bytes under the shared archive publication leaf lock."""
    _limit(max_bytes)
    with archive_publication_lock(archives, lock_timeout):
        return _retain_archive(source, archives, max_bytes, check, expected=expected)


def _retain_archive(
    source: pathlib.Path,
    archives: pathlib.Path,
    max_bytes,
    check=None,
    *,
    expected=None,
) -> tuple[pathlib.Path, str, int]:
    """Retain an immutable content-addressed copy without replacing existing data.

    A same-directory hard link atomically publishes the fsynced temporary inode
    without clobbering another retained archive. Existing copies are verified.
    An expected (SHA256, size) identity is checked before publication.
    The archive filesystem must support hard links; otherwise publication fails
    with a lifecycle error and existing files remain untouched.
    """
    _limit(max_bytes)
    source = pathlib.Path(source)
    archives = pathlib.Path(archives)
    temporary = archives / f".archive.{uuid.uuid4().hex}.tmp"
    try:
        with temporary.open("xb") as stream:
            digest, size = _transfer(source, max_bytes, check, stream)
            stream.flush()
            os.fsync(stream.fileno())
        if expected is not None and (digest, size) != expected:
            raise errors.CatalogLifecycleError(
                "retained source differs from the active manifest; implicit rebuild refused"
            )
        target = archives / f"{digest}.tar.bz2"
        try:
            os.link(temporary, target)
        except FileExistsError:
            existing_digest, existing_size = hash_file(target, max_bytes, check)
            if (existing_digest, existing_size) != (digest, size):
                raise errors.CatalogLifecycleError(
                    f"Retained archive is corrupt: {target}"
                )
        temporary.unlink()
        sync_directory(archives)
        return target, digest, size
    except OSError as exc:
        raise errors.CatalogLifecycleError(
            f"Cannot retain archive {source}: {exc}"
        ) from exc
    finally:
        _discard(temporary)
