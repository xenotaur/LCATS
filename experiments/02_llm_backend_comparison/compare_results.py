"""Compute agreement rates between two backend JSONL result files.

Usage:
    python compare_results.py results/anthropic-*.jsonl results/openai-*.jsonl

Prints a per-story comparison table and summary agreement rates for
`verdict` and `genre_verdict`.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys


def load_jsonl(path: pathlib.Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _short(path: pathlib.Path) -> str:
    return path.name


def compare(file_a: pathlib.Path, file_b: pathlib.Path) -> int:
    records_a = load_jsonl(file_a)
    records_b = load_jsonl(file_b)

    if len(records_a) != len(records_b):
        print(
            f"warning: file lengths differ ({len(records_a)} vs {len(records_b)}); "
            "comparing up to the shorter length.",
            file=sys.stderr,
        )

    n = min(len(records_a), len(records_b))
    if n == 0:
        print("error: no records to compare", file=sys.stderr)
        return 1

    label_a = _short(file_a)
    label_b = _short(file_b)

    verdict_agree = 0
    genre_verdict_agree = 0
    errors_a = 0
    errors_b = 0
    n_valid = 0

    header = f"{'Story':<45} {'Verdict-A':<10} {'Verdict-B':<10} {'V-agree':<9} {'GM-A':<12} {'GM-B':<12} {'GM-agree'}"
    print(header)
    print("-" * len(header))

    for i in range(n):
        a = records_a[i]
        b = records_b[i]

        title_a = a.get("title") or pathlib.Path(a.get("file_path", "")).stem
        title = title_a[:44]

        err_a = bool(a.get("error"))
        err_b = bool(b.get("error"))
        is_error = err_a or err_b

        if err_a:
            errors_a += 1
        if err_b:
            errors_b += 1

        if is_error:
            err_label = f"ERROR({'A' if err_a else ''}{'B' if err_b else ''})"
            print(f"{title:<45} {err_label}")
            continue

        n_valid += 1
        v_a = a.get("verdict", "?")
        v_b = b.get("verdict", "?")
        gm_a = a.get("genre_verdict") or a.get("genre_match", "?")
        gm_b = b.get("genre_verdict") or b.get("genre_match", "?")

        v_ok = v_a == v_b
        gm_ok = gm_a == gm_b

        if v_ok:
            verdict_agree += 1
        if gm_ok:
            genre_verdict_agree += 1

        print(
            f"{title:<45} {v_a:<10} {v_b:<10} {'✓' if v_ok else '✗':<9} "
            f"{gm_a:<12} {gm_b:<12} {'✓' if gm_ok else '✗'}"
        )

    print()
    print(f"Files compared:     {label_a}  vs  {label_b}")
    print(f"Stories compared:   {n}  (valid: {n_valid}  errors: {errors_a + errors_b})")
    if n_valid:
        print(
            f"Verdict agreement:  {verdict_agree}/{n_valid} "
            f"({100*verdict_agree/n_valid:.0f}%)"
        )
        print(
            f"Genre-verdict agree: {genre_verdict_agree}/{n_valid} "
            f"({100*genre_verdict_agree/n_valid:.0f}%)"
        )
    else:
        print("Verdict agreement:   n/a (no valid rows)")
        print("Genre-verdict agree: n/a (no valid rows)")
    if errors_a or errors_b:
        print(f"Errors (A / B):     {errors_a} / {errors_b}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare two backend JSONL result files from run_comparison.py.",
    )
    parser.add_argument("file_a", type=pathlib.Path, help="First JSONL result file.")
    parser.add_argument("file_b", type=pathlib.Path, help="Second JSONL result file.")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    sys.exit(compare(args.file_a, args.file_b))
