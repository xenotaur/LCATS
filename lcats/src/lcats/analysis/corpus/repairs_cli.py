"""CLI wrapper for conservative Unicode/special-character repair proposals."""

import argparse
import json
import pathlib
import sys

from lcats.analysis.corpus import repairs


def load_input_text(file_path: pathlib.Path) -> str:
    """Return the decoded story body for story JSON files, else raw text.

    Story JSON is written with ASCII-escaped non-ASCII characters, so raw
    file text hides mojibake as \\uXXXX escapes; scanning it would report
    nothing. Offsets in proposals for JSON inputs refer to the decoded body.
    """
    raw = file_path.read_text(encoding="utf-8")
    if file_path.suffix.lower() != ".json":
        return raw
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if isinstance(payload, dict) and isinstance(payload.get("body"), str):
        return payload["body"]
    return raw


def build_parser(add_help: bool = True) -> argparse.ArgumentParser:
    """Build parser for dry-run repair proposal generation."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate conservative dry-run repair proposals for known "
            "Unicode/mojibake findings. This command is non-destructive and "
            "never modifies files. Story JSON inputs are scanned on the "
            "decoded body field; offsets refer to the decoded body text."
        ),
        add_help=add_help,
    )
    parser.add_argument("files", nargs="+")
    parser.add_argument("--header", action="store_true")
    parser.add_argument(
        "--format",
        choices=["tsv", "jsonl"],
        default="tsv",
        help="Dry-run report format (human TSV or machine JSONL).",
    )
    return parser


def run(argv=None, parsed_args=None) -> int:
    """Run dry-run repair proposal generation for one or more text files."""
    parser = build_parser()
    args = parsed_args if parsed_args is not None else parser.parse_args(argv)

    if args.header and args.format == "tsv":
        print("path\tstart\tend\trule\tconfidence\tbefore\tafter\treason")

    for file_name in args.files:
        file_path = pathlib.Path(file_name)
        text = load_input_text(file_path)
        suggestions = repairs.suggest_repairs_for_text(text)
        if args.format == "jsonl":
            report = repairs.build_dry_run_jsonl_report(
                suggestions,
                path=str(file_path),
            )
            if report:
                print(report)
            continue

        for entry in repairs.build_dry_run_plan_entries(suggestions):
            print(
                "\t".join(
                    [
                        str(file_path),
                        str(entry.start),
                        str(entry.end),
                        entry.rule_id,
                        entry.confidence,
                        entry.original_text,
                        entry.replacement_text,
                        entry.rationale,
                    ]
                )
            )

    return 0


if __name__ == "__main__":
    sys.exit(run())
