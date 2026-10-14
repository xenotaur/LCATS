---
"resolution": null
"blocked_reason": null
"blocked": false
"id": "WI-RELEASE-0037"
"title": "Verify LCATS-owned gettenberg resolves the PyPI dependency blocker"
"type": "deliverable"
"status": "proposed"
"owner": "xenotaur"
"contributors":
- "xenotaur"
"assigned_agents": []
"related_focus": []
"related_roadmap": []
"related_workstreams":
- "WS-RELEASE"
- "WS-GETTENBERG"
"related_design":
- "project/design/proposals/proposed/lcats-pypi-release-readiness/00_proposal.md"
- "project/design/proposals/proposed/lcats-gettenberg-redesign/00_proposal.md"
"depends_on":
- "WI-GETTENBERG-0008"
- "WI-GETTENBERG-0010"
"blocked_by": []
"expected_actions":
- "edit_file"
- "create_file"
- "run_tests"
- "create_pr"
"forbidden_actions":
- "force_push"
- "delete_branch"
- "publish_package"
- "modify_ci_pipeline"
"acceptance":
- "The approved internal redesign is delivered on main with no active gutenbergpy imports or installation\
  \ requirements; no vendor/fork/wait path is substituted."
- "pyproject.toml and environment.yml remove the external dependency consistently, and built distribution\
  \ metadata contains no direct URL/VCS requirements."
- "Real parser-to-SQLite tests cover multiple titles and contributor aliases; caller migration, offline/first-use\
  \ behavior and corpus comparisons have linked verification."
- "A fresh wheel installation works without gutenbergpy; canonical validation and independent review qualify\
  \ the release blocker resolution."
- "lrh validate reports zero errors; publication and near-publication WI-RELEASE-0039 remain separate."
"required_evidence":
- "manual_review"
- "lrh_validate"
- "test_output"
"artifacts_expected":
- "project/executions/WI-RELEASE-0037/"
- "pyproject.toml"
- "environment.yml"
- "src/lcats/gettenberg/"
---

## Summary

Verify that WS-GETTENBERG delivers the internally owned replacement and removes
the external gutenbergpy dependency from runtime and distribution metadata.
Implementation belongs to the linked gettenberg work items; this item retains
release-blocker ownership rather than duplicating their code changes.

## Problem / Context

### Historical decision context (superseded 2026-10-14)

The original item investigated waiting for upstream, vendoring its cache-builder
closure, or publishing a maintained fork. Alias/title fixes motivated the VCS
pin. That history remains available in this file at commit `5cfd2d71`; it is
not an active implementation instruction. The owner chose a full internal
redesign in PROP-LCATS-GETTENBERG-REDESIGN (PR #501), without a hard release date.
The upstream-release watch no longer blocks the decision.

### Duplication search

- Existing gettenberg implementation and WS-GETTENBERG own replacement delivery.
- No sibling consumer or separate replacement is known; no vendor/fork project is planned.
- Recommendation: verify/link delivered evidence rather than implement twice.

### Demand search

- WI-GETTENBERG-0008 and WI-GETTENBERG-0010 supply migration/qualification evidence.
- WS-RELEASE and the release-readiness proposal retain release coordination.
- Recommendation: keep this gate open until delivery is demonstrated.

## Scope

Release-blocker verification of the internal replacement, package/environment
requirements, fresh-wheel installation, and linked behavior evidence.

## Required Changes

1. Inspect delivered gettenberg migration/qualification evidence against the
   approved design; verify aliases and titles through the real ingestion path.
2. Build and inspect wheel/sdist metadata for external gutenbergpy and other
   direct URL requirements; verify a fresh installation without gutenbergpy.
3. Link exact commits, commands/results and reviewer findings in the execution
   record. Do not infer delivery from an internal integration merge.
4. Resolve only after human-approved main delivery and demonstrated acceptance;
   leave WI-RELEASE-0039 to an imminent publication session.

## Non-Goals

No vendoring, upstream wait, fork publication, CI changes, package publication,
release infrastructure expansion, or automatic corpus promotion.

## Acceptance Criteria

All frontmatter acceptance criteria are verified with linked exact-head evidence.
No work item is resolved by this planning reconciliation alone.

## Validation

- `scripts/format --check --diff`, `scripts/lint`, `scripts/test`, `lrh validate`.
- Fresh wheel build/install, dependency metadata inspection and supported offline
  catalog/gather smoke tests against recorded fixtures.
- Independent review of evidence, not just a green automated check.

## Dependencies / Order

WI-GETTENBERG-0008 and WI-GETTENBERG-0010 must deliver the replacement before this
release verification resolves. WI-RELEASE-0039 runs near actual publication.
