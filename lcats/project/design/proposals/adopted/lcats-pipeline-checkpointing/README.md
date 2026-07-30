---
id: PROP-LCATS-PIPELINE-CHECKPOINTING
type: design_proposal_set
status: adopted
implementation_status: not_started
---

# Staged, Checkpointed Pipeline Execution for LCATS Batch Scripts

This proposal set records the design for a shared, reusable checkpointing
pattern for LCATS's LLM-driven batch scripts, generalizing the existing
`DataGatherer.download` bucket-directory precedent. It is motivated by
`run_pilot.py`'s measured failure against 8 operational criteria this session
used to freeze it: no bounded small-scale trial and no persistence/resume,
meaning a crash or interruption discards every already-paid-for LLM call.

## Documents

- [`00_proposal.md`](00_proposal.md) — background, prior-art check, design
  decisions (checkpoint publication, staleness/identity, granularity,
  adoption path), non-goals, and implementation plan.

Governed by [`WS-PIPELINE-CHECKPOINTING`](../../../../workstreams/proposed/WS-PIPELINE-CHECKPOINTING.md).
