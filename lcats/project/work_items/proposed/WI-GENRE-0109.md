---
id: WI-GENRE-0109
title: Rewrite the 146 promoted genre.json files to basename-only cache_db_path
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
  - project/work_items/resolved/WI-GENRE-0077.md
  - project/work_items/resolved/WI-GENRE-0075.md
  - project/work_items/resolved/WI-PROMOTE-0097.md
  - docs/reference/corpus-promotion.md
  - src/lcats/analysis/corpus/genre_sidecar.py
depends_on: []
blocked_by: []
blocked: false
blocked_reason: null
resolution: null
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - use_promote_replace
  - modify_assessment_content_other_than_cache_db_path
  - promote_before_dry_run_review
acceptance:
  - "No genre.json under corpora/ contains an absolute assessments[*].provenance.cache_db_path; every value is a basename only"
  - "All 146 rewritten files re-validate cleanly via genre_sidecar.validate_sidecar() in their final corpora/ location"
  - "The diff changes only the cache_db_path values in those 146 files; no other field or file under corpora/ changes"
  - "The rewrite was promoted with lcats promote upsert (not replace) after a reviewed --dry-run, and a unit test covers the rewrite logic"
required_evidence:
  - test_output
  - manual_review
  - lrh_validate
artifacts_expected:
  - corpora/*/*/genre.json
  - tools/rewrite_genre_cache_db_path.py
---

# Work Item: WI-GENRE-0109

## Summary

Rewrite `assessments[*].provenance.cache_db_path` in the 146 `genre.json`
files promoted by PR #362 from an absolute, machine-specific path to its
basename, and promote the result with `lcats promote upsert`.

## Problem / Context

PR #362 (`WI-GENRE-0077`, merged 2026-09-29) promoted 146 `genre-sidecar-v1`
files whose `assessments[*].provenance.cache_db_path` holds an absolute path
such as `/Users/<user>/.../cache/gutenbergindex.db` (a Copilot finding on that
PR). The path exposes one machine's layout and cannot be resolved from another
checkout. The field lives under each assessment; the sidecar root has no
`provenance` key.

The producer was fixed in PR #448 (`cache_readiness()` now stores the basename
only), so future runs are clean. The already-promoted files were deliberately
not rewritten at that time. The maintainer decided on 2026-10-05 that a rewrite
is worthwhile. Nothing reads the field beyond display, so risk is low; the cost
is a 146-file data diff.

### Duplication search
- In-repo: no existing script or work item rewrites promoted sidecar
  provenance. The backlog entry in `project/design/backlog.md` (PR #471)
  describes this work and should be removed or marked when this item exists.
- Sibling repos: none identified.
- External libraries: none.
- Recommendation: Proceed.

### Demand search
- Work items: none open.
- Proposals: none.
- Backlog: the PR #362 entry, which this item promotes.
- Recommendation: Proceed.

## Scope

- Write a small, tested one-off script that rewrites each assessment's
  `provenance.cache_db_path` to its basename across `corpora/*/*/genre.json`.
- Promote the rewritten sidecars with `lcats promote upsert --sidecar genre`
  after reviewing a `--dry-run`.
- Re-validate every promoted file.

## Required Changes

- Add the rewrite script under `tools/` with a unit test covering absolute
  paths, already-basename values, missing `provenance`, and non-genre files.
- Produce a tranche manifest or `--source` tree of the rewritten sidecars,
  review the `--dry-run` output, then promote with `upsert`.
- Re-validate all 146 files with `genre_sidecar.validate_sidecar()`.
- Mark or remove the corresponding entry in `project/design/backlog.md`.

## Non-Goals

- Does not change any other field in any sidecar, or any other file under
  `corpora/`.
- Does not use `lcats promote replace`.
- Does not change the producer; that was PR #448.
- Does not decide how genre sidecars join the release workflow; that is
  `WI-PROMOTE-0108`.

## Acceptance Criteria

- No `genre.json` under `corpora/` contains an absolute `cache_db_path`.
- All 146 files re-validate in their final location.
- The diff changes only the `cache_db_path` values.
- Promotion used `upsert` after a reviewed `--dry-run`, and a unit test covers
  the rewrite logic.

## Validation

- `scripts/test`
- `lrh validate`
- `git diff --stat origin/main`

## Risk Notes

- `upsert` overwrites whole files, so the source tree must be exactly the
  current files with only that field changed. Compare before and after.
- Run the rewrite against a clean, up-to-date checkout so the 146 files match
  `main`.
- The editable `lcats` install can resolve to a sibling checkout; verify
  `lcats.__file__` before running the promotion.
