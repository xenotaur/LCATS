---
resolution: null
blocked_reason: null
blocked: false
id: WI-VISUALIZE-0092
title: Add mirrored and reference-overlay comparative charts
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
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - add_cli_command
  - run_tests
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - recompute_analysis_in_renderer
  - modify_existing_visualize_defaults
  - implement_pos_pipeline
acceptance:
  - Reusable rendering APIs consume the authoritative comparison table and produce mirrored-pair and commensurate reference-overlay horizontal bar charts
  - The reference-overlay chart shows a neutral reference, target overlap, and signed excess/deficit with color-independent texture or boundary cues
  - A thin lcats visualize compare CLI accepts a comparison specification through documented options and writes PNG, SVG, CSV, and comparison_manifest.json outputs
  - Mirrored charts clearly label independent axes when metrics differ, while overlay requests fail on incompatible metrics or denominators
  - Rendering, CLI, manifest, and real-corpus smoke tests pass without changing existing visualize behavior
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - src/lcats/visualize/rendering.py
  - src/lcats/visualize/cli.py
  - tests/visualize_tests/
  - docs/how-to/run-visualize.md
  - docs/reference/cli-commands.md
---

# Work Item: WI-VISUALIZE-0092

## Summary

Implement the paper-facing mirrored-pair and gray-reference overlay charts and
expose them through a thin, reproducible `lcats visualize compare` command.

## Problem / Context

Side-by-side or mirrored bars make exact term alignment visible, but differences
can still be hard to perceive. The approved reference-overlay variant mirrors
the comparison baseline onto the target side, draws the target over it, and
marks excess or deficit. Rendering must consume the table defined by
`WI-VISUALIZE-0091`; it must not recalculate metrics or quietly reinterpret
selectors.

### Duplication search

- In-repo: `rendering.py` and `graph_plotters.py` provide Matplotlib primitives,
  but no two-series mirrored or reference-overlay lexical renderer exists.
- Sibling repos: none identified.
- External libraries: Matplotlib supports all required primitives; no new chart
  dependency is justified.
- Recommendation: extend existing Matplotlib rendering APIs.

### Demand search

- Work items: no open item; this builds on resolved visualization items and the
  new analysis contract.
- Proposals: explicitly required by the governing proposal.
- Backlog: no matching open entry.
- Recommendation: proceed.

## Scope

- Mirrored horizontal paired bars.
- Reference-overlay bars with overlap and signed difference encodings.
- Thin CLI orchestration and complete data/manifest outputs.
- Accessible styling, vector output, tests, docs, and a real smoke example.

## Required Changes

1. Add renderer functions that accept the aligned comparison table, labels,
   style parameters, and output settings without performing analysis.
2. Implement mirrored left/right bars with shared term order, central labels,
   explicit zero/baseline, and independent labelled scales when permitted.
3. Implement a neutral gray reference overlay plus narrower/hatched target,
   visible excess/deficit region, signed values, legend, and color-independent
   cues.
4. Add `lcats visualize compare` options for universes, selectors, complement,
   metrics, filters, vocabulary, ordering, style, and output formats by mapping
   them to `ComparisonSpec`.
5. Write PNG/SVG (and optional PDF), authoritative CSV, and complete manifest;
   update visualization documentation and CLI reference.
6. Add numerical/structural renderer tests, CLI integration tests, and at
   least one non-committed-output real-corpus smoke run.

## Non-Goals

- Do not duplicate selector or analysis logic in rendering or CLI handlers.
- Do not add interactive/web visualization.
- Do not implement POS extraction or noun filtering.
- Do not use pixel-perfect snapshots as the principal correctness oracle.

## Acceptance Criteria

- Both renderers preserve the input table’s term order and numerical values.
- Reference, target, overlap, excess, and deficit remain interpretable in
  grayscale.
- CSV and manifest exactly describe the plotted data and configuration.
- Invalid overlay combinations fail before a figure is written.
- Existing visualization tests and real commands continue to pass unchanged.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `lcats visualize compare --help`
- `lcats visualize compare --universe manifest --manifest ../experiments/05_metadata_genre_prefilter/results/full_scan/genre_balanced_manifest.jsonl --right-genre "science fiction" --right-reference complement --metric per_million --output-dir /tmp/lcats_compare_smoke`

## Risk Notes

- A visually attractive overlap is misleading unless units match; rely on the
  comparison validator and repeat units in axis/legend text.
- Dense labels become unreadable; test bounded top-N layouts and long terms.
- Hatching can inflate vector files; keep styles simple and configurable.

## Dependencies / Order

Begins after `WI-VISUALIZE-0091`; it intentionally does not wait for the
linguistics lane, so count/TF-IDF figures can be collected immediately.
