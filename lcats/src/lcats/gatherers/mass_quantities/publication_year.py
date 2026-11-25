"""Extract an explicitly stated publication month and year from Gutenberg raw text.

Install as ``lcats/gatherers/mass_quantities/publication_year.py``.

``get_publication_date_from_text(raw_text)`` accepts the original, uncleaned
Gutenberg text and returns e.g. ``('October', '1950')`` or ``(None, '1918')``.

The extractor deliberately does not interpret Gutenberg release/update dates,
copyright years without months, title-page years, dates within story prose,
or dates that cannot be associated with an identifiable publication statement.
A magazine *issue* month is treated as the original publication month, when
clearly labeled as the source of the transcription.

No third-party dependencies. If the LCATS parser is installed, its Gutenberg
START/END markers are reused; otherwise equivalent local patterns are used.
"""

from __future__ import annotations

import re
import json
import os
import tempfile
import pathlib

_MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_MONTH_PART = r"(" + "|".join(_MONTH_NAMES) + r")"
_YEAR_PART = r"((?:1[5-9]\d{2}|20\d{2}))"
# Handle "June of 1960" as well as "June, 1960" and "June 1960".
_DATE = re.compile(
    r"\b" + _MONTH_PART + r"(?:\s*,?\s+|,\s*)(?:of\s+)?" + _YEAR_PART + r"\b", re.I
)
_START = re.compile(
    r"^\s*\*{3}\s*START OF (?:THE|THIS) PROJECT GUTENBERG (?:EBOOK|ETEXT)\b", re.I
)
_END = re.compile(
    r"^\s*\*{3}\s*END OF (?:THE|THIS) PROJECT GUTENBERG (?:EBOOK|ETEXT)\b", re.I
)
_RELEASE = re.compile(
    r"\b(?:release\s+date|posting\s+date|last\s+updated|updated|date\s+of\s+release|e-?book\s*#|gutenberg\s+release)\b",
    re.I,
)
_PUBLICATION = re.compile(
    r"\b(?:first\s+published|originally\s+published|initially\s+published|"
    r"published\b|publication\s+date|first\s+appeared\s+in|"
    r"originally\s+appeared\s+in|appeared\s+in|first\s+printed\s+in|"
    r"printed\s+in|originally\s+printed\s+in|"
    r"this\s+(?:e-?text|etext)\s+was\s+produced\s+from)\b",
    re.I,
)
_SOURCE = re.compile(
    r"\b(?:transcriber.s?\s+notes?|e-?text\s+prepared\s+from|transcribed\s+from|produced\s+from)\b",
    re.I,
)
_PERIODICAL = re.compile(
    r"\b(?:galaxy(?:\s+science\s+fiction)?|amazing\s+stories|"
    r"planet\s+stories|analog(?:\s+science\s+(?:fact\s*(?:&|and)\s*)?fiction)?|"
    r"astounding(?:\s+science\s+fiction)?|"
    r"worlds\s+of\s+if(?:\s+science\s+fiction)?|"
    r"imagination(?:\s+stories\s+of\s+science\s+and\s+fantasy)?|"
    r"fantastic\s+(?:adventures|story|stories|universe)|"
    r"if\s+worlds\s+of\s+science\s+fiction|"
    r"\b(?:science\s+fiction|magazine|monthly|weekly|quarterly)\b)\b",
    re.I,
)


def _body_after_start(raw_text: str) -> list[str]:
    lines = raw_text.splitlines()
    try:
        from lcats.gatherers.mass_quantities import parser as lcats_parser

        start, end = lcats_parser.START, lcats_parser.END
    except (ImportError, AttributeError):
        start, end = _START, _END
    for i, line in enumerate(lines):
        if start.match(line):
            lines = lines[i + 1 :]
            break
    for i, line in enumerate(lines):
        if end.match(line):
            return lines[:i]
    return lines


_YEAR_ONLY = re.compile(r"\b((?:1[5-9]\d{2}|20\d{2}))\b")
_YEAR_CONTEXT = re.compile(
    r"\b(?:first\s+published|originally\s+published|initially\s+published|"
    r"published|publication\s+date|first\s+appeared\s+in|"
    r"originally\s+appeared\s+in|appeared\s+in|first\s+printed\s+in|"
    r"printed\s+in|produced\s+from|transcribed\s+from)\b",
    re.I,
)
_COPYRIGHT = re.compile(r"\b(?:copyright|©|\(c\))\b", re.I)


def get_publication_date_from_text(raw_text: str) -> tuple[str | None, str | None]:
    """Return ``(month, year)`` from publication evidence in raw Gutenberg text.

    Only scan the first 160 lines after the Gutenberg START marker. An explicit
    first-publication date outranks later edition/issue dates. Year-only
    publication statements are supported; year-only copyright is a *fallback
    proxy*, not proof of the original publication date. When no defensible
    date can be extracted, return ``(None, None)``.
    """
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be a string")
    if not raw_text.strip():
        return (None, None)

    lines = _body_after_start(raw_text)[:160]
    candidates: list[tuple[int, int, str | None, str]] = []
    for i, line in enumerate(lines):
        previous = " ".join(x.strip() for x in lines[max(0, i - 2) : i] if x.strip())
        nearby = (previous + " " + line).strip()
        # Treat a month at the end of one physical line followed by a year
        # at the start of the next as a single publication date.
        joined = line
        if i + 1 < len(lines) and re.search(
            r"\b(?:" + "|".join(_MONTH_NAMES) + r")\s*[,]?[\s]*$", line, re.I
        ):
            joined += " " + lines[i + 1].strip()
        for match in _DATE.finditer(joined):
            before = joined[: match.start()]
            if _RELEASE.search(nearby) or _RELEASE.search(before[-100:]):
                continue
            lead = (previous + " " + before).strip()
            first_pub = re.search(
                r"\b(?:first|originally|initially)\s+(?:published|appeared|printed)\b",
                lead,
                re.I,
            )
            if first_pub:
                score = 5
            elif _PUBLICATION.search(nearby) and not _COPYRIGHT.search(before[-40:]):
                score = 4
            elif _PERIODICAL.search(nearby) and (
                _SOURCE.search(nearby) or _PERIODICAL.search(before)
            ):
                score = 3
            elif _PERIODICAL.search(before):
                score = 3
            else:
                continue
            candidates.append((score, -i, match.group(1).capitalize(), match.group(2)))

        # Consider a year without a month ONLY when clearly tied to publication
        # or, as the least preferred fallback, an explicit copyright notice.
        if _DATE.search(line) or _RELEASE.search(nearby):
            continue
        for match in _YEAR_ONLY.finditer(line):
            before = line[: match.start()]
            lead = (previous + " " + before).strip()
            if re.search(
                r"\b(?:first|originally|initially)\s+(?:published|appeared|printed)\b",
                lead,
                re.I,
            ):
                score = 2
            elif _YEAR_CONTEXT.search(lead[-170:]):
                score = 1
            elif _COPYRIGHT.search(before[-65:]):
                score = 0
            else:
                continue
            candidates.append((score, -i, None, match.group(1)))

    if not candidates:
        return (None, None)
    candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
    _, _, month, year = candidates[0]
    return (month, year)


def _resolve_story_dir(
    metadata, *, story_dir: str | pathlib.Path | None
) -> pathlib.Path:
    """Resolve exactly the same story slug and DataGatherer root as LCATS."""
    if story_dir is not None:
        return pathlib.Path(story_dir)
    from lcats import constants
    from lcats.utils import names
    from lcats.gatherers import downloaders
    from lcats.gatherers.mass_quantities import storymap

    title = metadata.titles[0]
    authors = list(metadata.authors)
    filename = names.title_and_author_to_filename(
        title, authors, ext=constants.FILE_SUFFIX, max_len=50
    )
    return (
        pathlib.Path(
            downloaders.DataGatherer(
                storymap.TARGET_DIRECTORY,
                description="Single stories from Gutenberg",
                license="Public domain, from Project Gutenberg.",
            ).path
        )
        / pathlib.Path(filename).stem
    )


def _save_year_json(directory: pathlib.Path, record: dict) -> pathlib.Path:
    """Write atomically without changing story.json or override.json."""
    directory.mkdir(parents=True, exist_ok=True)
    dest = directory / "year.json"
    fd, tmp = tempfile.mkstemp(prefix=".year-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, dest)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return dest


__all__ = ["get_publication_date_from_text"]


def get_publication_date_from_id(
    gutenberg_id: int,
    *,
    source,
    save: bool = False,
    story_dir: str | pathlib.Path | None = None,
) -> tuple[str | None, str | None]:
    """Retrieve the Gutenberg text and return ``(month, year)``.

    If ``save`` is true, write ``year.json`` to the LCATS story directory,
    using exactly the normalized title/author slug LCATS uses for story.json.
    ``story_dir`` may override this directory (useful for testing or custom
    output roots). The JSON field ``deterministic_year`` is the extracted year
    string or null; ``deterministic_month`` stores the optional month.

    Returns ``(None, None)`` if no publication date is supported by the text.
    Source retrieval errors propagate and never create a misleading record.
    """
    if (
        isinstance(gutenberg_id, bool)
        or not isinstance(gutenberg_id, int)
        or gutenberg_id <= 0
    ):
        raise ValueError("gutenberg_id must be a positive integer")
    if source is None:
        raise ValueError("A configured Gettenberg source is required")
    metadata = source.metadata(gutenberg_id)
    if metadata is None:
        return (None, None)
    prepared = source.read(metadata)
    month, year = get_publication_date_from_text(prepared.cleaned.text)
    if save:
        directory = _resolve_story_dir(metadata, story_dir=story_dir)
        titles = list(metadata.titles)
        authors = list(metadata.authors)
        _save_year_json(
            directory,
            {
                "gutenberg_id": gutenberg_id,
                "title": titles,
                "authors": authors,
                "deterministic_month": month,
                "deterministic_year": year,
            },
        )
    return (month, year)


__all__ = ["get_publication_date_from_text", "get_publication_date_from_id"]
