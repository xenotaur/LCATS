"""Deterministic story preparation for science-fiction analysis."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
import re
from typing import Any, Iterable

from lcats.analysis.corpus.discovery import CANONICAL_STORY_FILENAME

PREPARATION_CONFIG_VERSION = "sf-preparation-config-v1"
MANIFEST_VERSION = "sf-preparation-manifest-v1"
STORY_HASH_ALGORITHM = "sha256"


@dataclasses.dataclass(frozen=True)
class PreparationConfig:
    """Versioned knobs for deterministic preparation and chunk planning."""

    version: str = PREPARATION_CONFIG_VERSION
    whole_story_max_chars: int = 120_000
    chunk_target_chars: int = 60_000
    chunk_max_chars: int = 75_000
    chunk_overlap_paragraphs: int = 1
    boundary_heading_max_chars: int = 96

    def __post_init__(self) -> None:
        if self.version != PREPARATION_CONFIG_VERSION:
            raise ValueError(f"Unsupported preparation config version: {self.version}")
        if self.whole_story_max_chars < 1:
            raise ValueError("whole_story_max_chars must be positive")
        if self.chunk_target_chars < 1:
            raise ValueError("chunk_target_chars must be positive")
        if self.chunk_max_chars < self.chunk_target_chars:
            raise ValueError("chunk_max_chars must be >= chunk_target_chars")
        if self.chunk_overlap_paragraphs < 0:
            raise ValueError("chunk_overlap_paragraphs must be non-negative")
        if self.boundary_heading_max_chars < 1:
            raise ValueError("boundary_heading_max_chars must be positive")

    def to_manifest(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class Paragraph:
    """A stable paragraph anchor in normalized story text."""

    paragraph_id: str
    index: int
    start_char: int
    end_char: int
    text: str
    is_section_boundary: bool = False

    def to_manifest(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class ChunkPlan:
    """A paragraph-aligned chunk with explicit overlap accounting."""

    chunk_id: str
    index: int
    paragraph_ids: tuple[str, ...]
    core_paragraph_ids: tuple[str, ...]
    overlap_before_ids: tuple[str, ...]
    overlap_after_ids: tuple[str, ...]
    start_char: int
    end_char: int
    text: str

    def to_manifest(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "index": self.index,
            "paragraph_ids": list(self.paragraph_ids),
            "core_paragraph_ids": list(self.core_paragraph_ids),
            "overlap_before_ids": list(self.overlap_before_ids),
            "overlap_after_ids": list(self.overlap_after_ids),
            "start_char": self.start_char,
            "end_char": self.end_char,
            "char_count": len(self.text),
            "text_hash": hash_text(self.text),
        }


@dataclasses.dataclass(frozen=True)
class StoryPreparation:
    """Prepared story text, anchors, and deterministic chunk manifest."""

    manifest_version: str
    story_path: str
    story_name: str
    story_hash: str
    normalized_text: str
    paragraphs: tuple[Paragraph, ...]
    whole_story_eligible: bool
    chunks: tuple[ChunkPlan, ...]
    config: PreparationConfig

    def to_manifest(self, *, include_text: bool = False) -> dict[str, Any]:
        manifest: dict[str, Any] = {
            "manifest_version": self.manifest_version,
            "story_path": self.story_path,
            "story_name": self.story_name,
            "story_hash_algorithm": STORY_HASH_ALGORITHM,
            "story_hash": self.story_hash,
            "normalized_char_count": len(self.normalized_text),
            "paragraphs": [paragraph.to_manifest() for paragraph in self.paragraphs],
            "whole_story_eligible": self.whole_story_eligible,
            "chunks": [chunk.to_manifest() for chunk in self.chunks],
            "config": self.config.to_manifest(),
        }
        if include_text:
            manifest["normalized_text"] = self.normalized_text
        return manifest


def prepare_story_file(
    story_path: str | pathlib.Path,
    *,
    config: PreparationConfig | None = None,
) -> StoryPreparation:
    """Load a canonical story bucket and produce deterministic preparation data."""

    path = pathlib.Path(story_path)
    if path.name != CANONICAL_STORY_FILENAME:
        raise ValueError(
            f"Expected canonical story file named {CANONICAL_STORY_FILENAME}"
        )
    with path.open("r", encoding="utf-8") as handle:
        story_data = json.load(handle)
    if not isinstance(story_data, dict):
        raise TypeError(f"story file must contain a JSON object: {path}")
    return prepare_story_data(story_data, story_path=path, config=config)


def prepare_story_data(
    story_data: dict[str, Any],
    *,
    story_path: str | pathlib.Path,
    config: PreparationConfig | None = None,
) -> StoryPreparation:
    """Prepare an already-loaded story mapping without mutating it."""

    active_config = config or PreparationConfig()
    raw_body = story_data.get("body", "")
    if not isinstance(raw_body, str):
        raise TypeError("story body must be a string")
    normalized_text = normalize_story_text(raw_body)
    if not normalized_text:
        raise ValueError("story body is empty after normalization")

    paragraphs = tuple(split_paragraphs(normalized_text, config=active_config))
    if not paragraphs:
        raise ValueError("story body contains no paragraphs after normalization")

    whole_story_eligible = len(normalized_text) <= active_config.whole_story_max_chars
    chunks = tuple(
        plan_chunks(
            normalized_text,
            paragraphs,
            whole_story_eligible=whole_story_eligible,
            config=active_config,
        )
    )
    story_name = story_data.get("name", "")
    if not isinstance(story_name, str):
        story_name = str(story_name)

    return StoryPreparation(
        manifest_version=MANIFEST_VERSION,
        story_path=str(pathlib.Path(story_path)),
        story_name=story_name,
        story_hash=hash_text(normalized_text),
        normalized_text=normalized_text,
        paragraphs=paragraphs,
        whole_story_eligible=whole_story_eligible,
        chunks=chunks,
        config=active_config,
    )


def normalize_story_text(text: str) -> str:
    """Normalize analysis text without changing source files."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.rstrip() for line in normalized.split("\n"))
    return normalized.strip()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_paragraphs(
    normalized_text: str,
    *,
    config: PreparationConfig,
) -> Iterable[Paragraph]:
    """Yield paragraphs with stable IDs and character spans."""

    paragraph_index = 0
    for match in re.finditer(
        r"\S(?:.*?)(?=\n{2,}\s*\S|\Z)", normalized_text, re.DOTALL
    ):
        text = match.group(0).strip("\n")
        if not text.strip():
            continue
        start = match.start()
        end = start + len(text)
        yield Paragraph(
            paragraph_id=f"p{paragraph_index + 1:05d}",
            index=paragraph_index,
            start_char=start,
            end_char=end,
            text=text,
            is_section_boundary=is_section_boundary(
                text, max_chars=config.boundary_heading_max_chars
            ),
        )
        paragraph_index += 1


def is_section_boundary(text: str, *, max_chars: int) -> bool:
    """Detect simple chapter or section headings used as preferred cut points."""

    stripped = " ".join(text.strip().split())
    if not stripped or len(stripped) > max_chars or "\n" in text.strip():
        return False
    if re.fullmatch(r"(?i)(chapter|section|part|book)\s+([ivxlcdm]+|\d+).*", stripped):
        return True
    if re.fullmatch(r"(?i)[ivxlcdm]+\.?", stripped):
        return True
    return stripped.isupper() and any(character.isalpha() for character in stripped)


def plan_chunks(
    normalized_text: str,
    paragraphs: tuple[Paragraph, ...],
    *,
    whole_story_eligible: bool,
    config: PreparationConfig,
) -> Iterable[ChunkPlan]:
    if whole_story_eligible:
        yield _build_chunk(
            index=0,
            chunk_paragraphs=paragraphs,
            core_paragraphs=paragraphs,
            overlap_before=(),
            overlap_after=(),
            normalized_text=normalized_text,
        )
        return

    core_ranges = _core_ranges(paragraphs, config=config)
    for index, (core_start, core_end) in enumerate(core_ranges):
        chunk_start, chunk_end = _chunk_window_for_core(
            paragraphs, core_start=core_start, core_end=core_end, config=config
        )
        yield _build_chunk(
            index=index,
            chunk_paragraphs=paragraphs[chunk_start:chunk_end],
            core_paragraphs=paragraphs[core_start:core_end],
            overlap_before=paragraphs[chunk_start:core_start],
            overlap_after=paragraphs[core_end:chunk_end],
            normalized_text=normalized_text,
        )


def _core_ranges(
    paragraphs: tuple[Paragraph, ...],
    *,
    config: PreparationConfig,
) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start = 0
    while start < len(paragraphs):
        end = _choose_core_end(paragraphs, start=start, config=config)
        ranges.append((start, end))
        start = end
    return ranges


def _choose_core_end(
    paragraphs: tuple[Paragraph, ...],
    *,
    start: int,
    config: PreparationConfig,
) -> int:
    candidates: list[tuple[int, int, bool]] = []
    for end in range(start + 1, len(paragraphs) + 1):
        if (
            _planned_chunk_len(
                paragraphs, core_start=start, core_end=end, config=config
            )
            > config.chunk_max_chars
        ):
            if end == start + 1:
                candidates.append(
                    (end, _paragraph_window_len(paragraphs, start, end), False)
                )
            break
        core_len = _paragraph_window_len(paragraphs, start, end)
        boundary_after = end < len(paragraphs) and paragraphs[end].is_section_boundary
        candidates.append((end, core_len, boundary_after))

    if not candidates:
        return start + 1

    boundary_candidates = [candidate for candidate in candidates if candidate[2]]
    if boundary_candidates:
        return min(
            boundary_candidates,
            key=lambda candidate: (
                abs(candidate[1] - config.chunk_target_chars),
                candidate[0],
            ),
        )[0]

    target_candidates = [
        candidate
        for candidate in candidates
        if candidate[1] >= config.chunk_target_chars
    ]
    if target_candidates:
        return target_candidates[0][0]
    return candidates[-1][0]


def _planned_chunk_len(
    paragraphs: tuple[Paragraph, ...],
    *,
    core_start: int,
    core_end: int,
    config: PreparationConfig,
) -> int:
    chunk_start = max(0, core_start - config.chunk_overlap_paragraphs)
    chunk_end = min(len(paragraphs), core_end + config.chunk_overlap_paragraphs)
    return _paragraph_window_len(paragraphs, chunk_start, chunk_end)


def _chunk_window_for_core(
    paragraphs: tuple[Paragraph, ...],
    *,
    core_start: int,
    core_end: int,
    config: PreparationConfig,
) -> tuple[int, int]:
    chunk_start = core_start
    chunk_end = core_end

    for _ in range(config.chunk_overlap_paragraphs):
        candidate_start = chunk_start - 1
        if candidate_start < 0:
            break
        if (
            _paragraph_window_len(paragraphs, candidate_start, chunk_end)
            > config.chunk_max_chars
        ):
            break
        chunk_start = candidate_start

    for _ in range(config.chunk_overlap_paragraphs):
        candidate_end = chunk_end + 1
        if candidate_end > len(paragraphs):
            break
        if (
            _paragraph_window_len(paragraphs, chunk_start, candidate_end)
            > config.chunk_max_chars
        ):
            break
        chunk_end = candidate_end

    return chunk_start, chunk_end


def _paragraph_window_len(
    paragraphs: tuple[Paragraph, ...],
    start: int,
    end: int,
) -> int:
    return paragraphs[end - 1].end_char - paragraphs[start].start_char


def _build_chunk(
    *,
    index: int,
    chunk_paragraphs: tuple[Paragraph, ...],
    core_paragraphs: tuple[Paragraph, ...],
    overlap_before: tuple[Paragraph, ...],
    overlap_after: tuple[Paragraph, ...],
    normalized_text: str,
) -> ChunkPlan:
    start_char = chunk_paragraphs[0].start_char
    end_char = chunk_paragraphs[-1].end_char
    return ChunkPlan(
        chunk_id=f"c{index + 1:04d}",
        index=index,
        paragraph_ids=tuple(paragraph.paragraph_id for paragraph in chunk_paragraphs),
        core_paragraph_ids=tuple(
            paragraph.paragraph_id for paragraph in core_paragraphs
        ),
        overlap_before_ids=tuple(
            paragraph.paragraph_id for paragraph in overlap_before
        ),
        overlap_after_ids=tuple(paragraph.paragraph_id for paragraph in overlap_after),
        start_char=start_char,
        end_char=end_char,
        text=normalized_text[start_char:end_char],
    )


def assert_gap_free_core_coverage(preparation: StoryPreparation) -> None:
    """Raise if chunk cores do not cover every paragraph exactly once."""

    expected = [paragraph.paragraph_id for paragraph in preparation.paragraphs]
    actual = [
        paragraph_id
        for chunk in preparation.chunks
        for paragraph_id in chunk.core_paragraph_ids
    ]
    if actual != expected:
        raise ValueError("chunk core paragraphs do not provide gap-free coverage")
