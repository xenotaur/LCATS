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
  - promote_before_user_go_ahead
  - modify_corpora_before_the_reviewed_real_upsert
acceptance:
  - "No genre.json under corpora/ contains an absolute assessments[*].provenance.cache_db_path; every value is a basename only"
  - "All 146 rewritten files re-validate cleanly via genre_sidecar.validate_sidecar() in their final corpora/ location"
  - "The diff changes only the cache_db_path values in those 146 files; no other field or file under corpora/ changes"
  - "The rewrite was promoted with lcats promote upsert (not replace) from a staging source (a 146-record tranche manifest, or a staging tree that also contains each story.json), after a reviewed --dry-run that reported exactly 146 records; corpora/ was not modified before the real upsert; and a unit test covers the rewrite logic"
  - "The real upsert ran only after explicit, separate, in-session human approval, given after the executor showed the exact file count and a sample diff"
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
  provenance. The backlog entry that described this work (added in PR #471)
  was removed from `project/design/backlog.md` by the planning PR that
  created this item.
- Sibling repos: none identified.
- External libraries: none.
- Recommendation: Proceed.

### Demand search
- Work items: none open.
- Proposals: none.
- Backlog: the PR #362 entry, which this item promotes.
- Recommendation: Proceed.

## Scope

- Write a small, tested one-off script that reads `corpora/*/*/genre.json`
  and writes rewritten copies (each assessment's `provenance.cache_db_path`
  reduced to its basename) into a staging location. It never edits
  `corpora/` in place.
- Promote the staged sidecars with `lcats promote upsert --sidecar genre`
  after reviewing a `--dry-run`, and only after explicit human approval.
- Re-validate every promoted file.

## Required Changes

- Add the rewrite script under `tools/` with a unit test covering absolute
  paths, already-basename values, missing `provenance`, and non-genre files.
- Stage the rewritten sidecars as either a 146-record JSONL tranche manifest
  (envelopes of `{"lcats_id": ..., "payload": ...}`) or a staging tree that
  contains each bucket's `story.json` as well as its rewritten `genre.json`.
  A `--source` tree of bare sidecars does not work: the live scan only
  recognizes buckets that contain `story.json`, and an empty scan exits
  successfully while promoting nothing.
- Run `lcats promote upsert --sidecar genre --dry-run` against the staging
  source and confirm it reports exactly 146 records. Treat 0, or any count
  other than 146, as a failure.
- Show the human the exact file count and a sample diff, and wait for
  explicit, separate, in-session approval before running the real `upsert`.
  Real promotion is a release-time human action
  (`docs/reference/corpus-promotion.md`).
- Re-validate all 146 files with `genre_sidecar.validate_sidecar()` in their
  final `corpora/` location.

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
- Promotion used `upsert` from a valid staging source after a reviewed
  `--dry-run` that reported exactly 146 records, `corpora/` was untouched until
  the real upsert, and a unit test covers the rewrite logic.
- The real `upsert` ran only after explicit, separate, in-session human
  approval, given after the file count and a sample diff were shown.

## Validation

- `scripts/test`
- `lrh validate`
- `git diff --stat origin/main`

## Risk Notes

- A dry-run or real `upsert` that scans zero records still exits `0`
  (`all_promoted` is `not self.rejected`). Always check the reported record
  count equals 146; do not rely on the exit code.
- Rewriting in place would change `corpora/` before review. Write to staging.
- `upsert` overwrites whole files, so the source tree must be exactly the
  current files with only that field changed. Compare before and after.
- Run the rewrite against a clean, up-to-date checkout so the 146 files match
  `main`.
- The editable `lcats` install can resolve to a sibling checkout; verify
  `lcats.__file__` before running the promotion.
