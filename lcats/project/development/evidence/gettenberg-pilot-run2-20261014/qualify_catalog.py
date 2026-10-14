"""Bounded full cached-source qualification; run from the lcats/ root.

Arguments: archive, new private candidate path, output evidence JSON path.
The library enforces build limits. This helper adds no acquisition/activation.
"""

import dataclasses
import hashlib
import json
import pathlib
import resource
import sqlite3
import subprocess
import sys
import time

from lcats.gettenberg import catalog
from lcats.gettenberg import errors
from lcats.gettenberg import ingestion
from lcats.gettenberg import rdf

archive, candidate, evidence_path = map(pathlib.Path, sys.argv[1:])
start = time.monotonic()
evidence = {
    "candidate_head": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip(),
    "source_sha256": {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in pathlib.Path("src/lcats/gettenberg").glob("*.py")
    },
    "archive_path": str(archive),
    "limits": dataclasses.asdict(ingestion.BuildLimits()),
    "network_bytes": 0,
    "scope": "Local candidate build/query qualification only; no activation, remote lifecycle or corpus migration.",
}
try:
    report = ingestion.build_catalog(archive, candidate)
    evidence["build"] = dataclasses.asdict(report)
    if (
        report.archive_sha256
        != "358f177c30818027ad93b3478da2248d7996999475d83e59288ee74423050b28"
    ):
        raise ValueError("input differs from the recorded baseline snapshot")
    if report.imported != 78937 or report.rejected or report.uncommitted:
        raise ValueError("source record accounting differs from baseline")
    query_start = time.monotonic()
    with sqlite3.connect(candidate.as_uri() + "?mode=ro", uri=True) as connection:
        evidence["normalized_counts"] = {
            table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in (
                "ebooks",
                "sources",
                "titles",
                "agents",
                "contributions",
                "resources",
                "formats",
                "languages",
                "subjects",
                "shelves",
                "diagnostics",
            )
        }
    if (
        evidence["normalized_counts"]["resources"] != 2018879
        or evidence["normalized_counts"]["contributions"] != 109170
    ):
        raise ValueError(
            "resource/contribution accounting differs from parser baseline"
        )
    with catalog.Catalog(candidate) as library:
        all_ids, after = [], 0
        while page := library.find_ids(after_id=after, limit=1000):
            if page != tuple(sorted(set(page))) or page[0] <= after:
                raise ValueError("pagination is not monotonic and unique")
            all_ids.extend(page)
            after = page[-1]
            if len(all_ids) > 200000 or time.monotonic() - query_start > 120:
                raise ValueError("query qualification bound exceeded")
        if len(all_ids) != report.imported:
            raise ValueError("pagination does not enumerate every record")
        checked = []
        for path in sorted(
            pathlib.Path("tests/gettenberg_tests/fixtures").glob("*.rdf")
        ):
            identifier = int(path.stem.removeprefix("pg"))
            actual = library.get(identifier)
            expected = rdf.parse_record(
                path.read_bytes(), source_name=actual.source.source_name
            )
            if actual != expected:
                raise ValueError(f"fixture round trip differs: {identifier}")
            for title in actual.ebook.titles:
                if identifier not in library.find_ids(
                    catalog.Filters(ids=(identifier,), titles=(title.value.text,))
                ):
                    raise ValueError("exact title filter lost an association")
            for contribution in actual.ebook.contributors:
                for alias in contribution.agent.aliases:
                    if identifier not in library.find_ids(
                        catalog.Filters(ids=(identifier,), authors=(alias.text,))
                    ):
                        raise ValueError("alias filter lost an association")
            checked.append(identifier)
        batch = library.get_many([84, 999999999, 84])
        if [x.ebook.gutenberg_id if x else None for x in batch] != [84, None, 84]:
            raise ValueError("batch missing/duplicate semantics failed")
        evidence["query"] = {
            "enumerated_ids": len(all_ids),
            "fixture_round_trips": checked,
            "batch_missing_duplicates": "passed",
            "seconds": time.monotonic() - query_start,
        }
    evidence["qualified"] = True
except Exception as exc:
    evidence["qualified"] = False
    evidence["failure"] = f"{type(exc).__name__}: {exc}"
    if isinstance(exc, errors.CatalogBuildError) and exc.report is not None:
        evidence["build"] = dataclasses.asdict(exc.report)
    raise
finally:
    evidence["total_seconds"] = time.monotonic() - start
    evidence["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    evidence["rss_units"] = "macOS ru_maxrss bytes"
    evidence["peak_rss_target_pass"] = evidence["peak_rss_bytes"] <= 512 * 1024**2
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
