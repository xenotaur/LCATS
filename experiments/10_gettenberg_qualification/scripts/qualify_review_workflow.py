"""Qualify local review on immutable cached sources, without accepting a corpus.

From lcats/ with project Python/PYTHONPATH:
python ../experiments/10_gettenberg_qualification/scripts/qualify_review_workflow.py CATALOG TEXT_CACHE COLLECTION BASELINE_CENSUS NEW_WORK_DIRECTORY NEW_OUTPUT --approvals REVIEWED_DECISIONS --annotations REVIEWED_ANNOTATIONS
Requires the recorded census and explicit prior reviews; never generates approval
from a finding pattern. Work/output must be new and outside collection roots.
Builds a reusable local candidate queue, records the supplied reviews via the CLI,
and exports only the supplied approvals. No story publication or network. <=10000
sources; gzip text <=32MiB compressed/expanded; POSIX 600s alarm; >=6GiB disk free.
Partial failure JSON is preserved and exit is nonzero. Candidate bodies stay in the
local work directory; only the compact report/annotations are archival evidence.
"""

import argparse
import collections
import dataclasses
import gzip
import hashlib
import importlib.util
import json
import pathlib
import shutil
import signal
import socket
from unittest import mock

from lcats import cli
from lcats.analysis.corpus import discovery
from lcats.gatherers import candidate_review
from lcats.gatherers import gutenberg_source
from lcats.gatherers import parser
from lcats.gatherers import readiness
from lcats.gatherers import review_store
from lcats.gettenberg import lifecycle
from lcats.gettenberg import resources


def _helpers():
    path = pathlib.Path(__file__).with_name("assess_cached_readiness.py")
    spec = importlib.util.spec_from_file_location("review_workflow_census", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.helpers


helpers = _helpers()


def run_cli(arguments):
    """Exercise actual top-level command parsing and fail on nonzero results."""
    message, code = cli.dispatch("gather-review", arguments)
    if code:
        raise ValueError(message)
    return json.loads(message)


def exercise(queue, decisions, annotations, work):
    """Replay explicit input reviews, retaining no implied or blanket dispositions."""
    paths = {}
    for path in queue.glob("*.candidate.json"):
        record = candidate_review.load_candidate(path)
        book_id = record["report"]["gutenberg_id"]
        if book_id in paths:
            raise ValueError(
                "qualification queue must have one exact generation per ID"
            )
        paths[book_id] = path
    reviewed = []
    approval_paths = []
    for book_id, decision in decisions.items():
        path = paths[book_id]
        report = candidate_review.load_candidate(path)["report"]
        explicit = readiness.ReviewDecision.for_report(
            report,
            start=decision.selected_start,
            end=decision.selected_end,
            reviewer=decision.reviewer,
            rationale=decision.rationale,
        )
        if explicit != decision:
            raise ValueError("prior explicit review does not match current candidate")
        result = run_cli(
            [
                "record",
                str(path),
                "--outcome",
                "approve",
                "--start",
                str(decision.selected_start),
                "--end",
                str(decision.selected_end),
                "--reviewer",
                decision.reviewer,
                "--rationale",
                decision.rationale,
                "--directory",
                str(work / "dispositions"),
            ]
        )
        approval_paths.append(result["disposition"])
        reviewed.append(candidate_review.load_disposition(result["disposition"]))
    seen = set(decisions)
    for annotation in annotations:
        book_id = annotation["gutenberg_id"]
        if book_id in seen or annotation["outcome"] not in {"exclude", "defer"}:
            raise ValueError("annotations require unique non-approval IDs")
        seen.add(book_id)
        path = paths[book_id]
        report = candidate_review.load_candidate(path)["report"]
        evidence = report["provenance"]["publication_readiness"]
        for key in ("source_identity_sha256", "candidate_sha256", "assessment_sha256"):
            if annotation[key] != evidence[key]:
                raise ValueError("annotation source/candidate/assessment changed")
        result = run_cli(
            [
                "record",
                str(path),
                "--outcome",
                annotation["outcome"],
                "--reviewer",
                annotation["reviewer"],
                "--rationale",
                annotation["rationale"],
                "--directory",
                str(work / "dispositions"),
            ]
        )
        reviewed.append(candidate_review.load_disposition(result["disposition"]))
    export = None
    if approval_paths:
        export = run_cli(
            [
                "export",
                *approval_paths,
                "--candidates",
                str(queue),
                "--output",
                str(work / "approvals.json"),
            ]
        )["review_decisions"]
        actual = readiness.load_decisions(export)
        if actual != decisions:
            raise ValueError("export changed existing reviewed decisions")
    inventory = run_cli(
        [
            "list",
            str(queue),
            *(["--dispositions", str(work / "dispositions")] if reviewed else []),
        ]
    )
    return {
        "inventory": inventory,
        "reviewed_records": reviewed,
        "export": export,
        "exported_decisions_equal_explicit_inputs": True,
    }


def _read_baseline(path):
    """Bound decompression of the retained census, not an arbitrary giant JSON."""
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as stream:
        data = stream.read(64 * 1024**2 + 1)
    if len(data) > 64 * 1024**2:
        raise ValueError("baseline census exceeds 64MiB")
    report = json.loads(data)
    if report.get("completed") is not True:
        raise ValueError("baseline census is incomplete")
    return report


def timeout(*_):
    raise TimeoutError("review workflow qualification exceeded 600 seconds")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("catalog", "text_cache", "collection", "baseline", "work", "output"):
        ap.add_argument(name, type=lambda v: pathlib.Path(v).resolve())
    ap.add_argument("--approvals", type=pathlib.Path, required=True)
    ap.add_argument("--annotations", type=pathlib.Path, required=True)
    args = ap.parse_args(argv)
    if args.work.exists() or args.output.exists():
        ap.error("work and output must be new")
    if not hasattr(signal, "SIGALRM"):
        ap.error("POSIX SIGALRM required")
    review_store.working_root(args.work, data_root=args.collection)
    review_store.working_root(args.output.parent, data_root=args.collection)
    if shutil.disk_usage(args.work.parent).free < 6 * 1024**3:
        ap.error("less than 6GiB free")
    result = {"completed": False, "network_bytes": 0, "rows": [], "scope": __doc__}
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(600)
    try:
        baseline = _read_baseline(args.baseline)
        prior = {row["id"]: row for row in baseline["rows"]}
        paths = sorted(discovery.iter_collection_story_files(args.collection))
        if not 0 < len(paths) <= 10000 or len(paths) != len(prior):
            raise ValueError("source selection does not match bounded baseline census")
        decisions = readiness.load_decisions(args.approvals)
        annotations = json.loads(args.annotations.read_text(encoding="utf-8"))
        if not isinstance(annotations, list) or len(annotations) > 100:
            raise ValueError(
                "annotations must be a list of at most 100 reviewed records"
            )
        args.work.mkdir()
        queue = args.work / "candidates"
        queue.mkdir()
        result["source_sha256"] = {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(pathlib.Path("src/lcats").rglob("*.py"))
        }
        result["runner_sha256"] = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(pathlib.Path(__file__).parent.glob("*.py"))
        }
        result["input_sha256"] = {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (args.baseline, args.approvals, args.annotations)
        }
        with lifecycle.CatalogManager(
            args.catalog
        ).open() as catalog, mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ):
            source = gutenberg_source.GutenbergStorySource(
                catalog,
                resources.ResourceStore(args.catalog),
                routes=resources.GutenbergRoutes(
                    "https://www.gutenberg.org/files/",
                    "https://www.gutenberg.org/cache/epub/",
                ),
            )
            for path in paths:
                raw = path.read_bytes()
                saved = json.loads(raw)
                book_id = helpers.corpus.identifiers.ebook_id_from_url(
                    saved["metadata"]["url"]
                )
                text, compressed, decoded = helpers.corpus.cached_text(
                    args.text_cache, book_id
                )
                before = prior[book_id]
                if (
                    before["corpus_sha256"] != hashlib.sha256(raw).hexdigest()
                    or before["compressed_sha256"] != compressed
                    or before["decoded_utf8_sha256"] != decoded
                ):
                    raise ValueError("immutable source/corpus identity changed")
                cleaned = helpers.cleanup.strip_boilerplate(text)
                row = {
                    "id": book_id,
                    "corpus_sha256": before["corpus_sha256"],
                    "compressed_sha256": compressed,
                    "decoded_utf8_sha256": decoded,
                }
                if not cleaned.changed and any(
                    d.code != "no_markers" for d in cleaned.diagnostics
                ):
                    row["status"] = "cleanup_refused"
                else:
                    replay = helpers.HistoricalSource(
                        source,
                        helpers.HistoricalText(book_id, cleaned, compressed, decoded),
                    )
                    report = parser.inspect_story(book_id, source=replay)
                    row["status"] = report["status"]
                    if report["provenance"] != before.get("provenance"):
                        raise ValueError("candidate derivation differs from baseline")
                    if report["status"] == "needs_review":
                        candidate = review_store.save(
                            report, directory=queue, data_root=args.collection
                        )
                        row["candidate_record_sha256"] = readiness.identity(
                            candidate_review.load_candidate(candidate)
                        )
                if row["status"] != before["status"]:
                    raise ValueError("readiness changed from baseline")
                result["rows"].append(row)
            result.update(exercise(queue, decisions, annotations, args.work))
        result["source_counts"] = dict(
            collections.Counter(r["status"] for r in result["rows"])
        )
        result["stories_published"] = 0
        if list(args.work.rglob("story.json")):
            raise ValueError("unexpected story publication")
        result["completed"] = True
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        signal.alarm(0)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")


if __name__ == "__main__":
    main()
