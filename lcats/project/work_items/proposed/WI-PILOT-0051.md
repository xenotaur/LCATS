---
id: WI-PILOT-0051
title: Add --story/--story-list targeted test harness to run_pilot.py
type: deliverable
status: proposed
priority: high
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams:
  - WS-PILOT-COST-SUSTAINABILITY
related_design:
  - lcats/project/design/proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md
depends_on: []
blocked_by: []
blocked: false
blocked_reason: null
resolution: null
expected_actions:
  - edit_file
  - create_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - run_real_llm_calls_without_explicit_approval
  - implement_prompt_caching
  - implement_batch_api
  - implement_model_tiering
acceptance:
  - run_pilot.py gains a --story <collection/name> flag and a --story-list <file> flag that call run_story() directly on the named story/stories, bypassing build_stratified_sample's 200-candidate genre-detect scan entirely
  - A small, fixed, offline, git-committed fixture set (1-3 real short stories) exists under experiments/03_cross_segment_relation_pilot/fixtures/; --story-list with no argument defaults to this fixture set. run_pilot.py's existing no-argument invocation (no --story/--story-list at all) is unchanged and still runs the full stratified pilot - the fixture set is a zero-config default only within targeted mode, not a change to the script's own defaults
  - A targeted run supplies run_story()'s required genre argument without going through build_stratified_sample - an explicit --genre flag, a single genre-detect call for the targeted story, or an explicit not-yet-classified sentinel (decided at implementation time per the proposal's Decision 2(d))
  - Per-stage cost/timing reporting closes the pilot_usage.jsonl gap for at least this harness's own runs - every stage (genre-detect, segmentation, and each ERW pass) that a targeted run touches gets a PassUsage-style record, not just the existing ERW-pipeline stages
  - A bounded small-scale trial (the fixture set, or a single named story) can be run end to end and verified without real API cost via a fake-backend harness
  - lrh validate and scripts/test both report 0 errors/failures
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - experiments/03_cross_segment_relation_pilot/run_pilot.py
  - experiments/03_cross_segment_relation_pilot/run_pilot_test.py
  - experiments/03_cross_segment_relation_pilot/fixtures/
---

## Summary

Add a `--story`/`--story-list` targeted-run flag to
`experiments/03_cross_segment_relation_pilot/run_pilot.py`, along with a
small, fixed, offline fixture set and per-stage cost reporting. This is
WI 1 of `WS-PILOT-COST-SUSTAINABILITY`'s Implementation Plan (Decision 2
of `PROP-LCATS-PILOT-COST-SUSTAINABILITY`) — the harness that gates
validation of everything after it (WI 2-4: prompt-caching, Batch API,
and model-tiering evaluations all need a cheap, reproducible way to
measure their real effect before this item exists).

## Problem / Context

Two real runs of `run_pilot.py` together spent $67.54 without producing
usable data — mostly discovering and fixing bugs rather than gathering
the intended cross-segment relation density findings. There is currently
no inexpensive path between `--dry-run` (zero API cost, fake backend,
meaningless output) and a full real run at the current defaults
(`--max-candidates 200`, `--model claude-opus-4-8`, tuned for complete
stratified coverage, not minimum-cost validation). This makes it
expensive to validate even a small, targeted code change before
committing to a full paid run.

This directly closes two live entries in `project/design/backlog.md`:
- **P2, "`pilot_usage.jsonl` doesn't track genre-detect or segmentation
  cost at all"** — `pilot_usage.jsonl` only records `PassUsage` entries
  from `run_story`'s ERW-pipeline stages; `build_stratified_sample`'s
  `assess_story()` calls and every `_segment_story` call are invisible
  in the pilot's own cost reporting. This item's per-stage cost
  reporting requirement closes this gap for the harness's own runs.
- **P3, "Pilot's default parameters optimize for full genre coverage,
  not minimum-cost validation"** — explicitly asks for "an inexpensive
  smoke-test path... between `--dry-run`... and a full real run." The
  `--story`/`--story-list` flag is exactly that path.

### Duplication search
- In-repo: No existing targeted-run or single-story harness for this
  pilot. `check_segmentation_reliability.py` demonstrates per-story
  persistence for segmentation alone (a narrower, already-existing
  pattern this item does not duplicate — it targets the whole
  `run_story()` pipeline, not just segmentation). `run_pilot_test.py`
  has unit tests but no CLI-level targeted-run capability.
- Sibling repos: None identified.
- External libraries: None — this is a CLI flag and fixture-set
  addition to an existing script, not a new dependency.
- Recommendation: Proceed.

### Demand search
- Work items: None found beyond this proposal's own request.
- Proposals: `PROP-LCATS-PILOT-COST-SUSTAINABILITY` (adopted) requests
  this exact item as WI 1 of its Implementation Plan.
- Workstreams: `WS-PILOT-COST-SUSTAINABILITY` lists this as WI 1,
  first in sequence, with WI 2-4 depending on it.
- Backlog: `project/design/backlog.md` has two live entries this item
  closes or materially addresses (see above).
- Recommendation: Proceed.

## Scope

- Add `--story <collection/name>` and `--story-list <file>` flags to
  `run_pilot.py`'s argument parser, calling `run_story()` directly on
  the named story/stories and bypassing `build_stratified_sample`'s
  200-candidate genre-detect scan entirely.
- Add a small, fixed, offline, git-committed fixture set (1-3 real
  short stories) under `experiments/03_cross_segment_relation_pilot/fixtures/`.
  `--story-list` given with no argument defaults to this fixture set -
  this is the zero-config default *within targeted mode* only.
  `run_pilot.py`'s existing no-argument invocation (neither flag given
  at all) is unchanged and still runs the full stratified pilot; this
  item does not alter that path or its defaults.
- Decide and implement how a targeted run supplies `run_story()`'s
  required `genre` argument without going through
  `build_stratified_sample` (which is the only existing code path that
  classifies a candidate and supplies it) — per the proposal's Decision
  2(d), this needs an explicit decision (e.g. an explicit `--genre`
  flag, a single genre-detect call for the targeted story, or an
  explicit not-yet-classified sentinel), not an implicit default.
- Add explicit per-stage cost/timing reporting for targeted runs,
  covering genre-detect and segmentation in addition to the existing
  ERW-pipeline `PassUsage` stages, closing backlog P2 for at least this
  harness's own runs.
- Add or extend `run_pilot_test.py` with fake-backend-harness tests
  proving the fixture set runs end to end at zero real API cost, and
  that a single named story can be targeted and reproduced directly.

## Required Changes

1. Extend `run_pilot.py`'s `argparse` setup (`main()`) with
   `--story`/`--story-list`, and branch the main loop to call
   `run_story()` directly for each targeted story instead of iterating
   `build_stratified_sample`'s output.
2. Implement the genre-argument decision from Scope above and document
   the choice made (in code comments or the PR description) since the
   proposal explicitly left this open.
3. Create `experiments/03_cross_segment_relation_pilot/fixtures/` with
   1-3 real short stories, chosen to be small enough for a cheap real
   run and diverse enough to exercise more than one genre/segment
   shape.
4. Thread per-stage `PassUsage`-style cost/timing recording through the
   genre-detect and segmentation stages for targeted runs (mirroring
   the existing ERW-pipeline `PassUsage` recording pattern), so
   `pilot_usage.jsonl` reflects a targeted run's entire real cost.
5. Add fake-backend-harness tests in `run_pilot_test.py` covering: the
   fixture set runs end to end with zero real API cost; a single named
   story (`--story <collection/name>`) is targeted and its result is
   reproducible; `--story-list` targets multiple stories correctly.

## Non-Goals

- Does not implement or evaluate Anthropic prompt caching, the Batch
  API, or per-stage model tiering — those are WI 2-4, gated on this
  item landing first, per the proposal's Decisions 3-5.
- Does not change the checkpointing architecture itself
  (`WI-PIPELINE-0040`/`0041`) — the targeted harness uses the existing
  checkpoint helper as-is.
- Does not re-scope `WI-EVENT-0030`'s stratified pilot for 8 genres —
  that is `WI-ASSESS-0031`'s and the genre-reconciliation backlog
  entries' concern, tracked separately.
- Does not run a real, paid `run_pilot.py` execution as part of this
  item — validation must be demonstrated via a fake-backend harness,
  not a real API spend, matching this project's dry-run discipline
  (see `forbidden_actions`).
- Does not resolve backlog P3's broader "should the pilot gain a
  distinct low-cost mode" design question in full — it answers the
  narrower "is there a smoke-test path" half of that question with a
  concrete `--story`/`--story-list` flag; whether `run_pilot.py`'s
  *default* parameters should also change is left open.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- `scripts/version tools`
- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- Fake-backend harness run demonstrating the fixture set runs end to
  end and a single named story is targeted and reproducible (no real
  API calls)

## Risk Notes

- Results are stochastic — a specific failing story (e.g. a story that
  previously triggered an exclusion or truncation) needs to be
  reproducible directly via `--story`, not only representable through
  the fixture set's fixed sample.
- The genre-argument plumbing (Scope item 2) is a real design decision
  the proposal deliberately left open, not a mechanical add — an
  incorrect choice (e.g. silently defaulting to a wrong genre) could
  produce misleading validation results from the harness itself.
- A fake-backend test can pass for the wrong reason if it doesn't
  exercise the real targeted-story code path (a confirmed recurring
  failure mode on this project, per `WI-PIPELINE-0041`'s own Risk
  Notes) — tests must actually invoke `--story`/`--story-list`'s code
  path, not just assert on a mocked `run_story()` return value.
- Per-stage cost reporting must not double-count: `build_stratified_sample`'s
  genre-detect scan and `_segment_story` are shared code paths between
  targeted and full-sample runs, so care is needed that this item's
  recording addition doesn't change or duplicate the full-sample run's
  existing `pilot_usage.jsonl` output.

## Dependencies / Order

None — this is WI 1, first in `WS-PILOT-COST-SUSTAINABILITY`'s sequence.
WI 2 (prompt-caching evaluation), WI 3 (Batch API evaluation), and WI 4
(model-tiering evaluation) all depend on this item landing first, since
each needs this harness's fixture set and cost reporting to measure its
own real effect.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-PILOT-COST-SUSTAINABILITY.md`
- Design: `project/design/proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md`
