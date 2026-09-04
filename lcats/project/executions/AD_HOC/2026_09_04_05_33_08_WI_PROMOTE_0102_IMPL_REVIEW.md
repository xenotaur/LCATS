---
execution_id: 2026_09_04_05_33_08_WI_PROMOTE_0102_IMPL_REVIEW
prompt_id: PROMPT(AD_HOC:WI_PROMOTE_0102_IMPL_REVIEW)[2026-09-04T05:32:55+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_09_04_05_27_55_WI_PROMOTE_0102
pr: https://github.com/xenotaur/LCATS/pull/427
commit: 4eb05c27
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/427
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
created_at: 2026-09-04T05:33:08+00:00
---

# Summary

Review-response round for PR #427 (`WI-PROMOTE-0102` implementation).
The PR's automatic first-push review surfaced 1 real finding from
`chatgpt-codex-connector`.

# Result

- **Recommendation section mischaracterized replace's own pre-flight
  logic (real bug, fixed)**: the design note's Recommendation section
  stated that *all* of `replace`'s pre-flight validation is "recognizing
  an already-obsolete file shape" -- contradicted by the note's own
  "What was verified" section, which correctly documents that two call
  sites (v1-`genre.json` `validate_sidecar()`, the `scenes.json`
  required-key check) are real validation of currently-produced content,
  not legacy-shape detection. Independently re-verified the finding is
  real before fixing (re-read both sections side by side). Fixed by
  splitting the exemption into two distinct, accurately-labeled grounds:
  `is_legacy_flat_sidecar()`'s shape-detection call is structurally
  irreducible; `replace`'s current-format validation is technically
  routable but exempted by `WI-PROMOTE-0097`'s own documented design
  choice (replace never validates through the registry, per
  `sidecar_validators.py`'s own docstring). Updated both proposed
  replacement-wording blocks to match the corrected reasoning.

# Validation

- `lrh validate`: 0 errors.
- Direct re-read of the note's own prior sections to confirm the
  mischaracterization and the fix's internal consistency.

# Follow-up

- None outstanding from this round. Proceeding to confirm-fixes next.
