---
id: PROP-WORLDCON-FAST-PATH-ANNOTATION
type: design_proposal
title: Fast-Path Annotation Pipeline for the Worldcon 2026 Paper Dataset
status: adopted
created_on: 2026-08-05
updated_on: 2026-08-06
implementation_status: not_started
implemented_by: []
supersedes: []
superseded_by: null
related_design:
  - lcats/project/focus/current_focus.md
  - lcats/project/design/event-role-world-genre-target-reconciliation.md
  - lcats/project/design/proposals/adopted/lcats-story-bucket-layout/00_proposal.md
  - lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md
  - lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md
  - lcats/project/design/backlog.md
  - lcats/project/work_items/proposed/WI-ASSESS-0031.md
---

## Summary

Adds an `lcats annotate` command that runs the two extractors already
mature enough to trust at scale — genre detection (`lcats assess`) and
scene/sequel segmentation (`scene_analysis`) — over a small per-genre
story subset, writing `genre.json`/`scenes.json` sidecars plus a
per-bucket `README.md` into `data/` bucket directories, with `lcats
promote` copying and validating them into `corpora/`. This is a
deliberately narrower, faster path to a real Worldcon 2026 paper dataset
within ~10 days, explicitly bypassing ERW event/relation extraction,
which a parallel session found too slow/costly/unreliable for this
timeline.

## Background / Motivation

The paper needs a real, usable dataset soon. The ERW event/relation
extractor — the pipeline's most feature-complete output — was just shown
(this project's own parallel session, ~$110 spent) to be too expensive,
slow, and unreliable to finish in time. That track continues
independently: `PROP-LCATS-PILOT-COST-SUSTAINABILITY` has landed and
been adopted, and a local/hybrid-model fallback is being
built in parallel (`PROP-ERW-LOCAL-MODEL-EVALUATION`, infra merged via
PR #219, methodology since refined via PR #222/#223 — still `proposed`,
currently holding the `claude-opus-4-8` default). Neither of those
efforts blocks this proposal, and this proposal does not duplicate or
depend on them — it exists precisely so the paper has a dataset even if
neither lands in time.

Two other extractors are mature enough to use as-is today: `lcats
assess` (genre + specials detection, has a real CLI and strict-mode tool
schema) and `scene_analysis.make_segment_extractor` (one LLM call per
story, not ERW's ~26-call fan-out). Neither currently has a first-class
way to persist its output as a reusable sidecar in the corpus layout,
and neither has been run at even small scale without hitting a
truncation bug. This proposal designs the annotation command and its two
prerequisite fixes so the fast path is actually usable, not just
theoretically faster.

Genre scope is deliberately the current 4 `VALID_GENRES` (science
fiction, horror, western, romance) — `WI-ASSESS-0031`'s extension to the
8-genre Worldcon target is already underway in a parallel session and is
not duplicated here; this proposal's Step 7 (expand to 8 genres) is
explicitly gated on that work landing first.

## Prior Art Check

### Duplication search
- In-repo: No existing `lcats annotate` command, no prior design
  proposal for it. `discovery.py`'s own docstrings already anticipate
  `audit.json`/`scenes.json`/`events.json` sidecar shapes but no code
  writes them yet.
- Sibling repos: None identified.
- External libraries: None identified — this is a thin orchestration
  layer over two already-built in-repo extractors, not a
  general-purpose need.
- Recommendation: Proceed.

### Demand search
- Work items: None found requesting `lcats annotate` directly.
  `WI-ASSESS-0031` (4→8 genre extension) is related but non-overlapping
  scope, explicitly deferred to Step 7 here.
- Proposals: None found requesting this directly.
  `PROP-LCATS-PILOT-COST-SUSTAINABILITY` and `PROP-ERW-LOCAL-MODEL-EVALUATION`
  are related context (see Background/Motivation) but address the ERW
  track this proposal deliberately routes around, not this proposal's
  own scope.
- Backlog (`project/design/backlog.md`): No entry for `lcats annotate`
  itself, but a directly relevant, currently-unscoped bug was found:
  **`lcats stats` uses the broad `find_corpus_stories` selector instead
  of the canonical `find_json_files`/bucket-only selector** — confirmed
  2026-08-02, no WI yet. Once this proposal's `lcats annotate` starts
  writing `genre.json`/`scenes.json` sidecars into bucket directories,
  `lcats stats` will silently start counting those sidecars as
  additional stories, corrupting exactly the per-genre statistics this
  plan's Step 8 needs. This proposal folds fixing that selector into its
  own implementation plan rather than leaving it as a landmine triggered
  by its own output.
- Recommendation: Proceed; fold the `lcats stats` selector fix into this
  proposal's implementation plan (see Design Decision 7).

## Design Decisions

### Decision 1: Sidecar scope this sprint

Options: (a) genre + scenes + specials-audit sidecars together, matching
the original plan's example list; (b) genre + scenes only, deferring the
audit sidecar.

**Chosen: (b).** The specials/mojibake audit sidecar's own design (JSON
vs. the user's `prosoc`-repo markdown/YAML precedent) is a separate,
not-yet-made decision, and whether a per-story audit belongs in this
sprint at all is still open. Building only `genre.json` and
`scenes.json` this round avoids speculatively committing to an
undesigned format. *(User decision, recorded 2026-08-05.)*

### Decision 2: Sidecar format

**Chosen: JSON**, matching `discovery.py`'s own anticipated shape and
the existing `find_json_files`/`iter_collection_story_files` selector
convention. No real alternative was considered — this is following
established precedent, not an open choice.

### Decision 3: Per-bucket `README.md`

**Chosen:** `lcats annotate` itself writes/updates a `README.md` in each
story's bucket directory summarizing `story.json` plus whatever
sidecars exist, after writing that bucket's sidecars — not a separate
command. A `.md` file is never matched by any JSON-only selector
(`find_json_files`, `iter_collection_story_files`), so this is purely
additive: no discovery/promote/stats changes are needed to accommodate
it.

### Decision 4: `lcats promote` sidecar validation

Options: (a) trust `lcats annotate` to validate its own JSON before
writing, leave `promote`'s `survey_collection` untouched; (b) extend
`survey_collection` to also validate sidecar JSON validity as part of
the release gate.

**Chosen: (b).** `promote` is the actual release gate to `corpora/`; a
malformed `genre.json`/`scenes.json` should block promotion the same
way a mojibake finding does, not rely solely on the writer having gotten
it right. *(User decision, recorded 2026-08-05.)* Exact validation depth
(schema check vs. parse-only) is left to work-item design.

### Decision 5: Two prerequisite bug fixes, lifted to the shared level

- `assess.py:328`'s hardcoded `max_tokens=2048` in `assess_story()` must
  gain an override (parameter, or a higher default), fixed in
  `assess.py` itself — not worked around per-caller.
- `scene_analysis.py`'s `make_segment_extractor` has no `max_tokens`
  override at all (inherits the library's bare 4096 default), and — this
  proposal's original draft mis-cited a fix that does not actually
  exist: `run_pilot.py`'s `_segment_story()` calls
  `scene_analysis.make_segment_extractor(backend)` and `.extract(...)`
  with no `max_tokens` override of its own (verified directly against
  the current `experiments/03_cross_segment_relation_pilot/run_pilot.py`,
  correcting a review finding on this PR). The only existing precedent
  for overriding `max_tokens` on an extractor instance is
  `_build_erw_extractors`'s `extractor.max_tokens = _ERW_MAX_TOKENS`
  (same file), which applies to the five ERW extractors, not to
  segmentation. The fix must therefore be written fresh directly in
  `scene_analysis.py`'s `make_segment_extractor` (a parameter or a
  raised default), following that same override-pattern precedent, not
  lifted from anywhere.

Both are real, already-observed failures (confirmed this session on
real candidate stories), not speculative — `lcats annotate` would hit
them immediately at even small scale without these fixes.

### Decision 6: File discovery convention for `lcats annotate`

**Chosen:** `lcats annotate` iterates story buckets via
`discovery.iter_collection_story_files`, one collection directory at a
time — the same narrower bucket-only selector `promote`'s
`survey_collection` already uses, applied the same way `promote` applies
it: per collection, never directly against a multi-collection corpus
root. `iter_collection_story_files` only checks the immediate children
of the path it's given for a `story.json` (per its own docstring:
"Applies only one level of nesting relative to `collection_dir`");
called directly on a `data/`/`corpora/` root — whose immediate children
are collections, not story buckets — it silently yields nothing (review
finding, PR #226). `lcats annotate` must therefore enumerate collection
directories first (e.g. the immediate children of its `--source` root)
and call `iter_collection_story_files` once per collection, exactly
mirroring how `promote_collections` already drives `survey_collection`
per collection rather than across the whole root at once. `find_json_files`
remains the right tool only for call sites that genuinely need a single
recursive sidecar-safe sweep across an entire multi-collection root in
one call; `lcats annotate`'s per-collection loop does not need it.

### Decision 7: Fix `lcats stats`'s selector as part of this proposal's implementation plan

**Chosen:** yes, fold it in. `run_stats` currently calls
`discovery.find_corpus_stories` (broad) instead of `find_json_files`
(canonical), per the unscoped backlog finding above. This proposal's own
new sidecars are what will first trigger the bug in practice, and Step 8
(per-genre stats) depends on `lcats stats` being trustworthy — fixing
the one-line selector mismatch is cheap and directly unblocks this
proposal's own goal.

## Non-Goals

- Does not design or implement the specials/mojibake audit sidecar
  (Decision 1) — deferred to a later, separate decision.
- Does not implement `WI-ASSESS-0031`'s 4→8 genre extension — tracked
  and already underway in a parallel session; this proposal's Step 7
  only consumes that work once landed.
- Does not touch ERW event/relation extraction in any way — explicitly
  out of scope, per the parallel cost-sustainability finding. Does not
  depend on or duplicate `PROP-LCATS-PILOT-COST-SUSTAINABILITY` or
  `PROP-ERW-LOCAL-MODEL-EVALUATION`, even though both may land around
  the same time — this proposal exists so the paper has a dataset
  regardless of either's outcome.
- Does not adopt a schema-validation library or new dependency for
  sidecar validation (Decision 4) — depth of validation is left to
  work-item design, expected to be plain parse/shape checks.
- Does not change `lcats survey`'s CLI-level exclusion policy (the
  `DEFAULT_EXCLUDED_CHARS` vs. `excluded=set()` inconsistency) — noted
  as related context for Decision 4 but is `WS-SPECIALS-CLEANUP`'s
  scope, not this proposal's.

## Implementation Plan

Workstream-shaped (5+ pieces: two bug fixes, new CLI command, promote
validation extension, `lcats stats` selector fix, the actual per-genre
run + stats collection), mirroring how
`PROP-LCATS-PIPELINE-CHECKPOINTING` preceded
`WS-PIPELINE-CHECKPOINTING`. Suggested work items once adopted:

1. Fix `assess.py`'s `max_tokens` override and `scene_analysis.py`'s
   missing `max_tokens` override (Decision 5).
2. Build `lcats annotate`: writes `genre.json`/`scenes.json` +
   per-bucket `README.md`, using `iter_collection_story_files`
   (Decision 6), following `cli.py`'s existing subcommand-registration
   pattern.
3. Extend `lcats promote`'s `survey_collection` with sidecar validation
   (Decision 4).
4. Fix `lcats stats`'s file-discovery selector (Decision 7).
5. Run `lcats annotate` over the small per-genre analysis set; validate
   output; collect statistics (plan Steps 6 and 8), with Step 7's
   8-genre expansion gated on `WI-ASSESS-0031` landing.

## Cross-References

- `lcats/project/design/backlog.md` — `lcats stats` selector bug
  (Decision 7), specials exclusion-policy inconsistency (Non-Goals)
- `lcats/project/work_items/proposed/WI-ASSESS-0031.md` — 4→8 genre
  extension, gates Step 7 (already underway in a parallel session)
- `lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md`
  — related but independent ERW-track fallback effort; not a dependency
  of this proposal
- `experiments/03_cross_segment_relation_pilot/run_pilot.py` —
  `_build_erw_extractors`'s `extractor.max_tokens = _ERW_MAX_TOKENS` is
  the closest existing override precedent to follow (Decision 5); its
  `_segment_story()` has no override of its own, contrary to this
  proposal's original draft
- `lcats/src/lcats/analysis/corpus/discovery.py` —
  `iter_collection_story_files`/`find_json_files` selector convention,
  and `iter_collection_story_files`'s single-level-of-nesting docstring
  (Decision 6)
- `lcats/src/lcats/analysis/corpus/promote.py`'s `promote_collections` —
  precedent for per-collection iteration driving a per-collection
  selector (Decision 6)
- `lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md`
  — sibling proposal→workstream precedent for scope/structure

## Open Questions

- Exact `lcats annotate` CLI flags and story-subset selection criteria
  (how "a small set of stories per genre" is chosen) — left to
  work-item design.
- Exact stats collection approach (Step 8) — left to work-item design
  once Steps 1-6 land.
