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

COMMON_MOJIBAKE_REPAIRS = {
    "Ã©": "é",
    "Ã±": "ñ",
    "Ã¶": "ö",
    "Ã¼": "ü",
    "Ã¨": "è",
    "Ã¡": "á",
    "Ã": "à",
    "Â£": "£",
    "Â ": " ",
    "â€™": "’",
    "â€œ": "“",
    "â€\x9d": "”",
    "â€“": "–",
    "â€”": "—",
    "â€¦": "…",
    "√©": "é",
    "√±": "ñ",
    "√∂": "ö",
}
MOJIBAKE_KEYS = sorted(COMMON_MOJIBAKE_REPAIRS.keys(), key=len, reverse=True)
KNOWN_ODD_SPACES = {"\u00A0", "\u2007", "\u202F"}


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


def _is_word_like(ch: str) -> bool:
    return ch.isalpha() or ch in "'-"


def _is_likely_good_lexical(text: str, offset: int, ch: str) -> bool:
    if not ch.isalpha():
        return False
    if ord(ch) <= 127:
        return False
    if "LATIN" not in get_unicode_name(ch):
        return False
    prev_char = text[offset - 1] if offset > 0 else ""
    next_char = text[offset + 1] if offset + 1 < len(text) else ""
    return _is_word_like(prev_char) or _is_word_like(next_char)


def _build_metadata(ch: str) -> dict[str, str | bool]:
    nfc = unicodedata.normalize("NFC", ch)
    nfd = unicodedata.normalize("NFD", ch)
    return {
        "unicode_name": get_unicode_name(ch),
        "unicode_category": unicodedata.category(ch),
        "is_combining": bool(unicodedata.combining(ch)),
        "is_odd_space": ch in KNOWN_ODD_SPACES,
        "is_bom": ord(ch) == 0xFEFF,
        "nfc": nfc,
        "nfd": nfd,
        "is_normalized_nfc": nfc == ch,
    }


def _scan_repair_sequences(text: str) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    index = 0
    while index < len(text):
        matched = False
        for key in MOJIBAKE_KEYS:
            if text.startswith(key, index):
                candidates.append(
                    {
                        "offset": index,
                        "sequence": key,
                        "repair": COMMON_MOJIBAKE_REPAIRS[key],
                        "evidence": {
                            "rule": "known-mojibake-map",
                            "confidence": "high",
                            "original": key,
                            "proposed_repair": COMMON_MOJIBAKE_REPAIRS[key],
                        },
                    }
                )
                index += len(key)
                matched = True
                break
        if not matched:
            index += 1
    return candidates


def classify_character(
    text: str,
    offset: int,
    ch: str,
    covered_offsets: set[int],
) -> tuple[str | None, str]:
    """Classify one character using layered Unicode QA checks."""
    if offset in covered_offsets:
        return (None, "")

    metadata = _build_metadata(ch)
    if _is_likely_good_lexical(text, offset, ch):
        return (
            "likely-good-unicode",
            json.dumps(
                {
                    "layer": "likely-good",
                    "reason": "latin-letter-in-word-context",
                    "metadata": metadata,
                },
                ensure_ascii=False,
            ),
        )

    if metadata["is_bom"]:
        return (
            "review-needed",
            json.dumps(
                {
                    "layer": "metadata",
                    "reason": "bom-character",
                    "metadata": metadata,
                },
                ensure_ascii=False,
            ),
        )

    if metadata["is_odd_space"] or metadata["is_combining"]:
        return (
            "review-needed",
            json.dumps(
                {
                    "layer": "metadata",
                    "reason": "odd-space-or-combining",
                    "metadata": metadata,
                },
                ensure_ascii=False,
            ),
        )

    return (
        "suspicious-unicode",
        json.dumps(
            {
                "layer": "residual-review",
                "reason": "non-ascii-outside-likely-good-and-known-repairs",
                "metadata": metadata,
            },
            ensure_ascii=False,
        ),
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
    """Yield per-occurrence TSV rows for each Unicode QA finding in text."""
    occurrence_counts = {}
    covered_offsets = set()

    for candidate in _scan_repair_sequences(text):
        offset = candidate["offset"]
        sequence = candidate["sequence"]
        for idx in range(offset, offset + len(sequence)):
            covered_offsets.add(idx)
        occurrence_counts[sequence] = occurrence_counts.get(sequence, 0) + 1
        row = [
            path,
            f"U+{ord(sequence[0]):04X}",
            escape_for_tsv(sequence),
            truncate_text("KNOWN MOJIBAKE SEQUENCE", name_width),
            str(occurrence_counts[sequence]),
            str(offset),
            escape_for_tsv(get_context_snippet(text, offset, context)),
            "repair-candidate",
            escape_for_tsv(json.dumps(candidate["evidence"], ensure_ascii=False)),
        ]
        yield "\t".join(row)

    for offset, ch in enumerate(text):
        if not is_flagged(ch, allow_smart, excluded, allowlist):
            continue

        classification, evidence = classify_character(text, offset, ch, covered_offsets)
        if not classification:
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
