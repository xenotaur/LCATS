---
id: PROP-LCATS-STORY-BUCKET-LAYOUT
type: design_proposal_set
status: proposed
implementation_status: not_started
---

# Per-Story Bucket Directory Layout for LCATS Corpus Storage

This proposal set records the design for migrating LCATS story storage from
flat per-collection files (`data/<collection>/<story>.json`) to per-story
bucket directories (`data/<collection>/<story>/story.json`), resolving the
open questions left by `flat_story_layout_migration_impact_report.md` and
two additional gaps (gather-overrides identity collision, promotion
layout-validation) found during design review.

## Documents

- [`00_proposal.md`](00_proposal.md) — background, prior-art check, design
  decisions (migration strategy, canonical identity, discovery predicate,
  dual-layout window, output schema, promotion validation, overrides
  identity), non-goals, and implementation plan.
