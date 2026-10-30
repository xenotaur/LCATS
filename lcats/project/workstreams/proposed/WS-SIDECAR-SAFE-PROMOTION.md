---
id: WS-SIDECAR-SAFE-PROMOTION
kind: planning_node
title: Sidecar-safe promotion pipeline
status: proposed
stage: planned
origin: design_review
summary: "Make the corpus release procedure provably unable to silently lose a registered sidecar kind: a documented release rule and a verified seed or regeneration path for every kind, plus a decision on binding sidecars to story text."
related_focus: []
related_roadmap: []
related_design:
  - project/design/genre-sidecars-in-release-workflow.md
  - project/design/proposals/adopted/lcats-promote-mode-redesign/00_proposal.md
  - project/design/proposals/adopted/genre-evidence-sidecars/00_proposal.md
  - docs/reference/prepare-corpora-release.md
  - docs/reference/corpus-promotion.md
work_items:
  - WI-PROMOTE-0117
  - WI-PROMOTE-0118
  - WI-PROMOTE-0124
  - WI-PROMOTE-0125
exit_criteria:
  - "Every sidecar kind registered in sidecar_validators._REGISTRY (genre.json, scenes.json, linguistics.json, linguistics.tokens.json) has a documented release rule and a verified seed or regeneration path"
  - "The release runbook states or links that rule, so an operator following it cannot lose a registered sidecar"
  - "How a seeded genre sidecar is bound to its story has a recorded decision, covering whether a schema change or story-text fingerprint is needed and where any check would run"
  - "All work items are resolved and lrh validate reports 0 errors"
---

# Workstream: Sidecar-safe promotion pipeline

## Purpose

Close the "a corpus release cannot silently lose a sidecar" layer of the promotion
pipeline. `WS-PROMOTE-MODE-REDESIGN` delivered the explicit insert, upsert and
replace modes and the orphaned-sidecar guard. `WS-GENRE-EVIDENCE-SIDECARS`
delivered the genre evidence. `WI-PROMOTE-0108`, `WI-GENRE-0109`,
`WI-PROMOTE-0112` and `WI-PROMOTE-0115` delivered the design, the path rewrite,
the seed manifest tool and the runbook step that let a release carry the 146
tranche-promoted `genre.json` sidecars through `replace`.

What remains is the general rule for every other registered kind, and the
question of whether a seeded sidecar can be detected as stale. The priority is
the 1.0 corpus release procedure being complete and safe: an operator following
the runbook must not lose evidence sidecars. It is not driven by WorldCon timing.

## Scope

- A documented release rule, and a verified seed or regeneration path, for every
  sidecar kind registered in `sidecar_validators._REGISTRY`: `genre.json`,
  `scenes.json`, `linguistics.json` and `linguistics.tokens.json`
  (`WI-PROMOTE-0117`).
- A recorded decision on how a seeded genre sidecar is bound to its story (whether a
  schema change or story-text fingerprint is needed), and where any check would run (`WI-PROMOTE-0118`).
- Durable archive of the original genre-evidence checkpoint files and a baseline
  story-hash manifest derived from them (`WI-PROMOTE-0124`).
- A real-spaCy reproduction of linguistics sidecar release seeding, closing the gap
  the release-rule note left as "Not reproduced" (`WI-PROMOTE-0125`).
- Runbook edits (`docs/reference/prepare-corpora-release.md`) only where an
  operator step changes.

## Prior Art Check

### Duplication search
- In-repo: no workstream covers release-time sidecar safety. The nearest are the
  resolved `WS-PROMOTE-MODE-REDESIGN` (modes and guard) and
  `WS-GENRE-EVIDENCE-SIDECARS` (genre evidence), both closed; this workstream is
  the closure layer on top of them.
- Sibling repos and external libraries: none applicable.
- Recommendation: proceed.

### Demand search
- Design note `project/design/genre-sidecars-in-release-workflow.md` lists the two
  open items as follow-ups 3 (release rule for other kinds) and 4 (story-text
  binding).
- PR #362's open orphan-guard review thread raised the original concern.
- Recommendation: proceed; no existing work item covers either follow-up.

## Work Items

- **WI-PROMOTE-0117**: define the release rule for sidecar kinds other than
  `genre.json`. Resolved (PR #499; the rule is in
  `project/design/sidecar-kinds-release-rule.md`).
- **WI-PROMOTE-0118**: decide how a seeded genre sidecar is bound to its story
  (whether a schema change or story-text fingerprint is needed), and where any
  check would run. Resolved (PR #526; the note is
  `project/design/genre-sidecar-story-binding.md`).
- **WI-PROMOTE-0124**: archive the Opus and gpt-oss checkpoint files for the 146
  genre-evidence stories as tracked evidence and derive the baseline-hash manifest
  from them. Resolved (PR #533; the archive is under
  `experiments/05_metadata_genre_prefilter/results/full_scan/checkpoint_archive_2026-08-21/`).
- **WI-PROMOTE-0125**: reproduce linguistics sidecar release seeding with a real spaCy
  run (the two registered linguistics kinds, a real lexicon file, the single-collection
  live-scan case and the stray-story rejection), and update the release-rule note.
  Proposed.

Resolved provenance, not listed in `work_items` because they predate this
workstream: `WI-PROMOTE-0108`, `WI-GENRE-0109`, `WI-PROMOTE-0112`,
`WI-PROMOTE-0115`.

## Exit Criteria

- Every sidecar kind registered in `sidecar_validators._REGISTRY` has a documented
  release rule and a verified seed or regeneration path.
- The release runbook states or links that rule.
- How a seeded genre sidecar is bound to its story has a recorded decision.
- All work items are resolved and `lrh validate` reports 0 errors.

## Non-Goals

- No change to `lcats promote replace` semantics or the orphaned-sidecar guard.
- No focus decision: `related_focus` stays empty until a 1.0 focus exists, then is
  re-linked.
- No PyPI package release work; that is `WS-RELEASE`.
- No edits to `corpora/` or `data/`.
