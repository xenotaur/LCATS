"""CLI wrapper for conservative Unicode/special-character repair proposals."""

import argparse
import pathlib
import sys

from lcats.analysis.corpus import repairs


def build_parser(add_help: bool = True) -> argparse.ArgumentParser:
    """Build parser for dry-run repair proposal generation."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate conservative dry-run repair proposals for known "
            "Unicode/mojibake findings. This command is non-destructive and "
            "never modifies files."
        ),
        add_help=add_help,
    )
    parser.add_argument("files", nargs="+")
    parser.add_argument("--header", action="store_true")
    return parser


def run(argv=None, parsed_args=None) -> int:
    """Run dry-run repair proposal generation for one or more text files."""
    parser = build_parser()
    args = parsed_args if parsed_args is not None else parser.parse_args(argv)

    if args.header:
        print("path\tstart\tend\trule\tconfidence\tbefore\tafter\treason")

    for file_name in args.files:
        file_path = pathlib.Path(file_name)
        text = file_path.read_text(encoding="utf-8")
        suggestions = repairs.suggest_repairs_for_text(text)
        for suggestion in suggestions:
            print(
                "\t".join(
                    [
                        str(file_path),
                        str(suggestion.start),
                        str(suggestion.end),
                        suggestion.rule_id,
                        suggestion.confidence,
                        suggestion.original_text,
                        suggestion.replacement_text,
                        suggestion.rationale,
                    ]
                )
            )

    return 0


if __name__ == "__main__":
    sys.exit(run())
