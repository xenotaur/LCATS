# Move existing code to the internal gettenberg library

LCATS no longer installs `gutenbergpy` or a Git-pinned replacement. Use the normal
LCATS installation and `lcats gather` for smart first use. The CLI still asks
before creating a missing catalog; `--yes` supplies unattended approval, and
`--offline` forbids acquisition. See [gathering](gettenberg-gather.md).

For the detailed before/after behavior and the distinction between required
source integration and additional workflow choices, read
[why gettenberg changes gathering](../explanation/gettenberg-gather-changes.md).

## Track accepted adoption limitations

The [post-adoption backlog](../../project/development/gettenberg-post-adoption-backlog.md)
records the 13 known cleanup exclusions, 55 retained-notice cases, 12 specific body
changes and the measured qualification boundary accepted for replacement delivery.
It lists affected IDs, evidence and follow-up criteria. These are known limitations,
not claims that a corpus is editorially clean or that all configured inputs have
been measured. Adoption acceptance does not authorize corpus regeneration.

## Replace implicit access with explicit sessions

The old `gettenberg.api`, `cache`, `headers` and `metadata` modules are removed.
There is no SQL/API compatibility layer. Choose an existing catalog explicitly:

```python
# Example: catalog-query
from lcats.gettenberg import lifecycle
from lcats.gettenberg import catalog
from lcats.utils import genre

manager = lifecycle.CatalogManager("cache")
with manager.open() as library:
    record = library.get(84)
    ids = library.find_ids(catalog.Filters(languages=("en",)), limit=100)
    classification = genre.get_genre_by_id(84, catalog=library)
```

`library.get` returns a parsed record or `None`; its `ebook` contains ordered,
source-associated titles, contributors, subjects, languages and resource metadata.
Errors remain errors; missing data never triggers a text download or header
fallback. A missing catalog requires [explicit setup](gettenberg-preparation.md).
For a standalone candidate file use `catalog.Catalog(path)` in a context manager.
Advance `after_id` to the last returned ID to read another bounded page.

To acquire text, select a catalog resource with explicit routes, acquire original
bytes with `ResourceStore`, then [decode](gettenberg-decoding.md) and
[clean](gettenberg-cleanup.md) them. URLs found in metadata grant no network
permission. Do not replace this with guessed URL patterns or lossy decoding.

## Port old calls by responsibility

Use this map when updating code written against the pre-replacement LCATS API
(main baseline `22a739d2`). These are semantic migrations, not import substitutions.

| Old usage | Current equivalent and difference |
|---|---|
| `cache.ensure_gutenberg_cache()` / implicit cache setup | Prepare a catalog through the CLI, then own a `CatalogManager.open()` context. Library reads do not initialize or refresh it. |
| `api.get_etexts(languages="en", ...)` | `library.find_ids(catalog.Filters(languages=("en",)), limit=..., after_id=...)`; paginate explicitly. Returns ordered IDs rather than an unordered set. |
| `api.get_matching_rows()` / `extract_book_id(row)` | Query IDs, then `library.get(id)` for typed records. Old raw rows and SQL schemas are not supported. |
| `bookshelves=` / `downloadtype="text"` | Use `Filters(shelves=(... ,))`; MIME-format filtering/resource selection replaces the old download-type convention. There is no automatic one-to-one translation for `"text"`. |
| `api.get_metadata("title", id)` / `metadata.titles_for(...)` | `source.metadata(id).titles`, after checking for `None`. Ordered tuples replace sets; primary titles take precedence. |
| Author, alias, subject or language helpers | `metadata.authors`, `.aliases`, `.subjects`, `.languages` on the projection. Authors and aliases remain separate; the full record preserves contributor roles. |
| `api.load_etext(id)` followed by `strip_headers(...)` and decoding | `source.read(metadata)` returns original artifact, decoded text and cleanup evidence. Use `.cleaned.text` for the prepared Unicode text, not another decode/strip operation. |
| Header metadata fallback / cache skip mode | No automatic equivalent. Missing catalog metadata is explicit; a separate file-metadata reader belongs to the relevant gatherer. |
| `parser.gather_story(gatherer, id)` | Add keyword-only `source=source`; the `(id, path, rejection)` tuple remains. |
| `mass_quantities.gather_stories(ids)` | Add `source=source`; retains `(ready_paths, error_reasons)`. Use `gather_batch` when distinctions between skipped/refused/unavailable matter. |
| `mass_quantities.gather()` | Requires `source=source` and returns `BatchResult`; inspect `.ready`, `.written`, `.reused`, `.skipped`, `.refused`, `.unavailable`, and `.incomplete`. |

`Filters` combines dimensions with AND and values within each tuple with OR.
Exact matching preserves case; `search_ids` provides casefolded literal substring
search. Author filtering matches contributor names/aliases; the story projection
separately restricts authors to creator/author roles. Review selection differences
instead of assuming the old SQL query and new filters select identical records.
See [catalog reference](../reference/gettenberg-catalog.md).

## Construct a complete source for existing extraction code

This example requires an already prepared catalog at `cache`. It is offline and
only inspects metadata, so it does not download story text. Run from `lcats/`:

```python
# Example: source-session
from lcats.gatherers import gutenberg_source
from lcats.gettenberg import lifecycle
from lcats.gettenberg import resources

cache_dir = "cache"
manager = lifecycle.CatalogManager(cache_dir)
store = resources.ResourceStore(cache_dir)
routes = resources.GutenbergRoutes(
    "https://gutenberg.pglaf.org/",
    "https://gutenberg.pglaf.org/cache/epub/",
)
policy = resources.NetworkPolicy()  # Offline, including on a cache miss.

with manager.open() as library:
    source = gutenberg_source.GutenbergStorySource(
        library, store, routes=routes, policy=policy
    )
    metadata = source.metadata(84)
    if metadata is None:
        print("No catalog record for ebook 84")
    else:
        print(metadata.titles, metadata.authors, metadata.aliases)
        # Put existing extraction calls here while the catalog is open.
```

To inspect a cached story, add the following **inside that context**:

```python
# Example: inspect-story
from lcats.gatherers import parser

report = parser.inspect_story(84, source=source)
print(report["rejection"])
# report also includes body, metadata and provenance; no story is published.
```

To feed Kenny's own extraction function instead of LCATS's existing heuristics,
check `metadata is not None`, then use `prepared = source.read(metadata)` and pass
`prepared.cleaned.text` to that function. Preserve `prepared.provenance()` alongside
the result. A prepared text is not yet an extracted story. Do not run the old
Gutenberg header remover again or assume identical whitespace/title ordering.

For one LCATS output, add this inside the same open-catalog context. It writes
only to the separate `migration-output` directory; choose a fresh location when
comparing extraction changes:

```python
# Example: publish-story
from lcats.gatherers import downloaders
from lcats.gatherers import parser

gatherer = downloaders.DataGatherer("migration_preview", root="migration-output")
story_id, path, rejection = parser.gather_story(gatherer, 84, source=source)
```

For batch recovery and reporting, call
`mass_quantities.gatherer.gather_batch(ids, log_dir=..., source=source)` instead;
it uses `LCATS_DATA_DIR` for its output root, resolved when the gatherer is created.
Set that environment variable before calling it, and keep logs outside both data
and corpora roots. The catalog owner must outlive every source operation.

If acquisition is desired, explicitly replace `policy` with
`resources.NetworkPolicy(online=True, allowed_origins=("https://gutenberg.pglaf.org",))`.
A ready catalog does not authorize network requests, and opening this source does
not set up the catalog. Redirects to other origins require their own explicit
permission. This example selects a known route, not an availability guarantee.
See [acquisition policy](gettenberg-resources.md).

## Preserve failure distinctions and test both cold and warm runs

- An absent record or ordinary story ineligibility produces a rejection; it is
  not the same as failed acquisition or cleanup.
- Direct `source.read`, `inspect_story` and `gather_story` calls can raise structured
  resource errors. Per-item continuation lives in the mass **batch** boundary,
  which continues only cleanup refusals and terminal HTTP 404 responses.
- Other operational failures still abort. Do not recreate the old broad exception
  catch merely to make all inputs appear processed.
- A reused output has not been re-extracted or requalified. Compare your changes
  in a fresh, isolated output directory, then repeat with warm outputs to verify
  reuse. Preserve existing data and caches instead of deleting them for a test.
- Curated HTML gatherers retain their own downloader, decoding and publication
  behavior. They have not inherited mass gathering's atomic publication or
  per-item recovery just because both use `DataGatherer`.

Use fixed inputs to compare selection, title/author-derived bucket names, body
text, metadata/provenance, errors, and output reuse independently. A larger success
count alone does not establish narrative preservation. The accepted limitations
above remain separate follow-ups.

For a new source with per-file metadata, start with the
[new gatherer tutorial](../tutorials/create-file-metadata-gatherer.md). Neither
`GutenbergStorySource` nor the mass parser is a required interface for all gatherers.
The shared gather-result contract in
[GPA-E](../../project/development/gettenberg-post-adoption-backlog.md#gpa-e--shared-gather-result-contract-across-collections)
is a future follow-up, not an API available in this release.

## Reuse or remove old caches deliberately

The old SQLite database is not a valid new catalog. An already downloaded
`rdf-files.tar.bz2` can be supplied to `lcats catalog setup --archive PATH --yes`
without downloading it again. Retain the old cache until you have verified the
new catalog and any needed historical comparisons. Old filename-based text files
lack the new source receipts and are not silently treated as verified blobs.

`lcats clean --cache-only` explicitly deletes known new and old caches, including
all catalog generations and source receipts. Stop other LCATS processes first;
this command is not a concurrent retention service. It preserves configured root
directories/symlinks and does not follow nested symlinks when clearing contents.
Targeted `lcats clean mass_quantities` and `--data-only` leave caches intact.
`CatalogManager.cleanup()` only prunes abandoned candidates/publication temporaries;
it keeps published generations and retained archives.

## Use the maintained research entry points

- Notebooks 01 and 02 are small, offline HTML/catalog/cleanup examples.
- Notebook 15 and its Python companion call
  `analysis.corpus.reconciliation.compare_collections(left, right)`. They compare
  canonical `bucket/story.json` files by source URL without a catalog. Duplicate
  URLs stay visible; equality is unknown when there is no unique pair. No corpus
  output is rewritten automatically.
- `python KMo/genre.py CATALOG_SQLITE CORPUS_ROOT` reports genre counts using one
  read-only catalog. Missing records classify as Unclassified; invalid source URLs
  and catalog errors fail explicitly.
- Experiment 05 accepts `--cache-db` pointing to a new catalog. It no longer
  probes old SQL tables or extracts rules from Python source. Its archived results
  remain historical observations.

The upstream-internal notebooks 10 and 14 moved byte-for-byte to
`experiments/10_gettenberg_qualification/legacy-notebooks/`. They are unsupported
historical diagnostics requiring their recorded checkout/environment. Their
replacement regression checks use real RDF/SQLite fixtures. The historical
`probe_legacy.py` runner likewise requires the old checkout for measurements;
importing it or asking for help does not load the retired dependency.

See [CI cache maintenance](gettenberg-ci-maintenance.md) for the maintained
workflow and its approval boundaries.
Dependency removal alone does not claim that live full-catalog, whole-corpus or
release qualification has completed.
