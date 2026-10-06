"""Stage genre.json sidecars whose cache_db_path is rewritten to a basename.

One-off cleanup for WI-GENRE-0109. The 146 genre.json files promoted by PR #362
carry an absolute, machine-specific ``assessments[*].provenance.cache_db_path``.
This script reads those sidecars and writes a JSONL tranche manifest of the
rewritten payloads, for review and promotion with::

    lcats promote upsert --sidecar genre --tranche-manifest <manifest> --dry-run

It never edits ``corpora/`` itself: promotion is a separate, human-approved step.

Usage (from the ``lcats/`` directory)::

    python tools/rewrite_genre_cache_db_path.py --corpora-dir ../corpora \
        --manifest-out /path/to/manifest.jsonl
"""

import argparse
import copy
import json
import pathlib
import re
import sys
from typing import Any

GENRE_SIDECAR_FILENAME = "genre.json"
_SEPARATORS = re.compile(r"[\\/]")


def to_basename(value: str) -> str:
    """Return the last path component of a POSIX or Windows style path."""
    return _SEPARATORS.split(value)[-1]


def rewrite_cache_db_path(sidecar: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Return a copy of ``sidecar`` with each cache_db_path reduced to a basename.

    Only ``assessments[*].provenance.cache_db_path`` string values that contain a
    path separator are changed. Everything else, including assessments with no
    ``provenance`` or no ``cache_db_path``, is left exactly as it was.

    Returns:
        The rewritten copy and the number of values changed.
    """
    rewritten = copy.deepcopy(sidecar)
    changed = 0
    assessments = rewritten.get("assessments")
    if not isinstance(assessments, list):
        return rewritten, changed
    for assessment in assessments:
        if not isinstance(assessment, dict):
            continue
        provenance = assessment.get("provenance")
        if not isinstance(provenance, dict):
            continue
        value = provenance.get("cache_db_path")
        if isinstance(value, str) and _SEPARATORS.search(value):
            provenance["cache_db_path"] = to_basename(value)
            changed += 1
    return rewritten, changed


def build_manifest_records(
    corpora_dir: pathlib.Path,
) -> tuple[list[dict[str, Any]], int, int]:
    """Build tranche-manifest envelopes for every sidecar that needs a rewrite.

    Returns:
        ``(records, files_scanned, values_changed)``. Each record is
        ``{"lcats_id": "<collection>/<story>", "payload": <rewritten sidecar>}``.
    """
    records: list[dict[str, Any]] = []
    scanned = 0
    values_changed = 0
    for sidecar_path in sorted(corpora_dir.glob(f"*/*/{GENRE_SIDECAR_FILENAME}")):
        scanned += 1
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        rewritten, changed = rewrite_cache_db_path(sidecar)
        if changed == 0:
            continue
        lcats_id = sidecar_path.parent.relative_to(corpora_dir).as_posix()
        records.append({"lcats_id": lcats_id, "payload": rewritten})
        values_changed += changed
    return records, scanned, values_changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpora-dir", type=pathlib.Path, default="../corpora")
    parser.add_argument("--manifest-out", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)

    corpora_dir = pathlib.Path(args.corpora_dir)
    if not corpora_dir.is_dir():
        print(f"error: corpora dir not found: {corpora_dir}", file=sys.stderr)
        return 2

    records, scanned, values_changed = build_manifest_records(corpora_dir)
    with args.manifest_out.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
    print(
        f"scanned {scanned} {GENRE_SIDECAR_FILENAME} files; "
        f"{len(records)} need rewriting ({values_changed} values); "
        f"manifest written to {args.manifest_out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
