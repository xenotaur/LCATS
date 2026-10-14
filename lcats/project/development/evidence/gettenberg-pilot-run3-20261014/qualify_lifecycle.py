"""Qualify actual offline lifecycle setup against the known cached full archive.

Usage: python qualify_lifecycle.py ARCHIVE NEW_CACHE_ROOT OUTPUT_JSON
Run with this checkout's src on PYTHONPATH. Does not download or mutate source.
"""

import dataclasses
import hashlib
import json
import pathlib
import resource
import shutil
import signal
import socket
import subprocess
import sys
import time
from unittest import mock

from lcats.gettenberg import _lifecycle_io
from lcats.gettenberg import ingestion
from lcats.gettenberg import lifecycle
from lcats.gettenberg import rdf

EXPECTED_ARCHIVE = "358f177c30818027ad93b3478da2248d7996999475d83e59288ee74423050b28"


def timeout(*_):
    raise TimeoutError("full lifecycle probe exceeded 900 seconds")


def main():
    archive, cache, output = map(pathlib.Path, sys.argv[1:])
    if cache.exists():
        raise ValueError("qualification requires a new private cache root")
    if shutil.disk_usage(cache.parent).free < 6 * 1024**3:
        raise ValueError("qualification needs at least 6 GiB free space")
    started = time.monotonic()
    result = {
        "candidate_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "source_sha256": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(pathlib.Path("src/lcats/gettenberg").glob("*.py"))
        },
        "archive_path": str(archive),
        "cache_root": str(cache),
        "limits": dataclasses.asdict(ingestion.BuildLimits()),
        "network_bytes": 0,
        "qualified": False,
        "scope": "One real local lifecycle setup, activation, reuse and read qualification; remote acquisition/caller migration remain outside scope.",
    }
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(900)
    try:
        digest, size = _lifecycle_io.hash_file(archive, 256 * 1024**2)
        assert digest == EXPECTED_ARCHIVE
        result["archive_bytes"] = size
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ):
            manager = lifecycle.CatalogManager(cache)
            build_start = time.monotonic()
            generation = manager.setup(archive)
            result["setup_seconds"] = time.monotonic() - build_start
            result["manifest"] = generation.manifest
            result["generation_id"] = generation.generation_id
            counts = generation.manifest["counts"]
            assert (
                counts["ebooks"]
                == counts["sources"]
                == counts["archive_members"]
                == 78937
            )
            assert counts["resources"] == 2018879 and counts["contributions"] == 109170
            assert counts["diagnostics"] == 223
            assert generation.manifest["archive_sha256"] == EXPECTED_ARCHIVE
            query_start = time.monotonic()
            with manager.open() as first, manager.open() as second:
                after, found = 0, 0
                while page := first.find_ids(after_id=after, limit=1000):
                    assert page[0] > after
                    found += len(page)
                    after = page[-1]
                    assert found <= 200000
                assert found == 78937
                fixture_ids = []
                for fixture in sorted(
                    pathlib.Path("tests/gettenberg_tests/fixtures").glob("*.rdf")
                ):
                    expected = rdf.parse_record(
                        fixture.read_bytes(), source_name=fixture.name
                    )
                    actual = first.get(expected.ebook.gutenberg_id)
                    assert actual.ebook == expected.ebook
                    assert actual.source.data == expected.source.data
                    assert actual.diagnostics == expected.diagnostics
                    fixture_ids.append(expected.ebook.gutenberg_id)
                assert second.get(84) == first.get(84)
                result["query"] = {
                    "enumerated_ids": found,
                    "fixture_ids": fixture_ids,
                    "two_readers": "passed",
                    "seconds": time.monotonic() - query_start,
                }
                reuse_start = time.monotonic()
                reused = manager.setup(cache / "nonexistent-input")
                result["reuse_seconds"] = time.monotonic() - reuse_start
                assert (
                    reused.reused and reused.generation_id == generation.generation_id
                )
                assert manager.cleanup() == ()
                assert first.get(84) == second.get(84)
            status = manager.status()
            assert status["state"] == "ready" and not status["candidates"]
            result["status"] = {
                "state": status["state"],
                "generations": status["generations"],
                "candidates": status["candidates"],
            }
            assert generation.manifest["source"]["retrieved_at"] is None
        result["qualified"] = True
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        signal.alarm(0)
        result["total_seconds"] = time.monotonic() - started
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result["peak_rss_bytes"] = rss if sys.platform == "darwin" else rss * 1024
        result["peak_rss_target_pass"] = result["peak_rss_bytes"] <= 512 * 1024**2
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
