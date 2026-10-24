---
id: "WS-GETTENBERG"
kind: "planning_node"
title: "LCATS-owned Gutenberg library and bounded execution pilot"
status: "proposed"
stage: "designed"
origin: "design_review"
summary: "Replace gutenbergpy with internal gettenberg and capture evidence from bounded coordinator-led development."
related_focus:
  - "FOCUS-WORLDCON-2026"
related_roadmap:
  - "ROADMAP-CORE"
related_design:
  - "project/design/proposals/proposed/lcats-gettenberg-redesign/00_proposal.md"
  - "project/development/gettenberg-pilot-charter.md"
work_items:
  - "WI-GETTENBERG-0001"
  - "WI-GETTENBERG-0002"
  - "WI-GETTENBERG-0003"
  - "WI-GETTENBERG-0004"
  - "WI-GETTENBERG-0005"
  - "WI-GETTENBERG-0006"
  - "WI-GETTENBERG-0007"
  - "WI-GETTENBERG-0008"
  - "WI-GETTENBERG-0009"
  - "WI-GETTENBERG-0010"
execution_records: []
evidence: []
exit_criteria:
  - "All ten completion criteria in PROP-LCATS-GETTENBERG-REDESIGN have linked verification evidence."
  - "Replacement and caller dispositions are delivered on main with no active gutenbergpy dependency."
  - "Required validation, independent review, resource/corpus comparisons, and exercised documentation qualify delivery."
  - "Execution records, work items, release-plan reconciliation, and process observations accurately describe delivered and remaining scope."
---

# Workstream: LCATS-owned Gutenberg library

## Purpose

Implement the approved gettenberg redesign from PR #501. Coordinate technical
delivery and a bounded execution experiment without confusing the first run's
limit with full workstream completion. This initial plan is proposed/designed;
downstream WIs follow the bootstrap audit. Filing it does not begin execution.

## Scope

- Metadata models, bounded ingestion, catalog queries and lifecycle.
- Cached acquisition, decoding, conservative cleanup, smart gather preparation.
- Caller migration, notebook/experimental/experiments/Kmo dispositions,
  packaging and CI correction, and Diataxis docs.
- Evidence-led delivery under the
  [pilot charter](../../development/gettenberg-pilot-charter.md).

## Prior Art Check

### Duplication search

- In-repo: `src/lcats/gettenberg/` and `src/lcats/gatherers/` are replacement
  and integration targets. No separate gettenberg workstream or pilot charter
  was found in the planning tree at base `75eaf9e6`. WS-RELEASE retains release
  readiness responsibility.
- Sibling repos: logical_robotics_harness at inspected commit `08bed00b`
  has run-tree/execution-framework designs and documentation-only assistant
  roles. Reuse concepts; do not implement their runtime in LCATS.
- External libraries: gutenbergpy is the explicitly rejected long-term
  dependency. Standard parsing/storage libraries remain engineering choices;
  no new agent orchestration dependency is necessary.
- Recommendation: Proceed with the approved redesign and local pilot protocol;
  reconcile existing release planning rather than duplicate its gate.

### Demand search

- Work items: WI-RELEASE-0037 needs internal-replacement reconciliation;
  WI-RELEASE-0039 retains near-publication verification timing.
- Proposals: PROP-LCATS-GETTENBERG-REDESIGN governs technical delivery;
  PROP-LCATS-PYPI-RELEASE-READINESS remains a separate release concern.
- Backlog: `project/design/backlog.md` has the upstream-release watch for
  WI-RELEASE-0037, requiring a superseding decision note.
- Recommendation: Reconcile during WI-GETTENBERG-0001; do not close release
  items merely because this plan is filed.

## Work Items

**WI-GETTENBERG-0001 — Establish baseline and reconcile execution planning.**
The initial bootstrap item: feature/evidence matrix, caller audit,
fixture/provenance plan, baseline, release-plan reconciliation, and scoped next
WIs. It does not implement the library.

These are planned tranches; allocated WI IDs are listed in the amendment below.
Split large tranches into small items with scope, dependencies, acceptance,
validation, and evidence before dispatch.

| Stage | Deliverables and exit evidence | Prerequisite |
|---|---|---|
| 0. Planning/baseline | WI-GETTENBERG-0001: feature matrix, caller dispositions, fixtures, baseline, reconciled plans, next WIs | Approved charter and explicit start |
| 1. Models/ingestion | Field mapping/provenance, bounded RDF ingestion, real SQLite fixtures, title/alias regressions | Stage 0 and recorded model/schema decisions |
| 2. Catalog/lifecycle | Queries, validation, generation activation/recovery, concurrency, offline rebuild | Stable models/ingestion |
| 3. Acquisition/cleanup | Resource cache, network policy, decoding, conservative cleanup regressions | Stable resource/provenance contracts; may overlap stage 2 if independent |
| 4. Gather integration | Collection requirements, smart first use, catalog commands, preserved buckets/normalization, unrelated-source isolation | Qualified catalog/acquisition behavior |
| 5. Migration/packaging | Caller migration/archives, dependency removal, fresh install/wheel checks; separate CI WI before CI edits | Integrated API/gather behavior |
| 6. Qualification | Full-snapshot audit, performance/corpus comparison, exercised Diataxis docs, final traceability/review | All implemented capabilities/dispositions |

Tests and docs accompany every tranche. Stage 6 verifies the integrated result.
Dependent code work requires the charter's recorded dependency evidence.

## First Run and Promotion

The first run has a proposed two-hour elapsed ceiling, three total agents,
60 cumulative worker minutes, and four delegated assignments including review.
See the charter for reserves/accounting. Begin with stage 0; only proceed into
fully specified, reviewed downstream plans that fit the remaining allowance.
There is no claim that all stages fit two hours. Exhaustion yields a checkpoint
and remaining-work report, not a resolved workstream.

Use small internal PRs and one final main promotion. Propose an earlier milestone
only for review size, integration risk, or design issues. Main promotion and
budget renewal require human approval. Internal integration remains staged
evidence until actual main closeout.

## Exit Criteria

All ten governing design criteria need acceptance-to-evidence mapping:
dependency removal; first-run/cached/offline/unattended gather; unrelated-source
isolation; failed-refresh recovery; provenance; caller dispositions;
corpus/resource review; canonical validation; and accurate docs/control plane.
Obtain main promotion and reconcile all execution records and work item states.
The process log contains observed outcomes and concrete LRH recommendations.

## Non-Goals

- Old gutenbergpy API/SQL/MongoDB compatibility; vendoring or waiting upstream.
- PyPI publication, canonical corpus promotion, or unrelated pipeline redesign.
- Persistent consent changes or a reusable LRH runtime.
- Premature closure of WI-RELEASE-0039; it runs near actual publication.

## 2026-10-14 execution planning amendment

Run 1 was explicitly started under the charter; native lifecycle remains nonterminal until main delivery.

- **WI-GETTENBERG-0002** — Typed metadata and bounded RDF record parser.
- **WI-GETTENBERG-0003** — Streaming local archive ingestion and SQLite catalog queries.
- **WI-GETTENBERG-0004** — Recoverable catalog generations and offline lifecycle.
- **WI-GETTENBERG-0005** — Bounded resource acquisition and original-byte cache.
- **WI-GETTENBERG-0006** — Conservative boilerplate cleanup with diagnostics.
- **WI-GETTENBERG-0007** — Source-aware gather preparation and catalog commands.
- **WI-GETTENBERG-0008** — Migrate callers and remove gutenbergpy packaging dependency.
- **WI-GETTENBERG-0009** — Replace Gutenberg CI cache maintenance with supported operations.
- **WI-GETTENBERG-0010** — Qualify replacement, exercise Diataxis docs and reconcile delivery.

These items are scoped plans, not claims of implementation or accepted prerequisites.


## Main-promotion review checkpoint — 2026-10-24

The narrower provider replacement is internally integrated through PR #530 at
`df055256`. The [review guide](../../development/gettenberg-main-promotion.md)
indexes the full promotion, accepted A–D limitations, durable post-adoption backlog,
validation and staged-closeout plan. WIs0001–0004 are already delivered on main;
WIs0005–0010 remain staged pending human main promotion and verified closeout.
Do not merge the preserved broader PR #524 as part of provider delivery or close
post-adoption follow-up merely because this workstream later completes.
