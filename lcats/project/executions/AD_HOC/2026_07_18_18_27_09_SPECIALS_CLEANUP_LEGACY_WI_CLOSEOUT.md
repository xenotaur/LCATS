---
execution_id: 2026_07_18_18_27_09_SPECIALS_CLEANUP_LEGACY_WI_CLOSEOUT
prompt_id: PROMPT(AD_HOC:SPECIALS_CLEANUP_LEGACY_WI_CLOSEOUT)[2026-07-18T18:20:33-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/133
commit: 
created_at: 2026-07-18T18:27:09-04:00
agent: claude_app
instruction_source: user request following a clean lcats survey / lcats promote --dry-run result from their manual dogfood run of prepare-corpora-release.md
session_transcript: pending
---

# Summary

Record the maintainer's real, literal dogfood-run confirmation that the
special-character pipeline works end to end (EV-0003), and resolve the
three legacy work items (WI-SPANOPS-0002, WI-REVIEW-0003, WI-APPLY-0005)
adopted by WS-SPECIALS-CLEANUP but never in its own burn-down scope.

# Result

- Verified before writing anything: read `span_ops.py`, `review.py`,
  `application.py` in full and confirmed each satisfies its
  corresponding WI's acceptance criteria line by line (span operation
  schema with deterministic ordering and provenance; explicit
  PENDING/APPROVED/REJECTED/OVERRIDDEN review states with mandatory
  rationale; pure, non-mutating application with considered/applied/
  skipped audit reports). Ran the existing test suites for all three
  (`span_ops_test.py`, `review_test.py`, `application_test.py`) --
  24 tests, all passing -- before treating "acceptance criteria met" as
  established rather than asserted.
- `project/evidence/EV-0003.md` (new): documents the maintainer's
  confirmed clean `lcats survey --mode specials` (exit 0, no output)
  and clean `lcats promote --dry-run` (all 12 collections, zero
  `blocked:` lines) from a literal, non-simulated run -- explicitly
  framed as closing the gap EV-0002's own Confidence section named
  ("the maintainer operational step to confirm end-to-end").
- Resolved WI-SPANOPS-0002/WI-REVIEW-0003/WI-APPLY-0005: `status: active`
  -> `resolved`, `resolution:` set, moved `active/` -> `resolved/`.
- Added a 2026-07-18 `project/memory/decision_log.md` entry and a
  `project/design/design.md` State and Persistence Boundary bullet
  explicitly deciding to keep (not delete) the span-op/review/apply
  code as unused-until-needed infrastructure for a future per-instance
  review need, not dead code awaiting completion.

Self-caught mid-task: the first commit (be56e9a) added the three
`resolved/` files but never staged removal of the old `active/` copies
(the `mv` happened at the shell level, but `git add` only listed the new
paths) -- would have produced a `WORK_ITEM_ID_DUPLICATE` on a fresh
checkout despite the working directory looking correct. Caught via
`git status` before pushing, fixed with a follow-up commit (7dc4fa4),
verified via `git ls-tree -r HEAD` that only the `resolved/` copies
exist in the committed tree.

This resolves all 10 work items WS-SPECIALS-CLEANUP tracks, but this PR
does **not** close the workstream itself, and does not touch `corpora/`
-- the maintainer intends to run the actual `lcats promote` themselves
as a separate PR for a collaborator's review.

# Validation

- `lrh validate` -- 0 errors, 26 pre-existing owner-role/orphan warnings
- `scripts/test` -- 1346 tests OK (no code changes; unaffected suite)
- Re-ran `span_ops_test.py`/`review_test.py`/`application_test.py`
  directly -- 24 passed
- `git ls-tree -r HEAD` -- confirmed no stale `active/` duplicates after
  the follow-up fix

# Follow-up

- On merge: update this record to `landed`.
- Offered to the maintainer, not yet decided: since all 10
  WS-SPECIALS-CLEANUP work items are now resolved, its exit criteria
  may be fully met and the workstream itself could close. Its exit
  criteria include "promotion from data/ to corpora/ is gated by a
  passing specials survey, and the stale corpora/ snapshot is
  superseded by promotion at the next release" -- phrasing that reads
  as "the mechanism is ready," not "the promotion has already
  happened," but this should be confirmed explicitly with the
  maintainer before closing, especially since they're deliberately
  deferring the actual promotion to a collaborator-reviewed PR.
- The story-count discrepancy noted during the dogfood run (1868 vs.
  1971) remains unresolved and untracked by this record.
