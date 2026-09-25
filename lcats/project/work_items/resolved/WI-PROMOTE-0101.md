---
id: WI-PROMOTE-0101
title: Add orphaned-sidecar guard to lcats promote's replace mode
type: deliverable
status: resolved
priority: medium
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
  - lcats/src/lcats/analysis/corpus/promote_cli.py
  - lcats/src/lcats/analysis/corpus/discovery.py
  - lcats/src/lcats/analysis/corpus/sidecar_validators.py
depends_on:
  - WI-PROMOTE-0097
blocked_by: []
blocked: false
blocked_reason: null
resolution: "Implemented and merged in PR #416 (merge commit a19322d28fb09fa3cd70000a3cc5ed9cd523fbff). lcats promote replace now blocks an otherwise-clean collection by default when the wholesale replace would delete a registered sidecar kind that exists at the destination for a story but is missing from the corresponding source - the exact scenario PR #362's original review finding described. Added OrphanedSidecarFinding and _find_orphaned_sidecars(), which walks the destination collection's story buckets (the opposite traversal direction from every other check in promote.py) and checks only registered sidecar kinds via sidecar_validators.registered_filenames(), never a generic destination-only-file diff. --allow-orphaned-sidecar-deletion, replace-only, overrides the guard. A destination collection that doesn't exist yet is never blocked. insert/upsert are entirely unaffected. Review (Copilot) found and fixed 1 real P1 issue before merge: the original guard wrongly flagged a story that exists only at the destination (no story.json anywhere in the corresponding source bucket) as having an orphaned sidecar, blocking legitimate replaces of collections with retired stories; fixed by skipping any story whose source bucket lacks story.json before checking its sidecars. Also fixed a minor missing read_text() encoding on a new test. No automated reviewer response landed on the post-fix commits after a reasonable wait, so REVIEW-LANDED was satisfied via a substitute self-review pass (cold-context subagent + independent re-verification), which found no further issues. See project/executions/WI-PROMOTE-0101/ and project/executions/AD_HOC/*WI_PROMOTE_0101_ORPHAN_GUARD* for the full record chain. This was the last of WS-PROMOTE-MODE-REDESIGN's three anticipated stages."
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - implement_interactive_confirmation_prompt
  - change_promote_wholesale_replacement_mechanism
  - extend_validator_interface_to_non_json_kinds
  - implement_generic_destination_only_file_diff_guard
acceptance:
  - "replace refuses by default (copies nothing) when it would delete a registered sidecar kind present at the destination for a story but absent from the corresponding source story bucket"
  - "the guard checks only registered sidecar kinds via the WI-PROMOTE-0097 registry - not a generic destination-only-file diff, which was explicitly rejected for false-positive risk on legitimate corpora-only content"
  - "--allow-orphaned-sidecar-deletion overrides the guard and allows the wholesale replace to proceed, per collection"
  - "insert/upsert are entirely unaffected - the flag and the guard apply only to replace, since insert/upsert are structurally incapable of deleting anything regardless of flags"
  - "a destination collection that does not yet exist is never blocked by this guard - there is nothing to orphan on a fresh promotion"
  - "docs/reference/corpus-promotion.md and docs/reference/cli-commands.md document the guard and the escape hatch"
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
  - lcats/docs/reference/corpus-promotion.md
  - lcats/docs/reference/cli-commands.md
---

# Work Item: WI-PROMOTE-0101

## Summary

Add a targeted, registry-based orphaned-sidecar guard to `lcats promote
replace`: refuse the wholesale copy by default when it would delete a
registered sidecar kind that exists at the destination for a story but
is missing from the corresponding source. This is Stage 2 of
`WS-PROMOTE-MODE-REDESIGN`'s implementation plan
(`PROP-LCATS-PROMOTE-MODE-REDESIGN`, Decision 6).

## Problem / Context

Renaming the wholesale path to `replace` (`WI-PROMOTE-0097`) closed the
*accidental* silent-default invocation, but not a *deliberate* `replace`
against a collection that's since been `upsert`-into — the exact
scenario PR #362's original review finding described, made concrete by
the imminent whole-corpus `linguistics.json` rollout: someone runs
`replace` on a collection whose `data/` copy predates a bulk
`linguistics.json` upsert, silently destroying every promoted sidecar.

### Duplication search
- In-repo: No existing guard beyond the mode-rename itself.
  `WI-PROMOTE-0097` built the registry this guard depends on but
  implemented nothing about deletion.
- Sibling repos: None identified.
- External libraries: None — project-specific tooling.
- Recommendation: Proceed.

### Demand search
- Work items: None open besides this one fulfilling the anticipated
  slot.
- Proposals: `PROP-LCATS-PROMOTE-MODE-REDESIGN` Decision 6 is the
  governing design, already fully specified at design time (unlike
  Decision 8/Stage 3, which deferred detail) — this item implements it
  as designed.
- Backlog: `WS-PROMOTE-MODE-REDESIGN`'s own "Proposed Work Items" item 2
  anticipates this item ("Not yet minted").
- Recommendation: Proceed.

## Scope

- Add a pre-flight check inside `promote_collections()`, before
  `_copy_collection()` runs for each collection: for every registered
  sidecar kind, does the destination have it for a story whose source
  bucket lacks it?
- Add `--allow-orphaned-sidecar-deletion` to `replace` only.
- Update CLI flags and the two affected docs files.

## Required Changes

1. **`lcats/src/lcats/analysis/corpus/promote.py`**: add an
   orphan-detection function comparing a destination collection's
   registered sidecars against the corresponding source buckets (using
   `sidecar_validators.registered_filenames()`), and wire it into
   `promote_collections()`'s per-collection loop as an additional
   blocking condition alongside the existing mojibake/malformed-sidecar
   checks — a destination collection that doesn't exist yet is trivially
   never blocked.
2. **`lcats/src/lcats/analysis/corpus/promote_cli.py`**: add
   `--allow-orphaned-sidecar-deletion` to the `replace` subcommand only.
3. **`lcats/tests/analysis_tests/promote_test.py`**: cover the guard
   firing on a real orphaned-sidecar scenario, the escape hatch, the
   fresh-destination no-op case, and confirmation `insert`/`upsert` are
   unaffected.
4. **Docs**: update `corpus-promotion.md` and `cli-commands.md`.

## Non-Goals

- Does not implement an interactive confirmation prompt — explicitly
  rejected in Decision 6 (this codebase has zero existing interactive
  confirmations, and one would break the scripted release process in
  `prepare-corpora-release.md`).
- Does not implement a generic "any destination-only file" diff —
  rejected for false-positive risk on legitimate corpora-only content
  unrelated to sidecar promotion.
- Does not change `_copy_collection`'s own wholesale mechanism — only
  adds a pre-flight guard before it runs.
- Does not touch `insert`/`upsert` at all.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes

- The orphan check needs to iterate every story bucket in the
  *destination* collection (not the source), which is a different
  traversal direction from every other check in this file so far — get
  the source/destination comparison direction right, and cover it
  explicitly in tests, not just informally.
- `run_log.RunLog`'s existing per-collection event log
  (`WI-RUNLOG-0083`) should record a guard-blocked collection distinctly
  from a mojibake-blocked one, so a partial-run log stays diagnostic.

## Dependencies / Order

Depends on `WI-PROMOTE-0097` (resolved, provides the registry). This is
Stage 2 of `WS-PROMOTE-MODE-REDESIGN`; no dependency on Stage 3
(`WI-PROMOTE-0100`, resolved) — they are siblings, both depending only
on Stage 1.

## Related Workstream and Designs

- Workstream: `project/workstreams/active/WS-PROMOTE-MODE-REDESIGN.md`
- Design: `project/design/proposals/adopted/lcats-promote-mode-redesign/00_proposal.md`
