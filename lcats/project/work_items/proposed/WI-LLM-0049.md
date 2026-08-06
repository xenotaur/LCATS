---
resolution: null
blocked_reason: null
blocked: false
id: WI-LLM-0049
title: Add qwen3:30b-a3b (MoE) candidate to the local-model benchmark harness
type: evaluation
status: proposed
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
forbidden_actions:
  - force_push
  - delete_branch
  - merge_pr
acceptance:
  - "lcats/experimental/model_comparison/ollama_qwen3_30b_a3b/ exists with README.md, setup.py, benchmark.py, following the shape of ollama_qwen3_8b/"
  - "setup.py verifies Ollama is running and qwen3:30b-a3b is pulled (exact tag match), without downloading/installing anything itself"
  - "At least 2 real benchmark.py runs completed and committed as results.json/results_*.json, comparing entity-recall and latency against anthropic_opus and ollama_qwen3_8b on the identical sample_segment.json"
  - "README.md documents the real results and whether the entity-recall gap (11-14 vs. Opus's 21) narrows"
artifacts_expected:
  - lcats/experimental/model_comparison/ollama_qwen3_30b_a3b/README.md
  - lcats/experimental/model_comparison/ollama_qwen3_30b_a3b/setup.py
  - lcats/experimental/model_comparison/ollama_qwen3_30b_a3b/benchmark.py
  - lcats/experimental/model_comparison/ollama_qwen3_30b_a3b/results*.json
required_evidence:
  - lrh_validate
  - test_output
  - manual_review
---

## Summary

Add a new local-model candidate, `qwen3:30b-a3b` (a mixture-of-experts
model, ~30B total/~3B active parameters), to
`lcats/experimental/model_comparison/`'s benchmark harness, and run it
against the same real segment/schema `anthropic_opus` and
`ollama_qwen3_8b` already use. Goal: test whether a larger local model
narrows the entity-recall gap the 8B candidate showed (11-14 entities vs.
`claude-opus-4-8`'s 21 on the identical segment) at a still-acceptable
latency.

## Problem / Context

`PROP-ERW-LOCAL-MODEL-EVALUATION`
(`project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md`,
`status: proposed`) evaluated one local candidate, `qwen3:8b` via Ollama,
against the ERW pipeline's real stage-3 entity-extraction tool-schema
call. After a methodology fix (PR #223 - a real ~600-word segment instead
of a whole story, `temperature=0.6` matching Qwen3's own recommendation),
`qwen3:8b` succeeded consistently (3/3 runs) at ~1.5-2.2x
`claude-opus-4-8`'s latency, but extracted fewer entities (11-14 vs. 21).
The proposal's landscape survey named `qwen3:30b-a3b` as a plausible
"quality tier" candidate for extraction-grade stages, not yet tested -
this work item is that test, named as follow-on item #1 in the
proposal's Implementation Plan.

### Prior Art Check

**Duplication search:** In-repo, no `qwen3:30b-a3b` candidate or similar
MoE-tier benchmark exists. `lcats/experimental/model_comparison/ollama_qwen3_8b/`
is the direct template to follow (same harness, same `OpenAIBackend`
`base_url` mechanism, same real-segment input). No sibling repos or
external libraries considered - this is a benchmark configuration, not a
library gap. Recommendation: proceed.

**Demand search:** `PROP-ERW-LOCAL-MODEL-EVALUATION`'s Implementation
Plan directly requests this as follow-on item #1. No other work item or
backlog entry duplicates it. Recommendation: this work item satisfies
that request; link back to the proposal in the PR.

## Scope

- Add `lcats/experimental/model_comparison/ollama_qwen3_30b_a3b/` with
  `README.md`, `setup.py`, `benchmark.py`, following the existing shape
  of `ollama_qwen3_8b/` (see that directory for the pattern: `setup.py`
  checks Ollama reachability + exact model tag, never
  installs/downloads; `benchmark.py` builds an `OpenAIBackend` pointed at
  Ollama's `base_url` and calls `common.harness.run_entity_extraction()`).
- Explicit, deliberate step (not automated by this work item): install
  Ollama if not already present, `ollama pull qwen3:30b-a3b` (a larger
  download, ~18-20GB - confirm current size before pulling), with
  the implementer's explicit permission before downloading.
- Run `benchmark.py` at least twice. A single local-model run is not
  decision-grade evidence: `ollama_qwen3_8b`'s own first run against
  this harness failed outright, while an identical rerun succeeded but
  took ~8.5x the frontier baseline's latency - see the three real,
  committed runs at
  `lcats/experimental/model_comparison/ollama_qwen3_8b/results_segment_run1.json`
  through `results_segment_run3.json` (PR #223) for the committed
  evidence behind this requirement.
- Set an appropriate `temperature` override in `benchmark.py` if this
  model's own documented sampling recommendation differs from the
  pipeline's default (0.2) - do not assume `qwen3:8b`'s 0.6 applies
  without checking this model's own guidance.
- Update `README.md` (or the top-level `model_comparison/README.md`) with
  the real comparative results: latency, entity count, and whether the
  larger model's answer actually narrows the recall gap.

## Required Changes

- New directory `lcats/experimental/model_comparison/ollama_qwen3_30b_a3b/`
  (`README.md`, `setup.py`, `benchmark.py`).
- Committed `results*.json` from at least 2 real runs.
- `lcats/experimental/model_comparison/README.md` updated to list the new
  candidate.

## Non-Goals

- Does not change `run_pilot.py`'s default model or any pipeline
  configuration - this is benchmark-only, per
  `PROP-ERW-LOCAL-MODEL-EVALUATION`'s own Decision 3.
- Does not extend the harness to any stage beyond stage-3 entity
  extraction - see `PROP-ERW-LOCAL-MODEL-EVALUATION`'s Implementation
  Plan follow-on item #2 (the genre-detection/segmentation extension) for
  that separate scope.
- Does not perform a formal precision/recall comparison against
  ground-truth entities - only call-success, latency, and raw entity
  count, matching the existing harness's stated scope.
- Does not test the Kubuntu Focus/discrete-NVIDIA hardware profile.

## Acceptance Criteria

- `lcats/experimental/model_comparison/ollama_qwen3_30b_a3b/` exists with
  `README.md`, `setup.py`, `benchmark.py`.
- `setup.py` verifies Ollama reachability and an exact `qwen3:30b-a3b`
  tag match, without downloading/installing anything itself.
- At least 2 real `benchmark.py` runs completed, with `results.json`/
  labeled `results_*.json` files committed.
- `README.md` documents the real comparative results against
  `anthropic_opus` and `ollama_qwen3_8b`.

## Validation

- `scripts/test` (canonical full suite - do not claim tests passed on a
  raw `pytest` invocation instead, per `AGENTS.md`)
- `scripts/format --check` and `scripts/lint`
- `lrh validate`
- `python experimental/model_comparison/ollama_qwen3_30b_a3b/setup.py`
- `python experimental/model_comparison/ollama_qwen3_30b_a3b/benchmark.py` (run at least twice)

## Risk Notes

- `qwen3:30b-a3b` is a much larger download (~18-20GB) and may need more
  RAM/VRAM than this session's M1 Max/32GB test machine comfortably
  supports for a single-model-loaded-at-a-time benchmark - confirm
  headroom before pulling.
- Latency could be substantially higher than the 8B candidate; budget
  real wall-clock time for at least 2 runs (the 8B candidate's runs took
  74-106s each on real segment input; this could be several times
  longer).
