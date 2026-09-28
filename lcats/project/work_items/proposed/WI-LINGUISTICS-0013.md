---
resolution: null
blocked_reason: null
blocked: false
id: WI-LINGUISTICS-0013
title: Improve interactive POS audit prompts and record display
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
  - WI-LINGUISTICS-0012
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
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
  - Return retains an existing disposition and label; Return on a new record reprompts because there is no value to retain
  - Escape pauses the audit, while Q remains a supported textual quit command
  - Notes and issue-code prompts display their saved values and preserve or clear them according to the documented Enter/CLEAR rules
  - "Audit records retain the `AUDIT RECORD n/total: token` header and display aligned fields with consistently positioned colons"
  - Long field values wrap with readable continuation indentation
  - Focused tests and README documentation cover the prompt and display behavior without changing packet or ledger schemas
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

# Work Item: WI-LINGUISTICS-0013

## Summary

Improve the experiment-local interactive POS audit experience for revisiting
and correcting records. Prompts should make saved values visible at the point
of entry, Return should retain existing values safely, and Escape should
provide an immediate pause path. The displayed audit record should remain
headed by `AUDIT RECORD n/total: token` while using aligned, wrapped fields
for easier scanning.

## Problem / Context

The existing implementation supports revisit metadata retention in the notes
and issue-code helpers, but the label prompt currently treats blank input as
pause/quit. Saved values are displayed above the prompts, requiring reviewers
to scan backward. Record fields are printed through separate unaligned lines
in `experiments/09_rich_linguistics_genre_sample/audit_pos.py`.

Prior-art search found the related resolved items `WI-LINGUISTICS-0011` and
`WI-LINGUISTICS-0012`, but neither covers this prompt/display refinement. No
duplicate active work item was found. The present request supplies the demand
for this focused follow-up.

## Scope

- Add safe Return-to-retain behavior for revisited records.
- Reprompt when Return is used where no prior label/disposition exists.
- Add Escape as an interactive pause command while preserving Q.
- Show saved values directly in each relevant prompt.
- Render an aligned, wrapped audit-record summary while retaining the
  requested header.
- Add focused tests and update the experiment README.

## Required Changes

- Update the interactive choice and field prompts to distinguish retaining a
  saved value from pausing the session.
- Add a small terminal-formatting helper for aligned labels, saved-value
  hints, and wrapped long values.
- Add focused interaction and rendering tests and document the resulting
  behavior in the experiment README.

## Non-Goals

- No changes to the audit packet, ledger schema, scoring rules, or sample
  membership.
- No full-corpus run.
- No general-purpose annotation UI or terminal framework.

## Acceptance Criteria

1. Return retains an existing disposition and label; Return on a new record
   reprompts because there is no value to retain.
2. Escape pauses the audit, while Q remains a supported textual quit command.
3. Notes and issue-code prompts display saved values and preserve or clear them
   according to the documented Enter/CLEAR rules.
4. Audit records retain the `AUDIT RECORD n/total: token` header and display
   aligned fields with readable wrapping for long values.
5. Focused tests, README documentation, and `lrh validate` pass without packet
   or ledger-schema changes.

## Validation

- Run the focused audit tests.
- Run formatting and lint checks applicable to the changed files.
- Run `git diff --check`.
- Run `lrh validate`.

## Risk Notes

The main risk is ambiguity between “retain” and “quit” on blank input. The
implementation will distinguish revisits from fresh records and make the
behavior visible in the prompt text. Long values will wrap rather than
truncate.
