---
execution_id: 2026_06_30_22_17_14_WI_LLM_0008_MIGRATE_EXTRACTOR
prompt_id: PROMPT(WI-LLM-0008:WI_LLM_0008_MIGRATE_EXTRACTOR)[2026-06-30T22:16:01-04:00]
work_item: WI-LLM-0008
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/101
commit: d998b2e
created_at: 2026-06-30T22:17:14-04:00
agent: claude_app
instruction_source: project/work_items/proposed/WI-LLM-0008.md
session_transcript: claude-app:d400d14b-0041-4827-8ef9-a8da8fdba9d6
---

# Summary

Migrated `JSONPromptExtractor` (Pattern B) and `extract_from_story` (Pattern A2)
to use `LLMBackend` instead of raw OpenAI client calls. Renamed `client` to
`backend` throughout the call stack (four factory functions + both extractor
entry points). Deprecated `force_json=` with an `_UNSET` sentinel. Updated five
test files to use `FakeBackend` stubs instead of `MagicMock`/`Mock`.

# Result

- `lcats/lcats/analysis/llm_extractor.py` — `JSONPromptExtractor` now accepts
  `backend` (LLMBackend Protocol) instead of `client`. `force_json` deprecated.
  Result dict now uses `BackendResponse.model`, `BackendResponse.raw`, and
  normalized `{"input_tokens": N, "output_tokens": N}` usage dict.
- `lcats/lcats/extraction.py` — `extract_from_story` parameter renamed
  `client` → `backend`; call site uses `backend.complete()`.
- `lcats/lcats/analysis/scene_analysis.py` — `make_segment_extractor` and
  `make_semantics_extractor` renamed `client` → `backend`, dropped `force_json=True`.
- `lcats/lcats/analysis/story_analysis.py` — `make_doc_classification_extractor`
  renamed `client` → `backend`, dropped `force_json=True`.
- `lcats/lcats/analysis/story_processors.py` — `make_annotated_segment_extractor`
  renamed `client` → `backend`.
- Five test files updated: `FakeBackend` replaces `MagicMock`/`Mock` for all
  backend/client stubs. `llm_extractor_test.py` fully rewritten.

No bare `chat.completions.create` calls remain outside `lcats/llm/openai_backend.py`.

# Validation

- `black --check`: all changed files pass
- `ruff check`: all changed files pass
- `scripts/test`: 1213 tests passing (0 failures)
- `rg "chat.completions.create" lcats/lcats/`: only in `lcats/llm/openai_backend.py`

# Follow-up

- PR #101 needs review and merge
- After merge: move WI-LLM-0008 to `resolved/`; update `status: resolved` with commit hash
- WI-LLM-0009: Migrate `assess.py` / `assess_cli.py` to LLMBackend (next in workstream)
