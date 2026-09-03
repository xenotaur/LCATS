---
id: WI-PROMOTE-0102
title: Assess routing promote.py's legacy genre_sidecar usages through the sidecar-validator registry
type: investigation
status: proposed
priority: low
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams:
  - WS-PROMOTE-MODE-REDESIGN
related_design:
  - project/design/proposals/adopted/lcats-promote-mode-redesign/00_proposal.md
  - lcats/src/lcats/analysis/corpus/promote.py
  - lcats/src/lcats/analysis/corpus/sidecar_validators.py
  - lcats/src/lcats/analysis/corpus/genre_sidecar.py
depends_on: []
blocked_by: []
blocked: false
blocked_reason: null
resolution: null
expected_actions:
  - create_file
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - change_promote_wholesale_replacement_mechanism
  - retroactively_edit_resolved_execution_records
acceptance:
  - "A design note documents both current direct genre_sidecar usage sites in promote.py: _validate_sidecars' legacy-shape/v1 structural check (line ~189) and _promote_sidecar_records' legacy-flat overwrite guard (line ~916), their origin (WI-GENRE-0075/0076, PRs #350/#357), and an accurate account of what WI-PROMOTE-0097 (PR #405) did to each -- _validate_sidecars was untouched, while _promote_sidecar_records' guard was restructured (nested under a new sidecar_filename == GENRE_SIDECAR_FILENAME conditional while generalizing the promotion engine to multiple sidecar kinds) with its check logic and the genre_sidecar.is_legacy_flat_sidecar() call itself preserved unchanged"
  - "The note evaluates, for each usage separately, whether routing it through sidecar_validators would preserve its actual behavior -- noting both serve purposes (structural shape-detection, legacy-overwrite guarding) distinct from the registry's validate-on-promotion dispatch -- and states a clear recommendation: route through the registry, or leave as-is"
  - "If leaving as-is is recommended, the note proposes exact replacement wording for WS-PROMOTE-MODE-REDESIGN's exit criterion 3 and WI-PROMOTE-0097's acceptance criterion, without editing those files directly in this investigation"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - project/design/promote-genre-sidecar-import-assessment.md
---

# Work Item: WI-PROMOTE-0102

## Summary

Investigate whether `promote.py`'s two remaining direct `genre_sidecar`
usage sites should be routed through the `sidecar_validators` registry to
satisfy `WS-PROMOTE-MODE-REDESIGN`'s exit criterion 3 /
`WI-PROMOTE-0097`'s acceptance criterion literally, or whether that
wording should be narrowed instead. The deliverable is a design note with
a recommendation, not a code change.

## Problem / Context

`WS-PROMOTE-MODE-REDESIGN`'s exit criterion 3 reads: "a shared
sidecar-validator registry exists, registering every currently-produced
sidecar kind ..., with no direct promote.py import of any producer
subpackage." `WI-PROMOTE-0097`'s own acceptance criteria state it more
strongly: "promote.py imports only this registry, never genre_sidecar.py
or linguistics/sidecar.py directly."

`promote.py` on `main` still does `from lcats.analysis.corpus import
genre_sidecar` directly, used at two call sites:

1. `_validate_sidecars()` -- `replace`'s own pre-existing structural
   JSON-shape check (mojibake/malformed-sidecar findings), calling
   `genre_sidecar.validate_sidecar()`/`is_legacy_flat_sidecar()` to
   distinguish v1-shaped `genre.json` from the legacy flat shape.
2. `_promote_sidecar_records()` -- a guard in the insert/upsert engine
   that refuses to overwrite an existing legacy-flat `genre.json` at the
   destination, using `is_legacy_flat_sidecar()`.

Both usages predate `WI-PROMOTE-0097` entirely -- traced via `git log -S`
to `WI-GENRE-0075`/`WI-GENRE-0076` (PRs #350, #357), well before the
registry existed. `WI-PROMOTE-0097`'s merge commit (`9665a2d4`, PR #405)
did not touch usage 1 (`_validate_sidecars`) at all. It did touch usage 2:
diffing the merge commit against its actual mainline parent (not the
merge commit's own combined diff, which hides this) shows PR #405 nested
the legacy-flat-overwrite guard under a new `sidecar_filename ==
GENRE_SIDECAR_FILENAME` conditional while generalizing
`promote_sidecar_tranche()` into the shared multi-sidecar-kind
`_promote_sidecar_records()` engine -- the guard's own check logic and its
`genre_sidecar.is_legacy_flat_sidecar()` call were preserved unchanged,
only their structural nesting moved. Elsewhere in that same diff, PR #405
did remove a direct `genre_sidecar.validate_sidecar(record)` call from the
old tranche-validation path, replacing it with registry-driven dispatch --
consistent with the registry's actual purpose, just not a full removal of
every `genre_sidecar` reference. Review found: neither Copilot nor Codex
flagged the usages themselves on PR #405's review; Codex did flag (P2,
this WI's own first review round, PR #417) that an earlier draft of this
WI overstated usage 2 as "untouched" by PR #405 -- corrected above.

Neither usage bypasses the registry's actual safety property (uniform
validator dispatch for insert/upsert's manifest-driven promotion) --
one is `replace`'s own structural sanity check, unrelated to registry
validation; the other is a legacy-shape overwrite guard, also unrelated
to registry dispatch. This suggests the exit criterion was written more
broadly than what the registry work actually needed to guarantee, but
that has not been formally assessed or decided.

### Duplication search
- In-repo: no existing work item or design doc addresses this narrow
  question. Checked every file referencing `genre_sidecar` across
  `project/design/`, `project/work_items/`, and `project/workstreams/`
  -- all are about `genre_sidecar`'s own schema/content work
  (`WI-GENRE-*`, `WI-SF-*`, the knight-novum-analysis and
  genre-evidence-sidecars proposals), not this import-routing question.
- Sibling repos: None identified.
- External libraries: None -- project-specific tooling.
- Recommendation: Proceed.

### Demand search
- Work items: None open besides this one.
- Proposals: None reference this specific gap.
- Backlog: Surfaced by this session's own workstream exit-criteria audit
  for `WS-PROMOTE-MODE-REDESIGN` (2026-08-30), not a prior open request.
- Recommendation: Proceed.

## Scope

- Read both usage sites in full and confirm the behavioral analysis above
  (or correct it if the traversal turns up something missed).
- For each usage, assess whether it could be expressed as a
  `sidecar_validators`-registered validator without changing its actual
  behavior, or whether the registry's dispatch contract (validate an
  incoming payload against a filename-keyed validator) is a structural
  mismatch for what these two call sites actually do (shape-detection on
  an already-parsed value; overwrite-guarding against an existing
  destination file).
- Produce a design note stating the recommendation for each usage
  independently, plus, if applicable, proposed replacement wording for
  the two exit-criterion/acceptance-criterion texts.
- If the recommended change for a usage is small, mechanical, and
  behavior-preserving (e.g. swapping one call site to a registry lookup
  with no semantic change), this WI's own PR may apply it directly rather
  than deferring to a separate work item. Anything larger -- a change to
  the registry's own interface, a behavior change, or a multi-file
  refactor -- still requires a follow-up work item; use judgment and
  favor deferring when in doubt.

## Required Changes

1. **`project/design/promote-genre-sidecar-import-assessment.md`**: new
   design note covering both usages, the behavioral analysis, and the
   recommendation(s).

## Non-Goals

- Does not implement a large or behavior-changing routing change even if
  recommended -- that would be a separate, later work item. A small,
  mechanical, behavior-preserving fix may be applied directly in this
  WI's own PR (see Scope).
- Does not retroactively edit `WI-PROMOTE-0097`'s or
  `WS-PROMOTE-MODE-REDESIGN`'s files as part of this investigation --
  only proposes replacement wording in the design note.
- Does not change `replace`'s wholesale mechanism or any other
  `WS-PROMOTE-MODE-REDESIGN`-adjacent behavior.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- `lrh validate`

## Risk Notes

- The two usages serve genuinely different purposes from each other
  (structural shape-detection vs. overwrite-guarding) as well as from
  the registry's validate-on-promotion dispatch -- the assessment should
  treat them independently rather than assuming one answer covers both.

## Dependencies / Order

None. All three of `WS-PROMOTE-MODE-REDESIGN`'s originally anticipated
work items (`WI-PROMOTE-0097`, `WI-PROMOTE-0100`, `WI-PROMOTE-0101`) are
already resolved. This item was surfaced afterward, by an exit-criteria
audit -- per review feedback (Codex, PR #417), it is registered in the
workstream's own `work_items:` list rather than linked for context only,
so the workstream's "all work items resolved" exit criterion stays
gated on this item's resolution (and, if the recommendation requires a
follow-up implementation WI, on that item's resolution too) rather than
closing while exit criterion 3's literal wording is still unmet.

## Related Workstream and Designs

- Workstream: `project/workstreams/active/WS-PROMOTE-MODE-REDESIGN.md`
  (registered in its `work_items:` list; workstream closure is gated on
  this item's resolution)
- Design: `project/design/proposals/adopted/lcats-promote-mode-redesign/00_proposal.md`
