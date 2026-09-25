---
resolution: "Implemented comparative lexical analysis and selection contract in PR #388 (commit 4efe8ac30c3a0432f5d87164b29b30008a4338e2)"
blocked_reason: null
blocked: false
id: WI-VISUALIZE-0091
title: Define the comparative lexical analysis and selection contract
type: deliverable
status: resolved
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams:
  - WS-COMPARATIVE-LEXICAL-VISUALIZATION
related_design:
  - project/design/proposals/proposed/comparative-lexical-visualization/00_proposal.md
  - project/design/proposals/adopted/corpus-text-visualization/00_proposal.md
depends_on: []
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - implement_renderers
  - modify_existing_visualize_defaults
  - promote_sidecars
acceptance:
  - A typed immutable comparison specification declares universe, left/right selectors, membership mode, metrics, denominators, term form, token filters, vocabulary, ordering, style, and output formats
  - Selector algebra implements explicit universes and complements as U minus S, reports overlap, and distinguishes candidate, primary, and selection genre semantics
  - Analysis produces one deterministically aligned tabular vocabulary with raw support counts, denominators, left/right values, signed/absolute differences, and display order
  - Overlay compatibility rejects mismatched metric, normalization, denominator, term form, or filter policies, and TF-IDF comparisons fit once over the declared universe
  - Unit tests and documentation cover selection, metrics, ties, top-N policies, stopwords, manifests, and error paths; scripts/test passes
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - src/lcats/visualize/comparison.py
  - src/lcats/visualize/analysis.py
  - tests/visualize_tests/
  - docs/reference/comparative-visualization.md
---

# Work Item: WI-VISUALIZE-0091

## Summary

Define and implement the reusable comparison specification, selector algebra,
metric computation, aligned vocabulary, tabular result, and provenance
contract that all new comparative lexical charts consume.

## Problem / Context

The current visualization API accepts one text collection or one selected
genre and returns a single ranked mapping. The approved design requires two
selectors against a declared universe, optional complements, aligned terms,
controlled ranking, compatible metrics, and enough evidence to reproduce every
displayed value. This item establishes those semantics before rendering or POS
integration is added.

### Duplication search

- In-repo: extend `src/lcats/visualize/analysis.py` and reuse its corpus-wide
  TF-IDF fit and group-minus-complement primitive. No general comparison spec,
  selector algebra, or aligned two-series table exists.
- Sibling repos: none identified.
- External libraries: scikit-learn supplies vectorization but not LCATS group,
  membership, manifest, or vocabulary semantics.
- Recommendation: proceed by extending the current visualization package.

### Demand search

- Work items: `WI-VISUALIZE-0090` delivered only TF-IDF genre-versus-complement
  ranking and explicitly left broader comparison modes out of scope.
- Proposals: the governing proposal and adopted corpus visualization proposal
  require reusable, reproducible analysis rather than one-off charts.
- Backlog: no matching open item.
- Recommendation: proceed; link the resolved predecessor as prior demand.

## Scope

- Comparison specification and validation.
- Explicit universe, selector, complement, membership, and overlap semantics.
- Metrics, denominators, filters, aligned vocabulary, ordering, and ties.
- Authoritative comparison table plus manifest-ready provenance.

## Required Changes

1. Add a typed immutable `ComparisonSpec` and normalized selector types under
   `src/lcats/visualize/`, keeping CLI concerns outside the model.
2. Implement corpus, manifest, and explicit-story-list universes; all, genre,
   complement, manifest-genre, story-list, and include/exclude selectors; and
   explicit candidate/primary/selection membership modes.
3. Implement raw count, per-million frequency, document count/percentage,
   mean per-document relative frequency, shared-fit mean TF-IDF, and existing
   TF-IDF contrast adapters without changing existing command behavior.
4. Construct one aligned candidate vocabulary with all/top-N/union/
   intersection/include/exclude/min-document-frequency policies and stable
   ordering/tie rules.
5. Produce a serializable table and manifest payload containing support counts,
   denominators, values, differences, memberships, overlaps, warnings, and
   preprocessing/TF-IDF provenance.
6. Document metric comparability and reject invalid reference-overlay specs.

## Non-Goals

- Do not implement chart rendering or the new CLI command.
- Do not add POS-dependent behavior before lexical artifacts exist.
- Do not change the defaults or output meanings of existing visualization
  commands.
- Do not present metric difference as statistical significance.

## Acceptance Criteria

- The full frontmatter acceptance list passes with deterministic tiny-fixture
  tests.
- Complement tests prove `U - S` for both the whole corpus and a manifest
  universe, including overlap/multi-label cases.
- TF-IDF tests prove one shared universe fit and reject independently scaled
  overlay inputs.
- The table is sufficient for a renderer to operate without redoing selection
  or analysis.
- Documentation defines every public comparison field and invariant.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes

- Ambiguous universe or genre semantics can silently invalidate a comparison;
  make them required and visible in manifests.
- Raw count and normalized rates answer different questions; compatibility
  validation must prevent a misleading overlay.
- Deterministic ranking requires an explicit secondary tie order.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-COMPARATIVE-LEXICAL-VISUALIZATION.md`
- Design: `project/design/proposals/proposed/comparative-lexical-visualization/00_proposal.md`
