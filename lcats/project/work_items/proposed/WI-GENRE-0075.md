---
id: WI-GENRE-0075
title: Add a sidecar-tranche promotion mode to lcats promote
type: deliverable
status: proposed
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams:
  - WS-GENRE-EVIDENCE-SIDECARS
related_design:
  - project/design/proposals/proposed/genre-evidence-sidecars/00_proposal.md
  - project/work_items/resolved/WI-GENRE-0003.md
  - project/work_items/resolved/WI-GENRE-0004.md
  - lcats/src/lcats/analysis/corpus/genre_sidecar.py
  - lcats/src/lcats/analysis/corpus/promote.py
  - lcats/src/lcats/analysis/corpus/promote_cli.py
depends_on: []
blocked_by: []
blocked: false
blocked_reason: null
resolution: null
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - promote_sidecars
  - modify_lcats_annotate
  - change_wholesale_collection_promotion_default_behavior
acceptance:
  - "A new promotion mode (extending promote_collections() or a scoped sibling function) can promote selected stories' genre.json sidecars into corpora/ without wholesale-replacing the destination collection directory"
  - "Every sidecar promoted through this mode is validated via lcats.analysis.corpus.genre_sidecar.validate_sidecar() before being written; a sidecar that fails validation is refused, not silently written"
  - "A legacy flat genre.json (per genre_sidecar.is_legacy_flat_sidecar()) at the promotion destination is handled explicitly (converted or refused with a clear error), not silently overwritten or silently left stale"
  - "The existing wholesale-collection promote_collections() path is unchanged for every caller that does not opt into the new tranche mode"
  - "A dry-run mode exists for the new tranche-promotion path, consistent with promote_collections()'s existing dry_run parameter"
  - "The lcats promote CLI (promote_cli.py) can actually select and invoke the new tranche mode - not just the underlying library function - since promote_cli.run() currently always calls the wholesale promote_collections() path unconditionally"
  - "scripts/test passes with no new failures"
  - "lrh validate reports 0 errors"
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - lcats/src/lcats/analysis/corpus/promote.py
  - lcats/src/lcats/analysis/corpus/promote_cli.py
  - lcats/tests/analysis_tests/promote_test.py
---

# Work Item: WI-GENRE-0075

## Summary

Extend `lcats promote` with a sidecar-tranche promotion mode: the ability
to promote selected stories' `genre.json` sidecars into `corpora/` without
replacing the rest of the destination collection. This is Step 4 of
`PROP-GENRE-EVIDENCE-SIDECARS`'s Implementation Plan, unblocking the
downstream corpora-promotion work item that depends on it.

## Problem / Context

`WS-GENRE-EVIDENCE-SIDECARS` has landed real, validated evidence -
`WI-GENRE-0004`'s gated `claude-opus-4-8` run produced 146 real
`genre-sidecar-v1` records (`experiments/05_metadata_genre_prefilter/results/full_scan/validation_results.jsonl`),
each already validated via `genre_sidecar.validate_sidecar()` before being
written. That data has nowhere safe to land in `corpora/`: `lcats promote`
(`lcats/src/lcats/analysis/corpus/promote.py`) is wholesale-only by
design - `_copy_collection()`'s own docstring: "Wholesale-replace dest_dir
with a copy of source_dir's contents"; `promote_collections()`'s own
docstring: "Promotion wholesale-replaces the destination collection
directory... so stale files from a prior promotion cannot linger." There
is no way to promote a subset of stories' sidecars without replacing every
other file in that collection. `WI-GENRE-0004` explicitly deferred this -
its own `forbidden_actions` included `promote_sidecars` and
`modify_lcats_promote` - and `PROP-GENRE-EVIDENCE-SIDECARS`'s own
Implementation Plan names this as its own separate Step 4, ahead of the
Step 5 promotion step that depends on it.

### Duplication search
- In-repo: No existing tranche/partial-collection promotion path exists in
  `promote.py` - confirmed via `grep -n "^def \|^class " lcats/src/lcats/analysis/corpus/promote.py`,
  which shows `destination_name`, `_validate_sidecars`, `survey_collection`,
  `_validate_distinct_roots`, `_copy_collection`, and `promote_collections`
  (plus the `BlockingFinding`/`MalformedSidecarFinding`/`CollectionSurveyResult`/
  `PromotionReport` dataclasses) - every one of them shaped around
  whole-collection survey/copy, none offering a per-story or per-sidecar
  promotion path (review finding, PR #348 - an earlier draft of this
  entry named only three of the six functions, incorrectly implying they
  were the file's entire contents).
- Sibling repos: None identified.
- External libraries: None - this is native LCATS corpus-promotion logic.
- Recommendation: Proceed.

### Demand search
- Work items: `WI-GENRE-0004` (resolved) produced the real evidence this
  item needs a destination for; its own `forbidden_actions` explicitly
  deferred sidecar promotion and `lcats promote` modification to a later
  item. No other work item covers this.
- Proposals: `PROP-GENRE-EVIDENCE-SIDECARS` requests this directly as
  Implementation Plan Step 4.
- Workstreams: `WS-GENRE-EVIDENCE-SIDECARS` lists this as its own next
  step; still `status: proposed`, not yet closed.
- Backlog: No matching entry found in `project/design/backlog.md`.
- Recommendation: Proceed.

## Scope

- Add a promotion mode that operates on selected stories' `genre.json`
  sidecars specifically, not whole collection directories.
- Reuse `genre_sidecar.validate_sidecar()` for validation before any write;
  do not invent a second validation path.
- Handle the legacy-flat-sidecar case explicitly using
  `genre_sidecar.is_legacy_flat_sidecar()` (already implemented for this
  purpose) - convert or refuse, never silently overwrite.
- Preserve a dry-run mode consistent with the existing
  `promote_collections(..., dry_run: bool = False)` parameter shape.
- Leave the existing wholesale `promote_collections()` path and its
  callers completely unchanged.
- Wire the new mode into the `lcats promote` CLI itself
  (`promote_cli.py`), not just the underlying library function - the
  workstream's exit criterion is about what `lcats promote` can do, and
  `promote_cli.run()` currently only ever calls the wholesale path.

## Required Changes

1. **`lcats/src/lcats/analysis/corpus/promote.py`**: add a new function
   (or extend `promote_collections()` with a scoped mode - implementer's
   choice, justified against the existing `survey_collection`/
   `PromotionReport`/`CollectionSurveyResult` shapes already in this file)
   that accepts a set of story identifiers (or a manifest path, e.g. the
   `genre_balanced_manifest.jsonl`/`validation_results.jsonl` shape
   `WI-GENRE-0004` already produces) and promotes only those stories'
   `genre.json` files into the corresponding `corpora/` story directories,
   validating each via `genre_sidecar.validate_sidecar()` first.
2. **`lcats/src/lcats/analysis/corpus/promote_cli.py`**: `run()` currently
   calls `promote.promote_collections()` unconditionally - add a way to
   select the new tranche mode from the CLI (e.g. a `--tranche-manifest`
   flag alongside the existing `collections`/`--source`/`--dest`/
   `--dry-run` arguments), so `lcats promote` can actually invoke the new
   mode end-to-end, not just the library function in isolation. Existing
   invocations with no such flag must be unaffected.
3. **`lcats/tests/analysis_tests/promote_test.py`**: add tests covering:
   a clean tranche promotion of a subset of stories; refusal of an invalid
   sidecar (does not write, reports the validation failure); legacy-flat
   sidecar handling at the destination; dry-run mode makes no writes; the
   new CLI flag actually reaches the new tranche-mode function (not just
   the library function called directly); and confirmation that
   `promote_collections()`'s existing wholesale behavior, its CLI
   invocation, and their own tests are all unaffected.

## Non-Goals

- Does not actually run the promotion for real against `corpora/` or
  commit any promoted sidecars - that is a separate, dependent follow-on
  work item (`WI-GENRE-0077`).
- Does not touch `lcats annotate` - that is a separate, independent work
  item (`WI-GENRE-0076`), no dependency either direction.
- Does not change `promote_collections()`'s existing wholesale-collection
  default behavior for any other caller.
- Does not implement human-review/adjudication support - that is a later
  Implementation Plan step (Step 9), not this item.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes

- This item only builds the promotion mechanism; it explicitly does not
  run it for real against the tracked `corpora/` tree (`forbidden_actions`:
  `promote_sidecars`). Test against a scratch/fixture corpus root, not the
  real `corpora/` directory.
- The 5th-of-7 exit criterion this item partially unblocks
  (`WS-GENRE-EVIDENCE-SIDECARS`'s "lcats promote can promote selected
  genre.json sidecar tranches without wholesale collection replacement")
  is satisfied by this item alone; the workstream's 6th criterion (actual
  promotion into `corpora/`) needs the dependent follow-on item.

## Dependencies / Order

No `depends_on`. `WI-GENRE-0077` (corpora promotion) depends on this item.
`WI-GENRE-0076` (`lcats annotate` append-mode) has no dependency relationship
with this item in either direction and may proceed in parallel.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-GENRE-EVIDENCE-SIDECARS.md`
- Design: `project/design/proposals/proposed/genre-evidence-sidecars/00_proposal.md`
