---
id: PROP-LCATS-GETTENBERG-REDESIGN
type: design_proposal_set
status: "adopted"
implementation_status: "implemented"
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

## Main delivery and formal closeout — 2026-10-27

PR [#534](https://github.com/xenotaur/LCATS/pull/534) delivered the replacement to
main at `b4ec4c452ed178dd62472af9f1a46b44e70ce485`. The human approved the
closeout plan, exact resolution notes, all four workstream exit criteria and the
archive-sync exception. WI-GETTENBERG-0001–0010 are resolved, WS-GETTENBERG is
closed, and the redesign proposal is adopted/implemented. Earlier milestone
paragraphs retain their historical meaning; this dated entry records
the current disposition. See the [formal closeout](../../../../development/gettenberg-closeout.md) for evidence and inventory.

The post-adoption backlog GPA-A–E, PR #524's separated editorial work, Kenny's
independent gatherer work, WI-RELEASE-0037/0039 and WS-RELEASE remain open.
Replacement delivery does not approve package publication, corpus promotion,
universal editorial correctness or full live-source coverage.
