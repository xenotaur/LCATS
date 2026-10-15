---
resolution: null
blocked_reason: null
blocked: false
id: WI-LINGUISTICS-0015
title: Re-audit repaired pilot and decide POS quality gate
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
  - WI-LINGUISTICS-0014
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
  - run_experiment
  - create_report
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - merge_pr
  - run_full_corpus
  - promote_sidecars
  - fabricate_pos_labels
  - overwrite_historical_audit
acceptance:
  - The repaired pilot packet is regenerated or materialized with verified provenance and fingerprints.
  - The repaired packet receives a complete human POS audit using the existing audit helper.
  - The resulting ledger validates and produces the authoritative pos_audit_scored.json.
  - The report records blocked, uncertain, reviewed, overall, and genre-slice metrics.
  - A human-reviewed decision states whether POS-dependent work is authorized, requires further repair, or is deferred/no-go.
  - Historical pre-repair packet and ledger remain recoverable and unchanged.
required_evidence:
  - test_output
  - validation_output
  - manual_review
  - lrh_validate
artifacts_expected:
  - experiments/09_rich_linguistics_genre_sample/results/pos_audit_scored.json
  - experiments/09_rich_linguistics_genre_sample/results/repaired_pos_audit_report.json
  - provenance and fingerprint evidence for the repaired packet
---

# Work Item: WI-LINGUISTICS-0015

## Summary

Re-audit the repaired 146-story rich-linguistics pilot and produce the authoritative scored POS-quality decision required before POS figures or full-corpus rich analysis can proceed.

## Problem / Context

WI-LINGUISTICS-0014 reduced malformed audit rows from 56 to 29, but the repaired evidence remains unscored and explicitly keeps POS figures gated. Existing audit labels cannot be assumed to transfer because token-boundary repair can change row fingerprints. This item supplies the missing human-reviewed evidence step between tokenization repair and downstream gate decisions.

### Duplication search

- In-repo: Related repair work exists in `WI-LINGUISTICS-0014`, but no existing item performs the repaired-packet re-audit and gate decision.
- Sibling repos: None identified.
- External libraries: None replace the repository-specific audit ledger, fingerprints, and gate semantics.
- Recommendation: Proceed as a focused follow-up to `WI-LINGUISTICS-0014`.

### Demand search

- Work items: `WI-LINGUISTICS-0008` and `WI-VISUALIZE-0093` require reviewed pilot-quality evidence.
- Workstream: `WS-COMPARATIVE-LEXICAL-VISUALIZATION` requires a repaired, reviewed pilot before POS-dependent work proceeds.
- Backlog: No separate existing item covers this re-audit.
- Recommendation: Add this item to the comparative visualization workstream and execute it before `WI-LINGUISTICS-0008` or `WI-VISUALIZE-0093`.

## Scope

- Reuse the repaired-v1 pilot output and its provenance.
- Reconcile repaired packet rows with the audit helper and fingerprints.
- Complete the human review of the repaired audit sample.
- Score the resulting ledger and record the POS-quality decision.

## Required Changes

1. Materialize or regenerate the repaired audit packet using the documented repaired-tokenization command.
2. Verify packet identity, row fingerprints, source spans, provenance, and audit sample membership.
3. Run the existing interactive audit helper against the repaired packet, preserving the historical audit separately.
4. Validate and score the complete repaired ledger.
5. Produce a report comparing pre-repair and post-repair blocked rows, audit coverage, overall metrics, and genre-slice metrics.
6. Record an explicit decision: authorize POS-dependent downstream work, require another repair, or defer/no-go with the condition for reconsideration.

## Non-Goals

- Do not run the full corpus.
- Do not generate noun/POS figures.
- Do not overwrite the historical audit packet or ledger.
- Do not fabricate labels for malformed or ambiguous rows.
- Do not silently transfer labels across changed fingerprints.
- Do not change the canonical token-detail schema.
- Do not promote generated artifacts into `corpora/`.

## Acceptance Criteria

- The repaired packet is reproducible and provenance-linked.
- The audit helper can identify every repaired audit row deterministically.
- The complete repaired ledger validates without stale or mismatched fingerprints.
- `pos_audit_scored.json` contains the authoritative scoring and gate metrics.
- The report explicitly accounts for all blocked and uncertain rows.
- A human-reviewed decision authorizes, further gates, or defers downstream POS work.
- The historical pre-repair evidence remains unchanged and recoverable.
- `lrh validate` reports zero errors introduced by this item.

## Validation

- `python experiments/09_rich_linguistics_genre_sample/run_rich_linguistics_sample.py --tokenization-mode repaired-v1 --output-dir <repaired-output> --overwrite`
- `python experiments/09_rich_linguistics_genre_sample/audit_pos.py status`
- `python experiments/09_rich_linguistics_genre_sample/audit_pos.py validate`
- `python experiments/09_rich_linguistics_genre_sample/audit_pos.py score`
- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `git diff --exit-code -- corpora experiments/07_linguistics_corpora`

## Risk Notes

- Repaired token boundaries may invalidate existing row fingerprints and require a fresh audit.
- Remaining blocked rows may indicate defects that require another implementation cycle.
- Excluding blocked rows could bias the POS-quality result, so they must remain explicit in the report.
- The full-corpus decision and POS figures must remain separate decisions even after this audit.
