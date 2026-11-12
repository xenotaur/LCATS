---
id: WI-GENRE-0110
title: Implement three-way genre-evidence comparison report
type: deliverable
status: proposed
priority: medium
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
  - project/design/proposals/adopted/genre-evidence-sidecars/00_proposal.md
  - project/work_items/resolved/WI-GENRE-0078.md
depends_on:
  - WI-GENRE-0078
  - WI-GENRE-0004
  - WI-LLM-0074
blocked_by: []
blocked: false
blocked_reason: null
resolution: null
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_report
  - create_pr
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - rerun_model_assessments
  - modify_existing_validation_evidence
  - modify_corpora
  - promote_any_label_to_ground_truth
  - create_current_adjudication
  - perform_human_adjudication
  - silently_drop_input_errors
acceptance:
  - "compare_validation.py validates that all three inputs contain the same 146 story IDs and fails clearly on malformed, duplicate, missing, or mismatched records"
  - "The comparison validates model provenance, verifies distinct input hashes, and emits per-story JSONL, summary JSON, and Markdown report outputs"
  - "Every valid story receives exactly one agreement category, including metadata_multi_label_models_split for split selections within a multi-label metadata candidate set"
  - "Tests cover all agreement categories, normalization, malformed input, duplicate IDs, missing IDs, mismatched sets, deterministic output, and both known multi-label split cases"
  - "Existing validation JSONL files and corpora/ remain unchanged"
  - "The documented experiment-specific and package-level validation commands pass with 0 lrh validation errors"
required_evidence:
  - test_output
  - validation_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - experiments/05_metadata_genre_prefilter/compare_validation.py
  - experiments/05_metadata_genre_prefilter/compare_validation_test.py
  - experiments/05_metadata_genre_prefilter/results/full_scan/three_way_genre_comparison.jsonl
  - experiments/05_metadata_genre_prefilter/results/full_scan/three_way_genre_comparison_summary.json
  - experiments/05_metadata_genre_prefilter/results/full_scan/three_way_genre_comparison_report.md
---

# Work Item: WI-GENRE-0110

## Summary

Implement a reproducible three-way comparison over the existing 146-story
genre evidence: Gutenberg metadata-rule labels, Claude Opus `model_detect`
assessments, and local `gpt-oss:20b` assessments.

The implementation will produce machine-readable and human-readable reports
while preserving all existing validation evidence and corpus contents.

## Problem / Context

The planning scope is defined by `WI-GENRE-0078`, which established the
required provenance checks, comparison taxonomy, and report outputs. The
expected implementation artifacts are currently absent.

The existing evidence already contains separate metadata, Opus, and local-model
results for the same 146-story sample. This work turns those historical outputs
into a deterministic, reviewable comparison without rerunning either model.

### Duplication search

- In-repo: No existing `compare_validation.py` implementation or equivalent report generator found.
- Sibling repos: None identified.
- External libraries: None identified; standard repository JSON and testing utilities are sufficient.
- Recommendation: Proceed.

### Demand search

- Work items: Found `WI-GENRE-0078` — "Generate three-way genre-evidence comparison report"; it is the resolved planning item for this implementation.
- Proposals: No separate proposed implementation request found.
- Backlog: No exact matching implementation entry found.
- Recommendation: Implement as the follow-on to `WI-GENRE-0078`.

## Scope

- Read the existing 146-story metadata, Opus, and `gpt-oss:20b` validation outputs.
- Validate input identity, schema, provenance, hashes, and model assignment.
- Produce deterministic per-story, summary, and Markdown comparison outputs.
- Add experiment-local regression tests.

## Required Changes

1. Create `experiments/05_metadata_genre_prefilter/compare_validation.py`.
2. Validate that all inputs refer to the same 146 LCATS story IDs.
3. Validate uniform model provenance:
   - Opus: `claude-opus-4-8`
   - Local model: `gpt-oss:20b`
4. Reject identical source hashes and structural input errors.
5. Normalize genres using the existing repository vocabulary and aliases.
6. Implement all six comparison categories:
   - `all_three_agree`
   - `metadata_opus_only`
   - `metadata_local_only`
   - `models_agree_metadata_differs`
   - `all_three_differ`
   - `metadata_multi_label_models_split`
7. Create `compare_validation_test.py` covering normal, malformed, mismatched,
   and deterministic cases.
8. Generate the JSONL, summary JSON, and Markdown outputs under the existing
   full-scan results directory.
9. Demonstrate that existing validation files and `corpora/` are unchanged.

## Non-Goals

- Do not rerun Claude Opus or `gpt-oss:20b`.
- Do not modify existing validation JSONL files.
- Do not modify or promote files in `corpora/`.
- Do not designate any source as ground truth.
- Do not perform human adjudication.
- Do not implement later event-extraction or paper-analysis work.

## Acceptance Criteria

- The three inputs validate against the same 146-story ID set.
- Provenance, source hashes, and structural input failures are handled fail-closed.
- Every valid story receives exactly one category and preserves the orthogonal multi-label flag.
- Both known split cases are covered:
  - `london/day_s_lodging`
  - `mass_quantities/especially_dance_hall_women__ellerbe_ellerbe`
- All five expected artifacts are generated.
- Existing evidence and corpus files remain unchanged.
- Validation completes successfully.

## Validation

- From `lcats/`: `scripts/version tools`
- From `lcats/`: `scripts/format --check --diff -- ../experiments/05_metadata_genre_prefilter/compare_validation.py ../experiments/05_metadata_genre_prefilter/compare_validation_test.py`
- From `lcats/`: `scripts/lint ../experiments/05_metadata_genre_prefilter/compare_validation.py ../experiments/05_metadata_genre_prefilter/compare_validation_test.py`
- From `lcats/`: `scripts/test ../experiments/05_metadata_genre_prefilter`
- From `lcats/`: `scripts/test`
- From `lcats/`: `lrh validate`
- From the repository root: `git diff --check`

## Risk Notes

- Input files may have subtly different story ordering or schemas; comparison must key by LCATS story ID rather than line position.
- Existing validation outputs are historical evidence and must remain byte-for-byte untouched.
- Multi-label metadata can make naïve agreement categories non-exhaustive; category precedence must remain explicit and tested.
