"""Check that a regenerated story tree holds the story bytes the genre sidecars were assessed against.

Each of the 146 seeded ``genre.json`` sidecars carries a model assessment that
reads the story text, but no story-text fingerprint, so a release cannot tell
whether a regenerated ``data/<collection>/<story>/story.json`` still matches the
text that was assessed (see ``project/design/genre-sidecar-story-binding.md``,
``WI-PROMOTE-0118`` and ``WI-PROMOTE-0133``).

The tracked baseline,
``experiments/05_metadata_genre_prefilter/results/full_scan/story_hash_baseline.jsonl``
(``WI-PROMOTE-0124``), records for each of the 146 stories the sha256 of its
``story.json`` bytes at assessment time. This tool hashes the same file under a
given root and compares. It uses file bytes, which is conservative: it also flags
a change to a field the assessment ignores, such as ``year``, so it can cost an
unnecessary re-assess-or-accept decision but never misses a stale sidecar.

It is read-only: it never writes under the root it reads or anywhere else.

Usage (from the ``lcats/`` directory), after ``lcats gather`` and the seed step::

    python tools/check_genre_story_binding.py --root data

Problems are listed on stderr, one per line, in three kinds:

* ``changed``: the story's bytes differ from the baseline.
* ``missing``: the baseline lists the story but the root has no ``story.json``
  for it (for example a collection that was not regenerated).
* ``unlisted``: the root holds a ``genre.json`` for a story that is not in the
  baseline, so nothing says what text that sidecar was assessed against.

Exit codes: ``0`` every baseline story is present and matches, and no unlisted
story has a ``genre.json`` (one ``ok:`` line on stdout); ``1`` at least one
problem; ``2`` an unreadable or malformed baseline, an empty baseline, or an
unreadable or non-directory root.
"""

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_BASELINE = (
    _REPO_ROOT
    / "experiments"
    / "05_metadata_genre_prefilter"
    / "results"
    / "full_scan"
    / "story_hash_baseline.jsonl"
)

STORY_NAME = "story.json"
SIDECAR_NAME = "genre.json"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _require_story_id(lcats_id: str, where: str) -> str:
    """Return ``lcats_id`` if it is a safe ``<collection>/<story>`` pair.

    The id becomes a path under the root, so anything that could leave it
    (absolute, ``.``/``..`` parts, backslashes) is rejected.
    """
    parts = lcats_id.split("/")
    if len(parts) != 2 or any(p in ("", ".", "..") for p in parts) or "\\" in lcats_id:
        raise ValueError(f"{where}: lcats_id {lcats_id!r} is not <collection>/<story>")
    return lcats_id


def load_baseline(path: pathlib.Path) -> dict[str, str]:
    """Read the baseline JSONL into ``{lcats_id: story_content_hash}``.

    Only ``lcats_id`` and ``story_content_hash`` are read; any other field on a
    row is ignored.

    Raises:
        OSError: If the file cannot be read.
        ValueError: On a line that is not valid JSON or not an object, a missing
            or unsafe ``lcats_id``, a ``story_content_hash`` that is not 64
            lowercase hex digits, a repeated ``lcats_id``, or a file with no
            rows (an empty baseline would pass every root).
    """
    rows: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            where = f"{path}:{line_number}"
            try:
                row: Any = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{where}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{where}: row is not an object")
            lcats_id = row.get("lcats_id")
            if not isinstance(lcats_id, str):
                raise ValueError(f"{where}: missing string lcats_id")
            _require_story_id(lcats_id, where)
            story_hash = row.get("story_content_hash")
            if not isinstance(story_hash, str) or not _HEX64.match(story_hash):
                raise ValueError(
                    f"{where}: story_content_hash for {lcats_id} is not 64 hex digits"
                )
            if lcats_id in rows:
                raise ValueError(f"{where}: duplicate lcats_id {lcats_id}")
            rows[lcats_id] = story_hash
    if not rows:
        raise ValueError(f"{path}: baseline has no rows")
    return rows


def sha256_file(path: pathlib.Path) -> str:
    """Return the sha256 hex digest of the file's bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_root(root: pathlib.Path, baseline: dict[str, str]) -> dict[str, list[str]]:
    """Compare ``root`` with ``baseline``; return problems by kind.

    The result has the keys ``changed``, ``missing`` and ``unlisted``, each a
    sorted list of ``lcats_id`` strings. All three empty means the root holds
    exactly the assessed text for every story that has a ``genre.json``.

    Raises:
        ValueError: If ``root`` is not a directory.
        OSError: If a story file that exists cannot be read.
    """
    if not root.is_dir():
        raise ValueError(f"root is not a directory: {root}")
    changed: list[str] = []
    missing: list[str] = []
    for lcats_id, expected in baseline.items():
        story = root / lcats_id / STORY_NAME
        if not story.is_file():
            missing.append(lcats_id)
        elif sha256_file(story) != expected:
            changed.append(lcats_id)
    unlisted = [
        f"{sidecar.parent.parent.name}/{sidecar.parent.name}"
        for sidecar in root.glob(f"*/*/{SIDECAR_NAME}")
        if sidecar.is_file()
    ]
    return {
        "changed": sorted(changed),
        "missing": sorted(missing),
        "unlisted": sorted(i for i in unlisted if i not in baseline),
    }


_MESSAGES = {
    "changed": "story.json differs from the baseline hash",
    "missing": "no story.json under the root",
    "unlisted": "has a genre.json but is not in the baseline",
}


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        required=True,
        help="Story tree to check, laid out as <root>/<collection>/<story>/story.json "
        "(for a release, data/).",
    )
    parser.add_argument(
        "--baseline",
        type=pathlib.Path,
        default=DEFAULT_BASELINE,
        help="Baseline JSONL of {lcats_id, story_content_hash} rows "
        "(default: the tracked story_hash_baseline.jsonl).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the check; return the process exit code."""
    args = build_parser().parse_args(argv)
    try:
        baseline = load_baseline(args.baseline)
        problems = check_root(args.root, baseline)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    total = sum(len(ids) for ids in problems.values())
    if total == 0:
        print(f"ok: {len(baseline)} stories match the baseline under {args.root}")
        return 0
    for kind in ("changed", "missing", "unlisted"):
        for lcats_id in problems[kind]:
            print(f"{kind}: {lcats_id} ({_MESSAGES[kind]})", file=sys.stderr)
    print(f"check: {total} problem(s) under {args.root}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
