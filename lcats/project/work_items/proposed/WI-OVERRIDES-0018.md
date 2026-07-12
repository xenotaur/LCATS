---
resolution: null
blocked_reason: null
blocked: false
id: WI-OVERRIDES-0018
title: Versioned per-story overrides consumed at gather time
type: deliverable
status: proposed
priority: high
owner: unassigned
related_focus:
  - FOCUS-WORLDCON-2026
related_workstreams:
  - WS-SPECIALS-CLEANUP
related_design:
  - project/workstreams/proposed/WS-SPECIALS-CLEANUP.md
depends_on:
  - WI-NORMALIZE-0017
forbidden_actions:
  - rewrite_corpus_json_in_place
  - modify_ci_pipeline
acceptance:
  - An override entry for a real judgment-call defect (e.g. Ângstrom in f_o_b_venus__bond) is applied during regeneration with provenance in story metadata
  - Overrides live outside data/ so they are never discovered as story JSON and never wiped by regeneration
  - Override schema is documented and covered by tests
required_evidence:
  - test_output
  - lrh_validate
artifacts_expected:
  - per-collection overrides file under lcats/lcats/gatherers/ (exact location decided at implementation)
  - lcats/tests/gatherers_tests/
---

# Work Item: WI-OVERRIDES-0018

## Summary
Add a small, versioned per-story overrides file (story id → find/replace entries with rationale) that the gather-time normalization hook applies after rule-based repairs, for defects rules cannot safely cover.

## Problem / Context
A handful of the 35 measured defects are judgment calls rather than clean family decodes (e.g. `Ângstrom` → `Ångstrom`, `Tha√ºle`), and future upstream defects will need one-off fixes. Because `data/` regenerates, these fixes must be replayable repo inputs — this is the durable home for human review decisions from WI-RESIDUAL-0019. Forward-compatible with the deferred bucket layout (the overrides content later migrates into per-story audit files).

## Scope
- Define the override file schema (story identifier, match text with context, replacement, rationale, reviewer).
- Consume overrides in the WI-NORMALIZE-0017 hook, after rules.
- Document the schema for contributors.

## Required Changes
1. Create the overrides file location and schema (proposed: per-collection JSON under `lcats/lcats/gatherers/`, exact form decided at implementation; must not live under `data/`).
2. Extend the normalization hook to load and apply overrides deterministically, recording provenance in story metadata.
3. Tests: applied override, non-matching override (warn, don't fail silently), determinism.
4. Document the schema in the gatherers README or `docs/`.

## Non-Goals
- Do not perform the human review that populates the file — that is WI-RESIDUAL-0019.
- Do not implement the bucket/story-directory migration.
- Do not allow overrides to run against stored corpus files outside the gather flow.

## Acceptance Criteria
- Real judgment-call override applies during regeneration with provenance.
- Overrides survive cache-clear + regeneration (they are repo-versioned inputs).
- Non-matching overrides surface a visible warning.

## Validation
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes
- Match-by-text needs enough context to be unique within the story; bare single-character matches would misfire.
- Story identity must be stable across regenerations (filename stem today; revisit if the bucket migration lands).
