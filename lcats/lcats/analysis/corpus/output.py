"""Formatting and output helpers for corpus analysis."""

import csv
import json
import pathlib

from typing import Mapping, Sequence

from lcats.analysis.corpus import models

DEFAULT_OUTPUT_FORMAT = "human"
TSV_COLUMNS = [
    "story_title",
    "story_file",
    "path",
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
]

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
    "valid-typography": "valid-typo",
    "suspicious-unicode": "sus-unicode",
    "mojibake-pattern": "mojibake",
}
TSV_VALUE_LEGEND = (
    "Compact TSV values: "
    "check(spchar=special-characters, boundary=boundary-contamination); "
    "kind(spchar=special-character, start-contam=start-contamination, "
    "end-contam=end-contamination, rare-char=rare-review-character, "
    "mojibake=mojibake-sequence); "
    "classification(valid-typo=valid-typography, "
    "sus-unicode=suspicious-unicode, mojibake=mojibake-pattern)."
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
    if "mojibake" in lowered:
        return "error"
    if "rare" in lowered:
        return "info"
    if lowered:
        return "warning"
    return "warning"


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
    row = empty_tsv_row()
    row.update(
        {
            "story_title": story_title,
            "story_file": file_path.name,
            "path": str(file_path),
            "check": compact_value(check_name, CHECK_VALUE_MAP),
            "kind": compact_value(finding.kind, KIND_VALUE_MAP),
            "severity": finding.severity,
            "span_start": str(finding.span[0]),
            "span_end": str(finding.span[1]),
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
            "path": str(file_path),
            "check": "summary",
            "kind": "clean",
            "severity": "info",
            "message": "No findings.",
        }
    )
    return row


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
