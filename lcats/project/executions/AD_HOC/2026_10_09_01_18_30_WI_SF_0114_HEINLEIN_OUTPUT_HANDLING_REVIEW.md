---
execution_id: 2026_10_09_01_18_30_WI_SF_0114_HEINLEIN_OUTPUT_HANDLING_REVIEW
prompt_id: PROMPT(AD_HOC:WI_SF_0114_HEINLEIN_OUTPUT_HANDLING_REVIEW)[2026-10-09T01:17:41+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_10_09_00_03_38_WI_SF_0114_HEINLEIN_OUTPUT_HANDLING
pr: https://github.com/xenotaur/LCATS/pull/488
commit: 35061a703d92635cbd28a74797510207a1a79a2f
created_at: 2026-10-09T01:18:30+00:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/488
session_transcript: pending
---

# Summary

Review-response round for PR 488 (WI-SF-0114). Six open Codex and Copilot threads (four distinct findings) were triaged against the work item and the code, and the owner approved the fixes, choosing to reuse the shared strict fenced-JSON helper for finding 2.

# Result

- Fixed (two threads each from Copilot and Codex): item 1 still said the fail-loud rule awaited the owner and allowed an alias map, contradicting the acceptance criteria. Fail loudly is now recorded as the final owner-approved decision, the alias-map allowance and its Risk Note are removed.
- Fixed (Copilot): an accepted coercion had no place in the analysis contract (models.py:441-452, pipeline.py:263-280, rendering.py:1110-1125). Instead of expanding the contract, the item now reuses lcats.utils.extract_json with a new default-off strict_fence option, applied in the runner's existing text fallback (run_worldcon_spike.py:824-846), records each unwrap as a run-log event, and adds helper tests. No contract or sidecar field is added.
- Fixed (Copilot and Codex, three threads): the required local probe conflicted with the forbidden live trials. It is now an investigation from persisted artifacts, the backend code and documentation, with any unresolved question deferred to the canary rerun.
- Fixed (Copilot): Validation now includes direct black and ruff checks on run_worldcon_spike.py and the helper tests.
- The run logs also showed the text fallback was taken in all three Vonnegut evidence stages of the trials, which the Problem section now records. Fix commit: 35061a703d92635cbd28a74797510207a1a79a2f.

# Validation

- lrh validate reported 0 errors; lrh work-items readiness reported prompt_ready: yes.

# Follow-up

- Run confirm-fixes, then the merge and closeout ask.
- Update session_transcript from pending at closeout.
