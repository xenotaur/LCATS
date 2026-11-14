"""
registry.py

Maintain a persistent registry of stories gathered by LCATS.

A story is uniquely identified by:
    1. Its normalized filename
    2. The last names of its authors

Duplicate handling:
    ignore  - Accept duplicates silently.
    discard - Reject duplicates.
    warn    - Print a warning but accept duplicates.

The registry is stored in a SQLite database.

The registry can also be exported as a human-readable text file.
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

from lcats.utils import env


DEFAULT_REGISTRY_DIR = env.cache_root() / "registry"
DEFAULT_REGISTRY = DEFAULT_REGISTRY_DIR / "lcats_registry.db"
DEFAULT_REGISTRY_TSV = DEFAULT_REGISTRY_DIR / "lcats_registry.tsv"


def _connect(registry=DEFAULT_REGISTRY):
    """
    Open the registry database, creating it if necessary.
    """

    registry_path = Path(registry)
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(registry_path)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stories (
            filename TEXT NOT NULL,
            authors TEXT NOT NULL,
            source TEXT,
            date_added TEXT,
            PRIMARY KEY (filename, authors)
        )
    """
    )

    conn.commit()

    return conn


def _normalize_authors(authors):
    """
    Convert author last names into a standardized representation.

    Authors may be supplied as:
        "Asimov"
        ["Asimov"]
        ["Asimov", "Silverberg"]

    Author order and capitalization are ignored.
    """

    if isinstance(authors, str):
        authors = [authors]

    normalized = sorted(
        set(str(author).strip().casefold() for author in authors if str(author).strip())
    )

    return json.dumps(normalized)


def _normalize_filename(filename):
    """
    Standardize filename for comparison.

    Removes directory paths and ignores capitalization.
    """

    return os.path.basename(os.fspath(filename)).strip().casefold()


def check_story(filename, authors, registry=DEFAULT_REGISTRY):
    """
    Return True if the story is already in the registry.

    Parameters
    ----------
    filename : str
        Normalized story filename.

    authors : str or list
        Author last names.

    registry : str
        SQLite registry database filename.

    Returns
    -------
    bool
        True if the story exists, False otherwise.
    """

    filename = _normalize_filename(filename)
    authors = _normalize_authors(authors)

    with _connect(registry) as conn:

        result = conn.execute(
            """
            SELECT 1
            FROM stories
            WHERE filename = ? AND authors = ?
        """,
            (filename, authors),
        ).fetchone()

    return result is not None


def add_story(filename, authors, source=None, registry=DEFAULT_REGISTRY):
    """
    Add a story to the registry.

    Parameters
    ----------
    filename : str
        Normalized story filename.

    authors : str or list
        Author last names.

    source : str, optional
        Name of the gathering function or source.

    registry : str
        SQLite registry database filename.

    Returns
    -------
    bool
        True if newly added.
        False if already present.
    """

    filename = _normalize_filename(filename)
    authors = _normalize_authors(authors)

    with _connect(registry) as conn:

        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO stories
            (filename, authors, source, date_added)
            VALUES (?, ?, ?, ?)
        """,
            (filename, authors, source, datetime.now().isoformat()),
        )

        return cursor.rowcount == 1


def check_and_add(
    filename, authors, mode="warn", source=None, registry=DEFAULT_REGISTRY
):
    """
    Check whether a story has already been encountered.

    If the story has not been encountered, it is added
    to the registry.

    If the story already exists, the specified duplicate
    handling policy is applied.

    Parameters
    ----------
    filename : str
        Normalized story filename.

    authors : str or list
        Author last names.

    mode : str
        'ignore'  - Accept duplicates silently.
        'discard' - Reject duplicates.
        'warn'    - Print warning and accept duplicates.

    source : str, optional
        Name of the gathering function or source.

    registry : str
        SQLite registry database filename.

    Returns
    -------
    bool
        True  - Story should be accepted.
        False - Story should be discarded.
    """

    if mode not in ("ignore", "discard", "warn"):
        raise ValueError("mode must be 'ignore', 'discard', or 'warn'")

    filename_normalized = _normalize_filename(filename)
    authors_normalized = _normalize_authors(authors)

    with _connect(registry) as conn:

        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO stories
            (filename, authors, source, date_added)
            VALUES (?, ?, ?, ?)
        """,
            (
                filename_normalized,
                authors_normalized,
                source,
                datetime.now().isoformat(),
            ),
        )

        # New story successfully inserted.

        if cursor.rowcount == 1:
            return True

        # Duplicate detected.

        if mode == "discard":
            return False

        if mode == "warn":

            previous = conn.execute(
                """
                SELECT source
                FROM stories
                WHERE filename = ? AND authors = ?
            """,
                (filename_normalized, authors_normalized),
            ).fetchone()

            previous_source = previous[0] if previous else None

            print(f"WARNING: Duplicate story detected: " f"{filename} by {authors}")

            if previous_source:
                print(f"    Previously gathered from: " f"{previous_source}")

            if source:
                print(f"    Current source: {source}")

        return True


def export_registry(
    output_file=DEFAULT_REGISTRY_TSV,
    registry=DEFAULT_REGISTRY,
    include_source=False,
    format="tsv",
):
    """
    Export the registry database to a human-readable text file.

    Parameters
    ----------
    output_file : str
        Filename for the exported registry.

    registry : str
        SQLite registry database filename.

    include_source : bool
        Whether to include the original gathering source.

    format : str
        'tsv'  - Tab-separated columns (default).
        'text' - Labeled, human-readable entries.

    Returns
    -------
    int
        Number of stories exported.
    """

    if format not in ("tsv", "text"):
        raise ValueError("format must be 'tsv' or 'text'")

    with _connect(registry) as conn:

        stories = conn.execute(
            """
            SELECT filename, authors, source
            FROM stories
            ORDER BY filename, authors
        """
        ).fetchall()

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as output:

        if format == "tsv":

            columns = ["Filename", "Authors"]

            if include_source:
                columns.append("Source")

            output.write("\t".join(columns) + "\n")

            for filename, authors_json, source in stories:

                authors = ", ".join(json.loads(authors_json))

                row = [filename, authors]

                if include_source:
                    row.append(source or "")

                output.write("\t".join(row) + "\n")

        else:

            for filename, authors_json, source in stories:

                authors = ", ".join(json.loads(authors_json))

                output.write(f"Filename: {filename}\n")

                output.write(f"Authors:  {authors}\n")

                if include_source:
                    output.write(f"Source:   {source or ''}\n")

                output.write("\n")

    return len(stories)


def clear_registry(registry=DEFAULT_REGISTRY):
    """
    Remove all entries from the registry.

    The SQLite database and table remain intact.
    """

    with _connect(registry) as conn:

        conn.execute(
            """
            DELETE FROM stories
        """
        )


def registry_count(registry=DEFAULT_REGISTRY):
    """
    Return the number of unique stories in the registry.
    """

    with _connect(registry) as conn:

        result = conn.execute(
            """
            SELECT COUNT(*)
            FROM stories
        """
        ).fetchone()

    return result[0]
