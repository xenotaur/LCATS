# Live gathering and source contracts

## Command coordinator

`lcats.gatherers.main.run(names=None, dry_run=False, *, yes=False, offline=False,
catalog_archive=None, catalog_url=None, main_root=None, generated_root=None,
allow_origins=(), cache_dir=None)` returns `(message, exit_code)`. Success is 0;
input, catalog, resource and filesystem failures are 2. Completed batches with
unresolved cleanup refusals or unavailable story resources (HTTP 404) also return
2, with an explicit incomplete summary.
Earlier completed outputs
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
| Damaged original or failed strict decode | Abort; retain cached originals |
| Ambiguous boilerplate (`cleanup_refused`) | Record refusal; continue other inputs and collections; final CLI status 2 |
| Selected story resource returns HTTP 404 | Record unavailable item; continue other inputs and collections; final CLI status 2; no retry/fallback |
| Other acquisition failures, including HTTP 410 or offline misses | Abort; retain previous outputs; final CLI status 2 |

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

`mass_quantities.gather(*, source)` processes the configured collection and returns
`BatchResult`. `gather_batch(ids, log_dir=..., *, source)` returns the same report
for a supplied iterable. Its `ready` dictionary maps IDs to written/reused paths;
`skipped` maps ordinary exclusions to reasons; `refused` maps cleanup refusals to
reasons; `unavailable` maps HTTP 404 inputs to reasons. `incomplete` is true when
`refused` or `unavailable` is nonempty. `reused` maps IDs to existing output paths;
`written` returns the remaining ready paths newly published by this batch.
Ready counts partition unique IDs: an ID written then repeated in the same batch
remains written in the aggregate. `summary` distinguishes new writes from reuse
and labels observed 404s as download attempts, not global unavailability.
`http_404_attempts` counts actual failed attempts, including repeated input IDs;
`unavailable` still maps unique IDs. If omitted in manual construction, the summary
uses the unavailable-ID count for compatibility.
No editorial acceptance or fresh acquisition is implied. Existing three/four-argument
`BatchResult` construction still works; `unavailable` and `reused` default to new
empty dictionaries (a caller supplying only ready paths classifies them as written).

`gather_stories(ids, log_dir=..., *, source)` retains its historical two-dictionary
return: ready paths and error reasons (ordinary skips, cleanup refusals and
unavailable resources). All three entry points require an explicit source.
Only `cleanup_refused` and terminal `http_status` errors with structured status
404 continue; other operational exceptions propagate and the log records abortion.
`story_ready` retains that event name and adds `disposition: written|reused`.
Reuse does not revalidate contents, reacquire source bytes or rerun cleanup.
`story_failed` adds `disposition: skipped`.

`parser.gather_story(gatherer, id, *, source)` requires an explicit source and
shares selection, body/chapter/length extraction and normalization/override rules.
It retains its `(id, path, rejection)` tuple. `parser.gather_story_result` exposes
those fields as `story`, `path`, `rejection` plus a `disposition` of `written`,
`reused` or `skipped` for batch reporting. Atomic publication reports whether this
call wrote the file or preserved a concurrent writer's output; a race is reuse.
At that boundary CRLF and CR become LF; original bytes and decoder/cleanup evidence
retain physical line endings. The first primary title supplies the filename using the existing naming helper. There is no legacy acquisition fallback.

`parser.inspect_story(id, *, source)` returns JSON-compatible `gutenberg_id`,
`metadata`, `rejection`, `body` and `provenance`. It uses the same extraction rules
without writing a story. Missing/ineligible metadata returns a rejection without
acquiring text. Short/chaptered bodies remain in the report for inspection.
Eligible text uses the supplied source's explicit network/cache policy; operational
failures propagate. This replaces the old print-only debugging helpers.

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

## Cleanup refusal and operational logs

Source cleanup uses policy `gutenberg-boundaries-v3` and records its explicit
source/catalog/title context in provenance. The two corroborated terminal-notice
rules precede the unchanged migration-baseline body extractor. An ambiguous
envelope raises `ResourceDecodeError` with code `cleanup_refused`. Mass gathering
logs `story_cleanup_refused` with the ebook ID and reason, leaves that input
unpublished, and continues. It does not retry, weaken cleanup, or fall back to
another source. HTTP 404 transport failures are instead logged as
`story_source_unavailable`, with `story`, `reason`, `http_status`, `source_uri`,
`request_url` and `final_url`. The original request and final failed endpoint are
distinct when redirects occur. No error response is published to the source cache,
no story is emitted, and later inputs continue. This does not prove that an ebook
is absent on other endpoints or permanently unavailable. HTTP 410 is not included.
A `batch_summary` event retains ready/written/reused/skipped/refused/unavailable counts, `http_404_attempts`, and
an `incomplete` flag. `run_end` means iteration finished; it does not mean every
input was accepted. The CLI reports incomplete gathering with status 2 after
remaining selected collections run. Other operational failures still abort.
This is not an ineligible-story count or an editorial review outcome.

A run-log directory must be outside the configured data and corpora roots,
including resolved symlinks. This guard runs before gathering creates output and
also applies to installed wheels. Existing output reuse remains unchanged.
