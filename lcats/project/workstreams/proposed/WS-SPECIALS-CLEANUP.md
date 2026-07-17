---
id: WS-SPECIALS-CLEANUP
kind: planning_node
title: Special-character cleanup via pipeline-replayable repairs
status: proposed
stage: assessed
origin: ad_hoc
summary: Coordinate the release-oriented special-character cleanup — measured repair rules, a gather-time normalization hook, per-story overrides, residual human review, and survey-gated promotion — so regenerated data/ and promoted corpora/ are free of encoding damage.
related_focus:
  - FOCUS-WORLDCON-2026
related_design:
  - project/design/design.md
  - project/audits/2026-06-16-special-character-cleanup-workstream-audit.md
  - project/audits/2026-06-18-phase-4-repair-review-application-integration-audit.md
work_items:
  - WI-SPANOPS-0002
  - WI-REVIEW-0003
  - WI-APPLY-0005
  - WI-RULES-0016
  - WI-NORMALIZE-0017
  - WI-OVERRIDES-0018
  - WI-RESIDUAL-0019
  - WI-PROMOTE-0020
  - WI-RELEASE-0021
exit_criteria:
  - lcats survey --mode specials over freshly regenerated data/ reports zero unaddressed mojibake findings — every measured residual occurrence is repaired by rule, covered by a per-story override, or explicitly allowlisted
  - Repair rules and per-story overrides are versioned repo inputs applied during gathering, so clearing the cache and regenerating data/ reproduces the same repaired output deterministically
  - DEFAULT_REPAIR_RULES in lcats/lcats/analysis/corpus/repairs.py targets the encoding families measured in the live corpus, with tests against real sampled story contexts (the unmatched cp1252-form rules are replaced)
  - Promotion from data/ to corpora/ is gated by a passing specials survey, and the stale corpora/ snapshot is superseded by promotion at the next release rather than repaired in place
  - project/memory/decision_log.md and design.md's State and Persistence Boundary section record the pivot from offset-keyed span-op persistence to rule/override-keyed replayable repairs
---

# Workstream: Special-character cleanup via pipeline-replayable repairs

## Purpose

Coordinate the work that takes LCATS from "known encoding damage in the
corpus" to "regenerated data/ passes the specials survey and can be promoted
to corpora/ at release." This workstream connects the already-built detection,
classification, repair-proposal, span-operation, and review machinery
(`lcats/lcats/analysis/corpus/`) to the gather pipeline, so repairs are replayable
inputs to regeneration rather than one-off edits to stored files.

## Background / Rationale

A 2026-07-09 assessment measured the actual damage and overturned two
assumptions:

- The systemic mojibake in the repo `corpora/` snapshot (148 stories, ~19,800
  occurrences, dominated by latin-1-decoded UTF-8) is **stale history from old
  gather runs**. The freshly regenerated `data/` tree contains **35 stories
  with exactly one occurrence each**, all in `mass_quantities`, all byte-for-
  byte present in the upstream Project Gutenberg sources (three families:
  `Ã©`-form, Mac-Roman `√©`-form, `Â°`-form).
- The six `DEFAULT_REPAIR_RULES` target a cp1252-decoded form that occurs
  **zero times** in either corpora/ or data/ — the repair engine is currently
  a silent no-op on real data.

Because `data/` is cleared and regenerated after major changes (and users
regenerate with their own customizations), durable fixes must live in the
pipeline as versioned rule tables and per-story overrides, not in stored
JSON. This supersedes the 2026-06-18 decision to keep application workflows
out of scope, and amends the persistence boundary in project/design/design.md.
The 2026-06-16 special-character cleanup audit remains the governing survey of
reusable machinery; this workstream executes its "reuse, don't reinvent"
strategy with the corrected facts.

## Scope

- Add a post-extraction normalization step to the gather pipeline that applies
  repair rules and per-story overrides deterministically, recording applied
  rule ids in story metadata for provenance.
- Replace the dead repair-rule table with rules for the three measured
  encoding families, tested against real corpus samples.
- Add a versioned per-story overrides file for residual judgment calls that
  rules cannot safely cover.
- Human review of the ~35 measured residuals (rule-level approval, not
  per-occurrence).
- Gate promotion from data/ to corpora/ on a passing specials survey.
- Record the persistence-model pivot in the decision log and design.md.

## Work Items

Existing active items to re-scope under this workstream:

- **WI-SPANOPS-0002** — span-operation library work is complete; remaining
  scope is its role as the ephemeral execution layer under replayable rules.
- **WI-REVIEW-0003** — review decision models are complete; remaining scope is
  persisting decisions as rule/override-keyed versioned files.
- **WI-APPLY-0005** — the application library landed 2026-06-18 (decision log)
  but the item is still active; remaining scope is pipeline integration, or
  resolve it and open a successor.

New items created 2026-07-10:

- **WI-RULES-0016** — replace the dead repair-rule table with the three
  measured encoding families, tested against real corpus bytes.
- **WI-NORMALIZE-0017** — apply repair rules at gather time with provenance
  metadata (depends on WI-RULES-0016).
- **WI-OVERRIDES-0018** — versioned per-story overrides consumed by the
  normalization hook (depends on WI-NORMALIZE-0017).
- **WI-RESIDUAL-0019** — human review of residual defects and clean
  regeneration of data/ (depends on WI-RULES-0016..WI-OVERRIDES-0018).
- **WI-PROMOTE-0020** — survey-gated promotion from data/ to corpora/
  (depends on WI-RESIDUAL-0019).

## Exit Criteria

(See frontmatter `exit_criteria` — authoritative list.)

## Non-Goals

- Does not perform the bucket/story-directory layout migration
  (project/design/flat_story_layout_migration_impact_report.md) — deferred
  post-release; the overrides and decision files are forward-compatible with
  that layout.
- Does not repair the stale corpora/ snapshot in place — it is superseded by
  promotion.
- Does not use LLM-based repair; `lcats assess` remains a triage layer for
  non-mojibake issue classes (transcriber notes, missing quotations), which
  are tracked separately from this workstream's encoding scope.
- Does not implement an interactive review UI.

## Open Questions

- Where should the 2026-07-09 measurement evidence live —
  project/audits/ or project/evidence/? (A dated note should be written and
  linked from `related_design` or `evidence`.)
- Collection naming differs between data/ (ohenry-four_million,
  wilde_happy_prince) and corpora/ (ohenry, wilde) — the promotion mapping
  should be confirmed before the survey gate is defined.
