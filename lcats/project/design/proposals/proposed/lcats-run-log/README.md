---
id: PROP-LCATS-RUN-LOG
type: design_proposal_set
status: proposed
implementation_status: not_started
---

# Shared Run-Event Logging for LCATS Batch Scripts

This proposal set records the design for formalizing PR #334's per-run
JSONL event log (`_log_run_event()`,
`experiments/05_metadata_genre_prefilter/run_prefilter.py:883-905`) as a
shared `lcats.utils.run_log` module, and for triaging every existing and
candidate LCATS batch script/CLI command against it — upgrading
warranted-but-missing sites and explicitly recording a "no log needed"
disposition for the rest.

## Documents

- [`00_proposal.md`](00_proposal.md) — background, prior-art check, design
  decisions (implementation approach, module location, relationship to
  checkpoint roots, per-site migration disposition), non-goals, and
  implementation plan.

Governed by [`WS-RUN-LOG`](../../../../workstreams/proposed/WS-RUN-LOG.md)
(proposed; work items not yet created).
