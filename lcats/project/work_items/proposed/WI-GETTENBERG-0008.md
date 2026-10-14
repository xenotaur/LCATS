---
"resolution": null
"blocked_reason": null
"blocked": false
"id": "WI-GETTENBERG-0008"
"title": "Migrate callers and remove gutenbergpy packaging dependency"
"type": "deliverable"
"status": "proposed"
"owner": "xenotaur"
"contributors":
- "xenotaur"
"assigned_agents": []
"related_focus":
- "FOCUS-WORLDCON-2026"
"related_roadmap":
- "ROADMAP-CORE"
"related_workstreams":
- "WS-GETTENBERG"
"related_design":
- "project/design/proposals/proposed/lcats-gettenberg-redesign/00_proposal.md"
- "project/development/gettenberg-pilot-charter.md"
"depends_on":
- "WI-GETTENBERG-0003"
- "WI-GETTENBERG-0007"
"blocked_by": []
"expected_actions":
- "create_file"
- "edit_file"
- "run_tests"
- "create_pr"
"forbidden_actions":
- "force_push"
- "delete_branch"
- "publish_package"
- "promote_canonical_corpus"
- "modify_ci_pipeline"
"acceptance":
- "Every caller in the baseline inventory has an implemented migrate/archive/retain disposition with verification."
- "Reusable notebook/experimental core logic lives in tested libraries; maintained notebooks are minimal\
  \ clients and archives are explicitly unsupported historical evidence."
- "Active code and installation metadata contain no gutenbergpy dependency or VCS requirement; fresh wheel\
  \ install works without gutenbergpy."
- "Representative corpus comparisons explain material differences without promoting generated outputs\
  \ or rewriting historical experiment results."
"required_evidence":
- "manual_review"
- "lrh_validate"
- "test_output"
- "validation_output"
"artifacts_expected":
- "src/lcats/"
- "tests/"
- "notebooks/"
- "KMo/"
- "experimental/"
- "../experiments/"
- "pyproject.toml"
- "environment.yml"
- "docs/"
---

## Summary

Migrate callers and remove gutenbergpy packaging dependency under the approved gettenberg redesign.

## Problem / Context

See the measured baseline and caller inventory in `project/development/gettenberg-baseline.md`.

### Duplication search

- In-repo: existing gettenberg is the replacement target; no separate item for this tranche was found in the initial WI inventory. Reuse adjacent LCATS utilities where applicable.
- Sibling repositories: no known consumers or replacement implementations; LRH supplies process conventions only.
- External libraries: standard parsing/storage utilities are permitted; gutenbergpy, a fork, and a hosted replacement are outside the chosen direction.
- Recommendation: implement this bounded part of WS-GETTENBERG rather than duplicate release ownership.

### Demand search

- Governing proposal and WS-GETTENBERG request this tranche; WI-RELEASE-0037 owns the resulting release blocker verification.
- Upstream-watch backlog is historical, not a prerequisite. Link evidence; do not close release items automatically.

## Scope

Use the cited baseline inventory as the ownership checklist; add newly discovered callers explicitly. Preserve public user-facing capabilities rather than old SQL/API/MongoDB contracts. Do not duplicate existing gatherers.extractors, readers or reconcile helpers. Update environment and pyproject together. Package any required data resources and verify wheel contents. Link evidence to WI-RELEASE-0037 without resolving it before delivery and review. No CI edits here; coordinate WI-GETTENBERG-0009. Split implementation into smaller child items before dispatch if inventory size exceeds a reviewable change.

## Required Changes

1. Every caller in the baseline inventory has an implemented migrate/archive/retain disposition with verification.
2. Reusable notebook/experimental core logic lives in tested libraries; maintained notebooks are minimal clients and archives are explicitly unsupported historical evidence.
3. Active code and installation metadata contain no gutenbergpy dependency or VCS requirement; fresh wheel install works without gutenbergpy.
4. Representative corpus comparisons explain material differences without promoting generated outputs or rewriting historical experiment results.

## Acceptance Criteria

All frontmatter acceptance criteria require exact-head evidence and independent review before integration. Native execution records remain in_progress and work items nonterminal until human-approved main delivery.

## Validation

Run from `lcats/` in the project environment with imports bound to this worktree:

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `lrh work-items readiness WI-GETTENBERG-0008`
- `git diff --check`

Add focused behavior tests for the criteria above; unit tests are offline. Record commands, exit codes, fixture provenance and independent review separately from automated checks.

## Dependencies / Order

Dependencies listed above require canonical resolution or independently reviewed staged acceptance at an ancestor of the assignment base under the pilot charter. Native readiness alone does not prove dependency acceptance. No dispatch before the coordinator records that mapping and remaining budget.
