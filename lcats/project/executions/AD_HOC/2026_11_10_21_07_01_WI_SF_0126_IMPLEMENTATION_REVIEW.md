---
execution_id: 2026_11_10_21_07_01_WI_SF_0126_IMPLEMENTATION_REVIEW
prompt_id: PROMPT(AD_HOC:WI_SF_0126_IMPLEMENTATION_REVIEW)[2026-11-10T21:06:54+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_10_31_10_55_24_WI_SF_0126
pr: https://github.com/xenotaur/LCATS/pull/539
commit: f903ba66f016eb5175c9dc645236c0349eeae234
created_at: 2026-11-10T21:07:01+00:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/539
session_transcript: pending
---

# Summary

Address the review findings on PR 539 (WI-SF-0126, the heinlein_temporal contract): one Codex thread, three Copilot threads, and the substitute cold self-review of head 882c6471. Each finding was verified against the code and shown to the owner as a triage before any edit; the owner approved the fixes in three rounds.

# Result

Codex P2 (e55a6759): R2 uses not_assessable when the model cannot state a timeline at all, but an empty timeline was rejected. An empty timeline is now a valid unknown: derived statuses and relation are not_assessable, the premise counts as speculative, carries a stated condition, and combines to ambiguous so it never yields a vacuous present.

Copilot, three threads (882c6471), each reproduced first: (1) periods whose interiors overlapped were accepted, and now only a shared boundary may overlap; (2) a null or object criterion rationale was accepted, and a string is now required; (3) the stored assessment was compared with dict equality, so 0 matched false, and it is now compared as canonical JSON.

Cold self-review (no blocking defects; six low findings), three fixed in f903ba66: the whole stored record outside assessment is now compared with its normalized rebuild (new kind heinlein_temporal_record_mismatch), standing-period source and composition caveats are type-checked, adjacent day-precision periods within one month are accepted, and the record-level condition is built from counted premises only. Not changed: mixed-granularity boundary treated as overlap (defensible; R1 wording ambiguous), composition interval starting after the analysis date (deferred to WI-SF-0127, which builds the interval), and the pre-existing unhashable-status TypeError in the shared validator (disclosed in the PR body).

# Validation

Black, ruff, scripts/test (3079 tests OK) and lrh validate (0 errors, 354 existing warnings) passed on f903ba66. Existing sidecar and fingerprint hashes are unchanged, pinned by the golden-hash test and confirmed byte-identical against the base commit by the cold review. Threads are left for confirm-fixes to resolve.

# Follow-up

WI-SF-0127 should validate that the composition interval does not start after the analysis date, and its prompt should avoid mixed-granularity boundary dates. Cross-checking human and existing_statuses against the Heinlein record remains deferred to WI-SF-0127.
