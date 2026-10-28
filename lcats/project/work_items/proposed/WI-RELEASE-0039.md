---
"resolution": null
"blocked_reason": null
"blocked": false
"id": "WI-RELEASE-0039"
"title": "Reverify internal gettenberg readiness immediately before real PyPI publish"
"type": "evaluation"
"status": "proposed"
"owner": "xenotaur"
"contributors":
- "xenotaur"
"assigned_agents": []
"related_focus": []
"related_roadmap": []
"related_workstreams":
- "WS-RELEASE"
"related_design":
- "project/design/proposals/proposed/lcats-pypi-release-readiness/00_proposal.md"
- "project/design/proposals/adopted/lcats-gettenberg-redesign/00_proposal.md"
"depends_on":
- "WI-RELEASE-0037"
"blocked_by": []
"expected_actions":
- "create_report"
- "edit_file"
- "create_pr"
"forbidden_actions":
- "force_push"
- "delete_branch"
- "publish_package"
- "modify_ci_pipeline"
"acceptance":
- "A dated report in the same work session as an imminent real PyPI publish verifies the delivered internal\
  \ gettenberg replacement and current release candidate."
- "Fresh distribution metadata and installation have no gutenbergpy or direct URL/VCS requirement, and\
  \ the current supported Python/environment constraints are verified."
- "Current parser/title/alias, first-use/offline, cache recovery and caller migration evidence remains\
  \ valid for the release candidate; relevant dependency/security or upstream data-format changes are\
  \ assessed."
- "Any discrepancy is reported to the human before publication; the item does not silently redesign or\
  \ change dependencies."
- "An early dry run does not resolve this item; lrh validate reports zero errors."
"required_evidence":
- "manual_review"
- "lrh_validate"
"artifacts_expected":
- "project/executions/WI-RELEASE-0039/"
---

## Summary

Reverify the delivered internal gettenberg replacement immediately before an
actual LCATS PyPI publication attempt. This gate is tied to the publish event,
not completion of the implementation pilot or an arbitrary date.

## Problem / Context

### Historical decision context (superseded 2026-10-14)

The original gate revisited upstream release availability and vendor/fork drift.
Its timing requirement remains; the selected implementation is now internally
owned gettenberg under PROP-LCATS-GETTENBERG-REDESIGN. The original text is
preserved in this file's history at `5cfd2d71`. A later upstream gutenbergpy
release does not automatically reverse the owner's approved redesign.

### Duplication search

- This is WS-RELEASE's existing near-publication gate; no second gate is created.
- No sibling service/library substitutes for checking the actual LCATS release.

### Demand search

- WI-RELEASE-0037 supplies dependency-blocker resolution; gettenberg qualification
  supplies implementation evidence, which must still match the release candidate.
- Recommendation: retain the imminent-publication timing and human escalation.

## Scope

Current release candidate, packaging independence, supported behavior, retained
provenance and relevant general dependency/source-format changes.

## Required Changes

1. Confirm with the human that a real publish is imminent; identify exact
   candidate commit/version and the previously delivered replacement evidence.
2. Rebuild/inspect/install the distribution in an isolated environment without
   gutenbergpy. Verify no direct URL requirements and current environment support.
3. Recheck affected behavior and evidence after intervening changes, including
   titles/aliases, offline/first-use, cache recovery and caller migration.
4. Assess relevant dependency/security or Gutenberg source-format changes;
   report discrepancies to the human instead of silently revising the design.
5. Record dated commands/results and review. Do not perform publication here.

## Non-Goals

No publication, CI changes, periodic upstream-release monitoring, automatic
redesign, or premature resolution immediately after WI-RELEASE-0037.

## Acceptance Criteria

All frontmatter criteria hold in the same work session as imminent publication.
An earlier rehearsal or pilot result is evidence input, not satisfaction.

## Validation

- `lrh validate` and exact-release-candidate package metadata/install checks.
- Relevant canonical/behavior checks and dated manual review of the evidence.

## Risk Notes

This gate loses its purpose if resolved before publication is actually imminent.
WI-RELEASE-0037 must first resolve; any discrepancy returns to the human.

## Dependencies / Order

Depends on WI-RELEASE-0037. Run immediately before the actual publication attempt;
this pilot does not execute or resolve it.
