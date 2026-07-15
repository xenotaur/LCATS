---
resolution: "Implemented and merged in PR #121 (commit ac1857a). Added lcats/gatherers/normalization.py applying measured repair rules at gather time via the shared repair-specials path, wired into both write paths before json.dump, with rule-id provenance in story metadata; decision-log + design.md persistence-boundary amended."
blocked_reason: null
blocked: false
id: WI-NORMALIZE-0017
title: Apply repair rules at gather time with provenance metadata
type: deliverable
status: resolved
priority: high
owner: unassigned
related_focus:
  - FOCUS-WORLDCON-2026
related_workstreams:
  - WS-SPECIALS-CLEANUP
related_design:
  - project/workstreams/proposed/WS-SPECIALS-CLEANUP.md
  - project/design/design.md
depends_on:
  - WI-RULES-0016
forbidden_actions:
  - rewrite_corpus_json_in_place
  - modify_ci_pipeline
acceptance:
  - Regenerating a story with a known upstream defect produces a repaired body and metadata listing the applied rule ids
  - Stories with no findings pass through byte-identical
  - Two consecutive regenerations from the same cached source produce identical output
required_evidence:
  - test_output
  - lrh_validate
artifacts_expected:
  - lcats/lcats/gatherers/parser.py
  - lcats/lcats/gatherers/downloaders.py
  - lcats/tests/gatherers_tests/
---

# Work Item: WI-NORMALIZE-0017

## Summary
Add a deterministic post-extraction normalization step to the gather pipeline that applies the measured repair rules (and, later, per-story overrides) before story JSON is written, stamping applied rule ids into story metadata.

## Problem / Context
`data/` is cleared and regenerated after major changes, so edits to stored JSON are transient; durable fixes must be replayable pipeline inputs (see WS-SPECIALS-CLEANUP Background and the data/-vs-corpora/ lifecycle). The 35 measured defects are byte-for-byte present in upstream Gutenberg sources (verified: `parser.py` decodes strict UTF-8), so they can only be fixed after extraction. This supersedes the 2026-06-18 decision to keep application out of scope; a decision-log entry accompanies this item.

## Scope
- One normalization entry point in the gather write path shared by all gatherers.
- Provenance: applied rule ids recorded in story `metadata`.
- A decision-log entry and design.md persistence-boundary amendment recording the offsets→rules pivot.

## Required Changes
1. Add a normalization function (e.g. in `lcats/lcats/gatherers/gatherlib.py` or a new module) that applies `DEFAULT_REPAIR_RULES` to extracted body text deterministically.
2. Wire it into the story-write path used by both `DataGatherer` (`lcats/lcats/gatherers/downloaders.py`) and the mass_quantities parser (`lcats/lcats/gatherers/parser.py`).
3. Record applied rule ids (and counts) in the story JSON `metadata` field.
4. Add tests covering: repaired story, untouched story, determinism across runs.
5. Add the decision-log entry in `project/memory/decision_log.md` and amend the State and Persistence Boundary section of `project/design/design.md`.

## Non-Goals
- Do not implement the per-story overrides file — that is WI-OVERRIDES-0018 (but design the hook so overrides can plug in).
- Do not modify stored corpus/data JSON directly.
- Do not change detector or survey behavior.

## Acceptance Criteria
- Known-defect story regenerates repaired, with rule ids in metadata.
- Clean stories are byte-identical through the hook.
- Regeneration is deterministic (identical output twice from the same cache).
- Decision log and design.md updated.

## Validation
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes
- The hook must run on decoded text after extraction, not raw bytes, or family patterns will not match.
- Gatherers have multiple write paths; missing one leaves inconsistent output between collections.
