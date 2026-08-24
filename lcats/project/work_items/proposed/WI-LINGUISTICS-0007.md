---
resolution: null
blocked_reason: null
blocked: false
id: WI-LINGUISTICS-0007
title: Run and audit a 146-story rich linguistic pilot
type: evaluation
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
  - WI-LINGUISTICS-0005
  - WI-LINGUISTICS-0006
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_report
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - run_full_corpus
  - modify_sample_membership
  - promote_sidecars
  - make_paid_api_calls
acceptance:
  - A new numbered experiment deterministically reuses the 146-story experiment-05 manifest and writes v2 and lexical outputs only to an experiment-local mirror
  - A preregistered stratified human audit reports NOUN, PROPN, and combined noun-family precision, recall, confusion, and genre slices with adjudication guidance
  - The report measures completion, validation, runtime, peak memory where practical, bytes per story/token, lexical size, and projected full-corpus cost
  - The pilot applies the proposed combined noun-family 0.90 precision/recall gate and a preregistered severe-genre-failure rule, then records a clear quality recommendation
  - Results include separate explicit proceed/defer/no-go decisions for sample POS figures in WI-VISUALIZE-0093 and the full-corpus run in WI-LINGUISTICS-0008; no corpora/ files change
required_evidence:
  - test_output
  - validation_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - experiments/09_rich_linguistics_genre_sample/
  - experiments/09_rich_linguistics_genre_sample/results/experiment_report.json
  - experiments/09_rich_linguistics_genre_sample/results/pos_audit.json
  - experiments/09_rich_linguistics_genre_sample/results/linguistics_run_summary.json
---

# Work Item: WI-LINGUISTICS-0007

## Summary

Run a new rich linguistic experiment over the fixed 146-story genre sample,
audit noun-family POS quality, measure runtime/storage, and issue the explicit
go/no-go evidence required before a full-corpus run.

## Problem / Context

Experiment 06 proves the sample can be processed locally, but it did not retain
token detail. Before LCATS relies on POS filters or regenerates roughly 1,800
stories, it needs evidence that the chosen model handles historical literary
prose well enough and that rich artifacts have an acceptable operational cost.

### Duplication search

- In-repo: reuse experiment 05 membership and experiment 06 harness patterns;
  neither contains rich v2/lexical outputs or a human POS audit.
- Sibling repos: none identified.
- External libraries: evaluation utilities may help calculate metrics, but no
  external dataset substitutes for an audit of this exact LCATS sample.
- Recommendation: create a new experiment; do not overwrite experiment 06.

### Demand search

- Work items: no open match; resolved linguistics experiments establish the
  run/copy/report conventions.
- Proposals: the governing proposal requires the sample-first gate.
- Backlog: no matching entry.
- Recommendation: proceed after v2 and lexical delivery.

## Scope

- Preregistered 146-story experiment and immutable membership verification.
- Experiment-local v2 and lexical production with validation/reporting.
- Stratified human audit of `NOUN`, `PROPN`, and combined noun family.
- Runtime/storage/full-corpus projection and retention/go-no-go recommendation.

## Required Changes

1. Create the next available numbered experiment, copying the exact experiment
   05 selected story buckets and verifying IDs/hashes before processing.
2. Preregister backend/model, audit sampling, annotator instructions,
   adjudication, precision/recall formulas, combined 0.90 gate, and a concrete
   severe genre-slice failure rule before scoring.
3. Run v2 and lexical generation in the experiment mirror with resume support;
   validate every compact, v2, and lexical artifact and reconcile totals.
4. Audit examples stratified across all eight genres, authors, dialogue,
   contractions, archaic wording, noun/verb ambiguity, and proper names.
5. Report failures, confusion, overall/by-genre metrics, completion, elapsed
   time, memory where practical, artifact sizes, projection assumptions, and
   retained-output options.
6. Give `WI-VISUALIZE-0093` and `WI-LINGUISTICS-0008` separate explicit
   proceed/defer/no-go recommendations; a failed sample-figure gate must identify
   required remediation without authorizing figures from rejected data.

## Non-Goals

- Do not alter the 146-story sample membership or rerun genre classification.
- Do not process the full corpus.
- Do not make paid model calls.
- Do not write generated sidecars into `corpora/`.
- Do not silently tune the audit threshold after results are seen.

## Acceptance Criteria

- The experiment is rerunnable, resume-safe, and makes no corpus-tree changes.
- Every selected story is accounted for as success or documented failure.
- Human audit data and calculations are reviewable, with ambiguous cases
  retained rather than discarded.
- The report distinguishes `NOUN`, `PROPN`, and their union.
- Full-run and artifact-retention recommendations follow declared evidence.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `python ../experiments/09_rich_linguistics_genre_sample/run_rich_linguistics_sample.py --help`
- `git diff --exit-code -- ../corpora`

## Risk Notes

- Human audit effort can expand; preregister a bounded sample and adjudication
  procedure.
- Seven genres have 20 stories while adventure has six; report denominators and
  avoid implying a perfectly balanced eight-genre sample.
- Historical dialogue and proper names may cause genre-dependent errors that an
  aggregate score hides.

## Dependencies / Order

Starts only after v2 and lexical artifacts are implemented. Its separate gates
control the conditional full-corpus item and acceptance of POS-aware paper
figures; either gate may resolve as proceed, defer, or no-go.
