---
execution_id: 2026_06_30_23_17_22_WI_LLM_0008_MIGRATE_EXTRACTOR_REVIEW
prompt_id: PROMPT(AD_HOC:WI_LLM_0008_MIGRATE_EXTRACTOR_REVIEW)[2026-06-30T23:01:57-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_06_30_22_17_14_WI_LLM_0008_MIGRATE_EXTRACTOR
pr: 101
commit: 2e5544e
created_at: 2026-06-30T23:17:22-04:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/101
session_transcript: claude-app:d400d14b-0041-4827-8ef9-a8da8fdba9d6
---

# Summary

Addressed four review comments on PR #101 (WI-LLM-0008 migration of
JSONPromptExtractor and extraction.py to LLMBackend).

# Result

**Comment 1 (chatgpt-codex-connector P2) — client= alias:** Added deprecated
`client=` keyword alias to `JSONPromptExtractor.__init__`. Callers using
`client=client` (e.g. notebook `11_analyze_corpus.ipynb:1158`) now receive a
`DeprecationWarning` and continue to work instead of raising `TypeError`.
Passing both `backend=` and `client=` raises `TypeError`. Missing both raises
`TypeError`. Three new tests added.

**Comment 2 (copilot) — docstring overclaim:** Fixed `force_json` docstring:
"always returns JSON" changed to "requests JSON-friendly text; callers are
still responsible for parsing the response."

**Comment 3 (copilot) — warning message overclaim:** Fixed `DeprecationWarning`
text for `force_json` with the same correction.

**Comment 4 (copilot) — unused import:** Removed the unused
`from lcats.llm import backend as llm_backend  # noqa: F401` line from
`lcats/extraction.py`.

# Validation

- `black --check` on changed files: passes
- `ruff check` on changed files: passes
- `scripts/test`: 1216 tests passing (0 failures)
  (Note: `scripts/lint` reports pre-existing `metadata.py` formatting drift,
  unrelated to this PR — same baseline as before these changes.)

# Follow-up

- PR #101 needs review and merge
- `session_transcript: pending` should be updated to
  `claude-app:d400d14b-0041-4827-8ef9-a8da8fdba9d6` after session ends
