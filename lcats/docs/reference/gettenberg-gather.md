# Live gathering and source contracts

## Command coordinator

`lcats.gatherers.main.run(names=None, dry_run=False, *, yes=False, offline=False,
catalog_archive=None, catalog_url=None, main_root=None, generated_root=None,
allow_origins=(), cache_dir=None)` returns `(message, exit_code)`. Success is 0;
input, catalog, resource and filesystem failures are 2. Earlier completed outputs
are retained. Metadata/extraction skips do not make the whole run fail. Collection
selection and metadata configuration are checked before setup or execution.
The CLI spells roots `--gutenberg-main-root` and `--gutenberg-generated-root`.

| Input / state | Behavior |
|---|---|
| Curated-only selection | No catalog construction, setup or inspection |
| Metadata-dependent selection | Default PGLAF roots, or a complete explicit pair |
| Missing catalog | Default archive or explicit source, plus interactive approval or `--yes` |
| Ready catalog | Reuse pinned generation, no prompt or implicit refresh |
| `--dry-run` | Local plan only; no writes, requests, consumers or prompts |
| `--offline` | New store and curated HTML cache both refuse acquisition |
| Existing output | Reuse regular file before source acquisition; no validation/replacement |
| Damaged original, failed strict decode, ambiguous boilerplate | Abort; retain cached originals |

A dry-run can successfully report blocked preparation; it is not a prediction of
successful execution. Selected default or explicit resource/archive URLs permit their own origins;
additional origins use `--allow-origin`. These network controls apply to the new
Gutenberg store; curated HTML retains its existing HTTP implementation with an
offline acquisition guard. This is not a general plugin or arbitrary URL command.

## CLI source profile

| Role | Default |
|---|---|
| Catalog archive | `https://www.gutenberg.org/cache/epub/feeds/rdf-files.tar.bz2` |
| Main ebook root | `https://gutenberg.pglaf.org/` |
| Generated ebook root | `https://gutenberg.pglaf.org/cache/epub/` |

`gettenberg.sources_cli` resolves this static profile only for CLI workflows
requiring metadata. A local archive suppresses the default archive URL. An
explicit URL replaces it. Both resource roots replace the default pair; exactly
one is an input error. The library's preparation, routing and acquisition APIs
remain explicit and offline by default. No mirror discovery, failover, implicit
refresh, origin wildcard or human ebook-page fallback is added.

Dry-run displays catalog source, both roots, permitted origins and whether first
setup approval is needed. Offline always forbids requests even though configured
origins remain visible. Catalog setup uses the same default archive; status and
local rebuild select no remote source, and refresh still requires an explicit URL.
The default is based on bounded endpoint observations, not a full-download or
availability guarantee. Acquisition limits and integrity checks still apply.

## Catalog-backed extraction source

`GutenbergStorySource(catalog, store, *, routes, policy=NetworkPolicy())` in
`lcats.gatherers.gutenberg_source` uses an already-open pinned catalog and explicit
`GutenbergRoutes`. The caller owns the catalog's lifetime. Construction does not
prepare a catalog or fetch text. Default network policy is offline.

- `metadata(id)` returns immutable `StoryMetadata`, or `None` for an absent ID.
  It retains the complete ebook. Primary titles are preferred, with alternatives
  used only when primary titles are absent. Creator/author roles supply names and
  aliases; translators and other contributors are not promoted to authors.
  Exact duplicates are removed in RDF order. Subjects/languages retain source
  order. No header metadata fallback or legacy database query is attempted.
- `read(metadata)` returns `StoryText` containing the selected source URI, original
  artifact, strict decoded text and cleanup result. Only qualified plain-text
  resources are selected, preferring declared UTF-8. It does not try HTML or
  guessed download URLs on failure. Marker-free text is accepted; ambiguous or
  damaged recognized envelopes are refused before heuristic extraction.
- `StoryText.provenance()` is JSON-compatible: ebook ID, catalog archive SHA-256,
  catalog source URI, request/final URLs, original/receipt SHA-256, decode identity,
  encoding, cleanup policy version and diagnostics. It records derivation inputs,
  not a claim of whole-corpus equivalence.

`mass_quantities.gather(*, source)` and `gather_stories(ids, log_dir=..., *, source)`
require an explicit source. The latter returns successful paths and per-story skip
reasons. Operational failures propagate and the run log records abortion.
`story_ready` means newly published or reused, avoiding a false download claim.

`parser.gather_story(gatherer, id, *, source=None)` shares the existing selection,
body/chapter/length extraction and normalization/override logic. At that extractor
boundary, CRLF and CR become LF, matching the former header-stripper behavior;
original bytes and decoder/cleanup evidence retain physical line endings. A supplied source
uses the new path. Omitting it retains legacy experimental behavior until that
separate migration; importing the parser alone does not load `gutenbergpy`.

## Output and migration boundaries

Bucket slugs still use the existing title/author naming algorithm; per-story
overrides still receive that slug, not `story.json`. New JSON publication uses a
same-directory temporary file and atomic hard-link creation, preserving a concurrent
winner. Serialization failure leaves no partial output. The filesystem must support
hard links. This is file-content publication, not a power-loss durability promise.
Symlink or non-file output leaves are refused. Existing regular outputs are reused
without JSON validation; no source is needed to re-read them. Ancestor directories
are not a security sandbox.

`DataGatherer` resolves omitted data/cache roots at construction. Curated
`gather(*, offline=False, cache_dir=None)` functions pass policy to their existing
HTML cache at `<cache_dir>/resources`. They preserve current extraction and output
schemas. Their HTML decoding and publication behavior are not the new source API.

Expected differences from the legacy metadata path include stable RDF order,
creator/author-only projection, original catalog resource identity, strict decoding,
and explicit refusal of ambiguous boilerplate. Authored integration fixtures verify
body, bucket, filter, normalization and override behavior; no full corpus comparison
is claimed. Default endpoint observations do not establish full acquisition. Legacy helper migration and
external dependency removal remain WI-GETTENBERG-0008.
