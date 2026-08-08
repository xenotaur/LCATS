---
resolution: null
blocked_reason: null
blocked: false
id: WI-SEGMENT-0059
title: Fix silent misalignment fallback in text_segmenter.py's scene-segmentation aligner
type: deliverable
status: proposed
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams: []
related_design:
  - project/work_items/resolved/WI-ANNOTATE-0054.md
depends_on: []
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - rewrite_alignment_algorithm_from_scratch
acceptance:
  - build_paragraph_index detects single-newline-formatted source text (zero blank-line breaks) and falls back to single-newline paragraph splitting instead of collapsing to n_paragraphs=1
  - align_segment returns alignment failure (not a full-search-range fallback) when find_anchor_in_range genuinely fails to locate either start_exact or end_exact
  - segments_result_aligner (or its scene-analysis wrapper) propagates a failed span as a raised error rather than silently leaving the segment unchanged, so JSONPromptExtractor.extract's existing try/except actually sets alignment_error -- verified by an end-to-end assertion, not just a unit-level align_segment return value
  - Deterministic regression tests replay the exact recorded segment metadata (start_par_id/end_par_id/start_exact/end_exact) from WI-ANNOTATE-0054's 3 committed trial cases (love_of_life, story_of_keesh, brown_wolf) through the fixed text_segmenter functions against the real corpora/london story text, and confirm the fixed alignment no longer produces overlapping/degenerate offsets for that same recorded input -- this tests the alignment fix deterministically, not whether a fresh model call would segment differently, which is a separate, nondeterministic, out-of-scope claim
  - Existing callers (story_processors.py, run_pilot.py) and their test suites still pass unmodified
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/src/lcats/analysis/text_segmenter.py
  - lcats/tests/analysis_tests/text_segmenter_test.py
---

## Summary

Fix a real correctness defect in `text_segmenter.py`'s scene-segmentation
alignment, discovered during `WI-ANNOTATE-0054`'s hand-validation of real
pipeline output. `build_paragraph_index` only splits on a literal blank
line (`\n\n`); source text formatted with single-newline paragraph breaks
collapses to a single giant "paragraph," forcing every segment's anchor
search across the entire document. When `align_segment`'s anchor search
then fails, it silently falls back to end-of-document instead of raising
an alignment error — producing spurious, overlapping segment boundaries
with no error signal.

## Problem / Context

`text_segmenter.py`'s `build_paragraph_index` (`build_paragraph_index`,
splitting on `"\n\n"`) is the paragraph indexer scene-segmentation's
anchor-based alignment (`align_segment`, `find_anchor_in_range`) relies
on. A story with no blank-line paragraph breaks at all — single-newline
formatting — collapses to `n_paragraphs=1`, so every segment's
`start_par_id`/`end_par_id` (set by the model, forced to `1`) makes
`align_segment`'s search range the *entire document*. When
`find_anchor_in_range` then fails to locate a segment's `end_exact` text
verbatim within that range (`align_segment`, around line 146), the
function silently falls back to `hi` — the end of the search range, i.e.
end-of-document — instead of raising an alignment error. The result is a
spurious full-document-length segment that overlaps every segment after
it, and `annotate.py`'s existing `alignment_error`/`validation_error`
rejection never fires, because `align_segment` still returns a
syntactically valid `(start, end)` pair.

Confirmed during `WI-ANNOTATE-0054`'s real API run (PR #253) on 100% of
`corpora/london` stories in that trial's 24-story subset (3/3):
`love_of_life` (8 overlapping segments, 121,396 cumulative overlapping
chars), `story_of_keesh` (2,626 overlapping chars, segment 4 and 5
overlap), `brown_wolf` (degenerated to a single segment spanning the
entire 31.8k-char story — no real segmentation at all). Full evidence,
including reproducible detection code
(`_segment_overlap_chars`/`_paragraph_collapse` in
`lcats/experimental/annotation_feasibility_trial/collect_stats.py`), is
documented in that item's `stats_report.md` and closeout note.

### Duplication search

- In-repo: No existing work item addresses this. `WI-EVENT-0024` and
  `WI-EVENT-0033` are the only other work items mentioning
  `text_segmenter`, and neither touches this bug — `WI-EVENT-0024`
  establishes `text_segmenter.py` as the stage-1 input contract,
  `WI-EVENT-0033` references `segments_result_aligner`/`segments_auditor`
  for an unrelated schema-migration concern.
- Sibling repos: None identified.
- External libraries: None applicable — this is a fix to existing
  in-repo alignment logic, not a new capability.
- Recommendation: Proceed.

### Demand search

- Work items: Requested directly by `WI-ANNOTATE-0054`'s closeout note
  and `stats_report.md`'s recommended follow-up (higher priority than
  that item's other follow-up, `secondary_genre` sanitization, since
  this affects segmentation correctness for any caller of the shared
  library, not just one trial's output).
- Proposals: No existing proposal covers this.
- Backlog: No matching entry in `project/design/backlog.md`.
- Recommendation: Proceed.

## Scope

- Detect single-newline (no-blank-line) paragraph formatting in
  `build_paragraph_index` and fall back to splitting on single newlines
  in that case, rather than collapsing the whole document to one
  paragraph.
- Change `align_segment`'s anchor-not-found behavior for **both**
  `start_exact` and `end_exact`: return alignment failure (matching the
  function's existing `None`-return contract for the fully-invalid
  case) instead of the current silent fallbacks (`s_idx = lo` /
  `e_idx = hi`), so a genuinely failed anchor search is surfaced as an
  error rather than silently producing a wrong span. (Review finding,
  PR #255: the original scope only covered a failed `end_exact`
  search, leaving the identical `start_exact` fallback as an equivalent
  silent-corruption path.)
- **Propagate the failure up the call chain, not just out of
  `align_segment`.** Returning `None`/failure from `align_segment`
  alone does not make `annotate.py`'s `alignment_error` rejection fire:
  `text_segmenter.segments_result_aligner` currently catches any
  exception from `align_segment` per-segment and leaves that segment
  unchanged (`except Exception: span = None`, then `if span: ... #
  else: leave as-is`), so nothing propagates to
  `JSONPromptExtractor.extract`, which only sets `alignment_error` when
  its `result_aligner` callable itself raises. `segments_result_aligner`
  (or `scene_analysis.py`'s `_segment_result_aligner` wrapper) must
  itself raise when a segment's alignment fails, so the failure reaches
  `extract`'s existing `try/except` and `annotate.py`'s existing
  rejection logic actually catches it. (Review finding, PR #255 — P1.)
- Add regression tests that replay the *exact recorded* segment
  metadata from the 3 real WI-ANNOTATE-0054 trial failures through the
  fixed alignment functions — deterministic, since it reuses already-
  recorded model output rather than requiring a fresh API call. (Review
  finding, PR #255: the original scope implied testing "the model no
  longer produces the degenerate segmentation," which is nondeterministic
  and cannot be a stable regression test against a static committed
  fixture — see Acceptance Criteria.)

## Required Changes

1. In `lcats/src/lcats/analysis/text_segmenter.py`'s
   `build_paragraph_index`, detect the zero-blank-line-break case and
   split on single newlines instead, so multi-paragraph source text
   without blank-line separators still produces a meaningful
   `n_paragraphs > 1` index.
2. In `align_segment`, change **both** the start-anchor and end-anchor
   fallback: when `start_exact`/`end_exact` is non-empty but
   `find_anchor_in_range` returns `None`, return alignment failure
   instead of the current `s_idx = lo` / `e_idx = hi` defaults.
3. In `segments_result_aligner` (`text_segmenter.py`) or its
   scene-analysis wrapper `_segment_result_aligner`
   (`scene_analysis.py`), change the per-segment failure handling so a
   failed `align_segment` call is raised/propagated rather than
   silently caught and left as-is — this is what actually makes
   `JSONPromptExtractor.extract`'s existing `alignment_error` path
   fire.
4. Add tests to `lcats/tests/analysis_tests/text_segmenter_test.py`
   covering: (a) a synthetic single-newline-formatted story correctly
   produces `n_paragraphs > 1`; (b) a failed start-anchor search and a
   failed end-anchor search each correctly produce an alignment
   failure rather than a silent fallback; (c) an end-to-end assertion
   that a failed alignment actually surfaces as `alignment_error` at
   the `JSONPromptExtractor.extract`/`annotate.py` level, not just as
   `align_segment`'s own return value; (d) deterministic replay of the
   3 real `corpora/london` cases' exact recorded segment metadata from
   WI-ANNOTATE-0054 through the fixed functions, confirming no
   overlap/degenerate output for that same input.
5. Run the full test suite to confirm no regression in
   `story_processors.py`, `run_pilot.py`, or their own tests, which
   depend on this shared alignment logic.

## Non-Goals

- Does not rewrite the alignment algorithm from scratch — this is a
  targeted fix to two specific failure modes, not a redesign.
- Does not touch `annotate.py`'s own alignment/validation-error
  rejection logic — already correct; it simply never got a chance to
  fire before this fix.
- Does not address the separate `secondary_genre` corruption finding
  from `WI-ANNOTATE-0054` (assess.py's genre-detection output) — a
  distinct issue in a different module, tracked as its own follow-up
  work item.
- Does not re-run `WI-ANNOTATE-0054`'s trial or regenerate its
  committed sidecar output — this item fixes the underlying library so
  *future* runs are correct; it does not retroactively repair already-
  committed trial data.

## Acceptance Criteria

- `build_paragraph_index` detects single-newline-formatted source text
  (zero blank-line breaks) and falls back to single-newline paragraph
  splitting instead of collapsing to `n_paragraphs=1`.
- `align_segment` returns alignment failure (not a silent fallback)
  when `find_anchor_in_range` genuinely fails to locate either
  `start_exact` or `end_exact`.
- `segments_result_aligner` (or its scene-analysis wrapper) propagates
  a failed span as a raised error rather than silently leaving the
  segment unchanged, so `JSONPromptExtractor.extract`'s existing
  `try/except` actually sets `alignment_error` — verified by an
  end-to-end assertion at that level, not just a unit-level
  `align_segment` return-value check.
- Deterministic regression tests replay the exact recorded segment
  metadata (`start_par_id`/`end_par_id`/`start_exact`/`end_exact`) from
  `WI-ANNOTATE-0054`'s 3 committed trial cases (`love_of_life`,
  `story_of_keesh`, `brown_wolf`) through the fixed `text_segmenter`
  functions against the real `corpora/london` story text, and confirm
  the fixed alignment no longer produces overlapping/degenerate
  offsets for that same recorded input. This tests the alignment fix
  deterministically against already-recorded model output — it does
  not claim or require that a fresh model call would segment the story
  differently, which is a separate, nondeterministic question outside
  this item's scope.
- Existing callers (`story_processors.py`, `run_pilot.py`) and their
  test suites still pass unmodified.
- `lrh validate` reports 0 errors.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes

- `text_segmenter.py` is shared library code used by other callers
  beyond `lcats annotate` — `story_processors.py`, `run_pilot.py`, and
  `notebooks/12_extract_scenes.ipynb` per `scene_analysis.py`'s own
  docstring. The fix must not regress any of them; run the full test
  suite, not just `text_segmenter_test.py`, before considering this
  done.
- Changing `align_segment`'s failure behavior from "always return a
  span" to "sometimes return failure," and making `segments_result_aligner`
  raise on that failure instead of silently continuing, is a contract
  change for any caller that doesn't already handle a raised alignment
  failure — verify `annotate.py`'s existing `alignment_error` handling
  is the only consumer that needs this, or that other callers
  (`story_processors.py`, `run_pilot.py`) already tolerate/expect it.

## Dependencies / Order

None. Standalone fix; no other work item depends on this one yet.

## Related Workstream and Designs

- No active workstream currently owns shared `text_segmenter.py`
  maintenance; this item is standalone.
- Related: `project/work_items/resolved/WI-ANNOTATE-0054.md` (where this
  defect was discovered and fully documented).
