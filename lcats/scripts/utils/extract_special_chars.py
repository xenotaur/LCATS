#!/usr/bin/env python3
import argparse
import collections
import sys
import unicodedata


SMART_ALLOWED = {"–", "—", "‘", "’", "“", "”", "…"}
ASCII_PUNCT = {
    chr(i) for i in range(32, 127)
} - set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")


def parse_codepoint(text: str) -> str:
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
    items = []
    for value in values or []:
        for item in value.split(","):
            item = item.strip()
            if item:
                items.append(item)
    return items


def build_excluded_set(exclude_chars, exclude_codepoints):
    excluded = set()

    for item in split_csv_items(exclude_chars):
        for ch in item:
            excluded.add(ch)

    for item in split_csv_items(exclude_codepoints):
        excluded.add(parse_codepoint(item))

    return excluded


def is_allowed(ch: str, allow_smart: bool) -> bool:
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
    if ch in excluded:
        return False
    return not is_allowed(ch, allow_smart)


def iter_input(files):
    if not files:
        yield "stdin", sys.stdin
    else:
        for path in files:
            yield path, open(path, "r", encoding="utf-8")


def render_char(ch: str) -> str:
    return (
        ch.replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def char_name(ch: str) -> str:
    try:
        return unicodedata.name(ch)
    except ValueError:
        return "<unnamed>"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract suspicious or non-standard characters from text."
    )
    parser.add_argument("files", nargs="*")
    parser.add_argument(
        "--allow-smart",
        action="store_true",
        help="Allow common smart punctuation like em dash and curly quotes.",
    )
    parser.add_argument(
        "--counts",
        action="store_true",
        help="Show counts for each suspicious character.",
    )
    parser.add_argument(
        "--lines",
        action="store_true",
        help="Show full lines containing suspicious characters.",
    )
    parser.add_argument(
        "--names",
        action="store_true",
        help="Show Unicode names for reported characters.",
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
    args = parser.parse_args()

    excluded = build_excluded_set(args.exclude_char, args.exclude_codepoint)

    try:
        for label, fh in iter_input(args.files):
            counts = collections.Counter()

            try:
                for line_no, line in enumerate(fh, start=1):
                    bad = [
                        ch
                        for ch in line
                        if is_flagged(ch, args.allow_smart, excluded)
                    ]
                    if not bad:
                        continue

                    if args.lines:
                        sys.stdout.write(f"{label}:{line_no}:{line}")
                    else:
                        counts.update(bad)
            finally:
                if fh is not sys.stdin:
                    fh.close()

            if not args.lines:
                for ch in sorted(counts):
                    code = f"U+{ord(ch):04X}"
                    display = render_char(ch)

                    parts = []
                    if args.counts:
                        parts.append(str(counts[ch]))
                    parts.extend([code, display])

                    if args.names:
                        parts.append(char_name(ch))

                    print("\t".join(parts))

        return 0
    except BrokenPipeError:
        return 141


if __name__ == "__main__":
    raise SystemExit(main())
