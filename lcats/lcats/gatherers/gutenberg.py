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

import os
import pathlib
import sqlite3
import time

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any, Dict, Iterable, Mapping, Optional, Set, Union

from gutenbergpy import textget
from gutenbergpy import gutenbergcache as gc


# ------------ cache helpers ------------
# Automatic cache creation can be controlled by the environment; on by default.
_AUTO_CREATE = os.environ.get("GUTENBERGPY_AUTO_CREATE", "1") != "0"


_GUTENBERG_ROOT = pathlib.Path("cache")
_GUTENBERG_TEXTS = _GUTENBERG_ROOT / "texts"
_GUTENBERG_TEXTS.mkdir(parents=True, exist_ok=True)  # makes root too.
_GUTENBERG_TMP = _GUTENBERG_ROOT / "tmp"
_GUTENBERG_TMP.mkdir(parents=True, exist_ok=True)


gc.GutenbergCacheSettings.set(
    CacheFilename=str(_GUTENBERG_ROOT / "gutenbergindex.db"),
    # CacheUnpackDir=str(_GUTENBERG_TMP),  # Don't override, changes aren't respected.
    CacheArchiveName=str(_GUTENBERG_ROOT / "rdf-files.tar.bz2"),
    TextFilesCacheFolder=str(_GUTENBERG_TEXTS))


# Define a custom User-Agent to avoid 403 errors from Gutenberg servers.
_USER_AGENT = os.environ.get(
    "LCATS_GUTENBERG_UA",
    "LCATS/1.0 (+https://example.com) Python-urllib"
)


# Common URL patterns to try for downloading raw text files.
_URL_PATTERNS = [
    "https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
    # UTF-8 “no BOM”
    "https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt",
    # alternate UTF-8
    "https://www.gutenberg.org/files/{book_id}/{book_id}-8.txt",
    "https://www.gutenberg.org/files/{book_id}/{book_id}.txt",
    "https://www.gutenberg.org/files/{book_id}/pg{book_id}.txt",
    "https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt.utf8",
]


def _find_gutenberg_cache() -> pathlib.Path:
    """Find the path to the local Gutenberg metadata cache (SQLite)."""
    return pathlib.Path(gc.GutenbergCacheSettings.CACHE_FILENAME)


def _gutenberg_cache_ready(path: pathlib.Path) -> bool:
    """True if DB has expected tables. Open read-only so we never create a new file."""
    if not path.is_file() or path.stat().st_size == 0:
        # Returns False if file missing or empty without accidentally creating it.
        return False
    try:
        # File is present; open read-only to avoid mucking with the database.
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as con:
            # must have books table
            has_books = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='books'"
            ).fetchone()
            # subjects may be in 'subjects' or via a join table
            has_subjects = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table'"
                " AND name IN ('subjects','book_subjects')"
            ).fetchone()
            return bool(has_books) and bool(has_subjects)
    except sqlite3.Error:
        return False


def _ensure_gutenberg_cache():
    """Return cache handle; build only if explicitly allowed AND missing."""
    path = _find_gutenberg_cache()

    # If someone already opened the DB earlier, we might have a zero-byte file.
    if _AUTO_CREATE and not _gutenberg_cache_ready(path):
        # If an empty/stale file exists, delete it so create() doesn’t early-exit.
        if path.exists() and path.stat().st_size == 0:
            path.unlink(missing_ok=True)

        print("Gutenberg local cache missing / stale, (re)creating it...")
        gc.GutenbergCache.create(
            refresh=True,
            download=True,
            unpack=True,
            parse=True,
            cache=True,
            deleteTemp=True,
        )
        print(" - Checking for cache readiness...")

        # After create, verify schema; raise if still not ready to avoid silent failures
        if not _gutenberg_cache_ready(path):
            raise RuntimeError(f"Gutenberg cache NOT ready at {path}")
        print(" - Cache ready.")

    # Only now open the cache
    return gc.GutenbergCache.get_cache()


def _as_list(x: Optional[Union[str, Iterable[str]]]) -> Optional[list]:
    """Convert a string or iterable of strings to a list of strings, or None."""
    if x is None:
        return None
    if isinstance(x, (list, tuple, set)):
        return list(x)
    return [str(x)]



def _download_raw_text(book_id: int, url_patterns: Optional[list[str]] = None) -> bytes:
    """Download raw bytes for a Gutenberg text using several common URL patterns.

    Args:
        book_id: The Gutenberg book ID (integer).

    Returns: bytes of the text (not decoded).
    """
    # Prep the inputs for use
    book_id = int(book_id)
    url_patterns = url_patterns or _URL_PATTERNS

    # Try each URL pattern in order until one works, tracking the last error.
    last_err = None
    for url_pattern in url_patterns:
        url = url_pattern.format(book_id=book_id)
        try:
            req = Request(url, headers={"User-Agent": _USER_AGENT})
            with urlopen(req, timeout=30) as r:
                return r.read()
        except (HTTPError, URLError, TimeoutError) as e:
            last_err = e
            time.sleep(0.1)  # tiny backoff between patterns
            continue

    # All the patterns failed, return the last one.
    raise RuntimeError(f"Could not download book {book_id}: {last_err}")


def load_etext(book_id: int) -> bytes:
    """Returns the Gutenberg text as BYTES using a local file cache.

    The downloader is intended to be robust and returns encoded text.

    Args:
        book_id: The Gutenberg book ID (integer).
    Returns: encoded bytes of the text.
    """
    book_id = int(book_id)
    fp = _GUTENBERG_TEXTS / f"{book_id}.txt"
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
        data = _download_raw_text(book_id)

    # Failure to write to cache signals a configuration error and should raise an error.
    fp.write_bytes(data)
    return data


class _RefreshableMetadataCache:
    """Tiny facade returned by get_metadata_cache(), with a 'rebuild()' method."""

    def rebuild(self) -> None:
        """Rebuild / refresh the local metadata cache."""
        gc.GutenbergCache.create()

    def __repr__(self) -> str:
        return "<RefreshableMetadataCache (gutenbergpy-backed)>"


def get_metadata_cache() -> _RefreshableMetadataCache:
    """Return a simple object with 'rebuild()' to refresh metadata."""
    return _RefreshableMetadataCache()


def strip_headers(text: Union[bytes, str]) -> bytes:
    """    Remove Gutenberg headers/footers and return bytes of the content.

    Accepts either bytes or str (str is encoded as UTF-8 best-effort).

    Args:
        text: The text to process (either bytes or str).
    Returns: Bytes of the content.
    """
    if isinstance(text, str):
        text = text.encode("utf-8", errors="ignore")
    return textget.strip_headers(text)



def get_etexts(*, authors=None, titles=None, languages=None,
               subjects=None, bookshelves=None, downloadtype: Optional[str] = None) -> Set[int]:
    """Returns a set of Gutenberg IDs matching simple field filters.

    Example:
        get_etexts(authors="Mark Twain", languages="en")
        get_etexts(titles=["Moby Dick"], languages=["en"])

    Args:
        authors: Optional string or list of strings to match author names.
        titles: Optional string or list of strings to match title names.
        languages: Optional string or list of strings to match language codes (e.g. "en").
        subjects: Optional string or list of strings to match subject names.
        bookshelves: Optional string or list of strings to match bookshelf names.
        downloadtype: Optional string to specify download type (e.g. "text", "html", etc.).
    Returns: Set of integer Gutenberg book IDs.
    """
    cache = _ensure_gutenberg_cache()
    rows = cache.query(
        authors=_as_list(authors),
        titles=_as_list(titles),
        languages=_as_list(languages),
        subjects=_as_list(subjects),
        bookshelves=_as_list(bookshelves),
        downloadtype=downloadtype or "text"
    )
    ids = set()
    for r in rows:
        # gutenbergpy rows typically expose 'gutenberg_book_id'
        gid = r.get("gutenberg_book_id") or r.get("book_id") or r.get("id")
        if gid is not None:
            try:
                ids.add(int(gid))
            except Exception:  # pylint: disable=broad-except
                pass
    return ids


def _header_lines(book_id: int) -> Iterable[str]:
    """Yield non-blank lines from the header of a Gutenberg text (before '*** START')."""
    raw = load_etext(int(book_id))            # <— was textget.get_text_by_id
    pre, _, _ = raw.partition(b"*** START")
    for line in pre.splitlines():
        s = line.strip().decode("utf-8", errors="ignore")
        if s:
            yield s


def _vals(rows: Iterable[Mapping[str, Any] | tuple]) -> Set[str]:
    """Normalize sqlite rows (tuple or dict) to a set of string values."""
    out: Set[str] = set()
    for r in rows:
        if isinstance(r, (tuple, list)):
            if r and r[0] is not None:
                out.add(str(r[0]))
        else:
            v = r.get("v")
            if v is not None:
                out.add(str(v))
    return out

def titles_for(cache, bid: int) -> Set[str]:
    """Return set of title strings for a given Gutenberg book ID."""
    rows = cache.native_query(
        f"""
        SELECT t.name AS v
        FROM titles t
        JOIN books b ON t.bookid = b.id
        WHERE b.gutenbergbookid = {int(bid)}
        """
    )
    return _vals(rows)

def languages_for(cache, bid: int) -> Set[str]:
    """Return set of language strings for a given Gutenberg book ID."""
    rows = cache.native_query(
        f"""
        SELECT l.name AS v
        FROM languages l
        JOIN books b ON l.id = b.languageid
        WHERE b.gutenbergbookid = {int(bid)}
        """
    )
    return _vals(rows)

def authors_for(cache, bid: int) -> Set[str]:
    """Return set of author strings for a given Gutenberg book ID."""
    rows = cache.native_query(
        f"""
        SELECT a.name AS v
        FROM authors a
        JOIN book_authors ba ON a.id = ba.authorid
        JOIN books b         ON ba.bookid = b.id
        WHERE b.gutenbergbookid = {int(bid)}
        """
    )
    return _vals(rows)

def subjects_for(cache, bid: int) -> Set[str]:
    """Return set of subject strings for a given Gutenberg book ID."""
    rows = cache.native_query(
        f"""
        SELECT s.name AS v
        FROM subjects s
        JOIN book_subjects bs ON s.id = bs.subjectid
        JOIN books b          ON bs.bookid = b.id
        WHERE b.gutenbergbookid = {int(bid)}
        """
    )
    return _vals(rows)


def get_metadata(field: str, book_id: int) -> Set[str]:
    """Rough equivalent of gutenberg.query.get_metadata(field, book_id).

    Tries the gutenbergpy cache first (SQLite backend) via native_query(sql),
    then falls back to parsing the text header. Supported header fields:
    'title', 'author', 'language', 'subject'.

    Args:
        field: The metadata field to retrieve (e.g. 'title', 'author', 'language', 'subject').
        book_id: The Gutenberg book ID (integer).
    Returns:
        Set of strings (may be empty if not found).
    """
    field = field.lower().strip()

    # Allow a hard "offline" mode that skips cache entirely.
    use_cache = os.environ.get("GUTENBERGPY_OFFLINE") != "1"

    cache = None
    if use_cache:
        try:
            cache = _ensure_gutenberg_cache()
        except (sqlite3.Error, RuntimeError, OSError) as e:
            cache = None  # fall through to header parse
            print("Error accessing cache for book ID: ", book_id)
            raise e

    if cache:
        try:
            bid = int(book_id)  # ensures a safe numeric value before inlining
            if field in ("title", "titles"):
                return titles_for(cache, bid)
            if field in ("author", "authors"):
                return authors_for(cache, bid)
            if field in ("language", "languages"):
                return languages_for(cache, bid)
            if field in ("subject", "subjects"):
                return subjects_for(cache, bid)

            # Field not recognized, raise an error.
            raise ValueError(f"Unsupported metadata field: {field}")

        except Exception as e:  # pylint: disable=broad-except
            # Cache not ready / schema mismatch / bad ID → fall back to header parse
            print("Error accessing cache for book ID: ", book_id)
            raise e  # reraise the error; don't fall through if we got a cache to use.

    # Header-parse fallback if we have no cache
    return _parse_header_metadata(field, book_id)


def _parse_header_metadata(field: str, book_id: int) -> Set[str]:
    """Parse metadata from the header of a Gutenberg text for a given field."""
    vals: Set[str] = set()
    prefixes: Dict[str, str] = {
        "title": "title:",
        "author": "author:",
        "language": "language:",
        "subject": "subject:",
        "subjects": "subject:",
        "authors": "author:",
        "titles": "title:",
        "languages": "language:",
    }
    want = prefixes.get(field)
    if want:
        want = want.lower()
        # _header_lines() should already be robust; if it returns None, iterate over empty tuple.
        for line in _header_lines(book_id) or ():
            if line.lower().startswith(want):
                vals.add(line.split(":", 1)[1].strip())
    return vals
