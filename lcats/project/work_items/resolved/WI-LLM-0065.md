---
resolution: "Resolved by PR #288: gpt-oss:20b entity extraction is production-grounded behind the candidate-scoped adapter (3/3 final runs), but remains consider-only pending precision/recall evaluation; no default model, segmentation routing, or grounding strictness changes."
blocked_reason: null
blocked: false
id: WI-LLM-0065
title: Make gpt-oss:20b entity extraction production-grounded, or explicitly demote it to genre-only
type: evaluation
status: resolved
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams:
  - WS-GPT-OSS-20B-EVALUATION
related_design:
  - lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md
  - lcats/experimental/model_comparison/ollama_gpt_oss_20b/README.md
  - lcats/project/work_items/resolved/WI-LLM-0064.md
depends_on:
  - WI-LLM-0064
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
  - write_docs
  - create_report
forbidden_actions:
  - force_push
  - delete_branch
  - merge_pr
  - change_default_model
  - loosen_grounding_semantics
  - treat_raw_tool_call_as_entity_success
  - modify_segmentation_routing
acceptance:
  - "A candidate-scoped gpt-oss:20b entity-extraction mitigation is tested with 3+ real runs, reporting raw entity count, grounded entity count, grounded mention count, and grounding/item errors"
  - "The evaluation uses production build_entities() semantics as the pass/fail grounding check; raw tool-call success alone is not counted as entity-extraction success"
  - "The evaluation characterizes the complete malformed entity shape observed in results_entity_bestconfig_run*.json, including entity name/type keys and missing entity_id/canonical_name/entity_type fields, and either addresses that full shape for a viable verdict or records failed full-shape mitigation attempts for genre-only demotion"
  - "Any mitigation supporting a viable grounded-entity verdict, including prompt/schema changes or output-compatibility adapters, is wired into and tested through the production candidate path before build_entities(); benchmark-local-only mitigations are diagnostic and require genre-only demotion"
  - "If any output-compatibility adapter is added, it is conservative, candidate-scoped or explicitly production-reviewed, production-path tested, and does not fabricate evidence spans or weaken quote-substring grounding"
  - "The gpt-oss:20b README and ERW local-model proposal are updated to either mark grounded entity extraction viable under a production-wired and tested mitigation or demote gpt-oss:20b to genre-only"
  - "No production default model, segmentation routing, or grounding strictness change is made"
artifacts_expected:
  - lcats/experimental/model_comparison/ollama_gpt_oss_20b/benchmark_entity_production_grounded.py
  - lcats/experimental/model_comparison/ollama_gpt_oss_20b/results_entity_production_grounded.json
  - lcats/experimental/model_comparison/ollama_gpt_oss_20b/README.md
  - lcats/experimental/model_comparison/common/harness.py
  - lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md
required_evidence:
  - lrh_validate
  - test_output
  - manual_review
  - validation_output
---

## Summary

Determine whether `gpt-oss:20b` can be made production-grounded for ERW entity
extraction by testing candidate-scoped prompt/schema/output-handling mitigations
against the real production grounding path. If it cannot, update the local-model
evaluation to demote `gpt-oss:20b` to genre-only.

## Problem / Context

`WI-LLM-0064` showed that `gpt-oss:20b` is reliable at the raw entity tool-call
layer but not production-grounded: the candidate returned 11, 11, and 13 raw
entities across three runs, yet `build_entities()` produced 0 grounded entities
and 0 grounded mentions every time because the returned shape was not the
production entity schema. The committed per-run JSON uses entity objects shaped
like `{"name": "...", "mentions": ["..."]}` - and sometimes `type` - rather
than the `entity_id`, `canonical_name`, `entity_type`, and mention-object fields
that `build_entities()` consumes
(`lcats/experimental/model_comparison/ollama_gpt_oss_20b/README.md:169`). The
production builder explicitly drops ungrounded mentions and drops entities with
no grounded mentions rather than fabricating spans
(`lcats/src/lcats/analysis/event_role_world/entity_extractor.py:121`), and the
production processor routes entity output through that builder
(`lcats/src/lcats/analysis/event_role_world/processor.py:141`). The governing
proposal now leaves this exact follow-up open: whether a schema-specific
reminder, stricter validation, or small compatibility adapter can preserve
grounding without weakening production semantics
(`lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md:852`).

### Duplication search

- In-repo: Related prior work exists in `WI-LLM-0064`, but it diagnosed the
  failure and did not implement or evaluate a rescue path. No existing
  `WI-LLM-0065` or equivalent proposed work item was found.
- Sibling repos: None identified for this LCATS-specific model-comparison
  harness decision.
- External libraries: None identified; this is an LCATS schema/grounding
  compatibility question, not a generic library adoption problem.
- Recommendation: Proceed.

### Demand search

- Work items: No proposed work item already requests this exact follow-up.
- Proposals: Found the open ERW local-model evaluation question asking whether
  `gpt-oss:20b`'s grounded entity-extraction failure is addressable by
  prompt/schema/output handling.
- Backlog: No separate matching backlog entry identified.
- Recommendation: Proceed and link the result back to the proposal.

## Scope

- Evaluate entity extraction only for `gpt-oss:20b`; segmentation has already
  been fairly demoted for this candidate.
- Test at least one candidate-scoped mitigation aimed at producing the complete
  production-grounded entity and mention object shape, such as a schema-specific
  prompt reminder and/or conservative output compatibility handling.
- Use the real `build_entities()` path as the decisive grounding check.
- Treat any benchmark-local-only mitigation as diagnostic only, including
  schema reminders, prompt changes, stricter validation, and compatibility
  adapters. A viable production verdict requires the successful mitigation to be
  wired into and tested on the production candidate path that feeds
  `build_entities()`; otherwise demote `gpt-oss:20b` to genre-only.
- Update the candidate README and governing proposal with either a viable
  grounded-entity verdict or an explicit genre-only demotion.

## Required Changes

1. Inspect the committed `results_entity_bestconfig*.json` failures to
   characterize the complete malformed entity shape: entity `name`/`type`
   aliases, missing `entity_id`/`canonical_name`/`entity_type`, string-valued
   `mentions`, missing `mention_id`, and item-level grounding errors.
2. Add a candidate-local benchmark script, expected as
   `ollama_gpt_oss_20b/benchmark_entity_production_grounded.py`, that tests the
   mitigation under the same local Ollama `gpt-oss:20b` installation and
   records raw vs. grounded counts.
3. If adding output compatibility handling, keep it conservative: normalize only
   the documented malformed shape, synthesize stable IDs only where production
   semantics permit, preserve only evidence that is a verbatim substring of the
   segment, do not invent offsets, do not weaken `build_entities()` grounding
   semantics, and add focused tests if production or shared harness code changes.
4. If a prompt/schema or output-handling mitigation is needed for viability,
   wire it into the production candidate path before `build_entities()` and
   test that production path. If the mitigation remains only in the
   candidate-local benchmark, report the benchmark result as diagnostic and keep
   the production recommendation genre-only.
5. Run at least 3 real entity-extraction runs for each tested mitigation and
   commit the aggregate result JSON plus any per-run evidence needed to review
   failures.
6. Update `ollama_gpt_oss_20b/README.md` and
   `PROP-ERW-LOCAL-MODEL-EVALUATION` with the final recommendation: viable for
   grounded entity extraction only when the successful mitigation is wired into
   and tested through the production candidate path, or genre-only.

## Non-Goals

- Do not retry or rescue segmentation for `gpt-oss:20b`.
- Do not change the production default model.
- Do not treat raw tool-call success or raw entity count as production
  entity-extraction success.
- Do not loosen quote-substring grounding, alignment, or evidence-span
  requirements.
- Do not run a full human precision/recall evaluation; this item answers
  production grounding viability first.
- Do not implement a native Ollama backend or reasoning-effort control unless a
  separate work item scopes it.

## Acceptance Criteria

- A candidate-scoped `gpt-oss:20b` entity-extraction mitigation is tested with
  3+ real runs, reporting raw entity count, grounded entity count, grounded
  mention count, and grounding/item errors.
- The evaluation uses production `build_entities()` semantics as the pass/fail
  grounding check; raw tool-call success alone is not counted as
  entity-extraction success.
- The evaluation characterizes the complete malformed entity shape observed in
  `results_entity_bestconfig_run*.json`, including entity name/type keys and
  missing `entity_id`/`canonical_name`/`entity_type` fields, and either
  addresses that full shape for a viable verdict or records failed full-shape
  mitigation attempts for genre-only demotion.
- If any output-compatibility adapter is added, it is conservative,
  candidate-scoped or explicitly production-reviewed, tested on the production
  candidate path before any viable verdict, and does not fabricate evidence
  spans or weaken quote-substring grounding.
- The `gpt-oss:20b` README and ERW local-model proposal are updated to either
  mark grounded entity extraction viable under a production-wired and tested
  prompt/schema/output-handling mitigation, or demote `gpt-oss:20b` to
  genre-only.
- No production default model, segmentation routing, or grounding strictness
  change is made.

## Validation

- `cd lcats`
- `scripts/test`
- `scripts/test tests/llm_tests`
- `python experimental/model_comparison/ollama_gpt_oss_20b/setup.py`
- `python experimental/model_comparison/ollama_gpt_oss_20b/benchmark_entity_production_grounded.py`
- `lrh validate`

## Risk Notes

- A compatibility adapter could make the candidate look better than it is if it
  silently upgrades malformed output; require explicit evidence-preserving
  behavior, production-path wiring for any viable verdict, and tests.
- Nonzero grounded entity counts are necessary but not sufficient for quality;
  this item should not overclaim precision/recall.
- Local model latency and nondeterminism may make a borderline result hard to
  interpret; keep per-run evidence so the verdict is auditable.
