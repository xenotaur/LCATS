---
id: WI-GENRE-0077
title: Promote the validated genre-sidecar sample into corpora/
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
  - project/work_items/resolved/WI-GENRE-0004.md
  - project/work_items/proposed/WI-GENRE-0075.md
  - lcats/src/lcats/analysis/corpus/genre_sidecar.py
depends_on:
  - WI-GENRE-0075
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
  - run_network_or_cache_build_without_explicit_approval
  - promote_before_user_go_ahead
  - regenerate_or_modify_validation_evidence
acceptance:
  - "All 146 real, already-validated genre-sidecar-v1 records from experiments/05_metadata_genre_prefilter/results/full_scan/validation_results.jsonl are promoted into their corresponding corpora/ story directories as real genre.json files, using WI-GENRE-0075's tranche-promotion mode"
  - "Every promoted sidecar re-validates cleanly via genre_sidecar.validate_sidecar() in its final corpora/ location, not just as it sat in the experiment's own results directory"
  - "The promotion step makes no changes to any other file in the affected corpora/ collection directories"
  - "The underlying Opus assessment evidence itself is not regenerated or modified - this item only moves/promotes already-real, already-committed data"
  - "The promotion is only executed after explicit, separate, in-session human approval, showing the exact story/file count and a sample diff beforehand"
  - "scripts/test passes with no new failures"
  - "lrh validate reports 0 errors"
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - corpora/
  - experiments/05_metadata_genre_prefilter/results/full_scan/
---

# Work Item: WI-GENRE-0077

## Summary

Promote the real, already-validated 146-story `genre-sidecar-v1` evidence
from `WI-GENRE-0004`'s gated Opus validation run into `corpora/` as real
`genre.json` files, using the tranche-promotion mode `WI-GENRE-0075`
builds. This is the promotion half of Steps 5-6 of
`PROP-GENRE-EVIDENCE-SIDECARS`'s Implementation Plan (the selection and
validation half is already done).

## Problem / Context

`WI-GENRE-0004` produced real, committed evidence -
`experiments/05_metadata_genre_prefilter/results/full_scan/genre_balanced_manifest.jsonl`
(the 146-story genre-balanced selection),
`validation_results.jsonl` (146 real `genre-sidecar-v1` records, each
already validated via `genre_sidecar.validate_sidecar()` before being
written), and `validation_summary.json` (87.0% overall metadata-rule/model
agreement, with romance at 70% and western at 75% flagged as real,
measured weak spots). That PR's own body states this is
"Experiment-local only, per this item's own Non-Goals - not promoted into
`corpora/`." As of this item's creation, `find corpora/ -iname genre.json`
returns zero results anywhere in the real, tracked corpus (1880+ tracked
files under `corpora/`, none named `genre.json`).

### Duplication search
- In-repo: No existing genre-sidecar promotion into `corpora/` anywhere -
  confirmed via the `find` above.
- Sibling repos: None identified.
- External libraries: None - native LCATS corpus-promotion logic.
- Recommendation: Proceed, once `WI-GENRE-0075` lands.

### Demand search
- Work items: `WI-GENRE-0004` (resolved) produced the real evidence this
  item promotes; `WI-GENRE-0075` (proposed, this item's dependency)
  builds the promotion mechanism this item uses.
- Proposals: `PROP-GENRE-EVIDENCE-SIDECARS` requests this directly as
  Implementation Plan Steps 5-6.
- Workstreams: `WS-GENRE-EVIDENCE-SIDECARS` lists this as its own next
  step; still `status: proposed`, not yet closed. This item, once
  resolved, is expected to satisfy that workstream's sixth exit
  criterion ("Pilot and expanded sample genre.json sidecars are promoted
  to corpora/ and validated for the Worldcon paper workflow").
- Backlog: No matching entry found in `project/design/backlog.md`.
- Recommendation: Proceed, once the dependency lands.

## Scope

- Using `WI-GENRE-0075`'s tranche-promotion mode, promote all 146
  already-validated sidecar records into their corresponding `corpora/`
  story directories as real `genre.json` files.
- Verify post-promotion validity in place, not just pre-promotion validity
  in the experiment's own results directory.
- Confirm with whoever owns the Worldcon paper-analysis pipeline that the
  promoted files are actually consumable as expected.

## Required Changes

1. **Before starting**: confirm `WI-GENRE-0075` is resolved and merged.
   If it is not, stop and report rather than reimplementing its mechanism
   as a shortcut.
2. Using the new tranche-promotion mode, promote the 146 records from
   `experiments/05_metadata_genre_prefilter/results/full_scan/validation_results.jsonl`
   into `corpora/` - **only after explicit, separate, in-session human
   approval**, having shown the exact story/file count and a sample diff
   first.
3. Re-validate every promoted sidecar in its final `corpora/` location via
   `genre_sidecar.validate_sidecar()`.
4. Confirm no other file in any touched `corpora/` collection directory
   changed as a result of this promotion.

## Non-Goals

- Does not re-run or re-validate the underlying Opus assessment - that
  data is already real and already committed; this item only moves it.
- Does not implement the tranche-promotion mechanism itself - that is
  `WI-GENRE-0075`'s job, a hard dependency of this item.
- Does not touch `lcats annotate` or append any new assessments as part of
  this promotion (`WI-GENRE-0076` is separate, unrelated to this item).
- Does not expand the sample beyond the already-validated 146 stories.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- Explicit, separate, in-session human approval before the real promotion
  is executed and committed (this is a real, committed change to the
  tracked `corpora/` tree, not a fake-backend or dry-run-only step)

## Risk Notes

- This is the one item in this trio that writes to the real, tracked
  corpus. Treat it with the same real-artifact-commit discipline this
  project applies to every other irreversible-ish repo change - get a
  live human go-ahead before running the promotion for real, and show
  exactly what will change first.
- A promotion that silently reformats or subtly corrupts data on its way
  into `corpora/` would defeat the entire point of this item - the
  post-promotion re-validation step is not optional.

## Dependencies / Order

Depends on `WI-GENRE-0075` (sidecar-tranche promotion mode) - cannot start
its own real promotion step until that item is resolved and merged. No
dependency relationship with `WI-GENRE-0076` in either direction.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-GENRE-EVIDENCE-SIDECARS.md`
- Design: `project/design/proposals/proposed/genre-evidence-sidecars/00_proposal.md`
