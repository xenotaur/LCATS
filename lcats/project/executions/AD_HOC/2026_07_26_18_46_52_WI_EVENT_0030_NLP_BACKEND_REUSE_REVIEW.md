---
execution_id: 2026_07_26_18_46_52_WI_EVENT_0030_NLP_BACKEND_REUSE_REVIEW
prompt_id: PROMPT(AD_HOC:WI_EVENT_0030_NLP_BACKEND_REUSE_REVIEW)[2026-07-26T18:46:25-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_07_26_18_37_26_WI_EVENT_0030_PILOT_NLP_BACKEND_REUSE
pr: https://github.com/xenotaur/LCATS/pull/165
commit: 786c4d51
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/165
session_transcript: pending
created_at: 2026-07-26T18:46:52-04:00
---

# Summary

Address PR #165 review feedback — two reviewers independently flagged that this PR's own NLP-backend-reuse fix made the PR's own doc claims about `elapsed_seconds` timing stale, plus a stale docstring.

# Result

- **P2 (chatgpt-codex-connector + copilot, same issue from two reviewers): the "expect 1-5 real seconds per story" claim (written earlier in this same PR) became stale the moment the reuse fix landed** — model/pipeline loading now happens once in `main()`, before the per-story timer starts, so per-story `elapsed_seconds` no longer includes it and will typically be well under a second for spaCy. Fixed by: (1) adding explicit `Loading NLP backend: <name>...`/`NLP backend ready: <name>` console prints in `main()`, since spaCy has no loading banner of its own to rely on; (2) rewriting `running_the_pilot.md`'s 2b section to point at those prints as confirmation instead of `elapsed_seconds`, and to state plainly that a small `elapsed_seconds` now is expected and does not mean spaCy didn't run; (3) added a note to 2c clarifying Stanza's own loading banner should now print once total, not once per story (a regression signal if seen again).
- **`_run_erw_pipeline`'s docstring still said "with `model` correctly propagated to every ERW extractor"** — stale after this PR removed the `model` parameter from that function's signature (model is now baked into the pre-built `extractors` passed in). Rewrote the docstring's opening to describe the actual current signature.

# Validation

- `black --check`/`ruff check` on `run_pilot.py` — clean.
- `scripts/test` — 1436 tests pass. `lrh validate` — 0 errors, 43 pre-existing unrelated warnings.
- Verified the new print statements appear exactly once, before any story, in a real `--dry-run --nlp-backend spacy` run.

# Follow-up

- `session_transcript: pending` should be updated to `claude-app:<session-id>` after this session ends.
- Proceed to `/lrh-confirm-fixes https://github.com/xenotaur/LCATS/pull/165` to verify fixes against the current diff and resolve review threads, then the merge gate, then `/lrh-closeout`.
