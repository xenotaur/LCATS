---
execution_id: 2026_07_27_14_08_25_ERW_PIPELINE_STRUCTURED_OUTPUT_RELIABILITY_AUDIT_PR
prompt_id: PROMPT(AD_HOC:ERW_PIPELINE_STRUCTURED_OUTPUT_RELIABILITY_AUDIT_PR)[2026-07-27T14:08:15-04:00]
work_item: AD_HOC
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/169
commit: 4cdbe941
agent: claude_app
instruction_source: chat session (packaging the local-branch audit draft as a reviewable PR)
session_transcript: pending
created_at: 2026-07-27T14:08:25-04:00
---

# Summary

Package the ERW pipeline structured-output reliability audit (previously
drafted and iterated locally on `claude/erw-pipeline-audit-draft`, never
pushed) as an actual PR for review, per user direction: the pilot work is
paused for a postmortem, so this finding document is ready to go through
normal review rather than staying as a local-only draft.

# Result

Copied the final content of
`lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`
from the local `claude/erw-pipeline-audit-draft` branch (5 commits: initial
capture, Category E cost/checkpointing/local-models addition, postmortem
update after the second live crash, staged-pipeline design proposal, and
the corpus-wide multi-researcher/scale revisit of the checkpointing
options) onto a fresh branch based on current `origin/main`, as a single
commit - this repo's established convention is squash-merge, so granular
local history was not preserved.

Content is unchanged from the local draft; this is a packaging step only,
no new edits.

# Validation

- `lrh validate` - confirmed 0 errors, 43 pre-existing unrelated warnings.
- Documentation-only change; no code touched, no tests applicable.

# Follow-up

- `session_transcript: pending` should be updated to `claude-app:<session-id>`
  after this session ends.
- Proceed to open the PR, then the normal review/confirm/merge cycle.
- While review is pending, the minimal repro/fix for the
  `entity_extractor.py:144` crash (targeted at
  `corpora/mass_quantities/the_guardians__cox.json`, the story that has
  failed identically on every attempt) is being worked on separately.
