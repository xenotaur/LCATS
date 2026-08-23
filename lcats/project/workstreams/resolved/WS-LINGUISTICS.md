---
id: WS-LINGUISTICS
kind: planning_node
title: Linguistic Feature Sidecars and Worldcon Sample Runs
status: resolved
stage: closed
origin: follow_up
summary: Coordinate standalone LCATS linguistic-feature sidecar infrastructure, experiment-local Worldcon sample runs, and later output-location improvements.
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_design:
  - lcats/project/design/proposals/adopted/lcats-story-bucket-layout/00_proposal.md
  - lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md
work_items:
  - WI-LINGUISTICS-0001
  - WI-LINGUISTICS-0002
  - WI-LINGUISTICS-0003
exit_criteria:
  - WI-LINGUISTICS-0001 remains resolved and linked to this workstream
  - The WI-GENRE-0004 146-story sample has an experiment-local copied-bucket linguistics run with checked-in summary/report artifacts
  - lcats linguistics has a reviewed output-redirection design or implementation path captured separately from the sample-run experiment
  - Documentation clearly distinguishes experiment-local linguistic sidecars from any later corpus-promotion workflow
  - All work items resolved and lrh validate reports 0 errors
---

# Workstream: Linguistic Feature Sidecars and Worldcon Sample Runs

## Purpose

This workstream coordinates the standalone linguistic-feature sidecar path for
LCATS. It retroactively groups the resolved infrastructure work from
`WI-LINGUISTICS-0001` with the next two deliberately deferred follow-ups:
running the now-available `WI-GENRE-0004` genre-balanced sample in an
experiment-local copied-bucket mirror, and separately improving output
location support for future runs.

The workstream exists now because the generic `lcats linguistics` command has
landed, the 146-story genre-balanced sample has landed, and the documentation
from PR #336 explicitly names both the sample run and a later manifest/output
adapter as deferred work. Capturing the stream keeps the experiment run,
shared-runner improvement, and any later corpus-promotion decision separate.

## Scope

- Maintain the standalone `linguistics-sidecar-v1` infrastructure delivered by
  `WI-LINGUISTICS-0001` as the reusable substrate.
- Run `lcats linguistics` over the `WI-GENRE-0004` 146-story sample using an
  experiment-local copied-bucket mirror so the exact story state that produced
  the output is preserved without writing sidecars into `corpora/`.
- Capture output-root or output-redirection support as a separate shared
  infrastructure work item rather than silently expanding the sample-run
  experiment.
- Keep documentation and experiment reports clear about local sidecars,
  deterministic provenance, and the boundary between experiment-local outputs
  and any later corpus-promotion workflow.

## Prior Art Check

### Duplication search

- In-repo: `WI-LINGUISTICS-0001` already delivered the reusable sidecar
  infrastructure and CLI, but it is resolved and has no related workstream.
  `WS-GENRE-EVIDENCE-SIDECARS` owns genre-evidence sidecars, not linguistic
  feature extraction. No existing workstream coordinates linguistic-feature
  sidecars, the deferred Worldcon sample run, or output-location improvements.
- Sibling repos: No sibling repository was identified for this
  project-specific LCATS sidecar planning stream.
- External libraries: spaCy and Stanza provide NLP analysis behind LCATS's
  backend abstraction, but no external library replaces LCATS's sidecar,
  story-bucket, experiment-output, and LRH planning conventions.
- Recommendation: Proceed with a dedicated LCATS linguistics workstream.

### Demand search

- Work items: `WI-LINGUISTICS-0001` names the `WI-GENRE-0004` manifest
  adapter, selected Worldcon sample run, performance measurement, and later
  corpus-promotion workflow as follow-ups. `WI-GENRE-0004` has since resolved
  the sample prerequisite.
- Proposals: The adopted story-bucket and pipeline-checkpointing proposals
  provide relevant sidecar and atomic-output conventions, but no proposal
  defines this whole linguistic-feature run sequence.
- Backlog: No matching backlog entry was found beyond the explicit deferred
  work already recorded in the linguistics documentation and resolved work
  item.
- Recommendation: Proceed, linking `WI-LINGUISTICS-0001` and adding focused
  follow-up work items.

## Work Items

- **WI-LINGUISTICS-0001** - Build standalone linguistic-feature sidecar
  extraction. Resolved in PR #325; linked here retroactively as the substrate
  for this stream.
- **WI-LINGUISTICS-0002** - Run linguistics over the `WI-GENRE-0004` sample in
  experiment-local copied buckets. This owns the immediate sample execution
  using option 1 from the handoff: copy sampled story buckets first, then run
  `lcats linguistics` against the mirror.
- **WI-LINGUISTICS-0003** - Add output-root support to `lcats linguistics`
  sidecar writing. This owns the shared runner/CLI improvement separately from
  the sample-run experiment.

## Exit Criteria

- `WI-LINGUISTICS-0001` is resolved and names `WS-LINGUISTICS` in its
  `related_workstreams` list.
- The `WI-GENRE-0004` sample run exists as an experiment-local copied-bucket
  output with a manifest, run summary, report, and tests, and no generated
  linguistic sidecars are written into `corpora/`.
- The output-redirection question is resolved through a separate reviewed work
  item, either by implementing explicit output-root support or recording a
  design decision not to add it.
- Documentation clearly explains when to use copied-bucket experiment mirrors,
  when to use any output-root feature, and why corpus promotion remains a
  separate later gate.
- All listed work items are resolved and `lrh validate` reports 0 errors.

## Non-Goals

- This workstream does not implement Knight/Novum science-fiction sidecars or
  adjudication.
- It does not alter the `WI-GENRE-0004` sample manifest or rerun paid genre
  validation.
- It does not write generated linguistic sidecars into `corpora/` unless a
  separate future corpus-promotion workflow explicitly authorizes that.
- It does not make paid API calls; linguistic extraction is local NLP only.
- It does not change segmentation logic or ERW event/relation extraction.

## Open Questions

- Whether `WI-LINGUISTICS-0003` should implement output-root support directly
  or first produce a narrower design note depends on the exact collision and
  provenance semantics found during implementation.
- Whether long-story performance measurement should become a fourth work item
  remains deferred until the 146-story sample run produces real local timing
  data.
