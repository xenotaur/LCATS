"""Code produced by OpenAI ChatGPT 5.0, modified by K. Moorman"""

import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Dict

HONORIFICS = {
    "mr",
    "mrs",
    "ms",
    "miss",
    "mx",
    "dr",
    "prof",
    "sir",
    "madam",
    "dame",
    "lord",
    "lady",
}

# Common particles that may belong with the surname
SURNAME_PARTICLES = {
    "da",
    "de",
    "del",
    "della",
    "der",
    "di",
    "du",
    "la",
    "le",
    "van",
    "von",
    "bin",
    "binti",
    "al",
    "st",
    "st.",
}

# Generational suffixes we standardize; not academic/professional degrees.
SUFFIXES = {
    "jr": "Jr",
    "sr": "Sr",
    "ii": "II",
    "iii": "III",
    "iv": "IV",
    "v": "V",
}


@dataclass
class ParsedName:
    first: str
    middles: List[str]
    last: str
    suffix: Optional[str] = None


def _strip_diacritics(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def _clean_token(tok: str) -> str:
    tok = tok.replace(".", "").replace("’", "'").strip()
    tok = re.sub(
        r"[^\w'\- ]+", "", tok
    )  # keep letters, digits, apostrophe, hyphen, space
    return tok


def _normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def parse_name(
    raw: str,
    *,
    ascii_only: bool = True,
    nickname_map: Optional[Dict[str, str]] = None,
) -> ParsedName:
    """
    Parse a personal name into first/middles/last/suffix.
    Supports:
      - 'First Middle Last'
      - 'Last, First Middle'
      - optional suffix (with or without comma): Jr., Sr., II/III/IV/V
      - surname particles (e.g., 'van', 'de') stuck to the last name
    """

    if not raw or not raw.strip():
        raise ValueError("Empty name")

    s = raw.strip()
    if ascii_only:
        s = _strip_diacritics(s)

    # Normalize punctuation spacing
    s = s.replace(" ,", ",").replace(", ", ", ").replace("  ", " ")
    s = _normalize_space(s)

    # Separate any trailing suffix like ", Jr." or "Jr."
    # We'll capture suffix but not include it in canonical keys by default.
    suffix = None
    # Capture comma-separated suffix
    m = re.search(r",\s*([A-Za-z\.]+)$", s)
    if m:
        cand = _clean_token(m.group(1)).lower()
        if cand in SUFFIXES:
            suffix = SUFFIXES[cand]
            s = s[: m.start()].strip()

    # Or suffix at end without comma
    if suffix is None:
        m2 = re.search(r"\b([A-Za-z\.]+)$", s)
        if m2:
            cand = _clean_token(m2.group(1)).lower()
            if cand in SUFFIXES:
                suffix = SUFFIXES[cand]
                s = s[: m2.start()].strip()

    # Split on comma to detect "Last, First Middle" format
    parts = [p.strip() for p in s.split(",") if p.strip()]
    # tokens: List[str]  # not used
    if len(parts) == 2:
        # Format: Last, First Middlename(s)
        last_part, first_part = parts
        last_tokens = [
            _clean_token(t).lower() for t in _normalize_space(last_part).split()
        ]
        first_tokens = [
            _clean_token(t).lower() for t in _normalize_space(first_part).split()
        ]
    else:
        # Assume "First Middle Last"
        first_tokens = [_clean_token(t).lower() for t in _normalize_space(s).split()]
        last_tokens = []

    # Remove leading honorifics from first tokens
    while first_tokens and first_tokens[0] in HONORIFICS:
        first_tokens.pop(0)

    # If last not provided yet (no comma form), infer from the end and fold surname particles
    if not last_tokens:
        # Walk from the end to capture particles with surname (e.g., "van der waals")
        ft = first_tokens
        if len(ft) == 1:
            first, middles, last = ft[0], [], ""
        else:
            # start with the last token as surname core
            last_group = [ft[-1]]
            i = len(ft) - 2
            while i >= 0 and ft[i] in SURNAME_PARTICLES:
                last_group.insert(0, ft[i])
                i -= 1
            last = " ".join(last_group)
            core = ft[: i + 1]  # everything before last name block
            if not core:
                first, middles = "", []
            else:
                first, *middles = core
    else:
        # Comma-form: last part already extracted; treat particles as part of last as-is
        if len(last_tokens) == 1:
            last = last_tokens[0]
        else:
            # Keep particles together
            last = " ".join(last_tokens)
        if not first_tokens:
            first, middles = "", []
        else:
            first, *middles = first_tokens

    # Expand nickname to formal given name if provided
    if nickname_map and first in nickname_map:
        first = nickname_map[first].lower()

    # Title case consistently (preserve apostrophes/hyphens nicely)
    def _tcase(name: str) -> str:
        def tpart(p: str) -> str:
            if not p:
                return p
            # handle O'Neill, D'Angelo, McDonald-ish (lightweight)
            if "'" in p:
                return "_".join(sub.capitalize() for sub in p.split("'"))
            if "-" in p:
                return "_".join(sub.capitalize() for sub in p.split("-"))
            return p.capitalize()

        return " ".join(tpart(p) for p in name.split(" "))

    first = _tcase(first)
    middles = [_tcase(m) for m in middles if m]
    last = _tcase(last)

    return ParsedName(first=first, middles=middles, last=last, suffix=suffix)


def canonical_key(
    name: str,
    *,
    ascii_only: bool = True,
    nickname_map: Optional[Dict[str, str]] = None,
    include_middles: bool = False,
    include_suffix: bool = False,
    case: str = "lower",  # "lower" | "upper" | "title"
) -> str:
    """
    Build a canonical key. By default, ignores middles and suffix.
    Returns 'last,first' in chosen case.
    """
    p = parse_name(name, ascii_only=ascii_only, nickname_map=nickname_map)

    pieces = [p.last, p.first]
    if include_middles and p.middles:
        pieces.extend(p.middles)
    if include_suffix and p.suffix:
        pieces.append(p.suffix)

    key = "_".join(filter(None, [pieces[0], pieces[1] if len(pieces) > 1 else ""]))
    # If middles/suffix included, append after a second comma
    if (include_middles and p.middles) or (include_suffix and p.suffix):
        tail = []
        if include_middles and p.middles:
            tail.extend(p.middles)
        if include_suffix and p.suffix:
            tail.append(p.suffix)
        key = key + "_" + " ".join(tail)

    key = key.replace(" ", "_")
    if case == "lower":
        return key.lower()
    if case == "upper":
        return key.upper()
    if case == "title":
        return key  # already title-cased
    raise ValueError("case must be one of: lower, upper, title")


def last_name(canonical_name):
    split_name = canonical_name.split("_")
    if len(split_name) == 3:
        last = split_name[0] + "_" + split_name[1]
    else:
        last = split_name[0]

    return last


def first_name(canonical_name):
    split_name = canonical_name.split("_")
    if len(split_name) == 3:
        first = split_name[2]
    elif len(split_name) == 1:
        first = ""
    else:
        first = split_name[1]

    return first


def add_authors(
    file_name, authors, ext: str = ".json", max_len: int = 72
):  #  needs to go in constants BASENAME_MAXIMUM_LENGTH):
    file_name = file_name.split(ext)[0]
    file_name = file_name + "__"
    first = True
    for author in authors:
        if first:
            first = False
        else:
            file_name = file_name + "-"

        file_name = file_name + canonical_key(author)

    file_name = file_name + ext

    if len(file_name) > max_len:
        file_name = file_name[:max_len]

    return file_name
