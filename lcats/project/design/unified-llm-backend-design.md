---
id: DESIGN-LLM-BACKEND
title: Unified LLM Backend Abstraction
status: proposed
author: Anthony Francis
date: 2026-06-29
linked_workstream: WORKSTREAM-LLM-BACKEND
---

# Design: Unified LLM Backend Abstraction

## Motivation

LCATS currently makes LLM API calls via three distinct patterns across at
least five files, using two different provider SDKs (OpenAI and Anthropic).
For scientific model-comparison experiments — particularly the WorldCon 2026
analysis comparing results across models on the four target genres — we need
a single injectable backend so that one model string switch changes every LLM
call in the pipeline uniformly and reproducibly.

The goal is not to abstract away the provider — it is to make the provider an
experiment parameter.

## Prior Art and Best Practices

- **Dependency Injection + `typing.Protocol` (PEP 544, Python 3.8+)**: structural
  subtyping means any class implementing the method signature satisfies the
  protocol without inheritance coupling. The `FakeBackend` test double needs
  zero imports from production code.
- **Adapter pattern (GoF, "Design Patterns", 1994, ch. 4)**: the
  `OpenAIBackend` and `AnthropicBackend` implementations adapt the normalized
  `complete()` call to each provider's wire format.
- **Reproducibility requirements (Bender et al., FAccT 2021; Hutchinson et al.,
  NeurIPS 2021)**: pinned model version strings, logged token counts, and
  recorded full request/response metadata are the minimum bar for publishable
  model-comparison results.
- **LiteLLM field mapping** (MIT license, github.com/BerriAI/litellm): used
  as a reference for the OpenAI↔Anthropic field translation table; not adopted
  as a dependency because transparency over the exact wire format is a
  scientific requirement.

## Existing Call Patterns

| Pattern | File(s) | API method | JSON enforcement |
|---|---|---|---|
| A1 — direct, exploratory | `KMo/scenes.py`, `KMo/analyze.py` | `chat.completions.create` | None (prompted) |
| A2 — direct, packaged | `lcats/lcats/extraction.py` | `chat.completions.create` | None (prompted) |
| B — wrapped | `llm_extractor.py` via `scene_analysis.py`, `story_analysis.py` | `chat.completions.create` | `response_format=json_object` |
| C — tool use | `analysis/corpus/assess.py` | `messages.stream` + tool | Tool use schema |

Pattern B already accepts `client: Any` by duck typing; replacing it is the
smallest possible change. Pattern C constructs its own client internally and
must be updated to accept an injected backend.

Pattern A1 lives in exploratory `KMo/` scripts and is intentionally excluded
from this migration (see Non-Goals). Pattern A2 (`extraction.py`) is
distinct from A1: it lives in the packaged `lcats` library, ships with its
own unit tests (`tests/extraction_test.py`), and is importable independently
of `KMo/`. Even though its only current caller is `KMo/analyze.py`, it is
part of the public package surface and is **in scope** for migration — see
WI-LLM-0008. Excluding it would leave a packaged, production-reachable LLM
call path outside the unified backend, silently defeating model-comparison
runs that happen to exercise it.

## High-Level Design

```
lcats/lcats/llm/
├── __init__.py           re-exports all public names
├── backend.py            LLMBackend Protocol + BackendResponse dataclass
├── openai_backend.py     OpenAIBackend
├── anthropic_backend.py  AnthropicBackend
└── fake_backend.py       FakeBackend (test double)
```

All callers receive a `backend: LLMBackend` at construction time. The run
script or CLI constructs the concrete backend once and passes it down.

```
run script / CLI
  │  backend = AnthropicBackend(api_key=..., use_streaming=True)
  ▼
  JSONPromptExtractor(backend, ...)   assess_story(..., backend=backend, ...)
          │                                        │
          └──────── backend.complete(               └──── backend.complete(
                      system, messages,                     system, messages,
                      model, temperature,                   model, tool=SCHEMA,
                    ) → BackendResponse                    ) → BackendResponse

BackendResponse
  .text           str   (populated when tool=None)
  .tool_result    dict  (populated when tool provided; None otherwise)
  .model          str   (exact model string echoed from API)
  .input_tokens   int
  .output_tokens  int
  .raw            Any   (raw SDK response; repr=False)
```

## Protocol Definition

```python
@dataclass
class BackendResponse:
    text: str
    tool_result: dict | None
    model: str
    input_tokens: int
    output_tokens: int
    raw: Any = field(repr=False)

@runtime_checkable
class LLMBackend(Protocol):
    def complete(
        self,
        *,
        system: str,
        messages: list[dict],
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        tool: dict | None = None,
    ) -> BackendResponse: ...
```

`@runtime_checkable` permits `isinstance(backend, LLMBackend)` checks in
tests. One method, no inheritance required.

## Provider Translation

### OpenAI

```
system    → prepend {"role":"system","content":system} to messages
tool      → tools=[{"type":"function","function":{"name":..., "parameters": tool["input_schema"]}}]
            tool_choice={"type":"function","function":{"name":tool["name"]}}
no tool   → response_format={"type":"json_object"}
result    → choices[0].message.content               (no tool)
            json.loads(choices[0].message.tool_calls[0].function.arguments)  (tool)
tokens    → usage.prompt_tokens, usage.completion_tokens
```

### Anthropic

```
system    → top-level system= kwarg (not in messages list)
tool      → tools=[tool]  (Anthropic schema is already the canonical form)
            tool_choice={"type":"tool","name":tool["name"]}
no tool   → no response_format; prompt instructs JSON
result    → next(b.text for b in message.content if b.type=="text")     (no tool)
            next(b.input for b in message.content if b.type=="tool_use") (tool)
tokens    → usage.input_tokens, usage.output_tokens
streaming → use messages.stream(...).get_final_message() to avoid timeouts
            on large story inputs; transparent to caller
```

## Changes to Existing Code

### `lcats/lcats/analysis/llm_extractor.py`

- `__init__` parameter `client: Any` → `backend: LLMBackend`
- One call site (line 261) changes:
  ```python
  # before
  response = self.client.chat.completions.create(**kwargs)
  raw_output = response.choices[0].message.content
  # after
  result = self.backend.complete(
      system=messages[0]["content"], messages=messages[1:],
      model=model, temperature=self.temperature,
  )
  raw_output = result.text
  ```
- `force_json` parameter becomes a no-op (backend handles mode selection)
  and is deprecated with a warning.
- Add `max_tokens: int = 4096` to the extractor constructor; passed through
  to `backend.complete`.

### `lcats/lcats/extraction.py`

- `extract_from_story(story_text, template, client, model_name=..., temperature=...)`
  → `extract_from_story(story_text, template, backend: LLMBackend, model_name=..., temperature=...)`
- Call site (currently `client.chat.completions.create(...)`) changes the
  same way as `llm_extractor.py`:
  ```python
  # after
  result = backend.complete(
      system=template.system_template,
      messages=[{"role": "user", "content": ...}],
      model=model_name, temperature=temperature,
  )
  raw_output = result.text
  ```
- `tests/extraction_test.py` mocks replaced with `FakeBackend`.
- `KMo/analyze.py` (the only current caller) is out of scope per Non-Goals;
  it continues to construct its own `openai.OpenAI()` client directly and is
  unaffected by this migration. If `KMo/analyze.py` is later migrated, it
  would construct an `OpenAIBackend` and call the updated `extract_from_story`.

### `lcats/lcats/analysis/corpus/assess.py`

- `assess_story(file_path, genre, client, ...)` → `assess_story(file_path, genre, backend: LLMBackend, ...)`
- Replace `client.messages.stream(...)` block with:
  ```python
  result = backend.complete(
      system=system_prompt,
      messages=[{"role": "user", "content": user_message}],
      model=model, max_tokens=2048, tool=ASSESSMENT_TOOL,
  )
  a = result.tool_result
  ```

### `lcats/lcats/analysis/corpus/assess_cli.py`

- Replace `anthropic.Anthropic(api_key=api_key)` construction with
  `AnthropicBackend(api_key=api_key)`.
- Guard for missing `anthropic` package moves inside `AnthropicBackend.__init__`.

### Tests

- All existing test mocks of `client.chat.completions.create` are replaced
  with `FakeBackend(response_text="...", tool_result={...})`.
- New tests for `OpenAIBackend` and `AnthropicBackend` mock the SDK clients
  they construct internally.

## Implementation Sequence

The migration is split across four work items to allow independent review and
merging:

1. **WI-LLM-0007** — Create `lcats/llm/` package: Protocol, BackendResponse,
   FakeBackend, OpenAIBackend, AnthropicBackend, `__init__.py`, full unit tests.
   No existing code changes in this PR.

2. **WI-LLM-0008** — Migrate `JSONPromptExtractor` (Pattern B) and
   `extraction.py` (Pattern A2) to `LLMBackend`. Update test mocks. Deprecate
   `force_json`. Depends on WI-LLM-0007.

3. **WI-LLM-0009** — Migrate `assess.py` and `assess_cli.py` to `LLMBackend`.
   Depends on WI-LLM-0007.

4. **WI-LLM-0010** — Side-by-side comparison dry run: assess a small set of
   stories with both backends and confirm output schema is identical. Validates
   the migration end-to-end. Depends on WI-LLM-0008 and WI-LLM-0009.

## Open Question

Should `AnthropicBackend.complete()` use the streaming call (`messages.stream`)
or the blocking call (`messages.create`)? Streaming avoids gateway timeouts on
large story inputs (typical bodies are 40–100K chars). Blocking calls are
simpler to instrument for wall-clock timing. Recommended default: streaming,
with a constructor flag `use_streaming: bool = True` for opt-out.

## Non-Goals

- LiteLLM, LangChain, or any third-party routing layer.
- Migration of `KMo/analyze.py` or `KMo/scenes.py` (exploratory scripts;
  **note:** `extraction.py`, which `KMo/analyze.py` imports, is in scope —
  see "Existing Call Patterns" and WI-LLM-0008).
- Migration of `notebooks/` scripts.
- Replacing `tiktoken` usage (local token counting; no API call).
- Adding new LLM providers beyond OpenAI and Anthropic in this work.

## Dependency Scope

This migration introduces a runtime dependency on `openai` (currently absent
from `pyproject.toml`; `anthropic` was added in PR #98). The `pyproject.toml`
edit is explicitly in scope for WI-LLM-0007 — see that work item's Scope
section. Without it, `OpenAIBackend` can be merged without a declared
dependency, and any environment that installs from `pyproject.toml` alone
would fail at `OpenAIBackend` construction time.
