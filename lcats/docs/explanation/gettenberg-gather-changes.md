# Why gettenberg changes the gathering workflow

This explanation separates required source integration from additional workflow
choices. It describes the candidate in PR #534, not a general redesign of gather.
For migration steps use [the migration guide](../how-to/gettenberg-migration.md);
for exact APIs use [the source reference](../reference/gettenberg-gather.md).
The [team handoff](../../project/development/gettenberg-kenny-handoff.md) is the
short, independently shareable version.

## Comparison and status

Snapshot: 2026-10-26, candidate `aab07b291ef63c98c3ec545a9e70e6c1ed624f61`,
compared with main base `22a739d25c5a72359c1f8e37f54f9059876e6798`.
[PR #534](https://github.com/xenotaur/LCATS/pull/534) was open for team review at
this snapshot. Nothing here authorizes merging, publishing or regenerating a
canonical corpus. Code citations below are pinned to these revisions so they
remain useful after later changes.

The candidate replaces the external gutenbergpy dependency and LCATS's old
wrapper with an internally owned catalog/acquisition library. It preserves the
`lcats gather` entry command, but is **not a drop-in Python API, SQL schema, cache,
failure-policy or generated-story replacement**. Those are distinct compatibility
questions; retaining the command spelling does not establish the others.

## What the diff measures

Gathering plus the top-level CLI touches 20 product files: 901 inserted and 489
deleted lines at this snapshot. Eleven files are only three added/one removed
lines forwarding `offline` and `cache_dir` through curated gatherers. Nine shared
files contain the substantive integration and organization changes. The CLI diff
also contains the catalog command, so its full size is not solely gathering work.
[Example forwarding change][wrapper]; [shared HTML plumbing][html].

A responsibility-based classification gives approximately four direct integration
families, four additional functional families and three API/reporting families.
This is an explanatory grouping, not a percentage of necessary lines: one hunk
can implement several responsibilities, and multiple architectures could satisfy
one requirement. “Required” below means required by our chosen contract, not
logically necessary for every possible replacement of gutenbergpy.

| Family | Classification | Why it exists; what could have differed |
|---|---|---|
| Own catalog lifetime, construct and pass a source | Direct integration | The selected catalog, resource store, routes and network policy need an owner. Parameter names and the call hierarchy are choices. [Construction][dispatch] |
| Project metadata into extraction inputs | Direct integration | New records need translation into titles/authors/aliases/subjects/languages. A compatibility adapter could have retained field-by-field calls. [Projection][metadata] |
| Consume acquired/decoded/cleaned text and provenance | Direct integration | Gathering must consume the selected source contract instead of the retired byte/header helpers. Strict decoding and cleanup policy were themselves design choices. [Acquisition][read] |
| Translate failures at the batch boundary | Direct integration | A source failure must not accidentally turn a formerly recoverable item into batch abortion. Which failures continue and which abort is an explicit policy choice. [Handling][errors] |
| Smart setup, requirements and dry-run planning | Additional functional contract | Preserves agreed first-use behavior while avoiding catalog setup for unrelated sources. Not required by a bare dependency substitution. [Planning/setup][setup] |
| Workflow-wide offline/cache flags | Additional functional contract | Once the flags apply to all selected collections, HTML gatherers must obey them too. Explains the eleven forwarding changes. [Enforcement][offline] |
| Existing-output reuse and atomic publication | Additional behavior | Avoids unnecessary acquisition and protects previous/concurrent outputs. Changes mass gathering's overwrite behavior; not cosmetic. [Reuse][reuse], [publication][publication] |
| Runtime path resolution and log-root protection | Additional operational safeguard | Makes configured roots effective at construction and protects data/corpora when installed outside a checkout. [Paths][offline], [log guard][log-roots] |
| Consolidated inspection/debug helpers | Optional organization | Old helpers needed migration or retirement, but their replacement by one inspectable report was not forced. [Inspection][inspect] |
| BatchResult and detailed story outcomes | Optional API mechanism | Supports distinct skips, refusals, missing sources, writes and reuse. Another representation could implement the same behavior. [Batch][batch], [story result][results] |
| Console text, event labels and reporting layout | Presentation plus observability | Wording and removed diagnostic prints are closest to cosmetic. Accurate counters and dispositions require actual instrumentation. [Events][logs] |

Lazy plotting imports are part of making gather/catalog planning avoid unrelated
font-cache writes, rather than a visual style change. [CLI import boundary][lazy].
A smaller implementation was possible; the entire diff should not be attributed
to the explicit source object.

## Before and after the source boundary

The old wrapper exposed `get_metadata(field, id)` and `load_etext(id)`, with
library/cache access behind those calls. Text acquisition tried gutenbergpy and
then a raw downloader on failure, returning cached bytes. A metadata header-parse
path also existed; it was not a universal recovery path for every SQL exception.
[Old text API][old-api]; [old metadata branch][old-metadata].

Now the orchestrator opens a catalog and constructs `GutenbergStorySource` from
that catalog, a resource store, routes and network policy. `metadata(id)` is a
catalog projection and can return None. `read(metadata)` selects a qualified
plain-text representation, acquires original bytes, decodes and cleans them, and
returns text with provenance. Catalog lookups do not silently fetch text to infer
missing metadata. [Source contract][source].

Author names and aliases remain separate. Contributors are filtered by author
roles; translators are not indiscriminately put into authors. Primary titles are
preferred, alternatives are a fallback, and exact strings are deduplicated in RDF
order. This is a semantic projection, not just a new spelling of the old query.
Different metadata/order can affect eligibility, title selection, filename slugs
and the text supplied to title/author-sensitive extraction. [Projection][metadata].

The new store retains original bytes and receipt/source identity. The old database
and filename-only text cache are not silently accepted as new verified caches.
An existing RDF archive can be reused to build the new catalog. Preservation of
old story outputs is independent of migration of old source-cache entries.
[Cache migration][migration].

## Python interfaces and persisted output

| Interface | Previous behavior | Candidate behavior |
|---|---|---|
| `gettenberg.api/cache/headers/metadata` | Old wrapper modules and upstream-backed helpers | Retired; no SQL/API compatibility layer |
| `parser.gather_story(gatherer, id)` | Implicit provider; returns `(id, path, rejection)` | Requires `source=...`; retains that three-value tuple |
| `parser.gather_story_result(...)` | Absent | Detailed result with `story`, `path`, `rejection`, `disposition` |
| `mass_quantities.gather()` | Returns a successful-path dictionary | Requires `source=...`; returns `BatchResult` |
| `gather_stories(ids, ...)` | Successful-path/error-reason pair | Requires `source=...`; retains the pair, including refusal/unavailable reasons |
| `gather_batch(ids, ...)` | Absent | Structured ready/skipped/refused/unavailable outcomes and reuse/attempt accounting |
| Curated `gather()` functions | No workflow policy parameters | Optional `offline=False`, `cache_dir=None`; no source object/catalog requirement |
| Story JSON | Existing name/author/body/metadata shape; constructed Gutenberg URL | Retains that shape, adds `metadata.gettenberg` provenance and uses actual selected source URI for `metadata.url` |
| Mass ready log event | `story_downloaded`, even for a returned path | `story_ready`, with written/reused disposition; skipped events remain `story_failed` |

[Parser APIs/output][results]; [batch APIs][batch]; [source identity][provenance].
Consumers keyed by the literal old URL string or old log event name need review.
A source URI and a requested mirror URL are different identities; provenance
retains both. Updating an import alone cannot migrate these assumptions.

## What does and does not change story extraction

The 46 retained top-level parser functions other than `gather_story` are
AST-identical between the two pinned revisions, ignoring source locations.
This includes the existing body extraction/repair heuristics. The single-story
orchestration and old debug helpers are where that file changes. Normalization,
overrides and the configured mass story-ID map have no diff in this comparison.
There is also no canonical `corpora/` diff.

That does **not** guarantee identical stories. The old path used header stripping
followed by UTF-8 decoding with `errors="replace"`. The new source uses strict
supported decoding and conservative boilerplate cleanup, refusing ambiguous
recognized envelopes. The parser then normalizes physical newline conventions
before calling the retained body extractor. Metadata, source representation or
boundary text can therefore change the result of unchanged heuristics.
[Old preparation][old-parser]; [new source preparation][read]; [parser boundary][inspect].

These are approved source semantics, not consequences that an explicit object
would automatically impose. A broader editorial/gather redesign is preserved
separately in PR #524 and is not promoted by #534. Reconciliation with Kenny's
extraction work remains a separate task.

## Failure handling: a deliberate, limited compatibility repair

The old parser caught `Exception` specifically around `api.load_etext`; that was
not a catch-all around metadata, cleanup, extraction and filesystem operations.
The new source initially allowed some formerly per-item acquisition problems to
abort gathering. Kenny's ebook 1367 report exposed this integration regression.
[Old catch boundary][old-parser].

The candidate now applies this policy to **mass_quantities**:

| Outcome | Batch action | Final CLI status if nothing else aborts |
|---|---|---|
| Ordinary metadata/body exclusion | Record skip; continue | 0 unless another input is unresolved |
| Structured `cleanup_refused` | Record refusal; publish no story; continue | 2 |
| Terminal HTTP 404 | Record unavailable ID, endpoint and attempt; continue | 2 |
| Other operational failure | Abort, preserving earlier outputs/logs | 2 |

HTTP 410 and 403, exhausted transient errors, invalid decoding, integrity/policy
errors and filesystem failures are not silently converted into skips. There is
no automatic alternate mirror/format or retry for 404. This is narrower than the
old download-only broad catch, not complete failure-policy equivalence.
[Current boundary][errors]; [CLI status][dispatch].

This per-item continuation does not extend to every curated HTML gatherer.
Their acquisition implementation remains separate; they gained offline/cache
propagation, not the mass gatherer's error isolation. [Shared HTML workflow][html].

## Reuse and publication are substantive workflow choices

Previously, eligible mass stories proceeded through acquisition/extraction and
an ordinary `open(..., "w")` write. Now an existing regular output at the derived
slug is returned before acquisition/cleanup. No content validation is implied;
a changed title can derive a different slug. New publication uses a temporary
file plus exclusive hard-link creation, preserving a concurrent winner and
refusing symlink/non-file destinations. [Old write][old-write]; [current reuse][reuse];
[publication implementation][publication].

Consequences for development and review:

- A warm rerun does not apply new extraction fixes to existing outputs.
- Zero observed 404s/refusals does not establish source availability or fresh cleanup success.
- Newly written outputs can use cached source bytes; writes are not network-download counts.
- Ready counts partition unique IDs into written/reused; a repeated written ID stays written in the aggregate. `http_404_attempts` counts attempts, while `unavailable` retains unique IDs.
- Use separate output/cache roots for controlled comparisons; do not clear a shared corpus to test a single acquisition.

## Kenny's 1367 case and evidence boundaries

Two isolated live checks on 2026-10-26, one source-tree and one final installed
wheel, each made one GET to `https://gutenberg.pglaf.org/cache/epub/1367/pg1367.txt`.
Both returned 404; the CLI finished status 2 with no story or cached error body.
The existing Findelkind hash and original catalog size/mtime were preserved.
The user's earlier warm run reused Findelkind and therefore observed zero 404s.
The fix preserves batch progress; it does not recover the missing representation.
[Full reproduction and reporting evidence][reporting-evidence].

The candidate has 2,979 passing canonical tests, installed cold/repeat fixture
checks and matching committed-source/wheel/installed package hashes. All four
hosted checks passed at `aab07b29`; these are snapshot facts, not a promise about
future heads. Earlier frozen-source evidence measured 1,646 ready, 13 refused
and zero unattempted across 1,659 inputs. It is not fresh publication/availability
coverage for all 5,492 configured IDs. Accepted 55 notice-only additions, 12 specific
body effects and the 13 exclusions remain documented in the [adoption backlog][backlog].

## Reconciliation recommendation

Agree on the metadata/text/provenance and error boundary first. Kenny's extraction
work can consume that boundary without adopting every helper layout or result
representation. Compare his behavior against both the pinned base and candidate,
then port changes by responsibility rather than overwriting whole parser/gatherer
files. Preserve author/alias separation, source identities, batch progress and
output protection while reviewing extraction fixes separately. Include fresh-output
and reused-output runs; acceptance of existing bytes does not test new extraction.
This document explains the implemented choices; it proposes no new implementation
or relaxation of the accepted delivery criteria.

[old-api]: https://github.com/xenotaur/LCATS/blob/22a739d25c5a72359c1f8e37f54f9059876e6798/lcats/src/lcats/gettenberg/api.py#L27
[old-metadata]: https://github.com/xenotaur/LCATS/blob/22a739d25c5a72359c1f8e37f54f9059876e6798/lcats/src/lcats/gettenberg/api.py#L160
[old-parser]: https://github.com/xenotaur/LCATS/blob/22a739d25c5a72359c1f8e37f54f9059876e6798/lcats/src/lcats/gatherers/parser.py#L1401
[old-write]: https://github.com/xenotaur/LCATS/blob/22a739d25c5a72359c1f8e37f54f9059876e6798/lcats/src/lcats/gatherers/parser.py#L1477
[source]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/gutenberg_source.py#L82
[metadata]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/gutenberg_source.py#L109
[read]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/gutenberg_source.py#L129
[provenance]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/gutenberg_source.py#L54
[setup]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/main.py#L64
[dispatch]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/main.py#L114
[offline]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/downloaders.py#L151
[html]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/gatherlib.py#L110
[wrapper]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/sherlock/gatherer.py#L93
[batch]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/mass_quantities/gatherer.py#L46
[errors]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/mass_quantities/gatherer.py#L163
[logs]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/mass_quantities/gatherer.py#L202
[log-roots]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/mass_quantities/gatherer.py#L23
[inspect]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/parser.py#L1385
[results]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/parser.py#L1435
[reuse]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/parser.py#L1469
[publication]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/gatherers/story_output.py#L9
[lazy]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/src/lcats/cli.py#L371
[reporting-evidence]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/experiments/10_gettenberg_qualification/results/gettenberg-reporting-20261026/README.md
[backlog]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/project/development/gettenberg-post-adoption-backlog.md
[migration]: https://github.com/xenotaur/LCATS/blob/aab07b291ef63c98c3ec545a9e70e6c1ed624f61/lcats/docs/how-to/gettenberg-migration.md
