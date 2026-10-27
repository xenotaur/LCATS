# Gettenberg/gather handoff for Kenny

## Concise summary

- **The goal is to remove LCATS’s dependency on `gutenbergpy`.** PR #534 replaces it with our internal `gettenberg` library, which manages Gutenberg metadata, downloads, caching, decoding, and boilerplate cleanup.

- **You were right that this is not a drop-in replacement.** `lcats gather` remains the command, but Python callers now pass an explicit source object containing the catalog, cache, download locations, and network policy. Some return types and cache formats also changed.

- **Authors and aliases remain separate.** The new metadata interface also distinguishes contributor roles and prefers primary titles. Different metadata or title ordering can affect story selection and filenames.

- **We reproduced your ebook 1367 failure.** The selected mirror returns HTTP 404. Mass gathering now logs that input as unavailable and continues with later stories, returning exit status **2** to indicate incomplete gathering. It does not recover 1367 through another mirror.

- **Error recovery is deliberately limited.** Missing resources returning 404 and ambiguous boilerplate cleanup continue per item in `mass_quantities`. Other operational failures still stop the run. This recovery has not been added to every HTML gatherer.

- **Existing stories are now preserved and reused before downloading or extracting again.** Consequently, rerunning gather will not apply your extraction fixes to existing outputs. The summary now distinguishes newly written stories from reused ones; zero observed 404s does not mean every download URL was checked.

- **The existing body-extraction heuristics were retained, but their inputs can differ.** New metadata, resource selection, strict decoding, and boilerplate cleanup can produce different stories even with unchanged extraction code. Broader editorial fixes are excluded from this PR.

- **Validation is substantial but bounded:** 2,979 tests pass, installed-package checks pass, and the live 1367 failure was reproduced without altering existing data. Known story differences and exclusions are documented; we are not claiming every configured story is downloadable or editorially clean.

- **For reconciliation, we should compare responsibilities rather than replace whole files.** Keep your extraction improvements, adapt them to the metadata/text interface, and explicitly reconcile error handling and output reuse. PR #534 is still awaiting our joint review and has not been merged to main.

## Report snapshot

**Prepared 2026-10-26 for team review of [PR #534](https://github.com/xenotaur/LCATS/pull/534).**
Candidate: `aab07b291ef63c98c3ec545a9e70e6c1ed624f61`; compared with main
`22a739d25c5a72359c1f8e37f54f9059876e6798`. The PR is awaiting joint review at this
snapshot. This report does not authorize main promotion or corpus regeneration.

## What we are delivering

An internally owned gettenberg library replaces gutenbergpy and the old LCATS
wrapper. The existing `lcats gather` command remains, but the Python interfaces,
cache format, source preparation and some workflow behavior change. This is
**not a drop-in replacement achieved by changing an import**. Some changes are
required by the chosen source contract; others are deliberate improvements.

## Your 1367 report: reproduced and fixed at the batch boundary

Your reported mirror URL returned a real HTTP 404 in isolated checks using both
the source checkout and installed wheel. Each made one GET, using a tiny catalog
built from local RDF and empty temporary output/source-cache directories.

Mass gathering now records a structured HTTP 404 as an unavailable input,
continues later inputs, preserves successful outputs and reports incomplete
status **2**. Cleanup refusals likewise continue per item. Neither publishes the
failed story. There is **no alternate-mirror/format fallback**, and 1367 itself
has not been recovered. The request URL and status are logged.

Other failures—including 410/403, exhausted transient failures, strict decode,
policy/integrity and filesystem errors—still abort. The old parser caught broadly
around `load_etext`, so this is not exact old error-policy equivalence. Per-item
continuation applies to `mass_quantities`; curated HTML gatherers have not gained
that recovery loop. [Repair evidence][404-evidence]; [current error boundary][errors].

The subsequent warm run reported zero 404s because it reused the existing Findelkind
output before attempting acquisition. We now report **newly written** versus
**existing outputs reused**, plus **download attempts returning HTTP 404**.
New writes can use cached sources; reuse does not revalidate or re-extract a story.
Both live checks preserved the original story hash and catalog size/mtime.
[Live reproduction and reporting evidence][reporting-evidence].

Expected diagnostics leaking from unit tests were also captured per test, leaving
ordinary print debugging available. No global test-output suppression was added.
[Per-test diagnostic fix](https://github.com/xenotaur/LCATS/commit/059f22ba1243d896f564d48611616887b4841b55).

## What makes this more than a drop-in replacement

| Area | What to account for in your code |
|---|---|
| Source ownership | The caller opens a catalog and supplies `GutenbergStorySource(catalog, store, routes=..., policy=...)`. The CLI manages this for normal gathering. |
| Metadata | `source.metadata(id)` returns projected ordered fields or None. Authors and aliases remain separate; primary titles are preferred. Catalog/metadata errors do not silently trigger text-header lookup. |
| Text | `source.read(metadata)` returns prepared text and provenance. Source selection, strict decoding and conservative cleanup replace the old byte/header path; the input to unchanged extraction can differ. |
| Calls/returns | `parser.gather_story(..., source=source)` keeps its three-value tuple. `gather_stories(..., source=source)` keeps its two-dictionary pair. `mass_quantities.gather(source=source)` now returns `BatchResult`, not just successful paths. |
| Cache | Old SQLite/text-cache layouts are not verified new stores. Reuse the old RDF archive for setup if available; retain old caches deliberately for comparisons. |
| Output | Existing regular story files are preserved before acquisition; new writes are atomic and do not replace a concurrent winner. A warm rerun will not apply your new extraction fixes to existing files. |
| Provenance/logs | New JSON adds `metadata.gettenberg`; `metadata.url` is the selected source URI, not a constructed URL. Mass `story_downloaded` events become `story_ready` with written/reused disposition. Review consumers keyed by exact URLs/event names. |
| Other collections | Eleven curated gatherer wrappers only forward offline/cache options. Their extraction logic is unchanged; they do not need the Gutenberg catalog merely because their source URL is on Gutenberg. |

[Source and metadata contract][source]; [parser/result API][results];
[batch API][batch]; [migration guide][migration].

## What we have deliberately kept separate

The retained parser's 46 other top-level functions, including body heuristics,
are unchanged in an AST comparison against the pinned main base. Normalization,
overrides and the mass story-ID map also have no diff. Source text/metadata can
still change outcomes: unchanged heuristics are not a guarantee of identical bodies.
There is no canonical `corpora/` diff. The broader editorial/gather work preserved
in PR #524 is excluded from this promotion; reconciliation with your code is a
separate task once it is available.

Some changes were not forced by the library swap: smart setup/planning,
workflow-wide offline controls, atomic output preservation, helper consolidation
and result/reporting organization. We should not describe the entire diff as
unavoidable source plumbing.

## Evidence and remaining limitations

At this snapshot, **2,979 tests pass**, installed cold/repeat CLI checks pass,
all 167 package files match source/wheel/installation, and all four hosted checks
are green. Deterministic three-input tests verify continuation past a failed
middle input; the live 1367 experiment separately verifies the actual endpoint.

The historical 1,659-input qualification measured **1,646 ready, 13 refused,
zero unattempted** using cached sources. It is not a fresh all-5,492-ID yield
claim. The accepted exclusions, 55 notice-only additions, 12 body effects and
qualification limits remain in the [post-adoption backlog][backlog]. This delivery
does not certify editorially clean corpora. [Acceptance record][decision].

## Suggested reconciliation discussion

1. Agree on the source boundary: metadata, prepared text, provenance and structured failures.
2. Compare your changes by responsibility, especially around `gather_story`, failure handling and output reuse; avoid replacing whole files wholesale.
3. Test extraction changes with separate fresh output directories as well as warm reruns. Preserve your existing data and caches.
4. Review any desire for broader per-item recovery or missing-source fallback as an explicit separate policy decision.

The detailed explanation is in `lcats/docs/explanation/gettenberg-gather-changes.md`
on PR #534. This report is intended to be shareable as a standalone Markdown file;
all supporting links below use immutable repository revisions.

[source]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/gutenberg_source.py#L82
[batch]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/mass_quantities/gatherer.py#L46
[errors]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/mass_quantities/gatherer.py#L163
[results]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/parser.py#L1435
[reporting-evidence]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/experiments/10_gettenberg_qualification/results/gettenberg-reporting-20261026/README.md
[404-evidence]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/experiments/10_gettenberg_qualification/results/gettenberg-http404-20261026/README.md
[backlog]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/project/development/gettenberg-post-adoption-backlog.md
[decision]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/project/development/gettenberg-delivery-decision.md
[migration]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/docs/how-to/gettenberg-migration.md
