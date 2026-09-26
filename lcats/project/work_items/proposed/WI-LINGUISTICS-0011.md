---
resolution: null
blocked_reason: null
blocked: false
id: WI-LINGUISTICS-0011
title: Add an interactive POS audit session command
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
  - WI-LINGUISTICS-0010
blocked_by: []
expected_actions:
  - create_file
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
acceptance:
  - "`audit_pos.py audit` starts or resumes an audit and persists the reviewer name"
  - The interactive session presents readable row context and deterministic guidance
  - Reviewers can record NOUN, PROPN, OTHER, uncertain, or blocked decisions with notes and issue codes
  - The session pauses safely and supports explicitly confirmed restart from scratch
  - Completion automatically validates and scores the ledger
  - Existing non-interactive commands remain compatible
  - Documentation and focused tests cover the interactive workflow
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

# Work Item: WI-LINGUISTICS-0011

## Summary

Add a human-readable, resumable interactive session command for the experiment
09 POS audit, while preserving the existing ledger, validation, scoring, and
non-interactive command behavior.

## Problem / Context

The existing helper exposes deterministic `status`, `next`, and `record`
commands, but reviewing 192 rows requires repeatedly reading JSON output and
constructing command-line flags. A guided session reduces transcription errors
and makes the audit practical to resume after interruption while retaining the
separate immutable packet and editable ledger established by
`WI-LINGUISTICS-0010`.

### Duplication search

- In-repo: `WI-LINGUISTICS-0010` provides the ledger, validation, and scoring
  primitives, but no interactive audit session.
- Sibling repos: none identified.
- External libraries: none needed; standard input and the existing helper are
  sufficient.
- Recommendation: proceed as a thin extension of the experiment-local helper.

### Demand search

- Work items: `WI-LINGUISTICS-0008` requires a completed scored audit, and
  `WI-LINGUISTICS-0010` provides the underlying helper.
- Proposals: the comparative lexical visualization proposal requires an
  auditable POS quality gate before conditional full-corpus work.
- Backlog: no separate interactive audit entry identified.
- Recommendation: proceed; this improves execution of the existing audit gate.

## Scope

- Add the experiment-local `audit` subcommand.
- Preserve and resume the existing ledger and current 192-row audit state.
- Reuse the existing validation, recording, and scoring logic.
- Document the guided workflow and test it without changing the generated
  packet.

## Required Changes

1. Add `audit` argument parsing and an interactive session loop to
   `experiments/09_rich_linguistics_genre_sample/audit_pos.py`.
2. Persist and recall the reviewer name, and require explicit confirmation
   before restarting an existing audit from scratch.
3. Display each row's stable identity, context, machine label, and deterministic
   guidance; collect the label, disposition, notes, and issue codes through
   readable prompts.
4. Reuse the existing ledger validation and scoring path, automatically
   validating and scoring after the last unresolved row.
5. Update the experiment README and add focused tests for completion, resume,
   pause, reviewer persistence, and compatibility with existing commands.

## Non-Goals

- Do not change the generated audit packet or sample membership.
- Do not modify the canonical linguistic schemas or build a general annotation
  platform.
- Do not fabricate labels or run the full corpus.
- Do not produce POS figures or make the full-corpus go/no-go decision.

## Acceptance Criteria

- `audit_pos.py audit` starts or resumes an audit and persists the reviewer
  name.
- The interactive session presents readable row context and deterministic
  guidance.
- Reviewers can record `NOUN`, `PROPN`, `OTHER`, `uncertain`, or `blocked`
  decisions with notes and issue codes.
- The session pauses safely and supports an explicitly confirmed restart from
  scratch.
- Completion automatically validates and scores the ledger.
- Existing non-interactive commands remain compatible.
- Documentation and focused tests cover the interactive workflow.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `python -m unittest experiments/09_rich_linguistics_genre_sample/audit_pos_test.py`
- `lrh validate`
- `git diff --check`

## Risk Notes

- A restart prompt must not make it easy to discard the existing audit; use an
  explicit confirmation token.
- The interactive path must use the same validation and scoring functions as
  the existing commands so it cannot silently bypass ledger safeguards.
- Reviewer metadata must remain compatible with ledgers created before this
  command existed.
