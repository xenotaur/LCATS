---
execution_id: 2026_08_31_09_36_05_WI_SEGMENT_0101_PARAGRAPH_BOUNDARY_PROMPT_CONSISTENCY
prompt_id: PROMPT(WI-SEGMENT-0101:WI_SEGMENT_0101_PARAGRAPH_BOUNDARY_PROMPT_CONSISTENCY)[2026-08-31T09:35:59+00:00]
work_item: WI-SEGMENT-0101
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/420
commit: 6f888a044facc293491f56b3e192d137730cafe8
agent: claude_app
instruction_source: lcats/project/work_items/proposed/WI-SEGMENT-0101.md
session_transcript: pending
created_at: 2026-08-31T09:36:05+00:00
---

# Summary

Executed `WI-SEGMENT-0101`: built an isolated, non-production reworded
prompt variant deriving `end_par_id`/`start_par_id` from
`end_exact`/`start_exact`'s located position rather than independent
judgment, ran a real 17-story API ablation, and measured whether the
paragraph-boundary overshoot pattern `WI-SEGMENT-0098` found shrinks.

# Result

Built `experiments/03_cross_segment_relation_pilot/reworded_boundary_prompt.py`
(reworded variant, verified byte-identical to production outside the 4
targeted bullets by a dedicated test suite), `run_boundary_prompt_ablation.py`
(the ablation runner), and `measure_paragraph_boundary_overshoot.py` (the
overshoot measurement, replaying `WI-SEGMENT-0098`'s methodology
generalized to every segment/both anchors).

Presented a cost estimate (17 calls, `claude-haiku-4-5-20251001`, ~$0.59)
and got explicit approval before spending. Ran the real ablation against
the `WI-EVENT-0033`/`WI-EVENT-0096` 17-story baseline cohort; actual cost
$0.59. Compared against `WI-EVENT-0096`'s already-committed real output
(no re-spend needed for the "before" side).

**Result: directionally positive, not conclusive.** Anchor-level
overshoot dropped from 12/177 (baseline) to 8/162 (reworded); the exact
story that motivated the fix (`the_voice_in_the_fog__leverage`, whose
`end_exact` anchor was found during this item's own review round to
straddle two paragraphs) went from 3 overshoot instances to 0. But this
is a single, unmatched-per-segment run - the model's own segment
boundaries differ between runs independent of prompt wording - and 2
stories show new overshoot under the reworded prompt that didn't appear
under the baseline. Full results, honest limitations, and a
recommendation (adopt as a complement to, not instead of,
`WI-SEGMENT-0098`'s window-widening recommendation; do not implement in
production from this evidence alone) are in
`lcats/project/design/segmentation-paragraph-boundary-prompt-consistency-investigation.md`.

A diff-mode self-review before push (see the `AD_HOC/..._SELFREVIEW.md`
record) found and fixed 2 real issues: a missing cost-estimate/approval
record in the design doc, and the overshoot script's search bound not
matching `align_segment`'s real two-step bounded-search algorithm
(fixed; re-verified the reported numbers were unchanged by the fix).

No production behavior changed - `scene_analysis.py`/`text_segmenter.py`
untouched, per `forbidden_actions: implement_production_prompt_change`.

Opened PR #420 (branch
`xenotaur/spike/wi-segment-0101-paragraph-boundary-prompt-consistency`).

# Validation

- `scripts/format --check --diff` / `scripts/lint` - clean (LCATS conda env)
- `python -m unittest experiments.03_cross_segment_relation_pilot.reworded_boundary_prompt_test` - 4/4 pass
- Full `lcats` test suite - 2247/2248 pass (1 pre-existing, unrelated
  flake: `test_seed_affects_nndsvda_initialization`, NMF seed sensitivity
  in topic modeling - untouched by this PR, verified via `git status`
  that no topic-modeling files were modified)
- `lrh validate` - 0 errors, 299 warnings (pre-existing baseline)

# Follow-up

- Whether a follow-on `deliverable` WI combining this reworded prompt
  with `WI-SEGMENT-0098`'s window-widening recommendation is worth filing
  is an open decision, not resolved here.
- `session_transcript` still `pending` - update to the durable session
  pointer before landing.
