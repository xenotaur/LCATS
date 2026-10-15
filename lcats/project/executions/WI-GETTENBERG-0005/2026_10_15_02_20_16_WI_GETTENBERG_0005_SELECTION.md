---
execution_id: 2026_10_15_02_20_16_WI_GETTENBERG_0005_SELECTION
prompt_id: PROMPT(WI-GETTENBERG-0005:WI_GETTENBERG_0005_SELECTION)[2026-10-15T02:09:34+00:00]
work_item: WI-GETTENBERG-0005
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/511
commit:
created_at: 2026-10-15T02:20:16+00:00
agent: codex_app
instruction_source: project/work_items/proposed/WI-GETTENBERG-0005.md
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
---

# Summary

WI-GETTENBERG-0005 A17 selection slice under the human-approved 15-minute target,
20-minute hard stop (02:09:18–02:29:18 UTC). Base c447c15b on integration branch
codex/gettenberg-acquisition; child codex/gettenberg-resource-selection. Internal
integration only; main promotion and whole-WI completion remain human-gated.

# Result

resources.select_resource provides deterministic, pure declared-format ranking,
immutable preferences/results/diagnostics, source-order ties and explicit selection
of non-text formats. It preserves metadata and performs no I/O. Malformed MIME and
charset continuation claims are diagnosed, not normalized into encoding evidence.
How-to and reference docs are tested. Prior-art check is present in WI; this
satisfies A17 only, not the entire work item or replacement project.

# Validation

Final canonical scripts/test passes 2763 tests in 76.797 seconds; 19 focused selection
tests. Format/lint pass (260 files). LRH 0 errors / 351 existing warnings.
One cold independent review found a P2; coordinator reproduced both failure cases,
repaired them with regressions and obtained a clean same-assignment recheck.
A later hosted P2 (quadratic whitespace scanning) was also reproduced, repaired,
and independently cleared. Final six reviewed hashes and canonical evidence are in
[hosted-repair.json](../../development/evidence/gettenberg-selection-20261015/hosted-repair.json).
An earlier documentation-test failure and its repair are preserved in the runlog.

[Qualification evidence](../../development/evidence/gettenberg-selection-20261015/qualification.json).
Native review record links through rerun_of and PR511. No external data download,
notebook/CI/dependency changes, main promotion or persistent consent mutation.

# Follow-up

First hosted rounds observed; verify new repair-head checks before integration.
PR remains open at sprint stop. No integration or main merge occurred.
Remaining WI scope: conditional refresh, strict text/container decoding,
catalog receipt composition and qualified automatic Gutenberg routes.
This execution remains in_progress until human-approved main delivery.
