---
id: WS-GPT-OSS-20B-EVALUATION
kind: planning_node
title: Evaluate and productionize gpt-oss:20b as a local model candidate
status: proposed
stage: executing
origin: ad_hoc
summary: Coordinates the WI-LLM-0063->WI-LLM-0066 arc vetting, diagnosing, fixing, and scale-testing gpt-oss:20b as a local Ollama candidate for the ERW pipeline.
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_design:
  - lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md
  - lcats/experimental/model_comparison/ollama_gpt_oss_20b/README.md
  - lcats/project/work_items/resolved/WI-LLM-0056.md
work_items:
  - WI-LLM-0063
  - WI-LLM-0064
  - WI-LLM-0065
  - WI-LLM-0066
exit_criteria:
  - WI-LLM-0066 resolved with a written go/no-go recommendation for gpt-oss:20b at genre-census scale
  - A clear, evidence-backed per-stage recommendation (genre detection / entity extraction / segmentation) exists in lcats/experimental/model_comparison/ollama_gpt_oss_20b/README.md and the governing proposal
  - lrh validate reports 0 errors
---

## Purpose

This workstream groups the `WI-LLM-0063`->`WI-LLM-0066` arc: a sequence of
real-evidence investigations that took `gpt-oss:20b` from a thin, 2-run
early signal (`WI-LLM-0056`) to a fully vetted, diagnosed, and partially
production-grounded local model candidate. It exists to make this
multi-step narrative - vet -> diagnose -> fix -> scale-test - visible as a
single planning unit rather than four independently-discovered work items
linked only through a shared design proposal.

## Scope

- Full 3-stage vetting of `gpt-oss:20b` (genre detection, entity
  extraction, segmentation) - `WI-LLM-0063`.
- Harness diagnostic fixes and a best-of-breed config variant
  (`temperature=1.0`, verbatim-quote reminder) - `WI-LLM-0064`.
- A candidate-scoped adapter making entity extraction production-grounded
  - `WI-LLM-0065`.
- Scale-testing genre detection against a real multi-story, multi-genre
  sample via `run_census.py` - `WI-LLM-0066`.

## Prior Art Check

### Duplication search
- In-repo: no existing workstream covers this arc or any subset of it
  (checked `project/workstreams/{proposed,resolved}/` - no `gpt-oss`
  hits).
- Sibling repos / external libraries: none identified - specific to this
  project's local-model evaluation lineage.
- Recommendation: proceed, no duplication.

### Demand search
- Work items: none found requesting this grouping beyond this
  conversation's own review of `gpt-oss:20b`'s current status.
- Proposals: `PROP-ERW-LOCAL-MODEL-EVALUATION` already covers the broader
  multi-candidate evaluation but doesn't itself track this candidate's
  own sub-arc as a workstream.
- Recommendation: proceed; this workstream is additive
  documentation/tracking, not a duplicate effort.

## Work Items

- **`WI-LLM-0063`** (resolved) - Vetted `gpt-oss:20b` across all 3
  pipeline stages with 3+ real runs each: genre detection 3/3, entity
  extraction 3/3 (real variance found), segmentation 0/3 (new
  alignment-rejection failure mode).
- **`WI-LLM-0064`** (resolved) - Fixed two harness diagnostic gaps and
  tested a `temperature=1.0` config variant; found entity extraction's
  raw success was masking 0 grounded entities (malformed mention
  shapes), and segmentation stayed non-viable even with a verbatim-quote
  reminder.
- **`WI-LLM-0065`** (resolved) - Built a candidate-scoped compatibility
  adapter that repairs `gpt-oss:20b`'s known malformed entity shapes
  before the unchanged production `build_entities()` call - 3/3
  production-grounded successes.
- **`WI-LLM-0066`** (proposed) - Wires `run_census.py` to a local
  OpenAI-compatible endpoint and runs a real multi-story `gpt-oss:20b`
  sample against the existing Claude reference sample, to test whether
  genre detection's clean single-story result holds at corpus scale.

## Exit Criteria

(see frontmatter `exit_criteria:` - kept in sync)

## Non-Goals

- Does not change the ERW pipeline's default model or routing - every
  constituent WI explicitly excludes this.
- Does not cover other local candidates (`qwen3:8b`, `gemma4:12b`,
  `deepseek-r1:14b`, etc.) - those remain tracked only through the
  governing proposal, not this workstream.
- Does not authorize a full ~1,868-story local genre census -
  `WI-LLM-0066` explicitly stops at a go/no-go recommendation for that
  decision, not the run itself.

## Open Questions

- Whether entity extraction's precision/recall (not just grounded-count
  success) is good enough to prefer over Opus - explicitly deferred by
  `WI-LLM-0064`/`WI-LLM-0065`, not yet scoped as a work item.
- Whether `reasoning_effort`/`think`-level control or a native-Ollama-API
  backend (both deferred by `WI-LLM-0064` as too costly for that item)
  are worth a dedicated follow-up WI if `WI-LLM-0066`'s scale-test
  doesn't hold up.
