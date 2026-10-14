"""Explicit, read-only queries over a complete LCATS-owned local catalog."""

import copy
import dataclasses
import hashlib
import json
import pathlib
import sqlite3
import sys
import zlib
from collections import abc

from lcats.gettenberg import _store
from lcats.gettenberg import errors
from lcats.gettenberg import models
from lcats.gettenberg import rdf

MAX_PAGE_SIZE = 1000
MAX_FILTER_VALUES = 100


def _integer(value, name, *, minimum=1, maximum=2**63 - 1):
    if type(value) is not int or not minimum <= value <= maximum:
        raise errors.CatalogInputError(
            f"{name} must be an integer in [{minimum}, {maximum}]"
        )
    return value


@dataclasses.dataclass(frozen=True, slots=True)
class Filters:
    """AND across dimensions, OR within each tuple; empty tuples do not filter.

    Authors match contributor names or aliases. Exact matching preserves case;
    text search uses Unicode casefolded literal substrings, never SQL patterns.
    IDs always use integer equality. At most 100 values per dimension.
    """

    ids: tuple[int, ...] = ()
    titles: tuple[str, ...] = ()
    authors: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    subjects: tuple[str, ...] = ()
    shelves: tuple[str, ...] = ()
    types: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()
    formats: tuple[str, ...] = ()

    def __post_init__(self):
        for field in dataclasses.fields(self):
            values = getattr(self, field.name)
            if not isinstance(values, tuple) or len(values) > MAX_FILTER_VALUES:
                raise errors.CatalogInputError(
                    f"{field.name} must be a tuple of at most {MAX_FILTER_VALUES} values"
                )
            for value in values:
                if field.name == "ids":
                    _integer(value, "ID")
                elif not isinstance(value, str) or not value or len(value) > 4096:
                    raise errors.CatalogInputError(
                        f"{field.name} values must be nonempty strings of at most 4096 characters"
                    )
                elif field.name != "ids":
                    try:
                        value.encode("utf-8")
                    except UnicodeEncodeError as exc:
                        raise errors.CatalogInputError(
                            "filter text must be valid Unicode scalar values"
                        ) from exc


def _where(filters, text):
    if filters is None:
        filters = Filters()
    if not isinstance(filters, Filters):
        raise errors.CatalogInputError("filters must be a Filters instance")
    clauses, parameters = [], []
    for field in dataclasses.fields(filters):
        values = getattr(filters, field.name)
        if not values:
            continue
        name = field.name
        if name == "ids":
            clauses.append("e.id IN (" + ",".join("?" for _ in values) + ")")
            parameters.extend(values)
            continue
        if name == "authors":
            table = "agent_literals"
            extra = " AND q.kind IN ('names', 'aliases')"
        elif name == "roles":
            table, extra = "contributions", ""
        else:
            table, extra = name, ""
        column = "role_uri" if name == "roles" else "value"
        if text:
            # role URIs are ASCII by convention but may contain Unicode.
            column = "lcats_casefold(q.role_uri)" if name == "roles" else "q.folded"
            comparison = f"instr({column}, ?) > 0"
            parameters.extend(value.casefold() for value in values)
        else:
            comparison = f"q.{column} = ? COLLATE BINARY"
            parameters.extend(values)
        choices = " OR ".join(comparison for _ in values)
        clauses.append(
            f"EXISTS (SELECT 1 FROM {table} q WHERE q.ebook_id=e.id{extra} AND ({choices}))"
        )
    return " AND ".join(clauses) or "1", parameters


class Catalog:
    """A context-managed read-only connection to an explicitly named catalog.

    Args:
        path: Existing complete candidate SQLite file; never an implicit cache.
        max_record_bytes: Positive source size limit before fetching RDF blobs.

    Raises:
        errors.CatalogMissingError: The file does not exist.
        errors.CatalogSchemaError: Schema/parser/evidence is incompatible.
        errors.CatalogIncompleteError: Ingestion did not finish successfully.
        errors.CatalogError: SQLite cannot open or query the catalog.
    """

    def __init__(
        self, path: str | pathlib.Path, *, max_record_bytes: int = rdf.DEFAULT_MAX_BYTES
    ):
        self._connection = None
        self._max_record_bytes = _integer(
            max_record_bytes, "max_record_bytes", maximum=sys.maxsize - 65537
        )
        path = pathlib.Path(path).resolve()
        if not path.is_file():
            raise errors.CatalogMissingError(str(path))
        try:
            connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
            self._connection = connection
            connection.execute("PRAGMA query_only=ON")
            connection.create_function(
                "lcats_casefold", 1, str.casefold, deterministic=True
            )
            _store.validate_schema(connection)
            self._info = {
                key: json.loads(value)
                for key, value in connection.execute("SELECT key,value FROM metadata")
            }
            if self._info.get("status") != "complete":
                raise errors.CatalogIncompleteError("candidate status is not complete")
            if self._info.get("parser_version") != _store.PARSER_VERSION:
                raise errors.CatalogSchemaError("incompatible recorded parser version")
        except (sqlite3.Error, ValueError, errors.CatalogError) as exc:
            self.close()
            if isinstance(exc, errors.CatalogError):
                raise
            raise errors.CatalogSchemaError(f"cannot read catalog: {exc}") from exc

    def __enter__(self):
        self._require_open()
        return self

    def __exit__(self, *_):
        self.close()

    def close(self) -> None:
        """Close this session; repeated close calls are harmless."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _require_open(self):
        if self._connection is None:
            raise errors.CatalogClosedError("catalog session is closed")
        return self._connection

    def _rows(self, sql, parameters=()):
        try:
            return self._require_open().execute(sql, parameters).fetchall()
        except sqlite3.Error as exc:
            raise errors.CatalogError(f"catalog query failed: {exc}") from exc

    @property
    def info(self) -> dict:
        """Return detached build status, source identity, counts and limits."""
        self._require_open()
        return copy.deepcopy(self._info)

    def get(self, ebook_id: int) -> models.ParsedRecord | None:
        """Return complete source-scoped metadata, or None for a missing ID.

        Source length and SHA-256 are checked before parsing. Stored RDF is
        reparsed under the compatible parser version; no network is accessed.
        """
        _integer(ebook_id, "ebook_id")
        rows = self._rows(
            "SELECT source_name,parser_version,raw_size,sha256,encoding,length(data) FROM sources WHERE ebook_id=?",
            (ebook_id,),
        )
        if not rows:
            if self._rows("SELECT 1 FROM ebooks WHERE id=?", (ebook_id,)):
                raise errors.CatalogSchemaError("existing ebook has no source record")
            return None
        name, version, length, digest, encoding, compressed_size = rows[0]
        if version != _store.PARSER_VERSION:
            raise errors.CatalogSchemaError("incompatible record parser version")
        if (
            type(length) is not int
            or not 0 <= length <= self._max_record_bytes
            or type(compressed_size) is not int
            or compressed_size > self._max_record_bytes + 65536
        ):
            raise errors.CatalogInputError("stored RDF exceeds max_record_bytes")
        packed = self._rows(
            "SELECT substr(data,1,?) FROM sources WHERE ebook_id=?",
            (compressed_size, ebook_id),
        )[0][0]
        if encoding != "zlib" or not isinstance(packed, bytes):
            raise errors.CatalogSchemaError("unsupported source encoding")
        try:
            decoder = zlib.decompressobj()
            data = decoder.decompress(packed, self._max_record_bytes + 1)
        except zlib.error as exc:
            raise errors.CatalogSchemaError("invalid compressed source") from exc
        if (
            not decoder.eof
            or decoder.unused_data
            or decoder.unconsumed_tail
            or len(data) != length
        ):
            raise errors.CatalogSchemaError(
                "source decompression length/stream mismatch"
            )
        if not isinstance(data, bytes) or hashlib.sha256(data).hexdigest() != digest:
            raise errors.CatalogSchemaError("stored RDF hash mismatch")
        try:
            record = rdf.parse_record(
                data, source_name=name, max_bytes=self._max_record_bytes
            )
        except (errors.RecordParseError, ValueError, TypeError) as exc:
            raise errors.CatalogSchemaError(
                f"stored RDF cannot be parsed: {exc}"
            ) from exc
        if record.ebook.gutenberg_id != ebook_id:
            raise errors.CatalogSchemaError(
                "stored RDF identity disagrees with catalog"
            )
        return record

    def get_many(
        self, ebook_ids: abc.Sequence[int], *, max_source_bytes: int = 16 * 1024**2
    ) -> tuple[models.ParsedRecord | None, ...]:
        """Return ordered results including duplicate IDs and explicit misses.

        Preflight aggregate uncompressed source bytes before decoding. The
        positive max_source_bytes override budgets source content, not exact RSS.
        """
        if not isinstance(ebook_ids, (list, tuple)) or len(ebook_ids) > MAX_PAGE_SIZE:
            raise errors.CatalogInputError(
                "ebook_ids must be a list/tuple of at most 1000 IDs"
            )
        _integer(max_source_bytes, "max_source_bytes")
        self._require_open()
        total = 0
        for value in ebook_ids:
            _integer(value, "ebook_id")
            rows = self._rows("SELECT raw_size FROM sources WHERE ebook_id=?", (value,))
            if rows:
                size = rows[0][0]
                if type(size) is not int or not 0 <= size <= self._max_record_bytes:
                    raise errors.CatalogInputError(
                        "stored RDF exceeds max_record_bytes"
                    )
                total += size
                if total > max_source_bytes:
                    raise errors.CatalogInputError("batch source byte limit exceeded")
        return tuple(self.get(value) for value in ebook_ids)

    def _ids(self, filters, after_id, limit, text):
        _integer(after_id, "after_id", minimum=0)
        _integer(limit, "limit", maximum=MAX_PAGE_SIZE)
        clause, params = _where(filters, text)
        rows = self._rows(
            f"SELECT e.id FROM ebooks e WHERE e.id > ? AND ({clause}) ORDER BY e.id LIMIT ?",
            [after_id, *params, limit],
        )
        return tuple(row[0] for row in rows)

    def find_ids(
        self, filters: Filters | None = None, *, after_id: int = 0, limit: int = 100
    ) -> tuple[int, ...]:
        """Return one bounded ascending page using exact, case-sensitive matching."""
        return self._ids(filters, after_id, limit, False)

    def search_ids(
        self, filters: Filters | None = None, *, after_id: int = 0, limit: int = 100
    ) -> tuple[int, ...]:
        """Return one bounded page using literal casefolded substring matching."""
        return self._ids(filters, after_id, limit, True)

    def iter_records(
        self, filters: Filters | None = None, *, after_id: int = 0, limit: int = 100
    ) -> abc.Iterator[models.ParsedRecord]:
        """Iterate one bounded exact-match page; advance after_id for another page."""
        for ebook_id in self.find_ids(filters, after_id=after_id, limit=limit):
            yield self.get(ebook_id)
