---
resolution: null
blocked_reason: null
blocked: false
id: WI-RUNLOG-0084
title: Record no-log-needed disposition for run-log audit's out-of-scope sites
type: operation
status: proposed
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams:
  - WS-RUN-LOG
related_design:
  - lcats/project/design/proposals/proposed/lcats-run-log/00_proposal.md
depends_on: []
blocked_by: []
expected_actions:
  - edit_file
forbidden_actions:
  - force_push
  - delete_branch
  - add_run_log_to_these_sites
acceptance:
  - Each of the 5 sites carries an in-code comment (docstring or module-level note) stating it was assessed and found not to need a run log, citing PROP-LCATS-RUN-LOG's Decision 4 table and the one-line reason
  - No behavioral change to any of the 5 scripts/commands
  - lrh validate passes with 0 errors
required_evidence:
  - lrh_validate
artifacts_expected:
  - experiments/03_cross_segment_relation_pilot/run_stability_gate.py
  - experiments/02_llm_backend_comparison/run_comparison.py
  - lcats/src/lcats/analysis/corpus/clean_cli.py
  - lcats/src/lcats/analysis/corpus/repairs_cli.py
  - lcats/src/lcats/analysis/corpus/linguistics_cli.py
---

## Summary

Records the "historical/no-log-needed" disposition from
`PROP-LCATS-RUN-LOG`'s Decision 4 table directly in each of the 5
out-of-scope sites' own code, so a future reader doesn't have to
re-derive why they were skipped.

## Problem / Context

Proposal Implementation Plan step 7. The 5 sites (`run_stability_gate.py`,
`run_comparison.py`, `lcats clean`, `lcats repair-specials`,
`lcats linguistics`) were each assessed and found not warranted — but
that assessment currently lives only in the proposal document, not in
the code itself, and could be silently "rediscovered" as a gap by a
future contributor unaware of the deliberate decision.

### Duplication search
- In-repo: No existing disposition note at any of the 5 sites.
  Recommendation: Proceed.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found.
- Proposals: Found: `PROP-LCATS-RUN-LOG` — Implementation Plan step 7
  requests this directly.
- Backlog: No matching entries.
- Recommendation: No action.

## Scope

- Add a one-line disposition note to each of the 5 sites
- Do not add any run-log functionality to any of them — that would
  contradict the assessed disposition

## Required Changes

1. `run_stability_gate.py` — note: bounded 2-fixture scope; its pilot
   stage (`_run_pilot()`) is delegated to a `run_pilot.py` subprocess
   (covered transitively by WI-RUNLOG-0080), but its genre-detection
   stage (`_run_genre_detection()`) makes its own paid, in-process
   `assess_story()` calls, not subprocess-delegated (correction, PR
   #352 self-review) — still small/bounded enough (2 fixture stories)
   not to warrant its own run log.
2. `run_comparison.py` — note: small ad-hoc tool, existing flush-per-row
   JSONL already gives near-equivalent durability.
3. `clean_cli.py` — note: deterministic deletion, idempotent to rerun.
4. `repairs_cli.py` — note: explicitly non-destructive dry-run,
   deterministic.
5. `linguistics_cli.py` — note: per-story sidecar writes with
   fingerprint-based skip already act as an implicit checkpoint.

## Non-Goals

- Does not add run-log support to any of the 5 sites.
- Does not reopen the disposition assessment itself — that's the
  proposal's own job if usage patterns change later.

## Acceptance Criteria

(see frontmatter)

## Validation

- `scripts/version tools`
- `lrh validate`

## Dependencies / Order

Independent of WI-RUNLOG-0078 — can land anytime, no code dependency.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-RUN-LOG.md`
- Design: `project/design/proposals/proposed/lcats-run-log/00_proposal.md`
