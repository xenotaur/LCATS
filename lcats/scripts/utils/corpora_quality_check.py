#!/usr/bin/env python
import argparse
import pathlib
import subprocess
import sys

from tqdm import tqdm


DEFAULT_EXCLUDED_CODEPOINTS = [
    "1F4D6",  # Open Book
    "1F4DC",  # Scroll
    "1F5C2",  # Ledger
    "270D",  # Writing Hand
    "FE0F",  # Variation Selector-16
    "202F",  # NARROW NO-BREAK SPACE
    "00A0",  # NO-BREAK SPACE
]
DEFAULT_EXCLUDED_CHARS = [
    "£",  # Pound Sign
    "ç",  # Latin Small Letter C with Cedilla
    "é",  # Latin Small Letter E with Acute
    "œ",  # Latin Small Ligature OE
    "æ",  # Latin Small Letter AE
    "á",  # Latin Small Letter A with Acute
    "í",  # Latin Small Letter I with Acute
    "ñ",  # Latin Small Letter N with Tilde
    "ö",  # Latin Small Letter O with Diaeresis
    "ü",  # Latin Small Letter U with Diaeresis    
    "è",  # Latin Small Letter E with Grave
    "ë",  # Latin Small Letter E with Diaeresis
    "°",  # Degree Sign
    "´",  # Acute Accent
    "×",  # Multiplication Sign
    "ï",  # Latin Small Letter I with Diaeresis
    "ô",  # Latin Small Letter O with Circumflex
    "ä",  # Latin Small Letter A with Diaeresis
    "ê",  # Latin Small Letter E with Circumflex
    "ā",  # Latin Small Letter A with Macron
    "ī",  # Latin Small Letter I with Macron
    "ū",  # Latin Small Letter U with Macron
    "À",  # Latin Capital Letter A with Grave
    "Â",  # Latin Capital Letter A with Circumflex
    "Ã",  # Latin Capital Letter A with Tilde
    "Ç",  # Latin Capital Letter C with Cedilla
    "É",  # Latin Capital Letter E with Acute
    "Ê",  # Latin Capital Letter E with Circumflex
    "Î",  # Latin Capital Letter I with Circumflex
    "Ü",  # Latin Capital Letter U with Diaeresis
    "à",  # Latin Small Letter A with Grave
    "â",  # Latin Small Letter A with Circumflex
    "ó",  # Latin Small Letter O with Acute
    "ù",  # Latin Small Letter U with Grave
    "û",  # Latin Small Letter U with Circumflex
    "Ō",  # Latin Capital Letter O with Macron
    "ō",  # Latin Small Letter O with Macron
    "ū",  # Latin Small Letter U with Macron
    ]

DEFAULT_CHECKS = ["special-characters"]


def find_json_files(directories):
    for directory in directories:
        path = pathlib.Path(directory)
        if not path.exists():
            print(f"warning: directory does not exist: {directory}", file=sys.stderr)
            continue
        if path.is_file():
            if path.suffix == ".json":
                yield path
            continue
        for file_path in sorted(path.rglob("*.json")):
            if file_path.is_file():
                yield file_path


def run_lcats_display(file_path: pathlib.Path) -> str:
    result = subprocess.run(
        ["lcats", "display", str(file_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"lcats display failed for {file_path}:\n{result.stderr.strip()}"
        )
    return result.stdout


def run_special_characters_check(
    displayed_text: str,
    extract_script: str,
    allow_smart: bool,
    show_names: bool,
    excluded_codepoints,
    excluded_chars,
) -> str:
    cmd = [extract_script]

    if allow_smart:
        cmd.append("--allow-smart")
    if show_names:
        cmd.append("--names")
    if excluded_codepoints:
        cmd.append("--exclude-codepoint=" + ",".join(excluded_codepoints))
    if excluded_chars:
        cmd.append("--exclude-char=" + ",".join(excluded_chars))

    result = subprocess.run(
        cmd,
        input=displayed_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode not in (0, 141):
        raise RuntimeError(
            "special-character check failed:\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result.stdout.strip()


def survey_file(file_path: pathlib.Path, args) -> list[tuple[str, str]]:
    displayed_text = run_lcats_display(file_path)
    findings = []

    for check_name in args.check_for:
        if check_name == "special-characters":
            output = run_special_characters_check(
                displayed_text=displayed_text,
                extract_script=args.extract_script,
                allow_smart=args.allow_smart,
                show_names=args.names,
                excluded_codepoints=args.exclude_codepoint,
                excluded_chars=args.exclude_char,
            )
            if output:
                findings.append((check_name, output))
        else:
            raise ValueError(f"Unsupported check: {check_name}")

    return findings


def parse_csv_args(values):
    items = []
    for value in values or []:
        for item in value.split(","):
            item = item.strip()
            if item:
                items.append(item)
    return items


def build_parser():
    parser = argparse.ArgumentParser(
        description="Survey LCATS corpora files for issues."
    )
    parser.add_argument(
        "directories",
        nargs="*",
        default=["data/"],
        help="Directories or files to survey.",
    )
    parser.add_argument(
        "--check-for",
        action="append",
        default=[],
        help=(
            "Check(s) to run. Repeatable or comma-separated. "
            "Currently supported: special-characters"
        ),
    )
    parser.add_argument(
        "--print-clean-filenames",
        action="store_true",
        help="Print filenames even when no issues are found.",
    )
    parser.add_argument(
        "--extract-script",
        default="scripts/utils/extract_special_chars.py",
        help="Path to the extract_special_chars.py script.",
    )

    # special-characters options
    # allow-smart (default: True)
    parser.add_argument(
        "--allow-smart",
        dest="allow_smart",
        action="store_true",
        help="Allow common smart punctuation (default: enabled).",
    )
    parser.add_argument(
        "--no-allow-smart",
        dest="allow_smart",
        action="store_false",
        help="Disable smart punctuation allowance.",
    )
    parser.set_defaults(allow_smart=True)


    # names (default: True)
    parser.add_argument(
        "--names",
        dest="names",
        action="store_true",
        help="Show Unicode names (default: enabled).",
    )
    parser.add_argument(
        "--no-names",
        dest="names",
        action="store_false",
        help="Disable Unicode names.",
    )
    parser.set_defaults(names=True)
    parser.add_argument(
        "--exclude-codepoint",
        action="append",
        default=[],
        help=(
            "Exclude Unicode codepoints from the special-characters check. "
            "Repeatable or comma-separated."
        ),
    )
    parser.add_argument(
        "--exclude-char",
        action="append",
        default=[],
        help=(
            "Exclude literal characters from the special-characters check. "
            "Repeatable or comma-separated."
        ),
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    args.check_for = parse_csv_args(args.check_for) or list(DEFAULT_CHECKS)

    user_excluded_codepoints = parse_csv_args(args.exclude_codepoint)
    args.exclude_codepoint = list(DEFAULT_EXCLUDED_CODEPOINTS) + user_excluded_codepoints

    user_excluded_chars = parse_csv_args(args.exclude_char)
    args.exclude_char = list(DEFAULT_EXCLUDED_CHARS) + user_excluded_chars

    had_findings = False

    try:
        files_found = list(find_json_files(args.directories))
        for file_path in tqdm(files_found):
            findings = survey_file(file_path, args)

            if findings:
                had_findings = True
                print()
                print(file_path)
                for check_name, output in findings:
                    if len(args.check_for) > 1:
                        print(f"[{check_name}]")
                    print(output)
            elif args.print_clean_filenames:
                print()
                print(file_path)
                print("[clean]")

        return 1 if had_findings else 0

    except BrokenPipeError:
        return 141
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
