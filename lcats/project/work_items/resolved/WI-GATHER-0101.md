---
resolution: "Investigation complete via PR #414 (commit d0e7d69e). Classified sherlock as full reconciliation (zero behavior change once corrected on review), lovecraft and mass_quantities as no reconciliation without further work. Findings in project/design/gatherer-reconciliation-audit.md."
blocked_reason: null
blocked: false
id: WI-GATHER-0101
title: Audit mass_quantities/sherlock/lovecraft's separate gather() implementations for reconciliation onto gatherlib.gather()
type: investigation
status: resolved
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

- `lcats/src/lcats/gatherers/sherlock/gatherer.py:123-141` reuses
  `gatherlib.gather()`'s own download-loop shape (a `DataGatherer`
  instance, one `.download()` call per heading), just with its own
  hardcoded author/year/description constants instead of calling the
  shared function — a strong reconciliation candidate on its face.
- `lcats/src/lcats/gatherers/lovecraft/gatherer.py:123-134` shares that
  same loop shape, but is NOT a near-identical case (review finding, PR
  #412): each story is its own separate Gutenberg URL via a per-entry
  `extractors.Extractor` object (`lovecraft/gatherer.py:11-13`, one
  `url`/`title`/`author` per story, not one shared `gutenberg_url` for
  every heading the way `gatherlib.gather()`'s signature assumes), and
  it extracts a whole document with `extractors.extract_text_between_ids()`
  (`lovecraft/gatherer.py:105`) rather than locating a heading through
  `gatherlib.gather()`'s `paragraph_finder` callback shape. Any
  reconciliation here would need `gatherlib.gather()` to accept a
  per-entry URL and a pluggable extraction strategy, not just a rename.
- `lcats/src/lcats/gatherers/mass_quantities/gatherer.py:26-58` is
  structurally different again: it extracts many standalone single
  stories via `parser.gather_story()` (one per Gutenberg ID, not a
  corpus split into multiple headings under one `DataGatherer` target).
  Its `gather_stories()` returns a `failed_stories` dict rather than
  aborting the whole run on every failure, but this is **not** general
  per-story exception isolation (review finding, PR #412):
  `parser.gather_story()` (`parser.py:1365-1405`) only wraps
  `api.load_etext()` in `try`/`except` — metadata access
  (`api.get_metadata`, `parser.py:1377-1388`), parsing, normalization,
  directory creation, and JSON writes are unprotected and can still
  propagate. `failed_stories` mostly records rejection values
  `gather_story()` explicitly returns (bad metadata, excluded story),
  not a caught-and-classified exception. The audit must verify this
  distinction directly rather than assume a non-propagating contract
  exists, since assuming one could bias the investigation toward
  recommending an unwarranted `gatherlib.gather()` extension.

### Duplication search
- In-repo: No existing investigation of this reconciliation question.
  Recommendation: Proceed.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found before this one.
- Proposals: `PROP-LCATS-RUN-LOG`'s own Decision 4 table classifies
  `lcats gather` as an aggregate "upgrade" site and does not itself name
  `mass_quantities`/`sherlock`/`lovecraft` (review finding, PR #412 —
  correcting an earlier misattribution to the proposal). The actual
  exclusion was introduced by `WI-RUNLOG-0082`'s own Non-Goals
  (resolved WI, lines 113-118), which names these three sites
  explicitly and flags reconciliation as "a follow-up item if
  warranted," without requesting this investigation directly.
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
