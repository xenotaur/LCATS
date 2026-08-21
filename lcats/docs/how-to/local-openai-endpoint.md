# How to point `OpenAIBackend` at a local OpenAI-compatible endpoint

`lcats.llm.openai_backend.OpenAIBackend` accepts an optional `base_url`
constructor argument. Setting it redirects every call away from
`api.openai.com` to any server that speaks the OpenAI chat completions
wire format — Ollama, vLLM, LM Studio, and similar local runtimes all
qualify. No separate backend class exists or is needed for this; see
[`docs/reference/llm-backend.md`](../reference/llm-backend.md#openaibackend)
for the full constructor reference.

```python
from lcats.llm import openai_backend

backend = openai_backend.OpenAIBackend(
    api_key="ollama",  # most local servers ignore the value but require it be non-empty
    base_url="http://localhost:11434/v1",
)
result = backend.complete(
    system="You are a helpful assistant.",
    messages=[{"role": "user", "content": "Summarize this story."}],
    model="gpt-oss:20b",
)
```

Omitting `base_url` (the default, `None`) leaves real OpenAI API behavior
completely unchanged — this is an opt-in override, not a mode switch.

## Should you actually do this?

Before wiring a local model into a real pipeline call, check the evidence.
`lcats/experimental/model_comparison/` is a checked-in benchmark harness
built specifically to answer this question against the ERW pipeline's
real tool-schema calls, not synthetic ones — see its
[README](../../experimental/model_comparison/README.md) for how to add or
re-run a candidate. The governing design proposal is
[`project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md`](../../project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md)
(`PROP-ERW-LOCAL-MODEL-EVALUATION`), which chose the `base_url` approach
documented here over a dedicated `OllamaBackend` class specifically to
avoid duplicating `OpenAIBackend`'s translation logic per runtime.

The most complete real-evidence result so far is the `gpt-oss:20b`
evaluation arc
([`WS-GPT-OSS-20B-EVALUATION`](../../project/workstreams/resolved/WS-GPT-OSS-20B-EVALUATION.md),
work items `WI-LLM-0063` through `WI-LLM-0066`, all resolved). Its
per-stage verdict:

| Pipeline stage | Verdict | Notes |
|---|---|---|
| Genre detection | Prefer `gpt-oss:20b` | Held up at multi-story, multi-genre pilot scale (20 stories, not the full ~1,868-story corpus, which has not run for any candidate); go/no-go recommendation for that full run: go, ~20.8hr projected wall-clock, $0 cost — see [`ollama_gpt_oss_20b/README.md`](../../experimental/model_comparison/ollama_gpt_oss_20b/README.md) |
| Entity extraction | Consider it, but only behind the candidate-scoped compatibility adapter built in `WI-LLM-0065` | Raw success masked 0 grounded entities (malformed mention shapes) until the adapter repaired them ahead of the unchanged production `build_entities()` call |
| Scene/sequel segmentation | Do not use | New alignment-rejection failure mode found in `WI-LLM-0063`; persisted even with a verbatim-quote reminder in `WI-LLM-0064` |

Other candidates in `model_comparison/` (Anthropic Haiku, OpenAI GPT-5.5,
Gemini Flash, Gemma4, DeepSeek-R1, Qwen3 in both 8b and 30b-a3b MoE
variants) have their own per-candidate `README.md` with real
success/failure findings — read the specific candidate's README before
assuming a result generalizes across model families. None of this work
has changed the ERW pipeline's default backend or model; every
constituent work item explicitly excluded that.

## See also

- [`docs/reference/llm-backend.md`](../reference/llm-backend.md) — full `LLMBackend` / `OpenAIBackend` reference.
- [`experimental/model_comparison/README.md`](../../experimental/model_comparison/README.md) — the benchmark harness, its layout, and how to add a new candidate.
- [`project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md`](../../project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md) — design rationale for the `base_url` approach.
