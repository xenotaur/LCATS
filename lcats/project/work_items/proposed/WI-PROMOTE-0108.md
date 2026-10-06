---
id: WI-PROMOTE-0108
title: Design genre sidecars as part of the standard corpus release workflow
type: investigation
status: proposed
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams: []
related_design:
  - project/design/proposals/adopted/lcats-promote-mode-redesign/00_proposal.md
  - project/design/proposals/adopted/genre-evidence-sidecars/00_proposal.md
  - docs/reference/prepare-corpora-release.md
  - docs/reference/corpus-promotion.md
  - project/work_items/resolved/WI-PROMOTE-0101.md
  - project/work_items/resolved/WI-GENRE-0077.md
depends_on: []
blocked_by: []
blocked: false
blocked_reason: null
resolution: null
expected_actions:
  - create_file
  - edit_file
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - change_promote_replace_semantics
  - edit_corpora
  - implement_the_recommended_workflow_beyond_small_mechanical_doc_fixes
acceptance:
  - "A design note documents why the WI-PROMOTE-0101 orphaned-sidecar guard is a safeguard and not a release-source solution: the genre sidecars from PR #362 exist only in corpora/, the documented release step is a plain lcats promote replace from regenerated data/, and --allow-orphaned-sidecar-deletion would still delete them"
  - "The note compares at least three concrete options for making genre sidecars part of the repeatable release source, with trade-offs, and recommends one"
  - "The note drafts the revised release procedure for docs/reference/prepare-corpora-release.md as text in the note, and names every follow-up work item the recommendation implies, without editing the release doc beyond small mechanical fixes"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - project/design/genre-sidecars-in-release-workflow.md
---

# Work Item: WI-PROMOTE-0108

## Summary

Design how genre sidecars (`genre.json`, and by extension other registered
sidecar kinds) become part of the standard corpus release workflow, so a
plain `lcats promote replace` no longer depends on the orphaned-sidecar guard
alone to avoid destroying them. The deliverable is a design note with a
recommendation and a list of follow-up work items, not an implementation.

## Problem / Context

`docs/reference/prepare-corpora-release.md` ends its release procedure with a
plain `lcats promote replace` from regenerated `data/`, which wholesale
replaces each affected collection in `corpora/`. PR #362 (`WI-GENRE-0077`,
merged 2026-09-29) added 146 `genre.json` files directly to `corpora/` through
`lcats promote insert`, with no matching files in `data/`. A Copilot review
finding on that PR warned that the next ordinary promotion of those
collections could silently delete the promoted evidence.

`WS-PROMOTE-MODE-REDESIGN` (closed 2026-09-26) mitigated this with
`WI-PROMOTE-0101`'s orphaned-sidecar guard: `replace` now refuses by default
when it would delete a registered sidecar kind present at the destination but
absent from source, unless `--allow-orphaned-sidecar-deletion` is passed. That
guard only blocks deletion. It does not make the sidecars part of the
repeatable release source, so a release run that passes the override flag, or
a fresh checkout that regenerates `corpora/` another way, would still lose
them. The maintainer's direction (2026-10-05) is that genre sidecars should
probably become part of the standard release, and that this needs a
design-first work item because the promotion logic already exists but the
release procedure does not use it.

Both parent workstreams (`WS-GENRE-EVIDENCE-SIDECARS`,
`WS-PROMOTE-MODE-REDESIGN`) are resolved, so `related_workstreams` is left
empty rather than reopening either.

### Duplication search
- In-repo: no existing work item or design addresses sidecars in the release
  source. The release doc and `corpus-promotion.md` describe only the guard.
  The backlog entry for this item was captured in PR #471.
- Sibling repos: none identified.
- External libraries: none; project-specific tooling.
- Recommendation: Proceed.

### Demand search
- Work items: none open on this question.
- Proposals: `PROP-LCATS-PROMOTE-MODE-REDESIGN` covers the guard, not the
  release source.
- Backlog: surfaced by the end-of-session review of `WS-PROMOTE-MODE-REDESIGN`
  and the PR #362 triage, then directed by the maintainer.
- Recommendation: Proceed.

## Scope

- Document the gap between the guard and a true release source.
- Evaluate at least three options, for example: a tracked tranche manifest
  replayed after `replace`; a regenerable `data/` sidecar tree populated by the
  pipeline; a release step that runs `insert`/`upsert --source` after
  `replace`; and any option the investigation finds that is better.
- Recommend one option, with its failure modes and its effect on
  `prepare-corpora-release.md`.
- Name the follow-up work items the recommendation implies.

## Required Changes

- Create `project/design/genre-sidecars-in-release-workflow.md` with the
  analysis, the option comparison, the recommendation, a drafted revised
  release procedure, and the follow-up list.
- If the recommendation is small, mechanical, and behavior-preserving, apply it
  directly. Anything larger becomes a follow-up work item; favor deferring when
  in doubt.

## Non-Goals

- Does not implement the recommended workflow beyond small mechanical doc
  fixes.
- Does not change `lcats promote replace` semantics or the orphaned-sidecar
  guard.
- Does not modify anything under `corpora/`.
- Does not decide whether to rewrite the 146 promoted files; that is
  `WI-GENRE-0109`.

## Acceptance Criteria

- A design note documents why the `WI-PROMOTE-0101` guard is a safeguard and
  not a release-source solution (sidecars exist only in `corpora/`, the release
  step is a plain `replace`, and the override flag would still delete them).
- The note compares at least three concrete options with trade-offs and
  recommends one.
- The note drafts the revised release procedure and names every follow-up work
  item the recommendation implies.
- `lrh validate` reports 0 errors.

## Validation

- `lrh validate`
- `git diff --name-only origin/main`

## Risk Notes

- The release procedure touches the shared `data/` and `corpora/` layout, so a
  recommendation that changes where sidecars live must name every consumer.
- Multiple sidecar kinds are registered (genre, scenes, linguistics, linguistics
  tokens); the recommendation should be general across them, not genre-only.
