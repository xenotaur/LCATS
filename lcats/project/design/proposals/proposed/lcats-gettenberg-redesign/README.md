---
id: PROP-LCATS-GETTENBERG-REDESIGN
type: design_proposal_set
status: proposed
implementation_status: not_started
---

# LCATS-owned Gutenberg Catalog and Acquisition Library

This proposal set describes replacing the external `gutenbergpy` dependency
with an LCATS-owned `gettenberg` library for catalog ingestion, rich metadata,
predictable queries, cached resource acquisition, and Gutenberg boilerplate
removal. It preserves smart `lcats gather` behavior and defines migration,
testing, documentation, and evidence requirements.

## Documents

- [`00_proposal.md`](00_proposal.md) — design decisions, migration inventory,
  feature and evidence matrix, delivery stages, and the proposed development
  process experiment.

The proposal calls for establishing `WS-GETTENBERG` and approving a separate
execution charter before implementation; neither is created by this proposal set.
