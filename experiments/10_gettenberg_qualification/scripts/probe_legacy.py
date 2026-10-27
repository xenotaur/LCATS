"""Measure the historical gutenbergpy/wrapper query behavior.

Run from lcats/: python ../experiments/10_gettenberg_qualification/scripts/probe_legacy.py DATABASE
Requires the legacy dependency pinned by the recorded LCATS revision. Reads the
existing database through a read-only connection and prints JSON; never prepares
or downloads a cache. Only the acquisition factory is substituted so the actual
query implementation executes. This is an archival comparison, not product API.
"""

import argparse
import json
import pathlib
import sqlite3
from unittest import mock


def main(argv=None):
    """Run one explicit measurement; return only after its output is saved."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database")
    options = parser.parse_args(argv)
    # Keep import and --help usable after dependency removal. Actual historical
    # measurements require the recorded checkout; no compatibility shim is added.
    try:
        from gutenbergpy.caches import sqlitecache
        from lcats.gettenberg import api
        from lcats.gettenberg import cache
    except ImportError:
        parser.error(
            "historical probe requires its recorded LCATS checkout and gutenbergpy environment"
        )
    arguments = [options.database]

    database = pathlib.Path(arguments[0]).resolve()
    legacy = sqlitecache.SQLiteCache()
    legacy.connection = sqlite3.connect(
        database.as_uri() + "?mode=ro&immutable=1", uri=True
    )
    legacy.cursor = legacy.connection.cursor()
    legacy.connection.execute("PRAGMA query_only=ON")
    rows = legacy.query(languages=["en"])
    result = {
        "upstream_en_count": len(rows),
        "upstream_row_type": type(rows[0]).__name__,
        "upstream_row_example": rows[0],
        "factory_substitution": "Only cache acquisition factory replaced with real read-only SQLiteCache; actual query and wrapper implementations executed; no network.",
    }
    # Substitute only acquisition; exercise the real legacy query and wrapper.
    with mock.patch.object(cache, "ensure_gutenberg_cache", return_value=legacy):
        result["public_wrapper_en_count"] = len(api.get_etexts(languages="en"))
        try:
            api.get_matching_rows(languages="en", downloadtype=["text/plain"])
        except TypeError as error:
            result["mapping_probe_error"] = str(error)
            result["mapping_probe_scope"] = (
                "Diagnostic list-valued downloadtype bypasses separate string-iteration bug; not a supported public API call."
            )
    legacy.connection.close()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
