"""High-precision magazine-teaser removal for Gutenberg narrative boundaries.

The rule is deliberately narrow. It recognizes one short italicized display
blurb followed promptly by a decorative separator and a prose paragraph,
provided bibliographic/display material precedes it. It does *not* remove
longer italicized fictional prologues or choose a start from spacing alone.

Measured on 1,318 human-reviewed training examples; see study_frontmatter.py.
"""
from __future__ import annotations
import re
from typing import Sequence

_SEPARATOR = re.compile(
    r'^\s*(?:(?:\*\s*){3,}|(?:[-=~#]\s*){3,}|<tb>|\*{3,})\s*$', re.I
)
_CREDIT_OR_DISPLAY = re.compile(
    r'(?im)^\s*(?:illustrat(?:ed|ion|or)|by\s+\w|written by\b|'
    r'(?:[A-Z][A-Z\W]{5,80}))'
)


def _blocks(lines: Sequence[str], start: int, stop: int):
    """Consecutive nonblank physical-line blocks with original offsets."""
    out = []
    at = start
    while at < stop:
        if not lines[at].strip():
            at += 1
            continue
        beginning = at
        while at < stop and lines[at].strip():
            at += 1
        out.append((beginning, at, ' '.join(s.strip() for s in lines[beginning:at])))
    return out


def refine_promotional_blurb_boundary(
    lines: Sequence[str], start: int, end: int, title=None, authors=None,
    warnings: list[str] | None = None,
) -> int:
    """Move start *forward* only for a tightly bounded magazine blurb.

    Unlike the backward-only narrative safeguards, this operation can remove
    text. It is therefore limited to a single, short, fully italicized blurb
    before the first nearby separator; does not skip over prose prologues;
    and never fires on blank-line counts alone. Use only after the existing
    conservative start safeguards, and only after raw structural screening.
    """
    if start < 0 or start >= end:
        return start
    blocks = _blocks(lines, start, min(end, start + 36))
    for index, (a, b, value) in enumerate(blocks):
        if b - a != 1 or not _SEPARATOR.fullmatch(value):
            continue
        if index < 1 or index + 1 >= len(blocks):
            continue
        prior, following = blocks[index - 1], blocks[index + 1]
        # Do not jump across two or more italic prose blocks: these may be
        # a real fictional prologue followed by a scene separator.
        if sum(1 for item in blocks[:index] if item[2].startswith("_") and item[2].endswith("_")) > 1:
            continue
        # At most fifteen physical lines total: a long prologue or an
        # extended sequence of narrative paragraphs must remain untouched.
        if following[0] - b > 6 or following[0] - start > 15:
            continue
        if len(following[2]) < 65 and len(following[2].split()) < 9:
            continue
        if not (prior[2].startswith('_') and prior[2].endswith('_')):
            continue
        if prior[1] - prior[0] > 6 or len(prior[2]) > 450:
            continue
        # Very conservative first-person safeguard; these are frequently
        # genuine prologues, not advertising copy.
        if re.search(r'(?i)\b(?:I|we|my|our)\b', prior[2]):
            continue
        previous_context = '\n'.join(lines[max(0, start - 35):prior[0]])
        if not _CREDIT_OR_DISPLAY.search(previous_context):
            continue
        if warnings is not None:
            warnings.append('short_italic_teaser_separator_removed')
        return following[0]
    return start
