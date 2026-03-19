# lcats/names.py
from __future__ import annotations
import re
from unidecode import unidecode  # hard requirement
from typing import Optional, Pattern, Final, Tuple
from lcats.utils import canonical_author

# -------- Constants --------

BASENAME_MAXIMUM_LENGTH: Final[int] = 72
BASENAME_VALIDATION_REGEX: Final[Pattern[str]] = re.compile(
    r"^[a-z0-9]+(?:_[a-z0-9]+)*\Z", flags=re.ASCII
)

# -------- Core primitives --------


def ascii_transliterate(text: str) -> str:
    """Unicode→ASCII transliteration (deterministic via unidecode)."""
    s = text.casefold()
    s = unidecode(s)
    # ensure pure ASCII (just in case)
    return s.encode("ascii", "ignore").decode("ascii").casefold()


def is_valid_basename(
    basename: str,
    *,
    max_len: int = BASENAME_MAXIMUM_LENGTH,
    pattern: Optional[Pattern[str]] = None,
) -> bool:
    """True iff basename is 1..max_len of [a-z0-9] words joined by single '_' (ASCII)."""
    if max_len < 1 or not basename or len(basename) > max_len:
        return False
    pat = pattern or BASENAME_VALIDATION_REGEX
    return bool(pat.fullmatch(basename))


def repair_basename(
    raw: str,
    *,
    max_len: int = BASENAME_MAXIMUM_LENGTH,
) -> str:
    """Lowercase ASCII slug: map non [a-z0-9] → '_', collapse runs, trim edges, truncate."""
    if max_len < 1:
        raise ValueError("max_len must be >= 1")
    s = ascii_transliterate(raw)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    if len(s) > max_len:
        s = s[:max_len]
    s = re.sub(r"_+", "_", s)
    s = s.strip("_")
    return s  # may be '' if nothing usable remains


def title_and_author_to_filename(
    title: str,
    authors: str,
    *,
    ext: str = ".json",
    max_len: int = BASENAME_MAXIMUM_LENGTH,
    allow_empty: bool = False,
) -> str:
    ext = normalize_extension(ext)
    # TODO(centaur): this max_len is now applied only to the title component, not the whole
    # basename. We need to come up with a policy for normalizing these longer titles while
    # making sure they remain unique.
    title_component = normalize_basename(
        title, max_len=max_len, allow_empty=allow_empty
    )[0]
    author_component = canonical_author.last_name(
        canonical_author.canonical_key(authors[0])
    )
    for author in authors[1:]:
        author_component = (
            author_component
            + "_"
            + canonical_author.last_name(canonical_author.canonical_key(author))
        )

    return title_component + "__" + author_component + ext


def normalize_extension(ext: str) -> str:
    """Normalize extension to start with '.' and be lowercase. Validates that it matches r'\.[a-z0-9]+'."""
    if not ext.startswith("."):
        ext = "." + ext
    ext = ext.lower()
    if not re.fullmatch(r"\.[a-z0-9]+", ext):
        raise ValueError(f"Invalid extension policy: {ext!r}")
    return ext


def title_to_filename(
    title: str,
    *,
    ext: str = ".json",
    max_len: int = BASENAME_MAXIMUM_LENGTH,
    allow_empty: bool = False,
) -> str:
    """Title (Unicode) → canonical ASCII filename (basename + ext).

    - Gets a base from the normalized title, and appends the normalized extension.
    - If basename is empty and allow_empty=False, raises ValueError.
    - Extension must match r'\.[a-z0-9]+' and is lowered.
    """
    ext = normalize_extension(ext)
    base = normalize_basename(title, max_len=max_len, allow_empty=allow_empty)[0]
    return f"{base}{ext}" if base else ext


# -------- Convenience helper --------


def normalize_basename(
    basename: str,
    *,
    max_len: int = BASENAME_MAXIMUM_LENGTH,
    allow_empty: bool = False,
) -> Tuple[str, bool]:
    """Return (result, changed). If already valid, returns (basename, False);
    else returns (repair_basename(basename), True)."""
    if is_valid_basename(basename, max_len=max_len):
        return basename, False
    base = repair_basename(basename, max_len=max_len)
    if not base and not allow_empty:
        raise ValueError("Normalizing produced empty basename under current policy.")
    return base, True
