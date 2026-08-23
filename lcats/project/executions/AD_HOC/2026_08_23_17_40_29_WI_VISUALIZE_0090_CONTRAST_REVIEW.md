---
execution_id: 2026_08_23_17_40_29_WI_VISUALIZE_0090_CONTRAST_REVIEW
prompt_id: PROMPT(AD_HOC:WI_VISUALIZE_0090_CONTRAST_REVIEW)[2026-08-23T17:40:23+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/380
commit: 
created_at: 2026-08-23T17:40:29+00:00
agent: claude-sonnet-5
instruction_source: https://github.com/xenotaur/LCATS/pull/380
session_transcript: pending
---

# Summary

Review-response round for PR #380 (`WI-VISUALIZE-0090`). Two review
comments landed after the PR's first push (Codex, Copilot); both
triaged as valid, in-scope findings and fixed.

# Result

- **Codex (P2):** the dogfood README (`experiments/08_visualize_dogfood/README.md`,
  "Salience vs. contrast" section) claimed `said`/`not`/`all` were
  "filtered out entirely" under `--contrast`. Verified against the actual
  committed `tfidf_contrast_fantasy/tfidf_manifest.json`: `said` has a
  positive contrast score and ranks 3rd, `not` is positive and ranks 9th
  -- both retained, only demoted, not filtered. Independently recomputed
  `all`'s actual (unfiltered, untruncated) contrast score directly against
  the real corpus: 0.014, also positive -- it simply falls outside the
  top-20 cutoff, not filtered to zero either. Rewrote the paragraph to
  state this accurately (demoted vs. filtered, with each term's real
  rank/status).
- **Copilot:** `docs/reference/cli-commands.md`'s `tfidf` section reads as
  internally contradictory to a skimming reader -- the top description
  (verbatim `--help` text, by this file's own established convention) says
  genre-subset runs rank "distinguishing" terms, and only the Accuracy
  note below qualifies that this is true only with `--contrast`. Added a
  one-line forward-reference immediately after the description and before
  the Accuracy note, without altering the verbatim `--help`-matching text
  itself.

# Validation

- `scripts/format --check --diff`, `scripts/lint`: clean.
- `lrh validate`: 0 errors.
- Both fixes independently re-verified against real data/files (manifest
  JSON, a direct unfiltered recomputation of the `all` contrast score)
  before being accepted, not just taken from the reviewer comments at
  face value.

# Follow-up

- None -- both findings fully addressed in this round.
