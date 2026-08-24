---
resolution: null
blocked_reason: null
blocked: false
id: WI-LINGUISTICS-0008
title: Gate and conditionally run full-corpus rich linguistics
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
  - WI-LINGUISTICS-0007
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
  - run_before_gate_review
  - make_paid_api_calls
  - promote_sidecars
  - overwrite_experiment_07
acceptance:
  - The item records an explicit human-reviewed decision against pilot quality, validation, runtime, storage, retention, and research-need gates before any full run
  - If gates pass, a new numbered experiment runs v2 and lexical generation over the current corpus in an experiment-local/output-root layout with resume, full validation, timing, storage, and provenance reports
  - If any gate fails or need is insufficient, the item records an evidence-backed no-go/defer result and required follow-up without launching the full run
  - The selected retention policy is applied consistently and the report identifies which artifacts are checked in, archived, exported, or reproducibly omitted
  - No generated sidecars are written into corpora/, experiment 07 is unchanged, and all validation/tests pass
required_evidence:
  - test_output
  - validation_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - experiments/10_rich_linguistics_corpora/
  - experiments/10_rich_linguistics_corpora/results/experiment_report.json
  - experiments/10_rich_linguistics_corpora/results/linguistics_run_summary.json
  - experiments/10_rich_linguistics_corpora/results/artifact_retention.json
---

# Work Item: WI-LINGUISTICS-0008

## Summary

Apply the 146-story pilot gates and either run a new full-corpus rich
linguistic experiment with controlled retention or record a reviewable no-go/
defer decision without launching the run.

## Problem / Context

The compact experiment 07 run processed 1,867 non-empty stories in roughly 66
minutes, but rich token output can have a materially different storage and
validation cost. Full regeneration is useful only if the POS audit is adequate,
all artifacts validate, the projected cost is acceptable, retention is agreed,
and corpus-wide data is needed for planned figures. This item makes the gate an
explicit deliverable rather than an automatic consequence of finishing the
pilot.

### Duplication search

- In-repo: experiment 07 is the compact predecessor and must remain unchanged;
  no rich full-corpus experiment or conditional gate exists.
- Sibling repos: none identified.
- External libraries: no external service replaces this local LCATS run and
  retention decision.
- Recommendation: conditionally create a new experiment after review.

### Demand search

- Work items: resolved `WI-LINGUISTICS-0004` delivered the compact full-corpus
  run; it does not request rich regeneration.
- Proposals: the governing proposal makes this conditional rather than a paper
  prerequisite.
- Backlog: no matching entry.
- Recommendation: proceed as an evaluation with valid go and no-go outcomes.

## Scope

- Review and record pilot gates before execution.
- If approved, run a new full-corpus v2/lexical experiment safely.
- Validate, report, and apply the selected bulk-artifact retention policy.
- If not approved, record an evidence-backed no-go/defer resolution.

## Required Changes

1. Summarize pilot evidence and obtain an explicit reviewed decision for POS
   quality, genre slices, validation, runtime, storage, retention, and need.
2. On go only, create a new numbered experiment based on experiment 07's
   copied-bucket/output-root and resume conventions; fingerprint the selected
   corpus and exact backend/model/config.
3. Generate compact, v2, and lexical artifacts locally; account for every story
   and validate source identity, schemas, spans, dependencies, counts, and
   lexical regeneration.
4. Report elapsed time, failures, throughput, artifact counts/sizes, version
   provenance, and comparison with pilot projections.
5. Apply and document the selected check-in/archive/columnar/derived-only
   retention policy without changing `corpora/`.
6. On no-go/defer, create the decision/report artifacts only and state the
   condition required to reconsider.

## Non-Goals

- Do not start the full run before explicit gate review.
- Do not overwrite experiment 07.
- Do not make paid API calls.
- Do not promote sidecars into `corpora/`.
- Do not block sample-based noun figures when a full run is unnecessary.

## Acceptance Criteria

- The recorded gate decision precedes any full-run outputs.
- Both go and no-go paths yield a complete, reviewable resolution.
- A go run accounts for and validates every selected story or documented
  failure and can resume safely.
- Retained artifacts match the declared storage policy and provenance.
- `corpora/` and experiment 07 remain unchanged.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `git diff --exit-code -- ../corpora ../experiments/07_linguistics_corpora`

## Risk Notes

- Bulk token detail may be inappropriate for Git; select retention from measured
  evidence rather than convenience.
- Corpus membership may change between pilot and run; fingerprint the universe.
- A conditional item must not let “planned” be mistaken for authorization to
  execute; record a separate explicit gate review.
