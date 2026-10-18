"""Conservative, metadata-aware body boundaries after Gutenberg cleanup.

This layer interprets editorial headings; gettenberg.cleanup only handles the
Gutenberg envelope. Unknown material ends the opening-heading search. A later
byline, repeated title, or wrapped narrative line can never restart that search.
Selected offsets refer to the newline-normalized input, not original wire bytes.
"""

import dataclasses
import re
import unicodedata

POLICY_VERSION = "opening-prefix-v1"
_PARAGRAPH = re.compile(r"\S(?:.*?\S)?(?=\n[ \t]*\n|\Z)", re.DOTALL)
_END_NOTICE = re.compile(
    r"End of (?:the )?Project Gutenberg(?: EBook of |['’]s )(.+), by (.+)",
    re.IGNORECASE,
)


def _key(value):
    """Compare complete headings, allowing case, typography and line wrapping."""
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split()).strip(
        "_*. "
    )


def _values(values):
    """Accept the historical single-title string as well as metadata sequences."""
    return (values,) if isinstance(values, str) else values


def _titles(values):
    """Include explicitly delimited title/subtitle forms, never arbitrary words."""
    result = set()
    for title in _values(values):
        for value in (title, *re.split(r"[:\n]", title)):
            key = _key(value)
            if key:
                result.add(key)
    return result


def _authors(authors, aliases):
    """Retain catalog order and render inverted catalog names for printed bylines."""
    result = set()
    for name in (*_values(authors), *_values(aliases)):
        pieces = [p.strip() for p in name.split(",")]
        result.add(_key(name))
        if len(pieces) >= 2:
            result.add(_key(f"{pieces[1]} {pieces[0]}"))
    return result - {""}


def _heading(value, titles, authors):
    """Require a whole title or named byline, not a substring inside prose."""
    key = _key(value)
    return key in titles or re.sub(r"^by\s+", "", key) in authors


def _editorial(value):
    """Recognize only explicit opening production credits or illustration labels."""
    # A label followed by prose in the SAME paragraph is not an editorial
    # paragraph. Likewise "Illustrated by ..." can be an ordinary sentence;
    # without illustrator metadata we deliberately retain that ambiguous form.
    if re.fullmatch(r"\[Illustration(?:: [^\]\n]+)?\]", value, re.IGNORECASE):
        return True
    return (
        re.fullmatch(
            r"Produced by [\w\s,.'’&-]+Distributed Proofreading Team"
            r"(?: at https?://(?:www\.)?pgdp\.net/?)?",
            value,
            re.IGNORECASE,
        )
        is not None
    )


@dataclasses.dataclass(frozen=True, slots=True)
class BodyExtraction:
    """A contiguous body span with an explicit interpretation policy.

    Unknown front matter, notes, footnotes, closing bylines, and typography are
    retained. Diagnostics are review cues, not a claim of complete classification.
    No narrative sentence or interior separator is removed by this operation.
    """

    text: str
    content_start: int
    content_end: int
    diagnostics: tuple[str, ...]
    policy_version: str = POLICY_VERSION

    def provenance(self):
        """Describe derivation without copying the story or inventing wire offsets."""
        return {
            "policy": self.policy_version,
            "offset_basis": "newline_normalized_cleaned_text",
            "content_start": self.content_start,
            "content_end": self.content_end,
            "diagnostics": list(self.diagnostics),
        }


def extract(text, titles, authors, aliases=()):
    """Select a conservative story span from decoded, envelope-cleaned text.

    Normalize physical newlines, trim exterior whitespace, and consume only a
    contiguous prefix of known headings/credits. Titles/bylines wrapped over up
    to four paragraphs are recognized only when their joined text is an exact
    metadata match. The first unknown paragraph permanently ends heading search.
    Strip a terminal Gutenberg end notice only when its complete title and author
    agree with metadata. Unrecognized or nonterminal notices remain visible.

    Args:
        text: Decoded text after conservative envelope cleanup.
        titles: Catalog titles (or one historical title string).
        authors: Catalog author names, including inverted names.
        aliases: Catalog author aliases.

    Returns:
        BodyExtraction whose text is exactly the selected normalized-input span.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = list(_PARAGRAPH.finditer(text.rstrip()))
    if not paragraphs:
        return BodyExtraction("", 0, 0, ())
    title_keys = _titles(titles)
    author_keys = _authors(authors, aliases)
    start, end = paragraphs[0].start(), paragraphs[-1].end()
    diagnostics = []
    # Check the trailer before opening headings: an editorial-only input must
    # become empty/short, never a publishable footer fragment.
    trailer = paragraphs[-1]
    notice = _END_NOTICE.fullmatch(" ".join(trailer.group().split()))
    if notice and _key(notice[1]) in title_keys and _key(notice[2]) in author_keys:
        end = paragraphs[-2].end() if len(paragraphs) > 1 else start
        paragraphs.pop()
        diagnostics.append("corroborated_end_notice_removed")
    elif "project gutenberg" in trailer.group().casefold():
        diagnostics.append("unrecognized_end_notice_retained")

    index = 0
    while index < len(paragraphs):
        paragraph = paragraphs[index]
        consumed = 0
        for width in range(1, min(4, len(paragraphs) - index) + 1):
            value = " ".join(p.group() for p in paragraphs[index : index + width])
            if _heading(value, title_keys, author_keys):
                consumed = width
                break
        if not consumed and _editorial(paragraph.group()):
            consumed = 1
        if not consumed:
            break
        index += consumed
        start = paragraphs[index].start() if index < len(paragraphs) else end
    if index == 0 and paragraphs:
        diagnostics.append("unclassified_opening_retained")
    if any("transcriber" in p.group().casefold() for p in paragraphs[index:]):
        diagnostics.append("possible_editorial_note_retained")
    return BodyExtraction(text[start:end], start, end, tuple(diagnostics))
