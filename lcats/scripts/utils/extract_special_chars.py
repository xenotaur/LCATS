#!/usr/bin/env python3
import argparse
import sys
import unicodedata


SMART_ALLOWED = {"–", "—", "‘", "’", "“", "”", "…"}
ASCII_PUNCT = {chr(i) for i in range(32, 127)} - set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
)
TSV_COLUMNS = [
    "path",
    "codepoint",
    "char",
    "unicode_name",
    "occurrence_index",
    "offset",
    "context",
]


def parse_codepoint(text: str) -> str:
    """Parse a codepoint string and return the corresponding character."""
    s = text.strip().upper()
    if s.startswith("U+"):
        s = s[2:]
    try:
        value = int(s, 16)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid codepoint '{text}'. Expected forms like U+00A3 or 00A3."
        ) from exc
    try:
        return chr(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid Unicode scalar value '{text}'."
        ) from exc


def split_csv_items(values):
    """Split repeatable comma-separated CLI values into a flat list."""
    items = []
    for value in values or []:
        for item in value.split(","):
            item = item.strip()
            if item:
                items.append(item)
    return items


def build_excluded_set(exclude_chars, exclude_codepoints):
    """Build a set of characters to exclude from special-character reporting."""
    excluded = set()

    for item in split_csv_items(exclude_chars):
        for ch in item:
            excluded.add(ch)

    for item in split_csv_items(exclude_codepoints):
        excluded.add(parse_codepoint(item))

    return excluded


def is_allowed(ch: str, allow_smart: bool) -> bool:
    """Return True when a character is allowed by the configured filters."""
    if ch.isascii():
        if ch.isalnum():
            return True
        if ch in " \t\r\n":
            return True
        if ch in ASCII_PUNCT:
            return True
    if allow_smart and ch in SMART_ALLOWED:
        return True
    return False


def is_flagged(ch: str, allow_smart: bool, excluded: set[str]) -> bool:
    """Return True when a character should be reported."""
    if ch in excluded:
        return False
    return not is_allowed(ch, allow_smart)


def iter_input(files):
    """Yield (label, file handle) pairs for input files or stdin."""
    if not files:
        yield "stdin", sys.stdin
    else:
        for path in files:
            yield path, open(path, "r", encoding="utf-8")


def escape_for_tsv(text: str) -> str:
    """Escape tabs and line breaks so each output row stays single-line TSV."""
    return text.replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def get_unicode_name(ch: str) -> str:
    """Return a Unicode name for a character, or UNKNOWN when unnamed."""
    return unicodedata.name(ch, "UNKNOWN")


def truncate_text(text: str, width: int) -> str:
    """Truncate text to a deterministic width using an ellipsis."""
    if width <= 0 or len(text) <= width:
        return text
    if width == 1:
        return "…"
    return text[: width - 1] + "…"


def get_context_snippet(text: str, offset: int, context: int) -> str:
    """Return a left/target/right context snippet centered on one character offset."""
    if context <= 0:
        return ""
    start = max(0, offset - context)
    end = min(len(text), offset + context + 1)
    return text[start:end]


def iter_special_character_rows(
    path: str,
    text: str,
    allow_smart: bool,
    excluded: set[str],
    context: int,
    name_width: int,
):
    """Yield per-occurrence TSV rows for each flagged character in input text."""
    occurrence_counts = {}

    for offset, ch in enumerate(text):
        if not is_flagged(ch, allow_smart, excluded):
            continue

        occurrence_counts[ch] = occurrence_counts.get(ch, 0) + 1
        row = [
            path,
            f"U+{ord(ch):04X}",
            escape_for_tsv(ch),
            truncate_text(get_unicode_name(ch), name_width),
            str(occurrence_counts[ch]),
            str(offset),
            escape_for_tsv(get_context_snippet(text, offset, context)),
        ]
        yield "\t".join(row)


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI parser for special-character extraction."""
    parser = argparse.ArgumentParser(
        description=(
            "Extract suspicious or non-standard characters from text as TSV rows. "
            "Each row is one occurrence."
        )
    )
    parser.add_argument("files", nargs="*")
    parser.add_argument(
        "--allow-smart",
        action="store_true",
        help="Allow common smart punctuation like em dash and curly quotes.",
    )
    parser.add_argument(
        "--names",
        action="store_true",
        help="Reserved for compatibility; names are always included in TSV output.",
    )
    parser.add_argument(
        "--counts",
        action="store_true",
        help="Reserved for compatibility; output is per-occurrence TSV rows.",
    )
    parser.add_argument(
        "--lines",
        action="store_true",
        help="Reserved for compatibility; output is per-occurrence TSV rows.",
    )
    parser.add_argument(
        "--header",
        action="store_true",
        help="Emit a TSV header row.",
    )
    parser.add_argument(
        "--context",
        type=int,
        default=10,
        help="Number of left/right context characters to include (default: 10).",
    )
    parser.add_argument(
        "--nocontext",
        action="store_true",
        help="Convenience flag equivalent to --context=0.",
    )
    parser.add_argument(
        "--name-width",
        type=int,
        default=0,
        help="Optional max width for Unicode name (0 means no truncation).",
    )
    parser.add_argument(
        "--exclude-char",
        action="append",
        default=[],
        help=(
            "Exclude literal characters from reporting. Repeatable. "
            "Each use may contain a comma-separated list, e.g. --exclude-char '£,æ,œ'."
        ),
    )
    parser.add_argument(
        "--exclude-codepoint",
        action="append",
        default=[],
        help=(
            "Exclude Unicode codepoints such as U+00A3. Repeatable. "
            "Each use may contain a comma-separated list, e.g. "
            "--exclude-codepoint '00A3,1F4D6,1F4DC'."
        ),
    )
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

    try:
        if args.header:
            print("\t".join(TSV_COLUMNS))

        for label, fh in iter_input(args.files):
            try:
                text = fh.read()
            finally:
                if fh is not sys.stdin:
                    fh.close()

            for row in iter_special_character_rows(
                path=label,
                text=text,
                allow_smart=args.allow_smart,
                excluded=excluded,
                context=args.context,
                name_width=args.name_width,
            ):
                print(row)

        return 0
    except BrokenPipeError:
        return 141


if __name__ == "__main__":
    raise SystemExit(main())
