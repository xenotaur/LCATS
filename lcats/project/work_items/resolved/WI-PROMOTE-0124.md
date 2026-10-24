---
id: WI-PROMOTE-0124
title: Archive the Opus and gpt-oss checkpoint files for the 146 genre-evidence stories and derive the baseline-hash manifest from them
type: deliverable
status: resolved
priority: high
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams:
  - WS-SIDECAR-SAFE-PROMOTION
related_design:
  - project/design/genre-sidecar-story-binding.md
  - project/design/backlog.md
  - experiments/05_metadata_genre_prefilter/README.md
  - experiments/05_metadata_genre_prefilter/run_prefilter.py
  - experiments/05_metadata_genre_prefilter/results/full_scan/validation_results.jsonl
  - project/work_items/resolved/WI-PROMOTE-0118.md
depends_on:
  - WI-PROMOTE-0118
blocked_by: []
blocked: false
blocked_reason: null
resolution: 'Implemented and merged in PR #533: experiments/05_metadata_genre_prefilter/archive_checkpoints.py archives the 146 Opus and 146 gpt-oss:20b validation checkpoints (292 byte-identical files, 327,005 bytes) as tracked evidence under results/full_scan/checkpoint_archive_2026-08-21/, nested by lcats_id and renamed so .gitignore is unchanged, with a per-file sha256 index and README, and derives story_hash_baseline.jsonl (146 rows) from the archived Opus files only. Verified: all 292 copies equal the originals, every hash equals the archived Opus fingerprint, the current corpora story.json sha256 and the gpt-oss hash, and each archived Opus model_assessment equals the committed one in full; 35 tests including real-archive and ignore-status tests. The originals were not touched. Not done by design: the release-time comparison check and the file-bytes versus effective-input hash decision.'
expected_actions:
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
  - implement_release_check
  - delete_or_move_originals
acceptance:
  - "The 146 Opus validation.json checkpoints and the 146 gpt-oss:20b validation_openai_http_localhost_11434_v1.json checkpoints are archived byte-identical to the originals, nested by lcats_id as <archive>/<collection>/<story>/opus-checkpoint.json and gpt-oss-20b-checkpoint.json, with a per-file sha256 index, and the originals are untouched"
  - "git check-ignore reports none of the 292 archived paths as ignored, and the .gitignore file is not modified"
  - "A baseline manifest of exactly 146 rows {lcats_id, story_content_hash} has unique lcats_ids equal to those in validation_results.jsonl, with every hash taken from the archived Opus file's fingerprint and not from the live corpora; the gpt-oss files are not used to build it"
  - "Tests fail on drift: the manifest equals the archived Opus fingerprints; every hash equals the sha256 of the current corpora story.json bytes; each archived Opus data.model_assessment equals the committed model assessment in full (the whole object, not selected fields such as generated_at or input_tokens); each gpt-oss hash equals the Opus hash for the same story; archived files still match the sha256 index"
  - "A README beside the archive records the provenance (run ids, models, the source worktree, hash basis = sha256 over story.json bytes, the file-name mapping, and that the double underscore in 84 story names makes names unsafe to parse backwards)"
  - "lrh validate reports 0 errors, and the changed experiment paths are passed explicitly to format, lint and the experiment tests"
required_evidence:
  - test_output
  - manual_review
  - lrh_validate
artifacts_expected:
  - experiments/05_metadata_genre_prefilter/results/full_scan/checkpoint_archive_2026-08-21/ (292 archived checkpoint files, a sha256 index and a README)
  - experiments/05_metadata_genre_prefilter/results/full_scan/story_hash_baseline.jsonl (146-row baseline manifest)
  - experiments/05_metadata_genre_prefilter/ script that archives and derives the manifest, with tests and a bridge test under tests/
---

# Work Item: WI-PROMOTE-0124

## Summary

Make the original per-story text hashes of the genre evidence durable. The 146
Opus checkpoint files, and the 146 local-model checkpoint files beside them, exist
only as gitignored files in one detached-`HEAD` sibling worktree. Archive both
sets as tracked evidence and derive the genre-sidecar baseline-hash manifest from
the archived Opus files. This is the first follow-up recommended by
`WI-PROMOTE-0118` (`project/design/genre-sidecar-story-binding.md`), and it is
time-sensitive.

## Problem / Context

`WI-PROMOTE-0118` found that each genre sidecar's model assessment depends on the
story text, and that the original `story_content_hash` for every one of the 146
stories survives, but only in per-story checkpoint files under
`experiments/05_metadata_genre_prefilter/results/full_scan/<collection>__<story>/`
in the sibling worktree `lcats-special-char-strategy-c18aa7`:

- `validation.json`: the Opus run (`claude-opus-4-8`, run id
  `2026-08-21T18:55:51.831553Z`). Each carries `fingerprint.story_content_hash`
  (sha256 over `story.json` bytes) and `data.model_assessment`, which equals the
  committed model assessment in full (the whole object) for all 146. All 146
  hashes equal the sha256 of today's `corpora/<lcats_id>/story.json`. 159,630 bytes.
- `validation_openai_http_localhost_11434_v1.json`: a second full run of the same
  146 stories with `gpt-oss:20b` over Ollama (`WI-LLM-0074`, PR #361), same hashes,
  167,375 bytes, all outcomes `success`. Its results, run log and summary are
  committed, but without any hash, exactly like the Opus run.

`.gitignore:137` (`experiments/05_metadata_genre_prefilter/results/**/*__*/validation*.json`)
deliberately keeps these scratch files out of git, matching on the directory name.
The committed results contain no hash, and no other copy exists on the machine. A
fresh clone, `git clean -fdx` or removing that worktree loses them. Re-running the
Opus assessments cost about $36.32 originally and would not reproduce the same
outputs; a local re-run is cheap but not guaranteed identical.

The two sets are archived together because it is not yet known whether the
gpt-oss evidence will be needed, and the marginal cost is about 167 KB.

Layout, decided: nest by `lcats_id` and rename the file, so the archive path is the
same join key as `corpora/<lcats_id>/story.json`. 84 of the 146 story names (all in
`mass_quantities`) contain `__`, and the ignore rule matches on a directory name
containing `__` plus a file name starting `validation`, so a plain nested copy of
`validation.json` would be ignored for those 84. Checked with `git check-ignore`:
`<collection>/<story>/<renamed file>` is not ignored, so no `.gitignore` change is
needed and the ignore rule keeps doing its intended job for live scratch checkpoints.

Prior art check:

- **Duplication search:** no archive of these checkpoints exists. `story_content_hash`
  appears in tracked code only in `run_prefilter.py`, and in no tracked data.
- **Demand search:** the backlog entry "Preserve the 146 original story hashes and
  add a release-time story-binding check ..." and the follow-up list in
  `genre-sidecar-story-binding.md` request exactly this. Offer to remove or narrow
  the backlog entry when this item is promoted; do not edit it automatically.

## Scope

1. Copy the 146 Opus and 146 gpt-oss checkpoint files byte-for-byte from the
   source worktree into a tracked archive directory under
   `experiments/05_metadata_genre_prefilter/results/full_scan/`, nested by
   `lcats_id`, renamed to `opus-checkpoint.json` and `gpt-oss-20b-checkpoint.json`.
   Build the mapping forward from the 146 `lcats_id`s in `validation_results.jsonl`
   (directory = `lcats_id` with `/` replaced by `__`), never by parsing names.
2. Write a per-file sha256 index so anyone can later verify the archive against the
   originals as copied.
3. Derive a baseline manifest of `{lcats_id, story_content_hash}` for the 146 from
   the archived Opus files, recording the archived file and its sha256 per row.
4. Add tests and a README (see Required Changes).

## Required Changes

- A script in `experiments/05_metadata_genre_prefilter/` that (a) archives from a
  given source directory, refusing to overwrite an existing file with different
  content and never modifying or removing the source, and (b) builds and verifies
  the manifest from the archive. Stop and report if any of the 292 source files is
  missing.
- Tests in the experiment's existing style, wired through a bridge test under
  `tests/`, covering the drift conditions in the acceptance criteria.
- A README beside the archive with the provenance, the file-name mapping, the hash
  basis, and the naming caveat.
- Run format, lint and the experiment tests with the changed experiment paths named
  explicitly; `scripts/format` and `scripts/lint` do not cover `experiments/`.

## Non-Goals

- No release-time comparison check; that is a separate follow-up.
- No sidecar schema change.
- No edit to `validation_results.jsonl`, the committed gpt-oss results, or `corpora/`.
- No decision between file bytes and an effective-input hash; this item records only
  that the recovered values are sha256 over `story.json` bytes.
- No change to `.gitignore`, and no deletion, move or modification of the originals
  in the sibling worktree.
- No use of the gpt-oss files to build the manifest.

## Acceptance Criteria

- The 146 Opus and 146 gpt-oss checkpoints are archived byte-identical, nested by
  `lcats_id`, with a per-file sha256 index, and the originals are untouched.
- `git check-ignore` reports none of the 292 archived paths as ignored, and
  `.gitignore` is unchanged.
- The baseline manifest has exactly 146 rows with unique `lcats_id`s equal to those
  in `validation_results.jsonl`, each hash taken from the archived Opus fingerprint.
- Tests fail on drift in any of the conditions listed in the frontmatter.
- A README records the provenance and the caveats.
- `lrh validate` reports 0 errors, and the changed experiment paths were passed
  explicitly to format, lint and the experiment tests.

## Validation

- lrh validate
- git diff --stat main
- git check-ignore -q experiments/05_metadata_genre_prefilter/results/full_scan/checkpoint_archive_2026-08-21/mass_quantities/the_courting_of_lady_jane__bacon/opus-checkpoint.json (must exit 1: not ignored)
- scripts/test
- the changed experiment paths passed explicitly to black and ruff, and the experiment tests run

## Risk Notes

Time-sensitive: execute soon. The sibling worktree is on a detached `HEAD` and
holds the only copies; if any source file is missing at execution time, stop and
report instead of reconstructing it. A forced add or a `.gitignore` negation would
also work but leaves the ignore rule fighting the archive and risks un-ignoring live
scratch checkpoints, which `.gitignore:137`'s comments record as a past review
finding, so the renamed-file layout is used instead. The archive is small
(about 327 KB for 292 files). Do not use `git add -A` blindly in the experiments
tree; add the archive paths explicitly and confirm with `git status`.
