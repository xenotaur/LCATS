"""Build the sanitized genre-sidecar seed manifest from the tracked evidence file.

A corpus release regenerates ``data/`` (stories only) and then runs
``lcats promote replace``. The 146 tranche-promoted ``genre.json`` sidecars live
only in ``corpora/``, so a bare release run is blocked by the orphaned-sidecar
guard (see ``project/design/genre-sidecars-in-release-workflow.md``). The
recommended fix seeds the regenerated ``data/`` with these sidecars *before*
``replace``, using create-only ``insert``.

The seed source is the tracked evidence file
``experiments/05_metadata_genre_prefilter/results/full_scan/validation_results.jsonl``.
That file is immutable, and it still holds absolute ``cache_db_path`` values, so
this tool sanitizes each record (reusing ``rewrite_cache_db_path`` from
``tools/rewrite_genre_cache_db_path.py``) and writes a JSONL tranche manifest of
``{"lcats_id": ..., "payload": ...}`` envelopes. It never edits the evidence file,
``corpora/`` or ``data/``.

Usage (from the ``lcats/`` directory)::

    python tools/build_genre_seed_manifest.py --manifest-out /path/to/seed.jsonl
    lcats promote insert --sidecar genre --tranche-manifest /path/to/seed.jsonl \
        --dest data/ --dry-run
    lcats promote insert --sidecar genre --tranche-manifest /path/to/seed.jsonl \
        --dest data/

Use ``insert``, not ``upsert``: ``upsert`` overwrites a whole file and would
silently discard a pipeline-produced ``genre.json``; ``insert`` refuses and stops
the release.

Every sanitized payload is validated with ``genre_sidecar.validate_sidecar()``
before anything is written, so the manifest only ever contains seed records
that ``lcats promote insert`` will accept.

Exit codes: ``0`` success; ``1`` malformed evidence, an invalid sidecar payload,
or an ``--expect-count`` mismatch (no manifest is written); ``2`` usage or
environment error (missing or unreadable evidence file, ``--manifest-out`` would
overwrite the evidence file, or the manifest cannot be written, e.g. its
directory does not exist). The manifest is written atomically, so an error never
leaves a partial file behind.
"""

import argparse
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
from typing import Any

from lcats.analysis.corpus import genre_sidecar

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE = (
    _REPO_ROOT
    / "experiments"
    / "05_metadata_genre_prefilter"
    / "results"
    / "full_scan"
    / "validation_results.jsonl"
)


def _load_rewrite_module() -> Any:
    """Load the sibling ``rewrite_genre_cache_db_path`` tool by file path.

    ``tools/`` is not a package, so a plain import only works when this file is
    run as a script; loading by path works from tests and any working directory.
    """
    path = pathlib.Path(__file__).resolve().parent / "rewrite_genre_cache_db_path.py"
    spec = importlib.util.spec_from_file_location("rewrite_genre_cache_db_path", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence_records(path: pathlib.Path) -> list[dict[str, Any]]:
    """Read the evidence JSONL, one ``genre-sidecar-v1`` record per line.

    Raises:
        ValueError: On a line that is not valid JSON, is not an object, lacks a
            non-empty string ``lcats_id``, or repeats an earlier ``lcats_id``.
    """
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: record is not an object")
            lcats_id = record.get("lcats_id")
            if not isinstance(lcats_id, str) or not lcats_id.strip():
                raise ValueError(f"{path}:{line_number}: missing non-empty lcats_id")
            if lcats_id in seen:
                raise ValueError(f"{path}:{line_number}: duplicate lcats_id {lcats_id}")
            seen.add(lcats_id)
            records.append(record)
    return records


def build_seed_records(
    evidence: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Return tranche-manifest envelopes for every evidence record, sanitized.

    Every record is emitted (a seed needs all of them, not only the ones that
    needed rewriting), in evidence order.

    Returns:
        ``(records, values_changed)`` where ``values_changed`` counts the
        ``cache_db_path`` values reduced to a basename.
    """
    rewrite = _load_rewrite_module()
    records: list[dict[str, Any]] = []
    values_changed = 0
    for record in evidence:
        sanitized, changed = rewrite.rewrite_cache_db_path(record)
        records.append({"lcats_id": record["lcats_id"], "payload": sanitized})
        values_changed += changed
    return records, values_changed


def find_invalid_payloads(records: list[dict[str, Any]]) -> list[str]:
    """Return one message per seed record whose payload fails validation.

    Each message names the record's ``lcats_id`` and its first finding.
    """
    problems: list[str] = []
    for record in records:
        result = genre_sidecar.validate_sidecar(record["payload"])
        if not result.valid:
            first = result.findings[0]
            problems.append(f"{record['lcats_id']}: {first.path}: {first.message}")
    return problems


def _write_manifest_atomically(
    path: pathlib.Path, records: list[dict[str, Any]]
) -> None:
    """Write ``records`` as JSONL to ``path`` via a temp file and ``os.replace``."""
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")
        os.replace(tmp_name, path)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--evidence", type=pathlib.Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--manifest-out", type=pathlib.Path, required=True)
    parser.add_argument(
        "--expect-count",
        type=int,
        default=None,
        help="fail (exit 1, nothing written) unless exactly this many records",
    )
    args = parser.parse_args(argv)

    if not args.evidence.is_file():
        print(f"error: evidence file not found: {args.evidence}", file=sys.stderr)
        return 2
    if args.manifest_out.resolve() == args.evidence.resolve():
        print(
            "error: --manifest-out would overwrite the evidence file",
            file=sys.stderr,
        )
        return 2

    try:
        evidence = load_evidence_records(args.evidence)
    except OSError as exc:
        print(f"error: cannot read {args.evidence}: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.expect_count is not None and len(evidence) != args.expect_count:
        print(
            f"error: expected {args.expect_count} records, found {len(evidence)}",
            file=sys.stderr,
        )
        return 1

    records, values_changed = build_seed_records(evidence)
    problems = find_invalid_payloads(records)
    if problems:
        shown = problems[:10]
        print(
            f"error: {len(problems)} of {len(records)} payloads are not valid "
            "genre-sidecar-v1; nothing written:",
            file=sys.stderr,
        )
        for line in shown:
            print(f"  {line}", file=sys.stderr)
        if len(problems) > len(shown):
            print(f"  ... and {len(problems) - len(shown)} more", file=sys.stderr)
        return 1
    try:
        _write_manifest_atomically(args.manifest_out, records)
    except OSError as exc:
        print(f"error: cannot write {args.manifest_out}: {exc}", file=sys.stderr)
        return 2
    print(
        f"{len(records)} seed records ({values_changed} cache_db_path values "
        f"reduced to a basename); manifest written to {args.manifest_out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
