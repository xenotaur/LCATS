#!/usr/bin/env python3
import argparse
import json
import pathlib
import re
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
    "classification",
    "evidence",
]
MOJIBAKE_RE = re.compile(r"(?:Ã.|Â.|â.|ð.|�)")


class AllowlistConfig:
    """Allowlist settings loaded from CLI and optional JSON config."""

    def __init__(self):
        self.allowed_chars = set()
        self.allowed_codepoints = set()
        self.allowed_unicode_names = set()
        self.allowed_categories = set()

    def is_allowed(self, ch: str) -> bool:
        if ch in self.allowed_chars:
            return True
        if f"U+{ord(ch):04X}" in self.allowed_codepoints:
            return True
        if get_unicode_name(ch) in self.allowed_unicode_names:
            return True
        if unicodedata.category(ch) in self.allowed_categories:
            return True
        return False


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


def load_allowlist_config(config_path: str | None) -> AllowlistConfig:
    """Load allowlist config from JSON, returning an empty config when unset."""
    config = AllowlistConfig()
    if not config_path:
        return config

    with pathlib.Path(config_path).open("r", encoding="utf-8") as config_file:
        payload = json.load(config_file)

    for ch in payload.get("allowed_chars", []):
        for value in ch:
            config.allowed_chars.add(value)

    for codepoint in payload.get("allowed_codepoints", []):
        config.allowed_codepoints.add(f"U+{ord(parse_codepoint(codepoint)):04X}")

    for name in payload.get("allowed_unicode_names", []):
        config.allowed_unicode_names.add(name)

    for category in payload.get("allowed_categories", []):
        config.allowed_categories.add(category)

    return config


def is_allowed(ch: str, allow_smart: bool, allowlist: AllowlistConfig) -> bool:
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
    if allowlist.is_allowed(ch):
        return True
    return False


def is_flagged(
    ch: str, allow_smart: bool, excluded: set[str], allowlist: AllowlistConfig
) -> bool:
    """Return True when a character should be reported."""
    if ch in excluded:
        return False
    return not is_allowed(ch, allow_smart, allowlist)


def classify_character(text: str, offset: int, ch: str) -> tuple[str, str]:
    """Classify one character with a compact evidence string."""
    if ch in SMART_ALLOWED:
        return ("valid-typography", "common typographic punctuation")

    window_start = max(0, offset - 2)
    window_end = min(len(text), offset + 3)
    window = text[window_start:window_end]
    match = MOJIBAKE_RE.search(window)
    if match:
        return ("mojibake-pattern", f"matched mojibake fragment '{match.group(0)}'")

    return (
        "suspicious-unicode",
        f"unicode_category={unicodedata.category(ch)}; non-ascii outside allowlist",
    )


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
    allowlist: AllowlistConfig,
    context: int,
    name_width: int,
):
    """Yield per-occurrence TSV rows for each flagged character in input text."""
    occurrence_counts = {}

    for offset, ch in enumerate(text):
        if not is_flagged(ch, allow_smart, excluded, allowlist):
            continue

        occurrence_counts[ch] = occurrence_counts.get(ch, 0) + 1
        classification, evidence = classify_character(text, offset, ch)
        row = [
            path,
            f"U+{ord(ch):04X}",
            escape_for_tsv(ch),
            truncate_text(get_unicode_name(ch), name_width),
            str(occurrence_counts[ch]),
            str(offset),
            escape_for_tsv(get_context_snippet(text, offset, context)),
            classification,
            escape_for_tsv(evidence),
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
        "--allowlist-config",
        default="",
        help=(
            "Optional path to a JSON allowlist config containing keys such as "
            "allowed_chars, allowed_codepoints, allowed_unicode_names, and "
            "allowed_categories."
        ),
    )
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
    allowlist = load_allowlist_config(args.allowlist_config)

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
