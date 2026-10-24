# Local catalog lifecycle API

Module: `lcats.gettenberg.lifecycle`. All operations are offline and have no
implicit network acquisition, refresh, or legacy-cache migration.

## CatalogManager

`CatalogManager(cache_dir=None, *, lock_timeout=10.0, validation_seconds=120.0)`
resolves the LCATS cache root at construction. Managed data lives under its
`gettenberg/` child. Construction does not create directories. `lock_timeout`
is finite in `[0,60]`; `validation_seconds` is finite in `(0,3600]` and bounds
individual source-copy or full-verification phases. Build resource ceilings are
provided through `ingestion.BuildLimits` and remain separate from lock/verification
budgets. The total operation may include multiple bounded phases.

| Method | Contract |
|---|---|
| `setup(archive=None, *, limits=None)` | Reuse a valid active generation; otherwise require a local path or archive-kind `SourceArtifact`, build, verify and activate. Returns `Generation`. |
| `rebuild(archive=None, *, limits=None, allow_count_change=False)` | Always prepare a new candidate from a supplied path/`SourceArtifact` or active retained source; verify and activate if count policy allows. |
| `update(source, *, limits=None, allow_count_change=False)` | Consume an archive-kind `SourceArtifact` offline. Verify and reuse matching active archive bytes; otherwise build and activate through the same count-change policy. |
| `activate(generation_id, *, allow_count_change=False)` | Verify a sealed candidate or retained generation and atomically publish its pointer. |
| `open()` | Return a context-managed `catalog.Catalog` pinned to the selected generation. No writer lock or full hash scan. |
| `status()` | Return a JSON-compatible description with `missing`, `ready`, or `invalid` state, resolved paths, candidates, generations, activation and legacy information. Lightweight verification only. |
| `cleanup()` | Return a tuple of removed paths: candidates and recognized temporary files only. Requires writer lock. |

`Generation` is a frozen dataclass containing `generation_id`, `catalog_path`,
`archive_path`, a detached `manifest` dictionary, `previous_count`, and `reused`.
Mutating the detached manifest does not write it back. `previous_count` is the
count at the time of this activation; `reused` is true for setup or unchanged update reuse.

## Layout and manifest

```text
<cache_dir>/gettenberg/
  writer.sqlite
  active.json
  archives/<sha256>.tar.bz2
  candidates/<uuid32>/catalog.sqlite
  candidates/<uuid32>/manifest.json
  generations/<uuid32>/catalog.sqlite
  generations/<uuid32>/manifest.json
```

The manifest records its format version, generation ID, schema/parser versions,
archive and database SHA256/byte size, logical snapshot ID, counts, source provenance and preparation timestamp. Snapshot identity is SHA256 of the ASCII string
`<archive_sha256>:<schema_version>:<parser_version>`; distinct builds may share
this identity. Counts cover ebooks, sources, archive members, titles, contributions,
resources and diagnostics. `source.retrieved_at` and `source.http_etag` are null
for local input; no network provenance is inferred.

The versioned active pointer contains the generation ID, manifest hash,
activation time, previous generation/count, new count, and count-change approval.
Managed paths derive from validated IDs/hashes, never arbitrary manifest paths.
Generation manifest version2 is bounded to 128 KiB, allowing a complete receipt
(up to64 KiB) plus generation metadata. Version1 local manifests remain readable.
Active pointers retain version1 and their 64 KiB bound. All reject symlinks and
nonregular files.

Activation requires complete compatible catalog metadata, matching source hash,
matching sealed database identity, SQLite integrity and foreign-key checks,
actual import/source/member accounting, and explicit acceptance of any changed
ebook count. Candidates are not query-visible through manager.open before the
atomic pointer replacement. Existing readers keep their generation throughout.

## Errors

All lifecycle errors derive from `errors.CatalogError`.

| Error | Meaning |
|---|---|
| `CatalogInputError` | Invalid ID, limit or approval argument. |
| `CatalogMissingError` | No active generation or required local source selection. |
| `CatalogSchemaError` | Incompatible catalog or manifest schema/parser. |
| `CatalogLifecycleError` | Invalid managed state, failed integrity/accounting, verification budget, or local filesystem failure. |
| `CatalogLockError` | Writer lock contention reached its timeout. |
| `CatalogCountChangeError` | Explicit count approval required; attributes `generation_id`, `previous`, `candidate`. Candidate remains recoverable. |
| `CatalogPublicationError` | Commit point reached but durability confirmation failed; `published=True` means inspect status before deciding recovery. |
| `CatalogBuildError` | Importer failed; its report describes incomplete candidate accounting. |

Published generation and archive retention is conservative and unbounded across
operations. Individual build/copy/verification bounds do not impose a whole-cache
quota. Cleanup never deletes the coordination file, legacy artifacts or published
generations. See [the how-to](../how-to/gettenberg-catalog.md) for recovery and
filesystem/platform prerequisites.

Local archive paths must be representable as UTF-8 for manifest provenance.
A surrogate-escaped POSIX path raises `CatalogInputError` before any archive
copy or candidate build; setup reuse still ignores an unused archive argument.


Archive retention also takes `<cache>/gettenberg/archive-publication.sqlite`, a
persistent leaf lock shared with resource acquisition. It protects publication,
verification of an existing archive and temporary hard-link cleanup. Catalog
writer → archive publication is the lock order; no catalog/network outer lock
may be acquired while the archive leaf lock is held. Do not delete lock files.

Cleanup conservatively retains abandoned archive temporary files with more than
one hard link. Removing such a name changes the published inode's ctime and could
invalidate a concurrent lock-free resource integrity check. These linked orphans
are retained evidence; cleanup still removes unlinked recognized archive temps.

## Acquired archive provenance and refresh composition

Pass the `SourceArtifact` itself to `setup`, `rebuild` or `update` to preserve
acquisition evidence. Passing only `artifact.path` deliberately treats it as
unattributed local input. A catalog accepts only `kind="archive"` artifacts;
ordinary resource downloads cannot silently become catalog sources.

New manifests use `source.kind="acquired_archive"`, `source.receipt_sha256`, and
`source.receipt` (the complete schema1 or schema2 JSON receipt). Receipt schema,
canonical hash, archive-kind request identity, body hash and byte length are
validated before candidate construction and again when reading the manifest.
The retained archive is independently hashed against this identity. No receipt
file lookup or network access is needed to reopen or implicitly rebuild a
catalog. Implicit rebuild carries forward its original provenance; receipt
history is referenced by hash, not recursively traversed.

`update` always checks supplied receipt/body integrity, even on unchanged input.
Reuse also verifies the retained archive, database hash/integrity and accounting.
It does not prepare a candidate, change the active pointer, or replace the
immutable generation's build receipt with a later validation receipt. The latest
HTTP check remains in the resource cache. An older local generation remains
unattributed when update reuses its bytes; explicit `rebuild(artifact)` creates
a new generation with acquisition provenance if desired.

`setup` retains its existing reuse-first semantics and ignores unused supplied
input on an active hit. `rebuild` always builds, even from identical bytes.
Acquisition success does not approve activation: changed ebook counts require
`allow_count_change=True` or later explicit `activate` approval. Download,
receipt-validation, retention and build failures leave the prior active catalog
and pinned readers usable. Publication failures after the active-pointer commit
point retain the existing `CatalogPublicationError.published` contract.
