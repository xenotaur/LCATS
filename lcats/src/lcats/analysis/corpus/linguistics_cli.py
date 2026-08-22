"""CLI wrapper for standalone linguistic sidecar generation."""

from __future__ import annotations

import argparse
import pathlib
import sys

from lcats.analysis.linguistics import runner, sidecar


def build_parser(add_help: bool = True) -> argparse.ArgumentParser:
    """Build parser for the linguistics command."""
    parser = argparse.ArgumentParser(
        description=(
            "Analyze LCATS stories with an NLP backend and write compact "
            "linguistics.json sidecars."
        ),
        add_help=add_help,
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=pathlib.Path,
        help="Story.json files, story buckets, collection directories, or corpus roots.",
    )
    parser.add_argument(
        "--story-list",
        action="append",
        type=pathlib.Path,
        default=[],
        help="Text file listing story paths or bucket directories, one per line.",
    )
    parser.add_argument(
        "--backend",
        choices=["spacy", "stanza", "fake"],
        default="spacy",
        help="NLP backend to use (default: spacy).",
    )
    parser.add_argument(
        "--model",
        default="",
        help="Backend model name or language code (default: backend default).",
    )
    parser.add_argument(
        "--include-token-detail",
        action="store_true",
        help="Also write linguistics.tokens.json with normalized token records.",
    )
    parser.add_argument(
        "--existing",
        choices=[
            runner.EXISTING_SKIP,
            runner.EXISTING_VALIDATE,
            runner.EXISTING_OVERWRITE,
        ],
        default=runner.EXISTING_SKIP,
        help="Behavior when linguistics.json already exists (default: skip).",
    )
    parser.add_argument(
        "--summary-output",
        type=pathlib.Path,
        help="Optional path for a machine-readable JSON run summary.",
    )
    parser.add_argument(
        "--output-root",
        type=pathlib.Path,
        help=(
            "Optional root directory for redirected sidecars. By default, "
            "outputs are written beside each story.json."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve inputs and report what would run without writing sidecars.",
    )
    return parser


def run(argv=None, parsed_args=None) -> int:
    """Run lcats linguistics and return a process status code."""
    parser = build_parser()
    args = parsed_args if parsed_args is not None else parser.parse_args(argv)
    try:
        resolved = runner.resolve_story_inputs(
            args.inputs, story_list_files=args.story_list
        )
        if not resolved.story_paths and not resolved.missing_paths:
            print(
                "error: no stories resolved; provide story paths, story buckets, "
                "directories, or --story-list",
                file=sys.stderr,
            )
            return 1
        model_name = args.model or ("en" if args.backend == "stanza" else "")
        options = sidecar.LinguisticsOptions(
            backend_name=args.backend,
            model_name=model_name,
            include_token_detail=args.include_token_detail,
        )
        backend = (
            None if args.dry_run else runner.make_backend(args.backend, model_name)
        )
        if backend is None:
            from lcats.analysis.event_role_world import nlp_backend

            backend = nlp_backend.FakeNLPBackend()
        summary = runner.run(
            resolved.story_paths,
            backend=backend,
            options=options,
            existing=args.existing,
            dry_run=args.dry_run,
            output_root=args.output_root,
        )
        summary = runner.with_prepended_results(
            summary, runner.missing_input_results(resolved.missing_paths)
        )
        summary_text = sidecar.dumps_json(summary.to_dict())
        if args.summary_output:
            sidecar.write_json_atomic(args.summary_output, summary.to_dict())
        else:
            print(summary_text, end="")
        for result in summary.results:
            if result.status == runner.STATUS_FAILED:
                print(
                    f"error: {result.story_path}: {result.message}",
                    file=sys.stderr,
                )
        return 0 if summary.clean else 1
    except BrokenPipeError:
        return 141
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 2
