---
execution_id: 2026_08_23_05_21_06_LCATS_PROMOTE_MODE_REDESIGN
prompt_id: PROMPT(AD_HOC:LCATS_PROMOTE_MODE_REDESIGN)[2026-08-23T05:15:52+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/369
commit: 55ee68c7432e2900fc8c558b966120e5f500d22a
agent: claude_app
instruction_source: project/design/proposals/proposed/lcats-promote-mode-redesign/00_proposal.md
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
created_at: 2026-08-23T05:21:06+00:00
---

# Summary

Created `PROP-LCATS-PROMOTE-MODE-REDESIGN` and its companion workstream
`WS-PROMOTE-MODE-REDESIGN`, bundled in one PR per explicit user request
for joint review. The design removes `lcats promote`'s silently
destructive default in favor of mandatory `insert`/`upsert`/`replace`
modes, a shared sidecar-validator registry, and a targeted guard
preventing `replace` from destroying tranche-promoted sidecars.

# Result

- Design emerged from an extended, iterative design discussion (not a
  single interview pass): each major decision (mode names, the
  `--allow-unvalidated`/`--allow-orphaned-sidecar-deletion` flag names,
  the `--sidecar` flag, the validator-registry location, whether `insert`
  needs the same validation requirement as `upsert`, whether `replace`
  needs additional hardening) was independently stress-tested against
  real repo state (file:line citations throughout) and, where relevant,
  external precedent (SQL/POSIX for `insert`, vector-DB convention for
  `upsert`, clig.dev and fail-safe-defaults literature for the
  mandatory-mode requirement).
- Ran the required prior-art check (duplication + demand search) per
  `references/prior-art-check.md`: no duplicate implementation or
  open request found; `PROP-GENRE-EVIDENCE-SIDECARS` Decision 7 identified
  as the governing prior design this proposal extends, not a duplicate.
  Recorded in both artifacts' own `## Prior Art Check` sections.
- Proposal (`00_proposal.md`) captures 8 design decisions, each with
  options considered and grounded rationale for the chosen option.
  Workstream (`WS-PROMOTE-MODE-REDESIGN.md`) captures scope, its own
  prior-art check, and a 3-stage anticipated work-item breakdown in
  dependency order, with the third stage (live-directory-scan sourcing
  for `insert`/`upsert`) flagged as a priority given an imminent
  whole-corpus `linguistics.json` rollout that directly needs it.
- No code changes — planning artifacts only.

# Validation

- `lrh validate`: targeted check for both new files individually reports
  0 errors; overall repo error count unchanged from the pre-existing
  baseline (concurrent-session drift, not attributable to this PR).
- Confirmed both files land in their correct status buckets
  (`proposed/`) matching their `status:` frontmatter.

# Follow-up

- This PR is a planning-artifact PR — no implementation. Once
  `PROP-LCATS-PROMOTE-MODE-REDESIGN`/`WS-PROMOTE-MODE-REDESIGN` are
  adopted, individual work items follow via `/lrh-work-item`, per the
  workstream's own `## Proposed Work Items` staged breakdown.
- `session_transcript: pending` should be updated to the durable session
  pointer once available.
