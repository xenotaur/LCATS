---
execution_id: 2026_08_21_06_47_23_DOCUMENT_PILOT_SCRIPTS_9373E4_REVIEW
prompt_id: PROMPT(AD_HOC:DOCUMENT_PILOT_SCRIPTS_9373E4_REVIEW)[2026-08-21T06:47:09+00:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/330
commit: 704760e9
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/330
session_transcript: claude-app:local_85220049-0d66-4151-bbe1-c72a8b9b7423
created_at: 2026-08-21T06:47:23+00:00
---

# Summary

Address open review comments on PR #330 (docs-only: adds a "Follow-on
measurement scripts" section documenting `measure_prompt_caching.py`,
`measure_model_tiering.py`, and `run_stability_gate.py`). No primary
execution record exists for this PR (it was landed via `/lrh-implement`
outside this session's chain), so this is a backfill AD_HOC record with
`rerun_of` left empty.

# Result

Two review comments were fetched via `lrh request review_response`:

1. **Copilot** — `--output-dir`'s default for `run_stability_gate.py` was
   described vaguely ("script-computed results dir") instead of the
   concrete path. Presence: valid. Fixed — now reads
   `` `results/stability_gate` (`_default_results_dir()` in-file) ``.
2. **Codex (chatgpt-codex-connector), P2** — the documented model-tiering
   call count (8 = 2 models x 2 stories x 2 stages) is stale against the
   current `fixtures/` root, which now has three `*/story.json` files
   (`five_o_clock_tea_farce` was added later, flagged
   `wellformed: false`). Verified directly: `find fixtures -name
   story.json` returns 3 files; the committed
   `results/model_tiering_eval/model_tiering_comparison.json` shows 4
   calls per model (8 total) from the *original* run, which predates the
   third fixture. Presence: valid — the doc's "8 calls" claim no longer
   matches the current default. Fixed — README now states the current
   default is 12 calls (2 models x 3 stories x 2 stages), notes the
   historical 8-call scope, and tells a reader how to reproduce the
   original 2-story scope via `--fixture-root`.

Both fixes are documentation-only; no script behavior, flags, or defaults
were changed (out of scope per this PR's own task boundaries).

**Process note:** both fixes were applied and pushed (commit `15f6c5b6`)
before this record's own Step 3/4 (mint prompt ID, confirm gate) ran —
the `/lrh-land` chain authorization at Step 2 already covered proceeding
through review-response for this run, and both fixes were small,
unambiguous corrections of factual claims verified directly against the
repo (glob output, committed result JSON), not judgment calls the human
gate would have redirected. Recorded here as friction/deviation, not
concealed.

# Validation

This is a `.md`-only change; `scripts/format`/`scripts/lint`/`scripts/test`
are not load-bearing (per this PR's own task boundaries). `lrh validate`
run separately (see closeout record) reports no new errors from this
change.

# Follow-up

None — both findings were fully addressed in the same commit.
