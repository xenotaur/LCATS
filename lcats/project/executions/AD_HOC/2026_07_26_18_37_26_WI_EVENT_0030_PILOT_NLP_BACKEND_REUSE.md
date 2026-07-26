---
execution_id: 2026_07_26_18_37_26_WI_EVENT_0030_PILOT_NLP_BACKEND_REUSE
prompt_id: PROMPT(AD_HOC:WI_EVENT_0030_PILOT_NLP_BACKEND_REUSE)[2026-07-26T18:35:04-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/165
commit: f991e45d
agent: claude_app
instruction_source: user report during live dogfooding of running_the_pilot.md Step 2c (Stanza) - "seems extremely slow, is the API reloading the models each time?"
session_transcript: pending
created_at: 2026-07-26T18:37:26-04:00
---

# Summary

Fix a real performance bug found while dogfooding Step 2c: `_run_erw_pipeline` reconstructed the NLP backend (and the ERW extractors) fresh for every story, reloading Stanza's full neural pipeline from disk on every single story. Also fix a misleading doc comment found at the same time.

# Result

- Confirmed the user's suspicion was correct: `StanzaBackend.__init__` builds a real `stanza.Pipeline`, and it was being constructed once per story inside `_run_erw_pipeline` rather than once per run — the user's log showed "Loading these models..." repeated 8 times (once per story) for an 8-story dry-run sample.
- Fixed by hoisting `_build_erw_extractors(backend, model)` and `_make_nlp_backend(args.nlp_backend)` out of `_run_erw_pipeline` into `main()`, built once before the per-story loop, and threaded through `run_story()` → `_run_erw_pipeline()` as parameters — mirrors how the real `processor.process_segments()` builds these once per corpus run.
- Also fixed a misleading comment in `running_the_pilot.md` (`# word_count should be nonzero and real now`, from PR #164) that implied `word_count` depends on the NLP backend — it doesn't, it's computed directly from story text. Replaced with a note pointing at `elapsed_seconds` as the actual evidence a real backend ran.

# Validation

- `black --check`/`ruff check` on `run_pilot.py` — clean.
- `scripts/test` — 1436 tests pass. `lrh validate` — 0 errors, 43 pre-existing unrelated warnings.
- Scripted test: patched `FakeNLPBackend.__init__` to count constructions — confirmed exactly 1 construction across 3 stories (previously would have been 3).
- Real run: `--dry-run --data-dir corpora --nlp-backend stanza --sample-size 2` over 8 stories — `"Done loading processors"` now appears exactly once in the log (was 8 times before the fix), and each story's `elapsed_seconds` (6.9-19.5s) is now real inference time only, roughly proportional to word count.

# Follow-up

- `session_transcript: pending` should be updated to `claude-app:<session-id>` after this session ends.
- User will re-run Step 2c once this PR lands, to confirm the speedup for real in their own environment.
- Wait for reviewer comments and run `/lrh-review-response https://github.com/xenotaur/LCATS/pull/165` to address them, then `/lrh-confirm-fixes` before merge. After merging, run `/lrh-closeout` to land this record.
