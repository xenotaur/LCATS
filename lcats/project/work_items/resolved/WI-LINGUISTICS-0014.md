---
resolution: Implemented and merged the WI-LINGUISTICS-0014 planning artifact in PR #461 (commit 7314eaa2); implementation remains a separate execution step.
blocked_reason: null
blocked: false
id: WI-LINGUISTICS-0014
title: Repair rich-linguistics POS tokenization and blocked-row handling
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
  - WS-COMPARATIVE-LEXICAL-VISUALIZATION
related_design:
  - lcats/project/design/proposals/proposed/comparative-lexical-visualization/00_proposal.md
depends_on:
  - WI-LINGUISTICS-0007
  - WI-LINGUISTICS-0013
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
  - run_experiment
  - create_report
  - write_docs
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - merge_pr
  - run_full_corpus
  - modify_sample_membership
  - overwrite_audit_packet
  - fabricate_human_labels
  - bypass_pos_quality_gate
  - produce_pos_figures
acceptance:
  - The rich-linguistics tokenization path identifies and reports fused punctuation, malformed boundaries, and multiword/clitic cases before POS scoring
  - Tokenization handling preserves exact source text, offsets, provenance, and stable artifact fingerprints
  - Regression fixtures cover representative failures including `and--`, `thirst'--_he`, `body'd`, `I'll`, and punctuation-fused forms
  - The original 192-row audit packet and ledger remain preserved as historical evidence; regenerated artifacts are versioned or separately identified
  - A regenerated pilot packet reports pre/post blocked counts and an explicit decision for any residual blocked rows
  - POS scoring and downstream noun figures remain gated until the revised audit satisfies an explicit reviewed policy
  - Tests, experiment validation, documentation, and `lrh validate` pass
required_evidence:
  - test_output
  - validation_output
  - manual_review
  - lrh_validate
artifacts_expected:
  - lcats/src/lcats/analysis/event_role_world/nlp_backend.py
  - lcats/src/lcats/analysis/linguistics/sidecar.py
  - experiments/09_rich_linguistics_genre_sample/
  - experiments/09_rich_linguistics_genre_sample/results/
  - lcats/project/design/proposals/proposed/comparative-lexical-visualization/00_proposal.md
---

# Work Item: WI-LINGUISTICS-0014

## Summary

Repair the rich-linguistics tokenization path exposed by the 56 blocked rows in
the 192-row POS audit, preserve the original audit evidence, and regenerate a
provenance-linked pilot packet suitable for a reviewed POS-quality decision.

## Problem / Context

The current pilot has 56 blocked rows, or 29.2% of the sample, with malformed
or fused token forms. The existing pipeline copies backend token text and UPOS
directly into the audit packet, while validation checks structural integrity
and source spans but not whether a token is suitable for one POS judgment. The
comparative visualization workstream requires a clear pilot quality
recommendation before POS figures or conditional full-corpus work proceed.

Existing backend abstraction and token-detail code should be extended rather
than replaced: `lcats/src/lcats/analysis/event_role_world/nlp_backend.py`,
`lcats/src/lcats/analysis/linguistics/sidecar.py`, and
`experiments/09_rich_linguistics_genre_sample/`.

### Duplication search

- In-repo: Related backend and token-detail implementations already exist; no existing work item repairs this specific POS-tokenization failure.
- Sibling repos: None identified.
- External libraries: Universal Dependencies documents multiword-token handling for contractions and clitics; it informs the design but does not solve LCATS artifact and audit semantics.
- Recommendation: Proceed by extending the existing LCATS pipeline.

### Demand search

- Work items: `WI-LINGUISTICS-0007` established the pilot gate; `WI-LINGUISTICS-0008` and `WI-VISUALIZE-0093` require a reviewed POS-quality outcome.
- Proposals: The comparative lexical visualization proposal requires auditable POS evidence and evidence-backed defer/no-go outcomes.
- Backlog: No duplicate tokenization-repair item found.
- Recommendation: Link this item to the existing pilot and downstream gate items; do not close them automatically.

## Scope

- Diagnose the backend and token-detail boundary behavior producing malformed audit tokens.
- Define handling for contractions, clitics, punctuation-fused forms, and true multiword tokens.
- Preserve the original audit packet and ledger.
- Regenerate the sample only with explicit provenance and fingerprinting.
- Record the effect of residual blocked rows on scoring and downstream authorization.

## Required Changes

1. Trace representative blocked forms from source text through backend output, token-detail-v2, audit packet generation, and scoring.
2. Add tokenization-quality diagnostics and regression fixtures.
3. Extend the representation or adapter where necessary to distinguish surface tokens from syntactic words without fabricating labels.
4. Add a versioned regeneration path for the pilot packet and an evidence report comparing old and revised blocked counts.
5. Define and document the reviewed policy for residual blocked rows.
6. Keep POS figures and full-corpus rich analysis gated on the revised evidence.

## Non-Goals

- Do not run the full corpus.
- Do not modify the fixed 146-story sample membership.
- Do not overwrite the existing audit packet or ledger.
- Do not fabricate labels for malformed tokens.
- Do not produce noun/POS figures under the failed current audit.
- Do not redesign the entire visualization workstream.

## Acceptance Criteria

- The malformed-token classes are reproducibly diagnosed.
- The revised pipeline preserves source identity, offsets, and provenance.
- The original audit remains recoverable and distinguishable from regenerated evidence.
- The revised pilot provides blocked-rate, coverage, and scoring evidence.
- A human-reviewed decision states whether residual blocked rows permit scoring, require further repair, or produce a no-go.
- Downstream POS work remains deferred unless explicitly authorized by that decision.

## Validation

- (from `lcats/`): `scripts/version tools`
- (from `lcats/`): `scripts/format --check --diff`
- (from `lcats/`): `scripts/lint`
- (from `lcats/`): `scripts/test`
- Focused audit and linguistics tests
- Regenerated-packet validation and fingerprint checks
- (from `lcats/`): `lrh validate`
- (from repository root): `git diff --exit-code -- corpora experiments/07_linguistics_corpora`

## Risk Notes

- Changing token boundaries may invalidate existing row fingerprints and require selective or complete re-audit.
- Excluding blocked rows could bias metrics because the audit deliberately samples difficult token and POS cases.
- A surface-token/syntactic-word model may require schema evolution; that should be explicit rather than hidden in post-processing.
- A residual blocked rate must be treated as evidence, not silently folded into “reviewed”.
