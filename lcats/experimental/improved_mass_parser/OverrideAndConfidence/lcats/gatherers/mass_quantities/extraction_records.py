"""Auditable Gutenberg extraction records and human-reviewed start overrides.

The override itself is never generated or updated by runtime code. Overrides
apply ONLY on a new story.json publication, after the normal parser and
normalizer have run. If their reviewed opening cannot be found uniquely in the
extracted text, publication is refused rather than silently guessing.
"""
from __future__ import annotations

import datetime as _datetime
import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata

RAW_LINES = 120
EXTRACTED_LINES = 80


def timestamp() -> str:
    return _datetime.datetime.now(_datetime.timezone.utc).isoformat(timespec="seconds")


def opening_lines(text: str, count: int) -> str:
    """Take physical lines including empty lines, retaining their line endings."""
    return "".join(text.splitlines(keepends=True)[:count])


def _fold(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text).casefold()
    return re.findall(r"[^\W_]+", text, flags=re.UNICODE)


def _line_anchor(body: str, reviewed: str) -> int | None:
    """Locate a unique reviewed beginning at a physical line boundary.

    Word comparison tolerates underscore italics, straight/curly quotation
    marks, and normalization edits, but refuses matches that begin mid-line.
    Search at most the first 500 extracted physical lines. A sufficiently long
    sequence is required to avoid a short heading such as 'SCENE' matching
    some later occurrence by accident.
    """
    wanted = _fold(reviewed)
    if len(wanted) < 8:
        return None
    sample = wanted[:min(18, len(wanted))]
    offsets = []
    cursor = 0
    for line in body.splitlines(keepends=True)[:500]:
        words = _fold(line)
        if words and words[:min(len(words), len(sample))] == sample[:min(len(words), len(sample))]:
            # Verify across subsequent lines (ignore style/line-wrap differences).
            continuation = _fold(body[cursor:])
            if continuation[:len(sample)] == sample:
                offsets.append(cursor)
        cursor += len(line)
    return offsets[0] if len(offsets) == 1 else None


def apply_override(body: str, override: dict, *, gutenberg_id: int, title: str) -> str:
    """Drop ONLY the prefix before a verified narrative start; never rewrite prose.

    A review excerpt must be found in the actual extracted body. If the parser
    has lost that opening text, we refuse to publish rather than splice a
    partial human excerpt into an unrelated position.
    """
    if override.get("gutenberg_id") != gutenberg_id:
        raise ValueError("Override Gutenberg ID differs from story being saved")
    titles = override.get("title", [])
    if not isinstance(titles, list) or not titles:
        raise ValueError("Override missing title")
    if _fold(titles[0]) != _fold(title):
        raise ValueError("Override title differs from story being saved")
    reviewed = override.get("first_narrative_text")
    if not isinstance(reviewed, str) or not reviewed.strip():
        raise ValueError("Override missing reviewed narrative opening")
    offset = _line_anchor(body, reviewed)
    if offset is None:
        raise ValueError("Override beginning not uniquely found in extracted text; refusing publication")
    # Preserve original narrative formatting in body (beyond leading blank lines).
    return body[offset:].lstrip("\r\n")


def load_override(story_dir: str | Path, *, gutenberg_id: int, title: str) -> dict | None:
    override_path = Path(story_dir) / "override.json"
    if not override_path.exists():
        return None
    if not override_path.is_file() or override_path.is_symlink():
        raise ValueError(f"Invalid override path: {override_path}")
    with override_path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict) or value.get("gutenberg_id") != gutenberg_id:
        raise ValueError(f"Override does not match {gutenberg_id}: {override_path}")
    if not value.get("override_datetime"):
        raise ValueError(f"Override lacks timestamp: {override_path}")
    if not value.get("original_opening"):
        raise ValueError(f"Override lacks raw opening: {override_path}")
    if not value.get("first_narrative_text"):
        raise ValueError(f"Override lacks reviewed opening: {override_path}")
    return value


def extraction_record(*, gutenberg_id: int, title: str, authors: list[str],
                      raw_text: str, extracted_body: str,
                      overridden: bool, extracted_at: str | None = None,
                      raw_lines: int = RAW_LINES,
                      extracted_lines: int = EXTRACTED_LINES,
                      confidence: str = "low") -> dict:
    """Return ground-truth-like excerpts with the parser's heuristic confidence.

    Confidence reflects the parser's metadata/boundary heuristic, not a
    calibrated probability that the narrative opening is correct.
    """
    if confidence not in {"high", "medium", "low"}:
        raise ValueError("confidence must be high, medium, or low")
    return {
        "gutenberg_id": gutenberg_id,
        "title": [title],
        "authors": list(authors),
        "original_opening": opening_lines(raw_text, raw_lines),
        "first_narrative_text": opening_lines(extracted_body, extracted_lines),
        "review_status": "extracted",
        "confidence": confidence,
        "physical_lines_included": raw_lines,
        "extracted_lines_included": extracted_lines,
        "extraction_datetime": extracted_at or timestamp(),
        "override_applied": overridden,
    }


def save_extraction_record(story_dir: str | Path, record: dict) -> Path:
    """Publish diagnostic JSON atomically; do not modify an override file."""
    directory = Path(story_dir)
    target = directory / "extraction.json"
    if not (directory / "story.json").is_file():
        raise FileNotFoundError("story.json must exist before extraction.json is written")
    fd, temp = tempfile.mkstemp(dir=directory, prefix=".extraction-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return target
