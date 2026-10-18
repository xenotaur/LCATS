# Move existing code to the internal gettenberg library

LCATS no longer installs `gutenbergpy` or a Git-pinned replacement. Use the normal
LCATS installation and `lcats gather` for smart first use. The CLI still asks
before creating a missing catalog; `--yes` supplies unattended approval, and
`--offline` forbids acquisition. See [gathering](gettenberg-gather.md).

## Replace implicit access with explicit sessions

The old `gettenberg.api`, `cache`, `headers` and `metadata` modules are removed.
There is no SQL/API compatibility layer. Choose an existing catalog explicitly:

```python
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

For story extraction, construct `gatherers.gutenberg_source.GutenbergStorySource`
using the open catalog, resource store, routes and policy, then pass it explicitly:

```python
from lcats.gatherers import parser

report = parser.inspect_story(84, source=source)
# Inspect report["rejection"], ["metadata"], ["body"] and ["provenance"].
result = parser.gather_story(gatherer, 84, source=source)
```

`inspect_story` may acquire/cache eligible text according to the supplied policy,
but never publishes a story. Use an offline policy for read-only inspection of
already cached sources. `gather_story` preserves existing output and applies the
same story eligibility/extraction rules. See [source contracts](../reference/gettenberg-gather.md).

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
