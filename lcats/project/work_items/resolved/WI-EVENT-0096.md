---
resolution: "Executed via PR #398. Ran the exact original 17-story baseline cohort through check_segmentation_reliability.py with claude-haiku-4-5-20251001: 17 real API calls, $0.59 actual cost. Result: parsing_error structurally eliminated (11/17 -> 0/17); any-cause exclusion rate barely moved (65% -> 59%) because a different, pre-existing failure mode (near-miss anchor alignment, WI-SEGMENT-0069/0072) is now dominant. Full data and write-up: experiments/03_cross_segment_relation_pilot/results/segmentation_reliability/SUMMARY.md. WI-EVENT-0033.md updated with the real result and intentionally left proposed per its own stated practice of not forcing a pass on a smaller-than-expected improvement."
blocked_reason: null
blocked: false
id: WI-EVENT-0096
title: Measure live segmentation exclusion-rate improvement from WI-EVENT-0033's schema hardening
type: evaluation
status: resolved
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams:
  - WS-EVENT-STRUCTURED-OUTPUT-RELIABILITY
related_design:
  - lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md
  - lcats/project/work_items/proposed/WI-EVENT-0033.md
depends_on: []
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - modify_scene_analysis_extractor
  - modify_check_segmentation_reliability_measurement_logic
  - implement_new_architecture
  - run_real_llm_calls_without_explicit_approval
  - force_push
  - delete_branch
acceptance:
  - "Before any real API spend, the executor presents the exact 17-story cohort (resolved from experiments/03_cross_segment_relation_pilot/results/pilot_stories.jsonl's committed story_id/genre list to their current corpora/ paths), the model (claude-haiku-4-5-20251001, matching the original baseline run), and the expected call-count/cost estimate, and receives explicit in-session human approval"
  - "The exact original 17-story cohort is re-run through experiments/03_cross_segment_relation_pilot/check_segmentation_reliability.py (already built and reviewed for this exact purpose, PR #189) via its --story-list flag - not a fresh or substitute sample, since the original cohort's story IDs are in fact committed and resolvable"
  - "The comparison metric is the any-cause segmentation exclusion rate (api_error / extraction_error / alignment_error / no_segments, as check_segmentation_reliability.py's classify() already reports), never a bare parsing_error count - on the tool_schema code path, JSONPromptExtractor.extract() sets parsing_error=None unconditionally (llm_extractor.py's tool_schema branch), so a parsing_error-only comparison would report a 0% rate by construction regardless of whether the fix actually helped"
  - "The new any-cause exclusion rate is computed directly from real check_segmentation_reliability.py output (not estimated or assumed) and reported alongside the original 65% (11/17) baseline, broken down by cause and by genre, with an explicit western callout (both western stories were excluded in the original baseline)"
  - "Raw per-story output (as already written by check_segmentation_reliability.py, one JSON file per story) and a summary are saved as committed data under experiments/03_cross_segment_relation_pilot/results/segmentation_reliability/, alongside the existing pilot_stories.jsonl/pilot_summary.json this experiment already commits data under, so the measurement is independently checkable, not just narrated"
  - "WI-EVENT-0033.md is updated with the real measured result in its Risk Notes/resolution - if the exclusion rate dropped meaningfully, WI-EVENT-0033 is moved to resolved/ with a resolution citing the before/after; if not, the finding is reported plainly and WI-EVENT-0033 stays proposed with the gap documented, per this project's practice of not forcing a pass"
  - "scripts/test passes with no new failures"
  - "lrh validate reports 0 errors"
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - experiments/03_cross_segment_relation_pilot/results/segmentation_reliability/
  - lcats/project/work_items/proposed/WI-EVENT-0033.md
---

# Work Item: WI-EVENT-0096

## Summary

Close `WI-EVENT-0033`'s one outstanding acceptance criterion: a live
re-run against real API calls to measure whether its schema-hardening fix
(`SEGMENT_TOOL_SCHEMA` via `tool_schema=`, PR #188, merged 2026-07-29)
actually reduced the segmentation-exclusion rate observed before the fix
(65%, 11/17, all `parsing_error`), with the `western` genre stratum
particularly affected (both its stories excluded). That criterion was
explicitly left unverified at PR #188's merge time for lack of API
credentials in that environment, not skipped by oversight - the PR's own
description names it as the one remaining gap. A purpose-built measurement
script for exactly this comparison already exists
(`experiments/03_cross_segment_relation_pilot/check_segmentation_reliability.py`,
PR #189) but has never been run for real; this item runs it against the
real, committed original cohort and reports the result.

## Problem / Context

The 2026-07-27 ERW pipeline audit
(`lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md:238-245`)
found `scene_analysis.py`'s Stage 1 segmentation extractor
(`make_segment_extractor`) was the pipeline's actual, currently-blocking
reliability problem: with `claude-haiku-4-5-20251001` in a real user run,
11 of 17 sampled stories (65%) were excluded with
`extraction_error="parsing_error"`, and the `western` stratum had zero
included stories as a result. `WI-EVENT-0033` retrofitted this extractor
(plus `make_semantics_extractor` and `make_doc_classification_extractor`)
to use a `tool_schema=` structured-output call instead of unconstrained
`json_object` mode, per `lcats.llm.tool_schema.strict_tool_schema()`. That
work merged via PR #188 (commit `9cb37549`), but its own final commit
message states plainly the live re-run criterion was not verified in that
environment. `WI-EVENT-0033.md` itself was deliberately left
`status: proposed` for exactly this reason, not moved to `resolved/`.

**No `depends_on` on `WI-EVENT-0033`, deliberately.** This item's real
prerequisite - PR #188's schema-hardening fix actually merged - is already
satisfied; `depends_on` in this schema means "that WI's own `status` must
be `resolved`," which is a status this item exists to help produce, not
one it can wait on without deadlocking `/lrh-execute`'s own dependency
enforcement. The relationship is expressed instead via `related_design`/
`related_workstreams` and the Related Workstream and Designs section
below.

**Correction from this item's own review round (PR #396, both findings
confirmed real before fixing):**

1. The original 17-story cohort **is** committed:
   `experiments/03_cross_segment_relation_pilot/results/pilot_stories.jsonl`
   holds exactly 17 rows with the cited 11 `segmentation failed:
   parsing_error` exclusions and the 5 science-fiction / 5 horror / 2
   western / 5 romance composition - a byte-for-byte match to the audit's
   own figures. An earlier draft of this item claimed the cohort was
   unrecoverable, based on an insufficiently broad search; this was wrong,
   confirmed by directly reading that file's 17 rows. The exact cohort is
   used here, not a substitute sample.
2. `experiments/03_cross_segment_relation_pilot/check_segmentation_reliability.py`
   already exists, was already reviewed and tested (PR #189, six review
   comments all fixed), and was purpose-built for this exact measurement -
   its own docstring names `WI-EVENT-0033`'s acceptance criterion directly.
   It has never actually been run against real data (no API credentials
   were available in that session). Its `classify()` function and module
   docstring (`:55-67`) already document, and this item's own review round
   independently confirmed by reading `llm_extractor.py`'s tool_schema
   branch directly, that comparing raw `parsing_error` counts post-fix is
   invalid: `JSONPromptExtractor.extract()` sets `parsing_error = None`
   unconditionally on the `tool_schema` path (there is no JSON-text parse
   step to fail), so a `parsing_error`-only comparison reports 0% by
   construction regardless of the fix's real effect. The any-cause
   exclusion rate `classify()` already computes is the valid comparison.

### Duplication search

- In-repo: `check_segmentation_reliability.py` (PR #189) already exists
  for exactly this measurement - not a duplicate to avoid, but the
  mechanism this item exists to actually execute. This item's scope is
  running that existing, already-reviewed tool against the real committed
  cohort and reporting the result, not building new measurement tooling.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed, using the existing tool as-is.

### Demand search

- Work items: `WI-EVENT-0033.md`'s own acceptance criteria and PR #188's
  merge commit message both name this exact deliverable as outstanding;
  `SEGMENTATION_RELIABILITY_CHECK_BACKFILL.md`'s own Follow-up section
  states plainly: "Someone with real API credentials needs to run
  `check_segmentation_reliability.py` and report the resulting exclusion
  rate... to actually close WI-EVENT-0033's remaining acceptance
  criterion." Filed as a separate, `related_design`-linked evaluation item
  (rather than reopening `WI-EVENT-0033` directly) so the measurement has
  its own traceable execution record, bounded real-API cost gate, and PR -
  following this session's established pattern for `WI-EVENT-0030`'s own
  cost-gate sub-runs (`WI-EVENT-0078`/`0079`/`0080`).
- Proposals: None identified beyond the governing ERW extractor proposal,
  which already names `json_object` mode as the pattern being replaced.
- Backlog: No matching entry found.
- Recommendation: Proceed.

## Scope

- Resolve the 17 `story_id`/genre pairs in
  `experiments/03_cross_segment_relation_pilot/results/pilot_stories.jsonl`
  to their current `corpora/<collection>/<slug>` paths (the jsonl's own
  `path` field is stale, pointing at a retired `lcats/data/...` layout;
  the current canonical location is under `corpora/`) and write them to a
  `--story-list` input file for `check_segmentation_reliability.py`.
- Follow this project's established two-step real-cost-gate discipline:
  present the resolved 17-story cohort, the model
  (`claude-haiku-4-5-20251001`, matching the baseline), and the expected
  cost/call-count estimate (~17 calls, one per story); wait for explicit
  in-session approval; then run.
- Run `check_segmentation_reliability.py --story-list <file> --model
  claude-haiku-4-5-20251001 --output
  experiments/03_cross_segment_relation_pilot/results/segmentation_reliability/`.
- Report the resulting any-cause exclusion rate (not a bare
  `parsing_error` count) alongside the original 65% (11/17), broken down
  by cause and by genre, with an explicit `western` callout.
- Commit the script's raw per-story output plus a summary under
  `experiments/03_cross_segment_relation_pilot/results/segmentation_reliability/`
  - colocated with this experiment's existing committed data
  (`pilot_stories.jsonl`, `pilot_summary.json`), not a new
  `lcats/experimental/` location, since this is a direct, same-experiment
  follow-on measurement rather than a separate small trial.
- Update `WI-EVENT-0033.md` with the real measured outcome, and resolve
  it if the result supports that.

## Required Changes

1. Write a small resolution step (script or manual, whichever is
   simpler) that reads `pilot_stories.jsonl`'s 17 `story_id`/`genre`
   pairs, locates each story's current `corpora/<collection>/<slug>`
   directory, and writes a `--story-list` text file
   `check_segmentation_reliability.py` can consume directly (one path per
   line, per its documented format).
2. Present the resolved cohort, model, and cost estimate to the user for
   explicit approval before any spend.
3. After approval, run
   `check_segmentation_reliability.py --story-list <file> --model
   claude-haiku-4-5-20251001 --output
   experiments/03_cross_segment_relation_pilot/results/segmentation_reliability/`
   unmodified - no changes to the script's own measurement logic are in
   scope (see `forbidden_actions`).
4. Write a summary (old vs. new any-cause exclusion rate, per-genre
   breakdown, explicit `western` callout) alongside the script's raw
   per-story output, both committed under
   `experiments/03_cross_segment_relation_pilot/results/segmentation_reliability/`.
5. Update `WI-EVENT-0033.md`: populate its Risk Notes with the real
   measured before/after, and either move it to `resolved/` with a
   `resolution:` field citing the measurement, or leave it `proposed`
   with the gap stated plainly if the improvement is smaller than
   expected.
6. No changes to `scene_analysis.py`/`story_analysis.py`/
   `check_segmentation_reliability.py` are in scope - all already merged
   and reviewed. Add test coverage only if the small story-list
   resolution step from item 1 is substantial enough to warrant it.

## Non-Goals

- Does not modify `scene_analysis.py`'s or `story_analysis.py`'s schemas
  or extractors - `WI-EVENT-0033`'s schema-hardening code is already
  merged (PR #188); this item measures its real-world effect only.
- Does not modify `check_segmentation_reliability.py`'s own measurement
  logic (`classify()`, exclusion-rate computation) - already built and
  reviewed (PR #189) for exactly this purpose.
- Does not re-run `make_semantics_extractor` or
  `make_doc_classification_extractor` - both were unmeasured in the
  original 2026-07-27 audit too (no live failure rate to compare
  against), and `WI-EVENT-0033.md`'s own Risk Notes already flag this as
  a separate, unmeasured risk, not something this item resolves.
- Does not substitute a fresh or different cohort for the original
  17-story baseline - the real cohort is committed and resolvable, so no
  substitution is needed or used.
- Does not spend any real API budget without an explicit, presented,
  approved cost estimate first.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- scripts/format --check --diff
- scripts/lint
- scripts/test
- lrh validate

## Risk Notes

- **Story-ID-to-path resolution is a small but real step.** The
  committed `pilot_stories.jsonl`'s own `path` field points at a retired
  `lcats/data/...` layout that no longer exists in this repo; each
  story's current `corpora/` location must be located by its
  `story_id`/collection instead. This is mechanical (directory lookup by
  slug), not a design risk, but worth doing carefully so the `--story-list`
  file names the same 17 stories, not a near-miss set.
- **Metric correctness is the central risk this item's own review round
  already caught once.** An earlier draft of this item would have
  compared bare `parsing_error` counts, which is 0% by construction on
  the `tool_schema` path regardless of the fix's real effect - exactly
  the false-positive `check_segmentation_reliability.py`'s own docstring
  warns about. The any-cause exclusion rate is the only valid comparison;
  any future edit to this item's acceptance criteria should preserve that.
- **Directionally negative result is a valid outcome.** If the measured
  any-cause exclusion rate does not improve meaningfully, that is reported
  plainly in `WI-EVENT-0033.md` rather than forced into a "resolved"
  state - matching this project's own established practice (e.g.
  `WI-EVENT-0080.md`'s acceptance criteria, `WI-PILOT-0082.md`'s Risk
  Notes).
- **Real API spend requires the same bounded-approval discipline** this
  session already used for `WI-EVENT-0030`'s cost-gate sub-runs - no
  spend without a presented estimate and explicit go-ahead.

## Related Workstream and Designs

- Workstream: `lcats/project/workstreams/proposed/WS-EVENT-STRUCTURED-OUTPUT-RELIABILITY.md`
- Work item: `lcats/project/work_items/proposed/WI-EVENT-0033.md` - the
  item whose outstanding acceptance criterion this item executes
- Audit: `lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`
- Tool: `experiments/03_cross_segment_relation_pilot/check_segmentation_reliability.py`
  (PR #189) - the already-built, already-reviewed measurement script this
  item runs
- Data: `experiments/03_cross_segment_relation_pilot/results/pilot_stories.jsonl`
  - the real, committed original 17-story baseline cohort
