# openai_gpt55

OpenAI online candidate for `model_comparison/` (`WI-LLM-0056`, tranche 1)
- `gpt-5.5` via `lcats.llm.openai_backend.OpenAIBackend` (default
`base_url`, the real OpenAI API), verified against
`client.models.list()` at implementation time (not a secondary-source
model name guess - see `../README.md`'s "Research context").

## Setup

```bash
python setup.py
```

Checks the `openai` package is installed and `OPENAI_API_KEY` is set
(env var or `.secrets/openai_api_keys.env`). Makes no API calls.

## Run

```bash
python benchmark.py
```

Makes **one real, billable** OpenAI API call: the ERW pipeline's actual
stage-3 entity-extraction tool-schema call
(`lcats.analysis.event_role_world.entity_extractor`) against the same real
~600-word scene/sequel segment `anthropic_opus` uses
(`../common/sample_segment.json`), with `max_tokens=8192`.

Writes `results.json` in this directory. See `../benchmark_summary.py` to
compare against other candidates.

## Actual results (`WI-LLM-0056`)

**First attempt was blocked on account credits** (HTTP 429
`insufficient_quota`, 2.9s, 0 tokens - reported at the time but that raw
JSON was overwritten by the second run below before being separately
saved; not independently recoverable, only this prose record of it
remains). After credits were added, a second real attempt (the one
`results.json` now contains) surfaced a **genuine schema bug**, not a
candidate-quality result:

```
Invalid schema for function 'extract_entities': In context=('properties',
'entities', 'items', 'properties', 'mentions', 'items'), 'required' is
required to be supplied and to be an array including every key in
properties. Missing 'grammatical_role'.
```

Traced to `lcats/src/lcats/analysis/event_role_world/entity_extractor.py:51-68`:
`ENTITY_TOOL_SCHEMA`'s per-mention sub-schema defines `grammatical_role`
as a property (line 66) but its `required` array (line 68) only lists
`["mention_id", "text", "quote"]` - `grammatical_role` is missing.
OpenAI's strict function-calling validator (`strict: true`, forwarded by
`openai_backend.py`) enforces that *every* declared property appears in
`required` for strict mode; Anthropic's strict-tool-use validation
apparently does not enforce this same completeness rule, which is why
`anthropic_opus`/`anthropic_haiku` never surfaced it.

**This is a real bug in the shared, production `ENTITY_TOOL_SCHEMA`**
(used by every caller of `make_entity_extractor()`, not just this
benchmark), not an `openai_gpt55`-candidate-specific issue or a
`lcats.llm` backend gap - fixing it is out of this tranche's own scope
(Non-Goals: no `lcats.llm` backend changes; this bug lives one layer up,
in `entity_extractor.py`'s schema definition, and touches real production
callers, not just this harness). Flagged as a follow-up rather than fixed
here. `gpt-5.5` itself remains unexercised against this schema - no valid
result is possible until the schema bug is fixed.
