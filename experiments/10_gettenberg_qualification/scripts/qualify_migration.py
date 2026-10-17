"""Compare gathering before/after the caller migration using authored fixtures.

From lcats/: python ../experiments/10_gettenberg_qualification/scripts/qualify_migration.py OUTPUT_JSON
Requires the source checkout, its tests, Git and the LCATS development environment.
The pinned integration-base parser is read from Git and loaded in a temporary
module; it uses the same explicit new source as the current parser, so no old
package is installed. All catalog, cache and output files are temporary. Network
is blocked except for the test fixture's in-memory HTTP transport. No existing
corpus/cache is read or changed. An unsupported baseline or any output difference
fails nonzero after saving evidence; archived results are never overwritten.

This qualifies extraction/consumer preservation, not a full corpus or live source.
"""

import argparse
import hashlib
import importlib.util
import json
import pathlib
import socket
import subprocess
import sys
import tempfile
from unittest import mock

from lcats.analysis.corpus import reconciliation
from lcats.gatherers import downloaders
from lcats.gatherers import parser
from lcats.gettenberg import resources

BASE = "003c2e08523c9360fdda3a2bfd69b42505c4c51f"
BASE_PATH = "lcats/src/lcats/gatherers/parser.py"


def compare_case(baseline, body, fixtures):
    """Run both parsers with identical immutable inputs in separate outputs."""
    fixture = fixtures.LiveGatherTests()
    fixture.setUp()
    try:
        source, artifact = fixture.acquire(body)
        source.policy = resources.NetworkPolicy()
        results = []
        payloads = []
        for name, module in (("before", baseline), ("after", parser)):
            gatherer = downloaders.DataGatherer(
                "mass_quantities", root=fixture.root / name
            )
            pathlib.Path(gatherer.path).mkdir(parents=True)
            result = module.gather_story(gatherer, fixtures.BOOK_ID, source=source)
            results.append({"id": result[0], "rejection": result[2]})
            payloads.append(
                None
                if result[1] is None
                else json.loads(pathlib.Path(result[1]).read_text())
            )
        comparisons = reconciliation.compare_collections(
            fixture.root / "before/mass_quantities",
            fixture.root / "after/mass_quantities",
        )
        return {
            "original_sha256": artifact.sha256,
            "same_result": results[0] == results[1],
            "same_story_json": payloads[0] == payloads[1],
            "results": results,
            "comparison": comparisons,
        }
    finally:
        fixture.doCleanups()


def main(argv=None):
    """Save exact-source and fixture comparison evidence, refusing overwrites."""
    args_parser = argparse.ArgumentParser(description=__doc__)
    args_parser.add_argument("output", type=pathlib.Path)
    args = args_parser.parse_args(argv)
    output = args.output.resolve()
    if output.exists():
        args_parser.error("output exists; choose a fresh path")
    # Fixture builders are source-checkout test support, never wheel contents.
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lcats"))
    from tests.gatherers_tests import live_gather_test as fixtures

    baseline_bytes = subprocess.check_output(["git", "show", f"{BASE}:{BASE_PATH}"])
    cases = {
        "lf": fixtures.ENVELOPE.encode(),
        "crlf": fixtures.ENVELOPE.replace("\n", "\r\n").encode(),
        "cr": fixtures.ENVELOPE.replace("\n", "\r").encode(),
        "short": b"The Bell\n\nJohn Smith\n\nA short story.",
        "chapters": (
            "The Bell\n\nJohn Smith\n\nChapter I\n\n"
            + fixtures.BODY
            + "\n\nChapter II\n\n"
            + fixtures.BODY
        ).encode(),
    }
    with tempfile.TemporaryDirectory() as directory:
        module_path = pathlib.Path(directory) / "baseline_parser.py"
        module_path.write_bytes(baseline_bytes)
        spec = importlib.util.spec_from_file_location("baseline_parser", module_path)
        baseline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(baseline)
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ):
            results = {
                name: compare_case(baseline, body, fixtures)
                for name, body in cases.items()
            }
    qualified = all(r["same_result"] and r["same_story_json"] for r in results.values())
    evidence = {
        "baseline_commit": BASE,
        "baseline_parser_sha256": hashlib.sha256(baseline_bytes).hexdigest(),
        "current_parser_sha256": hashlib.sha256(
            pathlib.Path(parser.__file__).read_bytes()
        ).hexdigest(),
        "fixture_source_sha256": hashlib.sha256(
            pathlib.Path(fixtures.__file__).read_bytes()
        ).hexdigest(),
        "scope": "authored fixtures, explicit-source pre-migration vs current parser; not a full corpus",
        "network_requests": 0,
        "qualified": qualified,
        "cases": results,
    }
    with output.open("x", encoding="utf-8") as stream:
        json.dump(evidence, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"qualified": qualified, "cases": len(results)}))
    return 0 if qualified else 1


if __name__ == "__main__":
    raise SystemExit(main())
