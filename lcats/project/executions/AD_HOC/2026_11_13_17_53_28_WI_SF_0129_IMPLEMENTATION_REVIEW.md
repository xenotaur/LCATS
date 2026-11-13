---
execution_id: 2026_11_13_17_53_28_WI_SF_0129_IMPLEMENTATION_REVIEW
prompt_id: PROMPT(AD_HOC:WI_SF_0129_IMPLEMENTATION_REVIEW)[2026-11-13T17:53:28+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_11_13_00_18_09_WI_SF_0129
pr: https://github.com/xenotaur/LCATS/pull/553
commit: b99251454b609d3cb1788146cc32f8388b5889f7
created_at: 2026-11-13T17:53:28+00:00
agent: claude_app
instruction_source: project/work_items/proposed/WI-SF-0129.md
session_transcript: claude-app:dff6f127-44db-417c-9b1e-0f962af4c00a
---

# Summary

Review response for PR 553 (WI-SF-0129), two rounds. Round one answered the hosted Codex and Copilot threads on the first push. Round two answered a cold-context PR-mode substitute review of the round-one fixes. Each round was triaged and shown to the user, who approved before any edit.

# Result

Round one (approved, fixed in `423ceb7c`):
- A typographic apostrophe ("doesn’t") bypassed the negation guard, so a negated claim could be `table_confirmed`. Fixed by normalising apostrophes before matching.
- A `counterfactual_divergence` premise was compared although its timeline describes the enabling mechanism. It is now `not_comparable`.
- A repeated standing (the final standing also holding earlier) was mis-compared. The audit now uses the start of the trailing run of equal standings, and relabels the periods in that run.
- A confirmation reason listed an unopened source. It now lists opened sources only.

Round two (approved, fixed in `a5dd6ceb`; reviewer found no blocker):
- The negator list was incomplete (lack, hardly, none, anything but and similar forms let an opposite claim be audited). Widened, each form tested, and the over-blocking of "little" and "less than" is documented as a missed audit only.
- Stale prose said "final period only": the PR body, the runbook (which also omitted the `not_comparable` cases), two test names and an awkward docstring wrap. All corrected.

Left alone, by design: a timeline such as contradicted, then open, then contradicted from 1965-07 is confirmed, because only the final standing and its boundary are enforced. This is documented.

# Validation

With the LCATS env first on PATH: scripts/test 3206 OK, black 25.11.0 and ruff 0.15.0 clean, `lrh validate` 0 errors (366 warnings, none mentioning these files), `git diff --check` clean. A first run under the default PATH used black 26.3.1 and base Python, which failed a subprocess test; that was environment drift, not the change. No hosted bot was retriggered and no model was called.

# Follow-up

Re-read all five review threads on the final head, resolve them, record the confirm pass, re-check CI, then the merge ask.
