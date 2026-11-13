---
id: WS-GENRE-HUMAN-REVIEW
kind: planning_node
title: Human Genre Review and Adjudication
status: proposed
stage: planned
origin: follow_up
summary: "Coordinate the design, implementation, bounded review, and reporting needed to turn the 49 WI-GENRE-0110 disagreements into traceable human genre evidence."
rationale: "The original genre-sidecar infrastructure workstream is closed after delivering metadata/model evidence and append-safe sidecars. Its plan explicitly deferred human review/adjudication; this successor preserves the historical closeout while giving that stage its own lifecycle and exit criteria."
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_design:
  - project/design/proposals/adopted/genre-evidence-sidecars/00_proposal.md
  - project/design/genre-sidecars-in-release-workflow.md
  - project/workstreams/resolved/WS-GENRE-EVIDENCE-SIDECARS.md
work_items:
  []
exit_criteria:
  - "WI-GENRE-0111 is resolved with its human-review implementation and execution evidence landed."
  - "All 49 WI-GENRE-0110 disagreement cases have deterministic review status: reviewed, unresolved, or explicitly excluded with rationale."
  - "Human assessments preserve existing metadata/model evidence and carry reviewer, timestamp, rationale, decision status, and source/story provenance."
  - "Optional current_adjudication references are explicit and validated; unreviewed stories remain unadjudicated."
  - "Reports document reviewed, unresolved, excluded, and downstream-ready cases, and lrh validate reports 0 errors."
---

# Workstream: WS-GENRE-HUMAN-REVIEW

## Purpose

This successor workstream coordinates the human-review and adjudication stage of the genre-labeling effort. It follows the completed metadata/model evidence pipeline and WI-GENRE-0110's three-way comparison, which identified 49 disagreements in the shared 146-story sample.

The parent `WS-GENRE-EVIDENCE-SIDECARS` remains closed; this is a fresh successor rather than a reopening, following the repository's established follow-on pattern. The parent explicitly listed human review as "Not yet scoped as its own work item."

## Scope

- Implement and validate WI-GENRE-0111's deterministic review manifest and human-assessment append path.
- Review a bounded, explicitly identified subset of the 49 disagreements.
- Produce auditable reports for reviewed, unresolved, excluded, and adjudicated cases.
- Preserve all metadata/model evidence and distinguish human assessments from automatic labels.

## Prior Art Check

### Duplication search

- In-repo: Related infrastructure exists in the closed `WS-GENRE-EVIDENCE-SIDECARS`, `genre-sidecar-v1`, and WI-GENRE-0110. No existing successor workstream for human genre review/adjudication was found.
- Sibling repositories: None identified.
- External libraries: None identified; this is an LCATS-specific evidence/provenance workflow.
- Recommendation: Proceed with a fresh successor workstream rather than reopening the closed parent.

This follows the repository precedent of creating a fresh follow-on after a closed investigation or evaluation workstream.

### Demand search

- Work items: `WI-GENRE-0111`, "Add human genre review and adjudication support," directly covers this workstream's first deliverable.
- Proposals: The adopted genre-evidence-sidecars proposal explicitly calls for human review/adjudication support.
- Backlog: No matching backlog entry was found.
- Recommendation: Link WI-GENRE-0111 to this workstream; do not close or reopen existing workstreams.

## Work Items

- **WI-GENRE-0111** — Add a deterministic manifest for the 49 disagreements, a validated human-assessment append path, bounded review outputs, and reporting. This item is currently proposed on its own open PR and will be added to authoritative workstream frontmatter after it lands.
- Future review/adjudication work items may be added only after their scope and dependencies are explicit.

## Exit Criteria

- WI-GENRE-0111 is resolved and its execution evidence is landed.
- All 49 disagreement cases have deterministic status accounting with no silent drops.
- Human assessment records preserve prior evidence and include reviewer, provenance, rationale, and decision-status fields.
- Any `current_adjudication` pointer/reference is explicit, validated, and absent for unreviewed stories.
- Review reports clearly distinguish reviewed, unresolved, excluded, and downstream-ready cases.
- `lrh validate` reports zero errors.

## Non-Goals

- Do not reopen or modify `WS-GENRE-EVIDENCE-SIDECARS` or rewrite its historical closeout.
- Do not rerun Claude Opus, `gpt-oss:20b`, or any other model.
- Do not modify historical validation JSONL or WI-GENRE-0110 comparison artifacts.
- Do not automatically promote metadata/model agreement to ground truth.
- Do not adjudicate all 146 stories by default; review must be bounded and explicit.
- Do not replace or wholesale-rewrite `corpora/`.
- Do not build a general-purpose annotation UI or event-analysis workflow in this stream.

## Relationship to Design and Prior Work

- Adopted design: `project/design/proposals/adopted/genre-evidence-sidecars/00_proposal.md`
- Prior workstream: `project/workstreams/resolved/WS-GENRE-EVIDENCE-SIDECARS.md`
- Comparison implementation: `WI-GENRE-0110`
- Current human-review item: `WI-GENRE-0111`

## Open Questions

- What exact bounded subset of the 49 disagreements should be reviewed first?
- Should `current_adjudication` reference assessment IDs, normalized labels, or both?
- What reviewer identity and review protocol should be recorded for the first tranche?
