---
id: WI-PROMOTE-0133
title: Build the release-time story-binding check for the seeded genre sidecars
type: deliverable
status: proposed
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams:
  - WS-SIDECAR-SAFE-PROMOTION
related_design:
  - project/design/genre-sidecar-story-binding.md
  - project/design/sidecar-kinds-release-rule.md
  - project/design/backlog.md
  - docs/reference/prepare-corpora-release.md
  - tools/build_genre_seed_manifest.py
  - experiments/05_metadata_genre_prefilter/archive_checkpoints.py
  - experiments/05_metadata_genre_prefilter/results/full_scan/story_hash_baseline.jsonl
  - project/work_items/resolved/WI-PROMOTE-0118.md
  - project/work_items/resolved/WI-PROMOTE-0124.md
depends_on:
  - WI-PROMOTE-0118
  - WI-PROMOTE-0124
blocked_by: []
blocked: false
blocked_reason: null
resolution: null
expected_actions:
  - read_files
  - create_file
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - edit_corpora
  - modify_validation_evidence
  - change_genre_sidecar_schema
  - change_promote_replace_semantics
  - implement_effective_input_hash
  - use_network
acceptance:
  - "A read-only tool, tools/check_genre_story_binding.py, compares the sha256 of each baseline story's story.json bytes under a given data/ root with the 146-row story_hash_baseline.jsonl. It exits 0 and prints nothing but a one-line ok summary when every story matches, and exits 1 listing every changed story, every baseline story missing from the root, and every story under the root that has a genre.json but is not in the baseline"
  - "Tests cover a match, changed bytes, a missing story, an extra story with a genre.json, an extra story without one (not reported), a malformed or duplicate baseline row, and the real 146-row baseline against the current corpora/ (all match). A test also asserts that the tool and archive_checkpoints.py verify agree, both passing and both failing on a changed story, when run on the real baseline. The tool never writes to the root it reads"
  - "docs/reference/prepare-corpora-release.md step 3b runs the check after the seed step and states the rule for a mismatch: stop; re-assess that story or record an owner-accepted exception; do not run replace past it silently"
  - "project/design/genre-sidecar-story-binding.md states in its status line that the recommendation is an adopted decision as of this work item, that the adopted form is the standalone tools/check_genre_story_binding.py (not the code-free runbook-only check its recommendation text describes), and that it no longer says the note changes no code. The recommendation text itself is otherwise unchanged"
  - "lrh validate reports 0 errors, and the changed tool and test paths are passed explicitly to format and lint"
required_evidence:
  - test_output
  - manual_review
  - lrh_validate
artifacts_expected:
  - tools/check_genre_story_binding.py
  - tests/dev_tests/check_genre_story_binding_test.py
  - docs/reference/prepare-corpora-release.md (check added to step 3b)
  - project/design/genre-sidecar-story-binding.md (status line only)
---

# Work Item: WI-PROMOTE-0133

## Summary

Build the half of the genre-sidecar story-binding decision that is still unbuilt: a
release-time, read-only check that the regenerated `data/` holds the same story
bytes the 146 seeded genre sidecars were assessed against. `WI-PROMOTE-0118`
recommended it and `WI-PROMOTE-0124` preserved the baseline it needs. This item adds
the comparison tool, tests, the runbook step, and promotes the recommendation to an
adopted decision.

## Problem / Context

The 146 seeded `genre.json` sidecars carry no story-text fingerprint, and the model
assessment in each reads the story text (`WI-PROMOTE-0118`). A release runs
`lcats gather` and then `lcats promote replace`; if a regenerated `story.json`
differs from the text that was assessed, the seeded sidecar is stale and nothing in
the runbook notices. `project/design/genre-sidecar-story-binding.md` recommends a
side manifest of baseline hashes compared with the regenerated `data/` at release
time, with no schema change and no change to `validate_sidecar` or `promote insert`.
The runbook says the check "is not built yet".

`WI-PROMOTE-0124` (PR #533) produced the baseline:
`experiments/05_metadata_genre_prefilter/results/full_scan/story_hash_baseline.jsonl`,
146 rows of `{lcats_id, story_content_hash, archive_path, archive_sha256}`, each hash
the sha256 of the `story.json` bytes at assessment time, taken from the archived Opus
checkpoints. All 146 equal the current `corpora/` bytes.

Design decisions, made at planning time:

- **A new standalone tool**, `tools/check_genre_story_binding.py`, beside
  `tools/build_genre_seed_manifest.py`, rather than a new subcommand of
  `experiments/05_metadata_genre_prefilter/archive_checkpoints.py`. That script's
  `verify --corpora <dir>` already hashes each story's `story.json` and compares it
  with the hash recorded in the archived Opus checkpoint (it also checks the baseline
  row against that same hash), but it also re-verifies the whole archive and the
  evidence file, which a release operator should not need. The tool reads only the
  baseline's `lcats_id` and `story_content_hash` fields. A test (an acceptance
  criterion) asserts the tool and `verify` agree on the real data, so the two cannot
  drift.
- **File bytes, not an effective-input hash.** File bytes are conservative: they also
  flag fields the assessment ignores, such as `year`, so the check can cause an
  unnecessary re-assess-or-accept decision but never miss a stale sidecar. The exact
  effective-input hash over `author`, `url` and body is deferred.
- **The mismatch rule is operator guidance, not automation.** The tool reports; the
  runbook says stop, re-assess or record an owner-accepted exception.

Prior art check:

- **Duplication search:** partial overlap only. `archive_checkpoints.py verify` does
  compare story bytes with the baseline, against `corpora/` and as part of a wider
  archive audit. Nothing compares the regenerated `data/`, and nothing is wired into
  the runbook. Decision recorded above: new tool, pinned to `verify` by a test.
- **Demand search:** the backlog entry "Build the release-time story-binding check
  for the seeded genre sidecars" and the Follow-ups list in
  `genre-sidecar-story-binding.md` request exactly this. The planning PR narrows the
  backlog entry; it does not remove it, because the `gather` reproducibility
  measurement stays open.

## Scope

1. A tool that reads the baseline and a `data/` root, hashes
   `<root>/<lcats_id>/story.json` as bytes, and reports changed, missing and
   unlisted-with-sidecar stories. Default baseline path is the tracked file; both
   paths are arguments.
2. Tests, including the real baseline against `corpora/`.
3. One runbook step in 3b, after the seed step, with the mismatch rule.
4. The binding note's status line only, which must also say the adopted form is the
   standalone tool and drop the "changes no code" wording.

## Required Changes

- Add `tools/check_genre_story_binding.py`: argparse, exit `0` on all matching, `1`
  on any reported problem, `2` on an unreadable or malformed baseline or an
  unreadable root. Duplicate `lcats_id` rows and rows missing either field are
  malformed. The tool reads the root and writes nothing.
- Add `tests/dev_tests/check_genre_story_binding_test.py` in the style of
  `tests/dev_tests/build_genre_seed_manifest_test.py`, covering the acceptance
  criteria, including the agreement test against `archive_checkpoints.py verify` on
  the real baseline; build fixture roots in a temporary directory.
- Edit `docs/reference/prepare-corpora-release.md` step 3b: add the command, its
  expected output, and the mismatch rule; update the sentence that says the check is
  not built yet. Keep the existing links and the two other read-only checks.
- Edit the status line of `project/design/genre-sidecar-story-binding.md` only: record
  the adopted decision and that its adopted form is the standalone tool, and remove
  "It changes no code". Leave the recommendation text unchanged.
- Run format and lint with the changed paths named explicitly.

## Non-Goals

- No effective-input hash over `author`, `url` and the body.
- No measurement of whether a fresh `lcats gather` reproduces the stored text; that
  stays in the backlog.
- No sidecar schema change, no change to `validate_sidecar`, `promote insert`,
  `promote replace` or the orphaned-sidecar guard.
- No automatic re-assessment, and no edit to `corpora/`, `data/`, the evidence file or
  the baseline.
- No change to `archive_checkpoints.py`.

## Acceptance Criteria

- The tool exits `0` with a one-line summary on a matching root, and exits `1` listing
  every changed, missing and unlisted-with-sidecar story otherwise.
- Tests cover a match, changed bytes, a missing story, an extra story with and without
  a `genre.json`, a malformed or duplicate baseline row, and the real baseline against
  the current `corpora/`.
- Step 3b runs the check after the seed step and states the mismatch rule.
- The binding note's status line records the adopted decision and names the standalone
  tool as its adopted form.
- A test shows the tool and `archive_checkpoints.py verify` agree on the real baseline.
- `lrh validate` reports 0 errors; changed paths are passed explicitly to format and
  lint.

## Validation

- `python -m unittest tests.dev_tests.check_genre_story_binding_test` from `lcats/`
- `python tools/check_genre_story_binding.py --root ../corpora` from `lcats/` exits 0
- `python tools/check_genre_story_binding.py --root ../corpora --baseline <copy with one hash altered>` exits 1
- `black --check tools/check_genre_story_binding.py tests/dev_tests/check_genre_story_binding_test.py`
- `ruff check tools/check_genre_story_binding.py tests/dev_tests/check_genre_story_binding_test.py`
- `lrh validate`

## Risk Notes

- File bytes also flag fields the assessment ignores, and a trailing-newline or
  whitespace difference will flag too. That is the conservative choice; the owner
  decides per story whether to re-assess or accept.
- The check proves the story bytes match the assessed text. It does not prove a
  sidecar was seeded for every story, which the orphaned-sidecar guard and the other
  read-only checks cover.
- `data/` after `lcats clean` and `lcats gather` has story files only for the
  regenerated collections; run the check after a full gather, or accept that
  baseline stories in other collections report as missing.
