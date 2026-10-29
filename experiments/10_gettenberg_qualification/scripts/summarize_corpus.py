"""Produce a compact review index for a cached-corpus comparison JSON report.

Usage: python summarize_corpus.py INPUT_JSON NEW_SUMMARY_JSON
No corpus/source reads or network. Classification is mechanical triage, not an
acceptance decision: all changed bodies still need review. In particular, a
prefix-preserving extension may be unwanted boilerplate; an earlier difference
may be either a correction or story loss. Do not infer narrative safety from size.
"""

import argparse
import collections
import hashlib
import json
import pathlib


def classify(row):
    """Label observed difference shape without pretending to establish safety."""
    if row["status"] != "compared":
        return row["status"]
    if row["body_equal"]:
        return "same_body" if row["retained_corpus_matches"] else "retained_corpus_only"
    if row["first_difference"]["offset"] != row["old_body_characters"]:
        return "earlier_body_difference"
    # The runner's excerpt starts at max(0, offset-60), so discard only that
    # shared context before classifying the newly appended first visible text.
    difference = row["first_difference"]
    suffix = difference["after"][min(60, difference["offset"]) :].lstrip()
    if suffix.startswith("End of"):
        return "appended_end_notice"
    if suffix.startswith("Transcriber"):
        return "appended_transcriber_note"
    if suffix.startswith("--"):
        return "appended_byline_or_separator"
    return "appended_other"


def summarize(report):
    """Retain a disposition row for every input; no missing/refusal becomes pass."""
    rows = []
    for row in report["rows"]:
        item = {
            "id": row["id"],
            "bucket": pathlib.Path(row["path"]).parent.name,
            "classification": classify(row),
            "metadata_rejection": row.get("metadata_rejection"),
            "extraction_rejection": row.get("new_rejection"),
        }
        if row.get("cleanup_diagnostics"):
            item["cleanup_diagnostics"] = row["cleanup_diagnostics"]
        rows.append(item)
    return {
        "experiment_completed": report["completed"],
        "acceptance": "blocked pending body-difference/refusal review",
        "counts": dict(collections.Counter(r["classification"] for r in rows)),
        "body_differences": report.get("body_differences"),
        "retained_corpus_differences": report.get("retained_corpus_differences"),
        "rows": rows,
    }


def main(argv=None):
    """Write a new compact evidence index without overwriting any artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    args = parser.parse_args(argv)
    raw = args.input.read_bytes()
    report = summarize(json.loads(raw))
    report["input_sha256"] = hashlib.sha256(raw).hexdigest()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
