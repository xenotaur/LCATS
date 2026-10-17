# Gather stories with explicit sources

Run from `LCATS/lcats` in the project environment. The catalog and originals live
under `--cache-dir` (otherwise `LCATS_CACHE_DIR`, default `cache`). Story outputs
live under `LCATS_DATA_DIR` (default `data`); collection logs live in `logs/gather`.

## Gather a curated collection without catalog setup

```bash
lcats gather sherlock --dry-run
lcats gather sherlock
lcats gather sherlock --offline
```

Curated collections have fixed source URLs and do not require metadata setup.
The normal command downloads missing HTML; offline mode uses cached HTML or
existing story outputs and fails with exit 2 on a source miss. It never downloads.

## Gather metadata-dependent stories

`mass_quantities` enriches and filters its existing fixed list of ebook IDs using
the new catalog. Select an archive and appropriate main/generated Gutenberg
mirror roots first. **No operational default mirror is configured yet.** These
variables are placeholders for endpoints you have deliberately selected, not
ready-to-use recommendations:

```bash
export ARCHIVE_URL='https://chosen.example/catalog/rdf-files.tar.bz2'
export MAIN_ROOT='https://chosen.example/main/'
export GENERATED_ROOT='https://chosen.example/generated/'

lcats gather mass_quantities --catalog-url "$ARCHIVE_URL" \
  --gutenberg-main-root "$MAIN_ROOT" --gutenberg-generated-root "$GENERATED_ROOT" \
  --dry-run

lcats gather mass_quantities --catalog-url "$ARCHIVE_URL" \
  --gutenberg-main-root "$MAIN_ROOT" --gutenberg-generated-root "$GENERATED_ROOT"
```

Review the local plan and endpoint policy before executing. The second command
asks for approval only if catalog setup is required. Supply `--yes` for approved
unattended setup. Redirected input is not an interactive approval; an unattended
missing approval fails promptly. To use a local RDF archive, replace
`--catalog-url "$ARCHIVE_URL"` with `--catalog-archive /path/to/rdf-files.tar.bz2`.
A ready catalog is reused without prompting or consulting the archive argument.
Explicit URLs permit their own origins. Additional redirect origins require
repeatable `--allow-origin https://chosen.example` flags for new resource access.

The command selects a supported plain-text resource, acquires missing original
bytes, strictly decodes, removes recognized Gutenberg boilerplate, then applies
existing story extraction, normalization and overrides. It writes
`data/mass_quantities/<story-slug>/story.json`, retaining acquisition and derivation
provenance. Existing regular output files are reused without replacement or a
claim that their contents are valid. Source/decode/integrity failures abort with
exit 2; metadata or extraction exclusions remain per-story skips in the run log.

## Repeat without network access

Keep the same roots: they are part of source request identity even when offline.

```bash
lcats gather mass_quantities --offline --cache-dir /path/to/cache \
  --gutenberg-main-root "$MAIN_ROOT" --gutenberg-generated-root "$GENERATED_ROOT"
```

A missing catalog can also be built offline from an explicit local archive or a
verified cached archive request, with setup approval. Missing story originals
cannot be downloaded offline. Corrupt cache evidence is a failure, not a miss.
`--yes` never refreshes a catalog, redownloads cached sources, or replaces story
outputs. For deliberate catalog maintenance, use the separate
[refresh/rebuild commands](gettenberg-preparation.md#refresh-or-rebuild-deliberately).

The offline flag also covers curated HTML when both collection types are selected.
With no names, all built-in collections are selected, so the metadata-dependent
configuration is required before any collection runs. Dry-run does not create
files or import consumers and leaves metadata-dependent counts unresolved.

## Diagnose a failed run

Inspect the failure and the collection's `logs/gather/*_gather_run_log.jsonl`.
Previously completed story files and source bytes remain available for a retry.
Invalid UTF-8 or ambiguous boilerplate is not silently replaced, guessed or sent
through the old API. Keep the original-byte receipt and catalog provenance when
investigating a record. Do not regenerate an existing corpus just to migrate its
metadata. This tranche changes live gathering; legacy experimental callers and
removal of the external dependency remain separate work.
