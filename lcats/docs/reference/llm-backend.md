# LLMBackend reference

`lcats.llm` (`lcats/lcats/llm/`) is the unified abstraction over LLM provider
APIs. Every LLM call in the packaged pipeline (`lcats.analysis.llm_extractor`,
`lcats.extraction`, `lcats.analysis.corpus.assess`) goes through an injected
`LLMBackend` instance, so switching providers or models is a call-site
argument, not a code change. Derived from
[`project/design/unified-llm-backend-design.md`](../../project/design/unified-llm-backend-design.md)
(`DESIGN-LLM-BACKEND`) and verified against the implementation in
`lcats/lcats/llm/`.

## Package layout

```
lcats/lcats/llm/
├── __init__.py           module docstring only; no re-exports
├── backend.py             LLMBackend Protocol + BackendResponse dataclass
├── openai_backend.py       OpenAIBackend
├── anthropic_backend.py    AnthropicBackend
└── fake_backend.py         FakeBackend (test double)
```

`lcats.llm.__init__` does not re-export any of these names. Import the
submodule directly, e.g. `from lcats.llm import anthropic_backend` then
`anthropic_backend.AnthropicBackend(...)` — `from lcats.llm import
LLMBackend` or `BackendResponse` will fail.

## `LLMBackend` Protocol

`lcats.llm.backend.LLMBackend` is a `typing.Protocol` (structural typing, not
inheritance) with one method:

```python
def complete(
    self,
    *,
    system: str,
    messages: list,
    model: str,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    tool: dict | None = None,
) -> BackendResponse: ...
```

| Parameter | Type | Description |
|---|---|---|
| `system` | `str` | System prompt text. |
| `messages` | `list[dict]` | Chat messages excluding the system prompt, e.g. `[{"role": "user", "content": "..."}]`. |
| `model` | `str` | Provider-specific model identifier. |
| `temperature` | `float` | Sampling temperature (default `0.2`). |
| `max_tokens` | `int` | Maximum tokens to generate (default `4096`). |
| `tool` | `dict \| None` | Optional single tool schema. When provided, the backend forces the model to call this tool and returns its arguments in `tool_result`. When `None`, the backend requests free-form JSON-friendly text in `text` instead. |

Being a `@runtime_checkable` Protocol means any object implementing
`complete()` with this signature satisfies `isinstance(obj, LLMBackend)` —
no explicit inheritance required.

## `BackendResponse`

```python
@dataclass
class BackendResponse:
    text: str
    tool_result: dict | None
    model: str
    input_tokens: int
    output_tokens: int
    raw: Any = field(repr=False, default=None)
```

| Field | Description |
|---|---|
| `text` | Free-text model output. Empty string when `tool` was provided. |
| `tool_result` | Structured tool-use output. `None` when no tool was used. |
| `model` | Exact model string echoed back by the provider's API response. |
| `input_tokens` | Input/prompt tokens reported by the API. |
| `output_tokens` | Output/completion tokens reported by the API. |
| `raw` | The raw, provider-specific SDK response object, for debugging. Excluded from `repr()`. |

## Providers

### `AnthropicBackend`

```python
from lcats.llm import anthropic_backend

backend = anthropic_backend.AnthropicBackend(api_key=None, use_streaming=True)
```

| Constructor argument | Description |
|---|---|
| `api_key` | Optional API key. When omitted, the Anthropic SDK reads `ANTHROPIC_API_KEY` from the environment. |
| `use_streaming` | Uses `messages.stream()` internally by default, to avoid gateway timeouts on large story inputs (typical bodies are 40–100K characters). Set `False` for a blocking `messages.create()` call instead. |

Raises `ImportError` at construction time if the `anthropic` package is not
installed.

**Temperature handling:** newer Claude models (`claude-opus-4-7`,
`claude-opus-4-8`, `claude-fable-5`, and later — any versioned model where
major > 4 or major == 4 and minor >= 7, plus all non-versioned model IDs)
reject the `temperature` parameter with an HTTP 400 error. `AnthropicBackend`
detects this from the model string and silently omits `temperature` from the
API call for those models — this is not in the original design doc, but is
implemented behavior worth knowing before debugging an unexpected-looking
request.

### `OpenAIBackend`

```python
from lcats.llm import openai_backend

backend = openai_backend.OpenAIBackend(api_key=None)
```

| Constructor argument | Description |
|---|---|
| `api_key` | Optional API key. When omitted, the OpenAI SDK reads `OPENAI_API_KEY` from the environment. |

Raises `ImportError` at construction time if the `openai` package is not
installed. Non-tool calls request `response_format={"type": "json_object"}`
rather than relying on prompt instructions alone.

### `FakeBackend`

```python
from lcats.llm import fake_backend

backend = fake_backend.FakeBackend(
    response_text="",
    tool_result=None,
    model="fake-1.0",
    input_tokens=0,
    output_tokens=0,
)
```

Deterministic test double — always returns a fixed `BackendResponse` built
from the constructor arguments, and records every call's keyword arguments in
`backend.calls` for assertions. Use this in tests instead of mocking
`client.chat.completions.create`/`client.messages.stream` directly.

## Provider wire-format translation

| | OpenAI | Anthropic |
|---|---|---|
| System prompt | Prepended as `{"role": "system", "content": system}` in `messages` | Top-level `system=` kwarg, not in `messages` |
| Tool call | `tools=[{"type": "function", "function": {...}}]`, `tool_choice={"type": "function", ...}` | `tools=[tool]` (schema is already canonical), `tool_choice={"type": "tool", "name": ...}` |
| No tool | `response_format={"type": "json_object"}` | No `response_format`; prompt instructs JSON |
| Result (no tool) | `choices[0].message.content` | First `text`-type content block |
| Result (tool) | `json.loads(choices[0].message.tool_calls[0].function.arguments)` | First `tool_use`-type content block's `.input` |
| Token counts | `usage.prompt_tokens`, `usage.completion_tokens` | `usage.input_tokens`, `usage.output_tokens` |

## Usage

```python
from lcats.llm import anthropic_backend

backend = anthropic_backend.AnthropicBackend()
result = backend.complete(
    system="You are a helpful assistant.",
    messages=[{"role": "user", "content": "Summarize this story."}],
    model="claude-opus-4-8",
)
print(result.text)
```

Callers construct one concrete backend and pass it down — `JSONPromptExtractor`,
`extract_from_story`, and `assess_story` all take a `backend: LLMBackend`
parameter rather than constructing a provider client internally.

## See also

- [`project/design/unified-llm-backend-design.md`](../../project/design/unified-llm-backend-design.md) — full design rationale, provider translation tables, and migration sequence (`WI-LLM-0007` through `WI-LLM-0010`, all resolved).
- [`docs/how-to/run-assess.md`](../how-to/run-assess.md) — using `lcats assess`, which is built on this abstraction.
