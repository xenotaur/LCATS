---
resolution: null
blocked_reason: null
blocked: false
id: WI-EVENT-0025
title: Evaluate NLP library for Event-Role-World surface-feature extraction
type: investigation
status: proposed
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams:
  - WS-EVENT-ROLE-WORLD
related_design:
  - project/design/proposals/proposed/lcats-event-role-world-extractor/00_proposal.md
depends_on: []
blocked_by: []
expected_actions:
  - create_file
  - create_pr
forbidden_actions:
  - add_new_dependency
  - implement_library_integration
  - modify_event_role_world_extractor
  - force_push
  - delete_branch
acceptance:
  - A design recommendation document compares candidate NLP libraries (spaCy, NLTK, Stanza, UDPipe, or explicitly recommending none for now) against LCATS's actual needs: accuracy on older/public-domain literary prose, offline/no-network CI compatibility, dependency and model-download weight, and license compatibility
  - The recommendation states plainly whether library adoption is justified now or should remain deferred, with a one-line rationale
  - If adoption is recommended, the document sketches which WI-EVENT-0024 surface-feature fields would be affected and roughly how, without implementing the change
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - project/design/event-role-world-surface-feature-nlp-evaluation.md
---

## Summary

Survey NLP libraries (spaCy, NLTK, Stanza, UDPipe, or similar) that could
provide real syntactic/morphological features for the Event-Role-World
extractor's surface-feature pass (stage 2), and produce a design
recommendation — not an implementation.

## Problem / Context

`WI-EVENT-0024` (still `status: proposed`, no implementation exists yet —
there is no `lcats/lcats/analysis/event_role_world/` package in the repo)
plans to implement stage 2 (surface features) as a lightweight,
dependency-free lexical/structural pass (word/sentence counts, average
word/sentence length, punctuation density) rather than true syntactic or
morphological parsing, since this repo has no NLP/parsing dependency in
`pyproject.toml` today. The governing proposal's own "Low-level choices and
tradeoffs" table already states the general direction — "Use inspectable
NLP features plus constrained normalization where useful"
(`00_proposal.md:216`) — but never commits to a specific library or
integration depth. This work item closes that gap with a concrete
recommendation before any dependency is added, and should be coordinated
with `WI-EVENT-0024`'s implementation ordering rather than assumed to run
strictly after it.

### Duplication search
- In-repo: No existing NLP library integration or evaluation found. A
  string match on "stanza" in `lcats/lcats/analysis/story_analysis.py:307`
  is a false positive (the word "stanzas" in unrelated poetry-genre text,
  not the Stanza NLP library).
- Sibling repos: None identified.
- External libraries: spaCy, NLTK, Stanza, UDPipe are the obvious
  candidates to evaluate — that evaluation is this work item's deliverable.
- Recommendation: Proceed.

### Demand search
- Work items: None found.
- Proposals: None found beyond the governing proposal itself.
- Backlog: `project/design/backlog.md` does not exist in this repo.
- Recommendation: No action.

## Scope

- Survey spaCy, NLTK, Stanza, and UDPipe (or other well-known alternatives)
  against LCATS's specific corpus characteristics: older/public-domain
  literary prose, dialect, archaic punctuation.
- Assess offline/no-network CI compatibility, dependency and
  model-download weight, and license compatibility.
- Produce a written recommendation: adopt now (and which library), or
  defer (and why).

## Required Changes

1. Create `project/design/event-role-world-surface-feature-nlp-evaluation.md`
   with the survey and recommendation.
2. If adoption is recommended, sketch (not implement) which
   `WI-EVENT-0024` surface-feature fields would be affected.

## Non-Goals

- Does not add any new dependency to `pyproject.toml`.
- Does not implement library integration — a follow-up `deliverable` work
  item would do that if this investigation recommends adoption.
- Does not modify `WI-EVENT-0024`'s existing implementation.

## Acceptance Criteria

- A design recommendation document compares candidate NLP libraries
  against LCATS's actual needs (older literary prose, offline CI
  compatibility, dependency weight, license).
- The recommendation states plainly whether adoption is justified now or
  should remain deferred, with a one-line rationale.
- If adoption is recommended, the document sketches affected
  `WI-EVENT-0024` surface-feature fields without implementing the change.
- `lrh validate` reports 0 errors after the file is written.

## Validation

- `lrh validate`

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-EVENT-ROLE-WORLD.md`
- Design: `project/design/proposals/proposed/lcats-event-role-world-extractor/00_proposal.md`
