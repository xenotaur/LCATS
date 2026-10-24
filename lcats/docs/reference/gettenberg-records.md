# Gutenberg metadata records and RDF parsing

`lcats.gettenberg.rdf` parses one supplied Gutenberg RDF/XML record into
immutable, typed metadata. It does not open files, download data, set up a
catalog, or prompt. It supplies the records used by the local catalog and current
metadata-dependent gathering; see [the architecture](../explanation/gettenberg-architecture.md).

## Entry point

```python
from lcats.gettenberg import rdf

result = rdf.parse_record(raw_bytes, source_name="cache/epub/84/pg84.rdf")
book = result.ebook
```

`parse_record(data: bytes, *, source_name: str, max_bytes: int = 2 * 1024**2)`
returns `models.ParsedRecord`. `source_name` is a nonempty evidence label,
never interpreted as a filename or URL. The limit is checked before XML
parsing; an explicit positive integer override is available. The caller owns
reading the input and enforcing archive/download bounds.

The following small example is executed by the unit suite:

```pycon
>>> import base64
>>> import json
>>> from lcats.gettenberg import rdf
>>> raw = b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:pg="http://www.gutenberg.org/2009/pgterms/" xmlns:dc="http://purl.org/dc/terms/" xml:base="https://www.gutenberg.org/"><pg:ebook rdf:about="ebooks/42"><dc:title xml:lang="en">A title</dc:title></pg:ebook></rdf:RDF>'
>>> result = rdf.parse_record(raw, source_name="example.rdf")
>>> result.ebook.gutenberg_id
42
>>> result.ebook.titles[0].value.text
'A title'
>>> result.ebook.titles[0].value.language
'en'
>>> result.ebook.downloads is None
True
>>> exported = json.loads(json.dumps(result.to_dict()))
>>> base64.b64decode(exported["source"]["data"]["value"]) == raw
True
>>> result.diagnostics
()

```

## Record types

All types live in `lcats.gettenberg.models`. They are frozen dataclasses with
slots. The parser returns tuples for collections, preserving source order and
multiplicity. An absent collection is `()`; an absent download count is `None`.
An explicitly empty source literal remains an empty string. XML comments and
processing instructions do not discard adjacent literal text. No placeholder
authors, dates, or titles are invented.

| Type | Fields and meaning |
|---|---|
| `Literal` | `text`, optional `language` and `datatype` URI. Language inherits `xml:lang`; an empty tag clears inheritance. |
| `Title` | `value: Literal`, `kind` (`primary` or `alternative`). All titles survive; callers choose a display title. |
| `Term` | `value: Literal`, `schemes: tuple[str, ...]`, optional resolved `uri` and source `node_id`. Used for languages, subjects, shelves, ebook types and resource formats. Blank-node labels are scoped to the original record, never global contributor/catalog IDs. |
| `Agent` | `uri`, `names`, `aliases`, `birth_dates`, `death_dates`, `webpages`. Aliases remain attached to this identity. Dates are lexical source claims, including uncertain or negative dates. |
| `Contribution` | `role_uri`, `agent`. Creator uses the complete DCTERMS creator URI; other roles use their complete Library of Congress relator URI. |
| `Resource` | `uri`, `formats`, `sizes`, `modified`, `is_format_of`. Repeated size/modification claims are preserved. Separate URLs remain separate even with equal MIME types. MIME parameters, including declared charset, remain in format text. |
| `MetadataValue` | `predicate_uri`, `value`. Preserves source MARC fields, including source-supplied summaries and print-source notes. |
| `Ebook` | `gutenberg_id`, `uri`, `titles`, `contributors`, `languages`, `subjects`, `shelves`, `types`, `resources`, `publishers`, `rights`, `issued`, `descriptions`, `contents`, `licenses`, `downloads`, `additional_metadata`. |
| `SourceEvidence` | Caller `source_name`, SHA-256 `sha256`, exact `data: bytes`, `parser_version` (`"1"`). No retrieval time or URL is fabricated. |
| `Diagnostic` | `code`, XML `path`, `predicate_uri`, `message`. Unmodeled values remain available in source evidence. |
| `ParsedRecord` | `ebook`, `source`, `diagnostics`; `to_dict()` exports every field. |

These are **ebook/volume** records. Their titles and subjects do not become
confirmed story-level metadata. `issued` is the Gutenberg release date, not
an original publication date. MARC summaries retain their source wording;
they are not LCATS analysis or independently verified facts.

`ParsedRecord.to_dict()` returns a detached JSON-compatible export with
`schema_version: 1`. Tuples become arrays. Bytes become
`{"encoding": "base64", "value": "..."}`. All modeled fields and exact source
bytes survive serialization; mutating an exported dictionary does not mutate
the record. There is currently no public JSON-to-record constructor.

Shared agents are expanded by JSON export. To bound that expansion, `to_dict`
accepts `max_nodes=100_000` (traversed values and field names) and
`max_text_bytes=16 * 1024**2` (cumulative UTF-8 text plus base64 payload).
Generated schema/base64 wrapper fields are included. Repeated text is counted
each time. Surrogate code points in caller-supplied source labels are counted
as six-byte backslash escapes and preserved in the exported string; default
`json.dumps` can encode such filesystem labels. These are traversal/content budgets, not
an exact serialized JSON length or process-RSS limit; JSON escaping, punctuation
and pretty printing add bytes. `errors.ExportLimitError` is raised before a
budget is exceeded; no partial export is returned and the original record is
unchanged. Explicit positive-integer overrides allow a caller to allocate more
space deliberately. The default is tested on every retained real fixture.

## Supported RDF/XML profile

The parser requires an `rdf:RDF` root with exactly one direct `pgterms:ebook`
and no additional nested ebooks. Ebook identity is an HTTP(S)
`www.gutenberg.org/ebooks/<positive-decimal-ID>` URI without query, fragment,
leading zero or trailing slash. Relative URIs require a resolving `xml:base`;
base resolution also applies to agents, files, links and datatypes. Whitespace
in source URI claims is percent-encoded and produces a `normalized_uri`
diagnostic with the original spelling; original RDF bytes are unchanged.
This does not relax strict ebook-ID validation or validate remote availability.

Supported properties follow the observed bulk-feed profile:

- Literal ebook titles/alternatives, publishers, rights, issuance,
  descriptions, table of contents, download counts, and `pgterms:marcNNN`
  source fields.
- Inline `pgterms:agent` under `dcterms:creator` or a predicate in
  `http://id.loc.gov/vocabulary/relators/`. Names, aliases, life dates and
  webpage links remain associated with each contribution.
- Inline `rdf:Description` containing `rdf:value` and optional
  `dcam:memberOf` for language, subject, bookshelf, type and format. Description
  identities are preserved explicitly; no graph inference or external lookup is
  performed. Stray non-whitespace text outside structured properties fails.
- Inline `pgterms:file` under `dcterms:hasFormat`, with format terms, extent,
  modification literals and source ebook relationships.
- Catalog-level `cc:Work` licensing/comments and linked-page descriptions
  are recognized but retained only in original RDF. They are not ebook rights.

Any `pgterms:marcNNN` field is modeled generically, including new numbers;
any predicate in the relator namespace is modeled as a role. Other unmodeled
predicates produce `unmodeled_predicate` diagnostics, even when a familiar
predicate appears in an unsupported context. Unknown attributes produce
`unmodeled_attribute`. Diagnostics include source paths; they are not permission
to treat an incomplete future catalog as qualified.

Contributor URI references resolve only to matching agent definitions inside
the same record, including forward references. Repeated references share one
immutable agent object, avoiding repeated expansion while parsing. Conflicting definitions or
unresolved references fail; no external fetch is attempted. The parser does
not resolve external/blank-node graph references, infer RDF triples, or support `rdf:parseType`/`rdf:ID` forms. A recognized property with
an unsupported shape fails rather than silently losing its typed value.
Multiple download counts are ambiguous and fail; file extents and modification
claims may repeat. Numeric counts/sizes must be nonnegative signed-64-bit-range
integers. Missing fields are allowed. Non-text ebooks remain metadata records;
collection selection belongs elsewhere. Deletion and non-ebook records fail
with `unsupported_record`; archive accounting is handled by the separate
[ingestion API](gettenberg-catalog.md).

## Errors and XML restrictions

Import `errors` from `lcats.gettenberg`. `RecordParseError` inherits both
`GettenbergError` and `ValueError`, and exposes `code` and `source_name`.

| Code | Meaning |
|---|---|
| `record_too_large` | Input exceeds the caller's byte limit. |
| `malformed_xml` | XML syntax/encoding or libxml structural-limit failure. |
| `unsafe_xml` | A syntactically valid DOCTYPE is present, including internal or external declarations. |
| `unsupported_record` | Not exactly one supported ebook record. |
| `invalid_identity` | Invalid ebook identity or an unresolved/invalid URI. |
| `unsupported_shape` | Known RDF property uses an unsupported or ambiguous representation. |
| `invalid_value` | Numeric metadata is not a supported nonnegative integer. |

Incorrect input types raise `TypeError`; an empty label or invalid byte limit
raises `ValueError`. Malformed DTD syntax can fail as `malformed_xml` before
the DOCTYPE check. Neither outcome accepts the input.

The parser disables entity resolution, DTD loading, network access, recovery
and huge-tree mode explicitly. It rejects DOCTYPE and never invokes XInclude.
Unknown XInclude elements remain source evidence with diagnostics. The byte
bound and libxml limits remain active. It uses the documented
[lxml parser options](https://lxml.de/parsing.html#parser-options), with lxml
explicitly declared as a dependency rather than supplied by gutenbergpy.

## Fixtures and qualification boundary

Seven original cached public-domain RDF records cover aliases, alternative
titles, multiple languages, roles, life dates, repeated resource formats,
in-record contributor references and whitespace in file URLs.
Their exact hashes, archive member names, source-archive hash and provenance
limitations are in
[`tests/gettenberg_tests/fixtures/provenance.json`](../../tests/gettenberg_tests/fixtures/provenance.json).
Authored tests cover unsupported/malformed/hostile records and import isolation.
No unit test downloads Gutenberg data. Parsing qualification does not establish
catalog lifecycle, acquisition, CLI migration or corpus equivalence.
