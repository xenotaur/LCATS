---
execution_id: 2026_11_11_07_08_54_WI_SF_0128_IMPLEMENTATION_REVIEW
prompt_id: PROMPT(AD_HOC:WI_SF_0128_IMPLEMENTATION_REVIEW)[2026-11-11T07:08:54+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_11_11_05_31_36_WI_SF_0128
pr: https://github.com/xenotaur/LCATS/pull/547
commit: e89b3dcff9e0a14863297173fc64580b4f457771
created_at: 2026-11-11T07:08:54+00:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/547
session_transcript: claude-app:dff6f127-44db-417c-9b1e-0f962af4c00a
---

# Summary

Address the review findings on PR 547 (WI-SF-0128, composition-date source tooling and the source evaluation): one Copilot thread. Codex reviewed the first head and reported no findings. The finding was verified against the report and the code and shown to the owner as a triage before any edit; the owner approved the docs-only fix.

# Result

Copilot, one thread (composition_date_source_evaluation.md): the report said a documented writing date "would be a lower bound only if the owner records it", which conflates commencement with completion, and following it by entering only an earliest date discards the computed upper bound because owner entries replace the interval. Both halves were valid. Reproduced: an owner entry of earliest 1926 over a 1928-02 publication and a 1937 death yields 1926 to unbounded. Fixed in ea056143 with no behaviour change: the report now distinguishes a completion date (an upper bound, tighter than publication), a commencement date (a lower bound) and a known range, flags a bare "written" date such as Cthulhu's "summer 1926" for the owner to classify, and states that an owner entry replaces the whole interval so both bounds should be supplied; the module docstring carries the same warning, and a new test pins the replace-not-merge behaviour.

Not changed: making an owner entry merge missing bounds from the computed interval, which would contradict the work item and the proposal ("owner override replaces the result"). It remains an option for the owner.

# Validation

Black, ruff, scripts/test (3147 tests OK) and lrh validate (0 errors, 360 existing warnings, unchanged from main) passed on ea056143. No second cold review pass was run for this one-thread documentation wording fix; no hosted bot was retriggered. The thread is left for confirm-fixes to resolve.

# Follow-up

Wiring the owner-dates file into the runner (WI-SF-0131) and the owner's nine hand checks in the report remain open.
