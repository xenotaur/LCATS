"""Formatting and output helpers for corpus analysis."""

import csv
import json
import pathlib

from typing import Mapping, Sequence

from lcats.analysis.corpus import discovery
from lcats.analysis.corpus import models

DEFAULT_OUTPUT_FORMAT = "human"
TSV_COLUMNS = [
    "check",
    "kind",
    "severity",
    "codepoint",
    "char",
    "unicode_name",
    "occurrence_index",
    "offset",
    "span_start",
    "span_end",
    "context",
    "classification",
    "evidence",
    "message",
    # "story_title",
    # "story_file",
    # "path",
    "story_identifier",
    # Appended (not inserted) so positional TSV consumers keep existing
    # column positions -- see Decision 5 of PROP-LCATS-STORY-BUCKET-LAYOUT.
    # story_file (a row-dict field, not part of this schema list -- see
    # the commented placeholder above) is the leaf filename, always
    # "story.json" for a canonical bucket file post-migration and
    # therefore non-unique; story_dir is the actual per-story identity
    # for that case.
    "story_dir",
]
IDENTIFIER_FIELDS = ("path", "filename", "title")
DEFAULT_IDENTIFIER_FIELD = "path"
DEFAULT_TSV_UNICODE_NAME_WIDTH = 48

CHECK_VALUE_MAP = {
    "special-characters": "spchar",
    "boundary-contamination": "boundary",
}
KIND_VALUE_MAP = {
    "special-character": "spchar",
    "start-contamination": "start-contam",
    "end-contamination": "end-contam",
    "rare-review-character": "rare-char",
    "mojibake-sequence": "mojibake",
}
CLASSIFICATION_VALUE_MAP = {
    "likely_good": "lgood",
    "likely_repairable": "lrepair",
    "review_needed": "review",
}
TSV_VALUE_LEGEND = (
    "Compact TSV values: "
    "check(spchar=special-characters, boundary=boundary-contamination); "
    "kind(spchar=special-character, start-contam=start-contamination, "
    "end-contam=end-contamination, rare-char=rare-review-character, "
    "mojibake=mojibake-sequence); "
    "classification("
    "lgood=likely_good, lrepair=likely_repairable, review=review_needed)."
)


def empty_tsv_row() -> dict[str, str]:
    """Return a blank TSV row with all stable fields present."""
    return {column: "" for column in TSV_COLUMNS}


def compact_value(value: str, mapping: Mapping[str, str]) -> str:
    """Return compact TSV value for known verbose labels."""
    return mapping.get(value, value)


def severity_from_classification(classification: str) -> str:
    """Map special-character classification to severity."""
    lowered = classification.lower()
    if lowered == "likely_repairable":
        return "error"
    if lowered == "likely_good":
        return "info"
    if lowered:
        return "warning"
    return "warning"


def story_dir_value(file_path: pathlib.Path) -> str:
    """Return the story's bucket directory name, or "" for a flat file.

    Only meaningful for a canonical per-story-bucket file (``story.json``),
    whose own leaf name is always the same reserved string and therefore not
    a usable identifier on its own (Decision 5 of
    PROP-LCATS-STORY-BUCKET-LAYOUT).

    Falls back to the resolved (absolute) path when the lexical parent has
    no name -- e.g. a bare relative ``story.json`` invoked from inside the
    bucket directory itself, whose ``pathlib.Path(...).parent`` is ``.``
    and therefore has an empty ``.name``. Resolving recovers the real
    directory name in that case instead of leaving the column blank.

    ``resolve()`` touches the filesystem and can raise (``OSError`` on a
    permission error, ``RuntimeError`` on a symlink loop on Python <3.13)
    -- guarded so a single unresolvable path doesn't crash the whole
    caller (e.g. ``cli.py``'s ``run_survey``, which has no per-file
    exception handling of its own); falls back to ``""`` on failure.
    """
    if file_path.name != discovery.CANONICAL_STORY_FILENAME:
        return ""
    parent_name = file_path.parent.name
    if parent_name:
        return parent_name
    try:
        return file_path.resolve().parent.name
    except (OSError, RuntimeError):
        return ""


def parse_special_character_rows(
    tsv_output: str, file_path: pathlib.Path, story_title: str = ""
) -> list[dict[str, str]]:
    """Parse extractor TSV output into stable report rows."""
    if not tsv_output.strip():
        return []

    rows = []
    parsed_rows = list(csv.reader(tsv_output.splitlines(), delimiter="\t"))
    if parsed_rows and parsed_rows[0] and parsed_rows[0][0] == "codepoint":
        parsed_rows = parsed_rows[1:]

    for parts in parsed_rows:
        if not parts:
            continue
        padded = parts + [""] * (8 - len(parts))
        row = empty_tsv_row()
        row.update(
            {
                "story_title": story_title,
                "story_file": file_path.name,
                "story_dir": story_dir_value(file_path),
                "path": str(file_path),
                "check": compact_value("special-characters", CHECK_VALUE_MAP),
                "kind": compact_value("special-character", KIND_VALUE_MAP),
                "severity": severity_from_classification(padded[6]),
                "codepoint": padded[0],
                "char": padded[1],
                "unicode_name": padded[2],
                "occurrence_index": padded[3],
                "offset": padded[4],
                "context": padded[5],
                "classification": compact_value(padded[6], CLASSIFICATION_VALUE_MAP),
                "evidence": padded[7],
                "message": "Special character finding.",
            }
        )
        rows.append(row)

    return rows


def finding_to_row(
    file_path: pathlib.Path,
    story_title: str,
    check_name: str,
    finding: models.Finding,
) -> dict[str, str]:
    """Convert one finding into a stable TSV row."""
    context = ""
    evidence_line = finding.evidence.get("line")
    if isinstance(evidence_line, str):
        context = evidence_line

    row = empty_tsv_row()
    row.update(
        {
            "story_title": story_title,
            "story_file": file_path.name,
            "story_dir": story_dir_value(file_path),
            "path": str(file_path),
            "check": compact_value(check_name, CHECK_VALUE_MAP),
            "kind": compact_value(finding.kind, KIND_VALUE_MAP),
            "severity": finding.severity,
            "span_start": str(finding.span[0]),
            "span_end": str(finding.span[1]),
            "context": context,
            "evidence": json.dumps(dict(finding.evidence), ensure_ascii=False),
            "message": finding.message,
        }
    )
    return row


def clean_row(file_path: pathlib.Path, story_title: str = "") -> dict[str, str]:
    """Build a summary row for files with no findings."""
    row = empty_tsv_row()
    row.update(
        {
            "story_title": story_title,
            "story_file": file_path.name,
            "story_dir": story_dir_value(file_path),
            "path": str(file_path),
            "check": "summary",
            "kind": "clean",
            "severity": "info",
            "message": "No findings.",
        }
    )
    return row


def with_identifier(
    row: Mapping[str, str], identifier: str = DEFAULT_IDENTIFIER_FIELD
) -> dict[str, str]:
    """Return row with selected identifier value and stable schema."""
    mutable = dict(row)
    if identifier == "filename":
        mutable["story_identifier"] = mutable.get("story_file", "")
    elif identifier == "title":
        mutable["story_identifier"] = mutable.get("story_title", "")
    else:
        mutable["story_identifier"] = mutable.get("path", "")
    return mutable


def truncate_value(value: str, width: int) -> str:
    """Return value truncated to width with ellipsis when needed."""
    if width <= 0 or len(value) <= width:
        return value
    if width == 1:
        return "…"
    return f"{value[: width - 1]}…"


def compact_human_tsv_row(
    row: Mapping[str, str], identifier: str, unicode_name_width: int
) -> dict[str, str]:
    """Return TSV row adjusted for human-readable terminal display."""
    mutable = with_identifier(row, identifier)
    mutable["unicode_name"] = truncate_value(
        mutable.get("unicode_name", ""), unicode_name_width
    )
    return mutable


def write_human_rows(
    output_stream,
    file_path: pathlib.Path,
    rows: Sequence[Mapping[str, str]],
) -> None:
    """Write human-readable findings for one file."""
    print(str(file_path), file=output_stream)
    for row in rows:
        details = []
        if row.get("codepoint", ""):
            details.append(row["codepoint"])
        if row.get("char", ""):
            details.append(repr(row["char"]))
        if row.get("span_start", "") or row.get("span_end", ""):
            details.append(
                f"span={row.get('span_start', '')}:{row.get('span_end', '')}"
            )
        suffix = f" ({', '.join(details)})" if details else ""
        print(
            f"  [{row.get('check', '')}] {row.get('severity', '')}: {row.get('message', '')}{suffix}",
            file=output_stream,
        )
        context = row.get("context", "")
        if context:
            for line in context.splitlines():
                print(f"    context: {line}", file=output_stream)
