"""CLI wrapper for lcats annotate (genre + scene sidecar generation)."""

import argparse
import os
import pathlib
import sys

from lcats.analysis.corpus import annotate
from lcats.utils import checkpoint, env
from lcats.utils import run_log


def build_parser(add_help: bool = True) -> argparse.ArgumentParser:
    """Build parser for the annotate command."""
    parser = argparse.ArgumentParser(
        description=(
            "Annotate data/ story buckets with genre.json/scenes.json "
            "sidecars plus a per-bucket README.md, via the mature lcats "
            "assess (genre) and scene_analysis (segmentation) extractors."
        ),
        add_help=add_help,
    )
    parser.add_argument(
        "collections",
        nargs="*",
        help="Collection names to annotate. Defaults to every collection under --source.",
    )
    parser.add_argument(
        "--source",
        type=pathlib.Path,
        default=env.data_root(),
        help="Root directory of source collections (default: data/).",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=pathlib.Path,
        default=pathlib.Path(".annotate_checkpoints"),
        help=(
            "Directory for checkpoint bookkeeping (default: "
            ".annotate_checkpoints/). Never data/, corpora/, or cache/ -- "
            "those are wiped by lcats clean / disposable by design."
        ),
    )
    parser.add_argument(
        "--model",
        default="claude-opus-4-8",
        help="Claude model to use for both genre and segmentation (default: claude-opus-4-8).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List story buckets that would be annotated without calling the API.",
    )
    return parser


def run(argv=None, parsed_args=None) -> int:
    """Run lcats annotate. Returns 0 if every considered story annotated cleanly."""
    parser = build_parser()
    args = parsed_args if parsed_args is not None else parser.parse_args(argv)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not args.dry_run and not api_key:
        print(
            "error: ANTHROPIC_API_KEY environment variable is not set.\n"
            "       Set it or use --dry-run to preview without API calls.",
            file=sys.stderr,
        )
        return 1

    collection_names = args.collections or None
    if args.dry_run:
        names = collection_names or sorted(
            entry.name for entry in args.source.iterdir() if entry.is_dir()
        )
        for name in names:
            from lcats.analysis.corpus import discovery

            for story_path in discovery.iter_collection_story_files(args.source / name):
                print(f"{name}/{story_path.parent.name}")
        return 0

    try:
        from lcats.llm import anthropic_backend

        backend = anthropic_backend.AnthropicBackend(api_key=api_key)
        roots = checkpoint.resolve_roots(
            working_root=args.checkpoint_dir, source_root=args.source
        )

        # log path lives under the existing --checkpoint-dir (reusing the
        # same roots already resolved above) - annotate has real per-item
        # checkpointing but no ordered, human-readable trail on top of it
        # (WI-RUNLOG-0082).
        with run_log.RunLog(
            roots,
            "annotate_run_log.jsonl",
            model=args.model,
            source=str(args.source),
        ) as log:
            results = annotate.annotate_collections(
                args.source,
                backend=backend,
                model=args.model,
                roots=roots,
                log=log,
                collection_names=collection_names,
            )

        all_clean = True
        for collection_name, story_results in results.items():
            for result in story_results:
                if not result.clean:
                    all_clean = False
                    print(
                        f"error: {collection_name}/{result.story_path.parent.name}: "
                        f"genre_error={result.genre_error!r} scenes_error={result.scenes_error!r}",
                        file=sys.stderr,
                    )
        return 0 if all_clean else 1
    except BrokenPipeError:
        return 141
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 2
