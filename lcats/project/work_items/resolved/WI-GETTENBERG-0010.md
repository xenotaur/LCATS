---
resolution: "Qualified the bounded replacement under approved Q1–Q8 and A–D acceptance, delivered it on main in PR #534 (b4ec4c45), and reconciled native lifecycle records; GPA-A–E, PR #524 and release gates remain open."
"blocked_reason": null
"blocked": false
"id": "WI-GETTENBERG-0010"
"title": "Qualify replacement, exercise Diataxis docs and reconcile delivery"
"type": "evaluation"
status: "resolved"
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
- "project/design/proposals/adopted/lcats-gettenberg-redesign/00_proposal.md"
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
  \ full-snapshot predicate/accounting and resource/corpus comparisons under the approved Q1–Q8 scope amendment."
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

Measure on immutable recorded inputs, distinguish audit time from full old/new build time, record memory method/disk/network bytes and account for every material replacement-induced corpus difference under the approved Q1–Q8 scope amendment. Use bounded runs with explicit resource budgets; missing baseline evidence is a gap, not a pass. Keep publication and canonical corpus promotion out of scope. Record process observations, alternatives and LRH acceptance-test recommendations without claiming one pilot proves speedup. One final main promotion is the default; propose earlier milestone only for review size, integration risk or design issues.

## Required Changes

1. All ten governing design completion criteria have exact-head acceptance-to-evidence links, including full-snapshot predicate/accounting and resource/corpus comparisons under the approved Q1–Q8 scope amendment.
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


## Approved scope and qualification amendment — 2026-10-22

The human approved the four decisions in the
[scope and causality audit](../../development/gettenberg-scope-causality-audit.md#human-decisions-and-next-sequence--2026-10-22).
Its [Q1–Q8 gates](../../development/gettenberg-scope-causality-audit.md#approved-qualification-criteria--adopted-2026-10-22)
govern the narrower candidate. This explicitly amends the corpus portion of scope,
frontmatter acceptance and required change 1, and clarifies governing design criterion
8; criteria 1–7 and 9–10 remain. The October 18 checkpoint above is historical, not a
requirement to finish all editorial reconciliation before provider delivery.

Use immutable stage-specific comparisons to account for each measured input and
material provider effect as an intended documented change, repaired regression,
explicit operational refusal or unresolved blocker. Prove independent gather defects
by controlled reproduction; preserve their evidence and follow-up separately from
provider acceptance. Unknown material provider effects still block until investigated
or narrowly contained. Missing historical wire provenance is an explicitly accepted
evidence boundary, never evidence of equivalence. Quantify usable gather yield; broad
refusal is not a substitute for successful operation.

Construct from migration reference ed20e9c2 with necessary replacement improvements
and the two narrow terminal-notice repair candidates, subject to full candidate
qualification. Preserve PR524 and the broader gather work for later reconciliation.
This planning approval and PR528 internal integration do not satisfy the product's
pre-integration gates or authorize main promotion, corpus promotion, package publication
or terminal closeout. A subsequent bounded grant is required for candidate construction.

### 2026-10-23 causal/yield evidence checkpoint

[PR #530 evidence](../../../../experiments/10_gettenberg_qualification/results/gettenberg-causal-yield-20261023/README.md)
now accounts for all 67 cleaner-substitution differences and 13 explicit refusals.
Production is unchanged. Actual configured-order gathering on the frozen decoded
cohort publishes 41 before refusing3699 and leaving1,617unattempted; isolated
one-item calls publish 1,646 and refuse13, with 1,646 unchanged empty-cache reuses.
These are separate measurements, not interchangeable yield claims. Q5 remains
blocked by batch fail-fast behavior. Causal accounting does not approve body
contracts or close Q1–Q8. The candidate manifest records bounded next decisions;
this WI and native executions remain nonterminal pending human delivery.


### 2026-10-24 delivery review checkpoint

The [delivery decision sheet](../../development/gettenberg-delivery-decision.md)
maps all ten design criteria and Q1–Q8 to the narrower candidate. The corrected
normal batch publishes/reuses 1,646, explicitly refuses 13 and leaves zero unattempted;
this supersedes the historical fail-fast checkpoint above. Fresh installed wheel/CLI
qualification and independent review support conditional internal integration.
Four human decisions remain: refusal exclusions, 55 retained notices, 12 specific
body effects and the measured scope/follow-up boundary. No decision is inferred from
causal accounting or passing tests. Keep native records nonterminal and do not
integrate until the decisions and final-head validation are recorded. Main promotion
and release verification remain separate.


### Human acceptance checkpoint — 2026-10-24

The human accepted A–D subject to durable backlog capture. The
[post-adoption register](../../development/gettenberg-post-adoption-backlog.md)
and [acceptance record](../../development/gettenberg-adoption-acceptance.json)
fulfill that condition: 13 exclusions, 55 notice additions, 12 specific body effects
and measured scope/provenance limits are accepted for bounded replacement delivery,
with follow-up still open. The prior checkpoint's pending-decision language is
historical. Do not rewrite experimental acceptance flags or mark native work resolved;
internal integration checks, separate main promotion and truthful closeout remain.


### Internal integration and main-review checkpoint — 2026-10-24

Human-authorized PR #530 internal merge df055256 preserves the exact approved tree.
The [main-promotion review guide](../../development/gettenberg-main-promotion.md)
records current-main synchronization, fresh canonical/package qualification and the
post-main closeout plan. A–D remain accepted with their durable backlog open. This
satisfies the internal-integration step, not the fourth/post-main acceptance gate;
keep this work item and staged executions nonterminal while main review is pending.
