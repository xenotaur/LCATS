---
resolution: null
blocked_reason: null
blocked: false
id: WI-GATHER-0101
title: Audit mass_quantities/sherlock/lovecraft's separate gather() implementations for reconciliation onto gatherlib.gather()
type: investigation
status: proposed
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams: []
related_design:
  - lcats/project/design/proposals/proposed/lcats-run-log/00_proposal.md
  - lcats/project/work_items/resolved/WI-RUNLOG-0082.md
depends_on: []
blocked_by: []
expected_actions:
  - create_file
forbidden_actions:
  - force_push
  - delete_branch
acceptance:
  - Each of the 3 gatherers (mass_quantities, sherlock, lovecraft) is classified as full reconciliation / partial reconciliation (with a concrete design sketch) / no reconciliation (with a concrete structural reason), backed by real file:line citations against both the target gatherer's own code and gatherlib.gather()'s actual signature/behavior
  - The classification for mass_quantities explicitly addresses its existing per-story error collection (gather_stories returns a failed_stories dict rather than propagating) versus gatherlib.gather()'s current propagate-on-exception behavior
  - Findings and per-site recommendations are written up as a design doc under project/design/, following the WI-SEGMENT-0069/WI-EVENT-0028 precedent for investigation-type work items
  - If reconciliation is recommended for any site, the doc states whether follow-up implementation work is warranted as a new deliverable WI (not created by this WI)
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - lcats/project/design/gatherer-reconciliation-audit.md
---

## Summary

`WI-RUNLOG-0082` explicitly excluded `mass_quantities`, `sherlock`, and
`lovecraft`'s own separate `gather()`/`gather_stories()` implementations
from run-log coverage, since none of them route through the shared
`gatherlib.gather()` loop the rest of the corpus gatherers use — noted
there as "a follow-up item if warranted," but no work item existed for
it until now. This investigation surveys all three implementations
against `gatherlib.gather()`'s actual signature and behavior to
determine which (if any) could be reconciled onto the shared function,
closing both this run-log gap and a general code-duplication gap where
it's actually safe to do so.

## Problem / Context

A quick read this session already found real structural differences
worth investigating properly:

- `sherlock/gatherer.py:123-141` and `lovecraft/gatherer.py:123-134` are
  each near-identical reimplementations of `gatherlib.gather()`'s own
  download-loop shape (a `DataGatherer` instance, one `.download()` call
  per heading/extractor), just with their own hardcoded
  author/year/description constants instead of calling the shared
  function.
- `mass_quantities/gatherer.py:26-58` is structurally different: it
  extracts many standalone single stories via `parser.gather_story` (one
  per Gutenberg ID, not a corpus split into multiple headings under one
  `DataGatherer` target), and its `gather_stories()` already does its
  own per-story error collection — returning a `failed_stories` dict
  rather than letting an exception propagate and abort the whole run,
  unlike `gatherlib.gather()`'s current behavior (no per-story exception
  isolation, per WI-RUNLOG-0082's own Non-Goal).

### Duplication search
- In-repo: No existing investigation of this reconciliation question.
  Recommendation: Proceed.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found before this one.
- Proposals: `PROP-LCATS-RUN-LOG`'s own Non-Goals section names these
  three sites as explicitly out of scope; `WI-RUNLOG-0082`'s own
  Non-Goals flags them as "a follow-up item if warranted" but does not
  request this investigation directly.
- Backlog: No matching entries in `project/design/backlog.md`.
- Recommendation: Proceed — this work item is the first place the
  follow-up is formally scoped.

## Scope

- Survey `mass_quantities/gatherer.py`, `sherlock/gatherer.py`, and
  `lovecraft/gatherer.py` against `gatherlib.gather()`'s real signature
  and behavior (parameters, `paragraph_finder`/callback shape, headings
  vs. single-story extraction, error handling).
- For each, classify: full reconciliation possible with no behavior
  change / partial reconciliation possible with a scoped
  `gatherlib.gather()` extension (sketch the extension, don't implement
  it) / no reconciliation (state the concrete structural reason).
- Record findings and a recommendation as a design doc.

## Non-Goals

- Does not implement any reconciliation by default — this is an
  investigation. If the audit finds an unambiguous, low-risk
  reconciliation opportunity, implementing it within this same work item
  is acceptable with explicit human sign-off at that point, rather than
  always mechanically deferring to a separate work item regardless of
  what's found.
- Does not change `gatherlib.gather()`'s existing behavior without that
  same explicit sign-off.
- Does not add run-log support to any of the three sites directly —
  that is downstream of whatever this investigation recommends, and
  contingent on its outcome.

## Required Changes

1. Read and diagram each of the 3 implementations against
   `gatherlib.gather()`'s actual signature and behavior.
2. Classify each per the Scope section above, with real file:line
   citations for every claim.
3. Specifically evaluate `mass_quantities`' per-story error collection
   (`gather_stories` returns `failed_stories`, doesn't propagate)
   against `gatherlib.gather()`'s current propagate-on-exception
   behavior — note explicitly whether reconciling would require changing
   `gatherlib.gather()`'s own error-handling contract, without deciding
   that change here.
4. Write up findings as a design doc under `project/design/`, following
   `WI-SEGMENT-0069`/`WI-EVENT-0028`'s precedent for investigation-type
   work items — per-site classification, real citations, and an explicit
   recommendation (including whether follow-up deliverable work is
   warranted, and for which sites).

## Acceptance Criteria

(see frontmatter)

## Validation

- `lrh validate`

## Related Workstream and Designs

- Design: `project/design/proposals/proposed/lcats-run-log/00_proposal.md`
- Work item: `project/work_items/resolved/WI-RUNLOG-0082.md` (the item
  whose own Non-Goals first flagged this gap)
