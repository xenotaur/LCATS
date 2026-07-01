---
id: WI-LLM-0008
title: Migrate JSONPromptExtractor and extraction.py to LLMBackend
status: active
priority: high
owner: unassigned
linked_workstream: WORKSTREAM-LLM-BACKEND
linked_design: DESIGN-LLM-BACKEND
depends_on: [WI-LLM-0007]
---

# Work Item: WI-LLM-0008

## Objective
Migrate `lcats/lcats/analysis/llm_extractor.py` (Pattern B) and
`lcats/lcats/extraction.py` (Pattern A2) to accept and use an `LLMBackend`
instead of a raw OpenAI-compatible client. Update test mocks to use
`FakeBackend`. The `llm_extractor.py` migration is the highest-leverage
piece: it covers `scene_analysis.py` and `story_analysis.py` by
transitivity. `extraction.py` is included because it is packaged library
code (not an exploratory `KMo/` script) and is part of the public `lcats`
package surface — see DESIGN-LLM-BACKEND, "Existing Call Patterns."

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

- `lcats/lcats/extraction.py`
  - `extract_from_story(story_text, template, client, model_name=..., temperature=...)`
    → `extract_from_story(story_text, template, backend: LLMBackend, model_name=..., temperature=...)`
  - Call site (`client.chat.completions.create(...)`) updated to
    `backend.complete(...)` (see DESIGN-LLM-BACKEND)
  - `ExtractionResult.response` (currently the raw OpenAI response object)
    becomes the raw `BackendResponse.raw` value — same field, normalized source

- `tests/extraction_test.py`
  - Replace `Mock()` / `client.chat.completions.create` mocks with `FakeBackend`
  - Existing assertions on `result.model_name`, `result.extracted_output`,
    `result.parsing_error`, `result.summary()` remain unchanged

No changes to `scene_analysis.py` or `story_analysis.py` themselves — they
pass `client` through to `JSONPromptExtractor`; renaming the parameter to
`backend` is a non-breaking keyword rename that can be done here or deferred.

`KMo/analyze.py`, the only current caller of `extract_from_story`, is **not**
modified in this work item (it remains out of scope per the design's
Non-Goals) and will break if run against the new signature until it is
separately updated or retired. This is acceptable because `KMo/analyze.py`
is exploratory and not part of any tested or scheduled pipeline run.

## Acceptance Criteria
- All existing tests pass after mock replacement
- `JSONPromptExtractor(FakeBackend(...), ...)` works end-to-end
- `force_json=True` (default) emits `DeprecationWarning` and is silently
  ignored (backend handles JSON mode)
- `force_json=False` (explicit) emits `DeprecationWarning` but does not error
- `BackendResponse.model` flows into `result["model_name"]`
- `BackendResponse.input_tokens` / `output_tokens` flow into `result["usage"]`
  (normalized form: `{"input_tokens": N, "output_tokens": N}`)
- `extraction.extract_from_story(..., backend=FakeBackend(...))` works
  end-to-end and all tests in `tests/extraction_test.py` pass after mock
  replacement
- `rg "chat.completions.create" lcats/lcats/` returns no matches outside
  `lcats/lcats/llm/openai_backend.py` (confirms no packaged-library call site
  was missed)

## Notes
- The `_normalize_api_error` logic in `JSONPromptExtractor` remains in place
  for this PR. Moving it into the backend is a separate future improvement.
- Deprecating `force_json` cleanly: emit the warning in `__init__` if
  `force_json` is explicitly passed (even `True`), so callers know to remove it.
- The `make_segment_extractor(client)` and `make_semantics_extractor(client)`
  factory functions in `scene_analysis.py` use the name `client` — those can
  be renamed to `backend` as a cosmetic follow-on; not required for correctness.
