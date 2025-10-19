# lcats/names.py
from __future__ import annotations
import re
from unidecode import unidecode  # hard requirement
from typing import Optional, Pattern, Final, Tuple


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


def title_to_filename(
    title: str,
    *,
    ext: str = ".json",
    max_len: int = BASENAME_MAXIMUM_LENGTH,
    allow_empty: bool = False,
) -> str:
    """Title (Unicode) → canonical ASCII filename (basename + ext).

    - Produces a basename via `repair_basename`.
    - If basename is empty and allow_empty=False, raises ValueError.
    - Extension must match r'\.[a-z0-9]+' and is lowered.
    """
    # normalize/validate extension
    if not ext.startswith("."):
        ext = "." + ext
    ext = ext.lower()
    if not re.fullmatch(r"\.[a-z0-9]+", ext):
        raise ValueError(f"Invalid extension policy: {ext!r}")

    base = repair_basename(title, max_len=max_len)
    if not base and not allow_empty:
        raise ValueError("Title produced empty basename under current policy.")
    return f"{base}{ext}" if base else ext


# -------- Convenience helper --------


def normalize_basename(
    basename: str,
    *,
    max_len: int = BASENAME_MAXIMUM_LENGTH,
) -> Tuple[str, bool]:
    """Return (result, changed). If already valid, returns (basename, False);
    else returns (repair_basename(basename), True)."""
    if is_valid_basename(basename, max_len=max_len):
        return basename, False
    return repair_basename(basename, max_len=max_len), True
