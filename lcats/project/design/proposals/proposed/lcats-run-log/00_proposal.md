---
id: PROP-LCATS-RUN-LOG
type: design_proposal
title: Shared Run-Event Logging for LCATS Batch Scripts
status: proposed
created_on: 2026-08-21
updated_on: 2026-08-21
implementation_status: not_started
implemented_by: []
supersedes: []
superseded_by: null
related_design:
  - lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md
  - lcats/src/lcats/utils/checkpoint.py
  - experiments/05_metadata_genre_prefilter/run_prefilter.py
  - lcats/project/work_items/resolved/WI-EVENT-0032.md
---

## Summary

Formalizes PR #334's per-run JSONL event log (`_log_run_event()`) as a
shared `lcats.utils.run_log` module — a free function plus a `RunLog`
context manager that guarantees a terminal event on *any* uncaught
exception, not just each script's specific anticipated fatal-error type —
and triages every existing and candidate LCATS batch script against it,
upgrading warranted-but-missing sites and explicitly recording a
"no log needed" disposition for the rest.

## Background / Motivation

`lcats.utils.checkpoint` (adopted via `PROP-LCATS-PIPELINE-CHECKPOINTING`)
answers "is this item done and resumable?" but deliberately does not
answer "what happened, in what order, and why did the run stop?" PR #334's
own summary documents auditing `run_prefilter.py`, `run_census.py`, and
`run_pilot.py` for checkpointing/resumability and finding `run_pilot.py`
had "the complete pattern" already, including a code comment citing a real
past incident (`WI-EVENT-0032`, resolved) where an unhandled per-story
exception discarded every already-completed story's results. That PR then
modeled `run_prefilter.py`'s `--validate --run-real-validation` fix on
`run_pilot.py`'s pattern, and — after a follow-up review round (commit
"Add a per-run JSONL event log to --validate's real run (Option C)") —
added `_log_run_event()`
(`experiments/05_metadata_genre_prefilter/run_prefilter.py:883-905`):
append-open-write-close per event, one JSON line per `run_start`/per-item/
`run_end`/`run_aborted_fatal`, so a hard crash never loses a buffered
line.

That log was scoped to `run_prefilter.py` alone. A follow-up audit this
session (2026-08-21) surveyed every `experiments/*/run_*.py` script and
every long-running/costly/externally-dependent `lcats` CLI command against
the same bar and found the identical gap recurring at five more sites —
including `run_pilot.py` itself, the script whose own docstring names the
precedent this pattern exists to prevent, which still has no incremental
run log today (its `pilot_stories.jsonl`/`pilot_usage.jsonl` are written
once at the very end,
`experiments/03_cross_segment_relation_pilot/run_pilot.py:1824-1832`) —
plus a differently-shaped but real case at `lcats promote` (a destructive
local `rmtree`-then-`copytree`, not a paid API loop). Left unaddressed,
each site would independently reinvent (or fail to reinvent)
`_log_run_event()`'s crash-safety property, the same fragmentation
`PROP-LCATS-PIPELINE-CHECKPOINTING` already named as the reason to make
checkpointing a shared pattern rather than a `run_pilot.py`-only fix.

## Prior Art Check

### Duplication search
- In-repo: No existing implementation found. From the `lcats/` project
  root:

  ```bash
  grep -rli "run.log\|run_event\|log_run_event\|runlog" src/ \
    project/design/proposals/ project/workstreams/ project/work_items/
  ```

  returns nothing outside `run_prefilter.py` itself. No proposal,
  workstream, or work item currently covers this.
- Sibling repos: None identified.
- External libraries: Considered directly in this session's design
  discussion — stdlib `logging` (rejected: default `FileHandler`
  buffering would need to be bypassed to get the crash-safety property
  this exists for, global mutable logger state has known test-interaction
  sharp edges, and it would be the first use of `logging` in a codebase
  that has standardized on `print()`) and third-party structured-logging
  libraries (`structlog`, `loguru`; rejected: no existing usage, would add
  a new runtime dependency to `lcats/pyproject.toml`'s deliberately
  minimal dependency list for functionality already implemented and
  working in ~23 stdlib-only lines).
- Recommendation: Proceed.

### Demand search
- Work items:

  ```bash
  grep -rli "run.log\|run.event" project/work_items/proposed/
  ```

  — none found. `WI-EVENT-0032` (resolved) names the underlying failure
  mode but is already closed against `run_pilot.py`'s exception-handling
  fix, not this proposal's scope.
- Proposals:

  ```bash
  grep -rli "run.log\|run.event" project/design/proposals/proposed/
  ```

  — none found.
- Backlog: `project/design/backlog.md` contains no matching entries.
- Recommendation: No action — no existing request to close/link.

## Design Decisions

### Decision 1: Implementation approach

Options considered:
- **Plain function**, extracting `_log_run_event()` verbatim into a shared
  module — zero new abstraction, matches this codebase's existing
  functional `utils/` style, but every caller still hand-rolls `run_id`
  generation and manually threads `run_start`/`run_end` calls through
  every `except` branch it happens to anticipate.
- **Context manager (`RunLog`)** wrapping a run, auto-emitting `run_start`
  on `__enter__` and, on `__exit__`, either `run_end` (clean exit) or an
  `run_aborted_*` event (an exception propagated).
- **Stdlib `logging`** with a JSON `Formatter` + `FileHandler`.
- **Third-party structured logging** (`structlog`/`loguru`).

**Chosen: plain function *and* context manager, both in the same
module** — the context manager is not a replacement for the function but
a wrapper around it, so ad-hoc call sites can still call the function
directly while full-run call sites get the `__exit__` guarantee. The
context manager closes a real, still-open gap: today, every audited site
logs a terminal event only for the specific exception type it explicitly
catches (`FatalValidationError`, `FatalCensusError`, etc.) — a genuinely
unanticipated exception during any other part of the run (e.g. in
output-writing code after the main loop) still produces no terminal log
line anywhere, including in `run_prefilter.py`'s own reference
implementation. `logging` and third-party libraries are excluded per the
Prior Art Check above: neither offers a decisive advantage for the one
property this needs (crash-safe, ordered, human-greppable JSONL), and
both carry real costs (buffering to work around, or a new dependency)
this codebase doesn't currently pay.

**Event-name vocabulary (review finding, this PR: `run_aborted` as
written was ambiguous against the reference implementation's actual
`run_aborted_fatal`).** `RunLog` reuses the reference implementation's
existing `run_start`/per-item/`run_end`/`run_aborted_fatal` vocabulary
(Background above) for the case it already covers — a caught
account-level fatal error — and adds a sibling `run_aborted_unexpected`
for `__exit__`'s new case, a truly unanticipated exception the caller
never anticipated catching. Both are members of one `run_aborted_*`
family (a shared prefix, not one bare `run_aborted` event), so a reader
grepping for `run_aborted` still finds every abort path, while the
suffix still distinguishes an expected fatal condition from a genuine
crash. Exact event field shape is otherwise left to work-item design —
see Open Questions.

**Durability scope (review finding, this PR: "crash-safe" needs
narrowing or an explicit `fsync` strategy).** Open-write-close per event
guarantees a line already written is never lost to *process*
termination — a `kill -9`, an OOM kill, or an uncaught exception —
because `close()` flushes Python's own buffer into the OS. It does
**not** guarantee durability across an unclean *machine* shutdown or
power loss: `close()` does not `fsync()`, so the OS may still hold the
just-written bytes in its page cache rather than on disk when power is
lost. This proposal scopes the guarantee to process-level crash safety
only, matching what the reference implementation's actual read/write
behavior provides (its own docstring's "power loss" language overstates
this and is not carried forward here) — whether `RunLog` should
additionally `fsync()` after each write (trading a small per-event
latency cost for true power-loss durability) is left to work-item
design, not decided by this proposal; see Open Questions.

### Decision 2: Module location

**Chosen: `lcats.utils.run_log`**, sibling to `lcats.utils.checkpoint` —
same directory, same "small, stdlib-only, one concern" convention already
established by `checkpoint.py`, `env.py`, `paths.py`, `secrets.py`.

### Decision 3: Relationship to checkpoint roots

`_log_run_event()`'s current signature takes a bare
`log_path: pathlib.Path` with no relationship to
`checkpoint.resolve_roots`'s protected-root guard
(`lcats/src/lcats/utils/checkpoint.py:21-29` — `working_root` is guarded
against `data/`/`corpora/`, but nothing stops a run log from being
pointed there). **Chosen: `RunLog` accepts a `checkpoint.CheckpointRoots`
(or its `working_root`) and derives the log path under it**, so a run log
gets the same protection checkpoints already have by construction, rather
than by each caller separately remembering to apply it. The plain
function keeps accepting a bare path, for callers with no
`CheckpointRoots` of their own.

**Requirement: `RunLog` must re-validate the root it is given, not just
derive a path under it (review finding, this PR).** `CheckpointRoots` is
publicly constructible and `working_root` is just a `Path` — the guard
above only actually runs inside `checkpoint.resolve_roots()`, so a caller
that constructs `CheckpointRoots` directly (bypassing `resolve_roots()`)
and passes a `working_root` of `data/` or `corpora/` would have that
root accepted by `RunLog` with no protection at all, silently writing
logs into a protected root and, via `lcats promote`'s unfiltered
`_copy_collection`, potentially carrying them into a promoted corpus.
`RunLog`'s own constructor must therefore apply
`checkpoint.resolve_roots`-equivalent validation to whatever root it is
given (or reject any `working_root` it cannot confirm was itself already
validated), not trust that a `CheckpointRoots` instance implies its
caller already went through `resolve_roots()`. Exact mechanism (e.g.
`RunLog` calls the same protected-root check `resolve_roots()` uses,
directly on the roots it receives) is left to work-item design, not
decided here — see Open Questions.

### Decision 4: Migration disposition per site

Every candidate site identified in this session's audit gets an explicit
disposition — either **upgrade** (warranted and currently missing) or
**historical/no-log-needed** (recorded and closed, not silently left
ambiguous):

| Site | Disposition |
|---|---|
| `experiments/05_metadata_genre_prefilter/run_prefilter.py` | **Upgrade** — migrate its inline `_log_run_event()` onto the shared module (dogfoods the new API against its own reference implementation). |
| `experiments/03_cross_segment_relation_pilot/run_pilot.py` | **Upgrade** — highest priority; this is the WI-EVENT-0032 precedent script and still has no incremental log today. |
| `experiments/04_genre_census/run_census.py` | **Upgrade** — same paid-loop shape as the reference implementation, largest corpus scope (~1,868 stories in `--full` mode). |
| `lcats gather` (`lcats/src/lcats/gatherers/`) | **Upgrade** — bulk network downloads, no `checkpoint` usage at all today, errors currently tracked only in memory. |
| `lcats assess` (`assess_cli.py`) | **Upgrade** — paid per-file loop, some output formats (`--format json`) buffer and are lossy on crash even for already-paid work. |
| `lcats annotate` (`annotate.py`) | **Upgrade** — already has real per-item checkpointing; only missing the ordered human-readable trail on top of it (smallest-diff upgrade of the set). |
| `lcats promote` (`promote.py`) | **Upgrade** — different risk shape (`rmtree`-then-`copytree` per collection, `lcats/src/lcats/analysis/corpus/promote.py:267-271`), no LLM cost but genuinely destructive local I/O with no record of in-flight state. |
| `experiments/03_cross_segment_relation_pilot/run_stability_gate.py` | **Historical / no-log-needed** — bounded 2-fixture-story scope, real work delegated to a `run_pilot.py` subprocess (covered transitively once that script is upgraded). |
| `experiments/02_llm_backend_comparison/run_comparison.py` | **Historical / no-log-needed** — small ad-hoc tool (default 5-story sample); existing flush-per-row JSONL already gives near-equivalent durability at this scale. |
| `lcats clean` | **Historical / no-log-needed** — deterministic deletion, idempotent to rerun, no external dependency. |
| `lcats repair-specials` | **Historical / no-log-needed** — explicitly non-destructive dry-run, deterministic, no LLM/network calls. |
| `lcats linguistics` | **Historical / no-log-needed** — no LLM/network cost; per-story sidecar writes with fingerprint-based skip already act as an implicit checkpoint, so a crash loses no completed work. |

## Non-Goals

- Does not implement dollar-cost budget enforcement
  (`PROP-LCATS-PIPELINE-CHECKPOINTING`'s deferred "Category E1" other
  half) — this proposal covers ordered event/narrative logging only.
- Does not change `checkpoint.py`'s resumability semantics — the run log
  is additive and observational; it is never consulted to decide whether
  an item is done.
- Does not itself perform the per-site migrations — this proposal decides
  which sites are in scope and which are explicitly out; the migrations
  are separately scoped implementation work.
- Does not adopt stdlib `logging` or a third-party structured-logging
  library — Decision 1 closes that option for this codebase, it is not
  deferred pending more information.
- Does not reopen the "historical/no-log-needed" sites' scope — a future
  change in one of those scripts' actual usage pattern (e.g.
  `run_comparison.py` scaling to large samples) would need its own
  re-assessment, not an assumption this proposal already covers it.

## Implementation Plan

Comparable in shape to `PROP-LCATS-PIPELINE-CHECKPOINTING` (module +
tests, then per-script migration) — workstream-sized, not a single work
item:

1. Implement `lcats.utils.run_log` (function + `RunLog` context manager
   per Decisions 1-3), with unit tests.
2. Migrate `run_prefilter.py` onto the shared module.
3. Add to `run_pilot.py` (highest priority).
4. Add to `run_census.py`.
5. Add to `lcats gather`, `lcats assess`, `lcats annotate`.
6. Add to `lcats promote`.
7. Record the "historical/no-log-needed" disposition (Decision 4 table)
   in each of those scripts' own docstrings/comments, so a future reader
   doesn't have to re-derive why they were skipped.

## Cross-References

- Reference implementation: `_log_run_event()`,
  `experiments/05_metadata_genre_prefilter/run_prefilter.py:883-905`
  (PR #334)
- Checkpoint module: `lcats/src/lcats/utils/checkpoint.py`
- Related proposal:
  `lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md`
- Resolved precedent: `lcats/project/work_items/resolved/WI-EVENT-0032.md`

## Open Questions

- Exact `RunLog` context-manager API (constructor signature, event-name
  vocabulary reuse vs. per-caller extension, e.g. `lcats promote`'s
  `collection_blocked`) — left to work-item design.
- Exact mechanism for `RunLog`'s own protected-root re-validation
  (Decision 3) — left to work-item design.
- Whether `RunLog` should `fsync()` after each write for true
  power-loss durability, or stay scoped to process-crash safety only
  (Decision 1) — left to work-item design.
- Whether `run_stability_gate.py`, `run_comparison.py`, or
  `lcats linguistics` should be revisited later if their usage pattern
  changes — flagged, not decided here.
