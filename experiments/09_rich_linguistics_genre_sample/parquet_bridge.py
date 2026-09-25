"""Parquet bridge for experiment-09 rich token-detail artifacts.

The canonical LCATS artifact is still ``linguistics.tokens.json``. This module
adds an experiment-scoped columnar export that can be used for fast statistics
and restored to canonical JSON for existing validators and downstream tools.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Iterable

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "lcats" / "src"))

from lcats.analysis.linguistics import lexicon, sidecar  # noqa: E402

STORIES_FILENAME = "token_detail_stories.parquet"
SENTENCES_FILENAME = "token_detail_sentences.parquet"
TOKENS_FILENAME = "token_detail_tokens.parquet"
MANIFEST_FILENAME = "parquet_manifest.json"
REQUIRED_PARQUET_FILES = (STORIES_FILENAME, SENTENCES_FILENAME, TOKENS_FILENAME)


def export_token_details(
    *,
    source_root: pathlib.Path,
    output_dir: pathlib.Path,
) -> dict[str, Any]:
    """Export v2 token-detail JSON files under ``source_root`` to Parquet."""
    pd = _pandas()
    source_root = pathlib.Path(source_root)
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    story_rows: list[dict[str, Any]] = []
    sentence_rows: list[dict[str, Any]] = []
    token_rows: list[dict[str, Any]] = []
    token_detail_paths = sorted(source_root.glob("**/linguistics.tokens.json"))
    for story_order, detail_path in enumerate(token_detail_paths, start=1):
        detail = sidecar.load_json(detail_path)
        if detail.get("schema_version") != sidecar.DETAIL_V2_SCHEMA_VERSION:
            raise ValueError(f"{detail_path}: expected token-detail-v2")
        story_key = str(detail["lcats_id"])
        compact_path = detail_path.parent / sidecar.SIDECAR_FILENAME
        compact_json = (
            sidecar.dumps_json(sidecar.load_json(compact_path))
            if compact_path.exists()
            else ""
        )
        story_rows.append(
            {
                "story_order": story_order,
                "story_key": story_key,
                "lcats_id": detail["lcats_id"],
                "story_path": detail["story_path"],
                "detail_relative_path": _relative_to(detail_path, source_root),
                "compact_relative_path": _relative_to(compact_path, source_root),
                "compact_json": compact_json,
                "extractor_json": _json_cell(detail.get("extractor", {})),
                "backend_json": _json_cell(detail.get("backend", {})),
                "input_json": _json_cell(detail.get("input", {})),
                "options_json": _json_cell(detail.get("options", {})),
                "source_json": _json_cell(detail.get("source", {})),
                "provenance_json": _json_cell(detail.get("provenance", {})),
            }
        )
        for sentence in detail.get("sentences", []):
            if not isinstance(sentence, dict):
                continue
            sentence_index = sentence.get("sentence_index")
            sentence_rows.append(
                {
                    "story_key": story_key,
                    "sentence_index": sentence_index,
                    "start_char": sentence.get("start_char"),
                    "end_char": sentence.get("end_char"),
                }
            )
            for token in sentence.get("tokens", []):
                if not isinstance(token, dict):
                    continue
                token_rows.append(
                    {
                        "story_key": story_key,
                        "sentence_index": sentence_index,
                        "token_index": token.get("token_index"),
                        "global_token_index": token.get("global_token_index"),
                        "start_char": token.get("start_char"),
                        "end_char": token.get("end_char"),
                        "text": token.get("text", ""),
                        "lemma": token.get("lemma", ""),
                        "upos": token.get("upos", ""),
                        "xpos": token.get("xpos", ""),
                        "feats": token.get("feats", ""),
                        "head_index": token.get("head_index"),
                        "deprel": token.get("deprel", ""),
                    }
                )

    _write_parquet(pd.DataFrame(story_rows), output_dir / STORIES_FILENAME)
    _write_parquet(pd.DataFrame(sentence_rows), output_dir / SENTENCES_FILENAME)
    _write_parquet(pd.DataFrame(token_rows), output_dir / TOKENS_FILENAME)
    manifest = {
        "schema_version": "rich-linguistics-token-detail-parquet-v1",
        "source_root": source_root.as_posix(),
        "story_count": len(story_rows),
        "sentence_count": len(sentence_rows),
        "token_count": len(token_rows),
        "files": {
            filename: {
                "path": (output_dir / filename).as_posix(),
                "sha256": _sha256_file(output_dir / filename),
                "bytes": (output_dir / filename).stat().st_size,
            }
            for filename in REQUIRED_PARQUET_FILES
        },
    }
    sidecar.write_json_atomic(output_dir / MANIFEST_FILENAME, manifest)
    return manifest


def restore_token_details(
    *,
    parquet_dir: pathlib.Path,
    output_root: pathlib.Path,
    include_compact: bool = True,
    include_lexicon: bool = True,
) -> dict[str, Any]:
    """Restore canonical JSON artifacts from an experiment Parquet export."""
    pd = _pandas()
    parquet_dir = pathlib.Path(parquet_dir)
    output_root = pathlib.Path(output_root)
    stories = pd.read_parquet(parquet_dir / STORIES_FILENAME)
    sentences = pd.read_parquet(parquet_dir / SENTENCES_FILENAME)
    tokens = pd.read_parquet(parquet_dir / TOKENS_FILENAME)
    restored_details = 0
    restored_compact = 0
    restored_lexicons = 0
    for story in stories.sort_values("story_order").to_dict("records"):
        story_key = story["story_key"]
        story_dir = output_root.joinpath(*pathlib.PurePosixPath(story_key).parts)
        story_dir.mkdir(parents=True, exist_ok=True)
        detail = {
            "schema_version": sidecar.DETAIL_V2_SCHEMA_VERSION,
            "lcats_id": story["lcats_id"],
            "story_path": story["story_path"],
            "extractor": _load_json_cell(story["extractor_json"]),
            "backend": _load_json_cell(story["backend_json"]),
            "input": _load_json_cell(story["input_json"]),
            "options": _load_json_cell(story["options_json"]),
            "source": _load_json_cell(story["source_json"]),
            "provenance": _load_json_cell(story["provenance_json"]),
            "sentences": [],
        }
        story_sentences = sentences[sentences["story_key"] == story_key]
        story_tokens = tokens[tokens["story_key"] == story_key]
        for sentence in story_sentences.sort_values("sentence_index").to_dict("records"):
            sentence_index = _int_or_none(sentence["sentence_index"])
            token_rows = story_tokens[
                story_tokens["sentence_index"] == sentence["sentence_index"]
            ]
            detail["sentences"].append(
                {
                    "sentence_index": sentence_index,
                    "start_char": _int_or_none(sentence["start_char"]),
                    "end_char": _int_or_none(sentence["end_char"]),
                    "tokens": [
                        _token_from_row(token)
                        for token in token_rows.sort_values("token_index").to_dict(
                            "records"
                        )
                    ],
                }
            )
        sidecar.write_json_atomic(story_dir / sidecar.TOKEN_DETAIL_FILENAME, detail)
        restored_details += 1
        compact_json = _optional_json_cell(story.get("compact_json"))
        if include_compact and compact_json:
            sidecar.write_json_atomic(
                story_dir / sidecar.SIDECAR_FILENAME, json.loads(compact_json)
            )
            restored_compact += 1
        if include_lexicon:
            sidecar.write_json_atomic(
                story_dir / lexicon.LEXICON_FILENAME, lexicon.build_lexicon(detail)
            )
            restored_lexicons += 1
    return {
        "schema_version": "rich-linguistics-token-detail-parquet-restore-v1",
        "parquet_dir": parquet_dir.as_posix(),
        "output_root": output_root.as_posix(),
        "restored_token_details": restored_details,
        "restored_compact_sidecars": restored_compact,
        "restored_lexicons": restored_lexicons,
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the Parquet bridge CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    export = subparsers.add_parser("export", help="export token details to Parquet")
    export.add_argument("source_root", type=pathlib.Path)
    export.add_argument("output_dir", type=pathlib.Path)
    restore = subparsers.add_parser("restore", help="restore token details from Parquet")
    restore.add_argument("parquet_dir", type=pathlib.Path)
    restore.add_argument("output_root", type=pathlib.Path)
    restore.add_argument("--no-compact", action="store_true")
    restore.add_argument("--no-lexicon", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the Parquet bridge CLI."""
    args = build_parser().parse_args(argv)
    try:
        if args.command == "export":
            result = export_token_details(
                source_root=args.source_root, output_dir=args.output_dir
            )
        else:
            result = restore_token_details(
                parquet_dir=args.parquet_dir,
                output_root=args.output_root,
                include_compact=not args.no_compact,
                include_lexicon=not args.no_lexicon,
            )
    except Exception as error:  # noqa: BLE001
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _write_parquet(frame: Any, path: pathlib.Path) -> None:
    frame.to_parquet(path, engine="pyarrow", compression="zstd", index=False)


def _pandas() -> Any:
    try:
        import pandas as pd
        import pyarrow  # noqa: F401
    except ImportError as error:
        raise RuntimeError(
            "Parquet export requires pandas and pyarrow; install pyarrow or use "
            "the canonical JSON artifacts"
        ) from error
    return pd


def _json_cell(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_json_cell(value: Any) -> Any:
    return json.loads(value if isinstance(value, str) else "{}")


def _optional_json_cell(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _token_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "token_index": _int_or_none(row["token_index"]),
        "global_token_index": _int_or_none(row["global_token_index"]),
        "start_char": _int_or_none(row["start_char"]),
        "end_char": _int_or_none(row["end_char"]),
        "text": _string_or_empty(row["text"]),
        "lemma": _string_or_empty(row["lemma"]),
        "upos": _string_or_empty(row["upos"]),
        "xpos": _string_or_empty(row["xpos"]),
        "feats": _string_or_empty(row["feats"]),
        "head_index": _int_or_none(row["head_index"]),
        "deprel": _string_or_empty(row["deprel"]),
    }


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        if value != value:
            return None
    except TypeError:
        pass
    return int(value)


def _string_or_empty(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _relative_to(path: pathlib.Path, root: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _sha256_file(path: pathlib.Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
