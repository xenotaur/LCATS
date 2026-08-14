---
execution_id: 2026_08_14_02_12_52_WS_GPT_OSS_20B_CLOSEOUT_DOC_FIX
prompt_id: PROMPT(AD_HOC:WS_GPT_OSS_20B_CLOSEOUT_DOC_FIX)[2026-08-14T02:06:33+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/307
commit: c2273769ffb3ad5b2488bd40abed5aff35581642
created_at: 2026-08-14T02:12:52+00:00
agent: claude_app
instruction_source: user request to check WS-GPT-OSS-20B-EVALUATION exit criteria and close out if satisfied
session_transcript: claude-app:bfb89eee-a2d6-49d1-93e9-a1a9598bb26c
---

# Summary

Fix a real gap found while checking `WS-GPT-OSS-20B-EVALUATION`'s exit
criteria for closeout readiness: `WI-LLM-0066` (resolved via PR #298 by
a concurrent session) added a real genre-census scale-test finding for
`gpt-oss:20b` to `experiments/04_genre_census/README.md`, but never
cross-referenced it into `ollama_gpt_oss_20b/README.md` or the governing
proposal - the two files the workstream's own exit criterion names.

# Result

Added a "Genre-census scale-test follow-up (`WI-LLM-0066`)" section to
`experimental/model_comparison/ollama_gpt_oss_20b/README.md` and a
matching `### Decision 3 update (2026-08-13 ...)` section to
`project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md`
(style-matched to its existing `WI-LLM-0063`/`WI-LLM-0064` entries),
bumped `updated_on:` to 2026-08-14. All numbers (18/20 agreement, $0.00
cost, 801.5s/40.1s-per-story wall clock, ~20.8hr full-corpus projection,
the 2 humor disagreements) verified directly against
`experiments/04_genre_census/README.md`'s own source-of-truth section -
no new evidence generated, purely a cross-reference fix. Opened PR #307
against `main`.

Deliberately left `WI-LLM-0065`'s own separate, pre-existing gap in the
proposal doc (its Decision 3 update section is also missing) untouched -
out of scope for this specific fix, which was scoped only to the gap
identified against this workstream's exit criteria.

# Validation

- `lrh validate` - 0 errors, 143 pre-existing warnings (unrelated to
  either changed file).
- Diff-mode self-review (cold-context subagent) before this PR's first
  push, per this session's standing guidance to use self-review rather
  than manually retriggering GitHub bots. Verified every numeric claim
  against `experiments/04_genre_census/README.md` directly - no issues
  found, clean pass.
- Confirmed via `git diff origin/main -- .../common/harness.py` (empty)
  and `git status --short` that only the two intended markdown files
  were touched.

# Follow-up

- `WI-LLM-0065`'s own proposal-doc Decision-3-update gap remains open -
  a separate, pre-existing issue from a different session's work, not
  fixed here.
- After this PR lands, `WS-GPT-OSS-20B-EVALUATION`'s exit criteria
  should be re-checked and the workstream closed if all 3 are now met.
