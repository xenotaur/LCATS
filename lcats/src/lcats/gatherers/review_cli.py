"""Local CLI for inspecting and explicitly reviewing saved gather candidates."""

import argparse
import json

from lcats.gatherers import candidate_review
from lcats.gatherers import review_store


def build_parser(*, add_help=True):
    """Build the standalone/nested review CLI with no catalog or network options."""
    parser = argparse.ArgumentParser(
        prog="lcats gather-review", add_help=add_help, description=__doc__
    )
    commands = parser.add_subparsers(dest="review_command", required=True)
    listing = commands.add_parser(
        "list", help="List saved candidates and explicit disposition states."
    )
    listing.add_argument(
        "candidates", nargs="?", default=str(review_store.DEFAULT_DIRECTORY)
    )
    listing.add_argument(
        "--dispositions", help="Optional directory of immutable disposition records."
    )
    show = commands.add_parser(
        "show", help="Preview exact candidate text with character offsets."
    )
    show.add_argument("candidate")
    show.add_argument("--start", type=int, default=0)
    show.add_argument("--end", type=int)
    record = commands.add_parser(
        "record", help="Record an explicit approve/exclude/defer disposition."
    )
    record.add_argument("candidate")
    record.add_argument(
        "--outcome", choices=("approve", "exclude", "defer"), required=True
    )
    record.add_argument("--reviewer", required=True)
    record.add_argument("--rationale", required=True)
    record.add_argument("--start", type=int)
    record.add_argument("--end", type=int)
    record.add_argument(
        "--directory", default=str(candidate_review.DEFAULT_DISPOSITIONS)
    )
    export = commands.add_parser(
        "export",
        help="Export explicitly named approvals for gather --review-decisions.",
    )
    export.add_argument("dispositions", nargs="+")
    export.add_argument("--candidates", required=True)
    export.add_argument("--output", required=True)
    return parser


def run(argv=None, *, parsed_args=None):
    """Return JSON and exit code; failures never acquire or publish a story."""
    args = parsed_args if parsed_args is not None else build_parser().parse_args(argv)
    try:
        if args.review_command == "list":
            result = candidate_review.inventory(
                args.candidates, dispositions=args.dispositions
            )
        elif args.review_command == "show":
            result = candidate_review.preview(
                args.candidate, start=args.start, end=args.end
            )
        elif args.review_command == "record":
            path = candidate_review.record_disposition(
                args.candidate,
                outcome=args.outcome,
                reviewer=args.reviewer,
                rationale=args.rationale,
                start=args.start,
                end=args.end,
                directory=args.directory,
            )
            result = {"disposition": path, "outcome": args.outcome, "published": False}
        else:
            path = candidate_review.export_approvals(
                args.dispositions, candidates=args.candidates, output=args.output
            )
            result = {
                "review_decisions": path,
                "published": False,
                "validation": "gather revalidates approvals against current sources",
            }
        # Escape source control characters in terminal output; never interpolate
        # source text as executable instructions or infer approval from it.
        return json.dumps(result, indent=2, ensure_ascii=True), 0
    except (OSError, ValueError) as exc:
        return f"Candidate review failed: {exc}", 2
