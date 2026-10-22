"""Measure explicitly reviewed promotional spans without approving stories.

From lcats/ with project Python/PYTHONPATH: python ../experiments/10_gettenberg_qualification/scripts/qualify_editorial_evidence.py CENSUS COMPARISON QUEUE DISPOSITIONS TEXT_CACHE COLLECTION PRIOR_REVIEWS SPAN_REVIEWS NEW_OUTPUT
Reuses full-population batch validation and cumulative intent; SPAN_REVIEWS is a
finite attributed catalogue, not inferred labels. Outputs summary and compressed
ledger with partial-role proofs and hypothetical composed selections. No recording,
export, source download or story publication. <=10,000 inputs, <=256 span reviews,
existing bounded artifact/cache readers, POSIX 600s alarm, >=6GiB free. Exclusive
output cannot be inside an input directory. Failures remain completed:false.
"""

import argparse
import collections
import hashlib
import importlib.util
import json
import pathlib
import shutil
import signal
import socket
import time
from unittest import mock

from lcats.gatherers import candidate_review
from lcats.gatherers import editorial_evidence
from lcats.gatherers import historical_review
from lcats.gatherers import readiness
from lcats.gatherers import review_rules


def _batch():
    """Share population, historical-source and immutable-intent verification."""
    path = pathlib.Path(__file__).with_name("qualify_review_batch.py")
    spec = importlib.util.spec_from_file_location("editorial_batch", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


batch = _batch()


def evaluate(
    census, comparison, queue, dispositions, cache, collection, prior, reviews
):
    """Return a verified population with separate non-authoritative span proposals."""
    if not isinstance(reviews, list) or len(reviews) > 256:
        raise ValueError("span reviews must be an explicit list of at most 256")
    reviewed = {}
    for review in reviews:
        if not isinstance(review, dict) or type(review.get("gutenberg_id")) is not int:
            raise ValueError("invalid reviewed catalogue entry")
        identifier = review["gutenberg_id"]
        key = (identifier, str(review.get("candidate_span")))
        if key in reviewed:
            raise ValueError("duplicate reviewed catalogue span")
        reviewed[key] = review
    rows, _, inventory = batch.evaluate(
        census,
        comparison,
        queue,
        dispositions,
        cache,
        collection,
        prior,
        dispositions,
        rule="terminal",
        historical_acceptance="source-grounded",
    )
    known = {row["id"] for row in rows if "candidate_record_sha256" in row}
    if any(key[0] not in known for key in reviewed):
        raise ValueError("reviewed catalogue contains an unknown candidate")
    for row in rows:
        if "candidate_record_sha256" not in row:
            continue
        path = queue / f"{row['id']}-{row['candidate_record_sha256']}.candidate.json"
        record = candidate_review.load_candidate(path)
        report = record["report"]
        row["preface_discovery"] = editorial_evidence.labeled_prefaces(report["body"])
        items = [
            review
            for (identifier, _), review in reviewed.items()
            if identifier == row["id"]
        ]
        if not items:
            continue
        source, _, _ = batch.tranche.workflow.helpers.corpus.cached_text(
            cache, row["id"]
        )
        proofs = [
            editorial_evidence.reviewed_preface(path, source, review)
            for review in items
        ]
        row["preface_role_proofs"] = proofs
        notice = row["rule_evidence"]
        # A failed notice composition cannot be silently discarded to make this
        # different proposal fit. No-match is safe: it contributes no omissions.
        if not notice["transformation_qualified"] and notice["blockers"] != [
            "no_matching_publication_notice"
        ]:
            row["preface_selection"] = {
                "blocked": "notice_proposal_unqualified",
                "publication_approved": False,
            }
            continue
        omissions = sorted(
            [*notice["omissions"], *(proof["omission"] for proof in proofs)],
            key=lambda omitted: omitted["start"],
        )
        # The existing partition validator rejects overlap and excessive ranges.
        # This object is used only for reconstruction; never export it as approval.
        selection = readiness.OrderedReviewDecision.for_report(
            report,
            omissions=omissions,
            reviewer="Partial role evidence proposal only",
            rationale="Hypothetical composition; story approval and history remain separate.",
        )
        selected = selection.reconstruct(report["body"])
        chapters, assessment = review_rules._assessment(selected, report["metadata"])
        blockers = ["whole_story_review_required"]
        if row["prior_intent"] != "unreviewed":
            blockers.append("prior_intent_preserved")
        if assessment.status != "ready":
            blockers.append("selected_" + assessment.status)
        if review_rules._RETAINED_LABEL.search(selected):
            blockers.append("retained_editorial_label")
        stored = json.loads((collection / row["path"] / "story.json").read_bytes())
        baseline_available = (
            readiness.text_sha256(stored["body"]) == row["historical_baseline_sha256"]
        )
        normalized = batch.normalized(selected, row["path"])
        history = (
            historical_review.explain_typography(selected, stored["body"])
            if baseline_available
            and normalized["sha256"] == readiness.text_sha256(selected)
            else {
                "complete": False,
                "residual_shape": "baseline_or_normalization_unavailable",
                "publication_approved": False,
            }
        )
        if not history["complete"]:
            blockers.append("historical_difference_unresolved")
        row["preface_selection"] = {
            "selected_spans": selection.selected_spans,
            "selected_sha256": selection.selected_sha256,
            "omissions": omissions,
            "editorial": selection.editorial(report["body"]),
            "assessment": assessment.to_dict(),
            "chapters": chapters,
            "history": history,
            "blockers": blockers,
            "publication_approved": False,
        }
    summary = {
        **batch.summarize(rows),
        "prior_candidate_inventory": inventory,
        "discovery_candidates": sum(bool(row.get("preface_discovery")) for row in rows),
        "reviewed_candidates": sum(
            bool(row.get("preface_role_proofs")) for row in rows
        ),
        "reviewed_spans": len(reviews),
        "discovered_unreviewed_candidates": sum(
            bool(row.get("preface_discovery")) and not row.get("preface_role_proofs")
            for row in rows
        ),
        "proposal_blockers": dict(
            collections.Counter(
                blocker
                for row in rows
                for blocker in row.get("preface_selection", {}).get("blockers", [])
            )
        ),
        "new_approvals": 0,
        "new_dispositions": 0,
        "new_historical_resolutions": 0,
        "publication_approved": False,
    }
    return summary, rows


def main(argv=None):
    """Persist complete or failed evidence with no side effects on supplied inputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "census",
        "comparison",
        "queue",
        "dispositions",
        "cache",
        "collection",
        "prior_reviews",
        "span_reviews",
        "output",
    ):
        parser.add_argument(name, type=lambda value: pathlib.Path(value).resolve())
    args = parser.parse_args(argv)
    for name in ("queue", "dispositions", "cache", "collection"):
        if args.output.is_relative_to(getattr(args, name)):
            raise ValueError("output cannot be inside an input directory")
    args.output.mkdir(parents=True, exist_ok=False)
    result = {"completed": False, "network_bytes": 0}
    started = time.monotonic()
    handler = signal.signal(signal.SIGALRM, batch.timeout)
    try:
        if shutil.disk_usage(args.output).free < 6 * 1024**3:
            raise ValueError("less than 6GiB free")
        signal.alarm(600)
        inputs = {
            name: batch.tranche.workflow._read_json(getattr(args, name), 64 * 1024**2)
            for name in ("census", "comparison", "prior_reviews", "span_reviews")
        }
        result["inputs"] = {
            name: hashlib.sha256(getattr(args, name).read_bytes()).hexdigest()
            for name in inputs
        }
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ):
            measured, rows = evaluate(
                inputs["census"],
                inputs["comparison"],
                args.queue,
                args.dispositions,
                args.cache,
                args.collection,
                inputs["prior_reviews"],
                inputs["span_reviews"],
            )
        result.update(measured)
        batch._write(args.output / "ledger.json.gz", rows)
        result["completed"] = True
    except Exception as error:
        result.update(completed=False, error=f"{type(error).__name__}: {error}")
        raise
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, handler)
        result["elapsed_seconds"] = time.monotonic() - started
        (args.output / "summary.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
