---
resolution: null
blocked_reason: null
blocked: false
id: WI-SEGMENT-0069
title: Investigate segmentation alignment failures beyond whitespace mismatches
type: investigation
status: proposed
priority: high
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams: []
related_design:
  - lcats/project/work_items/resolved/WI-SEGMENT-0068.md
  - lcats/project/work_items/proposed/WI-EVENT-0033.md
depends_on:
  - WI-SEGMENT-0068
blocked_by: []
expected_actions:
  - edit_file
  - create_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - widen_search_range_without_distribution_data
  - reintroduce_full_document_fallback
acceptance:
  - "A live smoke-test re-run (real API, matching WI-EVENT-0033's own verification cohort/method) with per-failure diagnostic capture (see Required Change 1) classifies every observed alignment_error into a small number of named failure categories, each backed by at least one concrete, cited example (real file/position/paragraph-id data, not a description alone)"
  - "The distribution across categories is reported with real counts (e.g. N of M failures were paragraph-mis-numbering vs. genuinely-absent-anchor vs. other), not just anecdotal examples"
  - "A clear recommendation is made for each category: fix now (with a concrete, safe design), defer with a named reason, or accept as an inherent LLM-reliability floor -- grounded in why WI-SEGMENT-0059's prior full-document-fallback rejection does or doesn't apply to each category"
  - "The investigation is recorded as a design doc under lcats/project/design/, following WI-EVENT-0028's precedent for investigation-type work items"
  - "check_segmentation_reliability.py persists enough per-failure detail (the pre-alignment raw segments, or equivalent) that a future investigator can analyze a captured failure without re-running a live LLM call to reproduce it"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/project/design/
  - experiments/03_cross_segment_relation_pilot/check_segmentation_reliability.py
---

## Summary

`WI-SEGMENT-0068` fixed one specific class of segmentation alignment
failure (a whitespace/newline-only mismatch between an LLM-provided
anchor quote and the real source text). A live smoke-test re-run after
that fix landed confirmed it genuinely helped -- exclusion dropped from
100% to 70% -- but 70% is still worse than the original 65%
`parsing_error`-only baseline, and `alignment_error` remains the
dominant cause. This item investigates the *remaining* alignment
failures, which live diagnostic sampling (2026-08-19, this session)
already shows are **not** the same whitespace-mismatch class, and are
not obviously one root cause either.

## Problem / Context

**Prior art check:**
- *Duplication search:* No existing WI investigates alignment failures
  beyond the whitespace-mismatch class `WI-SEGMENT-0068` fixed --
  confirmed via `grep -rl "alignment" project/work_items/` and a
  `backlog.md` search. `WI-SEGMENT-0059` (resolved) fixed a third,
  distinct, already-closed issue (paragraph-collapse on single-newline
  source text).
- *Demand search:* Not literally required by any existing acceptance
  criterion (review finding, PR #319): `WI-EVENT-0033`'s own criterion
  asks specifically for a measured reduction in the `parsing_error`
  rate, which the `tool_schema` migration guarantees structurally --
  `parsing_error` is set to `None` unconditionally on that code path
  (`llm_extractor.py:445`), regardless of whether alignment succeeds or
  fails. So `WI-EVENT-0033` is not formally blocked by this
  investigation (no `depends_on`/`blocked_by` edge links them), and
  this item does not add one -- that is a separate, explicit decision
  for whoever closes `WI-EVENT-0033` out, not something this WI's own
  creation should silently impose. This item exists as an independent
  follow-up: the live smoke test run to verify `WI-EVENT-0033`'s
  criterion is what surfaced this gap, even though the criterion itself
  doesn't require investigating it. No `backlog.md` entry yet; this
  WI's creation is the first place this finding is recorded.

**Evidence, gathered via live diagnostic sampling this session** (real
API calls against `claude-haiku-4-5-20251001`, capturing each failing
segment's raw pre-alignment anchor text and claimed paragraph IDs via a
monkey-patched `result_aligner`, since neither `extract()`'s return
value nor `check_segmentation_reliability.py`'s persisted output
retains this detail on failure -- see Required Change 1):

1. **Paragraph mis-numbering, large margin.** `mass_quantities/calling_the_empress__smith`:
   a failing segment's `end_exact` was **verbatim, real text**, confirmed
   present in the story at character position 5126 -- inside the
   story's real **paragraph 18**. The model claimed `end_par_id=11`,
   giving `align_segment` (`text_segmenter.py:208-209`) a search range
   of `[1889, 3982)` that doesn't contain position 5126 at all. The
   anchor text is correct; the model's own paragraph count is wrong by
   7 paragraphs.
2. **Paragraph mis-numbering, narrow margin.** `mass_quantities/problem_in_solid__smith`:
   a different failing segment's `end_exact` was real text at position
   8227, while the claimed `end_par_id=52` gave a range ending at
   `hi=8225` -- outside by only 2 characters. A materially different
   shape of the same general problem (claimed paragraph ID doesn't
   bound the real text), but by a margin small enough that it might
   have a different, more tractable explanation (e.g. a
   paragraph-boundary off-by-one) than case 1's large miss.
3. **Anchor genuinely absent from the document.** `mass_quantities/the_last_days_of_l_a__smith`:
   a failing segment's `end_exact` (`'Come home, come home,\n    Ye who
   are weary,\n    Come home."'`) does not appear anywhere in the real
   story text at all -- not exactly, not after whitespace
   normalization (`body.find(end_exact) == -1` against the full
   document, not just the search range). This looks like the model
   fabricating or badly misquoting content, not a search-range or
   whitespace problem `find_anchor_in_range` could ever resolve.
4. **`start_exact` itself unresolvable** (a second instance of the
   pattern in case 1/2, this time on the start anchor rather than the
   end): `mass_quantities/calling_the_empress__smith`, a different
   segment in a different sample, `start_exact` not found anywhere in
   its claimed `[lo, hi)` range at all.

These four data points already span at least two, probably three,
distinct underlying causes -- this is not a single bug with one fix,
unlike `WI-SEGMENT-0068`. Jumping straight to a code change (e.g.
widening the search range, or falling back to a full-document search)
risks repeating `WI-SEGMENT-0059`'s own documented mistake: an earlier
version of this alignment code's full-document fallback "produced
spurious, overlapping segment boundaries with no error signal" when it
guessed instead of failing cleanly. This item's job is to characterize
the failure distribution with enough real samples to know whether (and
which) categories have a safe fix, before anyone proposes one.

## Scope

- Improve diagnostic persistence so failures can be studied after the
  fact, not just live.
- Run a real smoke-test sample large enough to classify failures into
  named categories with real counts, not just the four hand-collected
  examples above.
- For each category, determine whether a safe fix exists, and if so
  sketch (not implement) its design.
- Record findings and a recommendation as a design doc.

## Non-Goals

- Does not implement any alignment-algorithm fix itself -- this is an
  investigation, per its `type`. A follow-up deliverable WI (or
  WI-SEGMENT-0068-style narrow fixes, one per confirmed-safe category)
  is the natural next step once a category's fix is actually designed.
- Does not re-investigate or re-verify `WI-SEGMENT-0068`'s own fix --
  already confirmed working: the specific whitespace-mismatch case it
  targeted no longer reproduces, and the overall smoke-test exclusion
  rate dropped from 100% (before the fix) to 70% (after). (Not cited as
  evidence here: `parsing_error` dropping to 0% -- review finding, PR
  #319 -- that metric is `None` unconditionally on the `tool_schema`
  code path regardless of alignment outcome, so it's tautological as
  evidence about an alignment-specific fix; it only demonstrates
  `WI-EVENT-0033`'s own `tool_schema` migration worked, a separate
  claim.)
- Does not widen `find_anchor_in_range`'s search range, or reintroduce
  any form of full-document fallback search, without first confirming
  via real distribution data that doing so is safe for the specific
  category it would apply to (see `forbidden_actions`).
- Does not investigate `make_semantics_extractor` or
  `make_doc_classification_extractor` (`WI-EVENT-0033`'s other two
  extractors) -- neither has `result_aligner`/`result_validator`, so
  neither is exposed to this alignment-specific failure class at all.

## Required Changes

1. **Add diagnostic persistence for alignment failures.**
   `check_segmentation_reliability.py` currently persists `raw_output`/
   `extracted_output` from `extract()`'s own return value, which
   `JSONPromptExtractor.extract()` clears to `None`/`""` on an
   alignment failure by design (`llm_extractor.py:479-490`,
   `WI-SEGMENT-0059`) -- so a captured failure currently has zero
   diagnostic detail for later analysis. Add a way to capture the
   pre-alignment raw segments (e.g. the same `result_aligner`
   monkey-patch pattern used for this WI's own investigation, made
   into a real, reusable option in the script) so a future run's
   failures are analyzable without a fresh live call.
2. **Run a real, adequately-sized smoke sample** and classify every
   `alignment_error` outcome into named categories (at minimum: anchor
   text real but outside claimed paragraph range; anchor text absent
   from the document entirely; any other pattern found), each with a
   real count and at least one cited concrete example. Per this
   project's own established practice for stochastic LLM-call
   investigations, don't rely on a single run -- use multiple samples
   or a larger single sample large enough that the category counts are
   meaningful, not anecdotal.
3. **For the paragraph-mis-numbering category**, investigate whether
   the model's paragraph counting correlates with anything observable
   (document length, paragraph density, a specific paragraph-marking
   convention in the indexed prompt) that could inform a safe,
   narrowly-scoped fix -- versus concluding it's inherent model
   unreliability with no code-level fix available.
4. **For the anchor-absent-from-document category**, determine whether
   this is better characterized as a prompt-design gap (the model
   isn't being asked clearly enough to quote verbatim) versus an
   inherent LLM-reliability floor not fixable via this pipeline's code
   at all.
5. Write up findings as a design doc under `lcats/project/design/`,
   following `WI-EVENT-0028`'s precedent for investigation-type work
   items -- distribution data, per-category recommendation, and an
   explicit determination of whether any follow-up deliverable WI is
   warranted (and for which categories).

## Acceptance Criteria

(see `acceptance` frontmatter above)

## Validation

- `lrh validate`
- `scripts/test` (confirm no regression from the diagnostic-persistence
  change to `check_segmentation_reliability.py`)
- Real smoke-test run(s) against `claude-haiku-4-5-20251001`, as
  described in Required Change 2

## Risk Notes

- This is real-money API spend (the same script `WI-EVENT-0033` and
  `WI-SEGMENT-0068` already used, ~1 call/story) -- get explicit
  authorization for the sample size before running, same as the prior
  two smoke tests this session.
- Resist the temptation to fix the first plausible-looking category
  without checking whether it's representative -- this session's own
  four hand-collected examples already span at least two different
  causes; a fix scoped to only one of them would look successful on a
  small sample while leaving the rest of the exclusion rate unexplained.
- If the investigation concludes some or all categories are an
  inherent LLM-reliability floor with no safe code fix, that is a
  legitimate, complete outcome for an investigation-type work item --
  report it plainly rather than forcing a fix recommendation that
  doesn't actually exist.

## Related Workstream and Designs

- Work item: `project/work_items/resolved/WI-SEGMENT-0068.md` (the
  fix whose own post-merge verification surfaced this gap)
- Work item: `project/work_items/proposed/WI-EVENT-0033.md` (whose own
  verification smoke test surfaced this gap -- not a formal dependency;
  see `## Problem / Context`'s demand-search note on why this item does
  not gate that WI's closure)
- Work item: `project/work_items/resolved/WI-SEGMENT-0059.md` (prior
  art on why a naive full-document fallback is unsafe)
