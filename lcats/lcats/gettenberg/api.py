"""
Compatibility wrapper: expose a minimal 'gutenberg' API using 'gutenbergpy' under the hood.

Supports the following imports we were using:
    from gutenberg.acquire import load_etext, get_metadata_cache
    from gutenberg.cleanup import strip_headers
    from gutenberg.query   import get_etexts, get_metadata

Notes:
- Text functions return BYTES (like gutenbergpy). Decode to str if you need text.
- get_etexts supports simple field filters (authors, titles, languages, subjects, bookshelves).
- get_metadata uses a pragmatic header-parse fallback (robust and schema-free).
"""

import sqlite3

from typing import Any, List, Mapping, Optional, Sequence, Set

from gutenbergpy import textget

from lcats.gettenberg import cache
from lcats.gettenberg import headers
from lcats.gettenberg import metadata
from lcats.utils import values


def load_etext(book_id: int) -> bytes:
    """Returns the Gutenberg text as BYTES using a local file cache.

    The downloader is intended to be robust and returns encoded text.

    Args:
        book_id: The Gutenberg book ID (integer).
    Returns: encoded bytes of the text.
    """
    book_id = int(book_id)
    fp = cache.GUTENBERG_TEXTS / f"{book_id}.txt"
    try:
        return fp.read_bytes()
    except FileNotFoundError:
        pass

    # Try gutenbergpy first; otherwise fall back to raw.
    try:
        # May return str or raise during decode.
        data = textget.get_text_by_id(book_id)
        if isinstance(data, str):  # If Gutenberg returns str, re-encode.
            data = data.encode("utf-8", errors="ignore")
    except Exception:  # pylint: disable=broad-except
        data = cache.download_raw_text(book_id)

    # Failure to write to cache signals a configuration error and should raise an error.
    fp.write_bytes(data)
    return data


def get_etexts(
    *,
    authors: Optional[Sequence[str] | str] = None,
    titles: Optional[Sequence[str] | str] = None,
    languages: Optional[Sequence[str] | str] = None,
    subjects: Optional[Sequence[str] | str] = None,
    bookshelves: Optional[Sequence[str] | str] = None,
    downloadtype: Optional[str] = None,
) -> Set[int]:
    """Return a set of Gutenberg IDs matching simple field filters.

    Example:
        get_etexts(authors="Mark Twain", languages="en")
        get_etexts(titles=["Moby Dick"], languages=["en"])

    Raises:
        Propagates errors from get_matching_rows() / extract_book_id().
    """
    rows = get_matching_rows(
        authors=authors,
        titles=titles,
        languages=languages,
        subjects=subjects,
        bookshelves=bookshelves,
        downloadtype=downloadtype,
    )
    return {extract_book_id(r) for r in rows}


def get_matching_rows(
    *,
    authors: Optional[Sequence[str] | str] = None,
    titles: Optional[Sequence[str] | str] = None,
    languages: Optional[Sequence[str] | str] = None,
    subjects: Optional[Sequence[str] | str] = None,
    bookshelves: Optional[Sequence[str] | str] = None,
    downloadtype: Optional[str] = None,
) -> List[Mapping[str, Any]]:
    """Return raw rows from gutenbergpy's cache.query() for the given filters.

    Raises:
        Any exception propagated by ensure_gutenberg_cache() or cache.query().
    """
    gut_cache = cache.ensure_gutenberg_cache()
    rows = gut_cache.query(
        authors=values.strings_as_list(authors),
        titles=values.strings_as_list(titles),
        languages=values.strings_as_list(languages),
        subjects=values.strings_as_list(subjects),
        bookshelves=values.strings_as_list(bookshelves),
        downloadtype=downloadtype or "text",
    )
    # We expect dict-like rows; coerce to list to make the return stable/testable.
    if not isinstance(rows, list):
        rows = list(rows)
    # Validate shape early so failures are clear and unit-testable.
    for i, r in enumerate(rows):
        if not isinstance(r, Mapping):
            raise TypeError(
                f"cache.query returned a non-mapping row at index {i}: {type(r).__name__}"
            )
    return rows  # type: ignore[return-value]


def extract_book_id(row: Mapping[str, Any]) -> int:
    """Extract the Gutenberg book ID (gutenbergbookid) from a query row.

    Expects the current gutenbergpy schema. Raises if missing/invalid.

    Raises:
        KeyError: if 'gutenbergbookid' key is missing.
        ValueError: if the value cannot be parsed as int.
        TypeError: if the value type is incompatible.
    """
    if "gutenbergbookid" not in row:
        raise KeyError("Row missing required key 'gutenbergbookid'")
    value = row["gutenbergbookid"]
    try:
        return int(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid 'gutenbergbookid' value: {value!r}") from e


def get_metadata(
    field: str, book_id: int, skip_cache: bool = cache.GUTENBERG_CACHE_SKIP_MODE
) -> Set[str]:
    """Rough equivalent of gutenberg.query.get_metadata(field, book_id).

    Tries the gutenbergpy cache first (SQLite backend) via native_query(sql),
    then falls back to parsing the text header. Supported header fields:
    'title', 'author', 'language', 'subject'.

    If GUTENBERG_CACHE_SKIP_MODE is True, allow a hard "offline" mode that skips cache entirely.

    Args:
        field: The metadata field to retrieve (e.g. 'title', 'author', 'language', 'subject').
        book_id: The Gutenberg book ID (integer).
        use_cache: Whether to use the local cache (default: True).
            If False, always falls back to header parse.
    Returns:
        Set of strings (may be empty if not found).
    """
    # Try to get a cache handle if allowed. If not allowed,
    # the code below will fall back to header-parse.
    gut_cache = None
    if skip_cache:
        print(" - get_metadata: skip_cache is True, falling back to header parse.")
    else:
        try:
            gut_cache = cache.ensure_gutenberg_cache()
        except (sqlite3.Error, RuntimeError, OSError) as e:
            gut_cache = None  # fall through to header parse
            print("Error accessing cache for book ID: ", book_id)
            raise e

    # Normalize the field name for matching.
    field = field.lower().strip()
    if gut_cache:
        return metadata.get_metadata_from_cache(gut_cache, field, book_id)

    # No cache, fall back to header parse.
    print(
        f" - get_metadata: falling back to header parse for field '{field}' and book ID {book_id}"
    )
    text = load_etext(int(book_id))
    header = headers.get_text_header_lines(text) or ()
    return metadata.get_metadata_from_header(field, header)
