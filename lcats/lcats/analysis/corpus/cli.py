"""CLI helpers for corpus survey and stats subcommands."""

import argparse
import csv
import json
import pathlib
import sys

from typing import Optional, Sequence

import lcats.inspect
import tqdm

from lcats.analysis.corpus import discovery
from lcats.analysis.corpus import output
from lcats.analysis.corpus import qa
from lcats.analysis.corpus import specials
from lcats.analysis.corpus import stats
from lcats.analysis.corpus.detectors import boundary
from lcats.analysis.corpus.detectors import unicode


def read_story_data(file_path: pathlib.Path) -> dict:
    """Read one corpus JSON file and return its parsed data."""
    with file_path.open("r", encoding="utf-8") as json_file:
        return json.load(json_file)


def run_lcats_display(file_path: pathlib.Path) -> str:
    """Render one corpus JSON file using the same formatter as lcats display."""
    rendered, _ = run_lcats_display_and_title(file_path)
    return rendered


def read_story_title(file_path: pathlib.Path) -> str:
    """Read one corpus JSON file and return a display title."""
    data = read_story_data(file_path)
    return infer_story_title(data, file_path)


def read_story_text(file_path: pathlib.Path) -> str:
    """Read one corpus JSON file and return the normalized story body text."""
    data = read_story_data(file_path)
    return coerce_story_text(data.get("body", ""))


def infer_story_title(data: dict, file_path: pathlib.Path) -> str:
    """Infer stable title from story data, falling back to filename stem."""
    story_title = (
        data.get("name") or data.get("metadata", {}).get("name") or ""
    ).strip()
    if not story_title:
        return file_path.stem
    return story_title


def coerce_story_text(value) -> str:
    """Return normalized story body text without importing heavier analysis modules."""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace")
    if isinstance(value, str):
        return lcats.inspect._decode_possible_bytes_literal(value)
    return str(value)


def run_lcats_display_and_title(file_path: pathlib.Path) -> tuple[str, str]:
    """Render one corpus JSON file and return display text plus story title."""
    data = read_story_data(file_path)
    story_title = infer_story_title(data, file_path)
    rendered = lcats.inspect.format_story_json(data, max_body_chars=None, width=80)
    return f"{rendered}\n", story_title


def run_special_characters_check(
    displayed_text: str,
    extract_script: str,
    allow_smart: bool,
    allowlist_config: str,
    excluded_codepoints,
    excluded_chars,
    context: int,
    nocontext: bool,
    name_width: int,
    header: bool,
) -> str:
    """Run the special-character extractor and return its TSV output."""
    _ = extract_script
    effective_context = 0 if nocontext else context
    excluded = specials.build_excluded_set(excluded_chars, excluded_codepoints)
    allowlist = specials.load_allowlist_config(allowlist_config)
    return specials.build_special_character_report(
        text=displayed_text,
        allow_smart=allow_smart,
        excluded=excluded,
        allowlist=allowlist,
        context=effective_context,
        name_width=name_width,
        header=header,
    )


def parse_csv_args(values):
    """Split repeatable comma-separated CLI values into a flat list."""
    items = []
    for value in values or []:
        for item in value.split(","):
            item = item.strip()
            if item:
                items.append(item)
    return items


def build_survey_parser(add_help: bool = True) -> argparse.ArgumentParser:
    """Build parser for the survey subcommand."""
    parser = argparse.ArgumentParser(
        description="Survey LCATS corpora files for issues.",
        add_help=add_help,
        epilog=output.TSV_VALUE_LEGEND,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "directories",
        nargs="*",
        default=["data/"],
        help="Directories or files to survey.",
    )
    parser.add_argument(
        "--mode",
        choices=["qa", "specials"],
        default="qa",
        help=(
            "Survey mode. Use qa (default) for normal checks, or specials to "
            "default to special-character extraction."
        ),
    )
    parser.add_argument(
        "--check-for",
        action="append",
        default=[],
        help=(
            "Check(s) to run. Repeatable or comma-separated. "
            "Currently supported: special-characters,boundary-contamination"
        ),
    )
    parser.add_argument("--print-clean-filenames", action="store_true")
    parser.add_argument(
        "--extract-script",
        default="scripts/utils/extract_special_chars.py",
        help="Legacy compatibility option; modern survey uses in-process extraction.",
    )
    parser.add_argument("--allowlist-config", default="")
    parser.add_argument("--allow-smart", dest="allow_smart", action="store_true")
    parser.add_argument("--no-allow-smart", dest="allow_smart", action="store_false")
    parser.set_defaults(allow_smart=True)
    parser.add_argument("--context", type=int, default=10)
    parser.add_argument("--nocontext", action="store_true")
    parser.add_argument("--name-width", type=int, default=0)
    parser.add_argument(
        "--identifier",
        choices=output.IDENTIFIER_FIELDS,
        default=output.DEFAULT_IDENTIFIER_FIELD,
        help=(
            "Identifier shown in TSV reports. "
            "Defaults to path; choose filename or title for alternate emphasis."
        ),
    )
    parser.add_argument(
        "--unicode-name-width",
        type=int,
        default=output.DEFAULT_TSV_UNICODE_NAME_WIDTH,
        help=(
            "Maximum Unicode name width for TSV shown on a TTY. "
            "Set 0 to disable truncation."
        ),
    )
    parser.add_argument("--header", dest="header", action="store_true")
    parser.add_argument("--no-header", dest="header", action="store_false")
    parser.set_defaults(header=None)
    parser.add_argument(
        "--format", choices=["human", "tsv"], default=output.DEFAULT_OUTPUT_FORMAT
    )
    parser.add_argument("--output", default="")
    parser.add_argument("--progress", dest="progress", action="store_true")
    parser.add_argument("--no-progress", dest="progress", action="store_false")
    parser.set_defaults(progress=None)
    parser.add_argument("--exclude-codepoint", action="append", default=[])
    parser.add_argument("--exclude-char", action="append", default=[])
    return parser


def build_stats_parser(add_help: bool = True) -> argparse.ArgumentParser:
    """Build parser for the stats subcommand."""
    parser = argparse.ArgumentParser(
        description="Compute LCATS corpus statistics.",
        add_help=add_help,
    )
    parser.add_argument("directories", nargs="*", default=["data/"])
    parser.add_argument("--dedupe", dest="dedupe", action="store_true")
    parser.add_argument("--no-dedupe", dest="dedupe", action="store_false")
    parser.set_defaults(dedupe=True)
    parser.add_argument("--story-output", default="")
    parser.add_argument("--author-output", default="")
    return parser


def _show_progress(progress_arg: Optional[bool]) -> bool:
    if progress_arg is not None:
        return progress_arg
    return sys.stderr.isatty()


def survey_file(file_path: pathlib.Path, args) -> list[dict[str, str]]:
    """Run enabled checks on a single corpus file and return report rows."""
    data = read_story_data(file_path)
    story_title = infer_story_title(data, file_path)
    story_text = coerce_story_text(data.get("body", ""))
    rows = []
    for check_name in args.check_for:
        if check_name == "special-characters":
            parsed = output.parse_special_character_rows(
                run_special_characters_check(
                    displayed_text=story_text,
                    extract_script=args.extract_script,
                    allow_smart=args.allow_smart,
                    allowlist_config=args.allowlist_config,
                    excluded_codepoints=args.exclude_codepoint,
                    excluded_chars=args.exclude_char,
                    context=args.context,
                    nocontext=args.nocontext,
                    name_width=args.name_width,
                    header=False,
                ),
                file_path,
                story_title,
            )
            rows.extend(parsed)
        elif check_name == "boundary-contamination":
            findings = qa.run_detectors(
                story_text,
                config={
                    "detectors": [boundary.StartDetector(), boundary.EndDetector()]
                },
            )
            rows.extend(
                output.finding_to_row(file_path, story_title, check_name, finding)
                for finding in findings
            )
        else:
            raise ValueError(f"Unsupported check: {check_name}")
    return rows


def run_survey(
    argv: Optional[Sequence[str]] = None,
    parsed_args: Optional[argparse.Namespace] = None,
) -> int:
    """Run survey subcommand."""
    parser = build_survey_parser()
    args = parsed_args if parsed_args is not None else parser.parse_args(argv)
    if args.context < 0:
        parser.error("--context must be >= 0")
    if args.name_width < 0:
        parser.error("--name-width must be >= 0")
    if args.unicode_name_width < 0:
        parser.error("--unicode-name-width must be >= 0")

    if args.mode == "specials" and not args.check_for:
        args.check_for = ["special-characters"]

    args.check_for = parse_csv_args(args.check_for) or list(qa.DEFAULT_CHECKS)
    args.exclude_codepoint = list(unicode.DEFAULT_EXCLUDED_CODEPOINTS) + parse_csv_args(
        args.exclude_codepoint
    )
    args.exclude_char = list(unicode.DEFAULT_EXCLUDED_CHARS) + parse_csv_args(
        args.exclude_char
    )

    had_findings = False
    output_stream = sys.stdout
    try:
        files_found = list(discovery.find_json_files(args.directories))
        if args.output:
            output_stream = pathlib.Path(args.output).open(
                "w", encoding="utf-8", newline=""
            )

        header_enabled = (
            args.header if args.header is not None else args.format == "tsv"
        )
        tsv_writer = None
        if args.format == "tsv":
            tsv_writer = csv.DictWriter(
                output_stream,
                fieldnames=output.TSV_COLUMNS,
                delimiter="\t",
                extrasaction="ignore",
            )
            if header_enabled:
                tsv_writer.writeheader()

        for file_path in tqdm.tqdm(
            files_found, disable=not _show_progress(args.progress)
        ):
            rows = survey_file(file_path, args)
            if rows:
                had_findings = True
                if args.format == "tsv":
                    human_tsv = output_stream is sys.stdout and output_stream.isatty()
                    for row in rows:
                        if human_tsv:
                            formatted_row = output.compact_human_tsv_row(
                                row,
                                identifier=args.identifier,
                                unicode_name_width=args.unicode_name_width,
                            )
                        else:
                            formatted_row = output.with_identifier(
                                row, identifier=args.identifier
                            )
                        tsv_writer.writerow(formatted_row)
                else:
                    output.write_human_rows(output_stream, file_path, rows)
            elif args.print_clean_filenames:
                if args.format == "tsv":
                    clean_row = output.with_identifier(
                        output.clean_row(file_path, read_story_title(file_path)),
                        identifier=args.identifier,
                    )
                    if output_stream is sys.stdout and output_stream.isatty():
                        clean_row = output.compact_human_tsv_row(
                            clean_row,
                            identifier=args.identifier,
                            unicode_name_width=args.unicode_name_width,
                        )
                    tsv_writer.writerow(clean_row)
                else:
                    print(f"{file_path} [clean]", file=output_stream)

        return 1 if had_findings else 0
    except BrokenPipeError:
        return 141
    except Exception as exception:  # noqa: BLE001
        print(f"error: {exception}", file=sys.stderr)
        return 2
    finally:
        if output_stream is not sys.stdout:
            output_stream.close()


def run_stats(
    argv: Optional[Sequence[str]] = None,
    parsed_args: Optional[argparse.Namespace] = None,
) -> int:
    """Run stats subcommand."""
    parser = build_stats_parser()
    args = parsed_args if parsed_args is not None else parser.parse_args(argv)
    files = []
    for directory in args.directories:
        if pathlib.Path(directory).is_dir():
            files.extend(
                discovery.find_corpus_stories(
                    directory, ignore_dir_names=("cache",), sort=True
                )
            )
        elif pathlib.Path(directory).suffix == ".json":
            files.append(pathlib.Path(directory))

    story_stats, author_stats = stats.compute_corpus_stats(files, dedupe=args.dedupe)
    if args.story_output:
        story_stats.to_csv(args.story_output, sep="\t", index=False)
    else:
        print(story_stats.to_csv(sep="\t", index=False), end="")

    if args.author_output:
        author_stats.to_csv(args.author_output, sep="\t", index=False)
    else:
        print(author_stats.to_csv(sep="\t", index=False), end="")
    return 0
