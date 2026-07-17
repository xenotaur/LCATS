---
resolution: null
blocked_reason: null
blocked: false
id: WI-RELEASE-0021
title: Document a manual corpora-release runbook for independent verification
type: deliverable
status: proposed
priority: high
owner: unassigned
related_focus:
  - FOCUS-WORLDCON-2026
related_workstreams:
  - WS-SPECIALS-CLEANUP
related_design:
  - docs/reference/corpus-promotion.md
  - project/workstreams/proposed/WS-SPECIALS-CLEANUP.md
depends_on:
  - WI-PROMOTE-0020
forbidden_actions:
  - execute_release_checklist
  - modify_data_or_corpora_contents
  - force_push
acceptance:
  - The runbook covers regenerate -> survey -> inspect -> promote as discrete, copy-pasteable CLI steps requiring no agent or Claude involvement
  - Each step states what a clean result looks like and what a problem result looks like, so a human with no LCATS-internals knowledge can tell pass from fail
  - The runbook is a superset of docs/reference/corpus-promotion.md, linking to it rather than duplicating its content
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - docs/reference/prepare-corpora-release.md
---

# Work Item: WI-RELEASE-0021

## Summary
Write a plain-language runbook a human can execute independently, with no
agent involvement, to regenerate `data/`, verify it's clean, and promote it
to `corpora/` — the first real (not simulated) end-to-end test of the
WS-SPECIALS-CLEANUP pipeline.

## Problem / Context
Every verification of this pipeline so far has been either automated-agent-run
or, per EV-0002's own stated method, a *simulated* regeneration (the real
pipeline applied in-memory, not a literal `lcats gather`). That's real
evidence, but it's evidence produced by the same agent that wrote the code —
a known-incomplete verification pattern. An independently-executed, documented
runbook is a different and stronger kind of check, and it's also the actual
onboarding doc for any human maintaining this package without Claude.

## Scope
- Cover the full sequence: environment check, regenerate, survey, inspect
  findings, dry-run promote, real promote (clearly marked as the
  release-committing step).
- Every command must be copy-pasteable as written, with no placeholders
  requiring LCATS-internals knowledge to fill in.
- State expected output for both the clean and dirty cases at each step.

## Required Changes
1. Create `docs/reference/prepare-corpora-release.md` with these sections:
   - Pre-flight (conda env / `scripts/develop`, per
     `project_lcats_python_environment` conventions).
   - Regenerate: `lcats gather <collection>` per collection (or full corpus),
     noting this re-downloads from Project Gutenberg and is network-dependent.
   - Verify: `lcats survey --mode specials data/ --no-progress`, with the
     expected-clean output shown and a troubleshooting pointer if findings
     remain (link to WI-RESIDUAL-0019's rule/override/allowlist disposition
     method).
   - Inspect (diagnostic): `lcats repair-specials <file> --format jsonl` for
     any flagged file, to see what a residual finding looks like.
   - Preview: `lcats promote --dry-run`, reading its report.
   - Promote (the actual release step): the one-time
     `git rm -r corpora/ohenry corpora/wilde` historical cleanup from
     `docs/reference/corpus-promotion.md`, then `lcats promote` for real,
     called out as the step that changes tracked files.
2. Link to `docs/reference/corpus-promotion.md` for the promote command's
   full reference rather than repeating it.

## Non-Goals
- Do not execute the release checklist as part of this work item — that is
  the maintainer's own independent, manual verification step (the entire
  point of this WI).
- Do not perform the actual real gather/promote during implementation.
- Do not create the follow-up evidence record for the manual run's
  outcome — that happens after the maintainer reports results, as its own
  activity.

## Acceptance Criteria
- A human unfamiliar with the codebase's internals could follow the doc
  top-to-bottom using only a terminal.
- Every command is copy-pasteable; no step requires guessing a path or flag.
- `lrh validate` reports 0 errors.

## Validation
- `lrh validate`

## Risk Notes
- The regenerate step is network-dependent (Project Gutenberg) and may be
  slow; the doc should say so up front rather than let it be a surprise.
- The real-promote step mutates tracked files in `corpora/`; the doc must
  make unmistakably clear which steps are read-only/dry-run and which one
  isn't.
