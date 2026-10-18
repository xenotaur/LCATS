---
"resolution": null
"blocked_reason": null
"blocked": false
"id": "WI-GETTENBERG-0010"
"title": "Qualify replacement, exercise Diataxis docs and reconcile delivery"
"type": "evaluation"
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
- "WI-GETTENBERG-0008"
- "WI-GETTENBERG-0009"
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
- "All ten governing design completion criteria have exact-head acceptance-to-evidence links, including\
  \ full-snapshot predicate/accounting and resource/corpus comparisons."
- "Tutorial/how-to/reference/explanation examples are executed and match actual first-use, cached, offline\
  \ and recovery behavior."
- "Canonical checks and independent review pass; fresh package metadata/import checks confirm dependency\
  \ independence."
- "Main promotion is human-approved and native closeout accurately reconciles delivered items; pre-publication\
  \ WI-RELEASE-0039 remains a later gate."
"required_evidence":
- "manual_review"
- "lrh_validate"
- "test_output"
- "validation_output"
"artifacts_expected":
- "docs/"
- "project/development/"
- "project/executions/"
- "project/work_items/"
- "project/workstreams/"
---

## Summary

Qualify replacement, exercise Diataxis docs and reconcile delivery under the approved gettenberg redesign.

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

Measure on immutable recorded inputs, distinguish audit time from full old/new build time, record memory method/disk/network bytes and explain every material corpus difference. Use bounded runs with explicit resource budgets; missing baseline evidence is a gap, not a pass. Keep publication and canonical corpus promotion out of scope. Record process observations, alternatives and LRH acceptance-test recommendations without claiming one pilot proves speedup. One final main promotion is the default; propose earlier milestone only for review size, integration risk or design issues.

## Required Changes

1. All ten governing design completion criteria have exact-head acceptance-to-evidence links, including full-snapshot predicate/accounting and resource/corpus comparisons.
2. Tutorial/how-to/reference/explanation examples are executed and match actual first-use, cached, offline and recovery behavior.
3. Canonical checks and independent review pass; fresh package metadata/import checks confirm dependency independence.
4. Main promotion is human-approved and native closeout accurately reconciles delivered items; pre-publication WI-RELEASE-0039 remains a later gate.

## Acceptance Criteria

The first three frontmatter criteria are pre-integration qualification gates: they require exact-head evidence and independent review before internal integration. The fourth is a post-main delivery gate, verified only after the human approves promotion and that promotion lands. Internal integration must include a reviewable closeout plan, but must not claim main delivery or completed closeout. Native execution records remain in_progress and work items nonterminal until the post-main gate is satisfied. The completion mapping distinguishes implemented technical criteria from the still-pending promotion and closeout criteria; it never labels pending delivery as accepted.

## Validation

Run from `lcats/` in the project environment with imports bound to this worktree:

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `lrh work-items readiness WI-GETTENBERG-0010`
- `git diff --check`

Add focused behavior tests for the criteria above; unit tests are offline. Record commands, exit codes, fixture provenance and independent review separately from automated checks.

## Dependencies / Order

Dependencies listed above require canonical resolution or independently reviewed staged acceptance at an ancestor of the assignment base under the pilot charter. Native readiness alone does not prove dependency acceptance. No dispatch before the coordinator records that mapping and remaining budget.


## Qualification checkpoint — 2026-10-18

The [qualification matrix](../../development/gettenberg-qualification.md) records
full local catalog/resource and installed-package evidence plus executed Diataxis
examples. Real cached-corpus comparison exposed a blocking cleanup/extractor
composition problem, including earlier-body changes and severe truncations.
The [repair scope](../../development/gettenberg-corpus-repair-plan.md) defines the
next narrative-preservation investigation and acceptance. This item is not accepted
or resolved; its first pre-integration gate remains unsatisfied. Keep the
qualification PR unmerged until repaired and requalified. No acceptance criterion
or main-promotion requirement changes.
