---
"resolution": null
"blocked_reason": null
"blocked": false
"id": "WI-GETTENBERG-0009"
"title": "Replace Gutenberg CI cache maintenance with supported operations"
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
- "WI-GETTENBERG-0004"
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
"acceptance":
- "Ordinary unit CI remains offline and does not build/download a full Gutenberg catalog."
- "Explicit maintenance uses real supported catalog commands, correct cache selection and failure propagation\
  \ rather than mocked tests or || true."
- "Cache keys account for schema/parser/input identity and preserve reusable archives without silently\
  \ trusting incompatible catalogs."
- "Workflow trigger/check inventory and dry-run failure-path validation demonstrate no weakened required\
  \ checks."
"required_evidence":
- "manual_review"
- "lrh_validate"
- "test_output"
- "validation_output"
"artifacts_expected":
- "../.github/workflows/cache_maintenance.yml"
- "../.github/workflows/tests.yml"
- "../.github/workflows/coverage.yml"
- "docs/how-to/"
---

## Summary

Replace Gutenberg CI cache maintenance with supported operations under the approved gettenberg redesign.

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

This is the only initial gettenberg WI authorizing CI pipeline edits. Inspect current GitHub Actions cache ID/key behavior before implementing deletion; never delete production caches during validation. Use workflow fixtures/local command tests and a separately approved live maintenance rehearsal if required. Keep final main-target lint/test/coverage checks; document internal-branch trigger behavior. No publishing or credential changes.

## Required Changes

1. Ordinary unit CI remains offline and does not build/download a full Gutenberg catalog.
2. Explicit maintenance uses real supported catalog commands, correct cache selection and failure propagation rather than mocked tests or || true.
3. Cache keys account for schema/parser/input identity and preserve reusable archives without silently trusting incompatible catalogs.
4. Workflow trigger/check inventory and dry-run failure-path validation demonstrate no weakened required checks.

## Acceptance Criteria

All frontmatter acceptance criteria require exact-head evidence and independent review before integration. Native execution records remain in_progress and work items nonterminal until human-approved main delivery.

## Validation

Run from `lcats/` in the project environment with imports bound to this worktree:

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `lrh work-items readiness WI-GETTENBERG-0009`
- `git diff --check`

Add focused behavior tests for the criteria above; unit tests are offline. Record commands, exit codes, fixture provenance and independent review separately from automated checks.

## Dependencies / Order

Dependencies listed above require canonical resolution or independently reviewed staged acceptance at an ancestor of the assignment base under the pilot charter. Native readiness alone does not prove dependency acceptance. No dispatch before the coordinator records that mapping and remaining budget.
