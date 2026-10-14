"""Qualify actual offline lifecycle setup against the known cached full archive.

Usage: python qualify_lifecycle.py ARCHIVE NEW_CACHE_ROOT OUTPUT_JSON
Run with this checkout's src on PYTHONPATH. Does not download or mutate source.
"""

import argparse
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
    """Interrupt the entire probe, including library copy/build/verification."""
    raise TimeoutError("full lifecycle probe exceeded 900 seconds")


def main(argv=None):
    """Qualify the pinned snapshot and write success or failure evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("archive", "cache", "output"):
        parser.add_argument(name, type=lambda value: pathlib.Path(value).resolve())
    options = parser.parse_args(argv)
    archive, cache, output = options.archive, options.cache, options.output
    if not hasattr(signal, "SIGALRM"):
        raise RuntimeError("this bounded qualification runner requires POSIX SIGALRM")
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
    # Bound the entire experiment, not only each independently bounded operation.
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(900)
    try:
        digest, size = _lifecycle_io.hash_file(archive, 256 * 1024**2)
        if not (digest == EXPECTED_ARCHIVE):
            raise ValueError("qualification failed: digest == EXPECTED_ARCHIVE")
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
            if not (
                counts["ebooks"]
                == counts["sources"]
                == counts["archive_members"]
                == 78937
            ):
                raise ValueError(
                    "qualification failed: counts['ebooks'] == counts['sources'] == counts['archive_members'] == 78937"
                )
            if not (
                counts["resources"] == 2018879 and counts["contributions"] == 109170
            ):
                raise ValueError(
                    "qualification failed: counts['resources'] == 2018879 and counts['contributions'] == 109170"
                )
            if not (counts["diagnostics"] == 223):
                raise ValueError("qualification failed: counts['diagnostics'] == 223")
            if not (generation.manifest["archive_sha256"] == EXPECTED_ARCHIVE):
                raise ValueError(
                    "qualification failed: generation.manifest['archive_sha256'] == EXPECTED_ARCHIVE"
                )
            query_start = time.monotonic()
            with manager.open() as first, manager.open() as second:
                after, found = 0, 0
                while page := first.find_ids(after_id=after, limit=1000):
                    if not (page[0] > after):
                        raise ValueError("qualification failed: page[0] > after")
                    found += len(page)
                    after = page[-1]
                    if not (found <= 200000):
                        raise ValueError("qualification failed: found <= 200000")
                if not (found == 78937):
                    raise ValueError("qualification failed: found == 78937")
                # Real fixture round trips qualify semantics beyond aggregate totals.
                fixture_ids = []
                for fixture in sorted(
                    pathlib.Path("tests/gettenberg_tests/fixtures").glob("*.rdf")
                ):
                    expected = rdf.parse_record(
                        fixture.read_bytes(), source_name=fixture.name
                    )
                    actual = first.get(expected.ebook.gutenberg_id)
                    if not (actual.ebook == expected.ebook):
                        raise ValueError(
                            "qualification failed: actual.ebook == expected.ebook"
                        )
                    if not (actual.source.data == expected.source.data):
                        raise ValueError(
                            "qualification failed: actual.source.data == expected.source.data"
                        )
                    if not (actual.diagnostics == expected.diagnostics):
                        raise ValueError(
                            "qualification failed: actual.diagnostics == expected.diagnostics"
                        )
                    fixture_ids.append(expected.ebook.gutenberg_id)
                if not (second.get(84) == first.get(84)):
                    raise ValueError(
                        "qualification failed: second.get(84) == first.get(84)"
                    )
                result["query"] = {
                    "enumerated_ids": found,
                    "fixture_ids": fixture_ids,
                    "two_readers": "passed",
                    "seconds": time.monotonic() - query_start,
                }
                reuse_start = time.monotonic()
                reused = manager.setup(cache / "nonexistent-input")
                result["reuse_seconds"] = time.monotonic() - reuse_start
                if not (
                    reused.reused and reused.generation_id == generation.generation_id
                ):
                    raise ValueError(
                        "qualification failed: reused.reused and reused.generation_id == generation.generation_id"
                    )
                if not (manager.cleanup() == ()):
                    raise ValueError("qualification failed: manager.cleanup() == ()")
                if not (first.get(84) == second.get(84)):
                    raise ValueError(
                        "qualification failed: first.get(84) == second.get(84)"
                    )
            status = manager.status()
            if not (status["state"] == "ready" and (not status["candidates"])):
                raise ValueError(
                    "qualification failed: status['state'] == 'ready' and (not status['candidates'])"
                )
            result["status"] = {
                "state": status["state"],
                "generations": status["generations"],
                "candidates": status["candidates"],
            }
            if generation.manifest["source"]["retrieved_at"] is not None:
                raise ValueError(
                    "qualification failed: generation.manifest['source']['retrieved_at'] is None"
                )
        result["qualified"] = True
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        # Keep failure reports and platform-normalized RSS for comparison.
        signal.alarm(0)
        result["total_seconds"] = time.monotonic() - started
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result["peak_rss_bytes"] = rss if sys.platform == "darwin" else rss * 1024
        result["peak_rss_target_pass"] = result["peak_rss_bytes"] <= 512 * 1024**2
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
