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
| `setup(archive=None, *, limits=None)` | Reuse a valid active generation; otherwise require local input, build, verify and activate. Returns `Generation`. |
| `rebuild(archive=None, *, limits=None, allow_count_change=False)` | Always prepare a new candidate from supplied local input or active retained source; verify and activate if count policy allows. |
| `activate(generation_id, *, allow_count_change=False)` | Verify a sealed candidate or retained generation and atomically publish its pointer. |
| `open()` | Return a context-managed `catalog.Catalog` pinned to the selected generation. No writer lock or full hash scan. |
| `status()` | Return a JSON-compatible description with `missing`, `ready`, or `invalid` state, resolved paths, candidates, generations, activation and legacy information. Lightweight verification only. |
| `cleanup()` | Return a tuple of removed paths: candidates and recognized temporary files only. Requires writer lock. |

`Generation` is a frozen dataclass containing `generation_id`, `catalog_path`,
`archive_path`, a detached `manifest` dictionary, `previous_count`, and `reused`.
Mutating the detached manifest does not write it back. `previous_count` is the
count at the time of this activation; `reused` is true only for setup reuse.

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
archive and database SHA256/byte size, logical snapshot ID, counts, local source
label and preparation timestamp. Snapshot identity is SHA256 of the ASCII string
`<archive_sha256>:<schema_version>:<parser_version>`; distinct builds may share
this identity. Counts cover ebooks, sources, archive members, titles, contributions,
resources and diagnostics. `source.retrieved_at` and `source.http_etag` are null
for local input; no network provenance is inferred.

The versioned active pointer contains the generation ID, manifest hash,
activation time, previous generation/count, new count, and count-change approval.
Managed paths derive from validated IDs/hashes, never arbitrary manifest paths.
Manifests and pointers are bounded to 64 KiB and reject symlinks/nonregular files.

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
