---
id: WI-DOCS-0015
title: Add a quickstart tutorial
type: deliverable
status: resolved
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams:
  - WS-DOCS
related_design: []
depends_on:
  - WI-DOCS-0013
  - WI-DOCS-0014
blocked_by: []
blocked: false
blocked_reason: null
resolution: "Implemented and merged in PR #136 (commit 0ba5e85), including two review-response rounds (5 comments total) and two confirm-fixes passes that independently verified all fixes before merge."
expected_actions:
  - create_file
  - edit_file
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - rewrite_unrelated_docs
  - publish_untested_commands
acceptance:
  - "docs/tutorials/quickstart.md exists and takes a new contributor from environment setup through a first successful lcats survey or lcats assess --dry-run run"
  - "every command in the tutorial was actually run end-to-end in a clean environment and verified to succeed before landing"
  - "docs/index.md's Tutorials section links the new page instead of stating tutorials are not scaffolded"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - lcats/docs/tutorials/quickstart.md
  - lcats/docs/index.md
---

# Work Item: WI-DOCS-0015

## Summary
Add `docs/tutorials/quickstart.md`, LCATS's first Tutorial-quadrant document: a reproducible,
step-by-step walkthrough from environment setup to a first working command, closing the last
empty Diataxis quadrant identified by the 2026-07-07 docs audit.

## Problem / Context
`docs/index.md` currently states "Tutorials are not scaffolded in this phase" — accurate as of
Phase 1, but a real gap for new contributors. The audit (Phase 4) recommends reusing content
already proven correct in `lcats/README.md` and `docs/secrets-setup.md` rather than writing new,
unverified instructions. This item depends on `WI-DOCS-0013` (accurate README) and `WI-DOCS-0014`
(CLI/LLM-backend reference docs to link into, and the finished `docs/how-to/run-assess.md`) so the
tutorial can point to settled, corrected material instead of documenting soon-to-change text.

## Scope
- One tutorial: environment setup through a first successful command with an interpretable result.
- Reuse existing verified content (`lcats/README.md`, `docs/secrets-setup.md`) rather than
  authoring new setup instructions from scratch.
- Do not attempt full CLI coverage — that's what `docs/reference/cli-commands.md` is for.

## Required Changes
1. Create `lcats/docs/tutorials/quickstart.md` covering, in order: cloning the repo, `cd LCATS/lcats`,
   `scripts/clean && scripts/build && scripts/develop`, `lcats info` to verify the install, then a
   first `lcats survey` (no API key required) as the primary path, with `lcats assess --dry-run`
   (also no API key required) offered as an alternative or follow-on step. Link to
   `docs/secrets-setup.md` for readers who want to continue to a live `lcats assess` call.
2. Update `docs/index.md`'s "Tutorials" section to link the new page instead of stating tutorials
   are not scaffolded.

## Non-Goals
- Do not cover the full CLI surface in the tutorial — link to `docs/reference/cli-commands.md`
  (`WI-DOCS-0014`) instead.
- Do not add a second tutorial in this item — one complete quickstart is the Phase 4 scope.
- Do not require a live API call as the tutorial's primary path — `survey`/`assess --dry-run` let
  a new contributor succeed without provisioning keys first; live `assess` is an optional next step.

## Acceptance Criteria
- `docs/tutorials/quickstart.md` exists and reaches a concrete, working outcome.
- Every command in the tutorial was run end-to-end in a clean environment and confirmed to work
  exactly as written before this item is considered done.
- `docs/index.md`'s Tutorials section links the new page.
- `lrh validate` reports 0 errors.

## Validation
- `scripts/version tools`
- `lrh validate`
- Manually execute every command in `quickstart.md` in order, in a clean checkout, and confirm
  each one produces the output described

## Dependencies / Order
Depends on `WI-DOCS-0013` and `WI-DOCS-0014` — the tutorial should link to (not duplicate) the
corrected README and the Phase 3 reference docs, and should not be written against text that's
about to change underneath it.

## Risk Notes
- Tutorials are the quadrant most likely to silently rot (a command that worked at write-time
  breaks later without anyone noticing, since it's read start-to-finish rather than scanned like
  reference). No automated check enforces this; re-verification is a manual, recurring cost future
  contributors should be aware of.
