---
id: PROP-LCATS-STORY-BUCKET-LAYOUT
type: design_proposal
title: Per-Story Bucket Directory Layout for LCATS Corpus Storage
status: proposed
created_on: 2026-07-30
updated_on: 2026-07-30
implementation_status: not_started
implemented_by: []
supersedes: []
superseded_by: null
related_design:
  - lcats/project/design/flat_story_layout_migration_impact_report.md
  - lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md
  - lcats/docs/reference/corpus-promotion.md
  - lcats/docs/reference/gather-overrides.md
---

## Summary

Adopts a staged expand-contract migration (Fowler's Parallel Change pattern)
from LCATS's current flat per-collection story storage
(`data/<collection>/<story>.json`) to per-story bucket directories
(`data/<collection>/<story>/story.json`), resolving the four open design
questions left by `flat_story_layout_migration_impact_report.md`, and
closing two additional gaps this session's follow-up analysis found: an
unaudited identity-collapse site in gather-time overrides, and a promotion
gate that doesn't check layout correctness.

## Background / Motivation

`flat_story_layout_migration_impact_report.md` audited LCATS's package and
tests and found 16 sites depending on the flat layout, concentrated in
discovery/loading, writer, identity/output, and test surfaces. It concluded
migration is feasible in a short staged chain but left four questions open:
what canonical identity should replace filename-stem fallback, how
discovery should distinguish a canonical story file from sibling JSON
artifacts, whether dual-layout support should be permanent or temporary, and
how output schema should represent identity once `story_file` stops being
unique.

This is more than a documentation gap: `PROP-LCATS-PIPELINE-CHECKPOINTING`
(adopted 2026-07-30) independently arrived at the same per-story-directory
mental model for its own checkpoint pattern and explicitly defers this
migration as separately-scoped work its own design "would extend cleanly"
into once it exists
(`lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md:268-275`).
Resolving this design now unblocks that cross-reference rather than leaving
it as an indefinite forward pointer.

A follow-up audit this session, scoped beyond the original report's
package-and-tests boundary, found the identity-collapse problem (Risk #1 in
the original report — `file_path.stem` becoming the literal string
`"story"` for every file) recurs at a site the original 16-item inventory
didn't cover: gather-time per-story overrides are keyed by filename stem
(`lcats/docs/reference/gather-overrides.md:29`,
`lcats/src/lcats/gatherers/downloaders.py:249`). It also found that `lcats
promote`'s existing survey gate
(`lcats/src/lcats/analysis/corpus/promote.py:27`) checks only for mojibake,
not layout correctness, so a Stage 2 writer bug would reach the `corpora/`
release snapshot undetected. Both are addressed as acceptance criteria
within this proposal's staging, not as new stages.

## Prior Art Check

### Duplication search
- In-repo: No existing implementation.
  `flat_story_layout_migration_impact_report.md` is the audit this
  proposal acts on, not an implementation. `PROP-LCATS-PIPELINE-CHECKPOINTING`'s
  Non-Goals (`00_proposal.md:268-275`) explicitly name this migration as
  future, separately-scoped work its own pattern anticipates.
- Sibling repos: None identified.
- External libraries: None applicable — an internal storage-layout
  convention, not a capability a library provides. The migration *approach*
  follows Martin Fowler's Parallel Change (expand-contract) pattern
  (https://martinfowler.com/bliki/ParallelChange.html).
- Recommendation: Proceed.

### Demand search
- Work items: None found in `project/work_items/proposed/`.
- Proposals: None found in `project/design/proposals/proposed/` (this is
  the first proposal on this topic).
- Backlog: No `project/design/backlog.md` exists in this repo.
- Recommendation: No action — proceed; nothing to close/link.

## Design Decisions

### Decision 1: Migration strategy

Options considered:
- Single atomic PR — all 16+ sites, tests, and fixtures changed at once.
- Staged expand-contract (read-path, then write-path, then convergence) —
  each stage independently testable and revertible.
- Permanent dual-layout support — never retract flat-layout compatibility.

**Chosen: staged expand-contract**, per Fowler's Parallel Change pattern and
matching the impact report's own recommendation
(`flat_story_layout_migration_impact_report.md:172-192`). A single atomic
PR stacks all 16+ sites and 2,207 lines of test changes into one review
pass with no interim validation point. Permanent dual-layout support never
resolves the report's own Risk #3 (over-broad recursive JSON discovery) and
was not supported by the source audit either.

### Decision 2: Canonical story identity

Options considered:
- Keep `file_path.stem` fallback (current) — collapses to the literal
  string `"story"` for every story once the writer moves to
  `<story>/story.json`.
- Directory slug as primary identifier.
- Metadata-only title (from JSON content).
- New explicit `story_id` field added to the schema.

**Chosen: directory slug as primary identifier.** Stable, human-legible,
already unique per collection today (it's the current flat filename stem),
and requires no schema migration of existing story content. Metadata title
is mutable and not guaranteed unique; an explicit `story_id` field is the
more robust long-term answer but requires a schema addition this proposal
doesn't need to force. `story_file` (`lcats/src/lcats/analysis/corpus/cli.py:53`,
`lcats/src/lcats/analysis/corpus/output.py:105-106`) stops being used for
identity.

### Decision 3: Discovery predicate

Options considered:
- Keep broad recursive `*.json` matching (current,
  `lcats/src/lcats/analysis/corpus/discovery.py:65`).
- Restrict to a canonical filename, `story.json`, only.
- Schema-sniff JSON files to determine which are stories.

**Chosen: canonical filename `story.json` only**, following the
single-canonical-manifest convention (`package.json`, `Cargo.toml`,
`pyproject.toml`). Schema-sniffing is fragile and slow at scale; broad
matching is exactly the ambiguity the report's Risk #3 warns about once
story directories can contain non-story JSON artifacts (analysis outputs,
overrides, etc.).

### Decision 4: Dual-layout window duration

Options considered:
- Permanent dual-layout read support.
- A window bounded to this migration's own staging, explicitly retracted
  once complete.

**Chosen: bounded window**, but **retraction is gated on the tracked corpus
migration, not on Stage 3's code merge.** A fresh checkout currently
contains 1,868 tracked `corpora/<collection>/<story>.json` files and zero
nested `story.json` files (verified via `git ls-files corpora/`). This
proposal's own Non-Goals correctly exclude the actual production `lcats
gather` + `lcats promote` run that would convert that tracked content — it's
a release-time human action, not something a design proposal performs. But
that means Stage 3 cannot retract flat-layout *read* support in the same PR
that lands its other convergence work: doing so would make `survey`/`stats`/
`assess` stop discovering the release snapshot entirely until the separate
corpus migration happens, an outage with no code-level trigger to prevent
it. Stage 3 therefore ships in two parts: the convergence work (fixtures,
tests, docs, promotion validation) lands first with dual-layout read support
still active; retraction of that support is a distinct, explicit follow-up
step, gated on confirming the tracked `corpora/` snapshot has actually been
migrated (via the deferred gather+promote action) — not bundled into the
same merge. Fowler's own caution on Parallel Change is that an expand phase
which never contracts becomes permanent debt, so the retraction step is
still required and tracked, just sequenced correctly against the content it
depends on.

### Decision 5: Output schema identifier column

Options considered:
- Repurpose `story_file`/`filename` identifier semantics in place.
- Add a new `story_dir`/`story_slug` column alongside the existing ones.

**Chosen: add a new column.** Repurposing `story_file`'s meaning silently
breaks existing TSV consumers that parse it; a new column is non-breaking
and makes the human-facing identifier change explicit in the schema itself
(`lcats/src/lcats/analysis/corpus/output.py:180-184`).

### Decision 6: Promotion validation

Options considered:
- Rely on `lcats promote`'s existing mojibake survey gate
  (`lcats/src/lcats/analysis/corpus/promote.py:27`) as sufficient
  validation.
- Add a one-time explicit end-to-end gather-then-promote validation step,
  required before the first real post-migration promote.
- Make canonical-layout validation a standing part of `lcats promote`
  itself, on every run.

**Chosen: standing validation in `lcats promote` itself**, not a one-time
step. A one-time pre-promotion check does not close the gap on any later
run: `CollectionSurveyResult.clean`
(`lcats/src/lcats/analysis/corpus/promote.py:56-59`) returns `not
self.findings`, so a collection where `discovery.find_corpus_stories`
returns zero canonical stories has `findings=()` and is reported `clean`
regardless — `_copy_collection` (`promote.py:156-160`) then copies it
wholesale. A writer regression or a stale flat collection that slips past
Stage 2/3's fixes would therefore still reach `corpora/` undetected after
the initial one-time validation passes once. `survey_collection` must
reject (not silently pass) a `story_count == 0` collection, and
`promote_collections` must treat that as a blocking condition alongside
existing mojibake findings — implemented in Stage 2 or 3 as a `promote.py`
code change, not documented only as a Stage 3 acceptance checklist item.

### Decision 7: Overrides identity site

The gather-time overrides mechanism keys per-story fixes by filename stem
(`lcats/docs/reference/gather-overrides.md:29`), derived at
`lcats/src/lcats/gatherers/downloaders.py:249` as
`story_id=os.path.splitext(filename)[0]`. **Chosen fix:** thread the
canonical story name (Decision 2's directory slug) into this call site as
part of Stage 2, rather than letting `story_id` be re-derived from the new
leaf filename (`"story"`) — the same collapse as Decision 2's core problem,
at a fourth site the original impact report didn't inventory.

### Decision 8: Additional flat-layout writer sites

`DataGatherer.ensure`/`download` (Decision 7's site) is not the only
production writer. `parser.gather_story()`
(`lcats/src/lcats/gatherers/parser.py:1468-1476`) independently constructs
`file_path = os.path.join(path, file_name)` and writes JSON directly to it
— it calls `gatherer.ensure(file_name)` beforehand but does not use its
return value for the write path, so migrating `DataGatherer.ensure` alone
does not change this site's behavior.
`lcats/src/lcats/gatherers/mass_quantities/gatherer.py:40-54`'s
`gather_stories()` calls `parser.gather_story()` for every story in
`storymap.SINGLE_STORIES` — LCATS's mass-quantities single-stories
collection. Left unmigrated, this collection keeps producing flat files
that Stage 3's canonical-only discovery (Decision 3) would then omit
entirely. **Chosen fix:** Stage 2 migrates `parser.gather_story()`'s write
path alongside `DataGatherer.ensure`, including updating its own parser
tests — not treated as covered by the `downloaders.py` change alone.

## Non-Goals

- Does not implement `lcats gather` incremental/restartable checkpointing.
  `PROP-LCATS-PIPELINE-CHECKPOINTING` (adopted 2026-07-30) already covers
  this pattern in general and states it "would extend cleanly to a future
  per-story-directory layout if/when that migration happens"
  (`00_proposal.md:268-275`); retrofitting it to `lcats gather`
  specifically is that proposal's own deferred, separately-scoped future
  work, not this one's.
- Does not fix hardcoded flat-layout paths in
  `lcats/notebooks/12_extract_scenes.ipynb` and `13_clean_corpus.ipynb`.
  Real, but lower urgency (last touched 2026-04-19) — a needed follow-on,
  scoped separately so it's fixed once against the final layout.
- Does not fix the non-recursive glob bugs in
  `experiments/02_llm_backend_comparison/run_comparison.py:57` and
  `smoke_test.py:109`, or the stem-collision output-naming bug in
  `experiments/03_cross_segment_relation_pilot/check_segmentation_reliability.py:193`.
  Real bugs with a worse (silent) failure mode than the notebooks, and more
  pressing given `experiments/03` is actively worked — but still a separate
  follow-on for the same reason: fix once, after this layout is final.
- Does not decide whether `notebooks/` and `experiments/` implementation
  code should be librarized into the installable package with unit test
  coverage. A separate, larger architecture question, deserving its own
  design pass.
- Does not perform the actual production `lcats gather` + `lcats promote`
  run migrating real corpus content. That is a release-time human action
  per `corpus-promotion.md`, out of scope for a design proposal.

## Implementation Plan

Workstream-sized: three work items matching the three stages, recommended
as a `/lrh-workstream` once this proposal is adopted.

1. **Stage 1 — Read-path compatibility.** Dual-layout-tolerant discovery
   and identity logic (Decisions 2-3); add a canonical story-file selector;
   dual-layout tests without changing writer output yet.
2. **Stage 2 — Write-path migration.** `DataGatherer.ensure`
   (`lcats/src/lcats/gatherers/downloaders.py:216`) **and**
   `parser.gather_story()` (`lcats/src/lcats/gatherers/parser.py:1468-1476`,
   Decision 8) both write to `<collection>/<story>/story.json`, with parser
   tests updated alongside; fix the overrides `story_id` derivation
   (Decision 7, `downloaders.py:249`); update output identifier semantics
   (Decision 5); add standing zero-story rejection to `lcats promote`
   (Decision 6).
3. **Stage 3 — Convergence and validation.** Normalize tests/fixtures/docs
   to the new layout. Ships in two parts, not one merge: (a) convergence
   work — fixtures, tests, docs, the standing promote validation from Stage
   2 — with dual-layout read support still active; (b) a distinct follow-up
   that retracts dual-layout support (Decision 4), gated on confirming the
   tracked `corpora/` snapshot (1,868 flat files, 0 nested, as of this
   proposal) has actually been migrated via the separately-scoped
   gather-then-promote action.

## Cross-References

- Audit: `lcats/project/design/flat_story_layout_migration_impact_report.md`
- Related, complementary proposal:
  `lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md`
- Promotion procedure: `lcats/docs/reference/corpus-promotion.md`
- Gather overrides mechanism: `lcats/docs/reference/gather-overrides.md`
- Key sites: `lcats/src/lcats/stories.py:51-52`,
  `lcats/src/lcats/analysis/corpus/discovery.py:65`,
  `lcats/src/lcats/gatherers/downloaders.py:216,249`,
  `lcats/src/lcats/gatherers/parser.py:1468-1476`,
  `lcats/src/lcats/gatherers/mass_quantities/gatherer.py:40-54`,
  `lcats/src/lcats/analysis/corpus/cli.py:53`,
  `lcats/src/lcats/analysis/corpus/output.py:105-106,180-184`,
  `lcats/src/lcats/analysis/corpus/promote.py:27,56-59,156-160`

## Open Questions

- Exact `story_dir`/`story_slug` column name and TSV schema version-bump
  policy — left to work-item design.
- Whether the overrides file format itself should key by directory slug (a
  schema change to `lcats/gatherers/overrides/<collection>.json`) or
  whether Decision 7's fix at the call site is sufficient on its own — left
  to work-item design.
- Relative priority and timing between the deferred `experiments/` fix and
  `notebooks/` fix (this proposal's Non-Goals recommend both happen after
  this migration lands, so they're fixed once) — left to future scoping.
