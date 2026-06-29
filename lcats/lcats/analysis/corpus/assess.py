"""Story quality and genre assessment using the Claude API."""

from __future__ import annotations

import pathlib
from dataclasses import asdict, dataclass, field

VALID_GENRES = ("science fiction", "horror", "western", "romance")

ASSESSMENT_TOOL = {
    "name": "record_story_assessment",
    "description": "Record a structured quality and genre assessment for a story.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["include", "exclude", "review"],
                "description": (
                    "include: wellformed + correct genre + no disqualifying issues. "
                    "exclude: incomplete story, wrong genre, or serious quality problems. "
                    "review: borderline — reasonable people could disagree."
                ),
            },
            "exclude_reason": {
                "type": "string",
                "description": (
                    "If verdict is exclude or review, a brief explanation. "
                    "Omit or leave empty for include."
                ),
            },
            "wellformed": {
                "type": "boolean",
                "description": (
                    "True if the story has a clear beginning and ending and reads "
                    "as a complete standalone narrative."
                ),
            },
            "genre_match": {
                "type": "string",
                "enum": ["confirmed", "disputed", "wrong"],
                "description": "Whether the story belongs to the claimed target genre.",
            },
            "genre_confidence": {
                "type": "number",
                "description": "Confidence in the genre assessment, 0.0 to 1.0.",
            },
            "genre_suggestion": {
                "type": "string",
                "description": (
                    "If genre_match is wrong or disputed, the most likely actual genre. "
                    "Omit or leave empty otherwise."
                ),
            },
            "specials_verdict": {
                "type": "string",
                "enum": ["author_intentional", "extraction_artifact", "error", "none"],
                "description": (
                    "Assessment of any non-ASCII or unusual characters in the text. "
                    "author_intentional: dialect, verse, period typography, accented names. "
                    "extraction_artifact: mojibake, garbled encoding, OCR errors. "
                    "error: clearly corrupted, unreadable passages. "
                    "none: no unusual characters present."
                ),
            },
            "summary": {
                "type": "string",
                "description": "One to two sentence plot summary of the story.",
            },
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": (
                                "Issue category: transcriber_note, copyright_notice, "
                                "toc_remnant, formatting_artifact, incomplete_text, or other."
                            ),
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                        },
                        "description": {"type": "string"},
                    },
                    "required": ["type", "severity", "description"],
                },
                "description": "Quality issues found in the story text.",
            },
        },
        "required": [
            "verdict",
            "wellformed",
            "genre_match",
            "genre_confidence",
            "specials_verdict",
            "summary",
            "issues",
        ],
    },
}

SYSTEM_PROMPT_TEMPLATE = """\
You are a literary corpus quality assessor for a {genre} fiction research project.

Assess the provided story for inclusion in a curated corpus:

WELLFORMEDNESS: Does the story have a clear beginning and ending? Is it a complete \
standalone narrative — not a chapter fragment, excerpt, or part of a longer work?

GENRE ACCURACY: Does the story actually belong to the genre "{genre}"?
  - science fiction: speculative technology, space, aliens, time travel, future societies
  - horror: dread, supernatural threat, psychological terror, monsters, dark atmosphere
  - western: frontier American West, cowboys, outlaws, settlers, frontier justice
  - romance: central love story with emotional relationship development as the primary plot

SPECIAL CHARACTERS: If the story contains non-ASCII or unusual characters, are they:
  - author_intentional: dialect spelling, verse, period typography, accented names
  - extraction_artifact: mojibake, garbled encoding, OCR errors, encoding artifacts
  - error: clearly corrupted, unreadable text passages
  - none: no unusual characters

QUALITY ISSUES: Flag any:
  - Transcriber notes, editor commentary, or Project Gutenberg boilerplate inside the body
  - Copyright notices, disclaimers, or legal text embedded in the story body
  - Tables of contents, chapter listings, or front matter inside the text
  - Significant formatting artifacts (stray markup, repeated separators, etc.)

VERDICT RULES:
  - include: wellformed + correct genre + no disqualifying issues
  - exclude: incomplete story, wrong genre, or serious quality problems
  - review: borderline case — reasonable people could disagree

Record your assessment using the record_story_assessment tool. \
Keep the summary to one or two sentences.\
"""


@dataclass
class AssessmentResult:
    file_path: str
    title: str
    author: str
    url: str
    target_genre: str
    verdict: str
    exclude_reason: str = ""
    wellformed: bool = True
    genre_match: str = "confirmed"
    genre_confidence: float = 1.0
    genre_suggestion: str = ""
    specials_verdict: str = "none"
    summary: str = ""
    issues: list = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _format_findings(findings: list) -> str:
    if not findings:
        return "None detected."
    return "\n".join(
        f"- [{f.severity.upper()}] {f.kind}: {f.message}" for f in findings
    )


def run_preflight(
    file_path: pathlib.Path,
) -> tuple[str, str, str, list, str]:
    """Read a story file and run QA detectors without calling the API.

    Returns (title, author, url, findings, full_body). Raises on file or parse
    errors.
    """
    from lcats.analysis.corpus.cli import (
        coerce_story_text,
        infer_story_title,
        read_story_data,
    )
    from lcats.analysis.corpus import qa

    data = read_story_data(file_path)
    title = infer_story_title(data, file_path)
    metadata = data.get("metadata") or {}
    author = metadata.get("author", "Unknown")
    url = metadata.get("url", "")
    full_body = coerce_story_text(data.get("body", ""))
    findings = qa.run_detectors(full_body)
    return title, author, url, findings, full_body


def assess_story(
    file_path: pathlib.Path,
    genre: str,
    client,
    model: str = "claude-opus-4-8",
    max_body_chars: int = 100_000,
) -> AssessmentResult:
    """Assess a single corpus JSON file for quality and genre fit."""
    title = file_path.stem
    author = "Unknown"
    url = ""

    try:
        title, author, url, findings, full_body = run_preflight(file_path)
        findings_text = _format_findings(findings)

        body = full_body
        if max_body_chars and len(body) > max_body_chars:
            body = body[:max_body_chars] + "\n\n[... text truncated ...]"

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(genre=genre)
        user_message = (
            f"STORY METADATA:\n"
            f"Title: {title}\n"
            f"Author: {author}\n"
            f"Source URL: {url}\n"
            f"Claimed genre: {genre}\n"
            f"\nPRE-FLIGHT QA FINDINGS:\n{findings_text}\n"
            f"\nSTORY TEXT:\n{body}"
        )

        with client.messages.stream(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            tools=[ASSESSMENT_TOOL],
            tool_choice={"type": "tool", "name": "record_story_assessment"},
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            message = stream.get_final_message()

        tool_block = next(
            (b for b in message.content if b.type == "tool_use"),
            None,
        )
        if tool_block is None:
            return AssessmentResult(
                file_path=str(file_path),
                title=title,
                author=author,
                url=url,
                target_genre=genre,
                verdict="review",
                error="No tool_use block in API response",
            )

        a = tool_block.input
        return AssessmentResult(
            file_path=str(file_path),
            title=title,
            author=author,
            url=url,
            target_genre=genre,
            verdict=a.get("verdict", "review"),
            exclude_reason=a.get("exclude_reason", ""),
            wellformed=bool(a.get("wellformed", True)),
            genre_match=a.get("genre_match", "confirmed"),
            genre_confidence=float(a.get("genre_confidence", 1.0)),
            genre_suggestion=a.get("genre_suggestion", ""),
            specials_verdict=a.get("specials_verdict", "none"),
            summary=a.get("summary", ""),
            issues=list(a.get("issues", [])),
        )

    except Exception as exc:
        return AssessmentResult(
            file_path=str(file_path),
            title=title,
            author=author,
            url=url,
            target_genre=genre,
            verdict="review",
            error=str(exc),
        )
