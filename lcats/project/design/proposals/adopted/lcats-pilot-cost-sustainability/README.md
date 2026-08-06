---
id: PROP-LCATS-PILOT-COST-SUSTAINABILITY
type: design_proposal_set
status: adopted
implementation_status: not_started
---

# Making the Event-Role-World Pilot Sustainable to Run

This proposal set records the design for making
`experiments/03_cross_segment_relation_pilot/run_pilot.py` cheap enough to
iterate on and validate before committing to a full, expensive real run.
It is motivated by two real runs that together cost $67.54 without
producing usable data — mostly discovering and fixing bugs rather than
gathering the intended cross-segment relation density findings. It is the
deferred follow-through on
`lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`'s
Category E (cost visibility and control), raised ten days earlier and
explicitly held pending this discussion.

## Documents

- [`00_proposal.md`](00_proposal.md) — background, prior-art check, seven
  design decisions (validation-first sequencing, a targeted single/small-story
  test harness, a prompt-caching evaluation gate, a Batch API evaluation
  gate, a model-tiering evaluation gate, rejecting call-fusion, and
  local-model evaluation as a separate track), non-goals, and
  implementation plan.

Not yet governed by a workstream — adopted 2026-08-06; the Implementation
Plan proposes one be created via `/lrh-workstream` next.
