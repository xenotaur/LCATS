"""Archive the genre-evidence checkpoint files and derive the baseline-hash manifest.

``WI-PROMOTE-0124``. The 146 stories of ``results/full_scan/validation_results.jsonl``
were each validated twice: by Claude Opus (``validation.json`` checkpoints) and by a
local ``gpt-oss:20b`` run (``validation_openai_http_localhost_11434_v1.json``
checkpoints). Every checkpoint carries ``fingerprint.story_content_hash``, the sha256
of the story's ``story.json`` bytes at assessment time. The committed results hold no
hash, and ``.gitignore`` deliberately keeps checkpoint scratch files out of git, so
those hashes existed only in gitignored files in one worktree.

This tool copies the 292 checkpoint files, byte for byte, to a tracked archive nested
by ``lcats_id`` (``<collection>/<story>/{opus,gpt-oss-20b}-checkpoint.json``). The
renamed files do not match the ignore rule, so no ``.gitignore`` change is needed. It
writes a per-file sha256 index, derives a ``{lcats_id, story_content_hash}`` baseline
manifest from the archived **Opus** files only, and verifies the whole set.

Two subcommands:

* ``archive --source DIR``: copy, index, derive the manifest, then verify.
* ``verify``: re-check an existing archive. Safe to run any time, including in CI.

The source directory is only ever read. A source name is built forward from the known
``lcats_id`` (``/`` replaced by ``__``); names are never parsed backwards, because 84
story names themselves contain ``__``.

Exit codes: 0 success; 1 verification problems; 2 missing sources, conflicting
archive content, or bad input (nothing is written in the first two cases).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
import tempfile
from typing import Any, Iterable

EXPERIMENT_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]
FULL_SCAN = EXPERIMENT_DIR / "results" / "full_scan"
DEFAULT_EVIDENCE = FULL_SCAN / "validation_results.jsonl"
DEFAULT_ARCHIVE = FULL_SCAN / "checkpoint_archive_2026-08-21"
DEFAULT_MANIFEST = FULL_SCAN / "story_hash_baseline.jsonl"
DEFAULT_CORPORA = REPO_ROOT / "corpora"

INDEX_NAME = "archive_index.jsonl"
README_NAME = "README.md"
ASSESS_METHOD_SUFFIX = "assess_story"

# (kind, source file name inside <collection>__<story>/, archived file name)
KINDS: tuple[tuple[str, str, str], ...] = (
    ("opus", "validation.json", "opus-checkpoint.json"),
    (
        "gpt-oss-20b",
        "validation_openai_http_localhost_11434_v1.json",
        "gpt-oss-20b-checkpoint.json",
    ),
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ArchiveError(Exception):
    """A condition that must stop the run before anything is written."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_evidence(evidence: pathlib.Path) -> dict[str, dict[str, Any]]:
    """Return ``{lcats_id: committed model assessment}`` in evidence order.

    The model assessment is the one whose method name ends in ``assess_story``.
    Raises ``ArchiveError`` on a malformed, duplicated or ambiguous record.
    """
    assessments: dict[str, dict[str, Any]] = {}
    with evidence.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            lcats_id = record.get("lcats_id")
            _require_safe_id(lcats_id, f"{evidence}:{number}")
            if lcats_id in assessments:
                raise ArchiveError(f"{evidence}:{number}: duplicate {lcats_id}")
            model = [
                a
                for a in record.get("assessments", [])
                if str(a.get("method", {}).get("name", "")).endswith(
                    ASSESS_METHOD_SUFFIX
                )
            ]
            if len(model) != 1:
                raise ArchiveError(
                    f"{evidence}:{number}: {lcats_id} has {len(model)} model "
                    "assessments, expected exactly 1"
                )
            assessments[lcats_id] = model[0]
    return assessments


def _require_safe_id(lcats_id: Any, where: str) -> str:
    if not isinstance(lcats_id, str):
        raise ArchiveError(f"{where}: lcats_id is not a string")
    parts = lcats_id.split("/")
    if len(parts) != 2 or any(p in ("", ".", "..") for p in parts):
        raise ArchiveError(f"{where}: unsafe lcats_id {lcats_id!r}")
    return lcats_id


def source_file(source_root: pathlib.Path, lcats_id: str, name: str) -> pathlib.Path:
    """Source path, built forward from the id (never parsed backwards)."""
    return source_root / lcats_id.replace("/", "__") / name


def archive_file(
    archive_root: pathlib.Path, lcats_id: str, archived_name: str
) -> pathlib.Path:
    return archive_root / lcats_id / archived_name


def archive_checkpoints(
    source_root: pathlib.Path,
    archive_root: pathlib.Path,
    ids: Iterable[str],
) -> list[dict[str, Any]]:
    """Copy every checkpoint byte for byte and return the index rows.

    Resolves every source and checks every destination before writing anything:
    a missing source or a destination that already holds different content raises
    ``ArchiveError`` and leaves the archive untouched. Re-running over an identical
    archive is a no-op. The source files are only read.
    """
    plan: list[tuple[str, str, pathlib.Path, pathlib.Path, bytes]] = []
    missing: list[str] = []
    conflicts: list[str] = []
    for lcats_id in ids:
        for kind, source_name, archived_name in KINDS:
            src = source_file(source_root, lcats_id, source_name)
            dest = archive_file(archive_root, lcats_id, archived_name)
            if not src.is_file():
                missing.append(str(src))
                continue
            data = src.read_bytes()
            if dest.exists() and dest.read_bytes() != data:
                conflicts.append(str(dest))
                continue
            plan.append((lcats_id, kind, src, dest, data))
    if missing:
        raise ArchiveError(
            f"{len(missing)} source checkpoint file(s) missing, nothing written; "
            f"first: {missing[0]}"
        )
    if conflicts:
        raise ArchiveError(
            f"{len(conflicts)} archive file(s) already hold different content, "
            f"nothing written; first: {conflicts[0]}"
        )
    rows: list[dict[str, Any]] = []
    for lcats_id, kind, _src, dest, data in plan:
        if not dest.exists():
            _write_bytes_atomically(dest, data)
        rows.append(
            {
                "lcats_id": lcats_id,
                "kind": kind,
                "archive_path": dest.relative_to(archive_root).as_posix(),
                "sha256": sha256_bytes(data),
                "bytes": len(data),
            }
        )
    rows.sort(key=lambda r: (r["lcats_id"], r["kind"]))
    return rows


def _write_bytes_atomically(path: pathlib.Path, data: bytes) -> None:
    """Write via a temp file and ``os.replace`` so a kill never leaves a stub."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_jsonl_atomically(path: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _checkpoint(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_or_problem(
    path: pathlib.Path, label: str, problems: list[str]
) -> dict[str, Any] | None:
    """Load a checkpoint, reporting unreadable or non-object content as a problem."""
    try:
        data = _checkpoint(path)
    except (OSError, ValueError) as exc:
        problems.append(
            f"{label}: unreadable archived checkpoint ({exc.__class__.__name__})"
        )
        return None
    if not isinstance(data, dict):
        problems.append(f"{label}: archived checkpoint is not a JSON object")
        return None
    return data


def _read_jsonl_or_problem(
    path: pathlib.Path, label: str, problems: list[str]
) -> list[dict[str, Any]] | None:
    try:
        rows = _read_jsonl(path)
    except (OSError, ValueError) as exc:
        problems.append(f"{label}: unreadable ({exc.__class__.__name__})")
        return None
    if not all(isinstance(r, dict) for r in rows):
        problems.append(f"{label}: contains a row that is not a JSON object")
        return None
    return rows


def derive_manifest(
    archive_root: pathlib.Path, ids: Iterable[str]
) -> list[dict[str, Any]]:
    """Build the baseline rows from the archived **Opus** checkpoints only."""
    rows: list[dict[str, Any]] = []
    opus_name = KINDS[0][2]
    for lcats_id in ids:
        path = archive_file(archive_root, lcats_id, opus_name)
        story_hash = _checkpoint(path).get("fingerprint", {}).get("story_content_hash")
        if not isinstance(story_hash, str) or not _HEX64.match(story_hash):
            raise ArchiveError(f"{path}: no valid fingerprint.story_content_hash")
        rows.append(
            {
                "lcats_id": lcats_id,
                "story_content_hash": story_hash,
                "archive_path": path.relative_to(archive_root).as_posix(),
                "archive_sha256": sha256_file(path),
            }
        )
    return rows


def verify(
    archive_root: pathlib.Path,
    manifest_path: pathlib.Path,
    evidence: pathlib.Path,
    corpora_root: pathlib.Path,
) -> list[str]:
    """Return one message per problem; an empty list means everything holds."""
    problems: list[str] = []
    committed = load_evidence(evidence)
    ids = list(committed)
    archived_names = {kind: archived for kind, _s, archived in KINDS}

    index_path = archive_root / INDEX_NAME
    if not index_path.is_file():
        return [f"missing index {index_path}"]
    index_rows = _read_jsonl_or_problem(index_path, "archive index", problems)
    if index_rows is None:
        return problems
    index = {}
    for row in index_rows:
        key = (row.get("lcats_id"), row.get("kind"))
        if key in index:
            problems.append(f"index has a duplicate row for {key[0]} {key[1]}")
        index[key] = row
    expected_keys = {(i, k) for i in ids for k, _s, _a in KINDS}
    if set(index) != expected_keys:
        problems.append(
            f"index covers {len(set(index))} (id, kind) pairs, "
            f"expected {len(expected_keys)}"
        )
    for (lcats_id, kind), row in sorted(
        index.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))
    ):
        if kind not in archived_names or lcats_id not in committed:
            continue
        expected_path = f"{lcats_id}/{archived_names[kind]}"
        if row.get("archive_path") != expected_path:
            problems.append(f"index archive_path wrong for {lcats_id} {kind}")
        path = archive_file(archive_root, lcats_id, archived_names[kind])
        if not path.is_file():
            problems.append(f"archived file missing: {lcats_id} {kind}")
            continue
        data = path.read_bytes()
        if sha256_bytes(data) != row.get("sha256") or len(data) != row.get("bytes"):
            problems.append(f"archived file differs from the index: {lcats_id} {kind}")

    allowed = {INDEX_NAME, README_NAME} | {
        f"{i}/{archived}" for i in ids for _k, _s, archived in KINDS
    }
    if archive_root.is_dir():
        for found in archive_root.rglob("*"):
            if found.is_file() and found.relative_to(archive_root).as_posix() not in (
                allowed
            ):
                problems.append(f"unexpected file in archive: {found}")

    if not manifest_path.is_file():
        problems.append(f"missing manifest {manifest_path}")
        return problems
    manifest = _read_jsonl_or_problem(manifest_path, "manifest", problems)
    if manifest is None:
        return problems
    by_id = {r.get("lcats_id"): r for r in manifest}
    if len(by_id) != len(manifest):
        problems.append("manifest has duplicate lcats_id rows")
    if set(by_id) != set(ids) or len(manifest) != len(ids):
        problems.append(
            f"manifest has {len(manifest)} rows, expected exactly the {len(ids)} "
            "evidence ids"
        )

    for lcats_id in ids:
        opus_path = archive_file(archive_root, lcats_id, archived_names["opus"])
        gpt_path = archive_file(archive_root, lcats_id, archived_names["gpt-oss-20b"])
        if not opus_path.is_file() or not gpt_path.is_file():
            continue
        opus = _load_or_problem(opus_path, f"{lcats_id} opus", problems)
        gpt = _load_or_problem(gpt_path, f"{lcats_id} gpt-oss", problems)
        if opus is None or gpt is None:
            continue
        opus_hash = opus.get("fingerprint", {}).get("story_content_hash")
        if opus.get("data", {}).get("model_assessment") != committed[lcats_id]:
            problems.append(
                f"{lcats_id}: archived Opus model_assessment differs from the "
                "committed one"
            )
        row = by_id.get(lcats_id)
        if row is None or row.get("story_content_hash") != opus_hash:
            problems.append(f"{lcats_id}: manifest hash differs from the Opus archive")
        elif row.get(
            "archive_path"
        ) != f"{lcats_id}/{archived_names['opus']}" or row.get(
            "archive_sha256"
        ) != sha256_file(
            opus_path
        ):
            problems.append(
                f"{lcats_id}: manifest archive_path or archive_sha256 is wrong"
            )
        if gpt.get("fingerprint", {}).get("story_content_hash") != opus_hash:
            problems.append(f"{lcats_id}: gpt-oss hash differs from the Opus hash")
        story = corpora_root / lcats_id / "story.json"
        if not story.is_file():
            problems.append(f"{lcats_id}: no story.json under {corpora_root}")
        elif sha256_file(story) != opus_hash:
            problems.append(f"{lcats_id}: current story.json differs from the hash")
    return problems


def _cmd_archive(args: argparse.Namespace) -> int:
    ids = list(load_evidence(args.evidence))
    try:
        rows = archive_checkpoints(args.source, args.archive_root, ids)
    except ArchiveError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    write_jsonl_atomically(args.archive_root / INDEX_NAME, rows)
    write_jsonl_atomically(args.manifest, derive_manifest(args.archive_root, ids))
    print(f"archived {len(rows)} files for {len(ids)} stories; manifest written")
    return _report(
        verify(args.archive_root, args.manifest, args.evidence, args.corpora)
    )


def _cmd_verify(args: argparse.Namespace) -> int:
    return _report(
        verify(args.archive_root, args.manifest, args.evidence, args.corpora)
    )


def _report(problems: list[str]) -> int:
    if not problems:
        print("verify: ok")
        return 0
    for problem in problems:
        print(f"problem: {problem}", file=sys.stderr)
    print(f"verify: {len(problems)} problem(s)", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name, handler in (("archive", _cmd_archive), ("verify", _cmd_verify)):
        p = sub.add_parser(name)
        p.add_argument("--evidence", type=pathlib.Path, default=DEFAULT_EVIDENCE)
        p.add_argument("--archive-root", type=pathlib.Path, default=DEFAULT_ARCHIVE)
        p.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST)
        p.add_argument("--corpora", type=pathlib.Path, default=DEFAULT_CORPORA)
        if name == "archive":
            p.add_argument("--source", type=pathlib.Path, required=True)
        p.set_defaults(handler=handler)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except ArchiveError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(
            f"error: unreadable or malformed input ({exc.__class__.__name__}: {exc})",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
