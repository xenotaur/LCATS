"""Compute agreement rates between two backend JSONL result files.

Usage:
    python compare_results.py results/anthropic-*.jsonl results/openai-*.jsonl

Prints a per-story comparison table and summary agreement rates for
`verdict` and `genre_match`.
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
    genre_match_agree = 0
    errors_a = 0
    errors_b = 0

    header = f"{'Story':<45} {'Verdict-A':<10} {'Verdict-B':<10} {'V-agree':<9} {'GM-A':<12} {'GM-B':<12} {'GM-agree'}"
    print(header)
    print("-" * len(header))

    for i in range(n):
        a = records_a[i]
        b = records_b[i]

        title_a = a.get("title") or pathlib.Path(a.get("file_path", "")).stem
        title = title_a[:44]

        v_a = a.get("verdict", "?")
        v_b = b.get("verdict", "?")
        gm_a = a.get("genre_match", "?")
        gm_b = b.get("genre_match", "?")

        v_ok = v_a == v_b
        gm_ok = gm_a == gm_b

        if v_ok:
            verdict_agree += 1
        if gm_ok:
            genre_match_agree += 1
        if a.get("error"):
            errors_a += 1
        if b.get("error"):
            errors_b += 1

        print(
            f"{title:<45} {v_a:<10} {v_b:<10} {'✓' if v_ok else '✗':<9} "
            f"{gm_a:<12} {gm_b:<12} {'✓' if gm_ok else '✗'}"
        )

    print()
    print(f"Files compared:     {label_a}  vs  {label_b}")
    print(f"Stories compared:   {n}")
    print(f"Verdict agreement:  {verdict_agree}/{n} ({100*verdict_agree/n:.0f}%)")
    print(
        f"Genre-match agree:  {genre_match_agree}/{n} ({100*genre_match_agree/n:.0f}%)"
    )
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
