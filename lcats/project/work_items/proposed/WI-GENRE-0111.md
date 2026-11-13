---
id: WI-GENRE-0111
title: Add human genre review and adjudication support
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
  - project/design/genre-sidecars-in-release-workflow.md
depends_on:
  - WI-GENRE-0003
  - WI-GENRE-0076
  - WI-GENRE-0110
blocked_by: []
blocked: false
blocked_reason: null
resolution: null
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_report
  - write_docs
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - rerun_model_assessments
  - modify_metadata_or_model_evidence
  - silently_promote_any_label_to_ground_truth
  - perform_corpus_wide_adjudication
  - modify_existing_validation_evidence
  - replace_corpora_wholesale
acceptance:
  - "A deterministic review manifest identifies the 49 disagreement cases from WI-GENRE-0110, preserves their source labels, and records review status without changing the comparison artifacts"
  - "A human-assessment input and append path records reviewer identity, timestamp, rationale, selected label or explicit unresolved status, and source/story provenance in genre-sidecar-v1"
  - "Optional current_adjudication references the reviewed assessment record or documented consensus and remains null for unreviewed stories"
  - "A bounded reviewed subset and all unresolved cases are reported without silently dropping cases or treating metadata/model output as ground truth"
  - "Tests cover valid human assessments, unresolved decisions, duplicate assessment IDs, invalid adjudication references, preservation of prior evidence, and atomic/validated writes"
  - "The documented experiment-specific and package-level validation commands pass with 0 lrh validation errors"
required_evidence:
  - test_output
  - validation_output
  - manual_review
  - lrh_validate
artifacts_expected:
  - experiments/05_metadata_genre_prefilter/human_review.py
  - experiments/05_metadata_genre_prefilter/human_review_test.py
  - experiments/05_metadata_genre_prefilter/results/full_scan/human_review_manifest.jsonl
  - experiments/05_metadata_genre_prefilter/results/full_scan/human_review_results.jsonl
  - experiments/05_metadata_genre_prefilter/results/full_scan/human_review_report.md
  - experiments/05_metadata_genre_prefilter/README.md
---

# Work Item: WI-GENRE-0111

## Summary

Add a traceable human-review layer for the 49 genre disagreements identified by
WI-GENRE-0110. The workflow will append human assessments and optional
adjudication references to the existing genre-sidecar evidence without
overwriting metadata or model assessments or declaring an automatic ground
truth.

## Problem / Context

The genre-labeling effort now has three comparable evidence sources for the same
146 stories: Gutenberg metadata-rule candidates, Claude Opus assessments, and
local `gpt-oss:20b` assessments. WI-GENRE-0110 measured their agreement and
disagreement, but intentionally stopped at comparison; its report records 97
three-way agreements and 49 disagreements and explicitly treats disagreement as
evidence for later review.

The adopted genre-sidecar design chooses to represent human review as another
assessment in the same append-only ledger, with optional `current_adjudication`.
The existing `genre-sidecar-v1` validator and append-mode annotation path provide
the preservation and validation foundation. This work is now needed to turn the
comparison output into a bounded, reviewable human decision process.

### Duplication search

- In-repo: Related foundations exist in `genre-sidecar-v1`, append-mode `lcats annotate`, and WI-GENRE-0110's comparison outputs; no existing human-genre review workflow or review-manifest implementation was found.
- Sibling repos: None identified.
- External libraries: None identified; the required workflow is project-specific and should use the existing sidecar schema and atomic-write conventions.
- Recommendation: Proceed by extending the existing sidecar/experiment infrastructure.

### Demand search

- Work items: No proposed work item directly covers human genre review or adjudication. WI-GENRE-0003 and WI-GENRE-0076 provide related foundations, while WI-GENRE-0110 provides the review population.
- Proposals: The adopted genre-evidence-sidecars proposal explicitly calls for human review/adjudication support.
- Backlog: No matching backlog entry found.
- Recommendation: Proceed and link this item to `WS-GENRE-EVIDENCE-SIDECARS`; no existing item should be closed.

## Scope

- Generate a deterministic review manifest from the 49 disagreement records in WI-GENRE-0110, retaining all metadata, Opus, and local-model evidence.
- Define a reviewer input contract for selected labels, unresolved decisions, rationale, reviewer identity, and timestamps.
- Append validated human assessments to existing `genre-sidecar-v1` records and support optional `current_adjudication` references.
- Review a bounded, explicitly identified subset and report reviewed, unresolved, and excluded cases.

## Required Changes

1. Create `experiments/05_metadata_genre_prefilter/human_review.py` to build the review manifest, validate reviewer input, append human assessments through the existing sidecar validation/write path, and produce deterministic review outputs.

2. Add `experiments/05_metadata_genre_prefilter/human_review_test.py` covering manifest construction, human-assessment validation, unresolved decisions, preservation of existing assessments, adjudication references, duplicate IDs, malformed input, and failed atomic writes.

3. Generate `results/full_scan/human_review_manifest.jsonl` containing all 49 disagreement cases and their immutable source evidence, plus explicit review status fields.

4. Generate `results/full_scan/human_review_results.jsonl` and `human_review_report.md` for the bounded reviewed subset, including reviewer provenance, rationales, unresolved cases, and any adjudication references.

5. Update the experiment README with the review-input contract, selection policy, preservation rules, and exact commands for reproducing or inspecting the review artifacts.

6. Revalidate every modified sidecar with `genre_sidecar.validate_sidecar()`; preserve existing metadata and model assessments byte-for-byte or by structured equality, except for the explicitly appended human assessment or adjudication reference.

## Non-Goals

- Do not rerun Claude Opus, `gpt-oss:20b`, or any other model.
- Do not modify historical validation JSONL or the WI-GENRE-0110 comparison artifacts.
- Do not infer a human label automatically from majority vote or agreement.
- Do not silently promote metadata or model labels to ground truth.
- Do not adjudicate all 146 stories by default; review must remain bounded and explicitly reported.
- Do not replace or wholesale-rewrite `corpora/`.
- Do not build a general-purpose annotation UI or a broader event-analysis workflow.

## Acceptance Criteria

- The 49 WI-GENRE-0110 disagreement records are represented in a deterministic, auditable review manifest with no source evidence dropped.
- Human assessments include reviewer identity, timestamp, rationale, decision status, and story/source provenance, and are appended through validated sidecar writes.
- `current_adjudication` is optional, explicit, and referenceable; unreviewed stories remain unadjudicated.
- A bounded reviewed subset, excluded cases, and unresolved cases are reported.
- Existing metadata/model evidence and comparison outputs remain unchanged.
- Focused tests, package tests, and `lrh validate` pass with 0 errors.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/format --check --diff ../experiments/05_metadata_genre_prefilter/*.py`
- `scripts/lint`
- `scripts/lint ../experiments/05_metadata_genre_prefilter/*.py`
- `scripts/test ../experiments/05_metadata_genre_prefilter`
- `scripts/test`
- `lrh validate`
- `git diff --check`

## Risk Notes

- Human decisions can be mistaken for objective truth; all outputs must retain evidence provenance and explicit reviewer rationale.
- A malformed review input could corrupt an existing sidecar; writes must be validated and atomic, with refusal rather than overwrite on failure.
- A review subset can bias later analysis; the manifest must expose selection, exclusion, and unresolved status.
- Existing promoted sidecars contain historical evidence; the implementation must append rather than rewrite or normalize unrelated fields.

## Dependencies / Order

WI-GENRE-0111 follows WI-GENRE-0110 because the comparison report defines the
review population. It relies on WI-GENRE-0003's sidecar validator and
WI-GENRE-0076's append-preserving write behavior. After this item, downstream
Worldcon or event-analysis work can consume explicitly reviewed evidence while
still distinguishing it from metadata and model assessments.
