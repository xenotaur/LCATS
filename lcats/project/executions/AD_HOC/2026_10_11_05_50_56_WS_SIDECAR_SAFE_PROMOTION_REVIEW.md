---
execution_id: 2026_10_11_05_50_56_WS_SIDECAR_SAFE_PROMOTION_REVIEW
prompt_id: PROMPT(AD_HOC:WS_SIDECAR_SAFE_PROMOTION_REVIEW)[2026-10-11T05:30:41+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_10_11_04_45_10_WS_SIDECAR_SAFE_PROMOTION
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/496
session_transcript: pending
pr: https://github.com/xenotaur/LCATS/pull/496
commit: 
created_at: 2026-10-11T05:50:56+00:00
---

# Summary

Review-response round 1 on PR #496 (head fa9e9f89). Six threads (Codex P2, five Copilot), all verified against the files.

# Result

- Threads on the model assessment (PRRT_kwDOKlhIbM6rKa-8, ...KbIv, ...KbI_): valid, and my error. I had inspected assessments[0] only; every one of the 146 evidence records also holds an assess_story model assessment that reads the story file, and run_prefilter.py:1026-1030 already fingerprints the story for that reason. WI-PROMOTE-0118 and its execution record now treat the two assessments separately; the PR body and the memory note were corrected.
- ...KbI5: genre.json can be both tranche-promoted and pipeline-produced (lcats annotate); WI-PROMOTE-0117 scope and acceptance now require every applicable production path.
- ...KbJF: partly valid. The drift test exists (tests/dev_tests/build_genre_seed_manifest_test.py:105) but it is a CI-time unit test, not a release-time check, and the tool never reads corpora/; the wording now says so.
- ...KbJJ: stale "To be drafted" in WS-SIDECAR-SAFE-PROMOTION changed to Proposed.

# Validation

Docs and control-plane files only. lrh validate: 0 errors.

# Follow-up

Run confirm-fixes, wait for CI, substitute self-review of the final head, merge gate.
