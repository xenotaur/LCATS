---
resolution: "Implemented and merged in PR #353 at fd050d710e83330cc2eec7d0724d1dd17af158b7."
blocked_reason: null
blocked: false
id: WI-LINGUISTICS-0002
title: Run linguistics over the WI-GENRE-0004 sample in experiment-local copied buckets
type: evaluation
status: resolved
priority: high
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams:
  - WS-LINGUISTICS
related_design:
  - lcats/project/work_items/resolved/WI-LINGUISTICS-0001.md
  - lcats/project/work_items/resolved/WI-GENRE-0004.md
  - lcats/docs/how-to/run-linguistics.md
  - lcats/docs/reference/linguistics-sidecar.md
depends_on:
  - WI-LINGUISTICS-0001
  - WI-GENRE-0004
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
  - write_docs
  - create_report
forbidden_actions:
  - write_corpus_sidecars
  - promote_sidecars
  - modify_linguistics_runner_output_root
  - make_paid_api_calls
  - modify_genre_sample_manifest
  - force_push
  - delete_branch
acceptance:
  - A new experiment directory reads the 146-row WI-GENRE-0004 genre_balanced_manifest.jsonl from experiments/05_metadata_genre_prefilter/results/full_scan/
  - The experiment copies sampled story buckets into an experiment-local mirror before running lcats linguistics, so corpora/ is not modified
  - A small smoke run verifies local spaCy/backend availability before the full sample run
  - The full run writes linguistics.json sidecars beside copied story.json files plus a machine-readable run summary and concise experiment report
  - Tests exercise the experiment script with fixtures/fake backend and do not require network, paid APIs, or real spaCy models
  - scripts/format --check --diff, scripts/lint, scripts/test, and lrh validate pass
required_evidence:
  - test_output
  - lrh_validate
  - validation_output
  - manual_review
artifacts_expected:
  - experiments/06_linguistics_genre_sample/
  - experiments/06_linguistics_genre_sample/README.md
  - experiments/06_linguistics_genre_sample/run_linguistics_sample.py
  - experiments/06_linguistics_genre_sample/results/
  - experiments/06_linguistics_genre_sample/run_linguistics_sample_test.py
---

# Work Item: WI-LINGUISTICS-0002

## Summary

Run `lcats linguistics` over the 146-story `WI-GENRE-0004` genre-balanced
sample using an experiment-local mirror of the sampled story buckets, and
commit the resulting deterministic run summary/report without writing generated
linguistic sidecars into `corpora/`.

## Problem / Context

`WI-LINGUISTICS-0001` delivered the standalone `lcats linguistics` command and
explicitly deferred the `WI-GENRE-0004` manifest adapter and selected Worldcon
sample run. `WI-GENRE-0004` has now resolved that prerequisite by writing the
validated 146-story manifest at
`experiments/05_metadata_genre_prefilter/results/full_scan/genre_balanced_manifest.jsonl`.

The central implementation constraint is output location. The current
linguistics runner writes `linguistics.json` directly beside whatever
`story.json` path it is given. Running against `corpora/` would therefore
create generated sidecars in the tracked corpus. For this experiment, use the
confirmed option 1: copy the selected story buckets into an experiment-local
mirror first, preserving the exact story state that produced the output while
keeping `corpora/` untouched.

### Duplication search

- In-repo: `experiments/05_metadata_genre_prefilter` owns sample selection and
  genre validation, not linguistic feature extraction. `lcats linguistics`
  already provides the sidecar writer, but no experiment runs it over the
  `WI-GENRE-0004` sample. The replay fixture under
  `experiments/03_cross_segment_relation_pilot/results/segmentation_paragraph_misnumbering_diagnostics/replay_fixture/`
  is related prior art for copying real story buckets into an experiment-local
  layout.
- Sibling repos: No sibling repository was identified for this LCATS-specific
  experiment run.
- External libraries: spaCy is the intended local NLP backend, but it does not
  replace the LCATS experiment harness, bucket mirroring, sidecar validation,
  or run reporting.
- Recommendation: Proceed by wrapping the existing `lcats linguistics`
  command/API in an experiment-local copied-bucket runner.

### Demand search

- Work items: `WI-LINGUISTICS-0001` explicitly defers the selected Worldcon
  sample run. `WI-GENRE-0004` supplies the manifest this item consumes.
- Proposals: The adopted story-bucket and pipeline-checkpointing proposals
  provide conventions for per-story artifacts and resumable runs.
- Backlog: No separate backlog entry was found beyond the deferred work already
  captured in the linguistics docs and resolved work item.
- Recommendation: Proceed and link to `WS-LINGUISTICS`.

## Scope

- Create a new experiment directory for the linguistics sample run.
- Read the 146-row `genre_balanced_manifest.jsonl` emitted by
  `WI-GENRE-0004`.
- Copy each sampled story bucket into an experiment-local mirror before
  analysis, preserving collection/story layout and source story content.
- Run `lcats linguistics` over the copied story paths with a local NLP backend,
  using a 2-3 story smoke run before the full 146-story run.
- Write a machine-readable run summary and concise report under the experiment
  results directory.
- Add fixture-based tests using deterministic/fake backend behavior so the
  portable suite does not require spaCy models, network access, paid APIs, or
  the full real sample.

## Required Changes

1. Create `experiments/06_linguistics_genre_sample/README.md` documenting the
   sample source, copied-bucket output strategy, no-corpus-write boundary,
   local NLP setup, smoke command, full command, result files, and validation
   commands.
2. Create `experiments/06_linguistics_genre_sample/run_linguistics_sample.py`
   with functions that:
   - read `experiments/05_metadata_genre_prefilter/results/full_scan/genre_balanced_manifest.jsonl`;
   - verify expected `story_id`/`story_path` fields and selected-row count;
   - copy each sampled `<collection>/<story>/story.json` bucket into an
     experiment-local mirror;
   - write a story-list file pointing at the copied `story.json` files;
   - run `lcats linguistics` or the established runner API over that story
     list;
   - write `--summary-output` JSON and any script-level aggregate report;
   - isolate per-story failures through the linguistics runner's existing
     batch semantics.
3. Add a smoke-run mode or documented smoke invocation that runs 2-3 stories
   first with `--backend spacy` to confirm local model availability before the
   full sample is processed.
4. Add tests mirroring `experiments/05_metadata_genre_prefilter/run_prefilter_test.py`
   style: fixture manifests and fixture story buckets drive end-to-end helper
   functions, with no real spaCy dependency.
5. Record the completed full run results under the experiment's `results/`
   directory, including copied-bucket outputs, the linguistics run summary, and
   a concise implementation/run report.

## Non-Goals

- Do not write `linguistics.json` or `linguistics.tokens.json` into
  `corpora/`.
- Do not promote generated linguistic sidecars into the main corpus.
- Do not add output-root support to the shared linguistics runner; that is
  `WI-LINGUISTICS-0003`.
- Do not modify the `WI-GENRE-0004` manifest format or rerun the genre
  validation pipeline.
- Do not make paid API calls or require an LLM.
- Do not require real spaCy/Stanza models for the deterministic test suite.

## Acceptance Criteria

- The experiment reads the checked-in `WI-GENRE-0004`
  `genre_balanced_manifest.jsonl` and reports the selected story count.
- The experiment copies sampled story buckets into an experiment-local mirror
  before analysis, and no generated linguistic sidecar is written under
  `corpora/`.
- A documented 2-3 story smoke path verifies local spaCy/model availability
  before the full run.
- The full run produces compact `linguistics.json` sidecars beside copied
  story files, plus a machine-readable run summary and concise report under
  `experiments/06_linguistics_genre_sample/results/`.
- Tests cover manifest reading, copied-bucket layout, story-list generation,
  deterministic fake-backend execution, and failure reporting without network,
  paid APIs, or real spaCy models.
- The PR report states exact commands and outcomes for formatting, linting,
  tests, and LRH validation.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `python experiments/06_linguistics_genre_sample/run_linguistics_sample_test.py`
- `lrh validate`

## Dependencies / Order

This item depends on `WI-LINGUISTICS-0001` for the reusable `lcats linguistics`
command and on `WI-GENRE-0004` for the sample manifest. It should run before
any corpus-promotion work and independently of `WI-LINGUISTICS-0003`, because
the copied-bucket strategy is the confirmed near-term approach.

## Risk Notes

- spaCy package/model availability varies by environment. The experiment should
  smoke-test availability and fail with clear setup guidance rather than half
  writing a large run.
- Copying story buckets preserves output provenance but can create a sizable
  experiment artifact. The PR should report the resulting file count/size and
  justify what is checked in.
- The `story_path` and `input.source_path` fields in sidecars preserve
  invocation spelling. The experiment should use stable mirror paths so resume
  and fingerprint behavior remain reproducible.

## Related Workstream and Designs

- Workstream: `lcats/project/workstreams/proposed/WS-LINGUISTICS.md`
- Substrate: `lcats/project/work_items/resolved/WI-LINGUISTICS-0001.md`
- Sample source: `lcats/project/work_items/resolved/WI-GENRE-0004.md`
- CLI docs: `lcats/docs/how-to/run-linguistics.md`
- Schema docs: `lcats/docs/reference/linguistics-sidecar.md`
