---
id: WI-PROMOTE-0115
title: Add the genre-sidecar seed step to the corpus release runbook
type: deliverable
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
  - project/design/genre-sidecars-in-release-workflow.md
  - docs/reference/prepare-corpora-release.md
  - docs/reference/corpus-promotion.md
  - tools/README.md
  - tools/build_genre_seed_manifest.py
  - tools/rewrite_genre_cache_db_path.py
  - project/work_items/resolved/WI-PROMOTE-0108.md
  - project/work_items/resolved/WI-PROMOTE-0112.md
  - project/work_items/resolved/WI-GENRE-0109.md
  - project/work_items/resolved/WI-PROMOTE-0101.md
  - project/work_items/resolved/WI-PROMOTE-0100.md
depends_on:
  - WI-PROMOTE-0108
  - WI-PROMOTE-0112
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
  - change_promote_replace_semantics
  - modify_tool_or_source_code
  - edit_corpora
  - write_to_real_corpora_or_data
  - use_promote_upsert_for_seeding
  - edit_immutable_evidence_or_execution_records
acceptance:
  - "docs/reference/prepare-corpora-release.md has a seed step placed before the promotion preview, with the exact commands (build the manifest with tools/build_genre_seed_manifest.py --expect-count 146, then lcats promote insert --sidecar genre --tranche-manifest <manifest> --dest data/ first with --dry-run and then for real), the expected output and exit codes, and what to do on a rejection or a collision; the existing step 7b orphaned-sidecar caution points at the new step and still warns against --allow-orphaned-sidecar-deletion; the 'If verification finds problems' section is updated so a re-run includes the seed step"
  - "A scratch run on copies of a populated data/ and of corpora/ (never the real trees) is recorded in the execution record with the exact commands and results: a seeded data/ previews clean (lcats promote replace --dry-run reports 12 would promote and 0 blocked), a bare replace exits 0, and the 146 genre.json files are byte-identical to corpora/; every command added to the docs was run"
  - "docs/reference/corpus-promotion.md documents seeding data/ with insert --dest data/ and why insert and not upsert; tools/README.md lists tools/build_genre_seed_manifest.py and tools/rewrite_genre_cache_db_path.py if that is a trivial accurate addition"
  - "No incoming reference breaks: a repo-wide grep for references to the runbook's step numbers (excluding immutable evidence and execution records) is recorded with its result, the chosen step numbering is recorded, and lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - docs/reference/prepare-corpora-release.md
  - docs/reference/corpus-promotion.md
  - tools/README.md
---

# Work Item: WI-PROMOTE-0115

## Summary

Make the documented corpus release procedure complete by adding the
genre-sidecar seed step, now that the seed tool exists
(`WI-PROMOTE-0112`, `tools/build_genre_seed_manifest.py`). Today an operator
following `docs/reference/prepare-corpora-release.md` hits the orphaned-sidecar
block at the final `replace` and has no documented way forward except the
override flag that would delete the 146 genre sidecars. This is follow-up 2 of
the `WI-PROMOTE-0108` design note.

## Problem / Context

A bare release `lcats promote replace` against the current `corpora/` exits `1`
and blocks 7 collections (146 orphaned genre sidecars). The recommended fix
(Option C in `project/design/genre-sidecars-in-release-workflow.md`) seeds the
regenerated `data/` with the sidecars *before* `replace`, using create-only
`lcats promote insert --sidecar genre --tranche-manifest <manifest> --dest data/`
(`insert`, never `upsert`, which would overwrite a pipeline-produced
`genre.json`). The manifest is built at release time from the tracked evidence
file by `python tools/build_genre_seed_manifest.py --manifest-out <path>
--expect-count 146`. On scratch copies, seeding then a bare `replace` gave exit
`0`, 12 collections promoted, 0 blocked, and 146 byte-identical `genre.json`
files.

**Design correction to resolve and record.** The note's drafted step 6b sits
*after* the runbook's step 6 preview (`lcats promote replace --dry-run`). But an
unseeded preview shows 7 blocked collections, while a seeded `data/` previews
clean (12 would promote, 0 blocked, checked on scratch copies). So the seed step
belongs *before* the preview. Seeding also does not disturb the Verify step: the
specials survey exits `0` on a seeded scratch copy with all 146 sidecars present.

Placement default: add the step as "3b" inside the Regenerate step. That needs
no renumbering, so the one incoming step reference outside the doc
(`docs/reference/cli-commands.md` cites "step 2") and the historical references
in immutable evidence and execution records (for example `EV-0003`'s "step 6" =
preview) stay correct. The executor may renumber instead only if it records why
and updates every non-immutable reference.

### Duplication search
- In-repo: no existing work item or doc adds the seed step. The runbook's step
  7b has only a caution that explains the block; the design note drafts the step
  but is not the runbook. This item is follow-up 2 of that note.
- Sibling repos: none identified.
- External libraries: none; project-specific docs.
- Recommendation: Proceed.

### Demand search
- Work items: none open; named as follow-up 2 in `WI-PROMOTE-0108`'s note and
  deferred by `WI-PROMOTE-0112`'s Non-Goals.
- Proposals: `PROP-LCATS-PROMOTE-MODE-REDESIGN` covers the guard, not the runbook.
- Backlog: no entry.
- Recommendation: Proceed.

Both parent workstreams (`WS-GENRE-EVIDENCE-SIDECARS`,
`WS-PROMOTE-MODE-REDESIGN`) are resolved, so `related_workstreams` is left empty.

## Scope

- `docs/reference/prepare-corpora-release.md`: add the seed step before the
  promotion preview, with exact commands, expected output and exit codes, and
  what to do on a rejection (a seed record whose story bucket regeneration no
  longer produces) or a collision (a pipeline-produced `genre.json` already in
  `data/`). Update the existing 7b orphaned-sidecar caution so it points at the
  new step and keeps the warning against `--allow-orphaned-sidecar-deletion`.
  Update the "If verification finds problems" section so a re-run includes the
  seed step, since `lcats clean` empties `data/` every time.
- `docs/reference/corpus-promotion.md`: in the `insert`/`upsert` section, document
  seeding `data/` with `insert --dest data/` and why `insert` and not `upsert`.
- `tools/README.md`: list the two tools if that is a trivial, accurate addition.
- Verify every command added to the docs on scratch copies, and record the
  results.

## Required Changes

- Edit the three docs as above. The seed step uses `insert` (create-only) and
  tells the operator to run the `--dry-run` first and to stop on any rejection.
- Run every added command on scratch copies of a populated `data/` (a shared one
  exists at `/Users/centaur/Tempspace/Projects/LCATS/data`) and of `corpora/`,
  never the real trees, and record the exact commands and results in the
  execution record: the manifest build, `insert --dry-run`, the real `insert`, a
  second `insert` (rejected for all 146), `replace --dry-run` on the seeded
  copy (12 would promote, 0 blocked), and a bare `replace` (exit 0, 146
  byte-identical `genre.json`). Also record that the unseeded preview is blocked
  (exit 1, 7 collections) as the control.
- Run a repo-wide grep for references to the runbook's step numbers, excluding
  immutable evidence and execution records, and record the result and the chosen
  numbering. Do not edit immutable evidence or execution records.
- Do not edit the design note; record the ordering correction in the execution
  record (a one-line correction to the note is allowed only if the executor shows
  the note's ordering is actively misleading).

## Non-Goals

- No code or tool changes; the tools are already merged (`WI-PROMOTE-0112`).
- Does not change `lcats promote replace` semantics or the orphaned-sidecar guard.
- Does not cover other sidecar kinds, a release preflight, or a story-text
  fingerprint for genre sidecars (design-note follow-ups 3 and 4).
- Does not write to the real `data/` or `corpora/`, and does not edit the tracked
  evidence file.

## Acceptance Criteria

- The runbook has a seed step before the promotion preview, with exact commands,
  expected output and exit codes, and rejection/collision guidance; the 7b caution
  points at it and still warns against the override flag; the "If verification
  finds problems" section covers a re-run.
- A recorded scratch run shows a seeded `data/` previews clean (12 would promote,
  0 blocked), a bare `replace` exits 0, and 146 `genre.json` files are
  byte-identical to `corpora/`; every added command was run.
- `corpus-promotion.md` documents the seeding and why `insert`; `tools/README.md`
  lists both tools if that was trivial.
- No incoming reference breaks, the chosen numbering is recorded, and
  `lrh validate` reports 0 errors.

## Validation

- `lrh validate`
- `git diff --name-only origin/main`
- `scripts/test`

## Risk Notes

- Seeding must happen after every regeneration: `lcats clean` empties `data/`, so
  an operator who re-runs step 2 or 3 must seed again. State this in the runbook.
- The seeded sidecars carry no story-text fingerprint, so stale evidence for a
  story whose text changed is not detected (design-note follow-up 4); say so
  briefly rather than implying the seed is verified against the text.
- The scratch runs need a populated `data/` copy; worktrees have none. The
  editable `lcats` install can resolve to another checkout, so verify
  `lcats.__file__` and run with `PYTHONPATH` set to this checkout's `src`; use the
  `LCATS` conda environment's pinned tools.
- The doc has a long step 2 and other fenced commands; keep new commands copy-
  pasteable from `lcats/`, as the runbook's other steps are.
