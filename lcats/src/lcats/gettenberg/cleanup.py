"""Pure, conservative Gutenberg envelope cleanup over already decoded text.

Only a unique, corroborated delimiter pair can select a content slice. Original
text, physical line endings and all offsets remain available to the caller.
Rules and fixtures are independently authored; qualification sources are recorded
in project/development/gettenberg-cleanup-design.md.
"""

import dataclasses
import re

from lcats.gettenberg import errors

_POLICY = "gutenberg-boundaries-v1"
_MAX_CANDIDATES = 16
_LINE_END = re.compile(r"\r\n|\r|\n")
_SPACE = re.compile(r"[ \t]+")
# Separator whitespace cannot also start the identifier: disjoint repetitions
# keep malformed lines without closing delimiters from quadratic backtracking.
_MARKER = re.compile(
    r"\*\*\*[ \t]*(START|END)[ \t]+OF[ \t]+(THE|THIS)[ \t]+"
    r"PROJECT[ \t]+GUTENBERG[ \t]+EBOOK[ \t]+([^* \t][^*]*)\*\*\*",
    re.IGNORECASE | re.ASCII,
)
# Candidate detection is deliberately broader than accepted marker syntax.
# A damaged or wrapped name must not hide a competing boundary. False positives
# here only preserve the original; removal still requires the complete grammar.
_CANDIDATE = re.compile(r"\*+\s*(?:START|END)\b", re.IGNORECASE)
# Observed historical footer metadata, not a book boundary. Keep this exception
# exact so damaged START-colon book markers still force conservative refusal.
_LICENSE_SECTION_START = "*** START: FULL LICENSE ***"
_BANNER = re.compile(
    r"(?:The[ \t]+)?Project[ \t]+Gutenberg(?:'s[ \t]+.+|[ \t]+eBook[ \t]+of[ \t]+.+)",
    re.IGNORECASE | re.ASCII,
)
_LICENSE = re.compile(
    r"THE[ \t]+FULL[ \t]+PROJECT[ \t]+GUTENBERG(?:™|-tm)?[ \t]+LICENSE",
    re.IGNORECASE | re.ASCII,
)
_END_NOTICE = re.compile(
    r"End[ \t]+of[ \t]+Project[ \t]+Gutenberg's[ \t]+([^ \t].*),[ \t]+by[ \t]+(.+)",
    re.IGNORECASE | re.ASCII,
)


class CleanupInputError(errors.GettenbergError, ValueError):
    """Invalid input or resource bounds; no partial cleanup result is returned."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclasses.dataclass(frozen=True, slots=True)
class CleanupMarker:
    """A whole physical line's half-open character span, including its newline.

    kind is start, end, end_notice, or unrecognized. line is one-based. Identifier
    preserves title/number spelling with only surrounding horizontal space removed.
    Unrecognized marker-like lines have no identifier or style.
    """

    kind: str
    start: int
    end: int
    line: int
    identifier: str | None = None
    style: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class CleanupDiagnostic:
    """Stable explanation code and optional one-based physical line number."""

    code: str
    message: str
    line: int | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class CleanupResult:
    """Exact original text plus a chosen slice and inspectable evidence.

    Offsets count Python Unicode characters, not bytes or grapheme clusters.
    A refused or absent envelope selects the entire original. No output whitespace
    is stripped, and text is computed on access rather than stored a second time.
    """

    original: str
    content_start: int
    content_end: int
    markers: tuple[CleanupMarker, ...]
    diagnostics: tuple[CleanupDiagnostic, ...]
    policy_version: str = _POLICY

    @property
    def text(self) -> str:
        """Return the exact chosen character slice."""
        return self.original[self.content_start : self.content_end]

    @property
    def changed(self) -> bool:
        """Report whether any prefix or suffix was removed."""
        return self.content_start != 0 or self.content_end != len(self.original)


def _lines(text):
    """Yield physical lines lazily, without splitlines' Unicode separators/copies."""
    start = 0
    number = 1
    for ending in _LINE_END.finditer(text):
        yield start, ending.end(), number, text[start : ending.start()]
        start = ending.end()
        number += 1
    if start < len(text):
        yield start, len(text), number, text[start:]


def _label(value):
    """Normalize comparison only; never rewrite the source or retained slice."""
    return _SPACE.sub(" ", value.strip(" \t")).casefold()


def strip_boilerplate(
    text: str, *, max_characters: int = 32 * 1024 * 1024
) -> CleanupResult:
    """Select content only when a unique Gutenberg envelope is corroborated.

    Args:
        text: Decoded plain text. Decode bytes separately; extract HTML separately.
        max_characters: Positive integer input bound, adjustable explicitly.

    Returns:
        Immutable original/slice/marker/diagnostic record. Unsupported, absent or
        ambiguous boundaries preserve all input, rather than guessing a cut.

    Raises:
        CleanupInputError: Non-str input, invalid limit, or input exceeds the limit.
    """
    if not isinstance(text, str):
        raise CleanupInputError("invalid_text", "decode bytes to str before cleanup")
    if type(max_characters) is not int or max_characters < 1:
        raise CleanupInputError(
            "invalid_limit", "max_characters must be a positive integer"
        )
    if len(text) > max_characters:
        raise CleanupInputError("input_too_large", "text exceeds max_characters")

    markers = []
    diagnostics = []
    first_nonblank = None
    previous_nonblank = None
    end_notice = None
    last_license_start = None
    # Keep at most a small number of candidates. Excess evidence means ambiguity,
    # not permission to ignore later markers and select an earlier pair.
    for start, end, line, raw in _lines(text):
        value = raw.strip(" \t")
        if start == 0:
            value = value.removeprefix("\ufeff").lstrip(" \t")
        if value.strip() and first_nonblank is None:
            first_nonblank = (start, value)
        if _LICENSE.fullmatch(value):
            # Only whether a license exists after the end marker matters; retain
            # the latest position, not an unbounded list of repeated headings.
            last_license_start = start
        if _CANDIDATE.match(value.lstrip()) and value != _LICENSE_SECTION_START:
            if len(markers) == _MAX_CANDIDATES:
                diagnostics.append(
                    CleanupDiagnostic(
                        "candidate_limit",
                        "Too many marker-like lines; scan stopped",
                        line,
                    )
                )
                break
            match = _MARKER.fullmatch(value)
            if (
                match
                and match[3].strip(" \t")
                and not any(ord(char) < 32 and char != "\t" for char in match[3])
            ):
                kind, article, identifier = match.groups()
                marker = CleanupMarker(
                    kind.lower(),
                    start,
                    end,
                    line,
                    identifier.strip(" \t"),
                    article.lower(),
                )
                if marker.kind == "end" and previous_nonblank is not None:
                    prior_start, prior_end, prior_line, prior_value = previous_nonblank
                    notice = _END_NOTICE.fullmatch(prior_value)
                    if (
                        notice
                        and _label(notice[1]) == _label(marker.identifier)
                        and notice[2].strip(" \t")
                    ):
                        end_notice = CleanupMarker(
                            "end_notice",
                            prior_start,
                            prior_end,
                            prior_line,
                            notice[1].strip(" \t"),
                            marker.style,
                        )
                markers.append(marker)
            else:
                markers.append(CleanupMarker("unrecognized", start, end, line))
                diagnostics.append(
                    CleanupDiagnostic(
                        "unrecognized_marker",
                        "Unsupported or malformed marker-like line",
                        line,
                    )
                )
        if value.strip():
            previous_nonblank = (start, end, line, value)

    def preserved(code=None, message=None, line=None):
        if code is not None:
            diagnostics.append(CleanupDiagnostic(code, message, line))
        return CleanupResult(text, 0, len(text), tuple(markers), tuple(diagnostics))

    if diagnostics:
        return preserved()
    if not markers:
        return preserved("no_markers", "No qualified envelope markers found")
    starts = [marker for marker in markers if marker.kind == "start"]
    ends = [marker for marker in markers if marker.kind == "end"]
    if len(starts) > 1 or len(ends) > 1:
        return preserved(
            "multiple_markers", "Repeated or nested boundaries are ambiguous"
        )
    if not starts or not ends:
        return preserved("incomplete_pair", "Both start and end markers are required")
    opening, closing = starts[0], ends[0]
    if opening.end > closing.start:
        return preserved("reversed_pair", "End marker precedes start marker")
    if opening.style != closing.style or _label(opening.identifier) != _label(
        closing.identifier
    ):
        return preserved("mismatched_pair", "Marker identifiers or styles disagree")
    if first_nonblank[0] < opening.start and not _BANNER.fullmatch(first_nonblank[1]):
        return preserved("unverified_header", "Removed prefix lacks a Gutenberg banner")
    if text[closing.end :].strip() and not (
        last_license_start is not None and last_license_start >= closing.end
    ):
        return preserved(
            "unverified_footer", "Removed suffix lacks the full-license heading"
        )
    content_end = end_notice.start if end_notice is not None else closing.start
    if not text[opening.end : content_end].strip():
        return preserved(
            "empty_content", "Envelope would leave no non-whitespace content"
        )
    if end_notice is not None:
        markers.insert(markers.index(closing), end_notice)
        diagnostics.append(
            CleanupDiagnostic(
                "end_notice_removed",
                "Title-matching notice corroborated by end marker",
                end_notice.line,
            )
        )
    diagnostics.append(
        CleanupDiagnostic("envelope_removed", "Unique corroborated envelope removed")
    )
    return CleanupResult(
        text, opening.end, content_end, tuple(markers), tuple(diagnostics)
    )
