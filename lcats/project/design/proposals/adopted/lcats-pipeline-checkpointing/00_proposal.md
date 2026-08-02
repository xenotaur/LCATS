---
id: PROP-LCATS-PIPELINE-CHECKPOINTING
type: design_proposal
title: Staged, Checkpointed Pipeline Execution for LCATS Batch Scripts
status: adopted
created_on: 2026-07-30
updated_on: 2026-08-02
implementation_status: not_started
implemented_by: []
supersedes: []
superseded_by: null
related_design:
  - lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md
  - lcats/project/design/flat_story_layout_migration_impact_report.md
  - lcats/project/workstreams/proposed/WS-EVENT-STRUCTURED-OUTPUT-RELIABILITY.md
  - lcats/project/design/proposals/adopted/lcats-story-bucket-layout/00_proposal.md
---

## Summary

Adopts a bucket-directory + file-existence checkpoint pattern —
generalizing the existing `DataGatherer.download` precedent — for LCATS's
LLM-driven batch scripts, replacing `run_pilot.py`'s current
in-memory-only, write-at-the-end architecture, which has zero
recoverability from any interruption.

## Background / Motivation

Three real `run_pilot.py` runs (~$50 total) left zero surviving
artifacts, because the script accumulates all results in memory and
writes only after its entire per-story loop finishes
(`experiments/03_cross_segment_relation_pilot/run_pilot.py`'s three
`.open("w")` write sites all come after the per-story loop completes).
Explicit vetting against 8 operational criteria this session (rate-limit
handling, a bounded small-scale trial, persistence/resume, call
estimation, logging, unit tests) found `run_pilot.py` fails both hard
blockers a resumed real run must clear: a minimal real run costs
~98-479 LLM calls (not "a few dozen" as initially estimated), and a
crash or Ctrl-C (which is not an `Exception` subclass and so escapes the
script's `except Exception` catch-all) discards every already-paid-for
result. 9 of the script's 14 functions — including both cost-dominant
ones, `build_stratified_sample` and `run_story` — have zero test
coverage.

The 2026-07-27 ERW pipeline structured-output reliability audit's
Category E (E1 model-invocation logging/budget enforcement, E2
restartable/checkpointed runs) already surveyed options and grounded a
recommendation in fetched, reputable sources (Apache Airflow's own
best-practices docs, Databricks' medallion architecture docs), but was
never promoted out of the audit document into an actionable design
artifact — it was explicitly deferred from both `WI-EVENT-0032` and
`WI-EVENT-0033`'s scope as "independent and schedulable separately."

An interim, narrower workaround
(`experiments/03_cross_segment_relation_pilot/check_segmentation_reliability.py`,
merged via PR #189) already demonstrates the value directly: it survives
a Ctrl-C or crash mid-run because each story's outcome (including the raw
LLM output) is written to its own file immediately as the run proceeds —
but it is deliberately scoped to a single stage (segmentation only), not
a general pattern for multi-stage pipelines.

Existing precedent: `lcats/src/lcats/gatherers/downloaders.py:223-253`'s
`DataGatherer.download` already does file-existence checkpointing in
production, at real corpus scale, with zero new dependency — *"If a file
doesn't already exist, get its resource and process it with the
handler."* This is already the house pattern for one of LCATS's two major
pipelines, not a novel idea being proposed for the first time.

LCATS's broader context makes this more than a single-script fix: the
project is used by two researchers, is open source with a planned PyPI
release, has multiple other pipeline-like processes beyond this one
pilot (other `experiments/` scripts, notebooks, `lcats/KMo/`, the
`lcats gather` pipeline), and has stated medium-term scale ambitions
(10x-100x corpus growth, a million-book corpus under consideration) plus
an explicit goal of processing stories "possibly in parallel." An
`run_pilot.py`-only fix would leave every other batch script with the
same fragility this proposal exists to eliminate.

## Prior Art Check

### Duplication search
- In-repo: No existing implementation found. No design proposal or skill
  currently covers checkpointing, persistence, or staged pipeline
  execution. `lcats/src/lcats/pipeline.py` is a related but incomplete
  skeleton (`Stage`/`Pipeline`/`RunResult`/`RunContext` dataclasses) — not
  a duplicate to extend as-is: it has no disk persistence at all (state
  lives only in the Python process, the same failure mode this proposal
  exists to fix), no parallelism, and its own `RunContext` and
  `Stage.cache` fields are declared but never read or acted upon anywhere
  (confirmed dead code — the file's own git history shows it was last
  touched only by a formatter-only commit, never a substantive one).
- Sibling repos: None identified.
- External libraries: Considered directly in the audit's Category E —
  Prefect, Dagster, Ray, Luigi, Airflow. None currently appear in
  `lcats/pyproject.toml`. Airflow is disqualified on operational-model
  grounds (needs a persistent scheduler + metadata DB + webserver, built
  for continuously-scheduled jobs; LCATS's usage is researcher-triggered
  ad hoc runs, not a standing service) rather than a scale question, so
  this is unchanged regardless of future growth. Prefect/Dagster/Ray are
  reasonable "graduate to a real tool" candidates once real
  parallel/distributed execution is actually warranted — not adopted now.
- Recommendation: Proceed.

### Demand search
- Work items: `WI-EVENT-0032` and `WI-EVENT-0033` both explicitly list
  "Does not implement Category E (cost/logging/checkpointing/local
  models)" as a Non-Goal — this proposal is what fulfills that
  deliberately deferred scope.
- Proposals: None found.
- Backlog: This repo has no `project/design/backlog.md` file.
- Recommendation: Proceed — no closeout opportunity, since nothing
  currently formally requests this; this proposal creates the artifact
  the deferrals in `WI-EVENT-0032`/`WI-EVENT-0033` were waiting for.

## Design Decisions

### Decision 1: Checkpoint mechanism

Options considered:
- Custom checkpoint file/directory, keyed on a success/failure predicate
  (not mere presence) — cheapest possible option; ~80% already built via
  `FatalPilotError`'s existing partial-write-on-abort pattern (PR #166)
  and `DataGatherer.download`'s existing precedent.
- `joblib.Memory` — trivial dependency, near-zero learning curve, but
  call-level memoization only, not real pause/resume/monitor semantics
  for a multi-stage job.
- Prefect (open-source core, no server required for local use) —
  purpose-built for this: `@flow`/`@task` decorators, built-in retries,
  result caching/resume, runs entirely locally.
- Dagster — its "Software-Defined Assets" model maps closely onto "each
  story-bucket directory holds versioned per-stage artifacts," the
  mental model the deferred `flat_story_layout_migration_impact_report.md`
  already arrived at independently.
- Ray — purpose-built for "checkpointed, parallel processing of many
  independent items," a close conceptual match to "per-story bucket,
  parallelizable."
- Luigi / Dagster / Airflow — considered and deprioritized per the
  duplication search above.

**Chosen: bucket-directory + file-existence checkpoint**, generalizing
`DataGatherer.download`'s pattern. Zero new dependency, proven at real
production scale in this exact codebase already, and matches a design
LCATS already independently arrived at (the deferred
`flat_story_layout_migration_impact_report.md`'s per-story-directory
migration). Prefect/Dagster/Ray remain live candidates to "graduate to"
later, specifically once real parallelism/distributed-scale needs are
demonstrated empirically rather than chosen speculatively ahead of need.

**Requirement: atomic checkpoint publication (review finding, PR #190).**
`DataGatherer.download`'s own precedent writes directly to its
destination path, which is not itself sufficient here: if the process is
interrupted after a checkpoint file is created or truncated but before
its contents are fully written, a naive file-existence check would treat
that torn file as a completed checkpoint on the next run — reproducing
exactly the interruption failure this proposal exists to eliminate. The
shared helper (Decision 4) must write to a temporary path in the same
directory and atomically rename it into place only after the write
completes (`os.replace`/`Path.replace`, which is atomic on the same
filesystem), and must treat any checkpoint file that fails to parse as
cleanly as the write's own error case (I/O error, JSON error) as
"incomplete," never as done and never as a hard failure that blocks
the whole run.

### Decision 2: Checkpoint predicate (what counts as "done")

Options considered:
- Bare presence of an output file for a given story/stage.
- A success/failure predicate that distinguishes a genuinely completed
  stage from a recorded, recoverable failure.
- A success/failure predicate plus a run-configuration identity check,
  so a checkpoint is only honored if it was produced under a
  configuration compatible with the current run.

**Chosen: success/failure predicate plus configuration identity.**
Confirmed via review on PR #169: mere presence would treat `excluded:
true` rows (transient parsing/extraction failures) as "done," silently
preserving or skipping recoverable failures on a resumed run — the
success/failure distinction alone fixes that. But review on this
proposal (PR #190, P1) correctly identified that success/failure alone
is still insufficient for the exact scenario Decision 2 already named:
"a resumed run after a model switch or bug fix." A checkpoint recorded
as successful under the *old* model, prompt template, tool schema, or
extractor code version is not actually valid evidence for a run under a
*new* one — treating it as done would silently combine stale successful
checkpoints with newly recomputed results, corrupting comparability
exactly the way a bare presence check corrupts it for transient
failures, just for a different reason. The shared helper (Decision 4)
must therefore write, alongside each checkpoint's outcome, an identity
fingerprint of the configuration that produced it — at minimum the model
name and a version/hash of the relevant prompt template or tool schema;
callers with additional relevant upstream dependencies (e.g. a specific
extractor module version) should include those too — and a checkpoint is
only honored on resume if that fingerprint matches the current run's
configuration; a mismatch is treated as if the checkpoint did not exist,
forcing recomputation. The exact fingerprint contents are caller-specific
(left to work-item design, not this proposal - see Open Questions), but
the helper's checkpoint API must make omitting one a deliberate choice, not
a silent gap. `check_segmentation_reliability.py` (PR #189) currently
treats any existing per-story output file as complete regardless of
recorded outcome or configuration, which is a deliberate, narrower
simplification correct only because that script does not retry and is
typically run once per model under study; a general pattern intended for
reuse must make both choices (success/failure, configuration identity)
explicit and documented per use case, not bake in one script's
simplification as the default.

### Decision 3: Staging granularity — per-item vs. per-stage

Options considered:
- Checkpoint only at the outermost per-story boundary (one artifact per
  story, covering the whole pipeline for that story).
- Break the pipeline into discrete stages (e.g. genre-detect, segment,
  ERW-extract, cross-segment-relate), each persisting its own
  intermediate artifact before the next stage runs.

**Chosen: per-stage staging** for scripts with expensive, distinct
stages like `run_pilot.py`'s genre-detection scan (up to 200 calls) vs.
its per-story ERW pipeline (1 segmentation + 4-per-segment + 1
story-level call). This directly serves the "inspect intermediate
output, tweak it, re-run just the affected stage" workflow motivating
this whole proposal, and would have directly resolved this session's own
debugging dead end during the earlier structured-output reliability
investigation: the malformed-tool-result crash could only be diagnosed
by reconstructing the raw payload from `ANTHROPIC_LOG=debug` output
after the fact, because nothing from the failing call had been persisted
anywhere. Grounded in Apache Airflow's own best-practices docs: *"You
should treat tasks in Airflow equivalent to transactions in a database.
This implies that you should never produce incomplete results from your
tasks,"* and, on passing data between stages, *"a good way of passing
larger data between tasks is to use a remote storage such as
S3/HDFS"* rather than in-memory objects; and Databricks' medallion
architecture, on the specific cost benefit of persisting intermediate
output: *"the ability to provide ... reprocessing if needed without
rereading the data from the source system."* Per-item-only staging
remains acceptable for smaller, single-stage scripts (correctly the
choice already made for `check_segmentation_reliability.py`).

### Decision 4: Scope — one script vs. a shared pattern/helper

Options considered:
- Fix `run_pilot.py` alone.
- Extract a small, shared checkpointing helper usable by `run_pilot.py`,
  `check_segmentation_reliability.py`, and future batch scripts alike.

**Chosen: shared pattern**, given LCATS's own stated context (2
researchers, open source, multiple pipeline-like processes, planned
scale growth) described in Background/Motivation above — a
`run_pilot.py`-only fix would leave every other batch script with the
same fragility, and the underlying pattern (does this story/stage's
output file already exist? if not, compute it and write it) is already
proven generic by `DataGatherer.download`'s existing use in a completely
different pipeline.

## Non-Goals

- Does not adopt Ray, Dagster, Prefect, or any other orchestration
  framework now — this proposal recommends starting with the
  zero-dependency bucket-directory pattern and revisiting a real
  orchestration tool only once real parallel/distributed execution is
  actually warranted by demonstrated scale needs, per the audit's own
  sequencing recommendation ("let that experience determine empirically
  whether Ray or Dagster ... is actually needed").
- Does not implement Category E1 (model-invocation logging and
  dollar-cost budget enforcement) — this proposal is scoped to
  persistence/checkpointing (E2) only. E1 (a pricing table, a
  backend-layer logging hook) is a separate, smaller, and largely
  orthogonal piece of work that could be proposed and implemented
  independently of this one.
- Does not migrate the corpus to the deferred per-story-directory layout
  (`flat_story_layout_migration_impact_report.md`'s 16-site impact
  audit) — that migration is a natural complement to this proposal's
  design but is its own large, separately-scoped body of work. This
  proposal's checkpoint pattern is designed to work against today's flat
  `data/<collection>/<story>.json` layout via a script-local
  output/checkpoint directory, and would extend cleanly to a future
  per-story-directory layout if/when that migration happens.
- Does not retrofit every existing LCATS batch script (`lcats/KMo/`'s
  `analyze.py`/`scenes.py`, other `experiments/` scripts) in this
  proposal's own implementation — the initial implementation targets
  `run_pilot.py`, the most acute and directly measured need; the shared
  helper is designed for reuse, but adopting it elsewhere is future,
  separately-scoped work.
- Does not change `check_segmentation_reliability.py`'s existing,
  already-working, narrower persistence approach — that script remains
  an interim, single-stage tool per its own module docstring, to be
  reconsidered (if at all) only once this proposal's shared pattern
  exists and is proven.
- Does not decide retry/backoff policy for rate-limited or
  truncated-output API errors — `llm_extractor.py`'s
  `_classify_api_error` already classifies these categories; a
  caller-level retry policy is a related but distinct decision,
  explicitly deferred here (matching the existing deferral in the
  max_tokens truncation-detection work, PR #170, which raises and
  classifies but does not itself retry).

## Implementation Plan

Given the scope (a shared, reusable pattern plus a `run_pilot.py`
migration plus re-vetting `run_pilot.py` against the same 8 operational
criteria that froze it before any further real run is attempted), this
is workstream-sized, not a single work item. Recommended breakdown, once
this proposal is adopted:

1. Design and implement a shared checkpoint helper (e.g.
   `lcats.utils.checkpoint` or similar location, to be settled during
   work-item scoping), with unit tests, following Decision 2's
   success/failure-predicate requirement.
2. Migrate `run_pilot.py` to staged, checkpointed execution using the
   helper (Decision 3's per-stage granularity), then re-vet the
   migrated script against this session's own 8 operational criteria
   before it is considered safe to attempt another real, paid run.
3. (Stretch / separately scoped, only if picked up as part of the same
   effort) Category E1: model-invocation logging and budget
   enforcement.

## Cross-References

- Audit: `lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`
  (Category E, E1/E2, and the grounding sources this proposal reuses)
- Precedent: `lcats/src/lcats/gatherers/downloaders.py:223-253`
  (`DataGatherer.download`)
- Related, deferred design:
  `lcats/project/design/flat_story_layout_migration_impact_report.md`
- Related, dead-code skeleton: `lcats/src/lcats/pipeline.py`
- Interim narrower tool:
  `experiments/03_cross_segment_relation_pilot/check_segmentation_reliability.py`
  (PR #189)
- Workstream: `project/workstreams/proposed/WS-EVENT-STRUCTURED-OUTPUT-RELIABILITY.md`
  (Category E explicitly deferred from its own scope)

## Open Questions

- Exact shared-helper API shape (function/class signature, directory
  and filename naming convention, how a caller declares its own stages,
  the exact configuration-fingerprint contents per Decision 2) — left to
  the follow-on workstream/work-item design, not decided by this
  proposal.
- Whether Category E1 (logging/budget enforcement) should be folded into
  the same workstream as this proposal's E2 work, or proposed/scoped
  entirely separately — the Non-Goals above defer this decision, not
  this proposal itself.
