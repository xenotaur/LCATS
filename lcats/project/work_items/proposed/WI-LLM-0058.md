---
resolution: null
blocked_reason: null
blocked: false
id: WI-LLM-0058
title: Fix or mitigate ASSESSMENT_TOOL schema-adjacent field corruption in forced tool-call output
type: investigation
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
  - project/design/event-role-world-genre-target-reconciliation.md
depends_on: []
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - run_paid_diagnostic_before_user_go_ahead
acceptance:
  - "Combines this item's own evidence with the already-existing, independent 24-story reproduction in lcats/experimental/annotation_feasibility_trial/stats_report.md (WI-ANNOTATE-0054) into one consolidated finding: corruption rate, affected field(s), and confirmation that detected_genre is unaffected across both real-API runs (44 stories total)"
  - "A documented root-cause hypothesis is reached and stated with its supporting evidence (schema field-adjacency at the secondary_genre/specials_verdict boundary, already narrowed by WI-ANNOTATE-0054 to an intermittent claude-opus-4-8 structured-output reliability issue, not a parsing bug or prompt injection) - or a good-faith investigation finds no further explanation and that is stated plainly"
  - "If a fix or mitigation is identified (e.g. ASSESSMENT_TOOL field reordering, or output validation/sanitization for free-text tool-result fields as WI-ANNOTATE-0054 recommended): it is implemented with a regression test, or an explicit decision not to fix now is recorded with rationale"
  - "A written go/no-go recommendation for WI-ASSESS-0051's --full corpus run, grounded in the combined 44-story evidence: is this corruption a blocker, and if so what threshold/fix resolves it"
  - "WI-ASSESS-0051's own depends_on lists this item, so an executor following its frontmatter discovers the prerequisite before starting the ~$435 full run"
  - "scripts/test passes with no new failures"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - test_output
artifacts_expected:
  - lcats/src/lcats/analysis/corpus/assess.py
  - lcats/tests/analysis_tests/assess_test.py
  - lcats/project/work_items/proposed/WI-ASSESS-0051.md
---

## Summary

Fix or mitigate a data-quality defect independently reproduced twice with
real API calls: `ASSESSMENT_TOOL`'s `secondary_genre` field is corrupted
with leaked tool-call-syntax fragments (e.g. `"</antml：parameter>\n
<parameter name=\"specials_verdict\">author_intentional"`) in a
substantial minority of calls - 7/20 (35%) in WI-ASSESS-0051's sample,
10/24 (42%) in the independent `annotation_feasibility_trial` run
(WI-ANNOTATE-0054, resolved). Combined: 17/44 real stories (39%) across
two independent runs. Root cause is already narrowed by WI-ANNOTATE-0054
to an intermittent `claude-opus-4-8` structured-output reliability issue
at the `secondary_genre`/`specials_verdict` schema boundary - not a
parsing bug in this codebase and not prompt injection. This item builds
on that existing evidence rather than re-deriving it, and moves to a
fix/mitigation decision plus a consolidated go/no-go recommendation for
WI-ASSESS-0051's `--full` run.

## Problem / Context

`ASSESSMENT_TOOL`'s schema in `lcats/src/lcats/analysis/corpus/assess.py`
defines `secondary_genre` immediately followed by `specials_verdict`
(`assess.py:107`, `assess.py:119`, adjacent again in the `required` list
at `assess.py:168-169`). The resulting corrupted JSON is well-formed
enough that neither `TruncatedResponseError` nor `NoToolCallError` fires,
so `result.error` stays empty - this defect is currently invisible to any
caller's exclusion/validation logic, including
`experiments/04_genre_census/run_census.py`'s own exclusion counting.

**This defect has already been independently reproduced and partially
diagnosed once**, in `lcats/experimental/annotation_feasibility_trial/stats_report.md`
(lines 26-47), from a real 24-story `claude-opus-4-8` run via `WI-ANNOTATE-0054`
(resolved; see its execution record at
`project/executions/WI-ANNOTATE-0054/2026_08_08_02_33_22_WI_ANNOTATE_0054.md`).
That run found:
- 10/24 stories (42%) with the same corruption pattern, at the same
  field boundary.
- Confirmed **not a parsing bug** in this codebase: `anthropic_backend.py`
  reads the Anthropic SDK's already-parsed native `tool_use.input` dict -
  the corruption is present in the value the model itself wrote.
- Confirmed **not prompt injection** from story text or the tool schema:
  `assess.py`'s `ASSESSMENT_TOOL` and system prompts contain no such tags.
- Confirmed **scoped entirely to `secondary_genre`**: `detected_genre`,
  `summary`, `issues`, `specials_verdict`, and scene segmentation were all
  clean in that run.
- Already recommends "a follow-up work item to add output
  validation/sanitization for free-text tool-result fields" - this item
  is that follow-up.

WI-ASSESS-0051's own 20-story sample independently reproduced the same
pattern (7/20, 35%) with `detected_genre` also clean - consistent with,
and reinforcing, WI-ANNOTATE-0054's finding. Combined across both real
runs: 17/44 stories (39%), `secondary_genre` the only field ever observed
affected, `detected_genre` clean in both.

This still blocks confident approval of WI-ASSESS-0051's `--full` corpus
run (~$435, ~1,868 stories) - not because `detected_genre` looks corrupted
(it doesn't, in either run), but because a ~39% corruption rate on
*any* field from two independent runs is a real signal about this
schema's reliability at scale that warrants a fix or mitigation decision,
not silent acceptance.

### Duplication search
- **Found and incorporated as baseline evidence** (this search was
  initially reported as clean in this item's first draft - a review
  finding, PR #257, corrected it):
  `lcats/experimental/annotation_feasibility_trial/stats_report.md`
  (`WI-ANNOTATE-0054`, resolved) already reproduces and characterizes this
  exact corruption pattern from an independent real 24-story run, with a
  more thorough per-field audit than this item's own 20-story sample
  (confirmed `detected_genre`/`summary`/`issues`/`specials_verdict` all
  clean; this item's sample only directly observed `detected_genre`).
  This item builds on that evidence rather than re-deriving it from
  scratch.
- `project/design/backlog.md` has unrelated malformed-data entries (e.g.
  the container-type-check gap in extractor `build_*()` functions) but
  nothing else matching this specific corruption.
- Sibling repos / external libraries: none identified.
- Recommendation: proceed, scoped to build on the existing evidence.

### Demand search
- Work items: `WI-ANNOTATE-0054`'s own execution record already
  recommends this exact follow-up ("a follow-up work item to add output
  validation/sanitization for free-text tool-result fields"). This item
  fulfills that recommendation.
- Proposals, backlog: no existing entry.
- Recommendation: proceed; this is the recommended next step from
  already-completed work, not a duplicate of it.

## Scope

- Consolidate this item's own 20-story evidence with
  `stats_report.md`'s 24-story evidence into one combined finding (44
  stories, 17 corrupted, 39%) - no new paid reproduction sample is
  required for this step, since reproduction and per-field scoping are
  already done twice, independently.
- Decide on a fix or mitigation approach. Two candidates, not mutually
  exclusive:
  1. **Schema reordering**: move `secondary_genre` so it is not
     immediately followed by another required string field in
     `ASSESSMENT_TOOL`, testing whether the corruption pattern
     disappears or shifts to whichever fields become newly adjacent.
  2. **Output validation/sanitization** (WI-ANNOTATE-0054's own
     recommendation): detect and strip or reject `secondary_genre` values
     matching the leaked-tag pattern, matching how `_annotate_scenes`
     already rejects malformed segmentation output.
- If testing candidate 1 requires new real API calls (to confirm a
  reordering actually changes behavior), keep that sample small (a
  handful of stories) and gated on go-ahead - see `forbidden_actions`.
  Candidate 2 requires no new paid calls at all.
- Write the consolidated go/no-go recommendation for WI-ASSESS-0051's
  `--full` run.
- Add `WI-LLM-0058` to `WI-ASSESS-0051`'s `depends_on` (frontmatter-level,
  not just prose) so an executor following the work item's own metadata
  discovers this prerequisite before starting the ~$435 run - a review
  finding (PR #257) noted the prose-only gate in this item's own
  Non-Goals does not by itself prevent that.

## Required Changes

1. `lcats/src/lcats/analysis/corpus/assess.py`: the fix, if schema
   reordering is chosen (moving `secondary_genre` so it isn't immediately
   followed by another required string field), and/or a runtime
   validation/sanitization check on `secondary_genre` if that mitigation
   is chosen instead or in addition.
2. `lcats/tests/analysis_tests/assess_test.py`: regression test(s)
   covering whichever fix/mitigation is implemented.
3. `lcats/project/work_items/proposed/WI-ASSESS-0051.md`: add
   `WI-LLM-0058` to `depends_on:`.
4. A written finding (in this work item's own execution record, or a
   short note appended to `project/design/event-role-world-genre-target-reconciliation.md`
   if warranted) consolidating both real-API runs' evidence and stating
   the go/no-go recommendation for WI-ASSESS-0051's `--full` run.

## Non-Goals

- Do not run WI-ASSESS-0051's `--full` corpus run - that remains gated on
  WI-ASSESS-0051's own explicit human go-ahead, informed by this item's
  findings, and now also encoded in `WI-ASSESS-0051`'s `depends_on`.
- Do not modify `experiments/04_genre_census/run_census.py`'s CLI surface
  or cost-gating logic.
- Do not change `lcats assess`'s CLI surface beyond the `ASSESSMENT_TOOL`
  schema fix itself, if one is implemented.
- Do not re-fix the scene-segmentation offset-corruption finding also
  documented in `stats_report.md` (lines 12-24) - that is a distinct,
  already-flagged, separately-scoped follow-up (shared `text_segmenter.py`
  code used by multiple callers), not this item's concern.
- Do not spend real API cost on *any* diagnostic or reproduction sample -
  including a small one - without explicit go-ahead first; see
  `forbidden_actions`.

## Acceptance Criteria

(see frontmatter `acceptance:` - kept in sync)

## Validation

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- If schema reordering is chosen and needs live confirmation: a small
  real-API sample (requires `ANTHROPIC_API_KEY`, real but small $ cost -
  go-ahead required per `forbidden_actions`)

## Risk Notes

- **Any real $ cost requires go-ahead first** - even a small diagnostic
  sample. Candidate fix 2 (output validation/sanitization) needs no new
  paid calls at all and should be preferred if schema reordering's
  effectiveness can't be cheaply confirmed.
- **Schema changes carry regression risk** - `ASSESSMENT_TOOL` is used by
  `lcats assess`'s CLI and any existing checkpoint fingerprints keyed to
  `_CLASSIFIER_VERSION`; a field-reordering fix should bump that version
  marker in any caller relying on it (e.g.
  `experiments/04_genre_census/run_census.py`'s own
  `_CLASSIFIER_VERSION`) so stale pre-fix checkpoints aren't silently
  reused.
- **Root cause may not be fully resolvable** - both real runs point to an
  underlying Anthropic API/model tool-call generation quirk outside this
  codebase's control; if so, the right outcome is a documented mitigation
  (output validation/sanitization) rather than a "root cause eliminated"
  claim.
