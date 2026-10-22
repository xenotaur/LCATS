"""Compare normalized index multiplicities with a completed snapshot XML inventory.

From lcats/: python qualify_index_counts.py SNAPSHOT_JSON NEW_DATABASE LEGACY_DATABASE NEW_JSON
Read-only SQLite access, no network/writes except new JSON. Uses explicit known
schema queries only. Raw-source public get() reparses RDF, so that audit alone
cannot establish normalized-index fidelity. These aggregate checks complement
semantic query fixtures; they do not prove every indexed value individually.
"""

import argparse
import hashlib
import json
import pathlib
import sqlite3
import time

DC = "{http://purl.org/dc/terms/}"
PG = "{http://www.gutenberg.org/2009/pgterms/}"

# Each audited mapping has matching multiplicity in this pinned XML profile.
CHECKS = {
    PG + "ebook": "SELECT COUNT(*) FROM ebooks",
    DC + "title": "SELECT COUNT(*) FROM titles WHERE kind='primary'",
    DC + "alternative": "SELECT COUNT(*) FROM titles WHERE kind='alternative'",
    DC + "language": "SELECT COUNT(*) FROM languages",
    DC + "subject": "SELECT COUNT(*) FROM subjects",
    PG + "bookshelf": "SELECT COUNT(*) FROM shelves",
    DC + "type": "SELECT COUNT(*) FROM types",
    PG + "file": "SELECT COUNT(*) FROM resources",
    DC + "format": "SELECT COUNT(*) FROM formats",
    DC + "extent": "SELECT COUNT(*) FROM resource_sizes",
    DC + "modified": "SELECT COUNT(*) FROM resource_modified",
    DC + "isFormatOf": "SELECT COUNT(*) FROM resource_links WHERE kind='is_format_of'",
    PG + "agent": "SELECT COUNT(*) FROM agents",
    PG + "name": "SELECT COUNT(*) FROM agent_literals WHERE kind='names'",
    PG + "alias": "SELECT COUNT(*) FROM agent_literals WHERE kind='aliases'",
    PG + "birthdate": "SELECT COUNT(*) FROM agent_literals WHERE kind='birth_dates'",
    PG + "deathdate": "SELECT COUNT(*) FROM agent_literals WHERE kind='death_dates'",
    PG + "webpage": "SELECT COUNT(*) FROM agent_links WHERE kind='webpages'",
    DC + "publisher": "SELECT COUNT(*) FROM ebook_literals WHERE kind='publishers'",
    DC + "rights": "SELECT COUNT(*) FROM ebook_literals WHERE kind='rights'",
    DC + "issued": "SELECT COUNT(*) FROM ebook_literals WHERE kind='issued'",
    DC + "tableOfContents": "SELECT COUNT(*) FROM ebook_literals WHERE kind='contents'",
    DC + "license": "SELECT COUNT(*) FROM ebook_links WHERE kind='licenses'",
}


def file_digest(path):
    """Hash a database without retaining multi-gigabyte contents in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def main(argv=None):
    """Save all matching/mismatching counts, returning nonzero on mismatch."""
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("snapshot", "database", "legacy_database", "output"):
        ap.add_argument(name, type=lambda value: pathlib.Path(value).resolve())
    args = ap.parse_args(argv)
    if args.output.exists():
        ap.error("output exists")
    raw = args.snapshot.read_bytes()
    snapshot = json.loads(raw)
    if not snapshot["qualified"]:
        ap.error("snapshot audit did not qualify")
    comparisons = []
    with (
        sqlite3.connect(args.database.as_uri() + "?mode=ro", uri=True) as new,
        sqlite3.connect(args.legacy_database.as_uri() + "?mode=ro", uri=True) as old,
    ):
        identity = json.loads(
            new.execute("SELECT value FROM metadata WHERE key='report'").fetchone()[0]
        )
        if identity["archive_sha256"] != snapshot["archive_sha256"]:
            raise ValueError("database/snapshot source identity mismatch")
        for element, sql in CHECKS.items():
            comparisons.append(
                {
                    "element": element,
                    "xml": snapshot["elements"][element],
                    "index": new.execute(sql).fetchone()[0],
                    "sql": sql,
                }
            )
        for element, count in snapshot["elements"].items():
            if element.startswith(PG + "marc"):
                value = new.execute(
                    "SELECT COUNT(*) FROM additional_metadata WHERE predicate_uri=?",
                    (element.replace("{", "").replace("}", ""),),
                ).fetchone()[0]
                comparisons.append({"element": element, "xml": count, "index": value})
        old_sql = "SELECT books.gutenbergbookid FROM books JOIN languages ON books.languageid=languages.id WHERE languages.name='en' ORDER BY books.gutenbergbookid"
        times = []
        for _ in range(3):
            start = time.monotonic()
            old_ids = [r[0] for r in old.execute(old_sql)]
            times.append(time.monotonic() - start)
        new_ids = {
            r[0]
            for r in new.execute(
                "SELECT DISTINCT ebook_id FROM languages WHERE value='en'"
            )
        }
        extra = sorted(new_ids - set(old_ids))
        missing = sorted(set(old_ids) - new_ids)
        languages = {
            str(book): new.execute(
                "SELECT value FROM languages WHERE ebook_id=? ORDER BY position",
                (book,),
            ).fetchall()
            for book in extra
        }
    result = {
        "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
        "database_sha256": file_digest(args.database),
        "legacy_database_sha256": file_digest(args.legacy_database),
        "qualified": all(row["xml"] == row["index"] for row in comparisons)
        and not missing,
        "scope": __doc__,
        "comparisons": comparisons,
        "english": {
            "legacy_count": len(old_ids),
            "new_count": len(new_ids),
            "legacy_query_seconds": times,
            "legacy_query": old_sql,
            "new_only": extra,
            "old_only": missing,
            "new_only_languages_in_source_order": languages,
        },
    }
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    return 0 if result["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
