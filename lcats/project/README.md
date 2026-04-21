# LCATS Project Control Plane

This `project/` directory is the LRH planning and memory layer for LCATS.

## Current Truth (2026-04-21)
- Goal: narrative reasoning on top of a trustworthy corpus substrate.
- Current execution: repair + review pipeline.
- Completed foundations: ingestion, survey/classification, and immediate correctness fixes.

## Directory Guide
- `goal/`: long- and near-term intent.
- `roadmap/`: phase-structured progress with completion state.
- `focus/`: narrow active priority.
- `design/`: active architecture for execution phases.
- `work_items/`: actionable items (active/planned only).
- `memory/`: durable decision log for retired/completed work.

- Migration planning: `design/flat_story_layout_migration_impact_report.md` documents code/test/doc dependencies on the current flat story JSON layout.

## Operating Rule
If work is complete, move it out of active `work_items/` and record it in `memory/decision_log.md`.
