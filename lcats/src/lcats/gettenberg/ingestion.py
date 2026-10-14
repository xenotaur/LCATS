"""Bounded local tar.bz2 ingestion into an explicit, inactive SQLite candidate."""

import bz2
import dataclasses
import hashlib
import json
import math
import os
import pathlib
import sqlite3
import tarfile
import time

from lcats.gettenberg import _store
from lcats.gettenberg import errors
from lcats.gettenberg import rdf


@dataclasses.dataclass(frozen=True, slots=True)
class BuildLimits:
    """Explicit resource ceilings; elapsed checks are cooperative, not OS quotas."""

    max_compressed_bytes: int = 256 * 1024**2
    max_member_bytes: int = 2 * 1024**2
    max_expanded_bytes: int = 4 * 1024**3
    max_members: int = 200_000
    max_database_bytes: int = 4 * 1024**3
    max_seconds: float = 600.0

    def __post_init__(self):
        for field in dataclasses.fields(self):
            value = getattr(self, field.name)
            if field.name == "max_seconds":
                if (
                    type(value) not in (int, float)
                    or not math.isfinite(value)
                    or value <= 0
                ):
                    raise errors.CatalogInputError(
                        "max_seconds must be finite and positive"
                    )
            elif type(value) is not int or value <= 0:
                raise errors.CatalogInputError(
                    f"{field.name} must be a positive integer"
                )
        if self.max_database_bytes < 4096:
            raise errors.CatalogInputError(
                "max_database_bytes must allow at least one SQLite page"
            )


@dataclasses.dataclass(frozen=True, slots=True)
class BuildReport:
    """Final accounting; uncommitted records expose rollback after an abort."""

    output_path: str
    status: str
    archive_sha256: str | None
    archive_bytes: int
    expanded_bytes: int
    members: int
    imported: int
    rejected: int
    uncommitted: int
    diagnostics: int
    elapsed_seconds: float
    database_bytes: int


class _LimitExceeded(Exception):
    pass


class _CompressedInput:
    """Bound actual compressed reads and hash exactly the consumed bytes."""

    def __init__(self, raw, limit, check):
        self.raw, self.limit, self.check = raw, limit, check
        self.count = 0
        self.digest = hashlib.sha256()

    def read(self, size=-1):
        self.check()
        size = (
            self.limit - self.count + 1
            if size < 0
            else min(size, self.limit - self.count + 1)
        )
        data = self.raw.read(size)
        self.count += len(data)
        if self.count > self.limit:
            raise _LimitExceeded("compressed byte limit exceeded")
        self.digest.update(data)
        return data

    def seekable(self):
        return False


class _ExpandedInput:
    def __init__(self, stream, limit, check):
        self.stream, self.limit, self.check = stream, limit, check
        self.count = 0

    def read(self, size):
        self.check()
        data = self.stream.read(min(size, 65536, self.limit - self.count + 1))
        self.count += len(data)
        if self.count > self.limit:
            raise _LimitExceeded("expanded archive byte limit exceeded")
        return data

    def exact(self, size):
        chunks = []
        while size:
            chunk = self.read(size)
            if not chunk:
                raise ValueError("truncated tar member/header")
            chunks.append(chunk)
            size -= len(chunk)
        return b"".join(chunks)


def _metadata(connection, values):
    connection.executemany(
        "INSERT OR REPLACE INTO metadata(key,value) VALUES (?,?)",
        [(key, json.dumps(value, ensure_ascii=True)) for key, value in values.items()],
    )


def _disk_bytes(path):
    return sum(
        p.stat().st_size
        for p in (
            path,
            pathlib.Path(str(path) + "-journal"),
            pathlib.Path(str(path) + "-wal"),
            pathlib.Path(str(path) + "-shm"),
        )
        if p.exists()
    )


def _safe_name(name):
    return (
        bool(name)
        and len(name) <= 4096
        and "\\" not in name
        and not name.startswith("/")
        and all(part not in ("", ".", "..") for part in name.split("/"))
    )


def build_catalog(
    archive: str | pathlib.Path,
    output: str | pathlib.Path,
    *,
    limits: BuildLimits | None = None,
    batch_size: int = 256,
) -> BuildReport:
    """Stream a local tar.bz2 into a new candidate, without extraction or activation.

    Args:
        archive: Existing local compressed archive, opened read-only.
        output: Explicit new SQLite path. Existing files are never overwritten.
        limits: Validated byte/member/time ceilings, with documented defaults.
        batch_size: Number of examined members between commits (1..1000).

    Returns:
        Complete accounting after every record imports and integrity checks pass.

    Raises:
        errors.CatalogInputError: Invalid limits/batch arguments.
        errors.CatalogBuildError: Source, resource, record or integrity failure.
            Its report identifies any created candidate. Partial candidates are
            deliberately retained and cannot be opened by Catalog.
    """
    limits = BuildLimits() if limits is None else limits
    if not isinstance(limits, BuildLimits):
        raise errors.CatalogInputError("limits must be BuildLimits")
    if type(batch_size) is not int or not 1 <= batch_size <= 1000:
        raise errors.CatalogInputError("batch_size must be an integer in [1,1000]")
    archive, output = pathlib.Path(archive), pathlib.Path(output).absolute()
    started = time.monotonic()
    connection = None
    compressed = expanded = None
    members = 0
    source_complete = False
    created = False

    def check():
        if time.monotonic() - started >= limits.max_seconds:
            raise _LimitExceeded("elapsed build limit exceeded")

    def report(status):
        def count(table, where=""):
            if connection is None:
                return 0
            try:
                return connection.execute(
                    f"SELECT count(*) FROM {table} {where}"
                ).fetchone()[0]
            except sqlite3.Error:
                return 0

        imported = count("ebooks")
        rejected = count("archive_members", "WHERE disposition='rejected'")
        return BuildReport(
            str(output),
            status,
            compressed.digest.hexdigest() if compressed and source_complete else None,
            compressed.count if compressed else 0,
            expanded.count if expanded else 0,
            members,
            imported,
            rejected,
            max(0, members - imported - rejected),
            count("diagnostics"),
            time.monotonic() - started,
            _disk_bytes(output) if created else 0,
        )

    try:
        if not archive.is_file():
            raise ValueError("archive must be a regular local file")
        with archive.open("rb") as raw:
            source_stat = os.fstat(raw.fileno())
            if source_stat.st_size > limits.max_compressed_bytes:
                raise _LimitExceeded("compressed archive exceeds limit")
            # Exclusive creation protects existing candidates, archives and caches.
            with output.open("xb"):
                pass
            created = True
            connection = sqlite3.connect(output)
            connection.execute("PRAGMA page_size=4096")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA cache_size=-8192")
            connection.execute("PRAGMA temp_store=FILE")
            connection.execute(
                f"PRAGMA max_page_count={limits.max_database_bytes // 4096}"
            )
            connection.set_progress_handler(
                lambda: int(time.monotonic() - started >= limits.max_seconds), 10000
            )
            _store.create(connection)
            connection.execute(
                "CREATE TABLE archive_members (position INTEGER PRIMARY KEY,name TEXT NOT NULL,size INTEGER NOT NULL,disposition TEXT NOT NULL,code TEXT,message TEXT)"
            )
            connection.execute(
                "CREATE INDEX archive_member_name ON archive_members(name)"
            )
            _metadata(
                connection,
                {
                    "status": "building",
                    "schema_version": _store.SCHEMA_VERSION,
                    "parser_version": _store.PARSER_VERSION,
                    "archive_path": str(archive.absolute()),
                    "limits": dataclasses.asdict(limits),
                },
            )
            connection.commit()
            compressed = _CompressedInput(raw, limits.max_compressed_bytes, check)
            with bz2.BZ2File(compressed, "rb") as decoder:
                expanded = _ExpandedInput(decoder, limits.max_expanded_bytes, check)
                while True:
                    header = expanded.exact(512)
                    if header == bytes(512):
                        if expanded.exact(512) != bytes(512):
                            raise ValueError("tar requires two end blocks")
                        while chunk := expanded.read(65536):
                            if any(chunk):
                                raise ValueError("nonzero data after tar end marker")
                        # BZ2File may read ahead; hash any remaining compressed bytes.
                        while compressed.read(65536):
                            pass
                        source_complete = True
                        break
                    member = tarfile.TarInfo.frombuf(
                        header, encoding="utf-8", errors="strict"
                    )
                    members += 1
                    if members > limits.max_members:
                        raise _LimitExceeded("archive member count exceeded")
                    if member.size < 0 or member.size > limits.max_member_bytes:
                        raise _LimitExceeded("archive member size exceeded")
                    # Extension records are not interpreted: their declared size is
                    # bounded before any payload allocation, unlike implicit PAX parsing.
                    data = expanded.exact(member.size)
                    expanded.exact((-member.size) % 512)
                    code, message = None, None
                    if not member.isfile() or member.type not in (
                        tarfile.REGTYPE,
                        tarfile.AREGTYPE,
                    ):
                        code, message = (
                            "unsupported_member",
                            "only ordinary RDF file members are supported",
                        )
                    elif not _safe_name(member.name) or not member.name.endswith(
                        ".rdf"
                    ):
                        code, message = (
                            "unsafe_member",
                            "expected safe relative RDF member name",
                        )
                    elif connection.execute(
                        "SELECT 1 FROM archive_members WHERE name=? LIMIT 1",
                        (member.name,),
                    ).fetchone():
                        code, message = "duplicate_member", "member name repeats"
                    else:
                        connection.execute("SAVEPOINT record")
                        try:
                            parsed = rdf.parse_record(
                                data,
                                source_name=member.name,
                                max_bytes=limits.max_member_bytes,
                            )
                            _store.insert_record(connection, parsed)
                        except errors.RecordParseError as exc:
                            code, message = exc.code, str(exc)
                        except sqlite3.IntegrityError as exc:
                            code, message = "record_conflict", str(exc)
                        except BaseException:
                            connection.execute("ROLLBACK TO record")
                            connection.execute("RELEASE record")
                            raise
                        if code:
                            connection.execute("ROLLBACK TO record")
                        connection.execute("RELEASE record")
                    connection.execute(
                        "INSERT INTO archive_members VALUES (?,?,?,?,?,?)",
                        (
                            members,
                            member.name,
                            member.size,
                            "rejected" if code else "imported",
                            code,
                            message[:4096] if message else None,
                        ),
                    )
                    if members % batch_size == 0:
                        connection.commit()
                    if _disk_bytes(output) > limits.max_database_bytes:
                        raise _LimitExceeded(
                            "candidate plus SQLite sidecars exceeds disk limit"
                        )
                after = os.fstat(raw.fileno())
                if (
                    source_stat.st_size,
                    source_stat.st_mtime_ns,
                    source_stat.st_ctime_ns,
                ) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                    raise ValueError("archive changed during ingestion")
            connection.commit()
            summary = report("building")
            if summary.rejected or not summary.imported or summary.uncommitted:
                raise errors.CatalogBuildError(
                    "incomplete_records",
                    "rejected, empty or unaccounted archive",
                    summary,
                )
            check()
            if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise ValueError("foreign key check failed")
            if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise ValueError("SQLite integrity check failed")
            check()
            summary = report("complete")
            # Persist all evidence while the authoritative state is still building.
            # Mark complete only after the potentially allocating writes/checks.
            _metadata(connection, {"report": dataclasses.asdict(summary)})
            connection.commit()
            if _disk_bytes(output) > limits.max_database_bytes:
                raise _LimitExceeded("final candidate exceeds disk limit")
            check()
            final = dataclasses.replace(
                summary,
                database_bytes=_disk_bytes(output),
                elapsed_seconds=time.monotonic() - started,
            )
            _metadata(connection, {"status": "complete"})
            connection.commit()
            return final

    except (
        OSError,
        EOFError,
        ValueError,
        sqlite3.Error,
        tarfile.TarError,
        errors.CatalogBuildError,
        _LimitExceeded,
    ) as exc:
        if connection is not None:
            connection.set_progress_handler(None, 0)
            try:
                connection.rollback()
                summary = report("failed")
                _metadata(
                    connection,
                    {
                        "status": "failed",
                        "report": dataclasses.asdict(summary),
                        "failure": str(exc)[:4096],
                    },
                )
                connection.commit()
            except sqlite3.Error:
                # A full/damaged candidate may not allow writing even a failure
                # manifest. Its prior building state still prevents opening it.
                pass
        summary = report("failed") if created else None
        code = "resource_limit" if isinstance(exc, _LimitExceeded) else "build_failed"
        if isinstance(exc, errors.CatalogBuildError):
            code = exc.code
        raise errors.CatalogBuildError(code, str(exc), summary) from exc
    finally:
        if connection is not None:
            connection.close()
