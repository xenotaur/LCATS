---
resolution: null
blocked_reason: null
blocked: false
id: WI-LINGUISTICS-0010
title: Add a resumable POS audit helper
type: deliverable
status: proposed
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams:
  - WS-COMPARATIVE-LEXICAL-VISUALIZATION
related_design:
  - project/design/proposals/proposed/comparative-lexical-visualization/00_proposal.md
depends_on:
  - WI-LINGUISTICS-0007
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - run_full_corpus
  - promote_sidecars
  - change_canonical_linguistics_schemas
  - build_general_annotation_platform
  - fabricate_human_labels
  - produce_pos_figures
acceptance:
  - An experiment-local helper presents the next unresolved audit row with stable token identity, story/genre, context, machine label, and audit guidance
  - Human decisions are stored separately from the generated sample and support explicit reviewed, uncertain, blocked, and issue-bearing states
  - Segmentation, tokenization, context, and POS issues can be recorded without silently discarding the affected example
  - The helper validates completeness, stable token keys, allowed labels, and explicit dispositions before scoring
  - Existing deterministic POS scoring remains authoritative, and tests cover resume behavior, invalid input, unresolved rows, issue recording, and scoring handoff
artifacts_expected:
  - experiments/09_rich_linguistics_genre_sample/audit_pos.py
  - experiments/09_rich_linguistics_genre_sample/audit_pos_test.py
  - experiments/09_rich_linguistics_genre_sample/README.md
---

# Work Item: WI-LINGUISTICS-0010

## Summary

Add a small experiment-local helper for reviewing the 192-row POS audit
packet produced by the rich linguistics pilot. The helper should make the
review resumable and deterministic, provide detailed context and guidance,
record segmentation and other data-quality issues explicitly, and hand
validated decisions to the existing POS scoring implementation.

## Problem / Context

The pilot currently generates a CSV with stable token keys, machine UPOS
labels, context, and blank `gold_upos` and `notes` fields. Reviewers must edit
that CSV manually and rerun the experiment, with no command for finding the
next unresolved row, tracking review state, or distinguishing an uncertain
POS judgment from a segmentation or tokenization defect.

The helper is needed because the pilot contains historical prose, ambiguous
tokens, and observed segmentation problems. It must preserve the generated
sample as an input snapshot and store human decisions separately so generated
data is not accidentally overwritten.

### Duplication search

The existing pilot runner provides deterministic sample generation, label
validation, scoring, and gate calculation, but it does not provide an
interactive or resumable review workflow. The repository contains broader
annotation and adjudication work for genre and other analyses, but no POS
audit queue or helper for this experiment. No existing component provides the
required bounded behavior.

### Demand search

The need is established by the unresolved `manual_audit_pending` state in the
pilot output and by `WI-LINGUISTICS-0008`, which cannot evaluate its
full-corpus quality gate until the pilot evidence is complete. This item
supports that gate but does not replace or broaden the linguistics collection
pipeline.

## Scope

- Operate on the existing experiment-09 audit sample and stable `token_key`
  identifiers.
- Provide commands for status, next unresolved row, recording a decision,
  recording issue codes, validation, and scoring handoff.
- Display the token, lemma, machine UPOS, story, genre, context, audit
  features, and concise labeling guidance.
- Store human review data separately from the generated sample.
- Support `NOUN`, `PROPN`, and `OTHER`, plus explicit unresolved or blocked
  dispositions.
- Preserve all reviewed examples, including ambiguous and defective examples,
  for later inspection and adjudication.
- Reuse the existing deterministic precision/recall and genre-slice scoring.

## Required Changes

1. Define a small experiment-local audit record or ledger keyed by the existing
   stable `token_key`.
2. Implement deterministic `status` and `next` operations that show progress
   and select the next unresolved row without changing sample order.
3. Implement decision and issue recording with validation for allowed labels,
   issue codes, notes, and reviewer metadata.
4. Distinguish a completed label from an uncertain or blocked review; do not
   silently count unresolved rows as negative labels.
5. Validate that every sample row is represented exactly once, all keys match
   the generated packet, and every row has an explicit disposition before
   scoring.
6. Add tests for normal progression, resume behavior, malformed records,
   duplicate or stale token keys, unresolved rows, segmentation issues, and
   scoring handoff.
7. Update the experiment README with detailed reviewer instructions and the
   exact commands for starting, resuming, validating, and scoring an audit.

## Non-Goals

- Do not run the full corpus.
- Do not change token-detail-v2 or linguistics-lexicon-v1 schemas.
- Do not modify files under `corpora/`.
- Do not alter the preregistered POS thresholds or scoring formulas.
- Do not fabricate, infer, or auto-fill human labels.
- Do not produce noun/POS figures.
- Do not build a general-purpose annotation platform or collaborative review
  service.
- Do not silently repair segmentation or tokenization; record the issue for
  explicit follow-up.

## Acceptance Criteria

- A reviewer can start, pause, resume, and inspect progress without editing
  generated sample rows directly.
- Every audit row has a stable identity, visible context, an explicit review
  disposition, and preserved notes/issues.
- Invalid, duplicate, stale, incomplete, or silently skipped records are
  rejected before scoring.
- Segmentation and tokenization defects are represented as explicit issues and
  remain available for review.
- The existing scorer consumes the validated decisions without changing its
  registered thresholds or interpretation.
- Tests and documentation demonstrate the complete review-to-score workflow.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `python ../experiments/09_rich_linguistics_genre_sample/audit_pos.py --help`
- `cd .. && python -m unittest experiments/09_rich_linguistics_genre_sample/audit_pos_test.py`
- `git diff --exit-code -- ../corpora ../experiments/07_linguistics_corpora`

## Risk Notes

- A review helper can create false confidence if unresolved or defective rows
  are hidden; validation must require explicit dispositions.
- Segmentation defects may affect both token identity and POS judgments and
  should be reported separately from ordinary POS disagreement.
- The helper should remain experiment-local until repeated audit workflows
  demonstrate a need for a broader annotation framework.
