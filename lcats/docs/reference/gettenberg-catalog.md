# Local Gutenberg catalog ingestion and queries

This interface builds an explicitly named **inactive candidate** from a local
Gutenberg RDF tar.bz2 archive. It does not download, refresh, select a cache,
activate a generation or prompt. [Catalog lifecycle](gettenberg-lifecycle.md)
and [live gathering](gettenberg-gather.md) compose this interface.

## Build a candidate

```python
from lcats.gettenberg import ingestion

report = ingestion.build_catalog(
    "/path/to/rdf-files.tar.bz2",
    "/path/to/new-candidate.sqlite",
)
```

The output must not already exist. Its parent directory must exist. The source
archive is opened read-only and retained unchanged. All ordinary RDF members
must import for a successful result. No archive tree is extracted.

`build_catalog(archive, output, *, limits=None, batch_size=256)` returns a
frozen `BuildReport`. `limits=None` selects `BuildLimits()`; batch size is 1–1000.

| Default limit | Value |
|---|---:|
| Actual compressed bytes read | 256 MiB |
| Individual member payload | 2 MiB |
| Expanded archive, including headers/padding | 4 GiB |
| Archive members examined | 200,000 |
| Candidate database and observed SQLite sidecars | 4 GiB |
| Elapsed build time | 600 seconds |

`BuildLimits` accepts explicit positive overrides for each named field:
`max_compressed_bytes`, `max_member_bytes`, `max_expanded_bytes`, `max_members`,
`max_database_bytes`, `max_seconds`. The time value must be finite; database
capacity is rounded down to SQLite pages. Time checks occur between bounded
reads and records and through a SQLite progress callback. These are cooperative
limits, not an operating-system deadline or RSS sandbox. Database page limits
and sidecar checks do not establish a quota on all SQLite temporary files;
full-source qualification measures disk and peak RSS separately.

Only ordinary regular-file entries with safe relative `.rdf` names are
supported. Links, directories, sparse files, PAX/GNU extension entries, unsafe
paths, duplicate member names, duplicate ebook IDs, malformed RDF and
unsupported non-book/deletion shapes prevent a complete result. No deletion
format is guessed. The end marker, padding after it and compression EOF are
checked. Exactly one bzip2 stream is accepted; trailing compressed bytes and
concatenated bzip2 streams are rejected. Oversized headers/payload declarations are rejected before allocating
their declared content. Parser diagnostics for otherwise supported records are
retained and counted; they remain visible for future qualification decisions.

## Accounting and failed candidates

`BuildReport` fields are `output_path`, `status`, `archive_sha256`,
`archive_bytes`, `expanded_bytes`, `members`, `imported`, `rejected`,
`uncommitted`, `diagnostics`, `elapsed_seconds`, and `database_bytes`.
Use `dataclasses.asdict(report)` for JSON-compatible reporting.

A successful build has status `complete`, at least one imported record, zero
rejections and zero uncommitted members. Foreign-key and SQLite integrity
checks must pass before the authoritative status becomes complete. The source
hash identifies the bytes read; it is absent when reading aborted before EOF.
Retrieval time/URL are not invented from a local archive path.

Failures raise `errors.CatalogBuildError`, with `code` and `report` attributes.
The report is `None` if no output was created. Record rejection produces
`incomplete_records`; explicit resource checks produce `resource_limit`;
other source/SQLite failures produce `build_failed`. Partial files are retained
for inspection. Their manifest remains `failed` or, if even recording the
failure is impossible, `building`; the public reader refuses either state.

`uncommitted` exposes examined members lost to a batch rollback after an
abort. Rejected members have persisted reason codes and bounded messages in
the diagnostic candidate's internal `archive_members` table. The count does
not claim unexamined members were accounted for after an early abort. A failed
candidate is never reusable as a complete catalog merely because it contains
some valid rows. To retry, choose a new output path or explicitly remove your
own failed candidate after inspection.

## Read records and query

```python
from lcats.gettenberg import catalog

with catalog.Catalog("/path/to/new-candidate.sqlite") as library:
    book = library.get(84)           # ParsedRecord, or None if ID is absent
    page = library.find_ids(
        catalog.Filters(languages=("en",), titles=("Frankenstein",)),
        after_id=0,
        limit=100,
    )
    matches = library.search_ids(catalog.Filters(titles=("frankenstein",)))
```

`Catalog(path, *, max_record_bytes=2 * 1024**2)` accepts a positive byte limit
no greater than `sys.maxsize - 65537`, preventing overflow in bounded reads. It opens SQLite in read-only mode
and requires a complete compatible schema/parser version. `close()` is
idempotent. Use the context manager; operations after close raise
`CatalogClosedError`. The reader never implicitly creates a missing database.

| Operation | Contract |
|---|---|
| `get(ebook_id)` | Complete `models.ParsedRecord`, or `None` for an absent positive integer ID. |
| `get_many(ebook_ids, *, max_source_bytes=16 * 1024**2)` | Tuple aligned with a list/tuple of at most 1000 IDs, including duplicate requests and `None` misses. Preflights total uncompressed source bytes, counting duplicates, before loading records. |
| `find_ids(filters=None, *, after_id=0, limit=100)` | Tuple of exact-match IDs, ascending, strictly greater than `after_id`. |
| `search_ids(filters=None, *, after_id=0, limit=100)` | Same pagination, using casefolded literal substring matching for text dimensions. |
| `iter_records(filters=None, *, after_id=0, limit=100)` | Lazy records for one bounded exact-match page; does not secretly traverse the whole catalog. |
| `info` | Detached dictionary of build status, versions, input identity, limits and accounting. |

Page size is 1–1000. Advance `after_id` to the last returned ID for the next
page. IDs are integers from 1 through SQLite's signed 64-bit maximum; booleans
and numeric strings are rejected. `after_id=0` starts at the beginning.
`get_many` budgets source content rather than exact process RSS. Large explicit
overrides permit higher memory use; `iter_records` avoids retaining a page's
records together. Closing a catalog before consuming its iterator fails.

`Filters` is immutable and accepts tuples for `ids`, `titles`, `authors`,
`languages`, `subjects`, `shelves`, `types`, `roles`, and `formats`. There are at
most 100 values per dimension. Text values are nonempty, at most 4096 characters.
Surrogate code points that cannot be encoded as UTF-8 and unknown constructor
fields are rejected. Empty tuples impose no restriction.

Dimensions combine with **AND**; values within a dimension combine with **OR**.
Authors match names and aliases; roles use complete predicate URIs; format
values preserve media-type parameters. All primary/alternative titles are
searched. Subject schemes remain in records but are not separate filter fields
in this version. Original publication dates are not inferred from issuance.

Exact matching is case-sensitive equality to original text. Text search uses
Unicode casefolded literal substrings: `%`, `_`, quotes and SQL fragments have
no wildcard or executable meaning. ID matching always uses integer equality.
Indexes support exact lookups and parent joins. Substring search can scan rows;
there is no ranking, stemming, general SQL, regex or FTS query language.

## Fidelity, schema and errors

Schema version 1 uses separate ordered tables for titles, contributor
identities/roles/names/aliases, term values/schemes, resources/formats/attributes,
additional literals/links and diagnostics. Contributor identities are scoped to
their ebook; equal resource media types never collapse distinct files.

Original RDF is stored with lossless zlib compression, original byte length,
SHA-256 and parser version. Full-record reads enforce size/decompression bounds,
verify the hash and reparse the original bytes with the compatible parser.
Thus every modeled value and diagnostic in
[the record API](gettenberg-records.md) survives ingestion. Filter tables are
not used to reconstruct a reduced record. SQLite tables are internal and may
change with a future schema version; callers should use the public API.

| Failure | Exception |
|---|---|
| Invalid IDs, filters, limits or pagination | `CatalogInputError` (`ValueError` subclass); unknown `Filters` keyword is `TypeError` |
| Missing catalog | `CatalogMissingError` (`FileNotFoundError` subclass) |
| Building/failed candidate | `CatalogIncompleteError` |
| Wrong schema/parser version or corrupt source evidence | `CatalogSchemaError` |
| Closed session | `CatalogClosedError` |
| SQLite query failure | `CatalogError` |
| Build failure | `CatalogBuildError`, with code and optional report |

All are available from `lcats.gettenberg.errors` and derive from
`GettenbergError`. No public API accepts arbitrary SQL or mutable connection
objects.

## Executed example

For this example, `archive_path` names a local archive containing ebook 84,
and `candidate_path` is a new path. Tests supply the retained real RDF fixtures.

```pycon
>>> from lcats.gettenberg import ingestion
>>> from lcats.gettenberg import catalog
>>> report = ingestion.build_catalog(archive_path, candidate_path)
>>> report.status
'complete'
>>> report.imported > 0
True
>>> with catalog.Catalog(candidate_path) as library:
...     book = library.get(84)
...     print(book.ebook.gutenberg_id)
...     print(library.find_ids(catalog.Filters(ids=(84,))))
84
(84,)

```

Generation activation and recovery belong to [catalog lifecycle](gettenberg-lifecycle.md);
remote acquisition belongs to [the resource store](gettenberg-network.md).
[CLI preparation](gettenberg-preparation.md) composes first use. These interface
contracts alone do not establish whole-corpus selection equivalence.
