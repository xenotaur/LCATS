"""Normalized SQLite storage for one explicitly built catalog generation.

The caller owns transactions and enables foreign keys. Every position is
zero-based and scoped to its parent; original spelling and repeated values are
retained. Only contributor identities are shared, within a single ebook.
"""

import sqlite3
import zlib

from lcats.gettenberg import errors
from lcats.gettenberg import models

SCHEMA_VERSION = 1
APPLICATION_ID = 0x4C434754
PARSER_VERSION = "1"

_LITERAL_COLUMNS = (
    "value TEXT NOT NULL",
    "language TEXT",
    "datatype TEXT",
    "folded TEXT NOT NULL",
)
_EBOOK_FK = "FOREIGN KEY (ebook_id) REFERENCES ebooks(id)"
_AGENT_FK = (
    "FOREIGN KEY (ebook_id, agent_position) " "REFERENCES agents(ebook_id, position)"
)
_RESOURCE_FK = (
    "FOREIGN KEY (ebook_id, resource_position) "
    "REFERENCES resources(ebook_id, position)"
)

# Columns and constraints are kept together so creation and compatibility
# checks describe the same schema. Table identifiers are internal constants.
_TABLES = {
    "metadata": ("key TEXT PRIMARY KEY", "value TEXT NOT NULL"),
    "ebooks": ("id INTEGER PRIMARY KEY", "uri TEXT NOT NULL", "downloads INTEGER"),
    "sources": (
        "ebook_id INTEGER PRIMARY KEY",
        "source_name TEXT NOT NULL UNIQUE",
        "sha256 TEXT NOT NULL",
        "parser_version TEXT NOT NULL",
        "encoding TEXT NOT NULL",
        "raw_size INTEGER NOT NULL",
        "data BLOB NOT NULL",
        _EBOOK_FK,
    ),
    "titles": (
        "ebook_id INTEGER NOT NULL",
        "position INTEGER NOT NULL",
        "kind TEXT NOT NULL",
        *_LITERAL_COLUMNS,
        "PRIMARY KEY (ebook_id, position)",
        _EBOOK_FK,
    ),
    "agents": (
        "ebook_id INTEGER NOT NULL",
        "position INTEGER NOT NULL",
        "uri TEXT NOT NULL",
        "PRIMARY KEY (ebook_id, position)",
        "UNIQUE (ebook_id, uri)",
        _EBOOK_FK,
    ),
    "agent_literals": (
        "ebook_id INTEGER NOT NULL",
        "agent_position INTEGER NOT NULL",
        "kind TEXT NOT NULL",
        "position INTEGER NOT NULL",
        *_LITERAL_COLUMNS,
        "PRIMARY KEY (ebook_id, agent_position, kind, position)",
        _AGENT_FK,
    ),
    "agent_links": (
        "ebook_id INTEGER NOT NULL",
        "agent_position INTEGER NOT NULL",
        "kind TEXT NOT NULL",
        "position INTEGER NOT NULL",
        "uri TEXT NOT NULL",
        "PRIMARY KEY (ebook_id, agent_position, kind, position)",
        _AGENT_FK,
    ),
    "contributions": (
        "ebook_id INTEGER NOT NULL",
        "position INTEGER NOT NULL",
        "role_uri TEXT NOT NULL",
        "agent_position INTEGER NOT NULL",
        "PRIMARY KEY (ebook_id, position)",
        _AGENT_FK,
    ),
    "resources": (
        "ebook_id INTEGER NOT NULL",
        "position INTEGER NOT NULL",
        "uri TEXT NOT NULL",
        "PRIMARY KEY (ebook_id, position)",
        _EBOOK_FK,
    ),
    "resource_sizes": (
        "ebook_id INTEGER NOT NULL",
        "resource_position INTEGER NOT NULL",
        "position INTEGER NOT NULL",
        "value INTEGER NOT NULL",
        "PRIMARY KEY (ebook_id, resource_position, position)",
        _RESOURCE_FK,
    ),
    "resource_modified": (
        "ebook_id INTEGER NOT NULL",
        "resource_position INTEGER NOT NULL",
        "position INTEGER NOT NULL",
        *_LITERAL_COLUMNS,
        "PRIMARY KEY (ebook_id, resource_position, position)",
        _RESOURCE_FK,
    ),
    "resource_links": (
        "ebook_id INTEGER NOT NULL",
        "resource_position INTEGER NOT NULL",
        "kind TEXT NOT NULL",
        "position INTEGER NOT NULL",
        "uri TEXT NOT NULL",
        "PRIMARY KEY (ebook_id, resource_position, kind, position)",
        _RESOURCE_FK,
    ),
    "ebook_literals": (
        "ebook_id INTEGER NOT NULL",
        "kind TEXT NOT NULL",
        "position INTEGER NOT NULL",
        *_LITERAL_COLUMNS,
        "PRIMARY KEY (ebook_id, kind, position)",
        _EBOOK_FK,
    ),
    "ebook_links": (
        "ebook_id INTEGER NOT NULL",
        "kind TEXT NOT NULL",
        "position INTEGER NOT NULL",
        "uri TEXT NOT NULL",
        "PRIMARY KEY (ebook_id, kind, position)",
        _EBOOK_FK,
    ),
    "additional_metadata": (
        "ebook_id INTEGER NOT NULL",
        "position INTEGER NOT NULL",
        "predicate_uri TEXT NOT NULL",
        *_LITERAL_COLUMNS,
        "PRIMARY KEY (ebook_id, position)",
        _EBOOK_FK,
    ),
    "diagnostics": (
        "ebook_id INTEGER NOT NULL",
        "position INTEGER NOT NULL",
        "code TEXT NOT NULL",
        "path TEXT NOT NULL",
        "predicate_uri TEXT NOT NULL",
        "message TEXT NOT NULL",
        "PRIMARY KEY (ebook_id, position)",
        "FOREIGN KEY (ebook_id) REFERENCES sources(ebook_id)",
    ),
}

_TERM_TABLES = ("languages", "subjects", "shelves", "types", "formats")
for _table in _TERM_TABLES:
    _TABLES[_table] = (
        "ebook_id INTEGER NOT NULL",
        "owner INTEGER NOT NULL",
        "position INTEGER NOT NULL",
        "value TEXT NOT NULL",
        "language TEXT",
        "datatype TEXT",
        "uri TEXT",
        "node_id TEXT",
        "folded TEXT NOT NULL",
        "PRIMARY KEY (ebook_id, owner, position)",
        (
            "FOREIGN KEY (ebook_id, owner) REFERENCES resources(ebook_id, position)"
            if _table == "formats"
            else _EBOOK_FK
        ),
        *(() if _table == "formats" else ("CHECK (owner = 0)",)),
    )
    _TABLES[f"{_table}_schemes"] = (
        "ebook_id INTEGER NOT NULL",
        "owner INTEGER NOT NULL",
        "term_position INTEGER NOT NULL",
        "position INTEGER NOT NULL",
        "uri TEXT NOT NULL",
        "PRIMARY KEY (ebook_id, owner, term_position, position)",
        f"FOREIGN KEY (ebook_id, owner, term_position) "
        f"REFERENCES {_table}(ebook_id, owner, position)",
    )

# Composite primary keys cover parent joins. Lookup indexes have the ebook ID
# as their trailing column so exact filter queries can use covering indexes.
_INDEXES = {
    "titles_value": "titles(value, ebook_id)",
    "agent_literals_value": "agent_literals(kind, value, ebook_id)",
    "contributions_role": "contributions(role_uri, ebook_id)",
    "contributions_agent": "contributions(ebook_id, agent_position)",
}
for _table in _TERM_TABLES:
    _INDEXES[f"{_table}_value"] = f"{_table}(value, ebook_id)"


def create(conn: sqlite3.Connection) -> None:
    """Create schema version 1 without committing the caller's transaction.

    Args:
        conn: A connection to a new catalog with foreign keys enabled.
    """
    for table, definitions in _TABLES.items():
        conn.execute(f"CREATE TABLE {table} ({', '.join(definitions)})")
    for name, target in _INDEXES.items():
        conn.execute(f"CREATE INDEX {name} ON {target}")
    conn.execute(f"PRAGMA application_id = {APPLICATION_ID}")
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def validate_schema(conn: sqlite3.Connection) -> None:
    """Reject incompatible or incomplete catalog schema without changing it.

    Manifest contents and generation status are checked by the catalog reader.

    Args:
        conn: An open SQLite connection.

    Raises:
        errors.CatalogSchemaError: Identity, version, tables or columns differ.
    """
    try:
        if conn.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID:
            raise errors.CatalogSchemaError("not an LCATS Gutenberg catalog")
        if conn.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            raise errors.CatalogSchemaError("unsupported catalog schema version")
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        for table, definitions in _TABLES.items():
            if table not in tables:
                raise errors.CatalogSchemaError(f"missing catalog table: {table}")
            expected = [
                tuple(definition.split()[:2])
                for definition in definitions
                if not definition.startswith(("PRIMARY", "FOREIGN", "UNIQUE", "CHECK"))
            ]
            actual = [
                (row[1], row[2].upper())
                for row in conn.execute(f"PRAGMA table_info({table})")
            ]
            if actual != expected:
                raise errors.CatalogSchemaError(
                    f"incompatible catalog columns: {table}"
                )
    except sqlite3.DatabaseError as exc:
        raise errors.CatalogSchemaError("cannot read catalog schema") from exc


def _literal(value: models.Literal) -> tuple:
    return value.text, value.language, value.datatype, value.text.casefold()


def _insert_terms(conn, table, ebook_id, owner, terms):
    conn.executemany(
        f"INSERT INTO {table} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            (
                ebook_id,
                owner,
                position,
                term.value.text,
                term.value.language,
                term.value.datatype,
                term.uri,
                term.node_id,
                term.value.text.casefold(),
            )
            for position, term in enumerate(terms)
        ),
    )
    conn.executemany(
        f"INSERT INTO {table}_schemes VALUES (?, ?, ?, ?, ?)",
        (
            (ebook_id, owner, term_position, position, uri)
            for term_position, term in enumerate(terms)
            for position, uri in enumerate(term.schemes)
        ),
    )


def insert_record(conn: sqlite3.Connection, record: models.ParsedRecord) -> None:
    """Insert one parsed record, retaining all values and exact source bytes.

    No commits, replacements, or whole-record serialization are performed.
    Input is one record bounded by the ingestion/parser limits. The caller
    must roll back its transaction if insertion fails partway through.

    Args:
        conn: A catalog connection with foreign keys enabled.
        record: A record produced by the supported parser.

    Raises:
        ValueError: A repeated agent URI has inconsistent metadata.
        sqlite3.DatabaseError: An insertion or integrity constraint fails.
    """
    ebook = record.ebook
    ebook_id = ebook.gutenberg_id
    source = record.source
    agents = {}
    for contribution in ebook.contributors:
        agent = contribution.agent
        if agent.uri in agents:
            if agents[agent.uri][1] != agent:
                raise ValueError(f"conflicting agent metadata: {agent.uri}")
        else:
            agents[agent.uri] = (len(agents), agent)

    conn.execute(
        "INSERT INTO ebooks VALUES (?, ?, ?)", (ebook_id, ebook.uri, ebook.downloads)
    )
    conn.execute(
        "INSERT INTO sources VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            ebook_id,
            source.source_name,
            source.sha256,
            source.parser_version,
            "zlib",
            len(source.data),
            zlib.compress(source.data, level=1),
        ),
    )
    conn.executemany(
        "INSERT INTO titles VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            (ebook_id, position, title.kind, *_literal(title.value))
            for position, title in enumerate(ebook.titles)
        ),
    )
    for agent_position, agent in agents.values():
        conn.execute(
            "INSERT INTO agents VALUES (?, ?, ?)", (ebook_id, agent_position, agent.uri)
        )
        for kind in ("names", "aliases", "birth_dates", "death_dates"):
            conn.executemany(
                "INSERT INTO agent_literals VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    (ebook_id, agent_position, kind, position, *_literal(value))
                    for position, value in enumerate(getattr(agent, kind))
                ),
            )
        conn.executemany(
            "INSERT INTO agent_links VALUES (?, ?, ?, ?, ?)",
            (
                (ebook_id, agent_position, "webpages", position, uri)
                for position, uri in enumerate(agent.webpages)
            ),
        )
    conn.executemany(
        "INSERT INTO contributions VALUES (?, ?, ?, ?)",
        (
            (
                ebook_id,
                position,
                contribution.role_uri,
                agents[contribution.agent.uri][0],
            )
            for position, contribution in enumerate(ebook.contributors)
        ),
    )
    for table in _TERM_TABLES:
        if table != "formats":
            _insert_terms(conn, table, ebook_id, 0, getattr(ebook, table))
    for resource_position, resource in enumerate(ebook.resources):
        conn.execute(
            "INSERT INTO resources VALUES (?, ?, ?)",
            (ebook_id, resource_position, resource.uri),
        )
        _insert_terms(conn, "formats", ebook_id, resource_position, resource.formats)
        conn.executemany(
            "INSERT INTO resource_sizes VALUES (?, ?, ?, ?)",
            (
                (ebook_id, resource_position, position, value)
                for position, value in enumerate(resource.sizes)
            ),
        )
        conn.executemany(
            "INSERT INTO resource_modified VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                (ebook_id, resource_position, position, *_literal(value))
                for position, value in enumerate(resource.modified)
            ),
        )
        conn.executemany(
            "INSERT INTO resource_links VALUES (?, ?, ?, ?, ?)",
            (
                (ebook_id, resource_position, "is_format_of", position, uri)
                for position, uri in enumerate(resource.is_format_of)
            ),
        )
    for kind in ("publishers", "rights", "issued", "descriptions", "contents"):
        conn.executemany(
            "INSERT INTO ebook_literals VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                (ebook_id, kind, position, *_literal(value))
                for position, value in enumerate(getattr(ebook, kind))
            ),
        )
    conn.executemany(
        "INSERT INTO ebook_links VALUES (?, ?, ?, ?)",
        (
            (ebook_id, "licenses", position, uri)
            for position, uri in enumerate(ebook.licenses)
        ),
    )
    conn.executemany(
        "INSERT INTO additional_metadata VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            (ebook_id, position, item.predicate_uri, *_literal(item.value))
            for position, item in enumerate(ebook.additional_metadata)
        ),
    )
    conn.executemany(
        "INSERT INTO diagnostics VALUES (?, ?, ?, ?, ?, ?)",
        (
            (ebook_id, position, item.code, item.path, item.predicate_uri, item.message)
            for position, item in enumerate(record.diagnostics)
        ),
    )
