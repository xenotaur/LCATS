"""Caching layer for the Gutenberg corpus using gutenbergpy."""

import os
import pathlib
import sqlite3
import time

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Optional

from gutenbergpy import gutenbergcache as gc


# ------------ cache helpers ------------
# Whether to auto-create the cache if missing.
GUTENBERG_CACHE_AUTO_CREATE = True
GUTENBERG_CACHE_SKIP_MODE = False  # Whether to skip using the cache entirely.

# Allow CI (or users) to override cache location, defaulting to "cache" in the current directory.
# This is a directory, not a file; the actual cache DB is inside it.
_GUTENBERG_ROOT_STR = os.environ.get("LCATS_CACHE_DIR", "cache")
GUTENBERG_ROOT = pathlib.Path(_GUTENBERG_ROOT_STR)

# Defensive: if a file exists where the directory should be, fail clearly
if GUTENBERG_ROOT.exists() and not GUTENBERG_ROOT.is_dir():
    raise RuntimeError(
        f"Gutenberg cache root '{GUTENBERG_ROOT}' exists but is not a directory. "
        "Set LCATS_CACHE_DIR to a valid directory path."
    )

GUTENBERG_TEXTS = GUTENBERG_ROOT / "texts"
GUTENBERG_TEXTS.mkdir(parents=True, exist_ok=True)  # makes root too.
GUTENBERG_TMP = GUTENBERG_ROOT / "tmp"
GUTENBERG_TMP.mkdir(parents=True, exist_ok=True)


gc.GutenbergCacheSettings.set(
    CacheFilename=str(GUTENBERG_ROOT / "gutenbergindex.db"),
    # CacheUnpackDir=str(_GUTENBERG_TMP),  # Don't override, changes aren't respected.
    CacheArchiveName=str(GUTENBERG_ROOT / "rdf-files.tar.bz2"),
    TextFilesCacheFolder=str(GUTENBERG_TEXTS),
)


# Define a custom User-Agent to avoid 403 errors from Gutenberg servers.
USER_AGENT = "LCATS/1.0 (+https://example.com) Python-urllib"


# Common URL patterns to try for downloading raw text files.
URL_PATTERNS = [
    "https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
    # UTF-8 “no BOM”
    "https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt",
    # alternate UTF-8
    "https://www.gutenberg.org/files/{book_id}/{book_id}-8.txt",
    "https://www.gutenberg.org/files/{book_id}/{book_id}.txt",
    "https://www.gutenberg.org/files/{book_id}/pg{book_id}.txt",
    "https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt.utf8",
]


def gutenberg_cache_path() -> pathlib.Path:
    """Find the path to the local Gutenberg metadata cache (SQLite)."""
    return pathlib.Path(gc.GutenbergCacheSettings.CACHE_FILENAME)


def gutenberg_cache_ready(path: pathlib.Path) -> bool:
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


def ensure_gutenberg_cache():
    """Return cache handle; build only if explicitly allowed AND missing."""
    # Find the expected cache path.
    path = gutenberg_cache_path()

    # Call once up front; reuse this value in the if-guard
    ready = gutenberg_cache_ready(path)
    if ready:
        # Don't print anything in normal operation.
        # print(f"Checking local Gutenberg cache at {path}...")
        # print(" - Cache present and ready.")
        pass

    elif GUTENBERG_CACHE_AUTO_CREATE:
        print(f"Checking local Gutenberg cache at {path}...")
        print(" - Cache missing or stale; (re)creating it...")
        # If an empty/stale file exists, delete it so create() doesn’t early-exit.
        if path.exists() and path.stat().st_size == 0:
            path.unlink(missing_ok=True)

        # Create the cache from scratch, downloading/parsing as needed.
        # This may take a while, so go get a coffee or soda.
        gc.GutenbergCache.create(
            refresh=True,
            download=True,
            unpack=True,
            parse=True,
            cache=True,
            deleteTemp=False,
        )

        # Second call only when we actually ran create()
        ready = gutenberg_cache_ready(path)
        if not ready:
            raise RuntimeError(f"Gutenberg cache NOT ready at {path}")
        print(" - Cache created and ready.")

    # Only now open the cache
    return gc.GutenbergCache.get_cache()


def download_raw_text(book_id: int, url_patterns: Optional[list[str]] = None) -> bytes:
    """Download raw bytes for a Gutenberg text using several common URL patterns.

    Args:
        book_id: The Gutenberg book ID (integer).

    Returns: bytes of the text (not decoded).
    """
    # Prep the inputs for use
    book_id = int(book_id)
    url_patterns = url_patterns or URL_PATTERNS

    # Try each URL pattern in order until one works, tracking the last error.
    last_err = None
    for url_pattern in url_patterns:
        url = url_pattern.format(book_id=book_id)
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=30) as r:
                return r.read()
        except (HTTPError, URLError, TimeoutError) as e:
            last_err = e
            time.sleep(0.1)  # tiny backoff between patterns
            continue

    # All the patterns failed, return the last one.
    raise RuntimeError(f"Could not download book {book_id}: {last_err}")


class RefreshableMetadataCache:
    """Tiny facade returned by get_metadata_cache(), with a 'rebuild()' method."""

    def rebuild(self) -> None:
        """Rebuild / refresh the local metadata cache."""
        gc.GutenbergCache.create()

    def __repr__(self) -> str:
        return "<RefreshableMetadataCache (gutenbergpy-backed)>"


def get_metadata_cache() -> RefreshableMetadataCache:
    """Return a simple object with 'rebuild()' to refresh metadata."""
    return RefreshableMetadataCache()
