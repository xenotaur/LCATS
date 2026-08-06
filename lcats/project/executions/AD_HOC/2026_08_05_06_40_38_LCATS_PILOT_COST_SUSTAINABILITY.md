---
execution_id: 2026_08_05_06_40_38_LCATS_PILOT_COST_SUSTAINABILITY
prompt_id: PROMPT(AD_HOC:LCATS_PILOT_COST_SUSTAINABILITY)[2026-08-05T06:32:10+00:00]
work_item: AD_HOC
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/221
commit:
agent: claude_app
instruction_source: lcats/project/design/proposals/proposed/lcats-pilot-cost-sustainability/00_proposal.md
session_transcript: pending
created_at: 2026-08-05T06:40:38+00:00
---

# Summary

Created `PROP-LCATS-PILOT-COST-SUSTAINABILITY`, a design proposal to make
the cross-segment relation pilot (`experiments/03_cross_segment_relation_pilot/run_pilot.py`)
sustainable to run, following a design review requested by the user after
two real runs this session cost $67.54 combined ($42.80 on the first,
$24.74 on a second, incomplete follow-up) without producing usable data.

# Result

- Ran the prior-art check: no in-repo duplication of prompt caching/Batch
  API/model-tiering; found a direct demand match in
  `lcats/project/design/backlog.md` (two entries) and, more significantly, in
  `lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`'s
  Category E, which raised this exact concern 10 days earlier and
  explicitly deferred it pending "the actual work item(s)/workstream/design
  proposal" - this proposal is that deferred follow-through.
- Recorded 7 design decisions: (1) sequence validation-enabling work
  before optimization work; (2) build a targeted, retargetable
  single/small-story test harness by extending `run_pilot.py`'s existing
  `run_story()` rather than writing a new script; (3) evaluate, don't yet
  adopt, Anthropic prompt caching (the confirm-fixes round found the
  original "adopt, zero quality tradeoff" framing factually wrong - each
  per-segment extractor call uses a different tool schema, and
  Anthropic's cache hierarchy invalidates everything downstream of a tool
  change, so the claimed cache-hit pattern across the 4 calls doesn't
  hold; downgraded to a gated evaluation like Decisions 4/5); (4)
  evaluate, don't yet adopt, the Batch API (50% flat discount but a real
  architecture tension with the just-built synchronous checkpointing
  design); (5) evaluate, don't yet adopt, per-stage model tiering (real
  pricing spread exists, but reliability under this pipeline's strict
  schemas is unvalidated - this session directly observed the top-tier
  model itself produce malformed output); (6) reject fusing the 4
  per-segment extractor calls (works against the adopted
  `PROP-LCATS-EVENT-ROLE-WORLD-EXTRACTOR`'s own reliability rationale);
  (7) local-model evaluation (Mac/Kubuntu Focus) is a separate, parallel,
  already-scoped research track, referenced but not implemented here.
- Every repo-grounded claim in the proposal cites `file:line` (`processor.py`,
  `run_pilot.py`, `anthropic_backend.py`, `llm_extractor.py`) verified by
  direct reading during this session, not recalled; every external claim
  (prompt-caching pricing multipliers, Batch API discount, per-model
  pricing) was fetched live from `platform.claude.com`'s current docs
  during this session, not from training-data recall.
- Confirmed with the user this is workstream-shaped (4+ related work
  items with real sequencing dependencies), matching the precedent of
  `PROP-LCATS-PIPELINE-CHECKPOINTING` → `WS-PIPELINE-CHECKPOINTING` - the
  Implementation Plan section names the follow-on workstream and 4 work
  items without creating them yet.
- User confirmed the complete proposal (frontmatter + all sections) before
  any file was written.

# Validation

- `lrh validate` (from `lcats/`) - 0 errors, 70 warnings (unchanged
  baseline).
- Confirmed the PR diff contains only the new proposal file
  (`gh pr diff 221 --name-only`) - unrelated pending changes in the
  working tree (a reverted `_ERW_MAX_TOKENS` fix, backlog updates, the
  earlier schema fix, all destined for a separate collected-fix PR) were
  stashed before creating this branch so they wouldn't be swept in.

# Follow-up

- Offer, once this proposal is adopted: create the governing workstream
  (`/lrh-workstream`) and its 4 work items (test harness, prompt caching,
  Batch API evaluation, model-tiering evaluation), per the Implementation
  Plan section.
- The stashed collected-fix changes (segmentation/`_ERW_MAX_TOKENS` revert,
  `assess_story` max_tokens, backlog updates) still need their own PR,
  separate from this proposal.
- Local-model evaluation (Decision 7) is tracked in a separate session/track
  and should be cross-referenced here once it reports findings.
