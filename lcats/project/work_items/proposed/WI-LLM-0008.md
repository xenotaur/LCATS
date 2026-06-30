---
id: WI-LLM-0008
title: Migrate JSONPromptExtractor to LLMBackend
status: proposed
priority: high
owner: unassigned
linked_workstream: WORKSTREAM-LLM-BACKEND
linked_design: DESIGN-LLM-BACKEND
depends_on: WI-LLM-0007
---

# Work Item: WI-LLM-0008

## Objective
Migrate `lcats/lcats/analysis/llm_extractor.py` to accept and use an
`LLMBackend` instead of a raw OpenAI-compatible client. Update test mocks
to use `FakeBackend`. This is the highest-leverage migration: it covers
`scene_analysis.py` and `story_analysis.py` by transitivity.

## Scope

Modified files:
- `lcats/lcats/analysis/llm_extractor.py`
  - `__init__` parameter `client: Any` → `backend: LLMBackend`
  - Internal call site (line 261) updated (see DESIGN-LLM-BACKEND)
  - Add `max_tokens: int = 4096` constructor parameter; pass to `backend.complete`
  - Deprecate `force_json` with `DeprecationWarning`; keep parameter for one
    release to avoid breaking callers, but ignore it
  - Update `_classify_api_error` / `_normalize_api_error` to handle exceptions
    from both providers (Anthropic raises `anthropic.APIError`; OpenAI raises
    `openai.OpenAIError` — both have `status_code` attribute, so existing
    logic is compatible)

- `tests/analysis_tests/llm_extractor_test.py`
  - Replace `unittest.mock.MagicMock` / `client.chat.completions.create` mocks
    with `FakeBackend(response_text=...)`
  - Existing test assertions on `result["raw_output"]`, `result["extracted_output"]`,
    etc. remain unchanged

- `tests/analysis_tests/scene_analysis_test.py`
  - Replace client mock with `FakeBackend`

- `tests/analysis_tests/story_analysis_test.py`
  - Replace client mock with `FakeBackend`

- `tests/analysis_tests/story_processors_test.py`
  - Replace client mock with `FakeBackend`

No changes to `scene_analysis.py` or `story_analysis.py` themselves — they
pass `client` through to `JSONPromptExtractor`; renaming the parameter to
`backend` is a non-breaking keyword rename that can be done here or deferred.

## Acceptance Criteria
- All existing tests pass after mock replacement
- `JSONPromptExtractor(FakeBackend(...), ...)` works end-to-end
- `force_json=True` (default) emits `DeprecationWarning` and is silently
  ignored (backend handles JSON mode)
- `force_json=False` (explicit) emits `DeprecationWarning` but does not error
- `BackendResponse.model` flows into `result["model_name"]`
- `BackendResponse.input_tokens` / `output_tokens` flow into `result["usage"]`
  (normalized form: `{"input_tokens": N, "output_tokens": N}`)

## Notes
- The `_normalize_api_error` logic in `JSONPromptExtractor` remains in place
  for this PR. Moving it into the backend is a separate future improvement.
- Deprecating `force_json` cleanly: emit the warning in `__init__` if
  `force_json` is explicitly passed (even `True`), so callers know to remove it.
- The `make_segment_extractor(client)` and `make_semantics_extractor(client)`
  factory functions in `scene_analysis.py` use the name `client` — those can
  be renamed to `backend` as a cosmetic follow-on; not required for correctness.
