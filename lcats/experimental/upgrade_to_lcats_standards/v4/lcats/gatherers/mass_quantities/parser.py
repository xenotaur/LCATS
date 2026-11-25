"""Gatherer for single stories from gutenberg"""

# - Should change the line to paragraph for accuracy - TODO?

# Several functions now exist with similar functionality; refactor to
#    collapse?    fix_body, in_body, remove_non_text

from __future__ import annotations

import os
import json
import tempfile
import dataclasses
import re

from lcats import constants
from lcats.utils import names
from lcats.gatherers import normalization
from lcats.gatherers import story_output
from lcats.analysis.corpus import discovery
import pathlib
from lcats.gatherers.mass_quantities import storymap
from lcats.gatherers.mass_quantities import structural_screen
from lcats.gatherers.mass_quantities import boundary_features
from lcats.gatherers.mass_quantities import frontmatter_precision
from lcats.gatherers.mass_quantities import extraction_records
from lcats.gatherers.mass_quantities import publication_year
from lcats.gatherers import registry

import dataclasses
import typing
import unicodedata

START = re.compile(
    r"^\s*\*{3}\s*START OF (?:THE|THIS) PROJECT GUTENBERG (?:EBOOK|ETEXT)\b", re.I
)
END = re.compile(
    r"^\s*\*{3}\s*END OF (?:THE|THIS) PROJECT GUTENBERG (?:EBOOK|ETEXT)\b|^\s*End of (?:the )?(?:Project Gutenberg(?:\'s)?)\b|^\s*End of (?:this )?e-?text\b",
    re.I,
)
EDITOR = re.compile(
    r"^\s*\[\s*(?:transcriber\'s? notes?|transcription notes?|editor\'s? notes?|illustrations?|image|frontispiece|sidenote|caption|plate|figure)\s*(?=[:\].\s])",
    re.I,
)


def _editorial_spelling(line: str) -> str:
    """Fold typographic apostrophes for editorial-label recognition only."""
    return line.replace("\u2019", "\u0027").replace("\u2018", "\u0027")


def _editor_marker(line: str) -> bool:
    return bool(EDITOR.match(_editorial_spelling(line)))


def _editor_heading(line: str) -> bool:
    return bool(EDITOR_UNBRACKETED.match(_editorial_spelling(line)))


EDITOR_UNBRACKETED = re.compile(
    r"^\s*(?:transcriber\'s? notes?|transcription notes?|e-?text notes?|proofreader\'s? notes?)\s*:?\s*$",
    re.I,
)
PRODUCTION = re.compile(
    r"^\s*(?:produced by|e-?text prepared by|transcribed (?:by|from)|prepared by|digitized by|project gutenberg (?:volunteers|team))\b",
    re.I,
)
YEAR = re.compile(r"^(?:1[5-9]\d{2}|20\d{2})\.?$")
META = re.compile(
    r"^(?:copyright\b|all rights reserved|published\b|first published\b|printed\b|illustrated by\b|with illustrations\b|author of\b|translated (?:by|from)\b|\b(?:new york|london|boston|philadelphia|chicago|paris)\b\s*$|by [^\n]{1,30} (?:& co\.|company|press|publishers?)\b)",
    re.I,
)
CHAPTER = re.compile(
    r"^(?:chapter|part|book|prologue|epilogue)\s+(?:[IVXLCDM0-9]+|one|two|three|four|five|six|seven|eight|nine|ten)\b|^(?:[IVXLCDM]{1,8}|\d{1,3})\.?$",
    re.I,
)
SCENE = re.compile(
    r"^(?:\*\s*){3,}$|^(?:#\s*){3,}$|^(?:-\s*){3,}$|^\s*\*\s+\*\s+\*\s*$"
)
FENCE = re.compile(r"^\s*(?:`{3,}|~{3,})\s*$")
THE_END = re.compile(r"^\s*the\s+end[.!]?\s*$", re.I)


@dataclasses.dataclass
class ExtractionDiagnostics:
    title_found: bool = False
    matched_author: typing.Optional[str] = None
    matched_pseudonym: typing.Optional[str] = None
    start_marker_found: bool = False
    end_marker_found: bool = False
    removed_years: tuple[str, ...] = ()
    narrative_start_line: int = 1
    narrative_end_line: int = 1
    boundary_confidence: str = "low"
    removed_editorial_blocks: int = 0
    removed_terminal_signature: typing.Optional[str] = None
    terminal_footnotes: typing.Optional[str] = None
    warnings: tuple[str, ...] = ()

    def to_dict(self):
        return dataclasses.asdict(self)


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).casefold().replace("’", "'")
    value = re.sub(r"[_*]", "", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _title_variants(title: typing.Union[str, typing.Sequence[str], None]) -> list[str]:
    """Include catalog titles and conservative main-title forms.

    A colon often separates a work's main title from a subtitle present
    in the catalog but absent from subsequent display headings. Restrict
    partial forms to a plausible multiword title, not arbitrary prefixes.
    """
    supplied = [title] if isinstance(title, str) else list(title or [])
    supplied = [
        re.sub(r"\s*:\s*\$[a-z]\s*", ": ", x, flags=re.I)
        for x in supplied
        if isinstance(x, str)
    ]
    variants = []
    for candidate in supplied:
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        variants.append(candidate)
        # Printed titles frequently omit a leading article found in catalogs.
        # Only derive an entire heading, never use arbitrary prefix matching.
        words = candidate.strip().split()
        if len(words) >= 3 and words[0].casefold() in ("the", "a", "an"):
            variants.append(" ".join(words[1:]))
        main = re.split(r"\s*[:：]\s*", candidate, maxsplit=1)[0].strip()
        if (
            main != candidate
            and len(_norm(main).split()) >= 2
            and len(_norm(main)) >= 12
        ):
            variants.append(main)
            main_words = main.split()
            if len(main_words) >= 3 and main_words[0].casefold() in ("the", "a", "an"):
                variants.append(" ".join(main_words[1:]))
    return list(dict.fromkeys(variants))


def _title_line(s: str, title: typing.Union[str, typing.Sequence[str], None]) -> bool:
    a = _norm(s)
    for variant in _title_variants(title):
        b = _norm(variant)
        if b and (
            a == b
            or a in {b + " by", "the " + b}
            or (a.startswith(b + " by ") and len(a) < len(b) + 55)
        ):
            return True
    return False


def _title_span(
    lines: typing.Sequence[str],
    position: int,
    limit: int,
    title: typing.Union[str, typing.Sequence[str], None],
) -> typing.Optional[int]:
    """Match a display title across up to three lines, favoring full titles.

    A title with an optional catalog subtitle may match its main heading;
    however a longer full-title match always takes precedence.
    """
    if position >= limit:
        return None
    supplied = [title] if isinstance(title, str) else list(title or [])
    supplied = [
        re.sub(r"\s*:\s*\$[a-z]\s*", ": ", x, flags=re.I)
        for x in supplied
        if isinstance(x, str)
    ]
    all_variants = _title_variants(title)
    parts = []
    best = None
    # Allow a single blank line within a display heading: OBIL / [blank] /
    # KEEPER OF CAMELS. Never accept leading or trailing blank lines.
    gaps = 0
    for last in range(position, min(position + 6, limit)):
        line = lines[last].strip()
        if not line:
            gaps += 1
            if not parts or gaps > 1:
                break
            continue
        if len(line) > 100:
            break
        parts.append(line)
        candidate = " ".join(parts)
        if any(_norm(candidate) == _norm(v) for v in supplied if v):
            return last
        if any(_norm(candidate) == _norm(v) for v in all_variants if v):
            best = last
        if len(candidate) > 180:
            break
    return best


def _author_line(s: str, names: typing.Sequence[str]) -> typing.Optional[str]:
    raw = re.sub(
        r"^\s*(?:(?:_?by_?\s+)|(?:written by\s+))", "", s.strip(), flags=re.I
    ).strip("_ *.,")
    a = _norm(raw)
    for name in names:
        n = _norm(name)
        # Bibliographic metadata often stores names as 'Surname, Given'.
        # Compare the printed byline against the reversed form as well.
        if "," in name:
            surname, given = name.split(",", 1)
            reordered = _norm(given + " " + surname)
            if reordered and (
                a == reordered
                or (a.startswith(reordered + " ") and len(a) - len(reordered) < 28)
            ):
                return name
        if n and (a == n or a.startswith(n + " ") and len(a) - len(n) < 28):
            return name
        # Some catalogues spell out the middle name while the story prints
        # an initial: Raymond Zinke Gallun / Raymond Z. Gallun.
        tokens = n.split()
        printed = a.split()
        if (
            len(tokens) >= 3
            and len(tokens) == len(printed)
            and tokens[0] == printed[0]
            and tokens[-1] == printed[-1]
            and all(
                x == y
                or (len(y) == 1 and x.startswith(y))
                or (len(x) == 1 and y.startswith(x))
                for x, y in zip(tokens[1:-1], printed[1:-1])
            )
        ):
            return name
    return None


def _paragraphs(lines):
    out = []
    start = None
    buffer = []
    for i, s in enumerate(lines + [""]):
        if s.strip():
            if start is None:
                start = i
            buffer.append(s)
        elif buffer:
            out.append((start, i, " ".join(x.strip() for x in buffer)))
            start = None
            buffer = []
    return out


def _prose(s: str) -> bool:
    words = s.split()
    if len(words) < 8 or len(s) < 48:
        return False
    if s.isupper() and len(s) < 260:
        return False
    if (
        PRODUCTION.match(s)
        or META.match(s)
        or re.match(
            r"^(?:contents|introduction|preface|foreword|note to the reader|author of)\b",
            s,
            re.I,
        )
    ):
        return False
    if s.startswith("["):
        return False
    return bool(re.search(r"[a-z][a-z]", s))


def _terminal_author_signature(line: str, names: typing.Sequence[str]) -> typing.Optional[str]:
    """Match an entire standalone author signature, not a mention in prose.

    Accepts common end credits: --AUTHOR, —AUTHOR, - AUTHOR, By AUTHOR,
    and a bare author name. A known name/pseudonym is always required.
    """
    value = line.strip()
    if not value or len(value) > 120:
        return None
    value = re.sub(r"^(?:(?:-|—|–){1,3}\s*|by\s+)", "", value, flags=re.I)
    value = value.strip(" ._*")
    for name in names:
        if _norm(value) == _norm(name) and _norm(name):
            return name
    return None


def _find_narrative_end(
    lines: list[str], start: int, end: int, names: typing.Sequence[str]
) -> tuple[int, typing.Optional[str], list[str]]:
    """Trim explicitly identified terminal editorial notes and author signatures."""
    warnings = []
    candidate = end
    for _ in range(5):
        while candidate > start and not lines[candidate - 1].strip():
            candidate -= 1
        if candidate <= start:
            break
        block_start = candidate - 1
        while block_start > start and lines[block_start - 1].strip():
            block_start -= 1
        first = lines[block_start].strip()
        # Editor headings can be separated from their contents by a blank.
        heading = block_start - 1
        while heading >= start and not lines[heading].strip():
            heading -= 1
        if _editor_heading(first) or _editor_marker(first):
            candidate = block_start
            warnings.append("removed_terminal_editorial_note")
            continue
        if heading >= start and _editor_heading(lines[heading].strip()):
            candidate = heading
            warnings.append("removed_terminal_editorial_note")
            continue
        break
    # If an editorial block was found, its start is the true ending.
    if candidate < end:
        end = candidate
    last = end - 1
    while last >= start and not lines[last].strip():
        last -= 1
    if last < start:
        return end, None, warnings
    matched = _terminal_author_signature(lines[last], names)
    if matched:
        warnings.append("removed_terminal_author_signature")
        return last, matched, warnings
    return end, None, warnings


def _frontmatter_mask(lines: list[str], start: int, end: int) -> list[str]:
    """Mask clearly labeled editorial blocks in the opening without shifting indices.

    Only scan before the narrative title page is resolved. Retain the original
    lines for output; the mask is exclusively for detecting heading anchors.
    """
    masked = list(lines)
    i = start
    while i < min(end, start + 180):
        value = lines[i].strip()
        if _editor_heading(value):
            j = i + 1
            # Gutenberg uses both one blank separator and a compact note.
            while j < end and not lines[j].strip():
                j += 1
            if j < end and re.match(
                r"(?i)^this\s+e-?text\b|^this\s+ebook\b|^this\s+electronic\b",
                lines[j].strip(),
            ):
                k = j
                while k < end and lines[k].strip():
                    k += 1
                for at in range(i, k):
                    masked[at] = ""
                i = k
                continue
        i += 1
    return masked


def _front_credit(line: str) -> bool:
    """Recognize bibliographic title-page credits, not narrative mentions."""
    s = line.strip()
    return bool(
        re.match(
            r"(?i)^(?:illustrator\s*:|illustrated by\b|with a drawing by\b|copyright\s*[,©\d]|university press\b|(?:first|second|third) edition\b|all rights reserved\b)",
            s,
        )
    )


def _front_blurb(lines: list[str], pos: int, end: int) -> int:
    """Skip an italicized magazine teaser after title/byline/illustrator credits."""
    if pos >= end or not lines[pos].strip().startswith("_"):
        return pos
    k = pos
    while k < end and lines[k].strip() and k - pos < 12:
        k += 1
    para = " ".join(x.strip() for x in lines[pos:k])
    if k - pos <= 10 and para.rstrip().endswith("_") and len(para) < 950:
        return k
    return pos


def identify_story_boundaries(
    text: str,
    title: typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
    authors: typing.Optional[typing.Sequence[str]] = None,
    pseudonyms: typing.Optional[typing.Sequence[str]] = None,
):
    """Return (start_line, end_line, diagnostics), lines zero-based, end exclusive.

    The indices refer to normalized line endings in the supplied text, not to
    the text after Gutenberg wrappers have been removed.
    """

    lines = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    n = len(lines)
    warn = []
    starts = [i for i, s in enumerate(lines) if START.match(s)]
    ends = [i for i, s in enumerate(lines) if END.match(s)]
    start = starts[0] + 1 if starts else 0
    end = next((i for i in ends if i >= start), n)

    if not starts:
        warn.append("no_standard_start_marker")
    if not ends:
        warn.append("no_standard_end_marker")

    # Without a START marker, older editions can include a license preamble.
    if not starts:
        legacy = next(
            (
                i
                for i, s in enumerate(lines[: min(300, n)])
                if re.match(r"^\s*\*{3}\s*START\b", s, re.I)
            ),
            None,
        )
        if legacy is not None:
            start = legacy + 1
    # Mask labeled transcriber-note contents for anchor detection only.
    masked = _frontmatter_mask(lines, start, end)
    # Only consider a bounded region of the opening for bibliographic anchors.
    opening_end = min(end, start + 240)
    # Use bibliographic header fields as fallback evidence when the caller
    # supplies no metadata; never override explicit caller-supplied values.
    header = "\n".join(lines[:start])

    if not title:
        m = re.search(r"(?im)^Title:\s*(.+?)\s*$", header)
        if m:
            title = m.group(1).strip()
    if not authors and not pseudonyms:
        m = re.search(r"(?im)^Author:\s*(.+?)\s*$", header)
        if m:
            authors = [m.group(1).strip()]

    names = list(authors or []) + list(pseudonyms or [])
    title_hits = []
    author_hits = []

    for i in range(start, opening_end):
        s = masked[i].strip()
        if _title_line(s, title or ""):
            title_hits.append(i)
        elif _title_span(masked, i, opening_end, title) is not None:
            title_hits.append(_title_span(masked, i, opening_end, title))
        named = None if _title_line(s, title) else _author_line(s, names)
        if named:
            author_hits.append((i, named))
    d = ExtractionDiagnostics(
        title_found=bool(title_hits),
        start_marker_found=bool(starts),
        end_marker_found=bool(ends),
    )
    if author_hits:
        matched = author_hits[0][1]
        if matched in (pseudonyms or []):
            d.matched_pseudonym = matched
        else:
            d.matched_author = matched

    # Candidate title-page recognition: exact heading matches, including line wraps.
    # A repeated heading following an explicitly labeled "About <title>" section
    # is the real beginning; the intervening prose is editorial background.
    title_starts = []
    for i in range(start, opening_end):
        last = _title_span(lines, i, opening_end, title)
        if last is not None:
            title_starts.append((i, last))

    # Do not take occurrences far inside an established story as title pages.
    def byline_near(last):
        return any(
            re.match(r"^\s*(?:_?by_?|written by)\s+\S+", lines[j], re.I)
            or _author_line(lines[j], names)
            for j in range(last + 1, min(last + 9, opening_end))
        )

    about_heading = any(
        re.match(r"^\s*about\s+[\"\'“]?", lines[j], re.I)
        and any(
            _norm(v) in _norm(lines[j])
            for v in ([title] if isinstance(title, str) else (title or []))
        )
        for j in range(start, min(opening_end, start + 130))
    )
    first_prose = next(
        (i for i in range(start, min(start + 115, end)) if _prose(masked[i].strip())),
        None,
    )
    heading_candidates = []
    for i, last in title_starts:
        # Unambiguously strong evidence: nearby byline, or an editorial
        # About-title section followed by another matching title heading.
        if (
            first_prose is None
            or i <= first_prose + 8
            or byline_near(last)
            or (about_heading and len(title_starts) > 1)
            or (len(title_starts) > 1 and i < start + 110)
        ):
            heading_candidates.append((i, last))
    later_heading = heading_candidates[-1] if heading_candidates else None
    following = (
        lines[later_heading[1] + 1].strip()
        if later_heading and later_heading[1] + 1 < end
        else ""
    )
    repeated_title_page = bool(
        following
        and len(following) < 100
        and following == following.upper()
        and not _prose(following)
    )
    if (
        len(heading_candidates) > 1
        and later_heading[0] < start + 110
        and (repeated_title_page or about_heading)
    ):
        # The later repeated display title follows introductory/editorial matter.
        heading = heading_candidates[-1]
    else:
        strong = [x for x in heading_candidates if byline_near(x[1])]
        heading = (
            strong[0]
            if strong
            else (heading_candidates[0] if heading_candidates else None)
        )
    # Author matches only count as title-page anchors if near its heading;
    # names appearing later in narrative are not front matter.
    boundary = heading[1] if heading else start - 1
    if heading:
        near = [i for i, _ in author_hits if heading[0] <= i <= heading[1] + 9]
        if near:
            boundary = max(boundary, max(near))
    elif author_hits and (first_prose is None or author_hits[0][0] < first_prose):
        boundary = author_hits[0][0]
    pos = boundary + 1
    years = []
    skips = 0

    # A scene divider directly after front matter is a strong boundary marker.
    # When present, material between the title page and this first divider
    # (including a magazine teaser) belongs to the front matter.
    divider = None
    if heading:
        for j in range(pos, min(end, pos + 38)):
            if SCENE.fullmatch(lines[j].strip()):
                divider = j
                break
            if j > pos + 5 and CHAPTER.fullmatch(lines[j].strip()):
                break
    # A byline/illustrator after a teaser signals that the intervening text
    # is editorial copy, not story narrative.
    late_credit = None
    for j in range(pos, min(end, pos + 32)):
        if re.match(r"^\s*(?:illustrated|illustrations?)\s+by\b", lines[j], re.I):
            late_credit = j
            break
    if divider is not None:
        # A divider may also separate the first and second narrative scenes.
        # Do not skip an already substantial prose paragraph before it.
        sections = _paragraphs(lines[pos:divider])
        if any(e - b >= 5 and _prose(t) for b, e, t in sections):
            divider = None
    if divider is not None:
        pos = divider + 1
    elif late_credit is not None:
        pos = late_credit + 1
    while pos < end and pos < start + 240:
        s = lines[pos].strip()
        if not s or FENCE.fullmatch(s):
            pos += 1
            continue
        if SCENE.fullmatch(s):
            pos += 1
            continue
        if YEAR.fullmatch(s) and pos < max([boundary, start]) + 35:
            years.append(s)
            pos += 1
            continue
        title_end = _title_span(lines, pos, min(pos + 3, end), title)
        if title_end is not None:
            pos = title_end + 1
            continue
        if (
            _author_line(s, names)
            or META.match(s)
            or _front_credit(s)
            or PRODUCTION.match(s)
            or re.match(
                r"^\s*(?:_?by_?|written by)\s+[A-Z][A-Za-z .\'-]{3,75}\s*$", s, re.I
            )
            and pos < boundary + 20
        ):
            pos += 1
            continue
        if re.fullmatch(r"_?by_?", s, re.I):
            pos += 1
            continue
        if re.match(
            r"^(?:contents|table of contents|list of illustrations|other works by|works of)\b",
            s,
            re.I,
        ):
            warn.append("contents_or_works_list")
            pos += 1
            continue
        if _editor_marker(s):
            depth = s.count("[") - s.count("]")
            pos += 1
            while depth > 0 and pos < end:
                depth += lines[pos].count("[") - lines[pos].count("]")
                pos += 1
            continue
        if _editor_heading(s):
            pos += 1
            while pos < end and not lines[pos].strip():
                pos += 1
            if pos < end and re.match(
                r"(?i)^this\s+(?:e-?text|ebook|electronic)\b", lines[pos].strip()
            ):
                while pos < end and lines[pos].strip():
                    pos += 1
            continue
        blurb_end = _front_blurb(lines, pos, end)
        if blurb_end > pos:
            pos = blurb_end
            continue
        if s.startswith("+") and re.match(r"^\+[-+]+\+$", s):
            # ASCII framed transcriber's note. Only remove when identified.
            close = next(
                (
                    j
                    for j in range(pos + 1, min(pos + 55, end))
                    if re.match(r"^\s*\+[-+]+\+\s*$", lines[j])
                ),
                None,
            )
            if close is not None and any(
                "transcriber" in x.lower() for x in lines[pos : close + 1]
            ):
                pos = close + 1
                continue
        if re.match(r"^\s*(?:by|written by)\s*$", s, re.I):
            pos += 1
            continue
        if CHAPTER.match(s):
            break
        # After a metadata-matched display title, flush-left dialogue is
        # narrative even when it is too short for _prose()'s word/length
        # thresholds.  Magazine teasers are normally centered/indented and
        # have already been handled by _front_blurb() and the credit rules.
        # This prevents losing a first paragraph such as '"Time," said ...'
        # and, consequently, any subsequent short narrative paragraphs.
        if (
            heading is not None
            and lines[pos] == lines[pos].lstrip()
            and s.startswith(('"', '\u201c', '\u2018', "'"))
        ):
            break
        if _prose(s):
            break
        # Verse narratives have short physical lines: after an anchored title
        # and optional subtitle, a run of verse lines is narrative, not metadata.
        if heading and pos > heading[1] and pos - heading[1] < 12:
            look = [lines[x].strip() for x in range(pos, min(pos + 5, end))]
            if len(look) >= 4 and all(
                x
                and len(x.split()) >= 3
                and not _front_credit(x)
                and not SCENE.fullmatch(x)
                for x in look[:4]
            ):
                break
        skips += 1
        if skips > 14:
            warn.append("uncertain_extended_front_matter")
            break
        pos += 1
    if not heading and not author_hits:
        warn.append("metadata_anchors_not_found")
        if starts:
            pos = min(
                pos,
                next(
                    (
                        i
                        for i in range(start, min(end, start + 60))
                        if _prose(masked[i])
                    ),
                    pos,
                ),
            )
        else:
            warn.append("manual_start_review")
    # Magazine display pages: validate the printed byline against metadata,
    # then skip a following strapline/editorial recommendation if present.
    _variants = [title] if isinstance(title, str) else list(title or [])
    _magazine_pos = find_magazine_start(lines, start, end, _variants, names)
    if _magazine_pos is not None and _magazine_pos > pos:
        pos = _magazine_pos
        warn.append("magazine_display_byline_boundary")
    if pos >= end:
        pos = start
        warn.append("story_start_not_found")
    end, terminal_signature, trailing_warnings = _find_narrative_end(
        lines, pos, end, names
    )
    warn.extend(trailing_warnings)
    d.removed_terminal_signature = terminal_signature
    d.narrative_start_line = pos + 1
    d.narrative_end_line = end
    d.removed_years = tuple(years)
    d.boundary_confidence = (
        "high"
        if title_hits and author_hits and not any("uncertain" in x for x in warn)
        else "medium" if title_hits or author_hits else "low"
    )
    if pos - start > 130:
        warn.append("long_frontmatter")
    d.warnings = tuple(dict.fromkeys(warn))
    return pos, end, d


def clean_story_text(
    text: str,
    *,
    remove_scene_breaks: bool = True,
    unwrap_lines: bool = True,
    strip_italics: bool = True,
    remove_the_end: bool = False,
    return_removed_count: bool = False,
):
    """Clean narrative-only text; does not make story-boundary decisions."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    output = []
    i = 0
    removed = 0

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if FENCE.fullmatch(s) and (i < 4 or i > len(lines) - 5):
            i += 1
            continue
        if _editor_marker(s):
            removed += 1
            depth = line.count("[") - line.count("]")
            i += 1
            while depth > 0 and i < len(lines):
                depth += lines[i].count("[") - lines[i].count("]")
                i += 1
            continue
        if _editor_heading(s):
            removed += 1
            i += 1
            while i < len(lines) and lines[i].strip():
                i += 1
            continue
        if SCENE.fullmatch(s):
            output.extend([""] if remove_scene_breaks else ["", "***", ""])
            i += 1
            continue
        output.append(s)
        i += 1

    if remove_the_end:
        # Only remove a standalone terminal marker, never a phrase in narration.
        last = next(
            (j for j in range(len(output) - 1, -1, -1) if output[j].strip()), None
        )
        if last is not None and THE_END.fullmatch(output[last]):
            del output[last]
    if unwrap_lines:
        paragraphs = []
        chunk = []
        for s in output + [""]:
            if not s or s == "***" or CHAPTER.fullmatch(s):
                if chunk:
                    paragraphs.append(" ".join(chunk))
                    chunk = []
                if s:
                    paragraphs.append(s)
            else:
                chunk.append(s)
        result = "\n\n".join(paragraphs)
    else:
        result = re.sub(r"\n{3,}", "\n\n", "\n".join(output).strip())

    if strip_italics:
        result = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"\1", result)
    result = result.strip() + "\n" if result.strip() else ""
    return (result, removed) if return_removed_count else result


def _refine_front_boundary(lines, lo, hi, title, warnings):
    """Resolve late title pages and clearly marked editorial prefaces.

    Works only in the opening; never search the entire narrative for matching
    words. Use isolated headings and editorial structure, not title substrings.
    """
    limit = min(hi, 190)
    variants = _title_variants(title)
    headings = []
    for i in range(0, limit):
        if not lines[i].strip() or len(lines[i].strip()) > 95:
            continue
        j = _title_span(lines, i, limit, title)
        if j is not None and (
            i == 0 or not lines[i - 1].strip() or lines[i].startswith(" ")
        ):
            headings.append((i, j))
    # Title-page repeats are common after copyright, publicity, and notes.
    # Refine only when the earlier boundary is still in that material.
    for i, j in headings:
        if i <= lo or i >= min(lo + 110, limit):
            continue
        between = "\n".join(lines[lo:i]).lower()
        evidence = bool(
            re.search(
                r"this\s+e-?text|copyright|publisher|edition|introduction|"
                r"by\s+[a-z]|louisville|university press|appeared|readers who|"
                r"perpetuated|reprint|all rights reserved|\*\s+\*\s+\*",
                between,
            )
        )
        # Evaluate the *whole* matched title span, not just its first line.
        # Otherwise a repeated title with a subtitle remains in the output.
        matched_heading = " ".join(lines[i : j + 1])
        exact_multiline_match = any(
            _norm(matched_heading) == _norm(v) for v in variants if v
        )
        after_heading = j + 1
        if evidence and (
            after_heading >= hi
            or not lines[after_heading].strip()
            or exact_multiline_match
        ):
            lo = j + 1
            warnings.append("late_repeated_title_page")
    # A publication-history sentence between two isolated occurrences of a
    # known title is front matter, even without a copyright keyword.
    if len(headings) >= 2:
        for i, j in headings:
            if lo < i < min(lo + 35, limit):
                between = " ".join(lines[lo:i]).lower()
                if "appeared" in between or "published" in between:
                    lo = j + 1
                    warnings.append("publication_history_removed")
    # Magazine pages may repeat the title, then insert caption and several
    # underscore-italicized editorial teasers before the actual story.
    if any(
        "this etext" in line.lower()
        for line in lines[max(0, lo - 25) : min(lo + 2, hi)]
    ):
        probe = lo
        last_italic = None
        italic_blocks = 0
        while probe < min(hi, lo + 45):
            st = lines[probe].strip()
            if st.startswith("_") and not re.match(r"(?i)^_?(?:by|copyright)\b", st):
                last_italic = probe
                italic_blocks += 1
                k = probe + 1
                while k < min(hi, lo + 50) and lines[k].strip():
                    k += 1
                probe = k
            else:
                probe += 1
        if last_italic is not None and italic_blocks >= 3:
            k = last_italic + 1
            while k < hi and lines[k].strip():
                k += 1
            if k < hi and k - lo < 52:
                lo = k
                warnings.append("magazine_editorial_blurbs_removed")
    # These forms of editor text are explicit, and the editorial paragraphs
    # end before the first unitalicized narrative paragraph.
    editorial_heading = next(
        (
            i
            for i in range(max(0, lo - 45), min(hi, lo + 55))
            if re.match(
                r"(?i)^\s*(?:a classic reprint from|introduction by)\b", lines[i]
            )
        ),
        None,
    )
    if editorial_heading is not None and editorial_heading >= lo - 5:
        intro = next(
            (
                i
                for i in range(editorial_heading, min(hi, editorial_heading + 12))
                if re.match(r"(?i)^\s*introduction by\b", lines[i])
            ),
            None,
        )
        if intro is not None:
            k = intro + 1
            while k < min(hi, intro + 85):
                if lines[k].strip() and not lines[k].lstrip().startswith("_"):
                    # Continuation lines of italicized paragraphs are also
                    # editorial. Blank lines followed by a non-italic line
                    # are the first plausible narrative boundary.
                    if k > intro + 3 and not lines[k - 1].strip():
                        lo = max(lo, k)
                        warnings.append("editorial_introduction_removed")
                        break
                k += 1
    # Standalone "This etext was produced" paragraph and accompanying
    # rights discussion are editorial, even without a Transcriber's heading.
    if lo < hi and re.match(r"(?i)^\s*this\s+e-?text\s+was\s+produced\b", lines[lo]):
        k = lo
        while k < hi and lines[k].strip():
            k += 1
        lo = k
        warnings.append("unlabeled_etext_credit_removed")
    return lo


def _refine_repeated_display_heading(
    lines, lo, hi, title, authors, pseudonyms, warnings
):
    """Strip isolated repeated title, byline, and publication epigraph near the chosen start.

    Only uses actual heading matches in a small window around an already
    identified story boundary. It does not scan the entire narrative.
    """
    names = list(authors or []) + list(pseudonyms or [])
    limit = min(hi, max(lo + 18, 225))
    matches = []
    for i in range(max(0, lo - 95), min(limit, lo + 95)):
        last = _title_span(lines, i, min(hi, i + 6), title)
        if last is None:
            continue
        if i > 0 and lines[i - 1].strip() and not lines[i].startswith(" "):
            continue
        matches.append((i, last))

    if not matches:
        return lo

    # Accept an immediately following repeat, or a later title after a
    # copyright/publication introduction. Do not jump across narrative prose.
    candidates = []
    for i, last in matches:
        if i <= lo and last + 1 >= lo - 2:
            candidates.append((i, last))
        elif lo < i <= lo + 95:
            between = " ".join(lines[lo:i]).casefold()
            editorial = bool(
                re.search(
                    r"copyright|published|publishers|introduction|\bthis etext\b|how did it happen",
                    between,
                )
            )
            empty_or_near = i - lo <= 8 and not any(
                _prose(x.strip()) for x in lines[lo:i]
            )
            if editorial or empty_or_near:
                candidates.append((i, last))
    if not candidates:
        return lo
    i, last = candidates[-1]
    pos = max(lo, last + 1)
    while pos < min(hi, last + 25) and not lines[pos].strip():
        pos += 1
    # A freestanding 'by' followed by a metadata-matched author name.
    if pos < hi and re.fullmatch(r"(?i)_?by_?", lines[pos].strip()):
        j = pos + 1
        while j < min(hi, pos + 5) and not lines[j].strip():
            j += 1
        if j < hi and _author_line(lines[j], names):
            pos = j + 1
    elif pos < hi and _author_line(lines[pos], names):
        pos += 1
    while pos < hi and not lines[pos].strip():
        pos += 1
    # Epigraph: isolated indented quotation, attributed to scripture / a
    # named source, followed by a paragraph break before narrative.
    if pos < hi and (lines[pos].startswith("  ") or lines[pos].strip().startswith("¶")):
        j = pos
        while j < min(hi, pos + 12) and lines[j].strip():
            j += 1
        verse = " ".join(x.strip() for x in lines[pos:j])
        if re.search(
            r"(?:--|—)\s*(?:MARK|LUKE|MATTHEW|JOHN|ACTS|PSALMS?)\s+[IVXLCDM0-9]+\s*:",
            verse,
            re.I,
        ):
            pos = j
            while pos < hi and not lines[pos].strip():
                pos += 1
            warnings.append("scriptural_epigraph_removed")
    if pos > lo:
        warnings.append("repeated_title_and_byline_removed")
        return pos
    return lo


# Explicitly marked publisher matter is safe to discard at a story ending.
# Do not interpret a prose reference to an advertisement or footnote as a label.
_TERMINAL_PRINTER = re.compile(
    r"^(?:(?:[A-Za-z][A-Za-z .'-]{1,30}:\s*[-\u2014\u2013]*\s*)?"
    r"printed\s+(?:by|in|at)\b|press\s+of\b|"
    r"the\s+country\s+life\s+press\b)", re.I
)
_TERMINAL_FOOTNOTE = re.compile(r"^\[(?:\d+|[A-Za-z])\]\s+\S")
_TERMINAL_FOOTNOTE_HEADING = re.compile(r"^footnotes?\s*:?$", re.I)
_TERMINAL_ADVERTISING = re.compile(
    r"^(?:illustrated\s+works\s+by\b|"
    r"(?:books|works|publications)\s+by\s+the\s+same\s+author\b)", re.I
)
_TERMINAL_AWARDS = re.compile(
    r"^as a service to our readers, we list the [\"\u201c]?hugo[\"\u201d]? award winners\b",
    re.I,
)


def _terminal_supplement(lines, lo, hi, warnings):
    """Trim only a clearly labeled appendix immediately following a final marker.

    Return the updated end and footnotes to preserve as a separate record.
    Unrecognized passages, even after THE END, are left untouched.
    """
    lower = max(lo, hi - 160)
    for marker in range(hi - 1, lower - 1, -1):
        if not _TERMINAL_END_MARKER.fullmatch(lines[marker].strip()):
            continue
        tail = lines[marker + 1:hi]
        paragraphs = _paragraphs(tail)
        if not paragraphs:
            continue
        first = paragraphs[0][2].strip()
        # Require an independently recognizable editorial heading, or
        # footnotes that are *all* numbered. A lone [1] after THE END may
        # be legitimate prose and is not sufficient if more follows.
        is_footnotes = bool(_TERMINAL_FOOTNOTE_HEADING.fullmatch(first))
        note_paragraphs = paragraphs[1:] if is_footnotes else paragraphs
        if is_footnotes or all(_TERMINAL_FOOTNOTE.match(p[2].strip()) for p in paragraphs):
            if note_paragraphs and all(
                _TERMINAL_FOOTNOTE.match(p[2].strip()) for p in note_paragraphs
            ):
                warnings.append("terminal_footnotes_preserved_separately")
                return marker + 1, "\n\n".join(p[2].strip() for p in note_paragraphs)
        if _TERMINAL_AWARDS.match(first) or _TERMINAL_ADVERTISING.match(first):
            warnings.append("terminal_publisher_appendix_removed")
            return marker + 1, None
    return hi, None


def _terminal_printed_byline(lines, lo, line):
    """Accept an ending pen name only when the same printed byline is explicit.

    This prevents guessing pseudonyms from arbitrary uppercase signatures.
    """
    if not re.match(r"^(?:[-\u2014\u2013]{1,4})\s*[A-Za-z]", line.strip()):
        return False
    signature = re.sub(r"^[-\u2014\u2013]{1,4}\s*", "", line.strip())
    signature = _norm(signature)
    if not signature:
        return False
    for front_line in lines[max(0, lo - 400):lo]:
        display = re.fullmatch(r"\s*(?:by|written by)\s+(.{3,90}?)\s*", front_line, re.I)
        if display and _norm(display.group(1)) == signature:
            return True
    return False


def _save_terminal_footnotes(directory: pathlib.Path, story: int, title: str, notes: str):
    """Preserve removed source footnotes atomically after successful publication."""
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "footnotes.json"
    fd, tmp = tempfile.mkstemp(prefix=".footnotes-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"gutenberg_id": story, "title": title, "footnotes": notes},
                      handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp, destination)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _trim_terminal_imprint(lines, lo, hi, authors, pseudonyms, warnings):
    """Remove publisher colophons and printer imprints only at the end."""
    end = hi

    def previous_nonempty(k):
        while k > lo and not lines[k - 1].strip():
            k -= 1
        return k

    for _ in range(5):
        end = previous_nonempty(end)
        if end <= lo:
            break
        j = end - 1
        while j > lo and lines[j - 1].strip():
            j -= 1
        paragraph = " ".join(x.strip() for x in lines[j:end])
        if SCENE.fullmatch(paragraph.strip()):
            end = j
            warnings.append("terminal_scene_divider_removed")
            continue

        # Gutenberg printed colophons often use 'HERE ENDS <title> BY <author>'
        # plus publisher/printer/date. This is distinct from story narration.
        colophon = bool(re.match(r"(?i)^here ends\b", paragraph)) and bool(
            re.search(r"(?i)\b(?:published by|printed for|press|company)\b", paragraph)
        )
        imprint = (
            bool(re.match(r"(?i)^(?:the )?university press\b", paragraph))
            and len(paragraph) < 180
        )
        edition_statement = (
            bool(re.match(
                r"(?i)^(?:[A-Z][A-Z-]*\s+){1,8}copies of this book\b",
                paragraph,
            ))
            and bool(re.search(
                r"(?i)\b(?:printed|paper|type distributed|impression)\b",
                paragraph,
            ))
            and len(paragraph) < 400
        )
        if edition_statement:
            end = j
            warnings.append("terminal_limited_edition_colophon_removed")
            continue
        printer = bool(_TERMINAL_PRINTER.match(paragraph)) and len(paragraph) < 190
        if colophon or imprint or printer:
            end = j
            warnings.append(
                "terminal_publisher_colophon_removed"
                if colophon
                else "terminal_printer_imprint_removed"
            )
            continue
        break
    return end


def _trim_trailing_transcriber_note(lines, lo, hi, warnings):
    """A terminal transcriber's note may have blank lines after its heading."""
    lower = max(lo, hi - 45)
    for i in range(hi - 1, lower - 1, -1):
        if not _editor_heading(lines[i].strip()):
            continue
        tail = [s.strip() for s in lines[i + 1 : hi] if s.strip()]
        # Avoid truncating a narrative that follows an editorial note.
        if tail and (len(tail) > 12 or any(len(s) > 250 for s in tail)):
            continue
        warnings.append("terminal_transcriber_note_removed")
        return i
    return hi




# Explicit editorial labels are safer terminal anchors than generic end markers.
_TERMINAL_EDITORIAL_LABEL = re.compile(
    r"^_?(?:"
    r"(?:transcriber(?:'s|s)?|transcription|proofreader(?:'s|s)?|"
    r"e-?text|editor(?:'s|s)?)\s+notes?"
    r"|typographical\s+errors?\s+corrected(?:\s+in\s+(?:the\s+)?text)?"
    r")_?(?=\s|:|\.|$)",
    re.I,
)
_TERMINAL_EDITORIAL_BOX = re.compile(r"^\+[-+]{8,}\+?(?:\s|$)")


def _trim_terminal_editorial_tail(lines, lo, hi, warnings):
    """Trim explicitly headed editorial material at a story's very end.

    An end note may extend well beyond 45 lines, or its heading may be part
    of a bordered ASCII table. Require an explicit heading near the end of
    the narrative; never use an ordinary mention of a transcriber in prose.

    Args:
        lines: Source lines before paragraph unwrapping.
        lo: First narrative line, inclusive.
        hi: Last possible narrative line, exclusive.
        warnings: Mutable collection of extraction diagnostics.

    Returns:
        Exclusive line boundary, shortened only for a recognized terminal note.
    """
    if hi <= lo:
        return hi
    # Cap the backward search but do not require the heading to be close
    # to the final line: correction tables can be dozens of lines long.
    lower = max(lo + 1, hi - 160)
    for index in range(lower, hi):
        candidate = _editorial_spelling(lines[index].strip())
        start = index
        if _TERMINAL_EDITORIAL_BOX.match(candidate):
            # The editorial heading must occur at the head of this box.
            preview = " ".join(lines[index : min(index + 9, hi)])
            # The label appears in the first few lines of a boxed note.
            if not re.search(
                r"(?:transcriber(?:'s|s)?|transcription|"
                r"proofreader(?:'s|s)?|e-?text)\s+notes?\b|"
                r"typographical\s+errors?\s+corrected(?:\s+in\s+(?:the\s+)?text)?\b",
                _editorial_spelling(preview),
                re.I,
            ):
                continue
        elif not _TERMINAL_EDITORIAL_LABEL.match(candidate):
            continue
        # Headings within normal prose are not terminal notes: only start
        # at a paragraph boundary, or immediately after an ending marker.
        if index > lo and lines[index - 1].strip():
            # Gutenberg transcriber notes sometimes follow THE END or a
            # terminal author signature without an intervening blank line.
            previous = lines[index - 1].strip()
            ending_or_signature = THE_END.match(previous) or re.fullmatch(
                r"[-\u2014]{1,2}\s*[A-Z][A-Z .&'-]{3,}", previous
            )
            if not ending_or_signature:
                continue
        # A heading followed by ordinary narrative is not safe to remove.
        # Editorial tails are anchored by either an explicit terminal marker
        # or a heading placed in the final quarter of the source document.
        warnings.append("terminal_editorial_tail_removed")
        return start
    return hi



# These are publication conventions, not story dialogue or description. Only
# recognize an entire final line, after editorial end notes have been removed.
_TERMINAL_END_MARKER = re.compile(
    r"^\s*(?:(?:-{2,}|[\u2014\u2013]{2,})\s*)?"
    r"(?:the\s+end|end|finis|fin)"
    r"(?:[.!])?\s*(?:-{2,}|[\u2014\u2013]{2,})?\s*$",
    re.I,
)


def _terminal_author_variants(name: str) -> set[str]:
    """Return name spellings supported by one catalog author entry.

    Gutenberg catalogs generally use `Surname, Given`. The terminal byline
    normally puts the given name first. Parenthetical expansions of initials
    are catalog descriptions rather than parts of the printed signature.
    """
    base = re.sub(r"\s*\([^)]*\)", "", name).strip()
    variants = {base}
    if "," in base:
        parts = [part.strip() for part in base.split(",") if part.strip()]
        if len(parts) >= 2:
            surname, given = parts[0], parts[1]
            suffix = ", ".join(parts[2:])
            variants.add(f"{given} {surname}")
            # A magazine may omit a catalogued middle initial or append Jr.
            given_parts = given.split()
            if len(given_parts) > 1 and all(
                len(part.strip(".")) == 1 for part in given_parts[1:]
            ):
                variants.add(f"{given_parts[0]} {surname}")
            if not suffix:
                variants.add(f"{given} {surname} Jr.")
                variants.add(f"{given} {surname}, Jr.")
            if suffix:
                variants.add(f"{given} {surname}, {suffix}")
                variants.add(f"{given} {surname} {suffix}")
    return {_norm(variant).replace(" ", "") for variant in variants if _norm(variant)}


def _terminal_metadata_author(line: str, authors, pseudonyms) -> bool:
    """Match a standalone ending credit to known authors, never arbitrary names.

    Args:
        line: One physical source line at the end of the extraction.
        authors: Catalog author names.
        pseudonyms: Catalog pseudonyms/aliases.

    Returns:
        Whether the complete line credits the known author or author pair.
    """
    value = line.strip()
    if not value or len(value) > 150:
        return False
    value = re.sub(r"^(?:[-\u2014\u2013]{1,4}\s*|by\s+)", "", value, flags=re.I)
    value = value.strip(" \t.=*_\u2014\u2013-")
    if not value:
        return False
    names = list(authors or []) + list(pseudonyms or [])
    known = set()
    for name in names:
        known.update(_terminal_author_variants(name))
    if _norm(value).replace(" ", "") in known:
        return True
    # A joint credit, such as Clifton & Apostolides, has to match *all*
    # listed names; never strip a fictional character's attribution.
    parts = re.split(r"\s+(?:&|and)\s+", value, flags=re.I)
    if len(parts) < 2 or len(parts) > len(authors or []):
        return False
    available = [ _terminal_author_variants(name) for name in (authors or [])]
    for part in parts:
        match = next((i for i, variants in enumerate(available)
                      if _norm(part.strip(" \t.=*_\u2014\u2013-")).replace(" ", "") in variants), None)
        if match is None:
            return False
        del available[match]
    return True


def _trim_terminal_publication_markers(
    lines, lo, hi, authors, pseudonyms, warnings, *, remove_end_marker=True
):
    """Remove ending markers and catalog-confirmed author lines at the tail.

    Only an isolated physical line is eligible. Unlike a general search for
    `THE END`, this cannot remove a marker that precedes more narrative text.

    Args:
        lines: Gutenberg source lines before paragraph unwrapping.
        lo: Beginning of extracted narrative, inclusive.
        hi: End of extracted narrative, exclusive.
        authors: Names from Gutenberg metadata.
        pseudonyms: Known alternate author names.
        warnings: Mutable diagnostic warnings.
        remove_end_marker: Whether to discard explicit terminal end markers.

    Returns:
        Updated exclusive narrative ending index.
    """
    end = hi
    while end > lo:
        candidate = end - 1
        while candidate >= lo and not lines[candidate].strip():
            candidate -= 1
        if candidate < lo:
            return end
        value = lines[candidate].strip()
        is_author = _terminal_metadata_author(value, authors, pseudonyms) or (
            _terminal_printed_byline(lines, lo, value)
        )
        # Without a separating blank, a bare name might be a fictional
        # letter signature. Require an explicit printed-credit prefix then.
        separated = candidate == lo or not lines[candidate - 1].strip()
        has_credit_prefix = bool(re.match(r"^(?:[-\u2014\u2013]{1,4}|by\s+)", value, re.I))
        if is_author and (separated or has_credit_prefix):
            warnings.append("terminal_metadata_author_removed")
        elif remove_end_marker and _TERMINAL_END_MARKER.fullmatch(value):
            warnings.append("terminal_end_marker_removed")
        else:
            break
        end = candidate
    return end


def _conservative_narrative_guard(lines, lo, hi, title, warnings):
    """Prefer keeping an uncertain opening over silently deleting story prose.

    The traditional Gutenberg title/byline heuristic can confuse an italic
    prologue, epigraph, or frame narrative with a magazine teaser. When prose
    occurs *after* an identifiable title page but *before* the selected start,
    retain it unless it has a clear bibliographic/editorial signature.

    This is an intentionally asymmetric safety check: leftover front matter
    is less damaging to a human-reviewed corpus than lost narrative.
    """
    if lo <= 0:
        return lo
    heading_end = None
    # Last recognized title heading before the proposed narrative. Requiring
    # this anchor avoids treating Gutenberg production credits as the story.
    for i in range(max(0, lo - 155), lo):
        j = _title_span(lines, i, min(hi, i + 6), title)
        if j is not None and j < lo:
            heading_end = j
            break
    if heading_end is None:
        # Multiline display titles may fail exact matching; a freestanding
        # bibliographic byline is still a useful conservative anchor.
        for i in range(max(0, lo - 100), lo):
            if re.match(r"(?i)^\s*_?by_?\s+[A-Z][A-Za-z .-]{4,65}_?\s*$", lines[i]):
                heading_end = i
                break
    if heading_end is None:
        return lo
    first = max(heading_end + 1, lo - 75)
    for i in range(first, lo):
        s = lines[i].strip()
        if not s or len(s) < 48:
            continue
        # Consider only starts of paragraphs, never continuation lines.
        if i > 0 and lines[i - 1].strip():
            continue
        if _editor_marker(s) or _editor_heading(s) or PRODUCTION.match(s):
            continue
        if META.match(s) or _front_credit(s) or SCENE.fullmatch(s):
            continue
        if re.match(r'(?i)^(?:transcriber|contents|introduction|foreword|preface|list of|about this|copyright|this e-?text|the following|illustrat)', s):
            continue
        if s.startswith('[') and not s.startswith('[\"'):
            continue
        # Reject bibliographic/editorial continuation even if it is long.
        if re.search(r'(?i)\b(?:online distributed proofreading|project gutenberg|copyright was renewed|license|ebook produced)\b', s):
            continue
        # At least two consecutive lines of likely prose, or a long
        # standalone prose line. No guesses about what italic means.
        j = i + 1
        while j < min(lo, i + 20) and lines[j].strip():
            j += 1
        para = ' '.join(x.strip() for x in lines[i:j])
        if (j - i >= 2 or (len(s) >= 60 and len(s.split()) >= 8)) and len(para) >= 60 and re.search(r'[a-z]{3}', para, re.I):
            warnings.append('conservative_opening_prose_preserved')
            return i
    return lo



def _bracketed_marker_narrative_guard(lines, lo, hi, title, authors, pseudonyms, warnings):
    """Keep a possible story opening immediately after an editorial marker.

    Recognize [Sidenote: ...], [Illustration: ...], and [Transcriber's Note:
    ...] including multi-line bracketed blocks. The first nonblank line after
    the closing bracket is a *candidate*, not an unconditional boundary: do
    not move the start if a display title, byline, or clearly non-narrative
    front-matter heading intervenes. This rule may only move a start earlier.
    """
    if lo <= 0:
        return lo
    marker = re.compile(
        r"^\s*\[\s*(?:sidenote|illustrations?|transcriber[’']s?\s+notes?|"
        r"transcription\s+notes?)\s*(?=[:\].\s])", re.I)
    byline = re.compile(r"(?i)^\s*(?:by|written by)\s+.{2,90}$")
    # Keep the search close to the proposed opening to avoid distant book
    # illustrations or notes in a lengthy front matter section.
    for i in range(max(0, lo - 85), lo):
        if not marker.match(lines[i].replace('\u2019', "'")):
            continue
        close = None
        for k in range(i, min(hi, i + 30)):
            if ']' in lines[k]:
                close = k
                break
        if close is None or close >= lo:
            continue
        candidate = next((k for k in range(close + 1, min(lo + 1, hi))
                          if lines[k].strip()), None)
        if candidate is None or candidate >= lo:
            continue
        first = lines[candidate].strip()
        if (_editor_marker(first) or _editor_heading(first) or
                PRODUCTION.match(first) or META.match(first) or
                SCENE.fullmatch(first)):
            continue
        # If a title/byline lies between the marker and the old start,
        # this is still front matter, not an immediately following story.
        blocked = False
        for k in range(close + 1, lo):
            s = lines[k].strip()
            if not s:
                continue
            if (_title_span(lines, k, min(hi, k + 6), title) is not None or
                    _author_line(s, list(authors or []) + list(pseudonyms or [])) or
                    byline.match(s) or
                    re.match(r"(?i)^(?:contents|table of contents|preface|"
                             r"introduction|foreword|copyright|chapter list)\b", s)):
                blocked = True
                break
        if blocked:
            continue
        warnings.append('post_bracketed_marker_opening_preserved')
        return candidate
    return lo



def _dated_scene_opening_guard(lines, lo, hi, title, authors, pseudonyms, warnings):
    """Preserve a dated/location scene heading directly before narrative prose.

    Only backtrack across a tiny adjacent block containing a *strong* fictional
    date (month/day/year or a four-digit year with an era marker) and at most
    one short location line. Never search across a title, author, copyright,
    or other front-matter heading. Conservative: this only moves lo backward.
    """
    if lo <= 0:
        return lo
    month = (r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|'
             r'Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Sept|'
             r'Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)')
    date = re.compile(
        rf'(?i)^(?:{month}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?\s*,?\s+\d{{4}}|'
        rf'\d{{1,2}}\s+{month}\.?\s+\d{{4}}|'
        r'.{2,65}?[, ]+\d{3,4}\s*(?:CE|BCE|AD|BC))\.?$'
    )
    # No more than two intervening empty lines. Exclude headings that occur
    # many paragraphs before the actual narrative.
    previous = lo - 1
    while previous >= 0 and not lines[previous].strip() and lo - previous <= 3:
        previous -= 1
    if previous < 0 or lo - previous > 3:
        return lo
    recent = [previous]
    before = previous - 1
    if before >= 0 and lines[before].strip():
        recent.insert(0, before)
    if not any(date.fullmatch(lines[i].strip()) for i in recent):
        return lo
    # If two lines are present, the other must look like a location label,
    # not a paragraph, title or byline. This supports date+location headers.
    if len(recent) == 2:
        other = next((lines[i].strip() for i in recent if not date.fullmatch(lines[i].strip())), '')
        if other and (len(other) > 65 or len(other.split()) > 8 or
                      re.search(r'[.!?][\s\"\']*$', other)):
            return lo
    start = recent[0]
    for i in range(start, lo):
        s = lines[i].strip()
        if not s:
            continue
        if (_editor_marker(s) or _editor_heading(s) or PRODUCTION.match(s) or
                _author_line(s, list(authors or []) + list(pseudonyms or [])) or
                re.match(r'(?i)^(?:by|written by|copyright|published by|'
                         r'publisher|preface|contents|introduction)\b', s) or
                _title_span(lines, i, min(hi, i + 6), title) is not None):
            return lo
    warnings.append('dated_scene_heading_preserved')
    return start

def clean_gutenberg_story(
    text: str,
    title: typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
    authors: typing.Optional[typing.Sequence[str]] = None,
    pseudonyms: typing.Optional[typing.Sequence[str]] = None,
    *,
    remove_scene_breaks: bool = True,
    unwrap_lines: bool = True,
    strip_italics: bool = True,
    remove_the_end: bool = True,
    return_diagnostics: bool = False,
):
    """Extract Gutenberg narrative using optional externally supplied metadata.

    `authors` and `pseudonyms` are sequences of names (not one comma-delimited
    string). Returns a string, or (string, diagnostics dictionary).
    """
    norm = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = norm.split("\n")
    lo, hi, report = identify_story_boundaries(norm, title, authors, pseudonyms)
    warnings = list(report.warnings)
    lo = _refine_front_boundary(lines, lo, hi, title, warnings)
    lo = _refine_repeated_display_heading(
        lines, lo, hi, title, authors, pseudonyms, warnings
    )
    lo = _conservative_narrative_guard(lines, lo, hi, title, warnings)
    lo = _bracketed_marker_narrative_guard(lines, lo, hi, title, authors, pseudonyms, warnings)
    lo = _dated_scene_opening_guard(lines, lo, hi, title, authors, pseudonyms, warnings)
    lo = boundary_features.preserve_structural_opening(lines, lo, hi, title, list(authors or []) + list(pseudonyms or []),
        title_match=_title_span, author_match=_author_line, warnings=warnings)
    lo = frontmatter_precision.refine_promotional_blurb_boundary(lines, lo, hi, title, authors, warnings)
    hi, terminal_footnotes = _terminal_supplement(lines, lo, hi, warnings)
    hi = _trim_terminal_imprint(lines, lo, hi, authors, pseudonyms, warnings)
    hi = _trim_trailing_transcriber_note(lines, lo, hi, warnings)
    hi = _trim_terminal_editorial_tail(lines, lo, hi, warnings)
    hi = _trim_terminal_imprint(lines, lo, hi, authors, pseudonyms, warnings)
    hi = _trim_terminal_publication_markers(
        lines, lo, hi, authors, pseudonyms, warnings, remove_end_marker=remove_the_end
    )
    report.narrative_end_line = hi
    report.narrative_start_line = lo + 1
    cleaned, removed = clean_story_text(
        "\n".join(lines[lo:hi]),
        remove_scene_breaks=remove_scene_breaks,
        unwrap_lines=unwrap_lines,
        strip_italics=strip_italics,
        remove_the_end=remove_the_end,
        return_removed_count=True,
    )
    # Original Gutenberg line wrapping sometimes conceals a terminal heading
    # until paragraph unwrapping. Recheck only explicit terminal structures on
    # the cleaned text; never cut arbitrary prose following an end marker.
    cleaned_lines = cleaned.splitlines()
    cleaned_end = len(cleaned_lines)
    checked_end, cleaned_footnotes = _terminal_supplement(
        cleaned_lines, 0, cleaned_end, warnings
    )
    if checked_end < cleaned_end:
        cleaned_end = checked_end
        if cleaned_footnotes is not None and terminal_footnotes is None:
            terminal_footnotes = cleaned_footnotes
    cleaned_end = _trim_terminal_imprint(
        cleaned_lines, 0, cleaned_end, authors, pseudonyms, warnings
    )
    if cleaned_end < len(cleaned_lines):
        cleaned = "\n".join(cleaned_lines[:cleaned_end]).strip()
        if cleaned:
            cleaned += "\n"

    if remove_the_end:
        # Source-level cleanup may expose a final marker after other formatting
        # normalization. Never remove an interior marker or narrative text.
        paragraphs = cleaned.rstrip().split("\n\n")
        if paragraphs and _TERMINAL_END_MARKER.fullmatch(paragraphs[-1].strip()):
            cleaned = "\n\n".join(paragraphs[:-1]).rstrip()
            warnings.append("terminal_end_marker_removed_after_cleaning")
    report.removed_editorial_blocks = removed
    report.terminal_footnotes = terminal_footnotes
    if re.search(
        r"(?im)^\s*(?:produced by|transcriber|\[illustration|table of contents)\b",
        cleaned,
    ):
        warnings.append("possible_editorial_residue")
    if len(cleaned) < 400:
        warnings.append("very_short_extraction")
    report.warnings = tuple(dict.fromkeys(warnings))
    return (cleaned, report.to_dict()) if return_diagnostics else cleaned


def normalize(s):
    """Normalize an extracted story for downstream processing."""
    return re.sub(r"[^a-z0-9]+", " ", re.sub(r"[_*]", "", s.lower())).strip()


def find_magazine_start(lines, lower, upper, titles, authors):
    """Find narrative after an anchored display byline, or return None.

    Require a metadata-matched author or a heading-to-byline relationship
    for metadata-free documents. Avoid deleting bylines inside narrative.
    """
    max_line = min(upper, lower + 125)
    names = {normalize(x) for x in authors if x}
    titlenames = {normalize(x) for x in titles if x}
    candidates = []
    for i in range(lower, max_line):
        s = lines[i].strip()
        m = re.fullmatch(r"(?i)_?by_?\s*(?:\.{2,}\s*)?(.{3,85}?)_?\s*", s)
        if not m:
            continue
        person = normalize(m.group(1))
        if len(person.split()) > 6:
            continue
        known = person in names or any(
            person.split()[-1] == a.split()[-1] and person.split()[0] == a.split()[0]
            for a in names
            if a
        )
        preceding = [lines[j].strip() for j in range(max(lower, i - 24), i)]
        near_title = any(t and t in normalize(" ".join(preceding)) for t in titlenames)
        # In a headerless document, a short isolated byline with display title
        # above is supporting but weaker evidence than supplied metadata.
        if not (known or near_title):
            # In headerless ebooks, a short centered title appearing before
            # a centered standalone byline is a plausible display title.
            heading = any(
                5 <= len(lines[j]) - len(lines[j].lstrip())
                and 2 <= len(lines[j].split()) <= 8
                and len(lines[j].strip()) < 80
                and lines[j].strip()[0].isupper()
                for j in range(max(lower, i - 18), i)
                if lines[j].strip()
            )
            if not (heading and i < lower + 50):
                continue
        candidates.append((i, known, near_title))
    if not candidates:
        return None
    i = next((x[0] for x in candidates if x[1] and x[2]), candidates[0][0])
    j = i + 1

    while j < upper and j < i + 45:
        s = lines[j].strip()
        if not s:
            j += 1
            continue
        if re.fullmatch(r"(?:\*\s*){3,}", s):
            j += 1
            continue
        if _front_credit(s) or re.match(r"(?i)(?:author of\b|\[illustration)", s):
            j += 1
            continue
        # A fully italicized short magazine strapline/teaser.
        if s.startswith("_"):
            k = j
            while k < upper and lines[k].strip():
                k += 1
            para = " ".join(x.strip() for x in lines[j:k])
            if (
                para.rstrip().endswith("_") or para.rstrip().endswith("....")
            ) and k - j <= 8:
                j = k
                continue
        # Standalone magazine taglines that end in four dots.
        k = j
        while k < upper and lines[k].strip():
            k += 1
        para = " ".join(x.strip() for x in lines[j:k])
        if para.endswith("....") and len(para) < 400:
            j = k
            continue
        # A magazine standfirst is often a one/two-line indented caption,
        # set off by blank lines from the flush-left narrative below.
        if (
            len(para.split()) < 38
            and k - j <= 3
            and all(lines[x].startswith(" ") for x in range(j, k))
            and k + 2 < upper
            and any(
                lines[x].strip() and not lines[x].startswith(" ")
                for x in range(k + 1, min(k + 5, upper))
            )
        ):
            j = k
            continue
        # Editorial introductions describing the author/story and addressing readers.
        if re.match(r"(?i)(?:the author of this story|this story (?:is|was))\b", s):
            j = k
            continue
        break
    return j


#################################################################


def chaptered(text):
    """Return True if the text contains chapters, False otherwise.

    Works for chapters in Roman numerals and w/o names.   Needs to be expanded.

    Args:
        text (str): The full text of the story.
    Returns:
        bool: True if the text contains chapters, False otherwise.
    """
    result = 0

    possible_titles = 0

    text_array = text.split("\n\n")

    # if several lines are simply all caps, then it's probably chapter names
    multiple_lines_all_caps = False
    for index, line in enumerate(text_array):
        if possible_internal_chapter_name(line):
            if index < len(text_array) - 2 and text_array[index + 1].isupper():
                multiple_lines_all_caps = True
            elif index > 0 and text_array[index - 1].isupper():
                multiple_lines_all_caps = True
            else:
                multiple_lines_all_caps = False

            # if index < len(text_array) - 2:
            #    multiple_lines_all_caps = True
            # else:
            #    multiple_lines_all_caps = False

            if not multiple_lines_all_caps:
                if index == 0:
                    possible_titles = possible_titles + 1
                else:
                    if (
                        len(text_array[index - 1]) > 0
                        and text_array[index - 1][-1] != ":"
                    ):
                        possible_titles = possible_titles + 1
                    else:
                        possible_titles = possible_titles + 1

        line = line.strip().lower()

        if line in ["table of contents", "contents", "contents.", "contents:"]:
            return True

        if line.startswith("i ~"):
            result = result + 1
        if line.startswith("ii ~"):
            result = result + 1
        if line.startswith("iii ~"):
            result = result + 1

        if line.startswith("i."):
            result = result + 1
        if line.startswith("ii."):
            result = result + 1
        if line.startswith("iii."):
            result = result + 1

        if line.startswith("chapter "):
            result = result + 1

        if line in [
            "i",
            "i.",
            "chapter i",
            "chapter 1",
            "chapter i.",
            "chapter one",
            "chap. i.",
            "part i",
            "part i.",
        ]:
            result = result + 1
        if line in [
            "ii",
            "ii.",
            "chapter ii",
            "chapter 2",
            "chapter two",
            "chapter ii.",
            "chap. ii.",
            "part ii",
            "part ii.",
        ]:
            result = result + 1
        if line in [
            "iii",
            "iii.",
            "chapter iii",
            "chapter 3",
            "chapter three",
            "chapter iii.",
            "chap. iii.",
            "part iii",
            "part iii.",
        ]:
            result = result + 1

    # A single I or II might be an anomoly so this is to see if both exist

    if result == 0 and possible_titles == 2:
        return False
    else:
        return result >= 2 or possible_titles >= 2


def possible_internal_chapter_name(line):
    """Check whether a heading could be an internal chapter name."""
    if line.strip().isupper() and len(line.strip().split(" ")) < 7:
        if line.strip()[0] == '"' and line.strip()[-2:] == '."':
            return False
        if line.strip()[0] == '"' and line.strip()[-1:] == '"':
            return False
        if line.strip()[-1:] == ":":
            return False
        if line.strip()[0] == "\“" and line.strip()[-1:] == "\”":
            return False
        #        if line.strip() == "THE END.":
        #            return False
        if line.strip()[0] == "_" and line.strip()[-1:] == "_":
            return False
        if not any(
            exception == line.strip() for exception in storymap.TITLE_EXCEPTIONS
        ):
            return True

    return False


def subject_ok(subject):
    """Return True if the subject is consistent with what we want (short fiction).

    Args:
        subject (frozenset): a string or list of strings representing the subject from the story metadata.
    Returns:
        bool: True if the subject appears to be short fiction, False otherwise.
    """

    if bad_subjects(subject):
        return False

    if loc_fiction(subject) and (short_story(subject) or fiction(subject)):
        return True

    return False


def author_ok(author):
    """Return True if the author is consistent with what we want.

    Args:
        author (frozenset): A frozenset representing the author from the metadata of the story.
    Returns:
        bool: True if the author is consistent with what we want, False otherwise.
    """
    return len(list(author)) > 0


def title_ok(title):
    """Return True if the title is consistent with a valid story.

    Args:
        title (list[str]): A list of titles to check.

    Returns:
        bool: True if the title is consistent with what we want, False otherwise.
    """

    result = True
    if len(title) > 1:  # multiple titles
        for a_title in title:
            result = result and title_ok([a_title])

        return result

    if "; and" in title[0].strip().lower():
        return False

    if ", and" in title[0].split("\n")[0].strip().lower():
        return False

    if "index of the project gutenberg" in title[0].lower():
        return False

    for part_indicator in storymap.EXCLUDED_TITLE_PART_WORDS:
        if re.search(rf"{part_indicator}\s*\d+", title[0], re.IGNORECASE):
            return False

    for piece in title[0].split(" "):
        piece = piece.lower()

        if piece in storymap.EXCLUDED_TITLE_WORDS:
            return False

    return True


def story_excluded(story_id):
    """Return True if OK to try this story, False otherwise"""
    return story_id in storymap.STORIES_TO_EXCLUDE


def only_english(languages, target="en"):
    """Return True if the only language is the target language (default "en" for English).

    Args:
        languages (list or set): A list or set of language codes (e.g., ["en", "fr"])
            presumably from the metadata of a Gutenberg story.
        target (str): The target language code to check against (default is "en").
    Returns:
        bool: True if the only language is the target language, False otherwise.
    """
    if target not in languages:
        return False
    other_languages = set(languages)
    other_languages.remove(target)
    return not other_languages


def fiction(subject):
    """Return True if the subject contains fiction
    Args:
        subjects (frozenset): The subject from the gutenberg metadata.
    Returns:
        bool:  True if identified as fiction, False otherwse
    """

    for piece in list(subject):
        if "fiction" in piece.lower().strip():
            return True

    return False


def short_story(subject):
    """Return True if the subject contains a short story tag
    Args:
        subjects (frozenset): The subject from the gutenberg metadata.
    Returns:
        bool:  True if identified as a short story / short stories, False otherwse
    """

    for piece in list(subject):
        if "short stor" in piece.lower().strip():
            return True

    return False


def loc_fiction(subject):
    """Return True if the subject contains a fiction tag via library of congress keys
    Args:
        subjects (frozenset): The subject from the gutenberg metadata.
    Returns:
        bool:  True if identified as a PS or PR library of congress tag, False otherwse
    """

    for piece in list(subject):
        if piece in ["PS", "PR"]:
            return True

    return False


def bad_subjects(subjects):
    """Return True if the subject contains a bad topic (currently just epistolary)
    Args:
        subjects (frozenset): The subject from the gutenberg metadata.
    Returns:
        bool:  True if identified as bad, False otherwse
    """

    for subject in subjects:
        for bad_subject in storymap.EXCLUDED_SUBJECTS:
            if bad_subject in subject.lower():
                return True

    return False


#################################################################


def _metadata_rejection(metadata, story):
    """Apply the shared gathering and inspection eligibility rules without I/O."""
    if metadata is None or not metadata.subjects:
        return "No data for this story, skipping"
    if not metadata.titles:
        return "No title for this story, skipping"
    if not all(
        (
            subject_ok(metadata.subjects),
            only_english(metadata.languages),
            title_ok(metadata.titles),
            author_ok(metadata.authors),
        )
    ):
        return "Metadata not suitable, skipping."
    if story_excluded(story):
        return "Story on exclusion list, skipping."
    return None


def _inspect_metadata(story, metadata, source):
    """Build the same deterministic extraction report used by gather_story."""
    report = {
        "gutenberg_id": story,
        "metadata": (
            None
            if metadata is None
            else {
                "titles": list(metadata.titles),
                "authors": list(metadata.authors),
                "aliases": list(metadata.aliases),
                "subjects": list(metadata.subjects),
                "languages": list(metadata.languages),
            }
        ),
        "rejection": _metadata_rejection(metadata, story),
        "body": None,
        "provenance": None,
        "structure": None,
        "raw_opening": None,
        "confidence": "low",
    }
    if report["rejection"] is not None:
        return report
    prepared = source.read(metadata)
    # Physical newlines remain intact in the original-byte cache. Normalize only
    # at the paragraph parser boundary, matching the historical extraction rules.
    raw = prepared.cleaned.text.replace("\r\n", "\n").replace("\r", "\n")
    report["raw_opening"] = extraction_records.opening_lines(raw, extraction_records.RAW_LINES)
    text = raw.strip()
    # Stage 1: screen the untrimmed Gutenberg body *before* narrative cleanup.
    # A CONTENTS list or chapter sequence must not disappear during stripping.
    structure = structural_screen.inspect_structure(text)
    report["structure"] = structure.to_dict()
    report["provenance"] = prepared.provenance()
    if structure.reject:
        report["rejection"] = "Story has chapters, skipping. (raw structural screen: " + structure.reason + ")"
        return report

    # Stage 2: clean the narrative only after structural eligibility passes.
    body, diagnostics = clean_gutenberg_story(
        text,
        title=list(metadata.titles),
        authors=list(metadata.authors),
        pseudonyms=list(metadata.aliases),
        return_diagnostics=True,
    )

    report["body"] = body
    report["terminal_footnotes"] = diagnostics.get("terminal_footnotes")
    report["confidence"] = diagnostics["boundary_confidence"]
    report["provenance"] = prepared.provenance()
    if chaptered(body):
        report["rejection"] = "Story has chapters, skipping."
    elif len(body.split("\n\n")) <= 10:
        report["rejection"] = "Story is too short, skipping."
    return report


def inspect_story(story, *, source):
    """Return JSON-compatible metadata, body, rejection and source provenance.

    This replaces the notebook/debug helpers that printed partial results and
    silently fetched metadata or text. The caller supplies a GutenbergStorySource
    and owns its catalog lifetime and network policy. Rejected metadata causes no
    acquisition. Eligible text may be cached according to that explicit policy;
    no story output is written. Operational errors propagate, not eligibility
    rejections. A rejected short/chaptered story retains its body for inspection.
    """
    return _inspect_metadata(story, source.metadata(story), source)


@dataclasses.dataclass(frozen=True)
class StoryGatherResult:
    """One extraction outcome; reused outputs have not been requalified.

    disposition is written, reused or skipped. A published path is not evidence
    of a new source download: writing may also use an already cached source.
    """

    story: int
    path: str | None
    rejection: str | None
    disposition: str


def gather_story(gatherer, story, *, source):
    """Return the historical (ID, saved/existing path, rejection) tuple."""
    result = gather_story_result(gatherer, story, source=source)
    return result.story, result.path, result.rejection


def gather_story_result(gatherer, story, *, source):
    """Extract and atomically publish a story using an explicit source.

    Args:
        gatherer: DataGatherer owning the output collection directory.
        story: Positive Gutenberg ebook ID.
        source: GutenbergStorySource with a pinned catalog and explicit policy.

    Returns:
        StoryGatherResult distinguishing a new write, output reuse or exclusion.
        Source, decoding, cleanup and output errors propagate to the run boundary.
        An existing regular output is reused before source acquisition; its content
        is not revalidated.
    """
    metadata = source.metadata(story)
    rejection = _metadata_rejection(metadata, story)
    if rejection is not None:
        return StoryGatherResult(story, None, rejection, "skipped")
    title = metadata.titles[0]
    author = list(metadata.authors)
    file_name = names.title_and_author_to_filename(
        title, author, ext=constants.FILE_SUFFIX, max_len=50
    )

    title_db, author_part = file_name.split("__", 1)
    author_db = author_part.rsplit(".", 1)[0]

    # Checking must not insert anything: acquisition, extraction and publication
    # can still fail or reject this story.
    if registry.check_story(title_db, author_db):
        return StoryGatherResult(
            story, None, "Mass Quantities -- Story already appears", "skipped"
        )

    story_slug = os.path.splitext(file_name)[0]
    existing = (
        pathlib.Path(gatherer.path) / story_slug / discovery.CANONICAL_STORY_FILENAME
    )
    if story_output.existing(existing):
        # A previously published output is safe to register without acquiring
        # the source again. This also reconciles an unregistered existing file.
        registry.add_story(title_db, author_db, source="Gutenberg mass retrieval")
        return StoryGatherResult(story, str(existing), None, "reused")
    report = _inspect_metadata(story, metadata, source)
    if report["rejection"] is not None:
        return StoryGatherResult(story, None, report["rejection"], "skipped")
    data_to_save = {
        "name": title,
        "author": author,
        "body": report["body"],
        "metadata": {
            "author": author,
            "year": "Unknown",
            "url": report["provenance"]["source_uri"],
            "name": file_name,
            "gettenberg": report["provenance"],
        },
    }
    # Human overrides live beside story.json.  Do not consult them if story.json
    # already exists: existing stories are reused without re-extraction.
    story_dir = existing.parent
    override = extraction_records.load_override(
        story_dir, gutenberg_id=story, title=title
    )
    # Normalize first so the override is anchored to the actual saved text.
    normalization.normalize_story_dict(
        data_to_save, collection=storymap.TARGET_DIRECTORY, story_id=story_slug
    )
    if override is not None:
        data_to_save["body"] = extraction_records.apply_override(
            data_to_save["body"], override, gutenberg_id=story, title=title
        )
    record = extraction_records.extraction_record(
        gutenberg_id=story,
        title=title,
        authors=author,
        raw_text=report["raw_opening"],
        extracted_body=data_to_save["body"],
        overridden=override is not None,
        confidence=report["confidence"],
    )
    _, file_path = gatherer.ensure(story_slug)
    written = story_output.publish(file_path, data_to_save)

    # Only register a newly published story. A False result may mean another
    # process published the output first; do not assume publication succeeded.
    if written:
        extraction_records.save_extraction_record(pathlib.Path(file_path).parent, record)
        if report.get("terminal_footnotes"):
            _save_terminal_footnotes(
                pathlib.Path(file_path).parent, story, title, report["terminal_footnotes"]
            )
        # Only newly published stories receive year.json. In particular, do not
        # revisit or overwrite a reused story's existing publication-year record.
        publication_year.get_publication_date_from_id(
            story,
            source=source,
            save=True,
            story_dir=pathlib.Path(file_path).parent,
        )
        registry.add_story(title_db, author_db, source="Gutenberg mass retrieval")

    return StoryGatherResult(story, file_path, None, "written" if written else "reused")
