---
resolution: null
blocked_reason: null
blocked: false
id: WI-LLM-0059
title: Investigate reminder mitigation for the production segmentation system prompt
type: investigation
status: proposed
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams: []
related_design:
  - lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md
  - lcats/src/lcats/analysis/scene_analysis.py
  - lcats/experimental/model_comparison/common/harness.py
depends_on:
  - WI-LLM-0051
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
  - create_pr
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - merge_pr
  - modify_ci_pipeline
acceptance:
  - "Several more real segmentation calls (ollama_qwen3_8b at minimum, ollama_qwen3_30b_a3b if time permits) run with the reminder text appended to the real SCENE_SEQUEL_SYSTEM_PROMPT (not just the benchmark harness's local copy), and their success/failure recorded"
  - "A real, live claude-opus-4-8 segmentation call on the same story/segment with the modified prompt, compared against an unmodified-prompt baseline call, checking for output-quality or latency regression"
  - "A written verdict recorded in PROP-ERW-LOCAL-MODEL-EVALUATION: either scene_analysis.py's SCENE_SEQUEL_SYSTEM_PROMPT is edited for real with covering tests, or a documented decision not to change it, with the evidence either way"
  - "lrh validate and the full test suite pass after any production edit"
artifacts_expected:
  - lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md
  - lcats/src/lcats/analysis/scene_analysis.py
  - lcats/tests/analysis_tests/scene_analysis_test.py
required_evidence:
  - manual_review
  - test_output
---

## Summary

Investigate whether appending WI-LLM-0051's tested reminder ("CRITICAL
INSTRUCTION: You MUST call the record_segments function/tool...") to the
*production* `SCENE_SEQUEL_SYSTEM_PROMPT` in `scene_analysis.py` improves
local-model segmentation reliability in the real pipeline, and whether it
has any negative effect on frontier-model paths that already work
reliably without it - then either edit the prompt for real with tests, or
document why not.

## Problem / Context

`WI-LLM-0051` reproduced a real, 0/5-baseline `tool_choice`
forced-function-name gap on Ollama's segmentation stage and found that
appending an explicit reminder to the system prompt raised success to
2/5 (40%). That mitigation was implemented as an automatic retry-once
path scoped deliberately to the benchmark harness only
(`experimental/model_comparison/common/harness.py`'s
`run_segmentation()`, via `_SEGMENTATION_RETRY_REMINDER` and the
`system_prompt_suffix` parameter on `_run_segmentation_once()`) -
`WI-LLM-0051`'s Non-Goals explicitly excluded touching shared
backend/production prompts. `PROP-ERW-LOCAL-MODEL-EVALUATION`'s Open
Questions (2026-08-08 update) name the resulting gap directly: would the
same reminder help if it were part of the real, permanent
`SCENE_SEQUEL_SYSTEM_PROMPT` (consumed by `make_segment_extractor()`) -
not just a benchmark-only retry - and would it have any side effect on
Claude/GPT frontier paths, since that prompt is shared across every
backend via the `LLMBackend` Protocol. Left open, this question will keep
resurfacing every time local-model segmentation reliability comes up
without ever being decided one way or the other.

### Duplication search
- In-repo: No existing test or investigation touches
  `SCENE_SEQUEL_SYSTEM_PROMPT`'s text for reminder-mitigation purposes -
  the only reminder-mitigation code that exists is harness-scoped
  (`WI-LLM-0051`'s `_SEGMENTATION_RETRY_REMINDER`). External: none
  identified as a wholesale replacement.
- Recommendation: Proceed.

### Demand search
- Work items: `WI-LLM-0051`'s own Follow-up section and
  `PROP-ERW-LOCAL-MODEL-EVALUATION`'s Open Questions both name this
  directly as an unresolved follow-up.
- Proposals: `PROP-ERW-LOCAL-MODEL-EVALUATION` (same lineage) is the
  proposal this work item's findings will update.
- Backlog: No matching entries.
- Recommendation: This work item satisfies the named follow-up.

## Scope

- Test the reminder against the real production prompt (not the
  harness's separate copy) for local models, using
  `_run_segmentation_once()`'s existing `system_prompt_suffix` parameter
  as the test vehicle so no production code is edited before the
  evidence is in.
- Test the same modified prompt against a frontier model
  (`claude-opus-4-8` via the `anthropic_opus` candidate) on the same
  story/segment, comparing against an unmodified-prompt baseline call for
  output quality and latency.
- Record a verdict and, conditionally, implement the production edit.

## Required Changes

1. Run several more real segmentation calls against `ollama_qwen3_8b`
   (and `ollama_qwen3_30b_a3b` if time permits) with the reminder text
   appended via `system_prompt_suffix`, recording success/failure per
   call the same way `WI-LLM-0051` did.
2. Run at least one real `claude-opus-4-8` segmentation call with the
   identical modified prompt on the same story, and compare its output
   (segment count/labels/quality) and latency against an unmodified-
   prompt baseline call on the same story.
3. If the reminder helps local reliability and is neutral-or-better for
   the frontier path: edit `SCENE_SEQUEL_SYSTEM_PROMPT` in
   `lcats/src/lcats/analysis/scene_analysis.py` to include the reminder
   permanently, and add covering tests (e.g. an assertion that the
   prompt text includes the reminder, plus any needed
   `scene_analysis_test.py` coverage).
4. If the reminder is neutral-to-local-but-risky-for-frontier, or
   otherwise not clearly net-positive: do not edit the prompt: document
   the finding and rationale in
   `PROP-ERW-LOCAL-MODEL-EVALUATION`'s Open Questions/Decision sections
   instead.
5. Either way, update `PROP-ERW-LOCAL-MODEL-EVALUATION` to close out the
   Open Question this work item answers.

## Non-Goals

- Does not remove, replace, or otherwise change the existing harness-only
  retry path in `common/harness.py`'s `run_segmentation()`
  (`_SEGMENTATION_RETRY_REMINDER`) - it stays as-is regardless of this
  work item's outcome.
- Does not investigate other prompt or schema changes beyond this one
  reminder.
- Does not evaluate local models beyond `qwen3:8b`/`qwen3:30b-a3b`
  already available from prior work items.
- Does not change whether the mitigation is harness-scoped-retry vs.
  eager/permanent for the *benchmark* path - this item is specifically
  about the production system prompt text itself, a separate question
  from `WI-LLM-0051`'s retry design.
- Does not test OpenAI/GPT paths directly (no OpenAI API key assumed
  available in this session) - if untested, state that plainly as a gap
  rather than inferring a verdict from the Anthropic result alone.

## Acceptance Criteria

- Several more real segmentation calls run with the reminder appended to
  the real `SCENE_SEQUEL_SYSTEM_PROMPT` against at least `ollama_qwen3_8b`.
- A real `claude-opus-4-8` call with the modified prompt, compared against
  an unmodified-prompt baseline on the same story, with no quality or
  latency regression before any production edit is made.
- A written verdict recorded in `PROP-ERW-LOCAL-MODEL-EVALUATION`.
- If edited: `scene_analysis.py`'s `SCENE_SEQUEL_SYSTEM_PROMPT` change is
  covered by a test, and `lrh validate` plus the full test suite pass.
- If not edited: the finding and rationale are documented in place of a
  code change - a valid, non-failing outcome (see Risk Notes).

## Validation

- `scripts/test tests/analysis_tests`
- `scripts/test` (full suite, if a production edit is made)
- `lrh validate`
- Real benchmark calls against `ollama_qwen3_8b` (and `claude-opus-4-8`)
  with the modified prompt, evidence committed or documented per
  `WI-LLM-0051`'s precedent (real results, not simulated)

## Risk Notes

- This is a negative-result-tolerant investigation, like `WI-LLM-0051`: a
  "reminder doesn't help enough, or risks the frontier path, so no
  production change" outcome is valid and complete, not a failed work
  item.
- `SCENE_SEQUEL_SYSTEM_PROMPT` is shared across every backend
  (`AnthropicBackend`, `OpenAIBackend`, and any future `LLMBackend`
  implementation) - a permanent edit is higher blast-radius than the
  harness-only retry `WI-LLM-0051` shipped, so the frontier-model
  regression check in Required Changes item 2 is a hard gate before any
  edit lands, not an optional nice-to-have.
- `WI-LLM-0051` found the reminder only helps 40% of the time even in the
  benchmark harness - a permanent production edit is not expected to make
  Ollama segmentation fully reliable; the realistic best-case outcome is
  a moderate improvement, not a fix.

## Dependencies / Order

Depends on `WI-LLM-0051` (resolved) for the reminder mitigation strategy,
the harness's `system_prompt_suffix` mechanism this item reuses as its
test vehicle, and the real, live evidence establishing the underlying
gap. No other open dependency.
