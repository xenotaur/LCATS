---
resolution: Implemented and merged in PR #127 (commit c2d1137)
blocked_reason: null
blocked: false
id: WI-RELEASE-0021
title: Document a manual corpora-release runbook for independent verification
type: deliverable
status: resolved
priority: high
owner: unassigned
related_focus:
  - FOCUS-WORLDCON-2026
related_workstreams:
  - WS-SPECIALS-CLEANUP
related_design:
  - lcats/docs/reference/corpus-promotion.md
  - project/workstreams/proposed/WS-SPECIALS-CLEANUP.md
depends_on:
  - WI-PROMOTE-0020
forbidden_actions:
  - execute_release_checklist
  - modify_data_or_corpora_contents
  - force_push
acceptance:
  - The runbook covers clear/regenerate -> survey -> inspect -> promote as discrete, copy-pasteable CLI steps requiring no agent or Claude involvement
  - Each step states what a clean result looks like and what a problem result looks like, so a human with no LCATS-internals knowledge can tell pass from fail
  - Each step is unambiguous about which working directory it runs from, so no step requires the reader to infer a cd
  - The runbook is a superset of lcats/docs/reference/corpus-promotion.md, linking to it rather than duplicating its content
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - lcats/docs/reference/prepare-corpora-release.md
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
- Cover the full sequence: environment check, clear stale local state,
  regenerate, survey, inspect findings, dry-run promote, real promote
  (clearly marked as the release-committing step).
- Every command must be copy-pasteable as written, with no placeholders
  requiring LCATS-internals knowledge to fill in.
- Every step must be unambiguous about which working directory it runs
  from (repo root vs. the `lcats/` package directory) — no step should
  require the reader to infer a `cd`.
- State expected output for both the clean and dirty cases at each step.

## Required Changes
1. Create `lcats/docs/reference/prepare-corpora-release.md` with these
   sections, each explicit about its working directory (repo root vs.
   `lcats/`):
   - Pre-flight (conda env / `scripts/develop`, per `lcats/scripts/README.md`).
   - Clear stale state (from `lcats/`): `lcats gather` skips any file that
     already exists (`DataGatherer.download` returns early —
     `lcats/gatherers/downloaders.py:230,260-261`; the resource cache does
     the same — `lcats/gatherers/downloaders.py:98-102`) and there is no
     `--force` flag on the CLI, so a stale `data/` makes the "regenerate"
     step a no-op that surveys old files while claiming a fresh run. The
     runbook must have the reader remove the relevant `data/<gatherer>`
     directories (and note `data/` is a regenerable cache, unlike
     `corpora/`) before gathering.
   - Regenerate (from `lcats/`): `lcats gather [gatherer ...]` — the
     command takes optional *gatherer* names (defaulting to every
     gatherer when none are given), not a `<collection>` placeholder; list
     the real names (`sherlock`, `lovecraft`, `ohenry_four_million`,
     `ohenry_whirligigs`, `hemingway`, `wilde_happy_prince`, `wodehouse`,
     `grimm`, `anderson`, `chesterton`, `london`, `mass_quantities`), and
     note this re-downloads from Project Gutenberg and is network-dependent.
   - Verify (from `lcats/`): `lcats survey --mode specials data/
     --no-progress`, with the expected-clean output shown and a
     troubleshooting pointer if findings remain (link to WI-RESIDUAL-0019's
     rule/override/allowlist disposition method).
   - Inspect (diagnostic, from `lcats/`): `lcats repair-specials <file>
     --format jsonl` for any flagged file, to see what a residual finding
     looks like.
   - Preview (from `lcats/`): `lcats promote --dry-run`, reading its
     report; note its `--source`/`--dest` defaults (`data/`, `../corpora`)
     are only correct when run from `lcats/`
     (`lcats/utils/env.py:21-36`).
   - Promote (the actual release step): the one-time
     `git rm -r corpora/ohenry corpora/wilde` historical cleanup **from the
     repo root** (`corpora/` does not exist under `lcats/`), then `cd
     lcats/` and `lcats promote` for real, called out as the step that
     changes tracked files.
2. Link to `lcats/docs/reference/corpus-promotion.md` for the promote
   command's full reference rather than repeating it.

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
- Every command is copy-pasteable; no step requires guessing a path, flag,
  or working directory.
- `lrh validate` reports 0 errors.

## Validation
- `lrh validate`

## Risk Notes
- The regenerate step is network-dependent (Project Gutenberg) and may be
  slow; the doc should say so up front rather than let it be a surprise.
- `lcats gather` silently skips files that already exist and has no
  `--force` flag (`lcats/gatherers/downloaders.py:98-102,230,260-261`), so
  a stale `data/` can make the "regenerate" step look successful while
  surveying old files; the clear-stale-state step must precede it.
- `git rm -r corpora/...` and `lcats gather`/`lcats promote` run from
  different working directories (repo root vs. `lcats/`); the doc must make
  each step's directory explicit rather than assuming continuity.
- The real-promote step mutates tracked files in `corpora/`; the doc must
  make unmistakably clear which steps are read-only/dry-run and which one
  isn't.
