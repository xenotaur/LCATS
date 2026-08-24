---
resolution: null
blocked_reason: null
blocked: false
id: WI-VISUALIZE-0095
title: Add aligned multi-subset comparison figures
type: deliverable
status: proposed
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
depends_on:
  - WI-VISUALIZE-0091
  - WI-VISUALIZE-0092
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_report
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - use_independent_panel_vocabularies_silently
  - use_incommensurate_panel_scales_silently
  - imply_overlapping_selectors_partition_the_universe
  - omit_manifest_or_csv
acceptance:
  - A reusable API and thin CLI compose an ordered sequence of subset panels such as S1, S2, S3 or universe-relative complements U minus S1, U minus S2, U minus S3
  - Every panel uses one declared universe, aligned vocabulary and term order, shared metric, denominator, preprocessing policy, and a common visible scale by default
  - The figure supports no reference, one common reference, or a per-panel complement/reference overlay while preserving commensurate-value checks
  - Manifests record ordered selectors, resolved membership, group sizes, pairwise intersections, complement construction, scale policy, panel wrapping, and output hashes
  - Long-form CSV output and tests establish deterministic values, ordering, layout, overlap handling, and accessible grayscale rendering
required_evidence:
  - test_output
  - validation_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - src/lcats/visualize/
  - tests/visualize_tests/
  - docs/how-to/run-visualize.md
---

# Work Item: WI-VISUALIZE-0095

## Summary

Add a reusable aligned small-multiples figure that compares several ordered
subsets, or the corresponding universe-relative complements, using the same
terms, order, metric semantics, and visible scale.

## Problem / Context

The two-series mirrored and reference-overlay charts make one target/reference
relationship legible. A paper figure may also need to compare several genres
or other subsets at once—for example `S1`, `S2`, `S3`, or `U - S1`, `U - S2`,
`U - S3`. Independently generated charts make cross-panel differences harder
to inspect and can silently change vocabulary, order, or scale. LCATS needs a
single composition contract that preserves comparability and provenance.

Genre selectors may overlap because candidate labels need not partition the
universe. The implementation must report overlap instead of treating the
panels as mutually exclusive, and every complement must be computed relative
to the same explicit universe `U`.

### Duplication search

- In-repo: `WI-VISUALIZE-0091` defines aligned comparison data and selector
  semantics, while `WI-VISUALIZE-0092` defines the two-series renderer. No
  existing LCATS command composes several aligned subset comparisons into one
  figure.
- Sibling repos: none identified.
- External libraries: Matplotlib supplies subplot and shared-axis primitives,
  but not LCATS selector, complement, alignment, overlap, or manifest rules.
- Recommendation: compose the existing comparison results and renderer rather
  than introduce a second analysis path.

### Demand search

- Work items: no open or resolved item specifies an ordered multi-subset
  figure.
- Proposals/workstream: the governing comparison proposal and workstream are
  the appropriate homes for this paper-facing variant.
- Backlog: no matching entry was found.
- Recommendation: add this bounded renderer/composition item and make final
  dogfooding depend on it.

## Scope

- An ordered list of two or more subset selectors under one declared universe.
- Direct subset panels and universe-relative complement panels.
- One aligned vocabulary and term order across every panel.
- Shared metric, denominator, term form, filters, preprocessing, and visible
  scale by default.
- Optional common reference or per-panel reference/complement overlays.
- Deterministic side-by-side columns with documented wrapping for larger panel
  counts.
- Long-form CSV, full manifest provenance, and accessible vector/raster output.

## Required Changes

1. Define a multi-panel specification that references one `ComparisonSpec`
   basis plus an ordered selector list, panel mode, reference policy, scale
   policy, column count, and output formats.
2. Resolve every selector against the same `U`; compute complements as `U - S`
   and record ordered story IDs, sizes, and all pairwise intersections.
3. Build one candidate vocabulary and order before calculating panel display
   rows. Reject or clearly label requests for independent vocabulary/order.
4. Require commensurate metric, denominator, term form, and preprocessing for
   shared axes and overlays. Use a common visible scale by default; make any
   explicit per-panel scale unmistakable in labels and the manifest.
5. Compose ordered side-by-side panels, wrapping deterministically when the
   requested count exceeds the configured column count. Keep term labels,
   reference marks, excess/deficit encodings, and legends readable.
6. Support direct subsets, their complements, a single common reference, and
   per-panel reference/complement overlays without assuming selectors form a
   partition.
7. Emit long-form CSV keyed by panel, selector, term, display rank, value,
   reference value, difference, and supporting denominators; extend manifests
   with layout and overlap provenance.
8. Add analysis, rendering, CLI, serialization, deterministic-layout, failure,
   grayscale, and documentation tests plus a checked real-data example.

## Non-Goals

- Do not add statistical significance testing or imply visual differences are
  significant.
- Do not silently choose independent vocabularies, term orders, denominators,
  or scales per panel.
- Do not require genre selectors to be disjoint or exhaustive.
- Do not replace the two-series mirrored/reference-overlay chart.
- Do not add arbitrary dashboard interactivity in this item.

## Acceptance Criteria

- All frontmatter acceptance conditions are verified by automated tests and a
  real-data review.
- A documented example renders at least three direct subsets in declared
  order, using identical terms, order, and scale.
- A documented example renders the three corresponding complements and proves
  each membership set equals `U - S`.
- An overlapping-selector fixture records the correct pairwise intersections
  and produces no partition claim.
- Common-reference and per-panel complement overlays reject incommensurate
  values and retain color-independent distinctions.
- CSV and manifest evidence reproduce every plotted panel, selector, value,
  difference, layout decision, and output hash.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- Manual SVG/PDF review at paper and presentation dimensions, including
  grayscale inspection and a three-or-more-panel wrapping case.

## Risk Notes

- Many panels can make labels too small; set and test a bounded default column
  count and deterministic wrapping rather than shrinking without limit.
- Overlapping genres can be mistaken for a partition; expose intersections and
  state membership semantics in the manifest and caption guidance.
- A single extreme panel can compress the rest on a shared scale; retain the
  common default for honest comparison and require an explicit, visible opt-in
  for per-panel scales.
- Complement panels can be misread if `U` changes; bind all panels to one
  universe fingerprint and reject mixed universes.

## Dependencies / Order

Starts after `WI-VISUALIZE-0091` supplies aligned comparison tables and
selector/provenance semantics and `WI-VISUALIZE-0092` supplies the two-series
rendering primitives. It blocks the multi-subset portion of
`WI-VISUALIZE-0094` but is independent of rich-token collection and may ship
before POS-aware figures.
