# Plan gathering and prepare a catalog

Run from `LCATS/lcats` in the project environment. These commands use
`LCATS_CACHE_DIR` (default `cache`); catalog and gather commands also accept `--cache-dir`.

## Inspect requirements first

```bash
lcats gather sherlock --dry-run
lcats gather mass_quantities --dry-run
lcats catalog status
```

Dry-run validates the entire collection selection before any collection runs.
It reports collection requirements, not guessed story counts. Curated fixed-URL
collections such as `sherlock` do not need a metadata catalog. `mass_quantities`
needs metadata for enrichment/filtering of its fixed ebook IDs. No collection
implementation is imported by dry-run, and no LCATS or plotting cache is created.
An unknown collection fails with exit 2 before gathering starts.

Actual `mass_quantities` gathering now uses the new catalog, original-byte store,
strict decoder and conservative boilerplate cleanup. Setup and offline policy
are enforced on that live path. Curated fixed-URL HTML collections use their
existing source cache with the same offline restriction. See
[gather with default or explicit sources](gettenberg-gather.md) for the complete workflow.
The retired helpers and external dependency have been removed; see the
[migration guide](gettenberg-migration.md) for maintained research entry points.

## Set up from an existing archive

```bash
lcats catalog setup --archive /path/to/rdf-files.tar.bz2 --dry-run
lcats catalog setup --archive /path/to/rdf-files.tar.bz2 --offline
```

The second command asks before initializing a missing catalog in an interactive
terminal. Answering no, EOF, or running unattended without `--yes` leaves it alone.
For an unattended approved setup:

```bash
lcats catalog setup --archive /path/to/rdf-files.tar.bz2 --offline --yes
```

A ready catalog is reused without prompting or reading the supplied archive.
`--yes` authorizes required setup only; it does not refresh, change an existing
catalog, redownload existing resources, or replace extracted story outputs.
An invalid catalog is reported as invalid, not silently rebuilt.

## Use the default or an explicitly chosen archive source

Standalone setup uses the same published archive as smart gathering:

```bash
lcats catalog setup --dry-run
lcats catalog setup --yes
```

The default is `https://www.gutenberg.org/cache/epub/feeds/rdf-files.tar.bz2`.
The first command shows the exact source, approval requirement, byte bound and
permitted origins without requests or writes. Use `--archive` for local bytes,
or replace the default URL with an explicitly chosen source:

```bash
lcats catalog setup --url "$ARCHIVE_URL" --dry-run
lcats catalog setup --url "$ARCHIVE_URL" --yes
```

The selected URL permits its origin. Redirects to other origins need repeated
`--allow-origin https://chosen.example` arguments. Existing bounded acquisition
limits apply (256 MiB archive, 900-second acquisition budget, pacing and bounded
retries). Planning sends no requests. `--offline` overrides online authority and
can reuse a verified acquired archive; it cannot download a missing archive.
No URLs are inferred from old cache files. Default endpoint selection does not
guarantee availability, archive validity or successful full acquisition.

## Refresh or rebuild deliberately

Both commands require a ready new catalog. Their invocation is separate authority
for that operation; neither accepts setup's `--yes` switch.

```bash
lcats catalog refresh --url "$ARCHIVE_URL" --dry-run
lcats catalog refresh --url "$ARCHIVE_URL"
lcats catalog rebuild --dry-run
lcats catalog rebuild
```

Refresh conditionally validates cached originals when possible, then applies the
acquired archive using the lifecycle API. Identical bytes reuse the generation.
Offline refresh is rejected even on a cache hit. Rebuild is entirely local and
uses the retained active archive unless `--archive` is supplied.

A changed ebook count leaves a recoverable candidate and reports its ID with exit
2. Inspect that candidate using the [lifecycle API](../reference/gettenberg-lifecycle.md),
or deliberately repeat the operation with `--allow-count-change` after reviewing
the change. Earlier generations are retained. Setup approval never grants this
count-change permission. Dry-run describes intended operations; it does not parse
the archive or predict successful validation or final record counts.
