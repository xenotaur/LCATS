# Design Directory

This directory captures architectural decisions for the active LCATS roadmap phases.

## Current Design Center
- Classification -> repair -> span operations -> review pipeline.
- Conservative, non-destructive corpus changes.
- Explainable and auditable decision paths.

## Files
- `design.md`: canonical design for the active repair/review horizon.
- `unified-llm-backend-design.md`: design for the unified `LLMBackend` Protocol
  and provider implementations (Phase 5.5, DESIGN-LLM-BACKEND).
- `flat_story_layout_migration_impact_report.md`: audit of flat `data/<collection>/<story>.json` assumptions and migration impact.
