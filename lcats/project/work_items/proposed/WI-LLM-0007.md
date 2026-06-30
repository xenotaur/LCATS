---
id: WI-LLM-0007
title: Create lcats/llm package with LLMBackend Protocol and provider implementations
status: proposed
priority: high
owner: unassigned
linked_workstream: WORKSTREAM-LLM-BACKEND
linked_design: DESIGN-LLM-BACKEND
---

# Work Item: WI-LLM-0007

## Objective
Create the `lcats/lcats/llm/` package containing the `LLMBackend` Protocol,
`BackendResponse` dataclass, `FakeBackend` test double, `OpenAIBackend`, and
`AnthropicBackend` — with full unit tests. No existing code is changed in
this PR.

## Scope

New files:
- `lcats/lcats/llm/__init__.py` — re-exports `LLMBackend`, `BackendResponse`,
  `OpenAIBackend`, `AnthropicBackend`, `FakeBackend`
- `lcats/lcats/llm/backend.py` — `LLMBackend` Protocol + `BackendResponse`
  dataclass (see DESIGN-LLM-BACKEND for signatures)
- `lcats/lcats/llm/openai_backend.py` — `OpenAIBackend` implementation
- `lcats/lcats/llm/anthropic_backend.py` — `AnthropicBackend` implementation;
  defaults to streaming (`use_streaming=True`)
- `lcats/lcats/llm/fake_backend.py` — `FakeBackend` with `self.calls` list
  for test assertion
- `tests/llm_tests/test_backend.py` — Protocol isinstance check, FakeBackend
  call recording
- `tests/llm_tests/test_openai_backend.py` — unit tests mocking `openai.OpenAI`
- `tests/llm_tests/test_anthropic_backend.py` — unit tests mocking
  `anthropic.Anthropic`

No existing files are modified.

## Acceptance Criteria
- `isinstance(FakeBackend(), LLMBackend)` is `True` (runtime_checkable)
- `isinstance(OpenAIBackend(), LLMBackend)` is `True`
- `isinstance(AnthropicBackend(), LLMBackend)` is `True`
- `OpenAIBackend.complete(tool=None)` passes `response_format=json_object`
- `OpenAIBackend.complete(tool=SCHEMA)` passes correct `tools` + `tool_choice`
- `AnthropicBackend.complete(tool=None)` passes system as top-level kwarg
- `AnthropicBackend.complete(tool=SCHEMA)` passes tool in Anthropic format
- `BackendResponse.model` echoes the model string from the SDK response
- `BackendResponse.input_tokens` and `output_tokens` are normalized from
  provider-specific field names
- `FakeBackend.calls` records each call's kwargs for assertion
- All tests pass; no live API calls in tests (mocked SDKs throughout)

## Notes
- `openai` is not currently in `pyproject.toml` dependencies; add it.
- `anthropic` was added in PR #98 and is already present.
- `FakeBackend` is a test utility; keep it in `lcats/llm/` (not `tests/`) so
  downstream test files can import it without test-path hacks.
- See DESIGN-LLM-BACKEND for the exact Protocol signature, field mapping
  tables, and the open question on streaming vs blocking.
