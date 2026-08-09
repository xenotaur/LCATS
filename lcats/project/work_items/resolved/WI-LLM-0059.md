---
resolution: "Implemented and merged in PR #266 (commit 27d772fb). Reminder mitigation replicated for qwen3:8b (2/8 combined success across two sessions) and showed no success/latency regression on Anthropic, but did surface a minor granularity side effect (2/3 modified runs split into 5 segments vs. baseline's 4). OpenAI leg originally could not be verified (zero account credits); a 2026-08-09 follow-up re-test after credits were added found a structural failure instead - gpt-4o cannot complete this call on this story within its own hard 16384-completion-token maximum, on either condition. Per the WI's own Required Changes item 5, an unverified OpenAI path forces the documented no-change outcome: SCENE_SEQUEL_SYSTEM_PROMPT was NOT edited. Full write-up in PROP-ERW-LOCAL-MODEL-EVALUATION's Decision 3 update (2026-08-08, updated 2026-08-09)."
blocked_reason: null
blocked: false
id: WI-LLM-0059
title: Investigate reminder mitigation for the production segmentation system prompt
type: investigation
status: resolved
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
  - "At least 3 paired baseline/modified claude-opus-4-8 segmentation calls on the same story/segment, checking for output-quality or latency regression - a single pair cannot distinguish a real prompt effect from ordinary model/API run-to-run variance"
  - "At least one real OpenAI/GPT segmentation call with the modified prompt compared against an unmodified-prompt baseline, OR (if no OpenAI API key is available) an explicit statement that the OpenAI path is untested, which by itself forces the documented no-change outcome rather than a production edit"
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
2. Run at least 3 paired baseline/modified `claude-opus-4-8` segmentation
   calls (same story, same segment boundaries) - not a single pair - and
   compare output (segment count/labels/quality) and latency across the
   paired runs. A single pair cannot distinguish a genuine prompt effect
   from ordinary model/API run-to-run variance on a stochastic call; only
   a consistent pattern across multiple pairs counts as evidence of
   regression or its absence.
3. Attempt at least one real OpenAI/GPT segmentation call with the
   identical modified prompt, compared against an unmodified-prompt
   baseline, via `OpenAIBackend` (the same backend the production
   `SCENE_SEQUEL_SYSTEM_PROMPT` is shared with). If no OpenAI API key is
   available in the execution session, state that plainly - per item 5
   below, an untested OpenAI path forces the no-change outcome rather
   than being silently treated as an acceptable gap.
4. If the reminder helps local reliability AND both the Anthropic and
   OpenAI frontier paths are neutral-or-better (per items 2-3): edit
   `SCENE_SEQUEL_SYSTEM_PROMPT` in
   `lcats/src/lcats/analysis/scene_analysis.py` to include the reminder
   permanently, and add covering tests (e.g. an assertion that the
   prompt text includes the reminder, plus any needed
   `scene_analysis_test.py` coverage).
5. Do not edit the prompt if any of the following hold: the reminder is
   neutral-to-local-but-risky-for-frontier on either the Anthropic or
   OpenAI path, the OpenAI path could not be tested at all (no API key
   available), or the local benefit is otherwise not clearly net-positive.
   In any of these cases, document the finding and rationale in
   `PROP-ERW-LOCAL-MODEL-EVALUATION`'s Open Questions/Decision sections
   instead - an untested or ambiguous frontier path is treated as "do not
   ship," not as a documented risk to accept.
6. Either way, update `PROP-ERW-LOCAL-MODEL-EVALUATION` to close out the
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
- Does not attempt OpenAI/GPT testing beyond a good-faith effort if no
  API key is available - but per Required Changes items 3 and 5, an
  untested OpenAI path is not a silently-accepted gap: it forces the
  documented no-change outcome, since `SCENE_SEQUEL_SYSTEM_PROMPT` is
  shared with `OpenAIBackend` and an Anthropic-only regression check
  cannot speak to it.

## Acceptance Criteria

- Several more real segmentation calls run with the reminder appended to
  the real `SCENE_SEQUEL_SYSTEM_PROMPT` against at least `ollama_qwen3_8b`.
- At least 3 paired baseline/modified `claude-opus-4-8` calls on the same
  story, with no consistent quality or latency regression pattern across
  the pairs before any production edit is made - a single pair is not
  sufficient evidence either way.
- At least one real OpenAI/GPT call with the modified prompt compared
  against an unmodified-prompt baseline, or an explicit statement that no
  OpenAI API key was available - and if the latter, the production edit
  does not proceed (see Required Changes item 5).
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
  regression checks in Required Changes items 2-3 (both Anthropic and
  OpenAI) are hard gates before any edit lands, not an optional
  nice-to-have. An untested OpenAI path is treated as a blocker, not an
  acceptable documented gap, since the edit would ship to GPT users too.
- A single paired comparison (one baseline call, one modified call)
  cannot distinguish a real prompt effect from ordinary stochastic
  model/API variance on a non-deterministic call - Required Changes
  item 2 requires at least 3 paired runs specifically to guard against a
  false "no regression" or false "regression" verdict from one unlucky
  or lucky pair.
- `WI-LLM-0051` found the reminder only helps 40% of the time even in the
  benchmark harness - a permanent production edit is not expected to make
  Ollama segmentation fully reliable; the realistic best-case outcome is
  a moderate improvement, not a fix.

## Dependencies / Order

Depends on `WI-LLM-0051` (resolved) for the reminder mitigation strategy,
the harness's `system_prompt_suffix` mechanism this item reuses as its
test vehicle, and the real, live evidence establishing the underlying
gap. No other open dependency.
