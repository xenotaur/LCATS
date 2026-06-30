---
id: WI-LLM-0010
title: Side-by-side model comparison dry run for assess pipeline
status: proposed
priority: medium
owner: unassigned
linked_workstream: WORKSTREAM-LLM-BACKEND
linked_design: DESIGN-LLM-BACKEND
depends_on: [WI-LLM-0008, WI-LLM-0009]
---

# Work Item: WI-LLM-0010

## Objective
Run the `lcats assess` pipeline on a small set of stories (5–10 per genre,
two genres) using both `AnthropicBackend` and `OpenAIBackend`, confirm the
output schema is identical across backends, and record the comparison results
as a baseline experiment. This is a validation run, not a full corpus
assessment.

## Scope

New file:
- `experiments/llm_backend_comparison/run_comparison.py`
  - Accepts `--backend anthropic|openai`, `--model MODEL`, `--genre GENRE`,
    `--sample N`, `--output DIR`
  - Constructs the appropriate backend
  - Runs `assess_story` on N sampled stories from the target genre corpus
  - Writes one JSONL file per run to `--output`

New file:
- `experiments/llm_backend_comparison/README.md`
  - Documents the comparison procedure, sample selection rationale, and
    how to interpret the output

New file (after running):
- `experiments/llm_backend_comparison/results/`
  - `anthropic-claude-opus-4-8-horror-N.jsonl`
  - `openai-gpt-4o-horror-N.jsonl`
  - (and analogous files for a second genre)

Analysis script (optional, in same directory):
- `compare_results.py` — computes agreement rate on `verdict` and `genre_match`
  across backends, prints a summary table

## Acceptance Criteria
- `run_comparison.py --backend anthropic --genre horror --sample 5` completes
  without errors and writes a valid JSONL file with 5 `AssessmentResult` dicts
- `run_comparison.py --backend openai --genre horror --sample 5` produces an
  identically-shaped JSONL file
- The two JSONL files have the same field set in every record
- Agreement rate on `verdict` is reported (no target threshold; this is a
  baseline, not a pass/fail)
- Results and README are committed to the repository for reproducibility

## Notes
- Sample selection: use the first N alphabetically from the genre corpus to
  ensure reproducibility without a random seed dependency.
- Use versioned model strings: `claude-opus-4-8` (not `claude-opus-latest`),
  `gpt-4o-2024-08-06` (not `gpt-4o`).
- Record `BackendResponse.model`, `input_tokens`, and `output_tokens` per
  story to support cost/latency comparison.
- This experiment intentionally uses a small sample. The full corpus
  assessment for the WorldCon paper is a separate planned activity.
- If `verdict` agreement is below ~70%, investigate whether prompt wording
  is the cause before scaling up.
