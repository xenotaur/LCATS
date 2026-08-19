"""Diff extracted entity identities across benchmark candidate results.

Usage examples:

    python lcats/experimental/model_comparison/entity_diff.py \
      anthropic_opus/results.json ollama_qwen3_8b/results.json

    python lcats/experimental/model_comparison/entity_diff.py

With no arguments, compares every ``*/results.json`` file under this
directory. The script is read-only and makes no LLM calls.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

_HERE = pathlib.Path(__file__).resolve().parent
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class EntityIdentity:
    """Normalized entity identity used for set comparisons."""

    normalized_name: str
    entity_type: str = field(compare=False)
    display_name: str = field(compare=False)


@dataclass(frozen=True)
class CandidateEntities:
    """Entities loaded from one candidate result file."""

    candidate: str
    path: pathlib.Path
    entities: frozenset[EntityIdentity]
    comparable: bool = True
    not_comparable_reason: str = ""


def normalize_name(name: str) -> str:
    """Normalize a model-produced entity name for coarse set comparison."""
    return _WHITESPACE.sub(" ", name.strip()).casefold()


def _candidate_name(path: pathlib.Path, row: dict[str, Any]) -> str:
    return str(row.get("candidate") or path.parent.name)


def _entity_identity(entity: Any) -> EntityIdentity | None:
    if isinstance(entity, dict):
        raw_name = entity.get("canonical_name") or entity.get("name") or entity.get("entity")
        raw_type = entity.get("entity_type") or entity.get("type") or ""
    elif isinstance(entity, str):
        raw_name = entity
        raw_type = ""
    else:
        return None

    if not isinstance(raw_name, str) or not raw_name.strip():
        return None

    entity_type = raw_type.strip() if isinstance(raw_type, str) else ""
    display_name = _WHITESPACE.sub(" ", raw_name.strip())
    return EntityIdentity(
        normalized_name=normalize_name(display_name),
        entity_type=entity_type,
        display_name=display_name,
    )


def _not_comparable_reason(row: dict[str, Any]) -> str:
    error_type = row.get("error_type")
    if row.get("success") is False and error_type:
        return f"not comparable: {error_type}"
    if row.get("success") is False:
        return "not comparable: benchmark failed"
    return "stale result: rerun benchmark to populate `entities`"


def _identity_preference(identity: EntityIdentity) -> tuple[int, str, str, str, str]:
    """Sort key for a stable representative of one normalized entity name."""
    return (
        0 if identity.entity_type else 1,
        identity.display_name.casefold(),
        identity.entity_type.casefold(),
        identity.display_name,
        identity.entity_type,
    )


def _best_identity(
    existing: EntityIdentity | None, candidate: EntityIdentity
) -> EntityIdentity:
    if existing is None:
        return candidate
    if _identity_preference(candidate) < _identity_preference(existing):
        return candidate
    return existing


def _dedupe_identities(identities: Iterable[EntityIdentity]) -> frozenset[EntityIdentity]:
    by_name: dict[str, EntityIdentity] = {}
    for identity in identities:
        by_name[identity.normalized_name] = _best_identity(
            by_name.get(identity.normalized_name), identity
        )
    return frozenset(by_name.values())


def _representative_entities(
    candidates: Iterable[CandidateEntities],
) -> dict[str, EntityIdentity]:
    representatives: dict[str, EntityIdentity] = {}
    for candidate in candidates:
        for identity in candidate.entities:
            representatives[identity.normalized_name] = _best_identity(
                representatives.get(identity.normalized_name), identity
            )
    return representatives


def load_candidate_entities(path: pathlib.Path) -> CandidateEntities:
    """Load one candidate results file into a normalized entity set."""
    row = json.loads(path.read_text(encoding="utf-8"))
    if row.get("success") is False:
        return CandidateEntities(
            candidate=_candidate_name(path, row),
            path=path,
            entities=frozenset(),
            comparable=False,
            not_comparable_reason=_not_comparable_reason(row),
        )

    entities = row.get("entities")
    if not isinstance(entities, list):
        return CandidateEntities(
            candidate=_candidate_name(path, row),
            path=path,
            entities=frozenset(),
            comparable=False,
            not_comparable_reason=_not_comparable_reason(row),
        )

    identities = _dedupe_identities(
        identity for entity in entities if (identity := _entity_identity(entity)) is not None
    )
    return CandidateEntities(
        candidate=_candidate_name(path, row),
        path=path,
        entities=identities,
    )


def default_result_paths() -> list[pathlib.Path]:
    """Return all candidate entity benchmark result files."""
    return sorted(_HERE.glob("*/results.json"))


def _format_entities(entities: Iterable[EntityIdentity]) -> str:
    formatted = []
    for entity in sorted(
        entities, key=lambda item: (item.normalized_name, item.entity_type, item.display_name)
    ):
        suffix = f" [{entity.entity_type}]" if entity.entity_type else ""
        formatted.append(f"{entity.display_name}{suffix}")
    return ", ".join(formatted) if formatted else "-"


def build_report(candidates: list[CandidateEntities]) -> str:
    """Build a human-readable entity-diff report."""
    if not candidates:
        return "No candidate results supplied."

    comparable_candidates = [candidate for candidate in candidates if candidate.comparable]
    not_comparable_candidates = [
        candidate for candidate in candidates if not candidate.comparable
    ]

    lines = ["# Entity Diff", ""]
    lines.append(
        "Normalization: entity names are stripped, internal whitespace is "
        "collapsed, and names are case-folded. Entity type is displayed "
        "when present but is not part of the comparison key."
    )
    lines.append("")
    lines.append("| Candidate | Entities | Source |")
    lines.append("|---|---:|---|")
    for candidate in candidates:
        source = f"`{candidate.path}`"
        if candidate.comparable:
            lines.append(f"| {candidate.candidate} | {len(candidate.entities)} | {source} |")
        else:
            reason = candidate.not_comparable_reason
            lines.append(f"| {candidate.candidate} | n/a | {source} ({reason}) |")

    if not_comparable_candidates:
        lines.extend(["", "## Not Comparable", ""])
        for candidate in not_comparable_candidates:
            lines.append(f"- {candidate.candidate}: {candidate.not_comparable_reason}")

    if len(comparable_candidates) < 2:
        lines.extend(
            [
                "",
                "Entity diff requires at least two comparable result files.",
            ]
        )
        return "\n".join(lines).rstrip() + "\n"

    representative_by_name = _representative_entities(comparable_candidates)
    entity_name_sets = [
        {identity.normalized_name for identity in candidate.entities}
        for candidate in comparable_candidates
    ]
    common_names = set.intersection(*entity_name_sets)
    union_names = set.union(*entity_name_sets)

    lines.extend(
        [
            "",
            "## Shared By All",
            "",
            _format_entities(representative_by_name[name] for name in common_names),
            "",
        ]
    )
    lines.extend(["## Candidate-Only Entities", ""])
    for candidate in comparable_candidates:
        other_sets = [
            {identity.normalized_name for identity in other.entities}
            for other in comparable_candidates
            if other is not candidate
        ]
        other_entities = set.union(*other_sets) if other_sets else set()
        candidate_names = {identity.normalized_name for identity in candidate.entities}
        only_names = candidate_names - other_entities
        lines.append(f"### {candidate.candidate}")
        lines.append("")
        lines.append(_format_entities(representative_by_name[name] for name in only_names))
        lines.append("")

    lines.extend(["## Missing Per Candidate", ""])
    for candidate in comparable_candidates:
        candidate_names = {identity.normalized_name for identity in candidate.entities}
        missing_names = union_names - candidate_names
        lines.append(f"### {candidate.candidate}")
        lines.append("")
        lines.append(_format_entities(representative_by_name[name] for name in missing_names))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diff entity identities across model-comparison results.json files."
    )
    parser.add_argument(
        "results",
        nargs="*",
        type=pathlib.Path,
        help="Candidate results.json files. Defaults to every */results.json.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = args.results or default_result_paths()
    candidates = [load_candidate_entities(path) for path in paths]
    print(build_report(candidates), end="")


if __name__ == "__main__":
    main()
