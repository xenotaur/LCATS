"""CLI wrapper for survey-gated data/ -> corpora/ promotion."""

import argparse
import pathlib
import sys

from lcats.analysis.corpus import promote
from lcats.utils import env


def build_parser(add_help: bool = True) -> argparse.ArgumentParser:
    """Build parser for the promote command."""
    parser = argparse.ArgumentParser(
        description=(
            "Promote data/ collections into corpora/, gated on a passing "
            "special-character survey. A collection with any mojibake "
            "finding is skipped and reported rather than promoted; clean "
            "collections wholesale-replace their corpora/ counterpart."
        ),
        add_help=add_help,
    )
    parser.add_argument(
        "collections",
        nargs="*",
        help="Collection names to consider. Defaults to every collection under --source.",
    )
    parser.add_argument(
        "--source",
        type=pathlib.Path,
        default=env.data_root(),
        help="Root directory of source collections (default: data/).",
    )
    parser.add_argument(
        "--dest",
        type=pathlib.Path,
        default=env.corpora_root(),
        help="Root directory to promote clean collections into (default: ../corpora).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Survey and report without copying any files.",
    )
    return parser


def run(argv=None, parsed_args=None) -> int:
    """Run survey-gated promotion. Returns 0 if all considered collections promoted."""
    parser = build_parser()
    args = parsed_args if parsed_args is not None else parser.parse_args(argv)

    collection_names = args.collections or None
    report = promote.promote_collections(
        source_root=args.source,
        dest_root=args.dest,
        collection_names=collection_names,
        dry_run=args.dry_run,
    )

    for name in report.promoted:
        verb = "would promote" if args.dry_run else "promoted"
        print(f"{verb}: {name} -> {promote.destination_name(name)}")

    for result in report.blocked:
        print(
            f"blocked: {result.collection} "
            f"({len(result.findings)} finding(s) across {result.story_count} stories)",
            file=sys.stderr,
        )
        for finding in result.findings:
            print(
                f"  {finding.story_path}: {finding.codepoint} {finding.character!r} "
                f"context={finding.context!r}",
                file=sys.stderr,
            )

    return 0 if report.all_promoted else 1


if __name__ == "__main__":
    sys.exit(run())
