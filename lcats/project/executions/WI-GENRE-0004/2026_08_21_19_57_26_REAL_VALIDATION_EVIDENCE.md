---
execution_id: 2026_08_21_19_57_26_REAL_VALIDATION_EVIDENCE
prompt_id: PROMPT(WI-GENRE-0004:REAL_VALIDATION_EVIDENCE)[2026-08-21T19:57:20+00:00]
work_item: WI-GENRE-0004
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/337
commit: 8f468116576d71e79e535bb4910bb8434a590d9a
agent: claude_app
instruction_source: WI-GENRE-0004
session_transcript: claude-app:b0d48070-0faf-4a35-942d-a29ec96d603a
created_at: 2026-08-21T19:57:26+00:00
---

# Summary

Ran WI-GENRE-0004's last remaining acceptance criterion: the real,
gated `claude-opus-4-8` validation pass over the full 146-story
genre-balanced selection, using the checkpoint-resilient
`--validate --run-real-validation` path landed in PR #334. Preceded by
a small real smoke test (3 stories, ~$0.41, separate scratch run) to
confirm the mechanics worked for real before the full spend, per the
user's own explicit go-ahead sequencing.

# Result

146/146 stories processed, 0 errors, 0 aborts, real cost $36.32 (vs.
the $34.01 pre-run estimate). Overall agreement between the
metadata-rule prefilter and the model's independent detection: 87.0%
(127/146). Fantasy/horror 100%, romance 70% and western 75% the
weakest genres - a real, measured gap now documented in
`WI-GENRE-0004.md`'s own new Findings section rather than left
unstated.

Landed via PR #337: the three evidence files
(`validation_results.jsonl`, `validation_summary.json`,
`validation_run_log.jsonl`) under
`experiments/05_metadata_genre_prefilter/results/full_scan/`, a
`.gitignore` entry for the per-story checkpoint state (mirrors
`run_census.py`'s existing pattern), and `WI-GENRE-0004.md` itself
moved from `proposed/` to `resolved/` with `status: resolved` and a
findings-grounded `resolution` string.

The smoke test's first attempt also incidentally re-confirmed the
fatal-abort fix from PR #334 for real: a stale worktree API key
produced a genuine 401, and the run aborted with exit code 3 and zero
tokens billed rather than a false success - the exact property that PR
fixed, now observed under a real failure, not a mock.

# Validation

- `lrh validate`: 0 errors, 164 pre-existing warnings (unchanged
  baseline).
- Manual verification: 146 lines in `validation_results.jsonl`,
  `aborted: false` / `error_count: 0` in `validation_summary.json`, run
  log event counts (`run_start`x1, `story_completed`x146, `run_end`x1)
  consistent with one clean pass.
- No application code changed in this PR (data + one WI markdown file
  only) - the code path itself (checkpointing, run log, exit codes,
  fingerprint) was already covered by PR #334's own test suite and
  self-review cycle, and exercised here for the first time against a
  real API key and the full real sample.

# Follow-up

- `WS-GENRE-EVIDENCE-SIDECARS` remains `proposed`, not closed - its
  governing proposal (`PROP-GENRE-EVIDENCE-SIDECARS`) is still
  `proposals/proposed/`, and the workstream likely has scope beyond
  this one WI (e.g. sidecar promotion into `corpora/`, explicitly out
  of scope here). Not evaluated for closeout in this pass.
- The romance/western agreement gap this run surfaced is a finding,
  not a fix - no follow-up WI opened yet for whether/how to address it;
  left for whoever next relies on metadata-rule labels for those two
  genres to decide.
- Status left `in_progress` pending PR #337 merge; update to `landed`
  and backfill this record's own PR/commit fields at closeout, per this
  session's established pattern.
