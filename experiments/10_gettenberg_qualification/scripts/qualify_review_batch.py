"""Measure narrow-rule review across an immutable corpus and cumulative inventory.

From lcats/ with project Python/PYTHONPATH:
python ../experiments/10_gettenberg_qualification/scripts/qualify_review_batch.py CENSUS COMPARISON QUEUE DISPOSITIONS TEXT_CACHE COLLECTION NEW_OUTPUT_DIRECTORY --prior-reviews REVIEWS --prior-dispositions DIRECTORY [--record-qualified]
--rule ordered opts into the interior notice extension; default boundary is unchanged.
--rule terminal composes ordered and qualified terminal notices. Recording this
mode ALWAYS requires an exact reviewed cohort, even for exact baseline equality.
--historical-acceptance source-grounded additionally accepts a fully evidenced
source-preserved typography difference. Full cohort inspection and cumulative
explicit exceptions are required before recording: historical preservation does
not classify blurbs already present in the old body. Default remains baseline.
No catalog, downloads or story publication. Rechecks every source/corpus identity,
validates population/queue completeness, replays prior tranche reconciliation and
preserves existing approve/exclude/defer/conflict intent. Default is measurement;
--record-qualified explicitly records only previously unreviewed, rule-eligible
selections meeting the explicitly selected historical-acceptance path.
No other differences are silently accepted. Old equality alone is never approval.
Outputs: summary.json, lossless ledger.json.gz, proposed-decisions.json; optional
immutable dispositions and exported approvals.json. <=10000 inputs, existing
bounded source/artifact readers, >=6GiB free, POSIX 600s alarm, no overwrite.
Failures preserve summary completed:false and exit nonzero; partial output is not
acceptance evidence. Candidate text stays in the supplied queue, never duplicated.
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
import time
from unittest import mock

from lcats.analysis.corpus import discovery
from lcats.gatherers import candidate_review
from lcats.gatherers import historical_review
from lcats.gatherers import normalization
from lcats.gatherers import readiness
from lcats.gatherers import review_rules
from lcats.gatherers import review_store


def _tranche():
    path = pathlib.Path(__file__).with_name("reconcile_review_tranche.py")
    spec = importlib.util.spec_from_file_location("batch_tranche", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tranche = _tranche()


def normalized(body, slug):
    """Record existing normalization separately from the exact retained text."""
    data = {"body": body, "metadata": {}}
    normalization.normalize_story_dict(
        data, collection="mass_quantities", story_id=slug
    )
    return {
        "sha256": readiness.text_sha256(data["body"]),
        "characters": len(data["body"]),
        "provenance": data["metadata"].get("normalization"),
    }


def evaluate(
    census,
    comparison,
    queue,
    dispositions,
    text_cache,
    collection,
    prior_reviews,
    prior_dispositions,
    *,
    rule="boundary",
    historical_acceptance="baseline",
):
    """Return a full evidence ledger and qualified decisions without writing them."""
    if rule not in {"boundary", "ordered", "terminal"}:
        raise ValueError("unknown qualification rule")
    if historical_acceptance not in {"baseline", "source-grounded"}:
        raise ValueError("unknown historical acceptance mode")
    baseline, historical = tranche.validated_population(census, comparison)
    if not isinstance(prior_reviews, list) or len(prior_reviews) > 100:
        raise ValueError("prior reviews must be an explicit list of at most 100")
    prior = (
        tranche.reconcile(
            census,
            comparison,
            prior_reviews,
            queue,
            prior_dispositions,
            text_cache,
            collection,
        )
        if prior_reviews
        else {"tranche_disposition_covered_changed_ids": []}
    )
    inventory = candidate_review.inventory(queue, dispositions=dispositions)
    if (
        inventory["multiple_generation_ids"]
        or inventory["unmatched_disposition_candidates"]
    ):
        raise ValueError(
            "inventory requires one generation and no unmatched dispositions"
        )
    by_id = {row["gutenberg_id"]: row for row in inventory["candidates"]}
    if set(by_id) != {
        i for i, row in baseline.items() if row["status"] == "needs_review"
    }:
        raise ValueError("candidate population differs from census")
    # The prior source-review input is independent evidence of known intent.
    # An incomplete cumulative directory must not turn exclude/defer into a new
    # unreviewed candidate eligible for automatic approval.
    for prior_row in prior.get("rows", []):
        known = by_id.get(prior_row["id"])
        present = (
            set()
            if known is None
            else {
                readiness.identity(candidate_review.load_disposition(p))
                for p in known["dispositions"]
            }
        )
        if prior_row["disposition_sha256"] not in present:
            raise ValueError("cumulative inventory omits a known prior disposition")
    paths = list(discovery.iter_collection_story_files(collection))
    expected_paths = {
        collection / tranche.named_file(pathlib.Path(), r["path"]) / "story.json"
        for r in baseline.values()
    }
    if set(paths) != expected_paths or len(paths) != len(baseline):
        raise ValueError("collection population differs from census")
    prior_covered = set(prior["tranche_disposition_covered_changed_ids"])
    rows, decisions = [], []
    for identifier, before in sorted(baseline.items()):
        old = historical[identifier]
        corpus_path = collection / before["path"] / "story.json"
        raw = corpus_path.read_bytes()
        cached = tranche.workflow.helpers.corpus.cached_text(text_cache, identifier)
        if cached is None:
            raise ValueError("missing cached source")
        _, compressed, decoded = cached
        if (
            hashlib.sha256(raw).hexdigest() != before["corpus_sha256"]
            or compressed != before["compressed_sha256"]
            or decoded != before["decoded_utf8_sha256"]
        ):
            raise ValueError("immutable source/corpus identity changed")
        stored = json.loads(raw)
        if (
            tranche.workflow.helpers.corpus.identifiers.ebook_id_from_url(
                stored["metadata"]["url"]
            )
            != identifier
        ):
            raise ValueError("corpus ID differs")
        row = {
            "id": identifier,
            "path": before["path"],
            "status": before["status"],
            "compressed_sha256": compressed,
            "decoded_utf8_sha256": decoded,
            "corpus_sha256": before["corpus_sha256"],
            "historical_body_changed": old["body_equal"],
            "prior_intent": "none",
            "historical_resolution": None,
            "new_rule_qualified": False,
        }
        # Store the positive changed predicate explicitly, while retaining the
        # original tri-state comparison so cleanup refusals cannot become equal.
        row["comparison_body_equal"] = row.pop("historical_body_changed")
        row["historical_body_changed"] = old["body_equal"] is False
        if identifier not in by_id:
            rows.append(row)
            continue
        item = by_id[identifier]
        path = pathlib.Path(item["candidate"])
        record = candidate_review.load_candidate(path)
        report = record["report"]
        if (
            report["provenance"] != before["provenance"]
            or report["metadata"] != before["metadata"]
            or readiness.text_sha256(report["body"]) != old["new_extracted_sha256"]
        ):
            raise ValueError("candidate/population context differs")
        current_normalized = normalized(report["body"], before["path"])
        if current_normalized["sha256"] != old["normalized_after_sha256"]:
            raise ValueError("normalization differs from historical comparison")
        findings = report["provenance"]["publication_readiness"]["findings"]
        row.update(
            candidate_record_sha256=readiness.identity(record),
            prior_intent=item["state"],
            prior_disposition_sha256=[
                readiness.identity(candidate_review.load_disposition(p))
                for p in item["dispositions"]
            ],
            finding_kinds=sorted({f["kind"] for f in findings}),
            recognized_notice_positions=[],
            normalized_candidate=current_normalized,
            historical_baseline_sha256=old["normalized_before_sha256"],
        )
        for finding in findings:
            start, end = finding["span"]
            body = report["body"]
            if finding["kind"] == "editorial_note" and review_rules.publication_notice(
                body[start:end]
            ):
                row["recognized_notice_positions"].append(
                    {
                        "span": [start, end],
                        "location": (
                            "leading"
                            if not body[:start].strip()
                            else "trailing" if not body[end:].strip() else "interior"
                        ),
                    }
                )
        proposal = (
            review_rules.evaluate_boundary_notice(path)
            if rule == "boundary"
            else review_rules.evaluate_publication_notices(
                path, include_terminal=rule == "terminal"
            )
        )
        row["rule_evidence"] = proposal
        # A full population inventory also includes nonmatching candidates. They
        # cannot acquire approval just because their history can be explained.
        selection_spans = (
            proposal.get("selected_spans")
            if rule in {"ordered", "terminal"}
            else (
                [proposal["selected_span"]] if proposal.get("selected_span") else None
            )
        )
        comparison_text = (
            "".join(report["body"][a:b] for a, b in selection_spans)
            if selection_spans
            else report["body"]
        )
        stored_baseline = (
            readiness.text_sha256(stored["body"]) == old["normalized_before_sha256"]
        )
        unchanged_normalization = normalized(comparison_text, before["path"])[
            "sha256"
        ] == readiness.text_sha256(comparison_text)
        if stored_baseline and unchanged_normalization:
            row["historical_evidence"] = historical_review.explain_typography(
                comparison_text, stored["body"]
            )
        else:
            # Never substitute the retained corpus for a different historical
            # baseline, or silently normalize away a text difference.
            row["historical_evidence"] = {
                "complete": False,
                "residual_shape": (
                    "baseline_unavailable"
                    if not stored_baseline
                    else "normalization_requires_review"
                ),
                "publication_approved": False,
            }

        # An earlier tranche has explicit source-grounded historical rationale.
        # It is not silently carried across a now-conflicting cumulative intent.
        if identifier in prior_covered and item["state"] in {"approve", "exclude"}:
            prior_row = next(r for r in prior["rows"] if r["id"] == identifier)
            if (
                prior_row["outcome"] == item["state"]
                and prior_row["disposition_sha256"] in row["prior_disposition_sha256"]
            ):
                row["historical_resolution"] = "prior_source_review"
        # Prior approvals supply independent selected-text review. Exact baseline
        # equality explains the historical delta without claiming old text is truth.
        if item["state"] == "approve":
            approval = candidate_review.load_disposition(item["dispositions"][0])[
                "approval"
            ]
            selected = readiness.selected_text(
                readiness.decision_from_dict(approval), report["body"]
            )
            row["prior_selected_normalized"] = normalized(selected, before["path"])
            if (
                row["historical_body_changed"]
                and row["prior_selected_normalized"]["sha256"]
                == old["normalized_before_sha256"]
            ):
                row["historical_resolution"] = "prior_review_baseline_reconciled"
            elif (
                historical_acceptance == "source-grounded"
                and stored_baseline
                and (
                    row["prior_selected_normalized"]["sha256"]
                    == readiness.text_sha256(selected)
                )
            ):
                evidence = historical_review.explain_typography(
                    selected, stored["body"]
                )
                row["prior_historical_evidence"] = evidence
                if evidence["complete"] and row["historical_body_changed"]:
                    row["historical_resolution"] = "prior_review_source_reconciled"
        spans = (
            proposal.get("selected_spans")
            if rule in {"ordered", "terminal"}
            else (
                [proposal["selected_span"]]
                if proposal["selected_span"] is not None
                else None
            )
        )
        if spans is not None:
            selected = "".join(report["body"][a:b] for a, b in spans)
            selected_normalized = normalized(selected, before["path"])
            row["rule_selected_normalized"] = selected_normalized
            equal = selected_normalized["sha256"] == old["normalized_before_sha256"]
            explained = equal or (
                historical_acceptance == "source-grounded"
                and row["historical_evidence"]["complete"]
            )
            row["rule_explains_entire_historical_difference"] = explained
            row["historical_acceptance_basis"] = (
                "exact_baseline"
                if equal
                else historical_review.RULE if explained else None
            )
            # Keep eligibility separate from accounting. In particular, a ready
            # assessment can miss an unlabelled blurb; unexplained added text is
            # not resolved merely because this notice was safely recognized.
            if (
                (
                    proposal["approval_eligible"]
                    if rule == "boundary"
                    else proposal["selected_readiness_eligible"]
                )
                and explained
                and item["state"] == "unreviewed"
                and row["historical_body_changed"]
            ):
                attribution = {
                    "reviewer": "Codex agent: qualified " + rule + " rule",
                    "rationale": (
                        f"Qualified {proposal['rule']}: only complete publication notices removed; "
                        "exact retained characters reassessed ready, no retained editorial labels; "
                        + (
                            "existing normalization exactly matches recorded historical baseline. "
                            if equal
                            else "Source-preserved typography explains every historical difference; "
                            "comparison-only projection never alters published text. "
                        )
                        + "Per-input proof in batch ledger; no claim of complete literary reading."
                    ),
                }
                decision = (
                    readiness.OrderedReviewDecision.for_report(
                        report, omissions=proposal["omissions"], **attribution
                    )
                    if rule in {"ordered", "terminal"}
                    else readiness.ReviewDecision.for_report(
                        report, start=spans[0][0], end=spans[0][1], **attribution
                    )
                )
                decisions.append(dataclasses.asdict(decision))
                row["new_rule_qualified"] = True
                row["historical_resolution"] = "qualified_" + rule + "_rule"
        rows.append(row)
    return rows, decisions, inventory["counts"]


def summarize(rows, *, record_qualified=False):
    """Derive disjoint historical coverage and separate inventory/rule measures."""
    changed = {r["id"] for r in rows if r["historical_body_changed"]}
    covered = {
        r["id"]
        for r in rows
        if r["historical_resolution"] is not None
        and (
            record_qualified or not r["historical_resolution"].startswith("qualified_")
        )
    }
    return {
        "historical_explanation_complete": sum(
            r.get("historical_evidence", {}).get("complete", False) for r in rows
        ),
        "residual_groups": dict(
            collections.Counter(
                r.get("historical_evidence", {}).get("residual_shape", "no_candidate")
                for r in rows
                if r["id"] in changed - covered
            )
        ),
        "population": len(rows),
        "historical_changed": len(changed),
        "historical_resolved_ids": sorted(changed & covered),
        "historical_unresolved_ids": sorted(changed - covered),
        "source_counts": dict(collections.Counter(r["status"] for r in rows)),
        "prior_intent_counts": dict(
            collections.Counter(r["prior_intent"] for r in rows)
        ),
        "rule_matched": sum(
            r.get("rule_evidence", {}).get("matched", False) for r in rows
        ),
        "rule_readiness_eligible": sum(
            r.get("rule_evidence", {}).get(
                "approval_eligible",
                r.get("rule_evidence", {}).get("selected_readiness_eligible", False),
            )
            for r in rows
        ),
        "rule_transformation_qualified": sum(
            r.get("rule_evidence", {}).get("transformation_qualified", False)
            for r in rows
        ),
        "new_rule_qualified_ids": [r["id"] for r in rows if r["new_rule_qualified"]],
        "notice_positions": dict(
            collections.Counter(
                p["location"]
                for r in rows
                for p in r.get("recognized_notice_positions", [])
            )
        ),
        "finding_groups": [
            {"kinds": list(k), "count": v}
            for k, v in collections.Counter(
                tuple(r.get("finding_kinds", [])) for r in rows
            ).most_common()
        ],
        "corpus_accepted": False,
    }


def verify_cohort(reviews, rows, decisions, queue, *, require_all=False):
    """Require explicit source inspection before recording non-equal selections.

    Historical equivalence cannot detect a blurb already in the old corpus.
    ``require_all`` also covers exact-baseline proposals: unchanged historical
    text can contain editorial material and must not bypass terminal-mode review.
    Bind this finite cohort review to exact candidate/selection/baseline identities
    and verify its cited candidate excerpts. Attribution is not authentication or
    proof of literary judgment; a review packet remains independently reviewable.
    """
    needed = {
        r["id"]: r
        for r in rows
        if r["new_rule_qualified"]
        and (
            require_all
            or r.get("historical_acceptance_basis") == historical_review.RULE
        )
    }
    if not isinstance(reviews, list) or len(reviews) != len(needed):
        raise ValueError("source-grounded recording requires the exact reviewed cohort")
    seen = set()
    by_id = {d["gutenberg_id"]: d for d in decisions}
    for review in reviews:
        identifier = review.get("id")
        if (
            type(identifier) is not int
            or identifier not in needed
            or identifier in seen
        ):
            raise ValueError("invalid or duplicate reviewed cohort ID")
        seen.add(identifier)
        row, decision = needed[identifier], by_id[identifier]
        for key, expected in (
            ("candidate_record_sha256", row["candidate_record_sha256"]),
            ("selected_sha256", decision["selected_sha256"]),
            ("historical_sha256", row["historical_baseline_sha256"]),
        ):
            if review.get(key) != expected:
                raise ValueError("reviewed cohort identity differs")
        for key in ("reviewer", "rationale"):
            if (
                not isinstance(review.get(key), str)
                or not 1 <= len(review[key].strip()) <= 4000
            ):
                raise ValueError("reviewed cohort attribution/rationale required")
        candidate = (
            queue / f"{identifier}-{row['candidate_record_sha256']}.candidate.json"
        )
        report = candidate_review.load_candidate(candidate)["report"]
        tranche.verify_anchors(report["body"], review.get("candidate_anchors"))
        row["cohort_review"] = review
        row["cohort_review_sha256"] = readiness.identity(review)


def _write(path, value):
    raw = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(gzip.compress(raw, mtime=0) if path.suffix == ".gz" else raw)


def timeout(*_):
    raise TimeoutError("batch qualification exceeded 600 seconds")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    for name in (
        "census",
        "comparison",
        "queue",
        "dispositions",
        "text_cache",
        "collection",
        "output",
    ):
        ap.add_argument(name, type=lambda value: pathlib.Path(value).resolve())
    ap.add_argument("--prior-reviews", type=pathlib.Path, required=True)
    ap.add_argument("--prior-dispositions", type=pathlib.Path, required=True)
    ap.add_argument("--record-qualified", action="store_true")
    ap.add_argument(
        "--cohort-review",
        type=pathlib.Path,
        help="Exact per-input source review packet; required for every terminal-mode proposal",
    )
    ap.add_argument(
        "--rule", choices=("boundary", "ordered", "terminal"), default="boundary"
    )
    ap.add_argument(
        "--historical-acceptance",
        choices=("baseline", "source-grounded"),
        default="baseline",
    )
    args = ap.parse_args(argv)
    if args.output.exists():
        ap.error("output directory must be new")
    review_store.working_root(args.output, data_root=args.collection)
    if (
        not hasattr(signal, "SIGALRM")
        or shutil.disk_usage(args.output.parent).free < 6 * 1024**3
    ):
        ap.error("requires POSIX alarm and at least 6GiB free")
    args.output.mkdir()
    result = {
        "completed": False,
        "network_bytes": 0,
        "scope": __doc__,
        "record_qualified": args.record_qualified,
        "rule": args.rule,
        "historical_acceptance": args.historical_acceptance,
    }
    started = time.monotonic()
    previous = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(600)
    try:
        inputs = (args.census, args.comparison, args.prior_reviews)
        reports = [tranche.workflow._read_json(p, 64 * 1024**2) for p in inputs]
        result["input_sha256"] = {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs
        }
        result["implementation_sha256"] = {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (
                pathlib.Path(__file__),
                pathlib.Path(tranche.__file__),
                pathlib.Path(review_rules.__file__),
                pathlib.Path(readiness.__file__),
                pathlib.Path(candidate_review.__file__),
                pathlib.Path(normalization.__file__),
                pathlib.Path(historical_review.__file__),
            )
        }
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ):
            rows, decisions, inventory = evaluate(
                reports[0],
                reports[1],
                args.queue,
                args.dispositions,
                args.text_cache,
                args.collection,
                reports[2],
                args.prior_dispositions,
                rule=args.rule,
                historical_acceptance=args.historical_acceptance,
            )
            if args.record_qualified and (
                args.historical_acceptance == "source-grounded"
                or args.rule == "terminal"
            ):
                reviews = (
                    []
                    if args.cohort_review is None
                    else tranche.workflow._read_json(args.cohort_review, 64 * 1024**2)
                )
                verify_cohort(
                    reviews,
                    rows,
                    decisions,
                    args.queue,
                    require_all=args.rule == "terminal",
                )
            result.update(summarize(rows, record_qualified=args.record_qualified))
            result["prior_candidate_inventory"] = inventory
            _write(args.output / "ledger.json.gz", rows)
            _write(args.output / "proposed-decisions.json", decisions)
            if args.record_qualified and decisions:
                paths = []
                for decision in decisions:
                    identifier = decision["gutenberg_id"]
                    row = next(r for r in rows if r["id"] == identifier)
                    candidate = (
                        args.queue
                        / f"{identifier}-{row['candidate_record_sha256']}.candidate.json"
                    )
                    paths.append(
                        candidate_review.record_disposition(
                            candidate,
                            outcome="approve",
                            **(
                                {
                                    "omissions": [
                                        {k: v for k, v in o.items() if k != "sha256"}
                                        for o in decision["omitted_spans"]
                                    ]
                                }
                                if decision["schema_version"] == 2
                                else {
                                    "start": decision["selected_start"],
                                    "end": decision["selected_end"],
                                }
                            ),
                            reviewer=decision["reviewer"],
                            rationale=decision["rationale"],
                            directory=args.output / "dispositions",
                        )
                    )
                candidate_review.export_approvals(
                    paths, candidates=args.queue, output=args.output / "approvals.json"
                )
            result["completed"] = True
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
        result["elapsed_seconds"] = time.monotonic() - started
        _write(args.output / "summary.json", result)


if __name__ == "__main__":
    main()
