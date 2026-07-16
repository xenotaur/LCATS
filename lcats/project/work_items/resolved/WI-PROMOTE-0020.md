---
resolution: "Implemented and merged in PR #125 (commit 526264f). Added 'lcats promote': per-collection survey gate on likely_repairable mojibake findings, wholesale-replace on promotion, identity collection-name mapping (resolved: data/'s current names canonical everywhere). Review hardened against source/dest path collisions and unhandled CLI exceptions. Last of the five WS-SPECIALS-CLEANUP burn-down items."
blocked_reason: null
blocked: false
id: WI-PROMOTE-0020
title: Survey-gated promotion from data/ to corpora/
type: deliverable
status: resolved
priority: high
owner: unassigned
related_focus:
  - FOCUS-WORLDCON-2026
related_workstreams:
  - WS-SPECIALS-CLEANUP
related_design:
  - project/workstreams/proposed/WS-SPECIALS-CLEANUP.md
depends_on:
  - WI-RESIDUAL-0019
forbidden_actions:
  - force_push
  - modify_ci_pipeline
acceptance:
  - A promotion command copies data/ collections to corpora/ only when the specials survey passes, and refuses with a clear report when it fails
  - The data/-to-corpora/ collection-name mapping (ohenry-four_million vs ohenry, wilde_happy_prince vs wilde) is explicit and documented
  - A seeded-defect test proves the gate blocks promotion of damaged text
required_evidence:
  - test_output
  - manual_review
  - lrh_validate
artifacts_expected:
  - promotion script or lcats CLI subcommand
  - collection mapping documentation
---

# Work Item: WI-PROMOTE-0020

## Summary
Build the survey-gated promotion step that copies a verified `data/` tree into the repo `corpora/` snapshot at release time, refusing to promote when the specials survey fails.

## Problem / Context
The current `corpora/` snapshot carries 148 stories of stale encoding damage precisely because promotion happened without a quality gate. Making the gate part of the promotion tool makes this class of drift self-detecting at every future release. Promotion also currently implies renaming/merging collections (data/ `ohenry-four_million` + `ohenry-whirligigs` vs corpora/ `ohenry`; `wilde_happy_prince` vs `wilde`), which is undocumented — an open question inherited from WS-SPECIALS-CLEANUP.

## Scope
- Promotion command (script or `lcats` subcommand — decide at implementation).
- Survey gate wired in, with clear failure reporting.
- Explicit, documented collection mapping.

## Required Changes
1. Implement the promotion step: run `lcats survey --mode specials` over the source tree; on pass, copy collections into `corpora/` per the mapping; on fail, exit non-zero with the findings report.
2. Resolve and document the collection-name mapping (confirm with maintainer whether ohenry sub-collections merge).
3. Test with a seeded mojibake fixture proving the gate refuses promotion.
4. Document the release-promotion procedure in `docs/` or the corpora README.

## Non-Goals
- Do not perform the actual release promotion — that is a release-time human action using this tool.
- Do not extend the gate to non-mojibake checks in this item (structural/boundary checks can be added later).
- Do not modify CI.

## Acceptance Criteria
- Gate demonstrably blocks damaged input and passes clean input.
- Mapping documented; promotion procedure written down.
- `scripts/test` passes with the new fixture test.

## Validation
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes
- The stale corpora/ snapshot will be wholesale replaced at first gated promotion; downstream consumers of current corpora/ paths should be flagged in the PR that performs it.
- Collection-mapping ambiguity (ohenry merge) needs a maintainer answer before the tool hardcodes it.
