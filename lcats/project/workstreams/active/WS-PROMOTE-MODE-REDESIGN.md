---
id: WS-PROMOTE-MODE-REDESIGN
kind: planning_node
title: lcats promote Mode Redesign
status: active
stage: planned
origin: design_review
summary: Deliver PROP-LCATS-PROMOTE-MODE-REDESIGN — mandatory insert/upsert/replace modes for lcats promote, a shared sidecar-validator registry, and a targeted safety guard preventing replace from silently destroying tranche-promoted sidecars.
related_focus: []
related_roadmap: []
related_design:
  - project/design/proposals/adopted/lcats-promote-mode-redesign/00_proposal.md
  - project/design/proposals/proposed/genre-evidence-sidecars/00_proposal.md
work_items:
  - WI-PROMOTE-0097
  - WI-PROMOTE-0100
  - WI-PROMOTE-0101
  - WI-PROMOTE-0102
exit_criteria:
  - lcats promote requires an explicit insert/upsert/replace mode; no silent default exists
  - insert and upsert both require a registered sidecar validator by default, with --allow-unvalidated as the only override
  - a shared sidecar-validator registry exists, registering every currently-produced sidecar kind (genre.json, scenes.json, linguistics.json, linguistics.tokens.json), with no direct promote.py import of any producer subpackage
  - replace refuses by default when it would delete a registered sidecar kind absent from source, overridable only via --allow-orphaned-sidecar-deletion
  - insert and upsert can source records from a live directory scan of data/, not only a pre-built manifest
  - all work items resolved and lrh validate reports 0 errors
---

# Workstream: lcats promote Mode Redesign

## Purpose

This workstream coordinates implementation of
`PROP-LCATS-PROMOTE-MODE-REDESIGN`: removing `lcats promote`'s silently
destructive default, replacing it with three mandatory, explicitly-named
modes, and closing the specific data-loss hazard between tranche-promoted
sidecars and the pre-existing wholesale path — surfaced live by a Copilot
review finding on PR #362 (`WI-GENRE-0077`) and made concrete and
near-term by an imminent whole-corpus `linguistics.json` rollout.

## Scope

- Restructure `lcats promote`'s CLI into mandatory `insert`/`upsert`/
  `replace` modes; no default mode.
- Build a shared sidecar-validator registry serving multiple producer
  subpackages (`genre_sidecar.py`, `linguistics/sidecar.py`) without
  `promote.py` importing either directly.
- Require a registered validator by default for every `insert`/`upsert`
  write, uniformly, with a single named escape hatch.
- Add a targeted, registry-based guard preventing `replace` from silently
  deleting a registered sidecar kind absent from `data/`.
- Extend `insert`/`upsert` to source records from a live scan of
  `data/<collection>/*/<sidecar-filename>`, not only a pre-built
  manifest.

## Prior Art Check

### Duplication search
- In-repo: No existing implementation found. `WI-GENRE-0075` (resolved)
  built the mechanism this workstream generalizes.
- Sibling repos: None identified.
- External libraries: None — project-specific tooling.
- Recommendation: Proceed.

### Demand search
- Work items: No open work item requests this redesign.
- Proposals: `PROP-GENRE-EVIDENCE-SIDECARS` Decision 7 is the governing
  design this workstream's own proposal extends, not a duplicate.
- Backlog: No matching entry.
- Recommendation: No action.

## Proposed Work Items

Anticipated breakdown, in dependency order (see the proposal's own
Implementation Plan):

1. Sidecar-validator registry + mandatory mode split + uniform validation
   requirement + `--sidecar` flag. **Resolved — `WI-PROMOTE-0097`
   (PR #405).**
2. `replace`'s targeted orphaned-sidecar guard. **Resolved —
   `WI-PROMOTE-0101` (PR #416).**
3. `insert`/`upsert` live-directory-scan sourcing — flagged as a priority
   given the imminent linguistics-sidecar rollout this directly de-risks.
   **Resolved — `WI-PROMOTE-0100` (PR #411).**
4. Assess whether `promote.py`'s two remaining direct `genre_sidecar`
   imports should route through the sidecar-validator registry, to
   satisfy exit criterion 3 literally, or whether that criterion's
   wording should be narrowed instead — surfaced by a post-Stage-3
   exit-criteria audit, not part of the original Implementation Plan.
   **In progress — `WI-PROMOTE-0102` (PR #417).**

## Non-Goals

- Does not implement schema-aware content merging inside `promote.py` for
  any sidecar kind.
- Does not extend the validator interface to non-JSON sidecar kinds.
- Does not touch `lcats annotate`'s own sidecar-writing behavior.

## Open Questions

- ~~Exact registry module filename/location (deferred to the first work
  item).~~ — **resolved by `WI-PROMOTE-0097`**: `analysis/corpus/
  sidecar_validators.py`.
- ~~Whether `--allow-unvalidated` also bypasses a registered-but-failing
  validator, or only covers the unregistered-kind case (deferred to the
  first work item).~~ — **resolved by `WI-PROMOTE-0097`**: only the
  unregistered-kind case; a registered validator's rejection is never
  bypassable.
