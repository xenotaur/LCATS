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
[gather with explicit sources](gettenberg-gather.md) for the complete workflow.
Legacy experimental helpers still exist; dependency removal is a later tranche.

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

## Use an explicitly chosen archive source

There is deliberately no default mirror in this tranche. Once you have chosen an
appropriate archive URL and permission to use it, substitute it for `$ARCHIVE_URL`:

```bash
lcats catalog setup --url "$ARCHIVE_URL" --dry-run
lcats catalog setup --url "$ARCHIVE_URL" --yes
```

The explicit URL permits its origin. Redirects to other origins need repeated
`--allow-origin https://chosen.example` arguments. Existing bounded acquisition
limits apply (256 MiB archive, 900-second acquisition budget, pacing and bounded
retries). Planning sends no requests. `--offline` overrides online authority and
can reuse a verified acquired archive; it cannot download a missing archive.
No URLs are inferred from old cache files. These commands do not constitute
qualification of a default operational mirror.

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
