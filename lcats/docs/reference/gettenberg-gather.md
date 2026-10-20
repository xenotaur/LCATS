# Live gathering and source contracts

## Command coordinator

`lcats.gatherers.main.run(names=None, dry_run=False, *, yes=False, offline=False,
catalog_archive=None, catalog_url=None, main_root=None, generated_root=None,
allow_origins=(), cache_dir=None, review_decisions=None)` returns `(message, exit_code)`.
Completed runs without review/refusals return 0; operational/input failures return 2;
completed batches with `needs_review` or `cleanup_refused` return 3. Earlier outputs
and partial logs are retained. Ordinary collection exclusions do not cause exit 3.
`review_decisions` is an explicit JSON file path (`--review-decisions` on the CLI),
valid only with `mass_quantities` selected. `--yes` never approves content. Collection
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
| Damaged original or failed strict decode | Abort with exit 2; retain cached originals |
| Ambiguous boilerplate | Record cleanup_refused, continue batch, exit 3 |
| Unresolved editorial/structural cues | Save separate review candidate, continue batch, exit 3 |

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
  damaged recognized envelopes are refused before body extraction.
- `StoryText.provenance()` is JSON-compatible: ebook ID, catalog archive SHA-256,
  catalog source URI, request/final URLs, original/receipt SHA-256, decode identity,
  encoding, cleanup policy version and diagnostics. It records derivation inputs,
  not a claim of whole-corpus equivalence.

`mass_quantities.gather(*, source, review_decisions=None)` and
`gather_stories(ids, log_dir=..., *, source, review_decisions=None)` return a
`gather_result.BatchResult`. Its `outcomes` tuple retains every completed
`GatherResult`; `counts`, `gathered`, `requires_attention` and `to_dict()` support
batch reporting. Review decisions are an ID-to-`ReviewDecision` mapping; IDs outside
the selection are errors. Selections are bounded to 100,000 entries.

`parser.gather_story(gatherer, id, *, source, review_decision=None, review_dir=...)`
returns a `GatherResult` with `gutenberg_id`, `status`, `path`, `reason`, `review_path`.

| Status | Meaning |
|---|---|
| `published` | A newly qualified story was atomically written. |
| `reused` | An existing output was preserved; no requalification is claimed. |
| `ineligible` | Metadata, short length or corroborated divided-work rule excludes it. |
| `needs_review` | Candidate saved separately; no accepted story output was created. |
| `cleanup_refused` | Batch caught an ambiguous-envelope refusal before extraction. |

Direct `gather_story` still raises the structured cleanup exception; the batch
converts only code `cleanup_refused` into that outcome. Other operational failures
abort and log `run_aborted_unexpected`. Per-input events are `story_<status>` with
ID, reason and output/review paths; these replace the ambiguous `story_ready` and
`story_failed` events. Runtime log/review roots must be outside data/corpora,
including explicit output roots and symlink aliases. The run log uses those
runtime guards in both editable checkouts and installed wheels.

`parser.inspect_story(id, *, source, review_decision=None)` returns JSON-compatible
`gutenberg_id`, `metadata`, `status`, `rejection`, `body`, `selected_span` and
`provenance`. Inspection writes no story or review queue file. Metadata exclusion
avoids text acquisition. `body` is always the full preserved candidate; the selected
span is a half-open Unicode-character range within that body, before normalization.
A reviewed selection never replaces the candidate in this report. `needs_review`
has no rejection: it is uncertainty, distinct from collection ineligibility.
Operational failures and stale decisions propagate. Existing publication reuse
bypasses acquisition unless an explicit decision was supplied; supplied decisions
are always validated, even when the existing output will ultimately be preserved.

## Publication readiness and reviewed decisions

`readiness.assess(body, chapter_assessment, *, titles=(), authors=(), aliases=())`
returns `Assessment(status, findings, exclusion, policy)` under
`publication-readiness-v1`. `to_dict()` exposes Finding-compatible kinds, warning
severity, half-open spans, messages and evidence. Spans address the exact candidate
body, not decoded source/wire bytes or normalized output.

The policy identifies explicit editorial notes (including ASCII frames), boundary
publication/production credits, bibliographies/advertisements, retained metadata
headings, illustration/Gutenberg labels and short uncertain opening labels. It
also routes ambiguous chapter evidence to review. Corroborated multi-work contents
or multiple distinct standalone numbered headings without conflicting editorial
cues support `divided_work`; <=10 split paragraphs remains `too_short`. These are
collection rules and bounded heuristics, not a guarantee of narrative purity.
A ready result means no unresolved findings under this policy. No detection deletes
text. In particular, uppercase signs and numbered advertisements are not alone
proof of narrative chapters. Genuine unnamed sections can remain `needs_review`.

Provenance adds `publication_readiness` containing the raw assessment, source-context
SHA-256, candidate SHA-256 and assessment SHA-256. Source context binds the ebook ID,
metadata projection and complete source provenance. A reviewed decision and selected
assessment/chapter evidence are retained alongside the original findings; the raw
assessment status can therefore remain `needs_review` while the inspection's resolved
status is `ready`. Existing normalization/overrides run after the approved selection.

Review candidates are immutable JSON under `logs/gather/review/mass_quantities/`,
with names `<id>-<report-hash>.candidate.json`, never `story.json`. The record has
`schema_version: 1`, `kind: gettenberg_review_candidate`, and the inspection `report`.
The hash covers the whole record. Repeated equal evidence is reused; corrupt or
conflicting existing evidence fails. Different sources/policies keep distinct files.
Queue files are historical evidence, not a live unresolved-count index: successful
later review does not delete old candidates. Use the latest batch outcomes/log.

`ReviewDecision.for_report(report, *, start, end, reviewer, rationale)` constructs
an explicitly requested decision after review. It performs no autonomous approval.
Serialize `dataclasses.asdict(decision)` in a JSON list for `--review-decisions`.
Each record contains `schema_version: 1`, `gutenberg_id`, `source_identity_sha256`,
`candidate_sha256`, `assessment_sha256`, `selected_start`, `selected_end`,
`selected_sha256`, `reviewer`, and `rationale`. Reviewers may be people or identified
agents; attribution is not an authenticated human signature.

`load_decisions(path)` rejects unknown/duplicate fields, duplicate IDs, invalid
hashes/types/spans and files over 8 MiB or 10,000 records. Current inspection
recomputes all identities and validates the selected substring. Drift fails visibly;
there is no fallback to approval by ID. A decision can resolve uncertain findings,
but cannot override metadata, short-story or corroborated divided-work exclusions.
Decisions made against historical decoded-cache evidence cannot be silently reused
for live original-byte sources: their source contexts differ.

## Conservative body boundaries

`gatherers.story_body.extract(text, titles, authors, aliases=())` returns a
`BodyExtraction` with `text`, `content_start`, `content_end`, `diagnostics` and
`policy_version`. Policy `opening-prefix-v1` selects a contiguous span after
normalizing CRLF/CR to LF. Offsets refer to this normalized **cleanup output**,
before corpus normalization or per-story overrides; they are not wire offsets.
`parser.body_of_text` delegates to this policy. Inspection and publication add
`body_extraction` to the existing source provenance.

Only whole catalog title/byline matches and explicitly recognized standalone
production credits or bracketed illustration labels advance the opening prefix.
A title/byline may span up to four adjacent paragraphs. The first unknown
paragraph ends the search permanently. A later repeated title, closing byline or
wrapped line beginning with “by” cannot discard preceding narrative. Unknown
opening prose remains visible, even when a recognizable title follows it.

A terminal plain Gutenberg end notice is removed only if its complete title and
author match catalog values. Wrapped notices are supported. Mismatched or
nonterminal notices remain. This is separate from gettenberg envelope cleanup,
whose policy is unchanged. Notes, footnotes, epigraphs, closing bylines, scene
separators and uncertain editorial material are retained, including ambiguous
“Illustrated by” prose. Diagnostics mark possible retained notes/unclassified
openings; they are not a complete editorial classification or acceptance signal.

`parser.assess_chapters(body, *, titles=(), authors=(), aliases=())` returns
JSON-compatible evidence under policy `metadata-aware-chapters-v1`.
`parser.chaptered(...)` returns its boolean decision. Inspection and publication
include `chapter_assessment` in provenance, with these fields:

| Field | Meaning |
|---|---|
| `chaptered` | Legacy heuristic signal; readiness decides whether it supports exclusion or needs review. |
| `paragraph_basis` | Indexes address `body.split('\n\n')` before corpus normalization. |
| `explicit_markers` | Contents/numbered-section indexes and historical scoring weights. |
| `possible_title_paragraphs` | Isolated short all-capital headings counted by the heuristic. |
| `ignored_metadata_paragraphs` | Complete catalog title/byline matches excluded from the weak heading heuristic. |

Metadata matching accepts the same case, wrapping, title/subtitle and inverted
name forms as body extraction, plus signature dashes and curly/straight quote
equivalence. Quote equivalence applies only to classification; it does not broaden
body-prefix deletion. Classification itself does not delete text.
Explicit contents and numbered sections retain their existing weights even when
their text matches metadata. A contents label on the first line of a paragraph
with at least two distinct entries corroborated by later standalone all-capital
headings is also explicit evidence (`contents_list`). These markers include
`supporting_paragraphs` indexes. An optional “By ...” attribution is separated from
the entry title. Mere following lines, duplicate entries, one matching heading,
or headings only before the list do not suffice. This remains a heuristic. The existing exception for exactly two unnamed
headings is unchanged. Other front matter can still cause false positives; the
paragraph evidence makes these inspectable.

These policies fix destructive heading searches and metadata false positives but
do **not** establish corpus readiness. Inspection exposes any rejection. Do not bulk regenerate an accepted corpus from
this unqualified candidate. Existing outputs are reused, not silently rewritten.

## Output and migration boundaries

Bucket slugs still use the existing title/author naming algorithm; per-story
overrides still receive that slug, not `story.json`. New JSON publication uses a
same-directory temporary file and atomic hard-link creation, preserving a concurrent
winner. Serialization failure leaves no partial output. The filesystem must support
hard links. This is file-content publication, not a power-loss durability promise.
Symlink or non-file output leaves are refused. Existing regular outputs are reused
without JSON validation; absent an explicit review decision, no source acquisition
is needed for reuse. Ancestor directories
are not a security sandbox.

`DataGatherer` resolves omitted data/cache roots at construction. Curated
`gather(*, offline=False, cache_dir=None)` functions pass policy to their existing
HTML cache at `<cache_dir>/resources`. They preserve current extraction and output
schemas. Their HTML decoding and publication behavior are not the new source API.

Expected differences from the legacy metadata path include stable RDF order,
creator/author-only projection, original catalog resource identity, strict decoding,
and explicit refusal of ambiguous boilerplate. Authored integration fixtures verify
body, bucket, filter, normalization and override behavior; no full corpus comparison
is claimed. Default endpoint observations do not establish full acquisition. The retired
helper API and external dependency have been removed; see the
[migration guide](../how-to/gettenberg-migration.md).
