---
resolution: null
blocked_reason: null
blocked: false
id: WI-LLM-0063
title: Thoroughly vet ollama_gpt_oss_20b as a local model candidate
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
  - lcats/project/work_items/resolved/WI-LLM-0051.md
  - lcats/project/work_items/resolved/WI-LLM-0056.md
  - lcats/project/work_items/resolved/WI-LLM-0062.md
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
  - "At least 3 real runs each for genre detection, segmentation, and entity extraction against gpt-oss:20b, all committed as evidence regardless of outcome"
  - "If segmentation fails via no_tool_call, the WI-LLM-0051 reminder-retry mitigation is tested and its effect documented"
  - "A written verdict per stage in ollama_gpt_oss_20b/README.md and PROP-ERW-LOCAL-MODEL-EVALUATION, not left as an open early signal"
artifacts_expected:
  - lcats/experimental/model_comparison/ollama_gpt_oss_20b/README.md
  - lcats/experimental/model_comparison/ollama_gpt_oss_20b/benchmark.py
  - lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md
required_evidence:
  - lrh_validate
  - manual_review
  - test_output
---

## Summary

Run additional real benchmark calls against `gpt-oss:20b` (via
`ollama_gpt_oss_20b/`) across all three ERW pipeline stages tested
elsewhere in this tranche - genre detection, segmentation, and entity
extraction - establishing a new 3-run-per-stage evidence bar for this
candidate (matching `qwen3:8b`'s own entity-extraction sample size, the
largest precedent in this tranche), and produce a real
reliability/viability verdict instead of a 2-run early signal.

## Problem / Context

`WI-LLM-0056`'s tranche 1 tested `gpt-oss:20b` only on entity extraction
(2/2 success, 35-38s latency - the fastest and one of the highest-quality
local results in the whole tranche), and only 2 runs, well below this
lineage's own 3-run standard for calling a candidate reliable. Genre
detection and segmentation were never attempted for this candidate at
all - and segmentation in particular is the stage where every local
model actually tested on it so far (`qwen3:8b`, `qwen3:30b-a3b`) has
shown a real `tool_choice` reliability problem (0/5 baseline across both
candidates). `gemma4:12b` and `deepseek-r1:14b` have a related but
distinct finding - a `tool_choice` silent-ignore failure on *entity
extraction*, not segmentation, which was never run against them. Either
failure mode could plausibly recur on `gpt-oss:20b`'s untested
segmentation stage, so it remains the stage most likely to surface an
issue if one exists. See
`experimental/model_comparison/ollama_gpt_oss_20b/README.md` and
`project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md`'s
Decision 3.

### Duplication search
- In-repo: No existing work item covers additional `gpt-oss:20b` testing.
  `WI-LLM-0062` covered the two `tool_choice` failure mechanisms found in
  other candidates (`gemma4:12b`, `deepseek-r1:14b`, `gemini_flash`), not
  this one.
- Sibling repos: None identified.
- External libraries: None identified - specific to this pipeline's tool
  schemas and Ollama's runtime behavior.
- Recommendation: Proceed, no duplication.

### Demand search
- Work items: `WI-LLM-0056`'s own execution record flags "Follow-up
  investigation into the tool_choice patterns deferred to a separate WI,"
  but that was resolved by `WI-LLM-0062` for the failing candidates
  specifically; no existing item requests deeper vetting of a succeeding
  candidate like `gpt-oss:20b`.
- Proposals: None found.
- Backlog: No matching entries.
- Recommendation: No action - this work item satisfies a real,
  previously-unaddressed gap.

## Scope

- Run genre detection, segmentation, and entity-extraction benchmarks
  against `gpt-oss:20b` using the existing harness
  (`common/harness.py`'s `run_genre_detection()`/`run_segmentation()`/
  `run_entity_extraction()`), matching the real-call, committed-evidence
  discipline used throughout this tranche.
- At least 3 real runs per stage (not a single one-off), consistent with
  this lineage's own established evidence standard.
- If segmentation fails via the `tool_choice` silent-ignore mechanism,
  test `WI-LLM-0051`'s reminder-retry mitigation
  (`retry_with_reminder=True`) the same way `WI-LLM-0062` did for other
  candidates.
- Update `ollama_gpt_oss_20b/README.md` and
  `PROP-ERW-LOCAL-MODEL-EVALUATION` with an explicit verdict for each
  stage.

## Required Changes

1. Add genre-detection and segmentation benchmark scripts to
   `experimental/model_comparison/ollama_gpt_oss_20b/` (mirroring the
   shape of scripts in `ollama_qwen3_8b/` or `ollama_gemma4_12b/`).
2. Run at least 3 real entity-extraction calls (1 more than the existing
   2), at least 3 genre-detection calls, and at least 3 segmentation
   calls (plus reminder-retry reruns if the baseline fails via
   `no_tool_call`).
3. Commit all result JSON files as real evidence, regardless of outcome.
4. Update `ollama_gpt_oss_20b/README.md` with a verdict per stage.
5. Update `PROP-ERW-LOCAL-MODEL-EVALUATION`'s Decision 3 / Open
   Questions with this candidate's full status.

## Non-Goals

- Does not change the pipeline's default model (`claude-opus-4-8` stays
  held per the proposal's current decision) - a positive result here is
  evidence for a future decision, not this item's own action.
- Does not test `gpt-oss-120b` - already explicitly deferred to non-Mac
  hardware in `WI-LLM-0056`.
- Does not run a precision/recall/ground-truth quality comparison - out
  of scope for this tranche, same Non-Goal as every sibling WI in this
  lineage.
- Does not touch `lcats.llm` or `run_pilot.py` production code unless a
  real finding justifies it (e.g., a mitigation proven to help).

## Acceptance Criteria

- At least 3 real runs each for genre detection, segmentation, and
  entity extraction against `gpt-oss:20b`, all committed as evidence.
- If segmentation fails via `no_tool_call`, the reminder-retry mitigation
  is tested and its effect (or lack thereof) documented.
- A written verdict per stage in `ollama_gpt_oss_20b/README.md` and
  `PROP-ERW-LOCAL-MODEL-EVALUATION`, not left as an open "early signal."

## Validation

- `scripts/test`
- `lrh validate`
- Real benchmark runs for all three stages, with `raw_output_preview`/
  `error_message` inspected on any failure

## Risk Notes

- `gpt-oss:20b` could turn out to share the segmentation-stage
  `tool_choice` reliability problem `qwen3:8b`/`qwen3:30b-a3b` showed
  (0/5 baseline), or the entity-extraction silent-ignore mechanism
  `gemma4:12b`/`deepseek-r1:14b` showed on a different stage - a negative
  result on either is a valid, complete finding, not a failed
  investigation (established precedent from `WI-LLM-0051`/`WI-LLM-0062`).
- The existing 2 entity-extraction runs showed real variance (12 vs 21
  entities) - a 3rd+ run could either tighten or widen that picture;
  either outcome is useful evidence.
