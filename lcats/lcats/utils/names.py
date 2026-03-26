"""Utilities for normalizing and validating filenames, basenames, and extensions."""

from __future__ import annotations
import hashlib
import os
import re
from typing import Optional, Pattern, Final, Tuple
from urllib.parse import urlparse, unquote

from unidecode import unidecode

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
    """Convert a Unicode title and author(s) to a canonical ASCII filename (basename + ext).

    - Gets a base from the normalized title and author(s), and appends the normalized extension.
    - If basename is empty and allow_empty=False, raises ValueError.
    - Extension must match r'\.[a-z0-9]+' and is lowered.
    - Author component is the last name(s) of the author(s), joined by '__' if multiple.
    - If multiple authors, the title and author components are joined by '__' to avoid ambiguity
      (e.g. "The Great Gatsby" by "F. Scott Fitzgerald" and "John Doe" would yield
      "the_great_gatsby__fitzgerald__doe.json" instead of "the_great_gatsby__fitzgerald.json"
      which could be confused with a single author named "F. Scott Fitzgerald").

    Args:
        title: The title to convert.
        authors: The author(s) to convert (comma-separated if multiple).
        ext: The extension to append to the basename (default: ".json").
        max_len: The maximum length of the basename (default: BASENAME_MAXIMUM_LENGTH).
        allow_empty: Whether to allow an empty basename (default: False).
    Returns:
        The normalized filename.
    Raises:
        ValueError: If the normalized basename is empty and allow_empty is False, or if the
            extension is invalid.
    """
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
    """Normalize extension to start with '.' and lowercase; validates match to r'\.[a-z0-9]+'."""
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
    """Convert a Unicode title to a canonical ASCII filename (basename + ext).

    - Gets a base from the normalized title, and appends the normalized extension.
    - If basename is empty and allow_empty=False, raises ValueError.
    - Extension must match r'\.[a-z0-9]+' and is lowered.

    Args:
        title: The title to convert.
        ext: The extension to append to the basename (default: ".json").
        max_len: The maximum length of the basename (default: BASENAME_MAXIMUM_LENGTH).
        allow_empty: Whether to allow an empty basename (default: False).
    Returns:
        The normalized filename.
    Raises:
        ValueError: If the normalized basename is empty and allow_empty is False, or if the
            extension is invalid.
    """
    ext = normalize_extension(ext)
    base = normalize_basename(title, max_len=max_len, allow_empty=allow_empty)[0]
    return f"{base}{ext}" if base else ext


def url_to_filename(url):
    """Generate a unique filename from a URL.

    This function creates a unique filename by hashing the URL and preserving the file extension
    if it exists. The filename is generated as follows:
    1. Parse the URL to extract the path and query components.
    2. Combine the path and query to create a unique string.
    3. Hash the unique string using SHA-256 to ensure uniqueness and avoid collisions.
    4. Extract the file extension from the URL path, if it exists.
    5. Combine the hash and the file extension to create the final filename.

    Args:
        url: The URL to generate a filename from.
    Returns:
        A unique filename derived from the URL.
    """
    # Parse the URL
    parsed_url = urlparse(url)

    # Extract the path and query to form the base of the filename
    url_path = unquote(parsed_url.path)
    url_query = unquote(parsed_url.query)

    # Combine path and query to form a unique identifier
    unique_string = url_path + "?" + url_query if url_query else url_path

    # Create a hash of the unique string
    url_hash = hashlib.sha256(unique_string.encode("utf-8")).hexdigest()

    # Get the file extension (if any) from the URL path
    file_extension = os.path.splitext(parsed_url.path)[1]

    # Combine the hash with the file extension to form the filename
    filename = f"{url_hash}{file_extension}"

    return filename


# -------- Convenience helper --------


def normalize_basename(
    basename: str,
    *,
    max_len: int = BASENAME_MAXIMUM_LENGTH,
    allow_empty: bool = False,
) -> Tuple[str, bool]:
    """Normalizes a filename and alerts to whether it was changed.

    Returns (result, changed). If already valid, returns (basename, False).

        Args:
        basename: The basename to normalize.
        max_len: The maximum length of the basename (default: BASENAME_MAXIMUM_LENGTH).
        allow_empty: Whether to allow an empty basename (default: False).
    Returns:
        A tuple containing the normalized basename and a boolean indicating whether it was changed.
    else returns (repair_basename(basename), True).
    """
    if is_valid_basename(basename, max_len=max_len):
        return basename, False
    base = repair_basename(basename, max_len=max_len)
    if not base and not allow_empty:
        raise ValueError("Normalizing produced empty basename under current policy.")
    return base, True
