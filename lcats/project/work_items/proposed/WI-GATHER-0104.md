---
resolution: null
blocked_reason: null
blocked: false
id: WI-GATHER-0104
title: Extend gatherlib.gather() for per-entry URL/extraction/name, then reconcile lovecraft/gatherer.py
type: deliverable
status: proposed
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams: []
related_design:
  - lcats/project/design/gatherer-reconciliation-audit.md
  - lcats/project/work_items/resolved/WI-GATHER-0101.md
depends_on: []
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
forbidden_actions:
  - force_push
  - delete_branch
acceptance:
  - gatherlib.gather() gains three backward-compatible, opt-in extensions matching the audit's 3 identified incompatibilities -- a per-entry URL (in place of one shared gutenberg_url), a pluggable full extraction-strategy callable (in place of the heading-text-search paragraph_finder contract), and a pluggable metadata-name source (in place of always deriving name from the normalized filename)
  - Every existing gatherlib.gather() caller (sherlock, and any other caller present at merge time) is unaffected by default -- the extensions activate only when a caller opts in, verified by the pre-existing test suites for those callers passing unchanged
  - lovecraft/gatherer.py's gather() calls the extended gatherlib.gather(), and its own create_download_callback is removed
  - lovecraft_gatherer_test.py's existing assertions pass, confirming output parity -- same files produced, same display-title name values (not the normalized-filename value gatherlib.create_download_callback would otherwise store)
  - Running gather() produces a logs/gather/*lovecraft* run log, confirming lovecraft inherits gatherlib.gather()'s RunLog coverage
  - lrh validate and scripts/test pass with 0 errors
required_evidence:
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/src/lcats/gatherers/gatherlib.py
  - lcats/tests/gatherers_tests/gatherlib_test.py
  - lcats/src/lcats/gatherers/lovecraft/gatherer.py
  - lcats/tests/gatherers_tests/lovecraft_gatherer_test.py
---

## Summary

`WI-GATHER-0101`'s audit (`project/design/gatherer-reconciliation-audit.md`)
classified `lovecraft/gatherer.py`'s `gather()` as unreconcilable without
first extending `gatherlib.gather()` itself, due to 3 real
incompatibilities: (1) each story has its own URL via a per-entry
`extractors.Extractor` object, not one shared `gutenberg_url`; (2)
extraction uses ID-based `extract_text_between_ids()`, not heading-text
search; (3) `story_data["name"]` sources differ --
`gatherlib.create_download_callback` stores the normalized filename,
Lovecraft's own callback stores the display title. This work item
extends `gatherlib.gather()` to support all three as opt-in additions,
then migrates `lovecraft` onto it, closing both the duplication and the
run-log gap the user's explicit "dedupe Lovecraft" preference targets.

## Problem / Context

`lovecraft/gatherer.py` duplicates `gatherlib.gather()`'s download-loop
shape but cannot call it directly today because of the 3 incompatibilities
above. Because `lovecraft` does not route through the shared function, it
did not inherit the `RunLog` coverage `WI-RUNLOG-0082` added there, and
its own extraction/URL/naming logic exists as a parallel implementation
that must be kept in sync with `gatherlib.gather()` by hand.

### Duplication search
- In-repo: No existing extension of `gatherlib.gather()` for per-entry
  URLs, pluggable extraction, or pluggable naming. Recommendation:
  Proceed.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: `WI-GATHER-0101` (resolved) -- its audit is the direct
  source of this item's scope and the 3 incompatibilities it addresses.
- Proposals: `PROP-LCATS-RUN-LOG` names `lcats gather` as an aggregate
  upgrade site; `lovecraft` was explicitly excluded from that item's own
  scope pending this audit. Deduping Lovecraft's separate implementation
  has independently been on the project's agenda per direct user
  confirmation.
- Backlog: No matching entries in `project/design/backlog.md`.
- Recommendation: Proceed -- this work item is the follow-up the audit
  itself named as requiring a `gatherlib.gather()` extension first.

## Scope

- Extend `gatherlib.gather()`'s signature with 3 opt-in parameters
  covering per-entry URL, pluggable extraction strategy, and pluggable
  metadata-name source, each defaulting to today's existing behavior
  when unset.
- Migrate `lovecraft/gatherer.py`'s `gather()` onto the extended
  function.
- Remove `lovecraft/gatherer.py`'s now-dead `create_download_callback`.
- Confirm output parity via the existing test suites for both
  `gatherlib` and `lovecraft`.

## Non-Goals

- Does not touch `sherlock` or `mass_quantities` -- separate work items
  (`WI-GATHER-0103`, `WI-GATHER-0105`).
- Does not change the default behavior of any existing
  `gatherlib.gather()` caller -- every extension must be opt-in.

## Required Changes

1. Design and add the 3 opt-in extensions to `gatherlib.gather()`'s
   signature: a per-entry URL parameter (replacing/augmenting the single
   `gutenberg_url` for callers that opt in), a pluggable full
   extraction-strategy callable (replacing/augmenting the
   heading-text-search `paragraph_finder` contract for callers that opt
   in), and a pluggable metadata-`name` source (replacing/augmenting the
   normalized-filename default for callers that opt in).
2. Extend `gatherlib_test.py` to cover the new extension points directly,
   independent of `lovecraft`.
3. Migrate `lovecraft/gatherer.py`'s `gather()` to call the extended
   `gatherlib.gather()`, passing its existing per-entry `Extractor`
   objects, `extract_text_between_ids`-based extraction, and
   `extractor.title`-sourced naming through the new extension points.
4. Remove `lovecraft/gatherer.py`'s `create_download_callback`.
5. Run `lovecraft_gatherer_test.py`, extending only if a real gap is
   found -- the audit's own goal is output parity (same files, same
   display-title `name` values).

## Acceptance Criteria

(see frontmatter)

## Validation

- `scripts/version tools`
- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`

## Related Workstream and Designs

- Design: `project/design/gatherer-reconciliation-audit.md`
- Work item: `project/work_items/resolved/WI-GATHER-0101.md` (the audit
  that identified and scoped these 3 incompatibilities)
