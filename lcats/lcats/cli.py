"""Command-line interface for the Literary Captain's Advisory Tool System (LCATS)."""

import argparse
import sys

from lcats.analysis.corpus import cli as corpus_cli
import lcats.gatherers.main
import lcats.inspect


TOP_LEVEL_DESCRIPTION = (
    "LCATS is a literary case-based reasoning toolkit for gathering, inspecting, "
    "surveying, and analyzing corpora."
)
TOP_LEVEL_EPILOG = (
    "Run 'lcats <command> --help' for more information.\n"
    "You can also use 'lcats help <command>'."
)


def _handle_info(_args):
    return "LCATS is a literary case based reasoning system.", 0


def _handle_gather(args):
    return lcats.gatherers.main.run(args.gatherers, dry_run=args.dry_run)


def _handle_inspect(args):
    return lcats.inspect.inspect_files(*args.files)


def _handle_display(args):
    return lcats.inspect.display_files(*args.files)


def _handle_survey(args):
    return "", corpus_cli.run_survey(parsed_args=args)


def _handle_stats(args):
    return "", corpus_cli.run_stats(parsed_args=args)


def _handle_index(_args):
    return "Indexing data files is not yet implemented.", 1


def _handle_advise(_args):
    return "Getting advice from LCATS is not yet implemented.", 1


def _handle_eval(_args):
    return "Evaluating LCATS is not yet implemented.", 1


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level LCATS command parser."""
    parser = argparse.ArgumentParser(
        prog="lcats",
        description=TOP_LEVEL_DESCRIPTION,
        epilog=TOP_LEVEL_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    command_parsers = {}

    help_parser = subparsers.add_parser(
        "help",
        help="Display top-level or command-specific help.",
        description="Display LCATS help, including command-specific help.",
    )
    help_parser.add_argument(
        "topic",
        nargs="?",
        help="Optional command name, for example: lcats help survey",
    )
    command_parsers["help"] = help_parser

    info_parser = subparsers.add_parser(
        "info",
        help="Describe LCATS.",
        description="Describe LCATS, the literary captain's advisory tool system.",
    )
    info_parser.add_argument("args", nargs=argparse.REMAINDER)
    info_parser.set_defaults(handler=_handle_info)
    command_parsers["info"] = info_parser

    gather_parser = subparsers.add_parser(
        "gather",
        help="Gather corpus data to a local database.",
        description="Gather one or more configured corpora.",
    )
    gather_parser.add_argument(
        "gatherers",
        nargs="*",
        help="Optional gatherer names. Defaults to all gatherers.",
    )
    gather_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which gatherers would run without executing downloads.",
    )
    gather_parser.set_defaults(handler=_handle_gather)
    command_parsers["gather"] = gather_parser

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Summarize one or more story JSON files.",
        description="Inspect one or more story JSON files and print summaries.",
    )
    inspect_parser.add_argument("files", nargs="*")
    inspect_parser.set_defaults(handler=_handle_inspect)
    command_parsers["inspect"] = inspect_parser

    display_parser = subparsers.add_parser(
        "display",
        help="Display full story JSON content.",
        description="Display one or more story JSON files in human-readable form.",
    )
    display_parser.add_argument("files", nargs="*")
    display_parser.set_defaults(handler=_handle_display)
    command_parsers["display"] = display_parser

    survey_parent = corpus_cli.build_survey_parser(add_help=False)
    survey_parser = subparsers.add_parser(
        "survey",
        parents=[survey_parent],
        help="Survey corpus files for quality issues.",
        description=(
            "Survey LCATS corpus JSON files for quality issues such as special "
            "characters and boundary contamination."
        ),
        epilog=(
            "Examples:\n"
            "  lcats survey --mode specials corpora/sherlock\n"
            "  lcats survey corpora/sherlock --check-for special-characters\n"
            "  lcats survey data/ --format tsv --output findings.tsv\n"
            "  lcats survey corpora/sherlock --no-progress --print-clean-filenames"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    survey_parser.set_defaults(handler=_handle_survey)
    command_parsers["survey"] = survey_parser

    stats_parent = corpus_cli.build_stats_parser(add_help=False)
    stats_parser = subparsers.add_parser(
        "stats",
        parents=[stats_parent],
        help="Compute corpus-level statistics.",
        description=(
            "Compute story-level and author-level statistics for one or more "
            "corpus directories or JSON files."
        ),
        epilog=(
            "Examples:\n"
            "  lcats stats corpora/sherlock\n"
            "  lcats stats data/ --no-dedupe\n"
            "  lcats stats data/ --story-output story_stats.tsv --author-output author_stats.tsv"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    stats_parser.set_defaults(handler=_handle_stats)
    command_parsers["stats"] = stats_parser

    index_parser = subparsers.add_parser(
        "index",
        help="Preprocess a corpus for question answering.",
        description="Preprocess a corpus to answer questions.",
    )
    index_parser.set_defaults(handler=_handle_index)
    command_parsers["index"] = index_parser

    advise_parser = subparsers.add_parser(
        "advise",
        help="Run the LCATS advising tool.",
        description="Run the LCATS command-line advising tool.",
    )
    advise_parser.set_defaults(handler=_handle_advise)
    command_parsers["advise"] = advise_parser

    eval_parser = subparsers.add_parser(
        "eval",
        help="Evaluate LCATS on benchmark suites.",
        description="Evaluate LCATS on a benchmark suite.",
    )
    eval_parser.set_defaults(handler=_handle_eval)
    command_parsers["eval"] = eval_parser

    def _handle_help(args):
        if not args.topic:
            return parser.format_help(), 0
        topic_parser = command_parsers.get(args.topic)
        if topic_parser is None:
            return f"Unknown command: {args.topic}", 1
        return topic_parser.format_help(), 0

    help_parser.set_defaults(handler=_handle_help)
    parser.command_parsers = command_parsers
    return parser


def usage() -> str:
    """Return the top-level LCATS help text."""
    return build_parser().format_help()


def dispatch(command, args):
    """Dispatch a command and list of arguments using the configured parser."""
    parser = build_parser()
    argv = [command, *args]
    if command in parser.command_parsers and command != "help":
        parsed = parser.command_parsers[command].parse_args(args)
        parsed.command = command
    else:
        parsed = parser.parse_args(argv)
    handler = getattr(parsed, "handler", None)
    if handler is None:
        return parser.format_help(), 1
    return handler(parsed)


def main(argv=None):
    """Main entry point for the LCATS command-line interface."""
    parser = build_parser()
    argv = list(argv) if argv is not None else sys.argv[1:]

    if not argv:
        print(parser.format_help())
        sys.exit(1)

    if argv[0] in parser.command_parsers and argv[0] != "help":
        parsed = parser.command_parsers[argv[0]].parse_args(argv[1:])
        parsed.command = argv[0]
    else:
        parsed = parser.parse_args(argv)

    result, status = parsed.handler(parsed)
    if result:
        print(result)
    sys.exit(status)


if __name__ == "__main__":
    main()
