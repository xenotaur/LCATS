---
execution_id: 2026_08_22_20_32_49_REAL_LOCAL_MODEL_RUN_EVIDENCE
prompt_id: PROMPT(WI-LLM-0074:REAL_LOCAL_MODEL_RUN_EVIDENCE)[2026-08-22T20:32:41+00:00]
work_item: WI-LLM-0074
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/361
commit: c94cf9de893d02d3e6d3d0baae056e41f00c34cd
agent: claude_app
instruction_source: WI-LLM-0074
session_transcript: claude-app:b0d48070-0faf-4a35-942d-a29ec96d603a
created_at: 2026-08-22T20:32:49+00:00
---

# Summary

Ran WI-LLM-0074's own deliberately-deferred acceptance criterion: the
real, gated `gpt-oss:20b` (via Ollama) validation pass over the full
146-story genre-balanced sample, using the local-backend wiring landed
in PR #349. Preceded by a 3-story smoke test (separate scratch run) to
confirm the mechanics worked for real before the full run.

# Result

146/146 stories processed, 0 errors, 0 aborts, real cost $0, real
measured wall-clock 111.5 minutes (from the run log's own
`run_start`/`run_end` timestamps). Computed the actual three-way
comparison directly from the two committed `validation_results.jsonl`
files: `gpt-oss:20b` agrees with Opus directly 69.9% of the time
(102/146) - reliable for horror/science-fiction/mystery/adventure
(80-95%), not safe for fantasy/romance/humor/western (50-60%, tends to
default to a generic "other" label rather than a wrong-but-specific
genre).

**Correction (later commit on this same PR, `cae8ece2`):** a review
finding (Copilot) caught a real bug - `gpt-oss:20b` returned
`"science_fiction"` (underscore) instead of the canonical
`"science fiction"` for 3/146 stories, silently miscounted as
disagreements. Fixed at the source
(`assess._canonicalize_detected_genre()`) and re-run for just those 3
stories. **Corrected figure: 71.2% (104/146)** local-vs-Opus agreement
- this section's own number above is left as originally written (not
silently edited) per this project's convention of noting corrections
explicitly rather than rewriting history; see the `_CONFIRM` record and
`WI-LLM-0074.md`'s own Findings section for the fully corrected
write-up.

Landed via PR #361: the three evidence files
(`validation_gpt_oss_20b_http_localhost_11434_v1_results.jsonl`/
`_summary.json`/`_run_log.jsonl`) under
`experiments/05_metadata_genre_prefilter/results/full_scan/`, a real
`.gitignore` fix (the existing checkpoint-ignore pattern stopped
matching once PR #349's checkpoint-collision fix started qualifying the
checkpoint filename by backend/endpoint - this run surfaced that gap
live, 146 checkpoint directories showed up as untracked before the
fix), and `WI-LLM-0074.md` itself moved from `proposed/` to `resolved/`
with a findings-grounded `resolution` string.

# Validation

- `lrh validate`: 0 errors, 204 pre-existing warnings (baseline drifted
  up from concurrent unrelated landings this session, not from this
  change).
- Manual verification: 146 lines in the local `validation_results.jsonl`,
  `aborted: false`/`error_count: 0` in the local summary, run log event
  counts (`run_start`x1, `story_completed`x146, `run_end`x1) consistent
  with one clean pass.
- `.gitignore` fix verified directly: `git status --short` showed all
  146 local checkpoint directories (both Opus and gpt-oss) correctly
  hidden after the fix, with only the 3 real evidence files remaining
  untracked before staging.

# Follow-up

- `WS-GENRE-EVIDENCE-SIDECARS` still has other open scope (human
  adjudication, event-extraction reassessment) beyond this WI - not
  evaluated for closeout here.
- The romance/humor/fantasy/western local-model weakness this run
  surfaced is a finding, not a fix - no follow-up WI opened yet; left
  for whoever next considers using `gpt-oss:20b` as a cost-saving
  pre-filter for those genres specifically.
