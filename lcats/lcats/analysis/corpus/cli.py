"""CLI helpers for corpus survey and stats subcommands."""

import argparse
import csv
import json
import pathlib
import subprocess
import sys

from typing import Optional, Sequence

import lcats.inspect
import tqdm

from lcats.analysis.corpus import discovery
from lcats.analysis.corpus import output
from lcats.analysis.corpus import qa
from lcats.analysis.corpus import stats
from lcats.analysis.corpus.detectors import boundary
from lcats.analysis.corpus.detectors import unicode


def run_lcats_display(file_path: pathlib.Path) -> str:
    """Render one corpus JSON file using the same formatter as lcats display."""
    with file_path.open("r", encoding="utf-8") as json_file:
        data = json.load(json_file)
    rendered = lcats.inspect.format_story_json(data, max_body_chars=None, width=80)
    return f"{rendered}\n"


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
    command = [extract_script]
    if allow_smart:
        command.append("--allow-smart")
    if allowlist_config:
        command.append(f"--allowlist-config={allowlist_config}")
    if excluded_codepoints:
        command.append("--exclude-codepoint=" + ",".join(excluded_codepoints))
    if excluded_chars:
        command.append("--exclude-char=" + ",".join(excluded_chars))
    if nocontext:
        command.append("--nocontext")
    else:
        command.append(f"--context={context}")
    if name_width > 0:
        command.append(f"--name-width={name_width}")
    if header:
        command.append("--header")

    result = subprocess.run(
        command,
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
            "Currently supported: special-characters,boundary-contamination"
        ),
    )
    parser.add_argument("--print-clean-filenames", action="store_true")
    parser.add_argument(
        "--extract-script", default="scripts/utils/extract_special_chars.py"
    )
    parser.add_argument("--allowlist-config", default="")
    parser.add_argument("--allow-smart", dest="allow_smart", action="store_true")
    parser.add_argument("--no-allow-smart", dest="allow_smart", action="store_false")
    parser.set_defaults(allow_smart=True)
    parser.add_argument("--context", type=int, default=10)
    parser.add_argument("--nocontext", action="store_true")
    parser.add_argument("--name-width", type=int, default=0)
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
    displayed_text = run_lcats_display(file_path)
    rows = []
    for check_name in args.check_for:
        if check_name == "special-characters":
            parsed = output.parse_special_character_rows(
                run_special_characters_check(
                    displayed_text=displayed_text,
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
            )
            rows.extend(parsed)
        elif check_name == "boundary-contamination":
            findings = qa.run_detectors(
                displayed_text,
                config={
                    "detectors": [boundary.StartDetector(), boundary.EndDetector()]
                },
            )
            rows.extend(
                output.finding_to_row(file_path, check_name, finding)
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
                    for row in rows:
                        tsv_writer.writerow(row)
                else:
                    output.write_human_rows(output_stream, file_path, rows)
            elif args.print_clean_filenames:
                if args.format == "tsv":
                    tsv_writer.writerow(output.clean_row(file_path))
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
