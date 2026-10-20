"""Verify explicit review evidence and account for a bounded corpus tranche.

From lcats/ with project Python/PYTHONPATH:
python ../experiments/10_gettenberg_qualification/scripts/reconcile_review_tranche.py CENSUS COMPARISON REVIEWS QUEUE DISPOSITIONS TEXT_CACHE COLLECTION NEW_OUTPUT
Inputs are immutable local files; no catalog, downloads or story publication.
REVIEWS is an explicit list of <=100 reviewed IDs, named disposition basenames,
source anchors (Unicode offsets/text), review scope and historical rationale.
This verifies evidence identity, not literary judgment or human authorship.
Only approve/exclude count as disposition-covered; defer remains unresolved.
Coverage is limited to this named tranche, never extrapolated to the population.
Evidence JSON <=64MiB expanded, sources <=32MiB, <=10000 population rows;
POSIX 180s alarm. Nonzero failure preserves completed:false evidence. Existing
output is refused. Product artifact loaders verify candidate/disposition identity.
"""

import argparse
import collections
import hashlib
import importlib.util
import json
import pathlib
import signal
import socket
from unittest import mock

from lcats.gatherers import candidate_review
from lcats.gatherers import readiness
from lcats.gatherers import review_store


def _helpers():
    """Reuse bounded historical-source readers without importing legacy packages."""
    path = pathlib.Path(__file__).with_name("qualify_review_workflow.py")
    spec = importlib.util.spec_from_file_location("tranche_workflow", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


workflow = _helpers()


def indexed_rows(report):
    """Reject partial or duplicate populations before deriving coverage counts."""
    if report.get("completed") is not True:
        raise ValueError("population evidence incomplete")
    rows = report.get("rows")
    if not isinstance(rows, list) or not 0 < len(rows) <= 10000:
        raise ValueError("population requires 1–10000 rows")
    result = {}
    for row in rows:
        identifier = row["id"]
        if type(identifier) is not int or identifier <= 0 or identifier in result:
            raise ValueError("population requires unique positive IDs")
        result[identifier] = row
    return result


def verify_anchors(text, anchors):
    """Check exact source excerpts; a matching excerpt is not narrative approval."""
    if not isinstance(anchors, list) or not 1 <= len(anchors) <= 50:
        raise ValueError("requires 1–50 explicit source anchors")
    for anchor in anchors:
        start, end = anchor["start"], anchor["end"]
        if (
            type(start) is not int
            or type(end) is not int
            or not 0 <= start < end <= len(text)
            or end - start > 4000
            or text[start:end] != anchor["text"]
        ):
            raise ValueError("source anchor differs or is out of bounds")


def named_file(root, name):
    """An evidence reference names a file inside its supplied root, never a path."""
    if (
        not isinstance(name, str)
        or pathlib.Path(name).name != name
        or name in {"", ".", ".."}
    ):
        raise ValueError("artifact reference must be a basename")
    return root / name


def validated_population(census, comparison):
    """Check complete population accounting before any tranche or batch analysis."""
    baseline, historical = indexed_rows(census), indexed_rows(comparison)
    if baseline.keys() != historical.keys():
        raise ValueError("population ID sets differ")
    # Validate EVERY row: omitted comparison fields must not become "unchanged".
    for identifier, row in historical.items():
        before = baseline[identifier]
        status = row.get("status")
        if "body_equal" not in row or status not in {"compared", "cleanup_refused"}:
            raise ValueError("invalid historical comparison status/body_equal")
        if (status == "compared" and type(row["body_equal"]) is not bool) or (
            status == "cleanup_refused" and row["body_equal"] is not None
        ):
            raise ValueError("invalid historical body_equal type")
        if status == "compared":
            digests = [
                row.get(key)
                for key in ("normalized_before_sha256", "normalized_after_sha256")
            ]
            if any(
                not isinstance(d, str)
                or len(d) != 64
                or any(c not in "0123456789abcdef" for c in d)
                for d in digests
            ):
                raise ValueError("invalid normalized comparison digest")
            if row["body_equal"] != (digests[0] == digests[1]):
                raise ValueError("historical equality flag differs from body hashes")
        if (status == "cleanup_refused") != (before["status"] == "cleanup_refused"):
            raise ValueError("population cleanup status differs")
        for old_key, baseline_key in (
            ("corpus_sha256", "corpus_sha256"),
            ("cache_sha256", "compressed_sha256"),
            ("decoded_utf8_sha256", "decoded_utf8_sha256"),
        ):
            if row[old_key] != before[baseline_key]:
                raise ValueError("population source/corpus identity differs")
    changed_count = sum(row["body_equal"] is False for row in historical.values())
    if "body_differences" in comparison and (
        type(comparison["body_differences"]) is not int
        or comparison["body_differences"] != changed_count
    ):
        raise ValueError("historical changed-body total differs")
    if "summary" in comparison and comparison["summary"] != dict(
        collections.Counter(row["status"] for row in historical.values())
    ):
        raise ValueError("historical comparison summary differs")
    return baseline, historical


def reconcile(census, comparison, reviews, queue, dispositions, text_cache, collection):
    """Bind each explicit disposition to source/corpus evidence and return coverage."""
    baseline, historical = validated_population(census, comparison)
    if not isinstance(reviews, list) or not 1 <= len(reviews) <= 100:
        raise ValueError("requires 1–100 explicit reviews")
    seen, rows = set(), []
    for review in reviews:
        identifier = review["id"]
        if (
            type(identifier) is not int
            or identifier in seen
            or identifier not in baseline
        ):
            raise ValueError("review IDs must be unique and in population")
        seen.add(identifier)
        for key in ("review_scope", "historical_rationale"):
            if not isinstance(review[key], str) or not review[key].strip():
                raise ValueError("review scope and historical rationale required")
        before, old = baseline[identifier], historical[identifier]
        record = candidate_review.load_candidate(named_file(queue, review["candidate"]))
        report = record["report"]
        disposition = candidate_review.load_disposition(
            named_file(dispositions, review["disposition"])
        )
        if (
            report["gutenberg_id"] != identifier
            or disposition["gutenberg_id"] != identifier
            or disposition["candidate_record_sha256"] != readiness.identity(record)
            or report["provenance"] != before["provenance"]
            or old["new_extracted_sha256"] != readiness.text_sha256(report["body"])
        ):
            raise ValueError("candidate/disposition/population identity differs")
        cached = workflow.helpers.corpus.cached_text(text_cache, identifier)
        if cached is None:
            raise ValueError("source missing")
        text, compressed, decoded = cached
        if (
            compressed != before["compressed_sha256"]
            or compressed != old["cache_sha256"]
            or decoded != before["decoded_utf8_sha256"]
            or decoded != old["decoded_utf8_sha256"]
        ):
            raise ValueError("historical source identity differs")
        corpus_path = named_file(collection, before["path"]) / "story.json"
        raw = corpus_path.read_bytes()
        if (
            hashlib.sha256(raw).hexdigest() != before["corpus_sha256"]
            or before["corpus_sha256"] != old["corpus_sha256"]
        ):
            raise ValueError("canonical corpus identity differs")
        verify_anchors(text, review["source_anchors"])
        # Approvals must validate against this exact report, not just match a
        # candidate-record digest. Exclude/defer cannot carry an approval payload.
        approval = disposition["approval"]
        selected = None
        if disposition["outcome"] == "approve":
            decision = readiness.ReviewDecision(**approval)
            selected = readiness.ReviewDecision.for_report(
                report,
                start=decision.selected_start,
                end=decision.selected_end,
                reviewer=decision.reviewer,
                rationale=decision.rationale,
            )
            if decision != selected:
                raise ValueError("approval differs from exact candidate")
        selected_text = (
            None
            if approval is None
            else report["body"][decision.selected_start : decision.selected_end]
        )
        retained = json.loads(raw)["body"]
        retained_suffix = None
        if selected_text is not None and retained.startswith(selected_text):
            suffix = retained[len(selected_text) :]
            retained_suffix = {
                "characters": len(suffix),
                "sha256": readiness.text_sha256(suffix),
                "text": suffix if len(suffix) <= 200 else None,
            }
        rows.append(
            {
                "id": identifier,
                "outcome": disposition["outcome"],
                "candidate_record_sha256": readiness.identity(record),
                "disposition_sha256": readiness.identity(disposition),
                "compressed_sha256": compressed,
                "decoded_utf8_sha256": decoded,
                "corpus_sha256": before["corpus_sha256"],
                "historical_body_changed": old["body_equal"] is False,
                "legacy_matches_retained": old["legacy_matches_retained"],
                "old_body_characters": old["old_body_characters"],
                "candidate_characters": len(report["body"]),
                "selected_span": (
                    None
                    if approval is None
                    else [approval["selected_start"], approval["selected_end"]]
                ),
                "review_scope": review["review_scope"],
                "historical_rationale": review["historical_rationale"],
                "anchors_verified": len(review["source_anchors"]),
                "approval_verified": selected is not None,
                "retained_suffix_after_exact_selected_prefix": retained_suffix,
            }
        )
    changed = {i for i, row in historical.items() if row["body_equal"] is False}
    covered = {row["id"] for row in rows if row["outcome"] in {"approve", "exclude"}}
    return {
        "rows": rows,
        "population_ids": sorted(baseline),
        "historical_changed_ids": sorted(changed),
        "tranche_reviewed_ids": sorted(seen),
        "tranche_disposition_covered_changed_ids": sorted(changed & covered),
        "historical_changed_ids_not_covered_by_tranche": sorted(changed - covered),
        "deferred_ids": sorted(row["id"] for row in rows if row["outcome"] == "defer"),
        "corpus_accepted": False,
    }


def timeout(*_):
    raise TimeoutError("tranche reconciliation exceeded 180 seconds")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    for name in (
        "census",
        "comparison",
        "reviews",
        "queue",
        "dispositions",
        "text_cache",
        "collection",
        "output",
    ):
        ap.add_argument(name, type=lambda value: pathlib.Path(value).resolve())
    args = ap.parse_args(argv)
    if args.output.exists():
        ap.error("output exists")
    review_store.working_root(args.output.parent, data_root=args.collection)
    if not hasattr(signal, "SIGALRM"):
        ap.error("POSIX SIGALRM required")
    result = {"completed": False, "network_bytes": 0, "scope": __doc__}
    previous = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(180)
    try:
        inputs = [args.census, args.comparison, args.reviews]
        reports = [workflow._read_json(path, 64 * 1024**2) for path in inputs]
        result["input_sha256"] = {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs
        }
        result["runner_sha256"] = hashlib.sha256(
            pathlib.Path(__file__).read_bytes()
        ).hexdigest()
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ):
            result.update(
                reconcile(
                    *reports,
                    args.queue,
                    args.dispositions,
                    args.text_cache,
                    args.collection,
                )
            )
        result["completed"] = True
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")


if __name__ == "__main__":
    main()
