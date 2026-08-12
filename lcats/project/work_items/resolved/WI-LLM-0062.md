---
resolution: "Both mechanisms investigated with real evidence via PR #277. Mechanism (a) (silent ignore): reminder-retry mitigation adapted from WI-LLM-0051 to run_entity_extraction() - ollama_gemma4_12b showed partial recovery (1 of 2 applicable retries succeeded, after correcting a max_tokens=8192 truncation confound by raising to 16384); ollama_deepseek_r1_14b showed no recovery (0/3), and a tuned temperature=0.6 didn't help either - a more robust instance of the mechanism. Mechanism (b) (active filter rejection): the original schema-complexity hypothesis was disproven - gemini_flash's real, unmodified ENTITY_TOOL_SCHEMA succeeds 3/3 at max_tokens=32000 (vs. failing at 8192/16384); a minimal synthetic schema also succeeded 3/3. The real constraint is token budget, not schema shape. A resource-accounting bug in the new retry wrapper (caught by automatic first-push review) was fixed and all affected result files regenerated with real reruns. Verdicts written into PROP-ERW-LOCAL-MODEL-EVALUATION and each affected candidate's README."
blocked_reason: null
blocked: false
id: WI-LLM-0062
title: Investigate the two distinct tool_choice failure mechanisms found in WI-LLM-0056's tranche 1
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
  - lcats/experimental/model_comparison/README.md
  - lcats/project/work_items/resolved/WI-LLM-0051.md
  - lcats/project/work_items/resolved/WI-LLM-0056.md
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
  - "At least 3 paired baseline/reminder runs per candidate (ollama_gemma4_12b, ollama_deepseek_r1_14b) for WI-LLM-0051's reminder-retry mitigation applied to entity extraction, not a single one-off attempt per model - WI-LLM-0051's own reminder has only a 40% success rate on segmentation, so one run cannot distinguish a real prompt effect from ordinary run-to-run variation"
  - "Real, committed test results characterizing whether Gemini's function_call_filter rejection is schema-shape-dependent (tested against at least one simpler tool schema, not just ENTITY_TOOL_SCHEMA)"
  - "A written verdict for each mechanism in PROP-ERW-LOCAL-MODEL-EVALUATION or a follow-on note - reproduced/characterized, or a documented good-faith 'not resolved,' not left open indefinitely"
artifacts_expected:
  - lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md
  - lcats/experimental/model_comparison/ollama_gemma4_12b/README.md
  - lcats/experimental/model_comparison/ollama_deepseek_r1_14b/README.md
  - lcats/experimental/model_comparison/gemini_flash/README.md
required_evidence:
  - manual_review
  - test_output
---

## Summary

`WI-LLM-0056`'s tranche 1 (real cross-provider entity-extraction
benchmarks) found that 3 of 6 candidates failed via `tool_choice` never
producing a usable result, but review caught that this is two genuinely
different failure mechanisms, not one combined gap:

- **Silent ignore** (`ollama_gemma4_12b`, `ollama_deepseek_r1_14b`): the
  model returns `finish_reason='stop'` with real free-text content,
  never attempting the forced tool call at all - the same mechanism
  `WI-LLM-0051` already characterized and partially mitigated (a
  system-prompt reminder recovered 40% of failures) on the segmentation
  stage.
- **Active filter rejection** (`gemini_flash` only): Gemini's own
  OpenAI-compatible endpoint *attempts* the function call, and its
  internal filter rejects it (`finish_reason` contains
  `'function_call_filter: MALFORMED_FUNCTION_CALL'`, content is empty).
  This is a provider-side validation rejection, not a silent ignore, and
  has not been investigated at all - `WI-LLM-0056` only observed and
  documented it.

This item investigates both mechanisms independently, since they likely
need different fixes and treating them as one combined question would
misdirect either investigation.

## Problem / Context

`WI-LLM-0051` tested and implemented a reminder-retry mitigation for
mechanism (a) on the segmentation stage only (`common/harness.py`'s
`run_segmentation()`). Whether the same mitigation helps on entity
extraction, and whether `deepseek-r1:14b`'s own recommended sampling
settings (never checked against
`ollama show deepseek-r1:14b --parameters`, unlike `ollama_qwen3_8b`'s
candidate-specific override)
change the outcome, are both explicitly flagged as untested in
`WI-LLM-0056`'s own follow-up notes. Mechanism (b) has no prior
investigation at all - `gemini_flash/README.md` only documents the
observed failure, with no hypothesis tested about its cause.

### Prior Art Check

**Duplication search:** In-repo, `WI-LLM-0051` covers mechanism (a) but
only on the segmentation stage; no existing investigation covers entity
extraction or mechanism (b) at all. No sibling repos or external
libraries considered - this is specific to this pipeline's exact tool
schemas and these providers' specific runtime behavior. Recommendation:
proceed, no duplication.

**Demand search:** `WI-LLM-0056`'s own execution record
(`project/executions/WI-LLM-0056/2026_08_09_06_08_48_WI_LLM_0056_TRANCHE1_COMPLETE.md`)
explicitly names this as follow-up work, deferred to a separate WI per
the user's own decision at that item's closeout. Recommendation: this
work item satisfies that request.

## Scope

- **Mechanism (a):** run `ollama_gemma4_12b`'s and
  `ollama_deepseek_r1_14b`'s entity-extraction benchmark with
  `WI-LLM-0051`'s reminder text appended to the system prompt (the same
  `_SEGMENTATION_RETRY_REMINDER`-style mechanism, adapted for
  `run_entity_extraction()` if it doesn't already support a retry path -
  check before assuming it needs new code) - **at least 3 paired
  baseline/reminder runs per candidate**, not a single one-off attempt,
  since the reminder's own known success rate (40% on segmentation)
  means one run cannot distinguish a real effect from ordinary
  run-to-run variation (review finding, PR #275). Separately, check
  `deepseek-r1:14b`'s own documented sampling defaults and test whether
  a tuned temperature changes its outcome, independent of the reminder.
- **Mechanism (b):** test `gemini_flash` against a simpler tool schema
  (e.g. reuse an existing smaller schema already in this repo, or a
  minimal synthetic one) to check whether the filter rejection is
  schema-complexity-dependent, matching the pattern `WI-LLM-0051` used to
  characterize the segmentation-vs-entity-extraction schema-size
  hypothesis. Check Gemini's own API documentation/known-issue trackers
  for `MALFORMED_FUNCTION_CALL` as a documented behavior.
- Update `PROP-ERW-LOCAL-MODEL-EVALUATION` (or a follow-on note) with an
  explicit verdict for each mechanism.

## Required Changes

- Real, live benchmark runs for both mechanisms (not simulated).
- `common/harness.py` changes only if a retry/mitigation path proves
  warranted by real findings for mechanism (a) - do not add speculative
  resilience code for an unconfirmed benefit, matching `WI-LLM-0051`'s
  own established discipline.
- README updates for the three affected candidates with real, committed
  results.

## Non-Goals

- Does not implement a production fix for either mechanism without a
  positive, tested mitigation first.
- Does not touch `run_pilot.py` or any `lcats.llm` backend code
  speculatively - any backend-level change must be justified by a real
  finding from this investigation, not assumed upfront.
- Does not investigate `openai_gpt55`'s schema bug
  (`entity_extractor.py`'s `ENTITY_TOOL_SCHEMA` missing `grammatical_role`
  from `required`) - that is a separate, already-flagged, unrelated
  finding.

## Acceptance Criteria

- At least 3 paired baseline/reminder runs per candidate (not a single
  one-off attempt) for the reminder-retry mitigation applied to entity
  extraction on both affected candidates.
- Real, committed test results characterizing whether Gemini's filter
  rejection is schema-shape-dependent.
- A written verdict for each mechanism, not left open indefinitely.

## Validation

- `scripts/test` (canonical full-suite runner, not a scoped
  `tests/llm_tests`-only invocation - this WI's own scope may touch
  `common/harness.py` and the entity-extraction/`analysis` layer, which
  `tests/llm_tests` alone does not cover)
- `lrh validate`
- Real benchmark runs for both mechanisms, with `raw_output_preview`/
  `error_message` inspected on any failure

## Risk Notes

- Mechanism (a)'s reminder mitigation was only 40% effective on
  segmentation - a similarly partial result on entity extraction is a
  valid, expected outcome, not a failed investigation.
- Mechanism (b) may turn out to be a Gemini-side bug or policy with no
  available workaround from this repo's side - a "could not resolve,
  documented as an external constraint" verdict is acceptable per this
  proposal lineage's established evidence-quality standard (see
  `WI-LLM-0051`'s own precedent for treating a negative/inconclusive
  result as a valid outcome).
