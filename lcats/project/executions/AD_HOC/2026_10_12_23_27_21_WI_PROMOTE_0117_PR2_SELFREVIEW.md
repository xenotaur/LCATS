---
execution_id: 2026_10_12_23_27_21_WI_PROMOTE_0117_PR2_SELFREVIEW
prompt_id: PROMPT(AD_HOC:WI_PROMOTE_0117_PR2_SELFREVIEW)[2026-10-12T23:27:03+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_10_12_06_38_19_WI_PROMOTE_0117
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/499
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
pr: https://github.com/xenotaur/LCATS/pull/499
commit: 0b1f17090323a3279d63859d499a6a72370f7b12
created_at: 2026-10-12T23:27:21+00:00
---

# Summary

PR-mode substitute self-review of PR #499 at head e387281e (cold subagent; no hosted-bot retrigger). The bots had reviewed only fafa7808 and 3fb0f5f3. This is the second cold pass on the PR; the first, in diff-mode before the first push, is the _SELFREVIEW record created then.

# Result

No high or medium findings. The reviewer re-ran all nine reproduction rows in a fresh scratch tree with PYTHONPATH set to this checkout, ran both runbook shell checks verbatim in a scratch layout mirroring the repository (and check 1 against the real repo, where it prints nothing), confirmed the destination-only skip and its test, the four-kind registry, exactly two unregistered per-story sidecars after listing every .json literal and the name-building cases, the legacy-flat refusal in upsert mode, and that no code, corpora/ or data/ change was made. Five low findings, all verified and fixed in 6c737df5: the row 8 wording ("prints nothing" became "prints no warning"), a stale not-reproduced caveat now covered by row 9, three line cites that were off by a few lines (promote.py:406-409, runner.py:517-518, and the lexicon write at runner.py:368), a missing mention of the per-item checkpoint json files, and a note that two story-list examples in the how-to do not name data/. The merged head 6c737df5 differs from the reviewed head only by those corrections to the note and the review record, which I checked myself and the cold reviewer did not see.

# Validation

lrh validate 0 errors; CI 4/4 on the merged head 6c737df5, with the check count verified because the first poll saw only one check.

# Follow-up

None for this record.
