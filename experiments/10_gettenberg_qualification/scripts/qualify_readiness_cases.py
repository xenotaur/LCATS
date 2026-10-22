"""Exercise real readiness outcomes and isolated publication for reviewed cases.

From lcats/: python ../experiments/10_gettenberg_qualification/scripts/qualify_readiness_cases.py CATALOG_CACHE TEXT_CACHE CASES_JSON OUTPUT_JSON [--review-decisions DECISIONS_JSON]
Read-only historical decoded UTF-8 gzip inputs, never original wire-byte evidence.
No network; accepted/review outputs live in an automatically removed temporary
root outside canonical data. Cases bind decoded hashes and expected raw statuses;
optional source-bound decisions independently resolve selected review cases.
Requires POSIX SIGALRM, <=100 cases, 180-second total bound, new output path.
Any identity/outcome/preservation mismatch fails nonzero with partial JSON evidence.
"""

import argparse
import contextlib
import importlib.util
import io
import json
import pathlib
import signal
import socket
import tempfile
from unittest import mock

from lcats.gatherers import downloaders
from lcats.gatherers import parser
from lcats.gatherers import readiness
from lcats.gettenberg import lifecycle
from lcats.gettenberg import resources
from lcats.gatherers import gutenberg_source


def _helpers():
    path = pathlib.Path(__file__).with_name("assess_cached_readiness.py")
    spec = importlib.util.spec_from_file_location("readiness_census_helpers", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.helpers


helpers = _helpers()


def check_case(case, text_cache, source, root, *, decision=None):
    """Verify raw classification, full candidate persistence and final outcome."""
    cached = helpers.corpus.cached_text(text_cache, case["id"])
    if cached is None:
        raise ValueError("case input missing")
    text, compressed_sha, decoded_sha = cached
    if decoded_sha != case["decoded_utf8_sha256"]:
        raise ValueError("case source identity changed")
    cleaned = helpers.cleanup.strip_boilerplate(text)
    if not cleaned.changed and any(d.code != "no_markers" for d in cleaned.diagnostics):
        raise ValueError("case cleanup refused")
    replay = helpers.HistoricalSource(
        source, helpers.HistoricalText(case["id"], cleaned, compressed_sha, decoded_sha)
    )
    raw_report = parser.inspect_story(case["id"], source=replay)
    if raw_report["status"] != case["expected_status"]:
        raise ValueError(
            f"raw readiness differs for {case['id']}: {raw_report['status']}"
        )
    gatherer = downloaders.DataGatherer("mass_quantities", root=root / "data")
    outcome = parser.gather_story(
        gatherer,
        case["id"],
        source=replay,
        review_decision=decision,
        review_dir=root / "review",
    )
    expected = (
        "published"
        if decision or case["expected_status"] == "ready"
        else case["expected_status"]
    )
    if outcome.status != expected:
        raise ValueError(
            f"publication outcome differs for {case['id']}: {outcome.status}"
        )
    row = {
        "id": case["id"],
        "decoded_utf8_sha256": decoded_sha,
        "compressed_sha256": compressed_sha,
        "raw_status": raw_report["status"],
        "outcome": outcome.status,
        "candidate_sha256": readiness.text_sha256(raw_report["body"]),
        "review_candidate_preserved": None,
        "published_sha256": None,
        "existing_output_unchanged": None,
    }
    if outcome.status == "needs_review":
        stored = json.loads(
            pathlib.Path(outcome.review_path).read_text(encoding="utf-8")
        )
        if stored["report"] != raw_report or outcome.path is not None:
            raise ValueError("review candidate differs or was published")
        row["review_candidate_preserved"] = True
    elif outcome.status == "published":
        path = pathlib.Path(outcome.path)
        saved = path.read_bytes()
        row["published_sha256"] = helpers.corpus.digest(saved)
        inspected = parser.inspect_story(
            case["id"], source=replay, review_decision=decision
        )
        # Compare the complete canonical JSON value: v2 retained spans are
        # tuples in memory and arrays after writing, with identical JSON meaning.
        if readiness.identity(
            json.loads(saved)["metadata"]["gettenberg"]
        ) != readiness.identity(inspected["provenance"]):
            raise ValueError("published source/review provenance differs")
        reused = parser.gather_story(gatherer, case["id"], source=replay)
        if reused.status != "reused" or path.read_bytes() != saved:
            raise ValueError("published output was not preserved on reuse")
        row["existing_output_unchanged"] = True
    return row


def timeout(*_):
    raise TimeoutError("readiness case checks exceeded 180 seconds")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("catalog_cache", "text_cache", "cases", "output"):
        ap.add_argument(name, type=lambda v: pathlib.Path(v).resolve())
    ap.add_argument("--review-decisions", type=pathlib.Path)
    args = ap.parse_args(argv)
    if args.output.exists():
        ap.error("output exists")
    if not hasattr(signal, "SIGALRM"):
        ap.error("POSIX SIGALRM required")
    result = {"completed": False, "network_bytes": 0, "cases": [], "scope": __doc__}
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(180)
    try:
        raw = args.cases.read_bytes()
        cases = json.loads(raw)["cases"]
        if not 0 < len(cases) <= 100 or len({case["id"] for case in cases}) != len(
            cases
        ):
            raise ValueError("requires 1–100 unique cases")
        if any(
            case["expected_status"] not in {"ready", "needs_review", "ineligible"}
            for case in cases
        ):
            raise ValueError("invalid expected case status")
        decisions = (
            readiness.load_decisions(args.review_decisions)
            if args.review_decisions
            else {}
        )
        if set(decisions) - {case["id"] for case in cases}:
            raise ValueError("unselected review decision IDs")
        result["cases_sha256"] = helpers.corpus.digest(raw)
        result["review_decisions_sha256"] = (
            helpers.corpus.digest(args.review_decisions.read_bytes())
            if args.review_decisions
            else None
        )
        result["source_sha256"] = {
            str(p): helpers.corpus.digest(p.read_bytes())
            for p in sorted(pathlib.Path("src/lcats").rglob("*.py"))
        }
        result["runner_sha256"] = {
            p.name: helpers.corpus.digest(p.read_bytes())
            for p in pathlib.Path(__file__).parent.glob("*.py")
        }
        with lifecycle.CatalogManager(
            args.catalog_cache
        ).open() as cat, tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ), contextlib.redirect_stdout(
            io.StringIO()
        ):
            source = gutenberg_source.GutenbergStorySource(
                cat,
                resources.ResourceStore(args.catalog_cache),
                routes=resources.GutenbergRoutes(
                    "https://www.gutenberg.org/files/",
                    "https://www.gutenberg.org/cache/epub/",
                ),
            )
            result["catalog_archive_sha256"] = cat.info["report"]["archive_sha256"]
            for case in cases:
                result["cases"].append(
                    check_case(
                        case,
                        args.text_cache,
                        source,
                        pathlib.Path(temporary),
                        decision=decisions.get(case["id"]),
                    )
                )
        result["completed"] = True
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        signal.alarm(0)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
