"""Story quality and genre assessment using the Claude API."""

from __future__ import annotations

import pathlib
from dataclasses import asdict, dataclass, field

from lcats.llm import tool_schema as tool_schema_module

VALID_GENRES = (
    "science fiction",
    "horror",
    "humor",
    "western",
    "romance",
    "mystery",
    "fantasy",
    "adventure",
)

_GENRE_DEFINITIONS = """\
  - science fiction: speculative technology, space, aliens, time travel, future societies
  - horror: dread, supernatural threat, psychological terror, monsters, dark atmosphere
  - humor: comedic intent as the primary mode, farce, wit, absurdity, satire played for laughs
  - western: frontier American West, cowboys, outlaws, settlers, frontier justice
  - romance: central love story with emotional relationship development as the primary plot
  - mystery: a puzzle or crime to be solved, clues, investigation, a detective or amateur sleuth
  - fantasy: magic, mythical creatures, invented worlds or physics not explained as technology
  - adventure: a physical journey or quest with danger and action as the primary plot engine
  - other: does not fit any of the eight target genres"""

_SPECIALS_SECTION = """\
SPECIAL CHARACTERS: If the story contains non-ASCII or unusual characters, are they:
  - author_intentional: dialect spelling, verse, period typography, accented names
  - extraction_artifact: mojibake, garbled encoding, OCR errors, encoding artifacts
  - error: clearly corrupted, unreadable text passages
  - none: no unusual characters"""

_QUALITY_SECTION = """\
QUALITY ISSUES: Flag any:
  - Transcriber notes, editor commentary, or Project Gutenberg boilerplate inside the body
  - Copyright notices, disclaimers, or legal text embedded in the story body
  - Tables of contents, chapter listings, or front matter inside the text
  - Significant formatting artifacts (stray markup, repeated separators, etc.)"""

ASSESSMENT_TOOL = tool_schema_module.strict_tool_schema(
    {
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
                "detected_genre": {
                    "type": "string",
                    "enum": list(VALID_GENRES) + ["other"],
                    "description": (
                        "The genre this story most likely belongs to, determined by "
                        "independent analysis without reference to any claimed genre. "
                        "Use 'other' if the story does not fit any of the eight target genres."
                    ),
                },
                "detected_genre_confidence": {
                    "type": "number",
                    "description": "Confidence in the detected genre, 0.0 to 1.0.",
                },
                "genre_verdict": {
                    "type": "string",
                    "enum": ["confirmed", "disputed", "wrong", "detected"],
                    "description": (
                        "confirmed: story belongs to the claimed target genre. "
                        "disputed: story has genre elements but is borderline or mixed. "
                        "wrong: story does not belong to the claimed genre. "
                        "detected: no genre was claimed; use this value in detect-only mode."
                    ),
                },
                "genre_suggestion": {
                    "type": "string",
                    "description": (
                        "If genre_verdict is wrong or disputed, any additional nuance "
                        "about the actual genre beyond the detected_genre enum value "
                        "(e.g. 'Gothic mystery-horror hybrid'). Omit or leave empty otherwise."
                    ),
                },
                "secondary_genre": {
                    "type": "string",
                    "description": (
                        "A free-text classificatory tag for a non-priority genre or "
                        "category the story also fits, beyond the eight target genres "
                        "(e.g. 'war', 'medical', 'children's'). Always evaluate this "
                        "field, in both detect and lens mode, regardless of "
                        "genre_verdict — unlike genre_suggestion, which only applies "
                        "to wrong/disputed lens results. Omit or leave empty if no "
                        "additional non-priority category applies."
                    ),
                },
                "specials_verdict": {
                    "type": "string",
                    "enum": [
                        "author_intentional",
                        "extraction_artifact",
                        "error",
                        "none",
                    ],
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
                "detected_genre",
                "detected_genre_confidence",
                "genre_verdict",
                "secondary_genre",
                "specials_verdict",
                "summary",
                "issues",
            ],
        },
    }
)

# Detect mode: no claimed genre; model identifies genre independently.
DETECT_SYSTEM_PROMPT = f"""\
You are a literary corpus quality assessor identifying genre and quality \
for a mixed research corpus.

The corpus targets eight genres: science fiction, horror, humor, western, \
romance, mystery, fantasy, and adventure.

Assess the provided story for inclusion in a curated corpus:

GENRE DETECTION: Identify which of the eight target genres best describes \
this story, or "other" if none fits.
{_GENRE_DEFINITIONS}

SECONDARY GENRE: Independently of the above, note any additional non-priority \
classificatory category the story also fits (e.g. "war", "medical", \
"children's") in secondary_genre. Leave it empty if none applies.

WELLFORMEDNESS: Does the story have a clear beginning and ending? Is it a \
complete standalone narrative — not a chapter fragment, excerpt, or part of \
a longer work?

{_SPECIALS_SECTION}

{_QUALITY_SECTION}

VERDICT RULES:
  - include: wellformed + detected genre is one of the eight targets + no disqualifying issues
  - exclude: story does not fit any target genre (detected_genre: other), \
incomplete, or serious quality problems
  - review: borderline case — reasonable people could disagree

Record your assessment using the record_story_assessment tool. \
Set genre_verdict to "detected". Keep the summary to one or two sentences.\
"""

# Lens mode: a genre is claimed; model detects independently then evaluates the claim.
SYSTEM_PROMPT_TEMPLATE = f"""\
You are a literary corpus quality assessor for a {{genre}} fiction research project.

Assess the provided story for inclusion in a curated corpus:

GENRE DETECTION: First, independently identify which of the eight target genres \
best describes this story — without reference to the claimed genre.
{_GENRE_DEFINITIONS}

SECONDARY GENRE: Independently of the above, note any additional non-priority \
classificatory category the story also fits (e.g. "war", "medical", \
"children's") in secondary_genre. Leave it empty if none applies.

GENRE ACCURACY: Having made your independent detection above, now evaluate \
the claimed genre "{{genre}}". Does the story actually belong to that genre?
  - confirmed: story clearly belongs to the claimed genre
  - disputed: story has some genre elements but is borderline or mixed
  - wrong: story does not belong to the claimed genre

WELLFORMEDNESS: Does the story have a clear beginning and ending? Is it a \
complete standalone narrative — not a chapter fragment, excerpt, or part of \
a longer work?

{_SPECIALS_SECTION}

{_QUALITY_SECTION}

VERDICT RULES:
  - include: wellformed + genre_verdict confirmed + no disqualifying issues
  - exclude: incomplete story, genre_verdict wrong, or serious quality problems
  - review: borderline case or genre_verdict disputed — reasonable people could disagree

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
    detected_genre: str = "other"
    detected_genre_confidence: float = 0.0
    genre_verdict: str = "detected"
    genre_suggestion: str = ""
    secondary_genre: str = ""
    specials_verdict: str = "none"
    summary: str = ""
    issues: list = field(default_factory=list)
    error: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    backend_model: str = ""

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
    genre: str = "",
    backend=None,
    model: str = "claude-opus-4-8",
    max_body_chars: int = 100_000,
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> AssessmentResult:
    """Assess a single corpus JSON file for quality and genre fit.

    When genre is empty, runs in detect mode: the model identifies the genre
    independently and sets genre_verdict to "detected". When genre is provided,
    runs in lens mode: the model detects genre independently then evaluates
    whether the story matches the claimed genre.

    max_tokens caps the assessment response (findings summary, issues list,
    etc.); the previous hardcoded 2048 ceiling truncated on longer/messier
    real stories (WI-ANNOTATE-0050).

    temperature defaults to this function's long-standing hardcoded value
    (tuned for Anthropic/OpenAI); callers driving a model with its own
    documented sampling recommendation (e.g. a local model via a different
    backend) should override it explicitly rather than inherit a value
    tuned for a different model family.
    """
    if backend is None:
        raise ValueError("assess_story requires a backend instance")

    title = file_path.parent.name
    if not title:
        # Bare relative path (e.g. Path("story.json") run from inside the
        # bucket dir itself) -- resolve to recover the real directory name.
        # Guarded: this runs before the try/except below, and unlike pure
        # string ops, resolve() touches the filesystem and can raise
        # (broken symlink loop, permission error) -- fall back to ""
        # rather than letting an unrelated fallback-title computation
        # crash the whole call.
        try:
            title = file_path.resolve().parent.name
        except OSError:
            pass
    author = "Unknown"
    url = ""

    try:
        title, author, url, findings, full_body = run_preflight(file_path)
        findings_text = _format_findings(findings)

        body = full_body
        if max_body_chars and len(body) > max_body_chars:
            body = body[:max_body_chars] + "\n\n[... text truncated ...]"

        if genre:
            system_prompt = SYSTEM_PROMPT_TEMPLATE.format(genre=genre)
            genre_line = f"Claimed genre: {genre}\n"
        else:
            system_prompt = DETECT_SYSTEM_PROMPT
            genre_line = ""

        user_message = (
            f"STORY METADATA:\n"
            f"Title: {title}\n"
            f"Author: {author}\n"
            f"Source URL: {url}\n"
            f"{genre_line}"
            f"\nPRE-FLIGHT QA FINDINGS:\n{findings_text}\n"
            f"\nSTORY TEXT:\n{body}"
        )

        backend_response = backend.complete(
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tool=ASSESSMENT_TOOL,
        )
        a = backend_response.tool_result
        if a is None:
            # backend_response is a real, billed API response even though
            # tool_result is None (a backend/test-double edge case, not
            # reachable via AnthropicBackend/OpenAIBackend today - both
            # raise TruncatedResponseError/NoToolCallError instead of
            # returning tool_result=None). Forward its usage rather than
            # discarding it, matching the exception-path fix below.
            return AssessmentResult(
                file_path=str(file_path),
                title=title,
                author=author,
                url=url,
                target_genre=genre,
                verdict="review",
                error="Backend returned no tool result",
                input_tokens=backend_response.input_tokens,
                output_tokens=backend_response.output_tokens,
                backend_model=backend_response.model,
            )

        return AssessmentResult(
            file_path=str(file_path),
            title=title,
            author=author,
            url=url,
            target_genre=genre,
            verdict=a.get("verdict", "review"),
            exclude_reason=a.get("exclude_reason", ""),
            wellformed=bool(a.get("wellformed", True)),
            detected_genre=a.get("detected_genre", "other"),
            detected_genre_confidence=max(
                0.0, min(1.0, float(a.get("detected_genre_confidence", 0.0)))
            ),
            genre_verdict=a.get("genre_verdict", "detected"),
            genre_suggestion=a.get("genre_suggestion", ""),
            secondary_genre=a.get("secondary_genre", ""),
            specials_verdict=a.get("specials_verdict", "none"),
            summary=a.get("summary", ""),
            issues=list(a.get("issues", [])),
            input_tokens=backend_response.input_tokens,
            output_tokens=backend_response.output_tokens,
            backend_model=backend_response.model,
        )

    except Exception as exc:
        # backend.TruncatedResponseError and backend.NoToolCallError both
        # carry input_tokens/output_tokens for a real, billed response
        # that failed only at the tool-result-parsing stage (see their own
        # docstrings) - forward that usage generically via getattr rather
        # than special-casing each exception type, so any future backend
        # exception carrying the same attributes is covered automatically.
        # Exceptions with no such attributes (e.g. a network error before
        # any response arrived) correctly default to zero usage here.
        return AssessmentResult(
            file_path=str(file_path),
            title=title,
            author=author,
            url=url,
            target_genre=genre,
            verdict="review",
            error=str(exc),
            input_tokens=getattr(exc, "input_tokens", 0),
            output_tokens=getattr(exc, "output_tokens", 0),
        )
