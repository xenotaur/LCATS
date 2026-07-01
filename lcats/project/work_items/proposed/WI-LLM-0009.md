---
id: WI-LLM-0009
title: Migrate assess.py and assess_cli.py to LLMBackend
status: active
priority: high
owner: unassigned
linked_workstream: WORKSTREAM-LLM-BACKEND
linked_design: DESIGN-LLM-BACKEND
depends_on: [WI-LLM-0007]
---

# Work Item: WI-LLM-0009

## Objective
Migrate `lcats/lcats/analysis/corpus/assess.py` and `assess_cli.py` to use
an injected `LLMBackend` instead of constructing an `anthropic.Anthropic`
client internally. After this PR, `assess.py` has no direct dependency on
any specific SDK.

## Scope

Modified files:
- `lcats/lcats/analysis/corpus/assess.py`
  - `assess_story(file_path, genre, client, ...)` →
    `assess_story(file_path, genre, backend: LLMBackend, ...)`
  - Replace `client.messages.stream(...)` block with `backend.complete(...)`
    (see DESIGN-LLM-BACKEND for exact diff)
  - Extract `a = result.tool_result` instead of `a = tool_block.input`
  - Remove `import anthropic` (was a deferred import inside `assess_cli.py`'s
    `run()`; `assess.py` itself never imported it directly — verify and remove
    any remnant)

- `lcats/lcats/analysis/corpus/assess_cli.py`
  - Replace `anthropic.Anthropic(api_key=api_key)` construction with
    `AnthropicBackend(api_key=api_key)`
  - Remove the `try: import anthropic / except ImportError` guard; that logic
    moves inside `AnthropicBackend.__init__` (which raises `ImportError` with
    the same message if the package is absent)
  - The `--model` argument already flows through `assess_story`; no change

New files:
- `tests/analysis_tests/assess_test.py` (new, or expand existing)
  - `assess_story(..., backend=FakeBackend(tool_result={...}))` round-trip test
  - Error path: `FakeBackend` raises exception → `AssessmentResult.error` populated
  - Dry-run path: `run_preflight()` (no backend involved)

## Acceptance Criteria
- `assess_story` accepts any `LLMBackend`, not just Anthropic
- `assess_story(..., backend=FakeBackend(tool_result=SAMPLE_RESULT))` returns
  a correct `AssessmentResult` without any API call
- `assess_cli.run(parsed_args)` uses `AnthropicBackend` when `ANTHROPIC_API_KEY`
  is set and `--dry-run` is not passed
- Missing `anthropic` package still produces a clear error message (moved
  into `AnthropicBackend.__init__`)
- Dry-run path (`--dry-run`) still works without any backend construction
- All existing `assess_cli` behavior is unchanged from the user's perspective
- `lcats assess --genre 'science fiction' --dry-run <dir>` still lists files
  and QA findings correctly

## Notes
- `assess.py` currently has `run_preflight()` as a separate function that
  does not touch the client; this is unaffected.
- The `--model` flag in `assess_cli.py` passes the model string through to
  `assess_story`; after this migration, passing `--model gpt-4o` with an
  `AnthropicBackend` would silently use the wrong model family. This is a
  known limitation: model strings are provider-specific, and the CLI currently
  only constructs `AnthropicBackend`. Mixing will be addressed when a
  `--backend` flag is introduced (out of scope here).
