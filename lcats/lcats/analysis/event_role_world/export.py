"""Stage 9: validation and export.

Emits canonical per-story JSON and derived JSONL/CSV analysis tables, and
runs the proposal's "Artifact validation" checks (Validation and metrics
section): all entity/event/relation IDs resolve, evidence spans align,
causal links carry evidence and certainty, SF tags carry evidence and a
fact/hypothesis status, and exports are deterministic for the same input.
"""

from __future__ import annotations

import csv
import io
import json
import os

from typing import Any, Dict, List

from lcats.analysis.event_role_world import schema

_VALID_RELATION_CERTAINTIES = {"explicit", "strongly_implied", "weakly_inferred"}
_VALID_SF_TAG_STATUSES = {"extractive", "hypothesis"}


def validate_artifacts(story: schema.StoryWorldAnnotation) -> List[str]:
    """Run the proposal's Artifact validation checks against `story`.

    Args:
        story: A StoryWorldAnnotation produced by
            schema.reconcile_story_annotations.

    Returns:
        A list of human-readable error strings; empty if all checks pass.
        Aggregates each segment's own validation_errors (ID resolution,
        evidence-span alignment) plus story.validation_errors (story-scoped
        ID resolution), and additionally checks that every relation's
        certainty and every SF tag's status are valid controlled values —
        the proposal's "inferred claims are marked inferred or hypothesis"
        requirement.
    """
    errors: List[str] = []

    for segment in story.segment_annotations:
        for error in segment.validation_errors:
            errors.append(f"segment {segment.segment_id!r}: {error}")

        for relation in segment.relations + segment.weakly_inferred_relations:
            if relation.certainty not in _VALID_RELATION_CERTAINTIES:
                errors.append(
                    f"segment {segment.segment_id!r} relation "
                    f"{relation.relation_id!r} has invalid certainty "
                    f"{relation.certainty!r}"
                )

        for tag in segment.sf_tags:
            if tag.status not in _VALID_SF_TAG_STATUSES:
                errors.append(
                    f"segment {segment.segment_id!r} SF tag {tag.tag_id!r} "
                    f"has invalid status {tag.status!r}"
                )

    errors.extend(story.validation_errors)

    return errors


def to_canonical_json(story: schema.StoryWorldAnnotation) -> str:
    """Serialize `story` to canonical, deterministic JSON.

    Args:
        story: A StoryWorldAnnotation to serialize.

    Returns:
        A JSON string with sorted keys and stable formatting — calling
        this twice on the same (unmodified) StoryWorldAnnotation produces
        byte-identical output, satisfying the proposal's "exports are
        deterministic" requirement.
    """
    return json.dumps(story.to_dict(), indent=2, sort_keys=True)


def export_story_json(story: schema.StoryWorldAnnotation, path: str) -> None:
    """Write `story`'s canonical JSON to `path`."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(to_canonical_json(story))


def build_analysis_tables(
    story: schema.StoryWorldAnnotation,
) -> Dict[str, List[Dict[str, Any]]]:
    """Flatten `story` into per-table rows for JSONL/CSV export.

    Args:
        story: A StoryWorldAnnotation to flatten.

    Returns:
        A dict of table_name -> list of flat row dicts, one table per
        annotation layer (entities, events, relations, speech_acts,
        explanations, sf_tags, temporal_anchors, spatial_anchors), each row
        tagged with segment_id (or "story" for story-level entities).
    """
    tables: Dict[str, List[Dict[str, Any]]] = {
        "entities": [],
        "events": [],
        "relations": [],
        "speech_acts": [],
        "explanations": [],
        "sf_tags": [],
        "temporal_anchors": [],
        "spatial_anchors": [],
    }

    for entity in story.entities:
        row = entity.to_dict()
        row["segment_id"] = "story"
        tables["entities"].append(row)

    for segment in story.segment_annotations:
        for event in segment.events:
            row = {
                "segment_id": segment.segment_id,
                "event_id": event.event_id,
                "predicate": event.predicate,
                "event_type": event.event_type,
                "modality": event.modality,
                "confidence": event.confidence,
            }
            tables["events"].append(row)

        for relation in segment.relations + segment.weakly_inferred_relations:
            row = relation.to_dict()
            row["segment_id"] = segment.segment_id
            tables["relations"].append(row)

        for speech_act in segment.speech_acts:
            row = speech_act.to_dict()
            row["segment_id"] = segment.segment_id
            tables["speech_acts"].append(row)

        for explanation in segment.explanations:
            row = explanation.to_dict()
            row["segment_id"] = segment.segment_id
            tables["explanations"].append(row)

        for tag in segment.sf_tags:
            row = tag.to_dict()
            row["segment_id"] = segment.segment_id
            tables["sf_tags"].append(row)

        for anchor in segment.temporal_anchors:
            row = anchor.to_dict()
            row["segment_id"] = segment.segment_id
            tables["temporal_anchors"].append(row)

        for anchor in segment.spatial_anchors:
            row = anchor.to_dict()
            row["segment_id"] = segment.segment_id
            tables["spatial_anchors"].append(row)

    return tables


def rows_to_jsonl(rows: List[Dict[str, Any]]) -> str:
    """Serialize `rows` as newline-delimited JSON, one object per line."""
    return "\n".join(json.dumps(row, sort_keys=True) for row in rows)


def rows_to_csv(rows: List[Dict[str, Any]]) -> str:
    """Serialize `rows` as CSV text with a stable, sorted column order.

    Nested values (e.g. an evidence dict, a list of linked IDs) are
    JSON-encoded into their cell rather than dropped, so no information is
    lost in the CSV form even though it is a flatter representation than
    JSONL.
    """
    if not rows:
        return ""
    fieldnames = sorted({key for row in rows for key in row})
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        flat_row = {
            key: (
                json.dumps(value, sort_keys=True)
                if isinstance(value, (dict, list))
                else value
            )
            for key, value in row.items()
        }
        writer.writerow(flat_row)
    return buffer.getvalue()


def export_analysis_tables(
    story: schema.StoryWorldAnnotation, output_dir: str
) -> Dict[str, str]:
    """Write JSONL and CSV derived tables for `story` to `output_dir`.

    Args:
        story: A StoryWorldAnnotation to export.
        output_dir: Directory to write "<table_name>.jsonl"/".csv" files
            into. Must already exist.

    Returns:
        A dict of "<table_name>.<ext>" -> the path written.
    """
    tables = build_analysis_tables(story)
    written: Dict[str, str] = {}

    for table_name, rows in tables.items():
        jsonl_path = os.path.join(output_dir, f"{table_name}.jsonl")
        with open(jsonl_path, "w", encoding="utf-8") as f:
            f.write(rows_to_jsonl(rows))
        written[f"{table_name}.jsonl"] = jsonl_path

        csv_path = os.path.join(output_dir, f"{table_name}.csv")
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            f.write(rows_to_csv(rows))
        written[f"{table_name}.csv"] = csv_path

    return written
