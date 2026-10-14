"""Offline, recoverable catalog generations with explicit activation and cleanup."""

import contextlib
import dataclasses
import datetime
import hashlib
import math
import os
import pathlib
import re
import shutil
import sqlite3
import time
import uuid

from lcats.gettenberg import _lifecycle_io
from lcats.gettenberg import _store
from lcats.gettenberg import catalog
from lcats.gettenberg import errors
from lcats.gettenberg import ingestion
from lcats.utils import env

_ID = re.compile(r"[0-9a-f]{32}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_MANIFEST_VERSION = 1
_COUNT_TABLES = (
    "ebooks",
    "sources",
    "archive_members",
    "titles",
    "contributions",
    "resources",
    "diagnostics",
)


def _identifier(value: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise errors.CatalogInputError(
            "generation ID must be 32 lowercase hexadecimal characters"
        )
    return value


def _seconds(value: float, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 < value <= 3600
    ):
        raise errors.CatalogInputError(
            f"{name} must be finite, positive and at most 3600 seconds"
        )
    return float(value)


class _Deadline:
    def __init__(self, seconds):
        self.ends = time.monotonic() + seconds

    def expired(self):
        return time.monotonic() >= self.ends

    def check(self):
        if self.expired():
            raise errors.CatalogLifecycleError(
                "catalog verification/copy time limit exceeded"
            )


@dataclasses.dataclass(frozen=True, slots=True)
class Generation:
    """A detached generation description; changing its manifest never writes storage."""

    generation_id: str
    catalog_path: pathlib.Path
    archive_path: pathlib.Path
    manifest: dict
    previous_count: int | None = None
    reused: bool = False


class CatalogManager:
    """Manage local candidates, retained sources, and an atomic active reference.

    Args:
        cache_dir: LCATS cache root; None resolves LCATS_CACHE_DIR at construction.
        lock_timeout: Writer contention timeout in seconds, from zero to 60.
        validation_seconds: Per-copy or full-verification elapsed ceiling.

    Construction performs no writes. All methods are offline. Published generations
    and retained archives survive cleanup so opened readers and reproduction inputs
    remain available. This is a cooperative local cache, not a security boundary
    against another process with permission to modify its files.
    """

    def __init__(
        self,
        cache_dir: str | pathlib.Path | None = None,
        *,
        lock_timeout: float = 10.0,
        validation_seconds: float = 120.0,
    ):
        if (
            isinstance(lock_timeout, bool)
            or not isinstance(lock_timeout, (int, float))
            or not math.isfinite(lock_timeout)
            or not 0 <= lock_timeout <= 60
        ):
            raise errors.CatalogInputError(
                "lock_timeout must be finite and between zero and 60 seconds"
            )
        self.cache_dir = (
            pathlib.Path(env.cache_root() if cache_dir is None else cache_dir)
            .expanduser()
            .resolve()
        )
        self.root = self.cache_dir / "gettenberg"
        self.lock_timeout = float(lock_timeout)
        self.validation_seconds = _seconds(validation_seconds, "validation_seconds")

    def _directory(self, path: pathlib.Path, *, create=False):
        if path.is_symlink():
            raise errors.CatalogLifecycleError(
                f"managed directory is a symlink: {path}"
            )
        if create:
            path.mkdir(parents=True, exist_ok=True)
        if path.exists() and not path.is_dir():
            raise errors.CatalogLifecycleError(
                f"managed path is not a directory: {path}"
            )
        return path

    def _paths(self, *, create=False):
        self._directory(self.root, create=create)
        for name in ("candidates", "generations", "archives"):
            self._directory(self.root / name, create=create)
        if create:
            # Persist the whole containing hierarchy, including a newly created
            # cache root. Repeat on retries/concurrent setup: an existing entry
            # may have been left by a creator that died before its parent sync.
            for parent in (self.root, *self.root.parents):
                _lifecycle_io.sync_directory(parent)

    @contextlib.contextmanager
    def _writer(self):
        try:
            self._paths(create=True)
            with _lifecycle_io.writer_lock(
                self.root / "writer.sqlite", self.lock_timeout
            ):
                yield
        except errors.CatalogError:
            raise
        except (OSError, sqlite3.Error) as exc:
            raise errors.CatalogLifecycleError(
                f"catalog filesystem/coordination failure: {exc}"
            ) from exc

    def _pointer(self):
        self._paths()
        path = self.root / "active.json"
        if not path.exists() and not path.is_symlink():
            return None
        value = _lifecycle_io.read_json(path)
        if value.get("version") != 1 or type(value.get("version")) is not int:
            raise errors.CatalogLifecycleError("unsupported active-pointer version")
        _identifier(value.get("generation_id"))
        digest = value.get("manifest_sha256")
        if not isinstance(digest, str) or not _HASH.fullmatch(digest):
            raise errors.CatalogLifecycleError(
                "active pointer has no valid manifest hash"
            )
        return value

    def _load(self, identifier, *, candidate=False, expected_hash=None):
        identifier = _identifier(identifier)
        self._paths()
        path = self._directory(
            self.root / ("candidates" if candidate else "generations") / identifier
        )
        if not path.is_dir():
            raise errors.CatalogMissingError(f"generation is missing: {identifier}")
        manifest_path = path / "manifest.json"
        manifest = _lifecycle_io.read_json(manifest_path)
        digest, _ = _lifecycle_io.hash_file(manifest_path, 65536)
        if expected_hash is not None and digest != expected_hash:
            raise errors.CatalogLifecycleError(
                "active manifest fingerprint differs from its pointer"
            )
        if (
            manifest.get("version") != _MANIFEST_VERSION
            or type(manifest.get("version")) is not int
        ):
            raise errors.CatalogSchemaError("unsupported generation manifest version")
        if (
            manifest.get("generation_id") != identifier
            or type(manifest.get("schema_version")) is not int
            or manifest.get("schema_version") != _store.SCHEMA_VERSION
            or manifest.get("parser_version") != _store.PARSER_VERSION
        ):
            raise errors.CatalogSchemaError(
                "generation identity/schema/parser is incompatible"
            )
        for field in ("archive_sha256", "database_sha256", "snapshot_id"):
            if not isinstance(manifest.get(field), str) or not _HASH.fullmatch(
                manifest[field]
            ):
                raise errors.CatalogLifecycleError(f"invalid manifest {field}")
        for field in ("archive_bytes", "database_bytes"):
            if type(manifest.get(field)) is not int or manifest[field] <= 0:
                raise errors.CatalogLifecycleError(f"invalid manifest {field}")
        counts = manifest.get("counts")
        if (
            not isinstance(counts, dict)
            or any(
                type(counts.get(t)) is not int or counts[t] < 0 for t in _COUNT_TABLES
            )
            or not counts["ebooks"]
        ):
            raise errors.CatalogLifecycleError("invalid manifest counts")
        database = path / "catalog.sqlite"
        archive = self.root / "archives" / (manifest["archive_sha256"] + ".tar.bz2")
        snapshot = hashlib.sha256(
            f"{manifest['archive_sha256']}:{_store.SCHEMA_VERSION}:{_store.PARSER_VERSION}".encode(
                "ascii"
            )
        ).hexdigest()
        if manifest["snapshot_id"] != snapshot:
            raise errors.CatalogLifecycleError(
                "logical snapshot identity is inconsistent"
            )
        for file in (database, archive):
            if file.is_symlink() or not file.is_file():
                raise errors.CatalogLifecycleError(
                    f"generation file missing or unsafe: {file}"
                )
        if archive.stat().st_size != manifest["archive_bytes"]:
            raise errors.CatalogLifecycleError("retained archive size changed")
        if database.stat().st_size != manifest["database_bytes"]:
            raise errors.CatalogLifecycleError("generation database size changed")
        return Generation(identifier, database, archive, manifest)

    def _active(self):
        pointer = self._pointer()
        if pointer is None:
            return None
        return self._load(
            pointer["generation_id"], expected_hash=pointer["manifest_sha256"]
        )

    def open(self) -> catalog.Catalog:
        """Open a reader pinned to the active immutable generation, without writes.

        Raises:
            CatalogMissingError: No generation is active.
            CatalogError: Pointer, manifest, schema or completion state is invalid.
        """
        try:
            generation = self._active()
            if generation is None:
                raise errors.CatalogMissingError(
                    "no active catalog; setup requires a local archive"
                )
            reader = catalog.Catalog(generation.catalog_path)
            try:
                self._check_info(reader.info, generation.manifest)
            except BaseException:
                reader.close()
                raise
            return reader
        except errors.CatalogError:
            raise
        except OSError as exc:
            raise errors.CatalogLifecycleError(
                f"cannot open managed catalog: {exc}"
            ) from exc

    @staticmethod
    def _check_info(info, manifest):
        report = info.get("report")
        if (
            not isinstance(report, dict)
            or info.get("schema_version") != _store.SCHEMA_VERSION
        ):
            raise errors.CatalogSchemaError("catalog build metadata is incompatible")
        expected = {
            "archive_sha256": manifest["archive_sha256"],
            "archive_bytes": manifest["archive_bytes"],
            "imported": manifest["counts"]["ebooks"],
            "members": manifest["counts"]["archive_members"],
            "diagnostics": manifest["counts"]["diagnostics"],
            "rejected": 0,
            "uncommitted": 0,
        }
        if any(
            report.get(k) != v or type(report.get(k)) is not type(v)
            for k, v in expected.items()
        ):
            raise errors.CatalogLifecycleError(
                "manifest and catalog build accounting disagree"
            )

    def _verify(self, database, archive, archive_sha, archive_bytes):
        deadline = _Deadline(self.validation_seconds)
        digest, size = _lifecycle_io.hash_file(archive, archive_bytes, deadline.check)
        if (digest, size) != (archive_sha, archive_bytes):
            raise errors.CatalogLifecycleError("retained archive identity changed")
        with catalog.Catalog(database) as reader:
            info = reader.info
        counts = {}
        try:
            with contextlib.closing(
                sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
            ) as connection:
                connection.set_progress_handler(lambda: int(deadline.expired()), 10000)
                if connection.execute(
                    "PRAGMA foreign_key_check"
                ).fetchone() is not None or connection.execute(
                    "PRAGMA integrity_check"
                ).fetchall() != [
                    ("ok",)
                ]:
                    raise errors.CatalogLifecycleError(
                        "catalog integrity or relationships failed"
                    )
                for table in _COUNT_TABLES:
                    counts[table] = connection.execute(
                        f"SELECT count(*) FROM {table}"
                    ).fetchone()[0]
                rejected = connection.execute(
                    "SELECT count(*) FROM archive_members WHERE disposition != 'imported'"
                ).fetchone()[0]
                if (
                    rejected
                    or not counts["ebooks"]
                    or counts["sources"] != counts["ebooks"]
                    or counts["archive_members"] != counts["ebooks"]
                ):
                    raise errors.CatalogLifecycleError(
                        "catalog actual record accounting is incomplete"
                    )
        except sqlite3.Error as exc:
            raise errors.CatalogLifecycleError(
                f"catalog verification failed or exceeded time limit: {exc}"
            ) from exc
        manifest = {
            "archive_sha256": archive_sha,
            "archive_bytes": archive_bytes,
            "counts": counts,
        }
        self._check_info(info, manifest)
        deadline.check()
        database_limit = info.get("limits", {}).get("max_database_bytes")
        if type(database_limit) is not int or database_limit < 4096:
            raise errors.CatalogLifecycleError("invalid recorded database size limit")
        digest, size = _lifecycle_io.hash_file(database, database_limit, deadline.check)
        return counts, digest, size

    def _prepare_candidate(self, source, limits, expected_archive=None):
        limits = ingestion.BuildLimits() if limits is None else limits
        if not isinstance(limits, ingestion.BuildLimits):
            raise errors.CatalogInputError("limits must be BuildLimits")
        archive, digest, size = _lifecycle_io.retain_archive(
            pathlib.Path(source),
            self.root / "archives",
            limits.max_compressed_bytes,
            _Deadline(self.validation_seconds).check,
            expected=expected_archive,
        )
        identifier = uuid.uuid4().hex
        path = self.root / "candidates" / identifier
        path.mkdir()
        database = path / "catalog.sqlite"
        ingestion.build_catalog(archive, database, limits=limits)
        counts, database_digest, database_size = self._verify(
            database, archive, digest, size
        )
        snapshot = hashlib.sha256(
            f"{digest}:{_store.SCHEMA_VERSION}:{_store.PARSER_VERSION}".encode("ascii")
        ).hexdigest()
        manifest = {
            "version": _MANIFEST_VERSION,
            "generation_id": identifier,
            "schema_version": _store.SCHEMA_VERSION,
            "parser_version": _store.PARSER_VERSION,
            "archive_sha256": digest,
            "archive_bytes": size,
            "database_sha256": database_digest,
            "database_bytes": database_size,
            "snapshot_id": snapshot,
            "counts": counts,
            "source": {
                "kind": "local_archive",
                "input_path": str(pathlib.Path(source).absolute()),
                "retrieved_at": None,
                "http_etag": None,
            },
            "prepared_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        try:
            _lifecycle_io.atomic_json(path / "manifest.json", manifest)
        except errors.CatalogPublicationError as exc:
            # Only the candidate manifest changed; the active pointer is intact.
            raise errors.CatalogLifecycleError(
                "candidate manifest durability failed; active catalog unchanged"
            ) from exc
        _lifecycle_io.sync_directory(path)
        _lifecycle_io.sync_directory(path.parent)
        return identifier

    def _activate(self, identifier, allow_count_change):
        if type(allow_count_change) is not bool:
            raise errors.CatalogInputError("allow_count_change must be bool")
        identifier = _identifier(identifier)
        candidate = (self.root / "candidates" / identifier).exists()
        generation = self._load(identifier, candidate=candidate)
        counts, digest, size = self._verify(
            generation.catalog_path,
            generation.archive_path,
            generation.manifest["archive_sha256"],
            generation.manifest["archive_bytes"],
        )
        if (
            counts != generation.manifest["counts"]
            or digest != generation.manifest["database_sha256"]
            or size != generation.manifest["database_bytes"]
        ):
            raise errors.CatalogLifecycleError(
                "prepared generation changed after sealing"
            )
        previous = self._active()
        previous_count = (
            None if previous is None else previous.manifest["counts"]["ebooks"]
        )
        count = counts["ebooks"]
        if (
            previous_count is not None
            and count != previous_count
            and not allow_count_change
        ):
            raise errors.CatalogCountChangeError(identifier, previous_count, count)
        # A recovered candidate may have survived a failed manifest-directory
        # sync. Establish that barrier again before publishing its active pointer.
        _lifecycle_io.sync_directory(generation.catalog_path.parent)
        if candidate:
            target = self.root / "generations" / identifier
            if target.exists() or target.is_symlink():
                raise errors.CatalogLifecycleError(
                    "generation destination already exists"
                )
            os.rename(generation.catalog_path.parent, target)
            _lifecycle_io.sync_directory(self.root / "candidates")
            _lifecycle_io.sync_directory(self.root / "generations")
            generation = self._load(identifier)
        manifest_hash, _ = _lifecycle_io.hash_file(
            generation.catalog_path.parent / "manifest.json", 65536
        )
        _lifecycle_io.atomic_json(
            self.root / "active.json",
            {
                "version": 1,
                "generation_id": identifier,
                "manifest_sha256": manifest_hash,
                "activated_at": datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
                "previous_generation_id": (
                    None if previous is None else previous.generation_id
                ),
                "previous_count": previous_count,
                "count": count,
                "count_change_approved": allow_count_change,
            },
        )
        return dataclasses.replace(generation, previous_count=previous_count)

    def setup(
        self,
        archive: str | pathlib.Path | None = None,
        *,
        limits: ingestion.BuildLimits | None = None,
    ) -> Generation:
        """Reuse a valid active catalog, or build/activate an explicit local archive.

        A supplied archive is ignored when a valid generation already exists.
        Invalid active metadata fails closed. Retained valid generations can be
        explicitly reactivated while the active pointer remains valid.
        """
        with self._writer():
            active = self._active()
            if active is not None:
                with self.open():
                    pass
                return dataclasses.replace(active, reused=True)
            if archive is None:
                raise errors.CatalogMissingError(
                    "setup needs an explicit local archive; no download is implicit"
                )
            return self._activate(self._prepare_candidate(archive, limits), False)

    def rebuild(
        self,
        archive: str | pathlib.Path | None = None,
        *,
        limits: ingestion.BuildLimits | None = None,
        allow_count_change: bool = False,
    ) -> Generation:
        """Build a new generation from local input, retaining the prior generation.

        Omit archive to reuse the active generation's retained source. A changed
        ebook count requires explicit approval; the error names a recoverable
        candidate which activate() can publish without rebuilding.
        """
        if type(allow_count_change) is not bool:
            raise errors.CatalogInputError("allow_count_change must be bool")
        with self._writer():
            expected_archive = None
            if archive is None:
                active = self._active()
                if active is None:
                    raise errors.CatalogMissingError(
                        "no active source archive to rebuild"
                    )
                archive = active.archive_path
                expected_archive = (
                    active.manifest["archive_sha256"],
                    active.manifest["archive_bytes"],
                )
            return self._activate(
                self._prepare_candidate(archive, limits, expected_archive),
                allow_count_change,
            )

    def activate(
        self, generation_id: str, *, allow_count_change: bool = False
    ) -> Generation:
        """Verify and activate a prepared candidate or retained generation by ID."""
        _identifier(generation_id)
        with self._writer():
            return self._activate(generation_id, allow_count_change)

    def status(self) -> dict:
        """Describe local state and preserved legacy paths without creating files.

        Invalid active metadata is reported with state=invalid and an error;
        open/activation still fail with structured errors. This lightweight
        inspection does not repeat full-file hashes or SQLite integrity scans.
        """
        result = {
            "cache_dir": str(self.cache_dir),
            "root": str(self.root),
            "state": "missing",
            "active": None,
            "candidates": [],
            "generations": [],
            "legacy": [],
            "retention": "published generations and source archives are never removed by cleanup",
        }
        try:
            self._paths()
            for name in ("candidates", "generations"):
                directory = self.root / name
                if directory.exists():
                    result[name] = sorted(
                        p.name
                        for p in directory.iterdir()
                        if _ID.fullmatch(p.name) and p.is_dir() and not p.is_symlink()
                    )
            pointer = self._pointer()
            if pointer is not None:
                active = self._load(
                    pointer["generation_id"], expected_hash=pointer["manifest_sha256"]
                )
                with catalog.Catalog(active.catalog_path) as reader:
                    self._check_info(reader.info, active.manifest)
                result.update(
                    state="ready",
                    active={
                        "generation_id": active.generation_id,
                        "catalog_path": str(active.catalog_path),
                        "archive_path": str(active.archive_path),
                        "manifest": active.manifest,
                        "activation": pointer,
                    },
                )
            for name in ("gutenbergindex.db", "rdf-files.tar.bz2", "texts", "tmp"):
                path = self.cache_dir / name
                if path.exists() or path.is_symlink():
                    result["legacy"].append(
                        {
                            "path": str(path),
                            "provenance": "unverified legacy artifact; preserved",
                        }
                    )
        except (OSError, errors.CatalogError) as exc:
            result.update(state="invalid", error=str(exc))
        return result

    def cleanup(self) -> tuple[str, ...]:
        """Remove abandoned candidates/known temp files, retaining all generations.

        Returns the exact removed paths. Cleanup is explicit and writer-locked;
        symlinked/unknown entries are left untouched. Published generations,
        retained archives and legacy files are never deleted.
        """
        removed = []
        with self._writer():
            for path in sorted((self.root / "candidates").iterdir()):
                if _ID.fullmatch(path.name) and path.is_dir() and not path.is_symlink():
                    shutil.rmtree(path)
                    removed.append(str(path))
            for directory, pattern in (
                (self.root, r"\.active\.json\.[0-9a-f]{32}\.tmp"),
                (self.root / "archives", r"\.archive\.[0-9a-f]{32}\.tmp"),
            ):
                for path in sorted(directory.iterdir()):
                    if (
                        re.fullmatch(pattern, path.name)
                        and path.is_file()
                        and not path.is_symlink()
                    ):
                        path.unlink()
                        removed.append(str(path))
            _lifecycle_io.sync_directory(self.root / "candidates")
        return tuple(removed)
