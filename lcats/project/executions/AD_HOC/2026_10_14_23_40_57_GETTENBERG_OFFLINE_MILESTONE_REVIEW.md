---
execution_id: 2026_10_14_23_40_57_GETTENBERG_OFFLINE_MILESTONE_REVIEW
prompt_id: PROMPT(AD_HOC:GETTENBERG_OFFLINE_MILESTONE_REVIEW)[2026-10-14T23:39:22+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_10_14_20_45_26_GETTENBERG_OFFLINE_MILESTONE
pr: https://github.com/xenotaur/LCATS/pull/508
commit:
created_at: 2026-10-14T23:40:57+00:00
agent: codex_app
instruction_source: project/development/gettenberg-offline-milestone.md
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
---

# Summary

Address all seven PR508 review comments and the human-approved placement plan.
Human approval in this session covers the displayed repair plan, stabilization,
main landing and partial closeout; no persistent consent/profile change. PR/base
identity verified at 1ea2ece8. Installed gates are fresh; stored skip consent is
invalid, so explicit task authorization is used. Routine verified repairs are
part of this approved task rather than a renewal of the completed pilot runs.

# Result

Document four-way repository convention, relocate 5 qualification runners and 9
archival measurements with original hashes, improve entry points/commentary,
fence how-to sessions, preserve strict JSON and reject non-UTF-8 archive paths
before copying/building, retain qualification checks under python -O, and resolve
candidate paths before SQLite URI conversion. Explain repeated predicate URLs
as diagnostic multiplicity, not repeated requests, in the experiment README.
Original measurements remain byte-identical. Historical record bodies unchanged;
relocation maps and current navigation resolve their original references.

# Validation

All 2,675 canonical tests and 197 focused tests passed. Canonical formatting/lint,
explicit experiment formatting/lint, LRH validation (0 errors, 351 existing
warnings), and diff checks passed. Nine measurement hashes and 24 current local
links verified. See repair-validation.json in milestone evidence for log hashes. The Mac filesystem
rejects an undecodable filename before the library; direct boundary inspection
confirmed serialization risk. Cross-platform regression verifies invalid path
rejection before source I/O and before candidate/archive writes. Initial broad
JSON-escaping idea failed two existing contract tests and was replaced by the
review's supported early-rejection alternative, preserving the original contract.

# Follow-up

Independent current-head review, required CI, exact-head merge and partial native
closeout of four delivered WIs and linked records. No workstream/design/release
closure or WI-0005 execution. Preserve internal PR attribution.
