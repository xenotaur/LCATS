"""Pre-cleanup structural screening for Gutenberg single-story eligibility.

This is deliberately separate from narrative text cleanup: it runs on the
original Gutenberg *body*, before title-page/preface removal or line unwrapping.
No positive result depends on preserving front matter in the published story.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import re


@dataclass(frozen=True)
class StructureFinding:
    code: str
    line: int  # one based
    excerpt: str

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class StructuralDecision:
    reject: bool
    reason: str | None
    findings: tuple[StructureFinding, ...]

    def to_dict(self):
        return {'reject': self.reject, 'reason': self.reason,
                'findings': [finding.to_dict() for finding in self.findings]}


CONTENTS = re.compile(r'^\s*(?:table\s+of\s+contents|contents)\s*[:.]?\s*$', re.I)
CHAPTER = re.compile(r'^\s*(?:chapter|chap\.|part|book)\s+(?P<number>[IVXLCDM]+|\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b(?:\s*[:.\-—]\s*.*|\s+\S.*)?\s*$', re.I)
ROMAN = re.compile(r'^\s*(?P<number>I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\s*(?:[.]\s*(?:--\s*)?[A-Z].*|[—\-]{1,2}\s+[A-Z].*)?\s*$', re.I)
ARABIC = re.compile(r'^\s*(?P<number>\d{1,2})\s*[.]\s*\S.{2,}$')
BRACKET_START = re.compile(r'^\s*\[\s*(?:transcriber[\'’]s?\s+notes?|illustrations?|sidenote|image|figure|plate)\b', re.I)
PG_MARKER = re.compile(r'^\s*\*{3}\s*(?:START|END) OF (?:THE|THIS) PROJECT GUTENBERG', re.I)
TOC_ITEM = re.compile(r'^\s*(?:\d+\s*[.:]\s*)?[\w\'“”‘’—\-][^\n]{1,80}(?:\s*\.{2,}\s*\d+|\s{3,}\d+)\s*$')


def _region_lines(text: str) -> list[tuple[int, str]]:
    """Ignore PG wrappers, but preserve absolute 1-based line indices."""
    lines = text.replace('\r\n','\n').replace('\r','\n').split('\n')
    start = 0
    end = len(lines)
    for index, line in enumerate(lines):
        if PG_MARKER.match(line) and re.search(r'\bSTART\b', line, re.I):
            start = index + 1
            break
    for index in range(start, len(lines)):
        if PG_MARKER.match(lines[index]) and re.search(r'\bEND\b', lines[index], re.I):
            end = index
            break
    return [(i+1, lines[i]) for i in range(start,end)]


def _ignore_bracket_blocks(indexed: list[tuple[int,str]]) -> list[tuple[int,str]]:
    output = []
    inside = False
    for line_no, line in indexed:
        if inside:
            if ']' in line:
                inside = False
            continue
        if BRACKET_START.match(line):
            inside = ']' not in line
            continue
        output.append((line_no,line))
    return output


def _contents_list_evidence(lines: list[tuple[int,str]], i: int) -> bool:
    """Only call a TOC decisive when its immediate vicinity resembles a list.

    This avoids rejecting a story that merely begins with 'Contents'.
    A two-item all-caps story list is sufficient even without page numbers.
    """
    following = [s.strip() for _,s in lines[i+1:i+32] if s.strip()]
    if not following:
        return False
    if any(CHAPTER.match(s) for s in following[:12]):
        return True
    if sum(bool(TOC_ITEM.match(s)) for s in following[:16]) >= 2:
        return True
    caps = [s for s in following[:12] if 2 <= len(s) <= 70
            and any(ch.isalpha() for ch in s) and s.isupper()
            and not s.startswith(('BY ', 'COPYRIGHT', 'ILLUSTRATION'))]
    return len(caps) >= 2


def inspect_structure(text: str) -> StructuralDecision:
    """Return evidence for a *multi*-section work in untouched source order.

    Recognizes contents lists and repeated chapter/part labels. A lone section
    title is insufficient: some valid short stories are explicitly 'I'.
    This deliberately does not use the old all-caps-title count, which can
    mistake a title page or byline for a chapter sequence.
    """
    lines = _ignore_bracket_blocks(_region_lines(text))
    headings: list[StructureFinding] = []
    toc: list[StructureFinding] = []
    for i,(line_no,raw) in enumerate(lines):
        s = raw.strip()
        # A heading can be italicized with underscore delimiters in PG text.
        heading = s.strip("_*").strip()
        if not s:
            continue
        if CONTENTS.fullmatch(heading):
            if _contents_list_evidence(lines,i):
                toc.append(StructureFinding('contents_list',line_no,s))
            continue
        m = CHAPTER.fullmatch(heading)
        if m:
            headings.append(StructureFinding('chapter_heading',line_no,s[:110]))
            continue
        # Numbered headings are display-style and short, not numbered prose
        # sentences, technical measurements, or instructions in the narrative.
        # A sentence ending in a period is not evidence of a chapter boundary.
        eligible_heading = (len(heading) <= 60 and not heading.endswith(('.', ':', ';', '!', '?')))
        # A numbered title is not a long sentence or a serial number/measurement.
        if ARABIC.fullmatch(heading) and re.search(r'^\d{1,2}\.\s', heading) is None:
            eligible_heading = False
        # Bare Roman numerals (I., II.) do end in a period.
        if re.fullmatch(r'(?:I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\.', heading, re.I):
            eligible_heading = True
        if not eligible_heading:
            continue
        # Bare Roman numerals only count when they appear as *standalone* lines.
        if ROMAN.fullmatch(heading):
            headings.append(StructureFinding('numbered_section',line_no,s[:110]))
            continue
        # Numbered titled sections (e.g. '1. The Shadow on the Chimney').
        if ARABIC.fullmatch(heading):
            headings.append(StructureFinding('numbered_section',line_no,s[:110]))
    if toc:
        return StructuralDecision(True, 'contents_list', tuple(toc+headings))
    # Two chapter headings (or two numbered sections), not necessarily adjacent.
    chapter = [x for x in headings if x.code == 'chapter_heading']
    numbered = [x for x in headings if x.code == 'numbered_section']
    if len(chapter) >= 2:
        return StructuralDecision(True,'multiple_chapter_headings',tuple(headings))
    if len(numbered) >= 2:
        # Inline numbered lists can occur inside a narrative (e.g. a fictional
        # inventory of nine professors). A run of 3+ closely spaced numbered
        # lines is list data, not three chapters. Drop those clusters.
        list_indices = set()
        for i in range(len(numbered)):
            a=i
            while a > 0 and numbered[a].line - numbered[a-1].line <= 2:
                a -= 1
            b=i
            while b+1 < len(numbered) and numbered[b+1].line - numbered[b].line <= 2:
                b += 1
            if b-a+1 >= 3:
                list_indices.update(range(a,b+1))
        numbered = [x for i,x in enumerate(numbered) if i not in list_indices]
    if len(numbered) >= 2:
        # Sections in a story are separated by substantive text, not consecutive
        # list items. Also require distinct labels (not repeated list item 1).
        distinct = set()
        for n in numbered:
            token = n.excerpt.strip('_* ').split()[0].rstrip('.:—-')
            distinct.add(token.casefold())
        separated = any(b.line - a.line >= 5 for a,b in zip(numbered,numbered[1:]))
        # A book's advertising/catalog list may enumerate other publications,
        # commonly including several 'By Author' phrases. That is not evidence
        # that the present story itself has chapters (e.g. PG 39216).
        matching = [x for x in numbered if re.search(r'\bby\s+[A-Z]',x.excerpt,re.I)]
        if len(matching) < 2 and len(distinct) >= 2 and separated:
            return StructuralDecision(True,'multiple_numbered_sections',tuple(headings))
    # Mixed style headings are evidence only if one is explicitly CHAPTER/PART.
    if chapter and numbered:
        return StructuralDecision(True,'mixed_chapter_sections',tuple(headings))
    return StructuralDecision(False,None,tuple(headings))
