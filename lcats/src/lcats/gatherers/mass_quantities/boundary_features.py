"""Conservative recognition of short opening blocks after Gutenberg display matter.

Measured spacing is a *secondary* signal: no rule fires on blank lines alone.
All changes are backward only, protecting narrative text from deletion.
"""

from __future__ import annotations
import re

CREDIT = re.compile(
    r"(?i)^(?:illustrated?\s+by|first published in|first appeared in|originally published in|by\s+[A-Z][\w .,'’\-]{3,70}|written by\s+[A-Z])\b"
)
SCENE = re.compile(r"(?i)^(?:SCENE(?:\s+[IVX\d]+)?|ACT\s+[IVX\d]+|PROLOGUE|EPILOGUE)$")
DATE = re.compile(
    r"(?i)^_?(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}\b"
)
EDITORIAL = re.compile(
    r"(?i)^(?:produced by|transcrib|copyright|all rights reserved|contents|table of contents|preface|foreword|introduction|illustrations list)\b"
)


def _prev_block(lines, at):
    i = at - 1
    while i >= 0 and not lines[i].strip():
        i -= 1
    if i < 0:
        return None
    end = i + 1
    while i >= 0 and lines[i].strip():
        i -= 1
    return i + 1, end


def preserve_structural_opening(
    lines, lo, hi, title, authors, *, title_match, author_match, warnings
):
    """Inspect up to three adjacent small opening blocks, not arbitrary prose.

    Anchor the previous block to a byline, publication/illustration credit,
    repeated printed title, or a standalone scene/person/date indicator.
    Do not traverse other front matter or infer boundaries from spacing alone.
    """
    if not 0 < lo < len(lines):
        return lo
    b = _prev_block(lines, lo)
    if b is None:
        return lo
    first, stop = b
    if lo - first > 9:
        return lo
    text = " ".join(s.strip() for s in lines[first:stop]).strip()
    if not text or EDITORIAL.match(text):
        return lo
    old = _prev_block(lines, first)
    if old is None:
        return lo
    oldtext = " ".join(s.strip() for s in lines[old[0] : old[1]]).strip()
    # The previous block must itself be a *specific* bibliographic terminator.
    credit = bool(
        CREDIT.match(oldtext)
        or (
            old[1] - old[0] == 1
            and title_match(lines, old[0], min(hi, old[0] + 6), title) is not None
        )
        or (old[1] - old[0] == 1 and author_match(oldtext, authors))
    )
    # 1) Protect scene labels that directly follow the final printed title.
    if SCENE.fullmatch(text.strip("_* ")) and credit:
        warnings.append("scene_heading_after_title_preserved")
        return first
    # 2) Short opening prose immediately after final byline/credit. Restrict
    # to single-line blocks, not long editorial introductions/teasers.
    if (
        credit
        and stop - first == 1
        and len(text.split()) >= 4
        and not text.startswith("_")
    ):
        if not CREDIT.match(text) and (len(text) < 135):
            warnings.append("single_line_opening_after_credit_preserved")
            return first
    # 3) Unmarked illustration credit followed by an *unfinished* italic
    # narrative lead-in, continuing into ordinary prose after the blank line.
    if (
        re.match(r"(?i)^illustrated?\s+by\b", oldtext)
        and text.startswith("_")
        and text.endswith("_")
        and stop - first >= 3
        and len(text.split()) >= 16
        and not text.rstrip("_ ").rstrip().endswith((".", "?", "!"))
    ):
        warnings.append("unbracketed_illustration_opening_preserved")
        return first
    # 4) A named viewpoint followed by an italic date and first-person prose.
    # This is a three-block pattern, not merely an isolated all-caps title.
    if (
        DATE.match(oldtext)
        and old[1] - old[0] == 1
        and re.match(r"(?i)^(?:i|we|my)\b", text)
    ):
        behind = _prev_block(lines, old[0])
        if behind and behind[1] - behind[0] == 1:
            viewpoint = lines[behind[0]].strip()
            if re.fullmatch(r"[A-Z][A-Z\-]{2,24}", viewpoint):
                warnings.append("viewpoint_date_heading_preserved")
                return behind[0]
    # 5) An italic teaser often precedes actual prose. Preserve a short
    # first sentence rather than delete it, only if it starts with a speaker
    # or scene and the teaser is itself immediately after a credit.
    if (
        stop - first == 1
        and len(text.split()) >= 4
        and not text.startswith("_")
        and oldtext.startswith("_")
        and oldtext.endswith("_")
    ):
        prior = _prev_block(lines, old[0])
        if prior:
            prior_text = " ".join(s.strip() for s in lines[prior[0] : prior[1]])
            if CREDIT.match(prior_text) and (
                re.match(r'^["“‘]', text) or re.search(r'["“][^"”]+["”]', text)
            ):
                warnings.append("opening_after_italic_blurb_preserved")
                return first
    return lo
