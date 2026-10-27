"""Inventory boundary residuals and measure a terminal-notice rule, without approval.

Run from lcats/ with project Python/PYTHONPATH; arguments are LEDGER QUEUE
COLLECTION TEXT_CACHE NEW_OUTPUT. The input is a completed cumulative batch ledger.
Revalidate every selected candidate, historical comparison and cached/corpus hash.
Outputs contain full boundary text, candidate-bound rule proofs and counters; they
are review evidence, not dispositions or publication authorization. No network or
writes to inputs. Maximum10,000 ledger rows,600-second alarm,6GiB free minimum.
"""

import argparse
import collections
import gzip
import hashlib
import importlib.util
import json
import pathlib
import re
import shutil
import signal
import socket
from unittest import mock

from lcats.gatherers import candidate_review
from lcats.gatherers import historical_review
from lcats.gatherers import readiness
from lcats.gatherers import review_rules


def _workflow():
    """Reuse the experiment's bounded JSON and historical cache readers."""
    path = pathlib.Path(__file__).with_name("qualify_review_workflow.py")
    spec = importlib.util.spec_from_file_location("boundary_workflow", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


workflow = _workflow()


def timeout(*_):
    """Let the finally block persist an incomplete checkpoint on timeout."""
    raise TimeoutError("boundary census exceeded600 seconds")


def project(text, ranges):
    """Reconstruct the recorded comparison projection, never publication text."""
    cursor, pieces = 0, []
    for item in ranges:
        start, end = item["span"]
        if not cursor <= start < end <= len(text) or text[start:end] != item["text"]:
            raise ValueError("invalid projection evidence")
        pieces.append(text[cursor:start])
        cursor = end
    return "".join([*pieces, text[cursor:]])


def family(text, side):
    """Return an exclusive lexical bucket; these names do not label prose roles."""
    text = text.strip()
    if not text:
        return "empty"
    if side == "suffix":
        if re.search("transcriber", text, re.I):
            return "contains_transcriber"
        if text.startswith(("End of", "*** END")):
            return "starts_end_marker"
    else:
        for pattern, name in (
            (r"Produced by ", "starts_produced_by"),
            (r"by\s", "starts_by"),
            (r"_", "starts_underscore"),
            (r"\[Sidenote", "starts_sidenote"),
            (r"\[Illustration", "starts_illustration"),
            (r"\[Transcriber", "starts_transcriber"),
        ):
            if re.match(pattern, text, re.I):
                return name
    return "other"


def evaluate(ledger, queue, collection, cache):
    """Recheck all boundary rows; qualify transformations, never resolve cases."""
    if not isinstance(ledger, list) or len(ledger) > 10000:
        raise ValueError("ledger population exceeds bound")
    ids = [r["id"] for r in ledger]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate ledger IDs")
    rows = []
    for row in ledger:
        history = row.get("historical_evidence", {})
        if (
            row["historical_resolution"]
            or history.get("residual_shape") != "additional_boundary_text"
        ):
            continue
        identifier = row["id"]
        paths = list(queue.glob(f"{identifier}-*.candidate.json"))
        if len(paths) != 1:
            raise ValueError("candidate generation missing or ambiguous")
        record = candidate_review.load_candidate(paths[0])
        if readiness.identity(record) != row["candidate_record_sha256"]:
            raise ValueError("candidate identity changed")
        relative = pathlib.Path(row["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe corpus path")
        corpus_path = collection / relative / "story.json"
        if corpus_path.stat().st_size > 32 * 1024**2:
            raise ValueError("corpus file exceeds bound")
        raw = corpus_path.read_bytes()
        cached = workflow.helpers.corpus.cached_text(cache, identifier)
        if cached is None:
            raise ValueError("missing cached source")
        _, compressed_sha, decoded_sha = cached
        if (
            hashlib.sha256(raw).hexdigest() != row["corpus_sha256"]
            or compressed_sha != row["compressed_sha256"]
            or decoded_sha != row["decoded_utf8_sha256"]
        ):
            raise ValueError("immutable corpus/source identity changed")
        baseline = json.loads(raw)["body"]
        body = record["report"]["body"]
        previous_rule = review_rules.evaluate_publication_notices(paths[0])
        if previous_rule != row["rule_evidence"]:
            raise ValueError("prior selection proof changed")
        spans = previous_rule.get("selected_spans") or [[0, len(body)]]
        selected = "".join(body[a:b] for a, b in spans)
        if historical_review.explain_typography(selected, baseline) != history:
            raise ValueError("historical comparison changed")
        projected = project(selected, history["selected_comparison_ranges"])
        before, after = (
            history["additional_prefix_characters"],
            history["additional_suffix_characters"],
        )
        prefix, suffix = projected[:before], (
            projected[len(projected) - after :] if after else ""
        )
        proof = review_rules.propose_trailing_publication_notice(body)
        subsequent = None
        if proof:
            # Compose in ORIGINAL candidate coordinates. Projection offsets are
            # diagnostic only and must never be used to cut the source text.
            cut = proof["span"][0]
            retained = "".join(body[a : min(b, cut)] for a, b in spans if a < cut)
            subsequent = historical_review.explain_typography(retained, baseline)
        rows.append(
            {
                "id": identifier,
                "candidate_record_sha256": row["candidate_record_sha256"],
                "corpus_sha256": row["corpus_sha256"],
                "compressed_sha256": row["compressed_sha256"],
                "decoded_utf8_sha256": row["decoded_utf8_sha256"],
                "prior_intent": row["prior_intent"],
                "prefix_family": family(prefix, "prefix"),
                "suffix_family": family(suffix, "suffix"),
                "boundary_offset_basis": "comparison_projection_only",
                "prefix": prefix,
                "suffix": suffix,
                "rule_evidence": proof,
                "after_rule_history": subsequent,
                "publication_approved": False,
            }
        )
    summary = {
        "completed": True,
        "boundary_cases": len(rows),
        "prefix_groups": dict(collections.Counter(r["prefix_family"] for r in rows)),
        "suffix_groups": dict(collections.Counter(r["suffix_family"] for r in rows)),
        "qualified_transformations": sum(r["rule_evidence"] is not None for r in rows),
        "complete_history_after_rule": sum(
            bool(r["after_rule_history"] and r["after_rule_history"]["complete"])
            for r in rows
        ),
        "new_approvals": 0,
        "new_historical_resolutions": 0,
    }
    return summary, rows


def main(argv=None):
    """Write an exclusive evidence checkpoint, preserving failure as incomplete."""
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("ledger", "queue", "collection", "cache", "output"):
        parser.add_argument(name, type=pathlib.Path)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=False)
    summary = {"completed": False}
    previous_handler = signal.signal(signal.SIGALRM, timeout)
    try:
        if shutil.disk_usage(args.output).free < 6 * 1024**3:
            raise ValueError("less than6GiB free")
        signal.alarm(600)
        ledger = workflow._read_json(args.ledger, 64 * 1024**2)
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ):
            measured, rows = evaluate(ledger, args.queue, args.collection, args.cache)
        summary.update(measured)
        summary["completed"] = False
        summary["input_ledger_sha256"] = hashlib.sha256(
            args.ledger.read_bytes()
        ).hexdigest()
        summary["rule"] = review_rules.TRAILING_NOTICE_RULE
        (args.output / "groups.json.gz").write_bytes(
            gzip.compress(json.dumps(rows, sort_keys=True).encode(), mtime=0)
        )
        summary["completed"] = True
    except Exception as error:
        summary["completed"] = False
        summary["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
