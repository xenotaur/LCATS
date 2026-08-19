---
resolution: "Implemented metadata-rule genre evidence pilot and merged in PR #301 (commit 4aee8a6ea50fc8ace4c5dc4eb61a0a6a8c07e3de)."
blocked_reason: null
blocked: false
id: WI-GENRE-0002
title: Add metadata-rule genre evidence and 40-story pilot manifest
type: deliverable
status: resolved
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams:
  - WS-GENRE-EVIDENCE-SIDECARS
related_design:
  - lcats/project/design/proposals/proposed/genre-evidence-sidecars/00_proposal.md
  - lcats/project/workstreams/proposed/WS-GENRE-EVIDENCE-SIDECARS.md
  - lcats/project/work_items/resolved/WI-GENRE-0001.md
  - experiments/05_metadata_genre_prefilter/README.md
  - lcats/src/lcats/utils/genre.py
depends_on:
  - WI-GENRE-0001
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
  - create_pr
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - run_network_or_cache_build_without_explicit_approval
  - run_model_calls
  - write_corpus_sidecars
  - promote_sidecars
  - modify_lcats_annotate
  - modify_lcats_promote
  - implement_genre_sidecar_v1_validator
  - run_full_corpus_metadata_labeling
  - implement_100_200_story_sample
acceptance:
  - run_prefilter.py can read Gutenberg subjects from an explicitly supplied existing SQLite cache in read-only mode and continues to report missing cache as a non-fatal readiness state
  - Metadata rows include an assessment-shaped metadata evidence object with LCATS story identity, Gutenberg provenance, scope "gutenberg_volume", timestamp, method/version, raw subjects, raw rule matches, normalized target candidates, secondary signals, and result fields
  - Rule extraction records all matching metadata labels, not only the first exclusive match
  - Normalization maps direct target labels to the 8 LCATS genres and retains non-target evidence separately
  - The runner writes candidates.jsonl, pilot_40_manifest.jsonl, and summary.json only under the experiment output directory
  - Pilot selection is deterministic and reports the target collection-group counts, shortfalls, repeated Gutenberg IDs, and cap behavior if a cap is used
  - Tests cover the cache, rule, normalization, assessment-shape, sampling, and no-mutation guarantees
  - README documents cache sync expectations, metadata-rule evidence fields, pilot outputs, and the current boundary before permanent genre.json sidecars
  - scripts/test passes with no new failures
  - lrh validate reports 0 errors when run from lcats/
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - experiments/05_metadata_genre_prefilter/README.md
  - experiments/05_metadata_genre_prefilter/run_prefilter.py
  - experiments/05_metadata_genre_prefilter/run_prefilter_test.py
  - experiments/05_metadata_genre_prefilter/results/.gitkeep
---

# Work Item: WI-GENRE-0002

## Summary

Extend `experiments/05_metadata_genre_prefilter` from a dry-run discovery scaffold into a metadata-rule evidence pilot: read Gutenberg subjects from an explicitly supplied existing cache, generate experiment-local genre evidence records, and select a deterministic 40-story heterogeneous pilot manifest.

## Problem / Context

`WI-GENRE-0001` deliberately stopped before metadata-rule genre assessment generation so the project could first validate LCATS story identity, Gutenberg ID parsing, cache readiness, and no-network behavior. The governing proposal's next implementation step is metadata rule evidence plus a 40-story pilot, using LCATS story IDs as primary identity and Gutenberg IDs only as provenance. The existing `lcats.utils.genre` rules are useful but need all-match extraction and normalization rather than exclusive first-match labeling.

### Duplication search

- In-repo: Related scaffolding exists in `experiments/05_metadata_genre_prefilter/`, and reusable rule definitions exist in `lcats/src/lcats/utils/genre.py`, but no existing implementation produces metadata-rule assessment records or a 40-story pilot manifest.
- Sibling repos: None identified.
- External libraries: None identified. This should reuse existing LCATS utilities and SQLite read-only access rather than adding a new dependency.
- Recommendation: Proceed by extending experiment 05.

### Demand search

- Work items: `WI-GENRE-0001` names metadata-rule assessment and pilot selection as the next work item, but does not implement them.
- Proposals: `PROP-GENRE-EVIDENCE-SIDECARS` explicitly requests metadata-rule evidence and a 40-story pilot as implementation step 2.
- Backlog: No separate matching backlog entry found beyond the proposal/workstream demand.
- Recommendation: Proceed and link this work item to `WS-GENRE-EVIDENCE-SIDECARS`.

## Scope

- Add read-only Gutenberg subject retrieval from an explicitly supplied existing cache database.
- Generate metadata-rule genre evidence records in the proposal's append-only assessment style, but keep them experiment-local.
- Normalize all matching `lcats.utils.genre` labels into LCATS target candidates and secondary signals.
- Select and write a deterministic 40-story heterogeneous pilot manifest across Lovecraft, Sherlock, O. Henry collections, and `mass_quantities`.
- Update tests and README for the metadata evidence and pilot-selection behavior.

## Required Changes

1. Update `experiments/05_metadata_genre_prefilter/run_prefilter.py`.
   - Keep the default no-network/read-only posture from `WI-GENRE-0001`.
   - Add a subject lookup path that opens `--cache-db` read-only and retrieves Gutenberg subjects for parseable Gutenberg IDs.
   - Do not import or call mutating Gutenberg cache builders on the default path.
   - Add rule matching that records every matching `lcats.utils.genre.GENRE_RULES` label and the subject/pattern evidence behind each match.
   - Normalize direct LCATS target mappings:
     - `SF` -> `science fiction`
     - `Fantasy` -> `fantasy`
     - `Horror` -> `horror`
     - `Mystery` -> `mystery`
     - `Western` -> `western`
     - `Adventure` -> `adventure`
     - `Romance` -> `romance`
     - `Humor / satire` -> `humor`
   - Treat `Crime` as suggestive evidence for `mystery`, and keep `Sea`, `Historical`, `War`, `Children / juvenile`, and other non-target labels as secondary evidence unless later work upgrades them.
   - Add an assessment-shaped metadata evidence object with `assessment_id`, `label`, `generated_at`, `scope`, `method`, `provenance`, `evidence`, and `result`.
   - Add deterministic pilot selection for roughly 10 stories each from `lovecraft`, `sherlock`, O. Henry collections (`ohenry-four_million` and/or `ohenry-whirligigs`), and `mass_quantities`.
   - Report repeated Gutenberg ID diagnostics and any optional `--max-per-gutenberg-id` cap behavior as sampling diagnostics, not identity semantics.
   - Write `candidates.jsonl`, `pilot_40_manifest.jsonl`, and `summary.json` under the requested output directory.

2. Update `experiments/05_metadata_genre_prefilter/run_prefilter_test.py`.
   - Use temporary SQLite fixtures that match the cache tables needed for subject lookup.
   - Cover read-only cache access and cache-missing behavior.
   - Cover all-match rule extraction rather than first-match-only classification.
   - Cover target normalization and secondary-signal retention.
   - Cover metadata assessment record shape and provenance fields.
   - Cover deterministic pilot selection and protected output paths.
   - Ensure no test performs real network, model, cache-building, corpus-sidecar, or promotion work.

3. Update `experiments/05_metadata_genre_prefilter/README.md`.
   - Document how to point the runner at an existing local Gutenberg metadata cache.
   - Document the metadata evidence record fields and label normalization.
   - Document candidate and pilot manifest outputs.
   - State the boundary before permanent `genre.json`, sidecar validation, promotion, annotation append mode, model evidence, human adjudication, and the 100-200 story sample.

4. Preserve `experiments/05_metadata_genre_prefilter/results/.gitkeep`.
   - Do not commit generated pilot output unless the implementation run explicitly includes and reviews a small deterministic fixture output or an approved real-cache pilot output.

## Non-Goals

- Do not build, download, refresh, or repair the Gutenberg metadata cache.
- Do not call local or remote models.
- Do not write `genre.json` sidecars into `data/` or `corpora/`.
- Do not modify `lcats annotate` or `lcats promote`.
- Do not define the final `genre-sidecar-v1` validator; this item emits assessment-shaped experiment records only.
- Do not promote pilot sidecars.
- Do not implement the larger 100-200 story sample.
- Do not run or commit a whole-corpus metadata-labeling pass; that remains optional future work after the 40-story pilot path is reviewed.

## Acceptance Criteria

- `run_prefilter.py` can read Gutenberg subjects from an explicitly supplied existing SQLite cache in read-only mode and continues to report missing cache as a non-fatal readiness state.
- Metadata rows include an assessment-shaped metadata evidence object with LCATS story identity, Gutenberg provenance, `scope: "gutenberg_volume"`, timestamp, method/version, raw subjects, raw rule matches, normalized target candidates, secondary signals, and result fields.
- Rule extraction records all matching metadata labels, not only the first exclusive match.
- Normalization maps direct target labels to the 8 LCATS genres and retains non-target evidence separately.
- The runner writes `candidates.jsonl`, `pilot_40_manifest.jsonl`, and `summary.json` only under the experiment output directory.
- Pilot selection is deterministic and reports the target collection-group counts, shortfalls, repeated Gutenberg IDs, and cap behavior if a cap is used.
- Tests cover the cache, rule, normalization, assessment-shape, sampling, and no-mutation guarantees.
- README documents usage and boundaries.
- `scripts/test` passes with no new failures.
- `lrh validate` reports 0 errors.

## Validation

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `cd lcats && lrh validate`
- `python experiments/05_metadata_genre_prefilter/run_prefilter.py --dry-run --output experiments/05_metadata_genre_prefilter/results/smoke`
- `python experiments/05_metadata_genre_prefilter/run_prefilter.py --dry-run --cache-db /path/to/existing/gutenbergindex.db --output experiments/05_metadata_genre_prefilter/results/pilot_40`

Readiness check after authoring:

- `cd lcats && lrh work-items readiness WI-GENRE-0002 --format md`

The readiness command should report `prompt_ready: yes` and no readiness
warnings. This is distinct from `lrh validate`, which may report existing
repository warnings unrelated to this work item.

## Risk Notes

- Gutenberg metadata is volume-level evidence for many LCATS story buckets, so every metadata assessment should use `scope: "gutenberg_volume"` and avoid treating Gutenberg ID as story identity.
- The current `lcats.utils.genre.classify_exclusive()` returns only the first match plus the broad match list; this item should use the underlying rules to preserve all evidence and avoid silently privileging rule order.
- Cache access must stay read-only and explicit. A missing cache should produce an incomplete metadata-evidence result or readiness warning, not a download/build attempt.
- The O. Henry corpus appears split across `ohenry-four_million` and `ohenry-whirligigs`; the pilot selector should treat those as the O. Henry collection group rather than assuming a single `ohenry` directory.
- Full-corpus metadata labeling may be tempting if the cache is fast, but committing that output belongs to a later explicitly approved work item.
