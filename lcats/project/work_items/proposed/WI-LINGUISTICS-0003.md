---
resolution: null
blocked_reason: null
blocked: false
id: WI-LINGUISTICS-0003
title: Add output-root support to lcats linguistics sidecar writing
type: deliverable
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
  - WS-LINGUISTICS
related_design:
  - lcats/project/work_items/resolved/WI-LINGUISTICS-0001.md
  - lcats/docs/reference/linguistics-sidecar.md
depends_on:
  - WI-LINGUISTICS-0001
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
  - create_pr
  - write_docs
forbidden_actions:
  - run_worldcon_sample
  - write_corpus_sidecars
  - promote_sidecars
  - change_default_output_location
  - make_paid_api_calls
  - force_push
  - delete_branch
acceptance:
  - lcats linguistics can optionally redirect sidecar output under an explicit output root while preserving default beside-story behavior
  - Redirected outputs preserve enough story identity/provenance to validate and reproduce the source story/body hash
  - Existing skip/validate/overwrite semantics remain deterministic for both beside-story and redirected outputs
  - Tests cover redirected output paths, collisions, resume behavior, and unchanged default behavior
  - Documentation explains when to use copied buckets versus output-root redirection
  - scripts/format --check --diff, scripts/lint, scripts/test, and lrh validate pass
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - lcats/src/lcats/analysis/linguistics/runner.py
  - lcats/src/lcats/analysis/corpus/linguistics_cli.py
  - lcats/tests/analysis_tests/linguistics_test.py
  - lcats/docs/how-to/run-linguistics.md
  - lcats/docs/reference/linguistics-sidecar.md
---

# Work Item: WI-LINGUISTICS-0003

## Summary

Add explicit output-root support to `lcats linguistics` so callers can redirect
generated linguistic sidecars away from source story buckets while preserving
the current beside-story default behavior.

## Problem / Context

`WI-LINGUISTICS-0001` intentionally kept the first standalone runner simple:
`run_story()` writes `linguistics.json` and optional token detail beside the
input story's own `story.json`. That is the right default for local story
buckets, but it forces experiment authors to copy story buckets when they need
sidecar-shaped output without touching `corpora/`.

For the immediate `WI-GENRE-0004` sample run, the confirmed approach is still
to copy sampled buckets (`WI-LINGUISTICS-0002`) because that also preserves the
exact input state that produced the output. This item captures the separate,
shared infrastructure improvement so future experiments can choose explicit
redirection without silently expanding the sample-run scope.

### Duplication search

- In-repo: `lcats.analysis.linguistics.runner` already resolves stories and
  writes sidecars, but hardcodes the sidecar path under `story_path.parent`.
  No output-root or redirect option exists in the runner, CLI, or docs.
- Sibling repos: No sibling repository was identified for this LCATS-specific
  sidecar writer behavior.
- External libraries: No external library replaces the project-specific need
  to map LCATS story identity and sidecar provenance into a redirected output
  tree.
- Recommendation: Proceed with a small shared-runner enhancement, separate
  from the sample-run experiment.

### Demand search

- Work items: `WI-LINGUISTICS-0001` and its documentation name the later
  manifest/sample adapter and corpus-promotion workflow as deferred; this item
  captures the output-location piece exposed by that follow-up.
- Proposals: The adopted story-bucket and pipeline-checkpointing proposals
  provide path/provenance and atomic-output conventions relevant to the design.
- Backlog: No separate backlog entry was found.
- Recommendation: Proceed under `WS-LINGUISTICS`.

## Scope

- Add an opt-in output-root or equivalent redirect parameter to the
  linguistics runner and CLI.
- Preserve the existing default behavior: without the new option, sidecars are
  still written beside each input `story.json`.
- Define redirected path semantics that avoid collisions across collections and
  retain enough provenance to validate/reproduce source input.
- Keep existing skip, validate, overwrite, token-detail, atomic-write, and run
  summary behavior deterministic under both default and redirected modes.
- Update tests and docs for the new output-location behavior.

## Required Changes

1. Extend `src/lcats/analysis/linguistics/runner.py` with a narrowly scoped
   output-root option or path-mapping hook for compact and token-detail
   sidecars.
2. Extend `src/lcats/analysis/corpus/linguistics_cli.py` with a CLI flag for
   the opt-in output location, including clear help text about default
   beside-story behavior.
3. Define collision behavior for redirected outputs. At minimum, collection
   and story identity must remain part of the redirected path or manifest so
   two same-slug stories from different collections cannot overwrite one
   another.
4. Preserve current validation, resume, skip, and overwrite behavior. Existing
   output checks must use the redirected target when redirection is active and
   the beside-story target otherwise.
5. Update `tests/analysis_tests/linguistics_test.py` for redirected compact
   sidecars, redirected token-detail files, collision/path behavior, stale
   output handling, and unchanged default behavior.
6. Update `docs/how-to/run-linguistics.md` and
   `docs/reference/linguistics-sidecar.md` to describe when output-root
   redirection is appropriate and when copied-bucket mirrors remain preferable.

## Non-Goals

- Do not run the `WI-GENRE-0004` Worldcon sample; that is
  `WI-LINGUISTICS-0002`.
- Do not change the default beside-story output location.
- Do not write generated sidecars into `corpora/` as part of this work item.
- Do not promote generated linguistic sidecars into the main corpus.
- Do not make paid API calls or add LLM dependencies.
- Do not broaden this into a general workflow framework.

## Acceptance Criteria

- `lcats linguistics` can redirect compact and optional token-detail outputs
  under an explicit output root.
- Omitting the new option preserves byte-for-byte compatible default behavior
  for existing tests/fixtures where applicable.
- Redirected outputs preserve source story identity, source path/body hash, and
  backend/options provenance in schema-valid sidecars and run summaries.
- Existing-output modes (`skip`, `validate`, `overwrite`) work deterministically
  against redirected targets.
- Tests cover redirected output, token detail, path/collision behavior,
  existing-output modes, and unchanged default behavior.
- Documentation explains the tradeoff between copied-bucket experiments and
  output-root redirection.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `python -m unittest tests.analysis_tests.linguistics_test`
- `lrh validate`

## Dependencies / Order

This item depends on `WI-LINGUISTICS-0001` but does not block
`WI-LINGUISTICS-0002`. The sample run should use copied buckets first because
that was the explicit user decision and because it preserves input-state
evidence. Output-root support can then land as a reusable improvement for later
experiments.

## Risk Notes

- Redirecting sidecars can make `story_path` and `input.source_path`
  semantics more visible. The implementation must document whether those
  fields continue to describe the source story path rather than the output
  location.
- A naive output-root mapping can collide for stories with identical slugs in
  different collections. Tests should include this case or a close equivalent.
- Changing existing-output lookup paths risks regressions in skip/resume
  behavior. The default mode should remain covered explicitly.

## Related Workstream and Designs

- Workstream: `lcats/project/workstreams/proposed/WS-LINGUISTICS.md`
- Substrate: `lcats/project/work_items/resolved/WI-LINGUISTICS-0001.md`
- CLI docs: `lcats/docs/how-to/run-linguistics.md`
- Schema docs: `lcats/docs/reference/linguistics-sidecar.md`
