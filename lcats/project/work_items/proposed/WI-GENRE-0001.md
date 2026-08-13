---
resolution: null
blocked_reason: null
blocked: false
id: WI-GENRE-0001
title: Create metadata genre prefilter scaffold
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
  - WS-GENRE-EVIDENCE-SIDECARS
related_design:
  - lcats/project/design/proposals/proposed/genre-evidence-sidecars/00_proposal.md
  - lcats/project/workstreams/proposed/WS-GENRE-EVIDENCE-SIDECARS.md
  - lcats/src/lcats/gettenberg/cache.py
  - lcats/src/lcats/gettenberg/api.py
  - lcats/src/lcats/utils/genre.py
depends_on: []
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - run_network_or_cache_build_without_explicit_approval
  - run_model_calls
  - write_corpus_sidecars
  - promote_sidecars
  - implement_40_story_metadata_pilot
acceptance:
  - experiments/05_metadata_genre_prefilter/ exists with a documented dry-run scaffold for LCATS story discovery, Gutenberg ID parsing, cache readiness reporting, and manifest/summary output
  - The scaffold refuses to build, download, refresh, import a mutating cache module, or otherwise mutate the Gutenberg metadata cache unless a future explicitly-approved mode is added; default behavior is no-network and read-only
  - Dry-run output uses LCATS story identity as primary and records Gutenberg ID only as provenance/diagnostic data
  - The scaffold reports cache availability, cache path, missing-cache behavior, parse failures, repeated Gutenberg ID distribution, and story discovery counts without writing to data/ or corpora/
  - Unit tests cover cache-missing/read-only behavior, LCATS identity construction, Gutenberg URL/ID parsing, dry-run manifest shape, and protection against cache-directory creation without real network, model, or cache-building work
  - experiments/README.md registers experiment 05
  - scripts/test passes with no new failures
  - lrh validate reports 0 errors
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - experiments/05_metadata_genre_prefilter/README.md
  - experiments/05_metadata_genre_prefilter/run_prefilter.py
  - experiments/05_metadata_genre_prefilter/run_prefilter_test.py
  - experiments/05_metadata_genre_prefilter/results/.gitkeep
  - experiments/README.md
---

# Work Item: WI-GENRE-0001

## Summary

Create the first experiment-local scaffold for
`experiments/05_metadata_genre_prefilter`: a no-network, dry-run-first runner
that discovers LCATS stories, parses Gutenberg IDs, reports Gutenberg
metadata-cache readiness, and writes manifest/summary output without mutating
`data/`, `corpora/`, or the Gutenberg cache.

## Problem / Context

`PROP-GENRE-EVIDENCE-SIDECARS` chooses
`experiments/05_metadata_genre_prefilter/` as the first implementation slice
because it can validate LCATS identity handling, Gutenberg metadata
availability, and sampling/manifest behavior before permanent `genre.json`
sidecars or promotion semantics are changed. The proposal also requires cache
preflight plus a no-network default: the project likely has a local Gutenberg
cache outside this worktree, and the runner must report missing cache state
rather than silently downloading or rebuilding it.

The existing Gutenberg cache helper has useful read-only readiness logic in
`lcats/src/lcats/gettenberg/cache.py`, but that module creates cache
directories at import time and `ensure_gutenberg_cache()` can auto-create the
cache when missing. This work item should use a side-effect-free readiness path
for the default dry-run preflight, such as checking the configured cache path
without importing `lcats.gettenberg.cache` or first refactoring the path/ready
helpers into a non-mutating module. It must not invoke any code path that
builds, refreshes, downloads, creates cache directories, or writes the cache by
default.

### Duplication search

- In-repo: No existing `experiments/05_metadata_genre_prefilter/`
  implementation found. Related artifacts exist: `experiments/04_genre_census/`
  is model-census oriented; `lcats/src/lcats/gettenberg/cache.py` exposes cache
  path/readiness helpers; `lcats/src/lcats/utils/genre.py` contains reusable
  metadata genre rules.
- Sibling repos: None identified.
- External libraries: None identified for this scaffold. Existing project
  utilities are the right substrate.
- Recommendation: Proceed.

### Demand search

- Work items: None found for this exact scaffold. Related proposed items include
  `WI-ASSESS-0051` and `WI-LLM-0066`, but those are model-census/local-model
  tracks rather than metadata-prefilter sidecar scaffolding.
- Proposals: Found `PROP-GENRE-EVIDENCE-SIDECARS`, which explicitly requests
  `experiments/05_metadata_genre_prefilter/` first.
- Backlog: No separate backlog entry found beyond the proposal/workstream
  demand.
- Recommendation: Proceed and link this work item to
  `WS-GENRE-EVIDENCE-SIDECARS`.

## Scope

- Create the experiment 05 directory and dry-run runner.
- Discover canonical LCATS `story.json` files from `corpora/` and derive LCATS
  story IDs from bucket-relative paths.
- Parse Gutenberg IDs from story metadata/URLs for provenance and repeated-ID
  diagnostics.
- Report Gutenberg metadata cache readiness using side-effect-free checks and
  explicit cache path reporting.
- Write experiment-local dry-run artifacts only under
  `experiments/05_metadata_genre_prefilter/results/`.

## Required Changes

1. Create `experiments/05_metadata_genre_prefilter/run_prefilter.py`.
   - Default to dry-run/no-network behavior.
   - Discover corpus stories without mutating inputs.
   - Produce JSONL manifest rows keyed by LCATS story ID.
   - Include Gutenberg ID as provenance when parseable.
   - Include cache readiness fields, cache path, cache status, and warnings.
   - Do not import `lcats.gettenberg.cache` on the default dry-run preflight
     path unless that module has first been made import-side-effect-free.
   - Report repeated Gutenberg ID distribution as diagnostics only, not
     identity.
2. Create `experiments/05_metadata_genre_prefilter/run_prefilter_test.py`.
   - Use temp fixtures and fake/cache-missing paths.
   - Assert no network/cache-build path is required.
   - Assert cache-missing dry runs do not create cache root, `texts/`, `tmp/`,
     index DB, RDF archive, or other cache artifacts.
   - Cover LCATS ID derivation, Gutenberg ID parsing, manifest row shape, and
     summary shape.
3. Create `experiments/05_metadata_genre_prefilter/README.md`.
   - Document purpose, no-network default, usage, outputs, and how to sync an
     existing Gutenberg cache path before metadata enrichment.
4. Add `experiments/05_metadata_genre_prefilter/results/.gitkeep`.
5. Update `experiments/README.md` to register experiment 05.

## Non-Goals

- Do not generate metadata-rule genre assessments yet; that is the next work
  item.
- Do not select or validate the 40-story pilot yet.
- Do not call local or remote models.
- Do not write `genre.json` sidecars into `data/` or `corpora/`.
- Do not modify `lcats annotate` or `lcats promote`.
- Do not build, download, refresh, or mutate the Gutenberg metadata cache
  without a separate explicit approval path.

## Acceptance Criteria

- `experiments/05_metadata_genre_prefilter/` exists with README, runner, tests,
  and results placeholder.
- Running the scaffold in dry-run mode discovers corpus stories, emits
  experiment-local manifest/summary files, and leaves `data/`, `corpora/`, and
  cache files untouched.
- Missing or unavailable Gutenberg cache is reported as a non-fatal readiness
  state, not repaired automatically, and not materialized merely by importing
  the preflight code.
- Manifest rows use LCATS story identity as primary and Gutenberg ID only as
  provenance.
- Summary output includes story counts, cache readiness, parse-failure counts,
  and repeated Gutenberg ID diagnostics.
- `experiments/README.md` lists experiment 05.
- `scripts/test` passes with no new failures.
- `lrh validate` reports 0 errors.

## Validation

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `python experiments/05_metadata_genre_prefilter/run_prefilter.py --dry-run --output experiments/05_metadata_genre_prefilter/results/smoke`

## Risk Notes

- Accidentally importing `lcats.gettenberg.cache` can create cache directories,
  and calling `ensure_gutenberg_cache()` can trigger cache creation/download
  because the current cache module has auto-create behavior. The implementation
  should use side-effect-free cache-path handling for preflight, or first
  refactor the cache helpers so importing readiness code does not mutate the
  filesystem.
- Gutenberg IDs are collection-volume provenance, not story identity. The
  scaffold should report repeated IDs without using them as LCATS story IDs.
- This item intentionally stops before metadata-rule assessment generation so
  cache synchronization and dry-run artifact shape can be reviewed before
  deeper sampling work.
