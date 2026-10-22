---
execution_id: 2026_10_22_07_51_27_GETTENBERG_SCOPE_AUDIT
prompt_id: PROMPT(WI-GETTENBERG-0010:GETTENBERG_SCOPE_AUDIT)[2026-10-22T07:51:13+00:00]
work_item: WI-GETTENBERG-0010
status: in_progress
rerun_of:
pr:
commit:
created_at: 2026-10-22T07:51:27+00:00
agent: codex_app
instruction_source: project/development/gettenberg-scope-causality-audit.md
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
---

# Summary

Human approved a two-hour target /three-hour maximum scope and causality audit,
starting 07:49:48 UTC. Separate provider replacement, strictly induced gather impact,
and independent gather enhancements. Kenny's unavailable code is a future reconciliation
input. No product changes, active qualification amendments, merge or release authority.

# Result

Produced retain/separate/defer matrix, causal findings, proposed Q1–Q8 qualification
criteria, construction alternatives and Kenny meeting brief. The migration seam is
ed20e9c2; only cleanup.py changed inside gettenberg afterward. Mixed parser/CLI/logging
dependencies prevent a mechanical revert. Minimum integration mitigation remains a
future decision; retaining the complete extractor is not automatically necessary.

Eight-case 2×2 replay reproduces all 16 archived hashes: 35401/50103 demonstrate replacement
cleanup→extractor truncation; 42640 shows extraction-induced chapter changes with either
cleaner. All eight current bodies need review with either cleaner. Historical unresolved
counts are not replacement defect counts. Metadata/query changes are audited separately.
Both investigator findings were coordinator-checked and an independent reviewer
reproduced the rows. Existing source/cache/corpus bytes and dispositions are untouched.

# Validation

Package format/lint, explicit diagnostic format/lint, eight-case replay and help/failure
smokes pass. LRH 0 errors /351 existing warnings. No full suite run or new product qualification
claimed. One review P2 (imported module identity) repaired and independently rechecked
using a real shadow import; no findings remain. Evidence includes exact product/input/
runner hashes, prior output and failure logs. Product/test/active-gate files unchanged.

# Follow-up

Human review of the proposed scope and qualification boundary, then a separately
bounded implementation grant if approved. Keep WI0010 and native records nonterminal;
PR524 remains unmerged. No broader editorial investigation, acceptance of stories,
Kenny reconciliation, canonical corpus promotion or package publication performed.

[Audit](../../development/gettenberg-scope-causality-audit.md).
[Meeting brief](../../development/gettenberg-scope-meeting-brief.md).
[Evidence](../../../../experiments/10_gettenberg_qualification/results/gettenberg-scope-audit-20261022/README.md).

Children: AD_HOC/2026_10_22_08_07_02_GETTENBERG_SCOPE_INVENTORY;
AD_HOC/2026_10_22_08_07_03_GETTENBERG_CAUSALITY_AUDIT;
AD_HOC/2026_10_22_08_07_04_GETTENBERG_SCOPE_AUDIT_REVIEW (including one focused recheck).
