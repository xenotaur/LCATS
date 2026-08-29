"""CLI wrapper for promoting sidecars or collections from data/ into
corpora/. Only ``replace`` mode is survey-gated (special-character
mojibake survey); ``insert``/``upsert`` promote sidecars via a validated
manifest, without running that survey."""

import argparse
import pathlib
import sys

from lcats.analysis.corpus import promote
from lcats.utils import env


def _add_sidecar_manifest_args(subparser: argparse.ArgumentParser) -> None:
    """Shared insert/upsert argument set (WI-PROMOTE-0097/WI-PROMOTE-0100)."""
    subparser.add_argument(
        "--sidecar",
        required=True,
        help=(
            "Registered sidecar kind to promote (e.g. genre, scenes, "
            "linguistics, linguistics.tokens.json). A value with no '.' "
            "assumes '.json'; a value containing '.' is matched exactly "
            "against the registry, with no inference."
        ),
    )
    source_group = subparser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--tranche-manifest",
        type=pathlib.Path,
        default=None,
        help=(
            "Path to a JSONL manifest, one envelope object per line: "
            '{"lcats_id": "<destination story id>", "payload": {<sidecar '
            "content>}}. Promotes only these stories' sidecars into --dest, "
            "without touching any other file in their collection "
            "directories. Mutually exclusive with --source."
        ),
    )
    source_group.add_argument(
        "--source",
        type=pathlib.Path,
        default=None,
        help=(
            "Root directory to scan for existing "
            "<collection>/<story>/<sidecar-filename> files (e.g. data/), "
            "instead of reading a pre-built manifest -- every story bucket "
            "under this root that already has the named --sidecar file is "
            "promoted. Mutually exclusive with --tranche-manifest."
        ),
    )
    subparser.add_argument(
        "--dest",
        type=pathlib.Path,
        default=env.corpora_root(),
        help="Root directory to promote into (default: ../corpora).",
    )
    subparser.add_argument(
        "--allow-unvalidated",
        action="store_true",
        help=(
            "Allow promoting a --sidecar kind with no registered validator. "
            "Never bypasses a registered validator's own rejection of "
            "malformed content."
        ),
    )
    subparser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report without writing any files.",
    )


def build_parser(add_help: bool = True) -> argparse.ArgumentParser:
    """Build parser for the promote command.

    An explicit mode subcommand is mandatory (WI-PROMOTE-0097): a bare
    invocation with no mode refuses rather than defaulting to any
    behavior, closing the data-loss hazard between additive sidecar
    promotion and the wholesale collection-replacement path.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Promote sidecars or collections from data/ into corpora/. "
            "An explicit mode is required: insert (create-only), upsert "
            "(create-or-overwrite), or replace (wholesale collection "
            "replacement)."
        ),
        add_help=add_help,
    )
    mode_subparsers = parser.add_subparsers(
        dest="mode",
        required=True,
        help="Promotion mode.",
    )

    insert_parser = mode_subparsers.add_parser(
        "insert",
        help="Create-only: write named sidecars, refusing any that already exist.",
        description=(
            "Promote sidecars from a JSONL manifest into corpora/, "
            "creating only -- refuses (does not overwrite) any destination "
            "sidecar that already exists. Never touches any other file in "
            "the destination bucket or collection."
        ),
    )
    _add_sidecar_manifest_args(insert_parser)

    upsert_parser = mode_subparsers.add_parser(
        "upsert",
        help="Create-or-overwrite: write named sidecars, overwriting if present.",
        description=(
            "Promote sidecars from a JSONL manifest into corpora/, "
            "creating or overwriting the named sidecar file whole -- never "
            "merges content, and never touches or deletes any other file "
            "in the destination bucket or collection."
        ),
    )
    _add_sidecar_manifest_args(upsert_parser)

    replace_parser = mode_subparsers.add_parser(
        "replace",
        help="Wholesale-replace one or more collections with their data/ counterpart.",
        description=(
            "Promote data/ collections into corpora/, gated on a passing "
            "special-character survey. A collection with any mojibake "
            "finding is skipped and reported rather than promoted; clean "
            "collections wholesale-replace their corpora/ counterpart."
        ),
    )
    replace_parser.add_argument(
        "collections",
        nargs="*",
        help="Collection names to consider. Defaults to every collection under --source.",
    )
    replace_parser.add_argument(
        "--source",
        type=pathlib.Path,
        default=env.data_root(),
        help="Root directory of source collections (default: data/).",
    )
    replace_parser.add_argument(
        "--dest",
        type=pathlib.Path,
        default=env.corpora_root(),
        help="Root directory to promote clean collections into (default: ../corpora).",
    )
    replace_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Survey and report without copying any files.",
    )
    replace_parser.add_argument(
        "--allow-orphaned-sidecar-deletion",
        action="store_true",
        help=(
            "Allow replace to delete a registered sidecar kind that exists "
            "at the destination for a story but is missing from source. "
            "Without this flag, an otherwise-clean collection with any such "
            "orphaned sidecar is blocked and reported rather than "
            "promoted."
        ),
    )

    return parser


def _run_sidecar_mode(args, *, overwrite: bool) -> int:
    promote_fn = (
        promote.promote_sidecar_upsert if overwrite else promote.promote_sidecar_insert
    )
    report = promote_fn(
        manifest_path=args.tranche_manifest,
        dest_root=args.dest,
        sidecar=args.sidecar,
        scan_source=args.source,
        allow_unvalidated=args.allow_unvalidated,
        dry_run=args.dry_run,
    )
    for lcats_id in report.promoted:
        verb = "would promote" if args.dry_run else "promoted"
        print(f"{verb} sidecar: {lcats_id}")
    for finding in report.rejected:
        print(f"rejected: {finding.lcats_id}: {finding.error}", file=sys.stderr)
    return 0 if report.all_promoted else 1


def _run_replace_mode(args) -> int:
    collection_names = args.collections or None
    report = promote.promote_collections(
        source_root=args.source,
        dest_root=args.dest,
        collection_names=collection_names,
        dry_run=args.dry_run,
        allow_orphaned_sidecar_deletion=args.allow_orphaned_sidecar_deletion,
    )

    for name in report.promoted:
        verb = "would promote" if args.dry_run else "promoted"
        print(f"{verb}: {name} -> {promote.destination_name(name)}")

    for result in report.blocked:
        print(
            f"blocked: {result.collection} "
            f"({len(result.findings)} mojibake finding(s), "
            f"{len(result.sidecar_findings)} malformed sidecar(s), "
            f"{len(result.orphaned_sidecar_findings)} orphaned sidecar(s) "
            f"across {result.story_count} stories)",
            file=sys.stderr,
        )
        for finding in result.findings:
            print(
                f"  {finding.story_path}: {finding.codepoint} {finding.character!r} "
                f"context={finding.context!r}",
                file=sys.stderr,
            )
        for sidecar_finding in result.sidecar_findings:
            print(
                f"  {sidecar_finding.story_path}: {sidecar_finding.sidecar_name}: "
                f"{sidecar_finding.error}",
                file=sys.stderr,
            )
        for orphaned_finding in result.orphaned_sidecar_findings:
            print(
                f"  {orphaned_finding.lcats_id}: {orphaned_finding.sidecar_name} "
                "exists at destination but is missing from source -- pass "
                "--allow-orphaned-sidecar-deletion to delete it anyway",
                file=sys.stderr,
            )

    return 0 if report.all_promoted else 1


def run(argv=None, parsed_args=None) -> int:
    """Run promotion for the selected mode. ``replace`` is survey-gated
    (special-character mojibake survey); ``insert``/``upsert`` are not --
    they validate the manifest instead. Returns 0 if the run promoted
    cleanly."""
    parser = build_parser()
    args = parsed_args if parsed_args is not None else parser.parse_args(argv)

    try:
        if args.mode == "insert":
            return _run_sidecar_mode(args, overwrite=False)
        if args.mode == "upsert":
            return _run_sidecar_mode(args, overwrite=True)
        return _run_replace_mode(args)
    except BrokenPipeError:
        return 141
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(run())
