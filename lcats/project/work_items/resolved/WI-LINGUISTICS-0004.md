---
resolution: "Implemented and merged in PR #376 (commit 0fb3d86105037262c9bffb3cebdd3e72ef5b71da)."
blocked_reason: null
blocked: false
id: WI-LINGUISTICS-0004
title: Run full-corpus linguistics experiment with copied bucket snapshot
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
  - lcats/project/work_items/resolved/WI-LINGUISTICS-0002.md
  - lcats/project/work_items/resolved/WI-LINGUISTICS-0003.md
  - lcats/docs/how-to/run-linguistics.md
  - lcats/docs/reference/linguistics-sidecar.md
  - experiments/06_linguistics_genre_sample/
depends_on:
  - WI-LINGUISTICS-0001
  - WI-LINGUISTICS-0002
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
  - write_docs
  - create_report
forbidden_actions:
  - run_local_genre_model_census
  - make_paid_api_calls
  - write_corpus_sidecars
  - promote_sidecars
  - include_token_detail_by_default
  - modify_linguistics_schema
  - modify_linguistics_runner
  - force_push
  - delete_branch
acceptance:
  - A new experiments/07_linguistics_corpora/ directory discovers every current corpora/**/story.json deterministically and records the inspected corpus commit
  - The experiment copies all discovered source story buckets into results/copied_buckets/ and runs lcats linguistics against those copied story.json files
  - The full run writes compact linguistics.json sidecars beside copied story.json files, with no linguistics sidecars written under corpora/
  - The experiment writes story-list.txt, snapshot_manifest.json, linguistics_run_summary.json, and experiment_report.json with counts, elapsed time, backend/model provenance, failures, and corpus-write safety checks
  - Tests exercise fixture discovery, copied-bucket snapshotting, pre-analysis snapshot provenance, resume provenance validation, sidecar placement, resume/overwrite behavior, failure reporting, and no-corpus-write checks without requiring spaCy, network access, paid APIs, or the full corpus
  - python experiment tests from the repository root, package scripts from lcats/, and lrh validate pass
required_evidence:
  - test_output
  - lrh_validate
  - validation_output
  - manual_review
artifacts_expected:
  - experiments/07_linguistics_corpora/
  - experiments/07_linguistics_corpora/README.md
  - experiments/07_linguistics_corpora/run_linguistics_corpora.py
  - experiments/07_linguistics_corpora/run_linguistics_corpora_test.py
  - experiments/07_linguistics_corpora/results/
  - experiments/README.md
---

# Work Item: WI-LINGUISTICS-0004

## Summary

Run `lcats linguistics` over the full current LCATS corpus using an
experiment-local copied-bucket snapshot, and commit the resulting compact
linguistic sidecars, run summary, and performance report without writing
generated sidecars into `corpora/`.

## Problem / Context

`WI-LINGUISTICS-0001` delivered the standalone linguistic sidecar
infrastructure, `WI-LINGUISTICS-0002` proved the copied-bucket experiment
pattern on the 146-story genre-balanced sample, and `WI-LINGUISTICS-0003`
added output-root support for cases where generated sidecars should be
separated from source buckets. For this full-corpus run, the preferred
artifact is a durable experiment snapshot: each copied story bucket should
contain the exact `story.json` used as input plus the generated
`linguistics.json` beside it, preserving the normal LCATS bucket structure
for downstream tools.

The run should be local NLP only and is expected to fit in an overnight
window. It must not run the local LLM genre census, make paid API calls,
write sidecars into `corpora/`, or promote any experimental sidecars into
the main corpus.

### Duplication search

- In-repo: Related but not duplicate. `experiments/06_linguistics_genre_sample/`
  already runs `lcats linguistics` over the 146-story `WI-GENRE-0004`
  sample using copied buckets. `lcats linguistics --output-root` already
  supports redirected sidecars, but no experiment runs linguistics over the
  full corpus while preserving copied input buckets as the result snapshot.
- Sibling repos: No sibling repository was identified for this LCATS-specific
  experiment run.
- External libraries: spaCy supplies the local NLP backend, but no external
  library replaces LCATS story-bucket copying, sidecar validation, deterministic
  run summaries, or experiment reporting.
- Recommendation: Proceed by adapting the `experiments/06_linguistics_genre_sample/`
  pattern to a full-corpus experiment.

### Demand search

- Work items: No proposed work item was found for this exact full-corpus
  linguistics snapshot run. Prior linguistics work explicitly deferred
  measuring performance over longer story sets.
- Proposals: No proposed design was found for this exact experiment. The
  proposed `lcats-run-log` design notes that `lcats linguistics` usually does
  not need separate run-log infrastructure because per-story sidecars and
  fingerprint-based skip behavior already provide implicit checkpointing.
- Backlog: No matching backlog entry was found beyond deferred performance
  measurement noted in the linguistics documentation.
- Recommendation: Proceed with a single focused evaluation work item.

## Scope

- Create `experiments/07_linguistics_corpora/` as the next numbered experiment.
- Discover every current canonical `corpora/**/story.json` story
  deterministically from the repository root.
- Copy each full source story bucket into
  `experiments/07_linguistics_corpora/results/copied_buckets/<collection>/<story>/`.
- Run `lcats linguistics` against the copied `story.json` paths with a local
  spaCy backend and compact sidecars only.
- Preserve normal bucket layout by writing `linguistics.json` beside copied
  `story.json` files.
- Write deterministic story-list, run-summary, and experiment-report artifacts.
- Write source snapshot provenance and inventory before analysis begins, so an
  interrupted or resumed run cannot falsely attribute copied buckets to a later
  checkout.
- Include elapsed-time and corpus-size measurements sufficient to evaluate
  full-corpus linguistics performance.
- Add deterministic fixture tests with the fake NLP backend.

## Required Changes

1. Create `experiments/07_linguistics_corpora/README.md` documenting the
   experiment purpose, copied-bucket snapshot layout, local NLP setup, smoke
   command, overnight full-run command, expected outputs, validation commands,
   and promotion boundary.
2. Create `experiments/07_linguistics_corpora/run_linguistics_corpora.py`
   with helpers that:
   - discover `corpora/**/story.json` deterministically;
   - optionally limit to `--smoke-count N`;
   - copy each full story bucket into `results/copied_buckets/`;
   - write `results/story-list.txt` pointing at copied `story.json` files;
   - write `results/snapshot_manifest.json` before running linguistics,
     including the source commit SHA, source story inventory, copied story
     paths, and source/copied `story.json` hashes;
   - run `lcats.analysis.linguistics.runner` or the established CLI behavior
     against the copied stories without `--output-root`;
   - write `results/linguistics_run_summary.json`;
   - write `results/experiment_report.json` with counts, elapsed time, commit
     SHA, backend/model, snapshot/output sizes, run-clean status, failure list,
     copied bucket root, story-list path, and no-corpus-write diagnostics.
3. Support safe execution modes:
   - default behavior refuses to mix with a pre-existing copied snapshot unless
     explicitly resuming or overwriting;
   - `--resume` or equivalent preserves the existing snapshot manifest,
     validates copied-bucket inventory and hashes against that manifest, and
     uses the linguistics runner's `--existing skip` semantics to continue an
     interrupted run without deriving source provenance from the resumed
     checkout;
   - `--overwrite` prunes stale copied buckets/results and rebuilds from the
     current corpus snapshot.
4. Run a small spaCy smoke pass before the full run to verify local model
   availability.
5. Run the full corpus pass with spaCy, compact sidecars only, and commit the
   resulting experiment artifacts under `experiments/07_linguistics_corpora/results/`.
6. Add `experiments/07_linguistics_corpora/run_linguistics_corpora_test.py`
   with fixture/fake-backend tests for discovery, complete bucket copying,
   sidecar placement beside copied stories, story-list determinism, no-corpus
   writes, skip/resume, overwrite pruning, and per-story failure reporting.
7. Update `experiments/README.md` to list experiment 07.

## Non-Goals

- Do not run the full local LLM genre census.
- Do not make paid API calls or require an LLM.
- Do not write `linguistics.json` or `linguistics.tokens.json` into `corpora/`.
- Do not promote generated linguistic sidecars into the main corpus.
- Do not enable `--include-token-detail` by default or commit token-detail
  artifacts unless explicitly added by a future work item.
- Do not change `linguistics-sidecar-v1`, `linguistics-run-summary-v1`, or
  the default `lcats linguistics` behavior.
- Do not reopen or mutate any other resolved workstream.

## Acceptance Criteria

- `experiments/07_linguistics_corpora/` exists with README, runner script,
  deterministic tests, and checked-in result artifacts.
- The experiment discovers all current corpus stories and records both the
  source story count and inspected commit SHA.
- The experiment writes snapshot provenance and story inventory before analysis
  begins, and `--resume` preserves and validates that provenance rather than
  replacing it with the resumed checkout's commit SHA.
- `results/copied_buckets/<collection>/<story>/story.json` preserves the input
  bucket snapshot, and `linguistics.json` is written beside each copied story.
- `results/story-list.txt`, `results/snapshot_manifest.json`,
  `results/linguistics_run_summary.json`, and `results/experiment_report.json`
  are deterministic and machine-readable.
- The full run reports clean completion, copied story count, sidecar count,
  elapsed wall time, backend/model provenance, and any failures.
- The report confirms no generated linguistics sidecars were written under
  `corpora/`.
- Fixture tests cover copy, resume, overwrite, failure, and no-corpus-write
  behavior, including resume refusal on snapshot provenance or hash mismatch,
  without requiring real spaCy or network access.
- Required validation commands pass.

## Validation

Run experiment commands from the repository root:

- `python experiments/07_linguistics_corpora/run_linguistics_corpora_test.py`
- `python experiments/07_linguistics_corpora/run_linguistics_corpora.py --backend fake --smoke-count 2 --overwrite`
- `python experiments/07_linguistics_corpora/run_linguistics_corpora.py --backend spacy --smoke-count 5 --overwrite`
- `python experiments/07_linguistics_corpora/run_linguistics_corpora.py --backend spacy --overwrite`
- `find corpora -path '*linguistics.json' -o -path '*linguistics.tokens.json' | wc -l`
- `find experiments/07_linguistics_corpora/results/copied_buckets -name linguistics.json | wc -l`

Run package checks from `lcats/` using the project Python environment:

- `(cd lcats && scripts/format --check --diff)`
- `(cd lcats && scripts/lint)`
- `(cd lcats && scripts/test)`
- `(cd lcats && lrh validate)`

## Dependencies / Order

This item depends on `WI-LINGUISTICS-0001` for the standalone sidecar runner
and `WI-LINGUISTICS-0002` for the copied-bucket experiment precedent. It does
not depend on `WI-LINGUISTICS-0003` because this experiment deliberately uses
beside-story sidecars in copied buckets, but the work item links it as related
context because it documents when output-root redirection is preferable.

## Related Workstream and Designs

- Workstream: `lcats/project/workstreams/proposed/WS-LINGUISTICS.md`
- Prior sample experiment: `experiments/06_linguistics_genre_sample/`
- Linguistics how-to: `lcats/docs/how-to/run-linguistics.md`
- Linguistics schema reference: `lcats/docs/reference/linguistics-sidecar.md`

## Risk Notes

- The run is larger than the 146-story sample and may take roughly an hour or
  more depending on local spaCy/model performance; the script should record
  elapsed time and remain resumable.
- Mixing a new source snapshot with old sidecars would undermine the experiment,
  so snapshot provenance must be written before analysis and resume/overwrite
  semantics must be explicit and tested.
- Copying the full corpus currently duplicates roughly 58 MB of story-bucket
  data, which is acceptable for an experiment snapshot but should be called out
  in the report.
- Downstream tools may assume normal story-bucket layout; keeping sidecars
  beside copied stories reduces that risk, but the report must still make clear
  that these are experiment artifacts, not promoted corpus sidecars.
