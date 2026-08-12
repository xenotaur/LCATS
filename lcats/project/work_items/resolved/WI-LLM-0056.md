---
resolution: "Implemented across PR #270 and PR #273 (final commit 551c6ea9). All 6 tranche 1 cells landed with real, committed, multi-run evidence: 3 succeeded (anthropic_haiku, ollama_gpt_oss_20b; openai_gpt55 exercised for real but surfaced a schema bug in ENTITY_TOOL_SCHEMA rather than a clean success), 3 documented failures (gemini_flash, ollama_gemma4_12b, ollama_deepseek_r1_14b). The 3 failures split into two genuinely distinct tool_choice mechanisms - gemma4/deepseek-r1 silently ignore tool_choice, gemini's own compat filter actively rejects an attempted call - both now confirmed on entity extraction, not just the segmentation stage WI-LLM-0051 characterized. Resolved per explicit user decision: the WI's deeper intent (real evidence per cell) is satisfied even though not every cell shows a working candidate. Follow-up investigation into the tool_choice patterns deferred to a separate WI."
blocked_reason: null
blocked: false
id: WI-LLM-0056
title: "Tranche 1: expand the benchmark harness to cross-provider coverage (Anthropic, OpenAI, Gemini, one open-weight family)"
type: evaluation
status: resolved
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams: []
related_design:
  - lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md
  - lcats/experimental/model_comparison/README.md
depends_on: []
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - merge_pr
acceptance:
  - "At least one additional online Anthropic candidate lands (a second model tier alongside anthropic_opus), reusing the existing AnthropicBackend"
  - "At least one online OpenAI candidate lands, reusing OpenAIBackend against the real OpenAI API (base_url unset)"
  - "At least one offline OpenAI candidate lands (gpt-oss-20b via Ollama), reusing OpenAIBackend + base_url exactly like ollama_qwen3_8b"
  - "At least one online Gemini candidate lands, using OpenAIBackend + base_url pointed at Google's documented OpenAI-compatible endpoint - a real spike run, not just wiring, since compat-layer tool-calling reliability for our exact schema is unverified"
  - "At least one offline Gemma candidate lands (Google's open-weight lineage, since Gemini itself has no open weights), via Ollama"
  - "A documented, reasoned decision on the second open-weight family (beyond the existing qwen3:8b) - candidate identified, its Mac-hardware fit checked, and either a real candidate landed or an explicit blocked/deferred note if nothing fits available hardware"
  - "gpt-oss-120b explicitly deferred to non-Mac hardware (Kubuntu/Linux) with a documented reason (~52-73GB minimum footprint exceeds this session's 32GB Mac), not silently dropped"
artifacts_expected:
  - lcats/experimental/model_comparison/anthropic_haiku/README.md
  - lcats/experimental/model_comparison/anthropic_haiku/setup.py
  - lcats/experimental/model_comparison/anthropic_haiku/benchmark.py
  - lcats/experimental/model_comparison/anthropic_haiku/results.json
  - lcats/experimental/model_comparison/openai_gpt5/README.md
  - lcats/experimental/model_comparison/openai_gpt5/setup.py
  - lcats/experimental/model_comparison/openai_gpt5/benchmark.py
  - lcats/experimental/model_comparison/openai_gpt5/results.json
  - lcats/experimental/model_comparison/ollama_gpt_oss_20b/README.md
  - lcats/experimental/model_comparison/ollama_gpt_oss_20b/setup.py
  - lcats/experimental/model_comparison/ollama_gpt_oss_20b/benchmark.py
  - lcats/experimental/model_comparison/ollama_gpt_oss_20b/results.json
  - lcats/experimental/model_comparison/gemini_flash/README.md
  - lcats/experimental/model_comparison/gemini_flash/setup.py
  - lcats/experimental/model_comparison/gemini_flash/benchmark.py
  - lcats/experimental/model_comparison/gemini_flash/results.json
  - lcats/experimental/model_comparison/ollama_gemma4_12b/README.md
  - lcats/experimental/model_comparison/ollama_gemma4_12b/setup.py
  - lcats/experimental/model_comparison/ollama_gemma4_12b/benchmark.py
  - lcats/experimental/model_comparison/ollama_gemma4_12b/results.json
  - lcats/experimental/model_comparison/<second-open-weight-family>/README.md
  - lcats/experimental/model_comparison/README.md
required_evidence:
  - lrh_validate
  - test_output
  - manual_review
---

## Summary

Expand `lcats/experimental/model_comparison/` from its current 2
candidates (`anthropic_opus`, `ollama_qwen3_8b`) to real coverage across
the three major hosted providers (Anthropic, OpenAI, Gemini) plus at
least one open-weight family, with a Mac-offline-first preference where a
given tier has an offline option at all. This is "tranche 1" of a wider
multi-provider comparison: get one working candidate per
provider/online-offline cell before adding more models within any single
cell.

## Problem / Context

The existing harness only compares one frontier baseline
(`claude-opus-4-8`) against one local candidate (`qwen3:8b`). The user
wants broader coverage - up to 2-4 models per provider eventually - but
asked to tranche it: first make sure every provider (Anthropic, OpenAI,
Gemini) and at least one open-weight family has *a* working candidate,
online and offline where offline exists, before widening within any one
cell. This work item is that first tranche.

A structural review (this session, in response to the user's question)
found the existing architecture already covers most of this without new
backend code:

- `AnthropicBackend` (`lcats/src/lcats/llm/anthropic_backend.py`) already
  handles Anthropic online.
- `OpenAIBackend` with its `base_url` parameter
  (`lcats/src/lcats/llm/openai_backend.py:15`, added in PR #219) already
  handles: OpenAI online (default `base_url`), any Ollama-served
  open-weight model (OpenAI offline via `gpt-oss`, Gemma offline, a
  second open-weight family offline - same pattern as
  `ollama_qwen3_8b/`), and - newly confirmed this session - **Gemini
  online**, via Google's own documented OpenAI-compatible endpoint
  (`https://generativelanguage.googleapis.com/v1beta/openai/`,
  [Google AI for Developers](https://ai.google.dev/gemini-api/docs/openai)).

The one confirmed gap, not a limitation of this work item's scope but a
fact about the provider landscape: **Anthropic has no offline/open-weight
option at all.** Anthropic's own stated position
([anthropic.com/news/position-open-weights-models](https://www.anthropic.com/news/position-open-weights-models))
rules this out - not a hardware or tooling constraint, a vendor policy
one. No offline Anthropic candidate is in scope for this or any future
tranche unless that position changes.

### Prior Art Check

**Duplication search:** In-repo, only `anthropic_opus/` and
`ollama_qwen3_8b/` exist as candidates; no existing OpenAI-online,
OpenAI-offline, Gemini, or second-open-weight-family candidate. No new
backend class needed per the finding above - `OpenAIBackend` already
covers OpenAI online/offline and Gemini online; `AnthropicBackend`
already covers Anthropic online. Recommendation: proceed, no
duplication.

**Demand search:** No existing work item or proposal requested
multi-provider coverage before this session's conversation; this is a
new user request, not linked to a pre-existing backlog entry.
Recommendation: proceed as a new item.

## Scope

For each cell below, land ONE real, working candidate (not the full 2-4
eventually wanted - that's later tranches):

- **Anthropic online (2nd tier):** a second Anthropic model alongside
  `anthropic_opus` (e.g. a Haiku-tier model), via the existing
  `AnthropicBackend` - new candidate directory only, no backend changes.
- **OpenAI online:** new candidate via `OpenAIBackend` with default
  `base_url` (real OpenAI API). Pin an exact, verified model ID before
  landing - do not trust unqualified "GPT-5.6"-style names from
  secondary pricing-tracker sites without cross-checking OpenAI's own
  API docs at implementation time, since this landscape moves fast and
  this session's research was not first-party-sourced for exact current
  model IDs.
- **OpenAI offline:** `gpt-oss-20b` via Ollama (`OpenAIBackend` +
  `base_url`, same shape as `ollama_qwen3_8b/`). Apache 2.0, native
  Ollama MXFP4 support confirmed
  ([Ollama Blog](https://ollama.com/blog/gpt-oss)), fits this session's
  Mac's memory class. Do NOT attempt `gpt-oss-120b` on this Mac - its
  ~52-73GB minimum footprint exceeds 32GB unified memory; explicitly
  deferred to Linux/Kubuntu hardware in a future tranche, not attempted
  here.
- **Gemini online:** new candidate via `OpenAIBackend` + `base_url`
  pointed at Google's OpenAI-compatible endpoint. This is the one cell
  in this tranche requiring real verification rather than just wiring -
  spike it the same way `ollama_qwen3_8b` was spiked (real tool-schema
  call, check the raw response), since the compat layer's own docs
  explicitly exclude some Gemini-native features and tool-calling
  reliability through it specifically is unverified by this session's
  research.
- **Gemma offline:** a Gemma 4 variant via Ollama, sized to fit the Mac
  comfortably (check exact size/quant at implementation time rather than
  trusting this session's secondary-source claims about the family's
  tool-calling accuracy).
- **Second open-weight family (offline):** identify ONE candidate beyond
  Qwen3 - this session's research found DeepSeek V4 and GLM-5.2 as the
  two with genuine current signal (Llama 4's actual 2026 release status
  was contested in available search results and should not be assumed
  without a direct check). Neither candidate's exact VRAM/RAM footprint
  per size was confirmed this session - check that first, and pick
  whichever has a size that plausibly fits the Mac; if neither does,
  document that explicitly rather than forcing a choice that won't run.

## Required Changes

- One new candidate directory per landed cell above (`README.md`,
  `setup.py`, `benchmark.py`, following the existing two candidates'
  shape).
- `lcats/experimental/model_comparison/README.md` updated to list the
  new candidates.
- No `lcats.llm` backend changes expected - if implementation discovers
  a real gap (e.g. the Gemini compat endpoint doesn't actually support
  forced `tool_choice` the way our schema needs), document that as a
  finding rather than silently working around it.

## Non-Goals

- Does not land the full 2-4 models per provider the user described -
  this tranche is "one working candidate per cell," widening within a
  cell is explicitly later work.
- Does not attempt any offline Anthropic candidate - confirmed
  impossible, not deferred.
- Does not attempt `gpt-oss-120b` on Mac hardware - deferred to
  Linux/Kubuntu, not attempted here.
- Does not implement `WI-LLM-0055`'s entity-diff tooling - that's a
  separate, parallel work item; this one only needs to produce
  `results.json` files in the existing shape for `WI-LLM-0055`'s tooling
  to later consume.
- Does not perform quality (precision/recall) comparison - same
  call-success/latency/entity-count scope as the existing harness.

## Acceptance Criteria

- One working candidate lands for each of: Anthropic online (2nd tier),
  OpenAI online, OpenAI offline (`gpt-oss-20b`), Gemini online, Gemma
  offline, and a second open-weight family offline (or an explicit,
  documented reason why none fit available hardware).
- `gpt-oss-120b` and any offline Anthropic candidate are explicitly
  documented as out of scope with reasons, not silently omitted.
- Each new candidate's `README.md` documents real, committed
  `results.json` from at least one actual run - no candidate lands
  without having actually been exercised.

## Validation

- `scripts/test tests/llm_tests`
- `lrh validate`
- Real `setup.py` + `benchmark.py` runs for every landed candidate, with
  committed `results.json`

## Risk Notes

- Model landscape and exact model IDs (Anthropic, OpenAI, Gemini) move
  fast; this work item's Problem/Context research was web-search-based,
  not first-party-verified for exact current model strings - re-verify
  against each provider's own docs at implementation time rather than
  trusting this write-up's specific names.
- The Gemini OpenAI-compat endpoint's tool-calling reliability for a
  forced `tool_choice` is unverified - budget for the possibility this
  cell behaves more like the original `ollama_qwen3_8b` spike (real,
  unexpected failure modes) than a clean pass.
- Hardware fit for the second open-weight family (DeepSeek V4 vs.
  GLM-5.2 vs. others) was not confirmed this session - this could turn
  out to be a "document why nothing fits" outcome rather than a landed
  candidate, and that is an acceptable result per this work item's own
  acceptance criteria.
