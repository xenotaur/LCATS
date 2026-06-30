---
id: WI-LLM-0007
title: Create lcats/llm package with LLMBackend Protocol and provider implementations
status: active
priority: high
owner: unassigned
linked_workstream: WORKSTREAM-LLM-BACKEND
linked_design: DESIGN-LLM-BACKEND
---

# Work Item: WI-LLM-0007

## Objective
Create the `lcats/lcats/llm/` package containing the `LLMBackend` Protocol,
`BackendResponse` dataclass, `FakeBackend` test double, `OpenAIBackend`, and
`AnthropicBackend` — with full unit tests. The only existing file touched is
`pyproject.toml`, to declare the new `openai` runtime dependency; no other
existing code is changed in this PR.

## Scope

New files:
- `lcats/lcats/llm/__init__.py` — module docstring only, no symbol
  re-exports. **Deviation from original plan:** `STYLE.md` §3 requires
  "always import modules, not symbols" for LCATS code (e.g.
  `from lcats.llm import backend` then `backend.LLMBackend`, not
  `from lcats.llm import LLMBackend`). The originally planned re-export
  list would have violated this; callers import each submodule directly.
- `lcats/lcats/llm/backend.py` — `LLMBackend` Protocol + `BackendResponse`
  dataclass (see DESIGN-LLM-BACKEND for signatures)
- `lcats/lcats/llm/openai_backend.py` — `OpenAIBackend` implementation
- `lcats/lcats/llm/anthropic_backend.py` — `AnthropicBackend` implementation;
  defaults to streaming (`use_streaming=True`)
- `lcats/lcats/llm/fake_backend.py` — `FakeBackend` with `self.calls` list
  for test assertion
- `tests/llm_tests/backend_test.py` — Protocol isinstance check, FakeBackend
  call recording. **Deviation from original plan:** filename uses the
  project's `*_test.py` suffix convention (`tests/AGENTS.md`), not the
  `test_*.py` prefix originally specified.
- `tests/llm_tests/openai_backend_test.py` — unit tests stubbing
  `openai.OpenAI`
- `tests/llm_tests/anthropic_backend_test.py` — unit tests stubbing
  `anthropic.Anthropic`

Modified files:
- `pyproject.toml` — add `"openai"` to `dependencies`. This is the only
  existing-file edit in this work item; it is required because
  `OpenAIBackend.__init__` imports `openai` and would otherwise be merged
  without a declared runtime dependency, causing import/construction failures
  in any environment installed strictly from `pyproject.toml`.

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
- `"openai"` is present in `pyproject.toml`'s `dependencies` list

## Notes
- `anthropic` was added in PR #98 and is already present.
- `FakeBackend` is a test utility; keep it in `lcats/llm/` (not `tests/`) so
  downstream test files can import it without test-path hacks.
- See DESIGN-LLM-BACKEND for the exact Protocol signature, field mapping
  tables, and the open question on streaming vs blocking.
