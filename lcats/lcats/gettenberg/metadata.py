"""Extract metadata from Gutenberg cache or text header."""

from typing import Any, Dict, Iterable, Set

from lcats.utils import values


def get_metadata_from_cache(cache: Any, field: str, book_id: int) -> Set[str]:
    """Extract metadata from the cache for a given field and book ID.

    Args:
        cache: The gutenbergpy cache object.
        field: The metadata field to retrieve (e.g. 'title', 'author', 'language', 'subject').
        book_id: The Gutenberg book ID (integer).
    Returns:
        Set of strings (may be empty if not found).
    Raises:
        ValueError: If the field is not recognized.
    """
    # Attempt to to retrieve the metadata from the cache.
    try:
        if field in ("title", "titles"):
            return titles_for(cache, book_id)
        if field in ("author", "authors"):
            return authors_for(cache, book_id)
        if field in ("alias", "aliases"):
            return aliases_for(cache, book_id)
        if field in ("language", "languages"):
            return languages_for(cache, book_id)
        if field in ("subject", "subjects"):
            return subjects_for(cache, book_id)

    except Exception as e:  # pylint: disable=broad-except
        # Cache not ready / schema mismatch / bad ID → fall back to header parse
        print("Error accessing cache for book ID: ", book_id)
        # reraise the error; don't fall through if we got a cache to use.
        raise e

    # Field not recognized, raise an error.
    raise ValueError(f"Unsupported metadata field: {field}")


def get_metadata_from_header(field: str, header: Iterable[str]) -> Set[str]:
    """Parse metadata from the header of a Gutenberg text for a given field.

    Args:
        field: The metadata field to retrieve (e.g. 'title', 'author', 'language', 'subject').
        header_lines: The header lines to search (as an iterable of strings).

    Returns:
        Set of strings (may be empty if not found).

    Raises:
        ValueError: If the field is not recognized.
    """
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
    # Look up the prefix for the requested field.
    want = prefixes.get(field)
    if want:
        want = want.lower()
        for line in header:
            if line.lower().startswith(want):
                vals.add(line.split(":", 1)[1].strip())
        return vals

    # Field not recognized, raise an error.
    raise ValueError(f"Unsupported metadata field: {field}")


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
    return values.strings_from_sql(rows)


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
    return values.strings_from_sql(rows)


def split_into_consecutive_chunks(arr):
    if not arr:
        return []

    chunks = []
    current_chunk = [arr[0]]

    for i in range(1, len(arr)):
        if arr[i] == arr[i - 1] - 1:  # Check for consecutive numbers
            current_chunk.append(arr[i])
        else:
            chunks.append(current_chunk)
            current_chunk = [arr[i]]

    chunks.append(current_chunk)  # Add the last chunk
    return chunks


def convert_to_name(cache, number):
    return cache.native_query(
        "Select * from authors where id=" + str(number)
    ).fetchall()[0][1]


def convert_to_names(cache, numbers):
    names = [convert_to_name(cache, number) for number in numbers]

    return names


def authors_split(cache, bid: int) -> Set[str]:
    """Return set of author strings for a given Gutenberg book ID."""
    rows = cache.native_query(
        f"""
        SELECT a.id AS v
        FROM authors a
        JOIN book_authors ba ON a.id = ba.authorid
        JOIN books b         ON ba.bookid = b.id
        WHERE b.gutenbergbookid = {int(bid)}
        """
    )

    number_list = [
        int(number_str) for number_str in list(values.strings_from_sql(rows))
    ]
    number_list.sort()
    number_list.reverse()
    number_chunks = split_into_consecutive_chunks(number_list)

    names = [convert_to_names(cache, number_chunk) for number_chunk in number_chunks]

    return names


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

    return values.strings_from_sql(rows)


def aliases_for(cache, bid: int) -> Set[str]:
    """Return set of alias strings for a given Gutenberg book ID."""
    rows = cache.native_query(
        f"""
        SELECT a.name AS v
        FROM aliases a
        JOIN book_aliases ba ON a.id = ba.authorid
        JOIN books b         ON ba.bookid = b.id
        WHERE b.gutenbergbookid = {int(bid)}
        """
    )

    return values.strings_from_sql(rows)


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
    return values.strings_from_sql(rows)
