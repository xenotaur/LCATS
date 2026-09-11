---
id: PROP-LCATS-RICH-LINGUISTICS-COLUMNAR-STORAGE
type: design_proposal
title: Durable Storage for Rich Linguistic Artifacts
status: proposed
created_on: 2026-09-10
updated_on: 2026-09-10
implementation_status: not_started
implemented_by:
  - WI-LINGUISTICS-0009
supersedes: []
superseded_by: null
related_design:
  - project/design/proposals/proposed/comparative-lexical-visualization/00_proposal.md
related_workstreams:
  - WS-COMPARATIVE-LEXICAL-VISUALIZATION
---

## Summary

LCATS should keep validated rich linguistic JSON as the canonical, reviewable
source artifact and use Parquet as the derived analysis format for larger token
tables. Canonical JSON should be retained in a release or durable archive when
it is too large for ordinary Git; manifests, reports, hashes, schemas, and
small derived artifacts remain in Git. Parquet should be produced with a pinned
schema, Zstandard compression, deterministic metadata, and a tested restore
path to canonical JSON. The project should not add Parquet, HDF5, DuckDB, or
another storage dependency to the core runtime until a later implementation
item demonstrates a stable API and dependency policy.

This is a storage and retention policy. It does not change
`linguistics-token-detail-v2`, `linguistics-lexicon-v1`, or the experiment-09
bridge.

## Evidence

The WI-LINGUISTICS-0007 pilot processed 146 stories and 1,087,742 tokens. Its
report records 409,385,970 bytes for the copied story and linguistic JSON,
146 valid compact sidecars, 146 valid token-detail artifacts, and 146 valid
lexicons. The experiment-local Parquet export contains three tables and is
13,253,393 bytes:

| Artifact | Measured bytes | Measurement source |
| --- | ---: | --- |
| Expanded experiment JSON mirror | 409,385,970 | `experiments/09_rich_linguistics_genre_sample/results/experiment_report.json` |
| `tar.zst` of the JSON mirror | 38,013,312 | fresh local measurement from the pilot mirror; temporary archive, not a committed artifact |
| Parquet package, Zstandard-compressed | 13,253,393 | `experiments/09_rich_linguistics_genre_sample/results/experiment_report.json` and `experiments/09_rich_linguistics_genre_sample/results/parquet/parquet_manifest.json` |

The expanded-mirror total is not a like-for-like comparison with Parquet: it
includes source stories, compact sidecars, token-detail JSON, and derived
lexicons, while the Parquet package contains token-detail sentence, story, and
token tables only. The Parquet package is 3.49% of the token-detail JSON alone
(13,253,393 / 379,609,077), and 3.24% of the all-in expanded mirror. It is
about 35% of the measured compressed JSON archive, but that archive comparison
also retains the other artifact classes. These are storage measurements, not
claims about statistical quality or significance. The report also projects
roughly 5.24 GB of expanded rich output for 1,868 stories; that projection is
linear and must be revisited after the full-run gate.

The experiment bridge exports the canonical token-detail JSON into sentence,
story, and token tables and restores canonical JSON. Its tests exercise export,
restore, manifest generation, and optional fields. Invalid-input and mismatch
rejection should be part of the future supported-library contract. The bridge
is valuable evidence, but its experiment-local location and pandas/PyArrow
dependency do not by themselves establish a project-wide API.

## Design goals and boundaries

The storage policy must preserve:

- source story identity, source commit, backend/model/configuration, schema
  versions, tokenizer and stopword policy, counts, and content hashes;
- validation against the existing compact, token-detail, and lexical schemas;
- deterministic regeneration and a machine-readable manifest for every derived
  artifact;
- access to alternate statistics without rerunning NLP;
- human-readable review paths for debugging and audit;
- operation without writing generated sidecars into `corpora/`.

The policy does not make a binary file the source of truth, change the rich
schemas, guarantee that every artifact belongs in Git, or authorize the
full-corpus run. Those decisions remain subject to WI-LINGUISTICS-0008's
explicit quality, runtime, storage, retention, and research-need gate.

## Options considered

### JSON

JSON is the strongest canonical source for LCATS because the current validators
and downstream tools already consume it, it is inspectable in code review, and
it preserves nested provenance without a translation layer. Its decisive cost
is size: the pilot's expanded mirror is about 409 MB. Pretty-printed JSON is
also a poor repeated-query format and is not suitable for storing a projected
full-corpus mirror in ordinary Git.

### JSONL and compressed JSON archives

JSONL permits streaming and independent record processing, while a compressed
`tar.zst` archive retains the original JSON without changing its schema. Both
are useful transport or archive choices. JSONL is less convenient for the
current nested per-story artifacts and does not solve the repeated parsing
cost. A compressed archive is not directly queryable and requires extraction,
but it is simple, auditable, and preserves the canonical bytes. The pilot's
fresh `tar.zst` measurement is substantially smaller than raw JSON, but still
larger than Parquet.

### Parquet

Parquet is the preferred derived analysis format. It is an open, column-oriented
format designed for compressed bulk storage and broad language/tool support.
Column chunks can be encoded and compressed independently, and readers can
avoid loading irrelevant columns or row groups. Those properties match queries
such as POS-filtered counts, lemma counts, document frequencies, and sentence
or story slices. DuckDB can query Parquet directly with projection and filter
pushdown, so a separate database file is not required for the normal analysis
path.

Parquet is not the canonical source here. Its schema is tabular, its nested
representation and metadata conventions would need LCATS-specific contracts,
and a Parquet reader is an additional dependency. The manifest and restore
contract must therefore remain mandatory.

### Arrow IPC / Feather

Arrow IPC is a strong in-process and cross-language interchange format. Its file
format supports random access to record batches, and Arrow libraries can
memory-map local files. It is attractive for dataframe workflows and can be a
useful intermediate during computation. It is not the first retention format
for LCATS because the pilot's measured win and existing bridge are Parquet-based,
and Arrow IPC is less naturally organized as a partitioned analytical dataset.
It remains an acceptable implementation detail or optional export, not a
second canonical format.

### HDF5

HDF5 is technically capable and may provide excellent compression, chunking,
hierarchical grouping, and partial dataset access. It is a good fit for
scientific multidimensional arrays or one cohesive hierarchical file. LCATS's
primary workload is relational token/sentence/story filtering and aggregation,
where Parquet's column and row-group semantics are more direct. HDF5 would also
introduce another native-library dependency and another schema/metadata
convention without a demonstrated advantage over the measured Parquet bridge.
It is therefore not disqualified in general, but it has no decisive advantage
for this workload and should not be adopted as the project default.

### SQLite and DuckDB

SQLite offers a stable, single-file, serverless relational database with
excellent ad hoc inspection and indexing. It is a reasonable packaging option
for a curated query database, but its row-oriented storage is less naturally
suited to bulk analytical scans and it would duplicate the Parquet data model.

DuckDB is an excellent analysis engine and can query Parquet directly, including
column and filter pushdown. A `.duckdb` database could be useful for a derived
index or local interactive analysis, but it is an engine/container choice, not
the most portable interchange artifact. The recommendation is to support
DuckDB as an optional consumer of Parquet before considering a committed
DuckDB database.

### CoNLL-U

CoNLL-U is the best interoperability choice when exchanging Universal
Dependencies annotations with NLP tools and treebanks. Its ten tab-separated
token fields, sentence boundaries, and comments are valuable for export and
manual inspection. It is not a lossless LCATS canonical format without custom
extensions for source offsets, stable story/sentence/token IDs, provenance,
and LCATS-specific fields. Use it only as an explicit interchange export when
needed, never as the storage default.

## Recommendation

Adopt a three-tier policy:

1. **Canonical validation artifacts:** retain the source story plus the
   validated per-story `linguistics.json` and `linguistics.tokens.json`
   artifacts, together with manifests, hashes, provenance, and validation
   reports. Keep these in the experiment output or a durable release archive.
   Do not promote generated sidecars into `corpora/`.
2. **Derived analysis artifacts:** treat `linguistics.lexicon.json` as a
   regenerable materialized view and produce Parquet tables from validated
   token-detail-v2 data. Both derived forms use versioned schemas, deterministic
   ordering, manifests, and tested linkage or restore paths. Use DuckDB or
   Arrow as optional readers rather than committing their databases or making
   them core dependencies.
3. **Git contents:** check in the work item/proposal, schemas and validators,
   small reports, manifests, hashes, reproducible commands, and derived data
   only when it remains within repository artifact policy. Keep bulky canonical
   JSON and full-corpus Parquet in a release or external archive with checksums
   and the exact source commit/configuration needed to regenerate it.

The existing experiment-09 Parquet bridge should remain the reference
implementation for the pilot. A future implementation item may extract a
supported library only after this policy is adopted and its API is bounded
around validation, export, restore, manifests, and provenance. That item should
not silently change the existing schemas or require every LCATS installation
to install PyArrow.

## Required contract for a future library

A supported implementation should provide:

- explicit input schema and schema-version checks;
- stable story, sentence, and token keys and deterministic row ordering;
- source/configuration/schema hashes in the manifest;
- compression and library-version metadata;
- export and restore round-trip tests against canonical JSON;
- rejection of stale, incomplete, mismatched, or duplicate inputs;
- a dependency-light canonical path and an optional columnar extra;
- a CLI or API that writes only to an explicit output root.

## Consequences for WI-LINGUISTICS-0008

WI-LINGUISTICS-0008 must not start a full-corpus run until a human has reviewed
this policy and selected the retention destination. On a go decision, the run
should:

- write to a new experiment-local output root;
- retain manifests, reports, hashes, and the selected derived Parquet package;
- archive canonical JSON rather than placing a multi-gigabyte mirror in Git;
- record the archive identifier or location without embedding credentials;
- validate that Parquet restores the canonical token-detail facts; and
- report actual sizes and timings before any subsequent promotion to a general
  library or project-wide artifact store.

A no-go or defer decision remains valid if the pilot quality gate, storage
budget, archive access, or research need is insufficient. The policy does not
turn a favorable Parquet size into authorization for POS figures or a
full-corpus run.

## External references

- Apache Parquet overview and compression specification:
  https://parquet.apache.org/ and
  https://parquet.apache.org/docs/file-format/data-pages/compression/
- Apache Arrow columnar and IPC file format:
  https://arrow.apache.org/docs/format/Columnar.html
- DuckDB Parquet scans, projection pushdown, and filter pushdown:
  https://duckdb.org/docs/stable/data/parquet/overview
- HDF5 data model and file structure:
  https://portal.hdfgroup.org/documentation/hdf5/latest/_h5_d_m__u_g.html
- SQLite application-file and on-disk format documentation:
  https://www.sqlite.org/appfileformat.html and
  https://www.sqlite.org/fileformat.html
- Universal Dependencies CoNLL-U format:
  https://universaldependencies.org/format.html

## Open implementation questions

The policy leaves these intentionally explicit for the implementation item:

- the exact Parquet partition and row-group sizing for the full corpus;
- the project archive/release service and retention period;
- the repository's maximum acceptable checked-in derived-artifact size;
- whether an Arrow IPC export is useful for a specific downstream consumer;
- whether a future CoNLL-U export should include LCATS-specific comments or
  use a documented CoNLL-U Plus extension.
