---
resolution: null
blocked_reason: null
blocked: false
id: WI-VISUALIZE-0094
title: Dogfood and package comparative lexical paper figures
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
  - WI-VISUALIZE-0092
  - WI-VISUALIZE-0093
  - WI-VISUALIZE-0095
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
  - cherry_pick_preferred_results
  - omit_manifest_or_csv
  - claim_statistical_significance
  - require_full_corpus_rich_run
acceptance:
  - A preregistered figure matrix covers whole-corpus and 146-story universes, science-fiction versus reference and complement, mirrored, overlay, and aligned multi-subset styles, and agreed raw/normalized/TF-IDF/stopword variants; noun variants are included only when the pilot authorizes them
  - Every committed final figure has adjacent authoritative CSV and comparison manifest with exact selections, denominators, filters, vocabulary/order, revisions, model provenance where applicable, and output hashes
  - Figures are reviewed for numerical agreement, readable labels, grayscale/color-blind interpretation, vector rendering, and consistent paper/presentation typography
  - The report records unsuccessful or rejected variants and selection rationale rather than cherry-picking unexplained outputs
  - Reproduction commands and tests pass, and the package does not depend on a full-corpus rich run unless that run was separately approved and completed
required_evidence:
  - test_output
  - validation_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - experiments/08_visualize_dogfood/
  - experiments/08_visualize_dogfood/results/comparative_lexical/
  - experiments/08_visualize_dogfood/results/comparative_lexical/figure_index.json
  - experiments/08_visualize_dogfood/README.md
---

# Work Item: WI-VISUALIZE-0094

## Summary

Dogfood the comparative lexical pipeline against real LCATS data and package a
reviewed, reproducible set of paper and presentation figures with their
authoritative tables and manifests.

## Problem / Context

Library and CLI tests do not establish which combinations communicate the
paper’s argument most clearly. The project needs a bounded figure matrix that
compares the whole corpus and fixed 146-story universe, toggles full-reference
versus complement, tests count/normalized/TF-IDF and stopword/POS variants, and
records why final figures were selected.

### Duplication search

- In-repo: experiment 08 already hosts visualization dogfooding and should be
  extended or given a clearly linked result subtree; it does not contain these
  two-series or noun figures.
- Sibling repos: none identified.
- External libraries: no external artifact replaces LCATS real-data
  dogfooding and paper-specific review.
- Recommendation: extend experiment 08 rather than create an unrelated chart
  gallery.

### Demand search

- Work items: no open duplicate; predecessor visualization work items establish
  the real-output and README convention.
- Proposals: the governing proposal identifies the paper/presentation package
  as the destination.
- Backlog: no matching entry.
- Recommendation: proceed after renderer and POS integration.

## Scope

- Preregistered real-data figure matrix and reproduction commands.
- Whole-corpus and 146-story science-fiction reference/complement comparisons.
- Mirrored/overlay/multi-subset, metric, stopword, term-form, and noun variants.
- Numerical, accessibility, vector-output, and editorial review.
- Final indexed package with rejected-variant rationale.

## Required Changes

1. Define the figure matrix before final selection, including universes,
   selectors, complement toggle, metric/denominator, vocabulary controller,
   stopword policy, term form, POS set, style, dimensions, and output formats.
2. Generate immediate non-POS figures from current corpus text and the fixed
   sample; include an aligned several-subset or several-complement figure; add
   noun figures only from pilot-authorized lexical artifacts, or record their
   evidence-backed omission after a defer/no-go outcome.
3. Store each figure beside CSV and manifest; build `figure_index.json` with
   title, intended claim, status, paths, command, and review notes.
4. Verify plotted values against CSV, selectors against story lists, and output
   hashes/revisions against manifests.
5. Review grayscale/color-blind legibility, hatch/line distinction, label
   density, font embedding/vector quality, and paper/presentation aspect ratios.
6. Update experiment documentation with exact reproduction commands, selected
   and rejected variants, limitations, and the no-significance caveat.

## Non-Goals

- Do not choose final figures without recording the tested matrix and rationale.
- Do not omit data/manifests for presentation-only images.
- Do not claim that excess/deficit or TF-IDF contrast is statistically
  significant.
- Do not require the conditional full-corpus rich run for sample noun figures.
- Do not modify source corpus or genre evidence.

## Acceptance Criteria

- All frontmatter acceptance conditions are verified in the experiment report.
- At minimum, final candidates include science fiction versus all 146 and
  science fiction versus the 126-story sample complement.
- At least one final candidate compares several ordered subsets or their
  universe-relative complements using one aligned vocabulary and term order.
- When authorized, noun figures explicitly distinguish `NOUN` from `PROPN`
  policy; after defer/no-go, the package records the omission and links the
  pilot decision instead of treating noun figures as required.
- Selected figures reproduce from documented commands in a clean output path.
- Editorial review identifies which figure/variant serves each paper claim.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `python ../experiments/08_visualize_dogfood/run_comparative_lexical.py --check`

## Risk Notes

- A large matrix invites selective reporting; preregister it and retain rejected
  outputs or their recorded summaries.
- Counts from unequal corpora need normalized companions and explicit
  denominators.
- Publication typography can regress independently of numerical correctness;
  review both raster and vector outputs.

## Dependencies / Order

Starts after the renderer, resolution of the POS-integration item, and the
multi-panel composer. It may incorporate noun figures only after a POS-figure
go outcome and full-corpus rich results only after `WI-LINGUISTICS-0008`
completes with a go outcome; neither conditional output blocks the package.
