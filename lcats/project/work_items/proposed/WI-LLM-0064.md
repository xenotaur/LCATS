---
resolution: null
blocked_reason: null
blocked: false
id: WI-LLM-0064
title: Establish a best-of-breed config for ollama_gpt_oss_20b and fix harness diagnostic gaps
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
  - lcats/experimental/model_comparison/ollama_gpt_oss_20b/README.md
  - lcats/project/work_items/resolved/WI-LLM-0051.md
  - lcats/project/work_items/resolved/WI-LLM-0062.md
  - lcats/project/work_items/resolved/WI-LLM-0063.md
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
  - break_shared_harness_existing_contracts
  - loosen_alignment_check_strictness
acceptance:
  - "Segmentation diagnostic capture implemented and exercised on at least 1 real alignment failure, with the model's actual anchor text visible in a committed result"
  - "Grounded entity counts (via build_entities()) computed for at least 3 real entity-extraction runs, compared against the existing raw counts"
  - "temperature=1.0 variant tested with 3+ real runs each for segmentation and entity extraction; verbatim-quote reminder variant tested with 3+ real runs for segmentation"
  - "A written best-of-breed config recommendation for gpt-oss:20b in ollama_gpt_oss_20b/README.md, grounded in the above evidence"
artifacts_expected:
  - lcats/experimental/model_comparison/ollama_gpt_oss_20b/README.md
  - lcats/experimental/model_comparison/ollama_gpt_oss_20b/benchmark_segmentation_bestconfig.py
  - lcats/experimental/model_comparison/ollama_gpt_oss_20b/benchmark_entity_bestconfig.py
  - lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md
required_evidence:
  - lrh_validate
  - manual_review
  - test_output
---

## Summary

Add diagnostic instrumentation the benchmark harness currently lacks (raw
model output on segmentation alignment failure; grounded - not raw -
entity counts for entity extraction), then use those diagnostics to test
a `gpt-oss:20b`-specific config variant (starting with `temperature=1.0`,
matching both Ollama's own bundled default and OpenAI's documented
guidance, plus a verbatim-quote reminder) - without changing the shared
harness code path every other candidate was already tested against.

## Problem / Context

Discussion following `WI-LLM-0063` surfaced two real, previously-
undiscovered gaps and one concrete, cheap hypothesis to test:

1. **Diagnostic gap (segmentation):** `_run_segmentation_once()`
   (`common/harness.py:465-473`) only reads `extracted_output`
   (explicitly `None` on alignment failure, per
   `llm_extractor.py:563-576`) and `raw_output` (empty on a successful
   tool call). It never reads `parsed_output`, which the extractor
   actually returns and which still holds the model's real
   pre-alignment anchor strings - every committed
   `results_segmentation_run*.json` has `raw_output_preview: null`, so
   `gpt-oss:20b`'s 3/3 alignment failures are undiagnosed.
2. **Diagnostic gap (entity extraction):** `entity_count` in
   `_run_entity_extraction_once()` (`common/harness.py:253-254,277`) is
   computed from the raw, ungrounded tool-call output. The real
   production pipeline (`processor.py:141`) calls `build_entities()`
   (`entity_extractor.py:121`), which silently drops any mention whose
   `quote` field isn't a real substring of the segment, and drops an
   entity entirely if all its mentions get dropped. The benchmark never
   calls this - `gpt-oss:20b`'s reported 12/21/34-entity spread across 3
   runs is an upper bound, not the number the real pipeline would
   actually keep.
3. **Untested config gap:** `ollama show gpt-oss:20b --parameters`
   reports this model's own bundled default is `temperature 1`, and
   OpenAI's own `gpt-oss` guidance (GitHub `openai/gpt-oss`) recommends
   `temperature=1.0, top_p=1.0` - but every `gpt-oss:20b` benchmark
   script inherits `common/harness.py`'s `DEFAULT_TEMPERATURE=0.2`
   unchanged, unlike `ollama_qwen3_8b`, which already overrides
   temperature per its own documented recommendation
   (`ollama_qwen3_8b/benchmark.py`).

Two other options discussed (explicit `reasoning_effort`/`think` level
via Ollama's native API; switching off the OpenAI-compat endpoint
entirely) require new backend code with documented external
unreliability, and are deliberately out of scope here - see Non-Goals.

### Duplication search
- In-repo: no existing work item covers harness diagnostic gaps or a
  candidate-specific config variant for `gpt-oss:20b`. `WI-LLM-0063`
  vetted the candidate as-tested but didn't change its configuration.
- Sibling repos / external libraries: none identified - specific to this
  repo's benchmark harness and entity/segment schemas.
- Recommendation: proceed, no duplication.

### Demand search
- Work items: none found requesting this specifically.
- Proposals: `PROP-ERW-LOCAL-MODEL-EVALUATION`'s Open Questions (updated
  by `WI-LLM-0063`) names the alignment-rejection failure as unresolved
  but doesn't request a fix - this WI satisfies that gap.
- Recommendation: no action; this work item is the first to address it.

## Scope

- Add diagnostic capture to a new, candidate-scoped path - not by
  changing `run_segmentation()`/`run_entity_extraction()`'s existing
  return contract, which every already-tested candidate's committed
  results depend on staying stable.
- Build a `gpt-oss:20b`-specific benchmark variant (e.g.
  `ollama_gpt_oss_20b/benchmark_bestconfig_*.py`) layering
  `temperature=1.0` and a verbatim-quote reminder on top of the existing
  calls.
- Run the grounded-entity-count analysis against already-committed
  and/or freshly-captured raw entity data.
- Document a best-of-breed config recommendation for this candidate
  specifically.

## Required Changes

1. Add a diagnostic-capture mechanism for segmentation alignment
   failures - either a purely additive new function in
   `common/harness.py` (e.g. a new, separately-named helper - not a
   change to `run_segmentation()`'s existing signature, default
   parameter values, or return contract) or a candidate-local wrapper in
   `ollama_gpt_oss_20b/`. Either is acceptable; what's forbidden is
   altering `run_segmentation()`'s existing behavior in a way that could
   change results already committed for other candidates.
2. Add a grounded-entity-count helper (new function, same additive-only
   constraint as above) that calls the real `build_entities()` against
   captured raw entity/quote data and segment text, reporting both raw
   and grounded counts.
3. Add `ollama_gpt_oss_20b/benchmark_segmentation_bestconfig.py` and
   `benchmark_entity_bestconfig.py` (or a combined variant), each
   testing `temperature=1.0` plus the diagnostic capture above; entity
   extraction variant also reports the grounded count.
4. Test a verbatim-quote reminder (reusing the existing
   `system_prompt_suffix` hook already wired into
   `_run_segmentation_once`) as a second, separately-labeled variant.
5. At least 3 real runs per variant tested, matching this lineage's
   evidence standard.
6. Write up findings and a best-of-breed config recommendation in
   `ollama_gpt_oss_20b/README.md` and `PROP-ERW-LOCAL-MODEL-EVALUATION`.

## Non-Goals

- Does not change `common/harness.py`'s existing `run_segmentation()`/
  `run_entity_extraction()`/`run_genre_detection()` default behavior or
  signatures in a way that could alter already-committed results for
  other candidates.
- Does not loosen `text_segmenter.py`'s alignment strictness
  (`find_anchor_in_range`/`align_segment`) - a deliberate,
  already-documented design decision (`WI-SEGMENT-0059`'s history of
  silent wrong-span bugs), not a knob to tune for one candidate.
- Does not implement `reasoning_effort`/`think`-level control or a
  native-Ollama-API backend - both require new production-adjacent
  backend code with documented external reliability concerns; deferred
  as a separate, larger WI if the config changes here prove
  insufficient.
- Does not change the pipeline's default model - a positive finding
  here is evidence for a future decision, not this item's own action.
- Does not run a full precision/recall ground-truth evaluation - the
  grounded-vs-raw entity count comparison is a cheaper, real proxy, not
  a substitute for that larger, still-deferred effort.

## Acceptance Criteria

- Segmentation diagnostic capture implemented and exercised on at least
  1 real alignment failure, with the model's actual anchor text visible
  in a committed result.
- Grounded entity counts computed (via `build_entities()`) for at least
  3 real entity-extraction runs, compared against the existing raw
  counts.
- `temperature=1.0` variant tested with 3+ real runs each for
  segmentation and entity extraction; verbatim-quote reminder variant
  tested with 3+ real runs for segmentation.
- A written best-of-breed config recommendation for `gpt-oss:20b` in
  `ollama_gpt_oss_20b/README.md`, grounded in the above evidence -
  including "no config change helped" as a valid, complete finding if
  that's what the evidence shows.

## Validation

- `scripts/test`
- `lrh validate`
- Real benchmark runs for each variant, with captured raw output
  inspected on any failure

## Risk Notes

- The grounded-entity-count check could reveal the raw counts were
  already close to grounded (little hallucination) - a valid negative
  finding, not a failed investigation.
- `temperature=1.0` might not fix the alignment-rejection failure at all
  (temperature affects diversity, not necessarily instruction-following
  fidelity) - testing it is still worthwhile since it's nearly free and
  directly evidence-grounded, but the WI should not assume success in
  advance.
- Ollama's own external, documented `reasoning_effort` flakiness
  (open-webui#17485) is exactly why that lever is excluded from this
  WI's scope rather than attempted here.
