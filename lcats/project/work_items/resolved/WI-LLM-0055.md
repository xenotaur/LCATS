---
resolution: "Implemented and merged in PR #311 (commit b8a959b66f697641877f269928e94791a549d0e2)"
blocked_reason: null
blocked: false
id: WI-LLM-0055
title: Capture full entity lists and diff them across benchmark candidates
type: deliverable
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
forbidden_actions:
  - force_push
  - delete_branch
  - merge_pr
acceptance:
  - "BenchmarkResult (common/harness.py) captures the full extracted entity list (canonical_name + entity_type, at minimum) alongside the existing entity_count, written to results.json"
  - "A comparison script or benchmark_summary.py extension prints, for a chosen pair or set of candidates, which entities each candidate found that the others did not (set difference by name, with a documented normalization/matching rule)"
  - "Run against at least 2 committed candidates (anthropic_opus, ollama_qwen3_8b), plus a 3rd (ollama_qwen3_30b_a3b) if WI-LLM-0049 has landed by then, and show a real, worked example of the diff output"
artifacts_expected:
  - lcats/experimental/model_comparison/common/harness.py
  - lcats/experimental/model_comparison/entity_diff.py
  - lcats/experimental/model_comparison/README.md
required_evidence:
  - lrh_validate
  - test_output
  - manual_review
---

## Summary

`lcats/experimental/model_comparison/`'s benchmark harness currently
records only `entity_count` per candidate - a scalar comparison, not a
real diff. Extend `BenchmarkResult`/`results.json` to capture the actual
extracted entity list, and add a small comparison tool that reports which
entities each candidate found that another candidate missed, so a
question like "does qwen3:8b miss the same entities Opus catches, or
different ones entirely?" has a real answer instead of just a count
gap.

## Problem / Context

The existing harness (`common/harness.py`'s `BenchmarkResult`) stores
`candidate, backend_kind, model, story_name, stage, success,
latency_seconds, input_tokens, output_tokens, entity_count, error_type,
error_message, raw_output_preview` - no field for the entities
themselves. `benchmark_summary.py` can therefore only show that, e.g.,
`ollama_qwen3_8b` found 13 entities against `anthropic_opus`'s 21 on the
same segment - not which 13, or which 8 were missed, or whether it found
entities Opus didn't. That gap surfaced directly while discussing
`WI-LLM-0049` (add a third candidate, `qwen3:30b-a3b`): landing a third
candidate would give three `results.json` files to compare, but the
existing tooling still couldn't answer "compare entity lists" - only
"compare counts."

### Prior Art Check

**Duplication search:** In-repo, no existing entity-list capture or
diffing tool. `common/harness.py`'s `run_entity_extraction()` already has
the full parsed tool result in scope (`parsed`/`entities` locals) before
discarding everything but the count - the capture itself is a small,
local change, not new extraction logic. No sibling repos or external
libraries considered; this is benchmark-harness tooling, not a new
capability requiring an external dependency. Recommendation: proceed.

**Demand search:** No existing work item or proposal requests this
directly - it surfaced from a user question about `WI-LLM-0049`'s
downstream value, not from a pre-existing backlog entry. No
`PROP-ERW-LOCAL-MODEL-EVALUATION` acceptance criterion currently requires
it either. Recommendation: proceed as a new, standalone item; no
existing request to link/close.

## Scope

- Extend `BenchmarkResult` (`common/harness.py`) with an `entities` field
  - a list of `{canonical_name, entity_type}` (or similar minimal shape)
  pulled from the already-parsed tool result, alongside the existing
  `entity_count` (keep `entity_count` for backward-compat with existing
  `results.json` consumers/`benchmark_summary.py`'s table).
- Write a small `entity_diff.py` (or extend `benchmark_summary.py`) that
  takes two or more candidates' `results.json` files and reports:
  entities found by all, entities found only by candidate A, only by
  candidate B, etc. - a straightforward set-difference by normalized
  name (document the normalization rule, e.g. case-folding, since exact
  string matches across models are unlikely to be perfectly consistent).
- Run it against the real, already-committed `anthropic_opus` and
  `ollama_qwen3_8b` results (re-running `benchmark.py` for both first,
  since existing `results.json` files predate this field and won't have
  `entities` populated) and include the real diff output in this work
  item's own PR/execution record as a worked example.
- If `WI-LLM-0049` (`ollama_qwen3_30b_a3b`) has landed by the time this
  is implemented, include it as a third comparison point; if not, two
  candidates is a sufficient demonstration - do not block on it.

## Required Changes

- `common/harness.py`: `BenchmarkResult.entities` field + population.
- New `entity_diff.py` (or `benchmark_summary.py` extension).
- Re-run at least `anthropic_opus` and `ollama_qwen3_8b` to populate the
  new field in committed `results.json`.
- `README.md` documents the new field and how to run the diff.

## Non-Goals

- Does not compute precision/recall against ground-truth entities - this
  is a same-input cross-candidate diff (what did each model see), not a
  correctness judgment against a labeled answer key. A true quality
  evaluation needs human-annotated ground truth, out of scope here (see
  `PROP-ERW-LOCAL-MODEL-EVALUATION`'s own Non-Goals on this point).
- Does not diff mentions, quotes, or actant roles - entity identity
  (name + type) only, for a first useful version. Widening to mention-
  level diffs is a natural follow-on, not required here.
- Does not change the real ERW production pipeline (`entity_extractor.py`,
  `run_pilot.py`) - this is benchmark-harness-only.

## Acceptance Criteria

- `BenchmarkResult`/`results.json` captures the full entity list, not
  just a count.
- A working comparison tool reports entity-level differences between at
  least two candidates.
- A real, worked diff example (not synthetic/mocked data) is included in
  this work item's own PR.

## Validation

- `scripts/test tests/llm_tests`
- `lrh validate`
- Real re-runs of at least 2 candidates' `benchmark.py`, with the new
  `entities` field populated and the diff tool run against them

## Risk Notes

- Entity-name matching across models will be noisy (different surface
  forms, aliasing, capitalization) - document the matching rule
  explicitly rather than presenting an unqualified diff as if names
  always align cleanly.
