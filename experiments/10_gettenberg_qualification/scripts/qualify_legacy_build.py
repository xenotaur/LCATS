"""Measure the installed historical gutenbergpy full build on the pinned archive.

From lcats/: python ../experiments/10_gettenberg_qualification/scripts/qualify_legacy_build.py ARCHIVE NEW_DIRECTORY OUTPUT_JSON
This historical-only runner needs an environment already containing gutenbergpy;
it never installs it. Imports occur only after argument and source validation.
The archive is copied into a fresh private directory, socket access is denied,
and upstream unpack/parse/SQLite code runs unchanged (progress output suppressed).
A POSIX alarm bounds the whole run to 1,200 seconds. Original caches are read-only;
failure evidence and the isolated partial directory remain for inspection.
"""

import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import os
import pathlib
import resource
import shutil
import signal
import socket
import sqlite3
import sys
import time
from unittest import mock

EXPECTED_ARCHIVE = "358f177c30818027ad93b3478da2248d7996999475d83e59288ee74423050b28"


def digest(path):
    """Hash a file without retaining the archive or database in memory."""
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024**2), b""):
            result.update(chunk)
    return result.hexdigest()


def timeout(*_):
    """Fail rather than silently continuing beyond the historical-build budget."""
    raise TimeoutError("legacy full build exceeded 1200 seconds")


def main(argv=None):
    """Measure one isolated build; retain failure JSON and never overwrite it."""
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("archive", "directory", "output"):
        parser.add_argument(name, type=lambda value: pathlib.Path(value).resolve())
    args = parser.parse_args(argv)
    if args.output.exists() or args.directory.exists():
        parser.error("output and build directory must be new")
    if not hasattr(signal, "SIGALRM"):
        parser.error("POSIX SIGALRM required")
    result = {"qualified": False, "network_bytes": 0, "archive": str(args.archive)}
    started = time.monotonic()
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(1200)
    try:
        if args.archive.stat().st_size > 256 * 1024**2:
            raise ValueError("compressed archive exceeds bound")
        result["archive_sha256"] = digest(args.archive)
        if result["archive_sha256"] != EXPECTED_ARCHIVE:
            raise ValueError("archive differs from pinned, previously audited snapshot")
        if shutil.disk_usage(args.directory.parent).free < 6 * 1024**3:
            raise ValueError("at least 6 GiB free required")
        # The exact audited archive has only regular bounded RDF members. Never
        # invoke this old extractor on arbitrary/unverified archive contents.
        from gutenbergpy import gutenbergcache
        from gutenbergpy import gutenbergcachesettings

        package = pathlib.Path(gutenbergcache.__file__).parent
        result["upstream_version"] = importlib.metadata.version("gutenbergpy")
        result["upstream_source_sha256"] = {
            str(p.relative_to(package)): digest(p)
            for p in sorted(package.rglob("*"))
            if p.suffix in (".py", ".sql")
        }
        args.directory.mkdir()
        local_archive = args.directory / "rdf-files.tar.bz2"
        shutil.copyfile(args.archive, local_archive)
        settings = gutenbergcachesettings.GutenbergCacheSettings
        settings.set(
            CacheFilename=str(args.directory / "gutenbergindex.db"),
            CacheUnpackDir=str(args.directory / "cache/epub"),
            CacheArchiveName=str(local_archive),
        )
        build_started = time.monotonic()
        with (
            contextlib.chdir(args.directory),
            open(os.devnull, "w", encoding="utf-8") as sink,
            contextlib.redirect_stdout(sink),
            mock.patch.object(
                socket, "socket", side_effect=AssertionError("network forbidden")
            ),
        ):
            gutenbergcache.GutenbergCache.create(
                refresh=False,
                download=False,
                unpack=True,
                parse=True,
                cache=True,
                deleteTemp=False,
            )
        result["full_build_seconds"] = time.monotonic() - build_started
        db = args.directory / "gutenbergindex.db"
        with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as connection:
            result["counts"] = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("books", "titles", "downloadlinks", "aliases")
            }
            result["integrity_check"] = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
        if result["counts"]["books"] != 78937 or result["integrity_check"] != "ok":
            raise ValueError("legacy catalog count/integrity mismatch")
        result["database_bytes"] = db.stat().st_size
        result["database_sha256"] = digest(db)
        result["retained_disk_bytes"] = sum(
            p.stat().st_size for p in args.directory.rglob("*") if p.is_file()
        )
        result["scope"] = (
            "Original upstream unpack+parse+SQLite build; excludes input copy and network; retains extracted RDF. Single observation, not controlled benchmark."
        )
        result["qualified"] = True
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        signal.alarm(0)
        result["total_seconds"] = time.monotonic() - started
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result["peak_rss_bytes"] = rss if sys.platform == "darwin" else rss * 1024
        result["platform"] = sys.platform
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")


if __name__ == "__main__":
    main()
