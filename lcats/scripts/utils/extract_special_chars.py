#!/usr/bin/env python3
"""Legacy wrapper around lcats.analysis.corpus.specials."""

import argparse
import sys

from lcats.analysis.corpus import specials


SMART_ALLOWED = specials.SMART_ALLOWED
ASCII_PUNCT = specials.ASCII_PUNCT
TSV_COLUMNS = ["path", *specials.TSV_COLUMNS]
AllowlistConfig = specials.AllowlistConfig

parse_codepoint = specials.parse_codepoint
split_csv_items = specials.split_csv_items
build_excluded_set = specials.build_excluded_set
load_allowlist_config = specials.load_allowlist_config
is_allowed = specials.is_allowed
is_flagged = specials.is_flagged
classify_character = specials.classify_character
escape_for_tsv = specials.escape_for_tsv
get_unicode_name = specials.get_unicode_name
truncate_text = specials.truncate_text
get_context_snippet = specials.get_context_snippet


def iter_input(files):
    """Yield (label, file handle) pairs for input files or stdin."""
    if not files:
        yield "stdin", sys.stdin
    else:
        for path in files:
            yield path, open(path, "r", encoding="utf-8")


def iter_special_character_rows(
    path: str,
    text: str,
    allow_smart: bool,
    excluded: set[str],
    allowlist: AllowlistConfig,
    context: int,
    name_width: int,
):
    """Yield per-occurrence TSV rows for each flagged character."""
    for row in specials.iter_special_character_rows(
        text=text,
        allow_smart=allow_smart,
        excluded=excluded,
        allowlist=allowlist,
        context=context,
        name_width=name_width,
    ):
        yield f"{path}\t{row}"


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI parser for special-character extraction."""
    parser = argparse.ArgumentParser(
        description=(
            "Extract suspicious or non-standard characters from text as TSV rows. "
            "Each row is one occurrence."
        )
    )
    parser.add_argument("files", nargs="*")
    parser.add_argument("--allowlist-config", default="")
    parser.add_argument("--allow-smart", action="store_true")
    parser.add_argument("--names", action="store_true")
    parser.add_argument("--counts", action="store_true")
    parser.add_argument("--lines", action="store_true")
    parser.add_argument("--header", action="store_true")
    parser.add_argument("--context", type=int, default=10)
    parser.add_argument("--nocontext", action="store_true")
    parser.add_argument("--name-width", type=int, default=0)
    parser.add_argument("--exclude-char", action="append", default=[])
    parser.add_argument("--exclude-codepoint", action="append", default=[])
    return parser


def main(argv=None) -> int:
    """Run the special-character extractor CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.nocontext:
        args.context = 0
    if args.context < 0:
        parser.error("--context must be >= 0")
    if args.name_width < 0:
        parser.error("--name-width must be >= 0")

    excluded = build_excluded_set(args.exclude_char, args.exclude_codepoint)
    allowlist = load_allowlist_config(args.allowlist_config)

    try:
        if args.header:
            print("\t".join(TSV_COLUMNS))

        for label, handle in iter_input(args.files):
            try:
                text = handle.read()
            finally:
                if handle is not sys.stdin:
                    handle.close()

            for row in iter_special_character_rows(
                path=label,
                text=text,
                allow_smart=args.allow_smart,
                excluded=excluded,
                allowlist=allowlist,
                context=args.context,
                name_width=args.name_width,
            ):
                print(row)

        return 0
    except BrokenPipeError:
        return 141


if __name__ == "__main__":
    raise SystemExit(main())
