---
resolution: null
blocked_reason: null
blocked: false
id: WI-LINGUISTICS-0012
title: Add rewind and goto navigation to the interactive POS audit
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
  - WI-LINGUISTICS-0011
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
  - create_pr
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - merge_pr
  - run_full_corpus
  - modify_sample_membership
  - overwrite_audit_packet
  - fabricate_human_labels
  - build_general_annotation_platform
acceptance:
  - "`R` returns to the immediately previous record visited in the current audit session"
  - "`G` jumps to a record by 1-based audit number or token key"
  - Revisiting a record displays its existing disposition, label, notes, and issue codes
  - Navigation does not mutate the ledger until the reviewer records a new decision
  - Enter retains existing metadata and an explicit input can clear notes or issue codes
  - Tests cover rewind, goto, overwrite, first-record navigation, and ledger compatibility
  - README documents the navigation and editing behavior
required_evidence:
  - test_output
  - validation_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - experiments/09_rich_linguistics_genre_sample/audit_pos.py
  - experiments/09_rich_linguistics_genre_sample/audit_pos_test.py
  - experiments/09_rich_linguistics_genre_sample/README.md
---

# Work Item: WI-LINGUISTICS-0012

## Summary

Extend the experiment-local interactive POS audit with session-local rewind and direct record navigation. Revisited records must show their current saved values and remain unchanged until the reviewer explicitly records an update.

## Problem / Context

The existing `audit` command supports linear review and resumable ledger updates, but it cannot return to a recently reviewed record or jump directly to a known problematic record. This makes correction of mistakes and investigation of context or segmentation problems unnecessarily cumbersome during the 192-row audit. The work builds directly on resolved `WI-LINGUISTICS-0011` and must preserve the immutable packet, editable ledger, validation, scoring, and non-interactive commands.

### Duplication search

- In-repo: Related implementation at `experiments/09_rich_linguistics_genre_sample/audit_pos.py`; no existing rewind or goto capability found.
- Sibling repos: None identified.
- External libraries: None identified; the feature is specific to the experiment-local interactive workflow.
- Recommendation: Proceed by extending the existing helper.

### Demand search

- Work items: `WI-LINGUISTICS-0011` — “Add an interactive POS audit session command” is the predecessor, not a duplicate.
- Proposals: The comparative lexical visualization proposal requires a completed auditable POS quality gate but does not specify navigation controls.
- Backlog: No matching navigation entry found.
- Recommendation: No action; link this item to `WI-LINGUISTICS-0011`.

## Scope

- Add session-local `[R]ewind` navigation.
- Add `[G]oto` navigation by audit ordinal or stable token key.
- Prepopulate saved values when revisiting records.
- Document and test safe overwrite and metadata-clearing behavior.

## Required Changes

1. Extend the interactive prompt in `audit_pos.py` with `R` and `G` navigation commands.
2. Maintain session-local visit history for rewind without changing persisted ledger state.
3. Resolve goto targets deterministically by 1-based audit number or exact `token_key`.
4. Display existing disposition, label, notes, and issue codes when revisiting a record.
5. Ensure navigation alone never writes ledger changes.
6. Define explicit retain and clear behavior for revisited notes and issue codes.
7. Add focused tests and update the experiment README.

## Non-Goals

- Do not change the audit packet or sample membership.
- Do not change the ledger schema unless strictly required for backward-compatible behavior.
- Do not fabricate or infer human labels.
- Do not run the full corpus.
- Do not build a general annotation platform.
- Do not alter existing non-interactive command behavior.

## Acceptance Criteria

- `R` returns to the prior record visited in the current session.
- `G` accepts a valid ordinal and exact token key and reports invalid targets without mutating state.
- Revisited records display their saved values.
- A reviewer can overwrite a prior decision only by explicitly recording a new one.
- Existing metadata is retained by default, with an explicit clearing mechanism.
- First-record rewind and empty-history cases are safe and understandable.
- Existing tests and commands remain compatible.
- Documentation explains the new controls.
- `lrh validate` reports zero errors.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `python -m unittest experiments/09_rich_linguistics_genre_sample/audit_pos_test.py`
- `lrh validate`
- `git diff --check`

## Risk Notes

- Rewind must not silently erase or roll back persisted audit decisions.
- Goto by ordinal must use a stable, clearly documented ordering.
- Revisiting records must not accidentally clear notes or issue codes when the reviewer only navigates.
- The implementation must remain compatible with ledgers already created by the current audit.
