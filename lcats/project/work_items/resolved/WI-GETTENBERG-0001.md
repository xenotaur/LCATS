---
"resolution": "Delivered offline milestone on main in PR #508 (35f80fb53c1820ff70708df0ab049266f25dc3c7); original internal review https://github.com/xenotaur/LCATS/pull/504."
blocked_reason: null
blocked: false
id: "WI-GETTENBERG-0001"
title: "Establish gettenberg baseline and reconcile execution planning"
type: "investigation"
"status": "resolved"
owner: "xenotaur"
contributors:
  - "xenotaur"
assigned_agents: []
related_focus:
  - "FOCUS-WORLDCON-2026"
related_roadmap:
  - "ROADMAP-CORE"
related_workstreams:
  - "WS-GETTENBERG"
related_design:
  - "project/design/proposals/adopted/lcats-gettenberg-redesign/00_proposal.md"
  - "project/development/gettenberg-pilot-charter.md"
depends_on: []
blocked_by: []
expected_actions:
  - "create_report"
  - "create_file"
  - "edit_file"
  - "run_tests"
  - "create_pr"
forbidden_actions:
  - "force_push"
  - "delete_branch"
  - "publish_package"
  - "modify_ci_pipeline"
  - "implement_replacement_library"
acceptance:
  - "A feature/evidence matrix maps design and upstream user-facing capabilities to planned verification, including aliases and multiple titles."
  - "Every discovered active/notebook/experimental/experiments/Kmo caller has a cited migrate/archive/retain disposition and testable library extraction plan where appropriate."
  - "Baseline commands, snapshot identity, fixture provenance, measurements or explicit blockers, and canonical validation results are reproducibly recorded."
  - "Release WIs/workstream/proposal, upstream-watch backlog, and focus/roadmap reflect internal replacement while preserving the near-publication gate."
  - "Next implementation WIs have scope, dependencies, acceptance, validation, and bounded decisions before dispatch."
  - "Charter authority, independent review, run budget, and resumable checkpoint are recorded; lrh validate has zero errors."
required_evidence:
  - "manual_review"
  - "lrh_validate"
  - "test_output"
  - "validation_output"
artifacts_expected:
  - "project/development/gettenberg-baseline.md"
  - "project/development/gettenberg-development-log.md"
  - "project/work_items/proposed/"
  - "project/executions/WI-GETTENBERG-0001/"
---

## Summary

Establish reproducible baseline evidence and a reconciled implementation plan
for WS-GETTENBERG. Produce the inputs and scoped next WIs needed to begin the
replacement under the bounded charter.

## Problem / Context

The approved design leaves engineering choices and repository-wide caller
dispositions to evidence-led implementation. Older release planning still
presents vendor/fork/wait options. This bootstrap produces explicit inputs
without rewriting production code.

### Duplication search

- In-repo: WI-RELEASE-0037 covers the dependency blocker, not the full baseline,
  caller audit, feature matrix, or pilot setup. Reconcile its plan rather than
  independently implement its fix here.
- Sibling repos: LRH provides evidence conventions; the owner knows no sibling
  implementation consumers.
- External libraries: None substitutes for this project-specific audit.
- Recommendation: Proceed with design stage 0.

### Demand search

- Work items: WI-RELEASE-0037 and WI-RELEASE-0039 need updated direction.
- Proposals: PROP-LCATS-GETTENBERG-REDESIGN explicitly requests this baseline.
- Backlog: Upstream-release watch needs a historical supersession note.
- Recommendation: Reconcile/link; leave implementation and near-release
  verification open until their evidence exists.

## Scope

- Read-only source/caller audit and fixture/baseline planning.
- Targeted control-plane reconciliation and downstream WI authoring.
- Reproducible local baseline validation and bounded resource measurements.
- Initial run checkpoint and process observations with independent review.

## Required Changes

1. Create `project/development/gettenberg-baseline.md`: feature/evidence matrix,
   actual file/line citations, caller dispositions, fixture provenance,
   snapshot identity, measurements, reproduction commands, and explicit gaps.
   Audit gettenberg/gatherers, scripts/tools, notebooks, and repository-level
   experimental/experiments/Kmo surfaces; enumerate discovered paths rather
   than assume these names exhaust consumers. Propose library/test destinations
   for core notebook functions; do not edit/archive notebooks in this item.
2. Define fixture coverage for parser edge cases, multiple titles, creator
   aliases/roles, metadata richness, failures, and cleanup regressions. Identify
   reusable cached inputs. Measurements record environment, source/input size,
   elapsed time, and peak-memory method. If no suitable cache exists, document
   bounded acquisition and the gap; do not perform an unbounded download.
3. Reconcile WI-RELEASE-0037, WI-RELEASE-0039, WS-RELEASE, the release-readiness
   proposal, and `project/design/backlog.md` with internal replacement. Preserve
   historical decisions as history, near-publication timing, unrelated release
   gates, and CI restrictions. Do not resolve either release item.
4. Reconcile gettenberg entries in `project/focus/current_focus.md` and
   `project/roadmap/roadmap.md`, preserving other sessions' priorities.
5. Allocate small downstream WIs under WS-GETTENBERG with explicit scope,
   dependencies, behavior acceptance, validation, resource bounds, and decisions.
   At least models/ingestion must be scoped. A separate CI WI must precede CI
   modifications. Run native readiness checks; separately record pilot
   dependency eligibility. Readiness is not authority or proof of main delivery.
6. Update the development log with checkpoints and linked execution evidence.
   Obtain independent review before internal integration. Evidence gaps that
   prevent safe downstream work stop that path rather than becoming a pass.

## Non-Goals

- No replacement implementation or production behavior changes.
- No CI, package dependency, notebook, or canonical corpus modifications.
- No publication, main merge, persistent consent changes, or LRH tooling.
- No full-workstream or pre-publication gate closure.

## Acceptance Criteria

- Feature/evidence matrix, discovered caller dispositions, and reproducible
  baseline exist with provenance and explicit limitations.
- Release/control-plane reconciliation preserves release timing and other gates.
- Next WIs are scoped/checked before dispatch; missing evidence is never a pass.
- Canonical validation, independent review, and resumable checkpoint are recorded;
  LRH validation has zero errors.

The execution evidence includes the independent agent review before internal
integration and the human review of final promotion to main. `manual_review`
records that human review at promotion; it does not add a per-item human gate
inside the pilot. Independent agent review is retained with the validation
evidence. Neither review is satisfied merely by passing automated checks.

## Validation

Run from `lcats/` in the project environment with imports bound to this worktree.
Record exit codes and failures, not just commands.

- `lrh validate`
- `lrh work-items readiness WI-GETTENBERG-0001`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `git diff --check`

Check readiness of each new WI. Manually trace the matrix and discovered callers
to evidence or explicit gaps; verify no canonical data or production changes.

## Dependencies / Order

Start after this planning PR is on main, the concrete charter is approved, and
the human explicitly initiates the run. There is no prerequisite WI; authority
and time are separate prerequisites. Later WIs consume staged evidence only
under the branch-aware charter, without prematurely resolving this item.
