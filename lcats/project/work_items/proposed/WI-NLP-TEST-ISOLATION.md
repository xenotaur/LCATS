---
id: "WI-NLP-TEST-ISOLATION"
title: "Separate native NLP smoke tests from ordinary unit discovery"
type: "deliverable"
status: "proposed"
blocked: false
blocked_reason: null
resolution: null
owner: "xenotaur"
contributors: ["xenotaur"]
assigned_agents: []
related_focus: ["FOCUS-WORLDCON-2026"]
related_roadmap: ["ROADMAP-CORE"]
related_workstreams: []
related_design:
  - "project/design/event-role-world-surface-feature-nlp-evaluation.md"
depends_on: []
blocked_by: []
expected_actions:
  - "edit_file"
  - "create_file"
  - "run_tests"
  - "write_docs"
  - "create_pr"
forbidden_actions:
  - "modify_pr_548"
  - "change_production_gpu_defaults"
  - "repair_contributor_gpu_environment"
  - "disable_existing_test_coverage"
  - "force_push"
  - "delete_branch"
  - "merge_pr"
  - "publish_package"
acceptance:
  - "Ordinary test discovery neither imports optional NLP packages nor loads their models, regardless of installed extras."
  - "Four existing real-model checks are preserved in an explicit CPU smoke suite, with the remaining ordinary coverage retained."
  - "Requested smoke validation fails clearly on missing prerequisites, native failures, assertion failures, timeouts, or zero selected tests."
  - "Native integration checks run in bounded child processes with preserved diagnostics and parent continuation after failure."
  - "A bounded CPU smoke CI job runs manually and weekly, provisions versioned dependencies/models separately, and preserves failure diagnostics."
  - "Canonical validation, CPU smoke execution, unchanged production defaults, and an untouched PR #548 are evidenced in a separate PR against main."
required_evidence:
  - "test_output"
  - "lrh_validate"
  - "manual_review"
artifacts_expected:
  - "lcats/tests/analysis_tests/event_role_world_test.py"
  - "lcats/tests/analysis_tests/linguistics_test.py"
  - "lcats/tests/smoke/*_smoke.py and test-only subprocess support"
  - "lcats/tests/analysis_tests/event_role_world_harness_test.py"
  - "lcats/scripts/smoke and lcats/scripts/README.md"
  - "lcats/docs/how-to/run-nlp-tests.md and documentation index link"
  - ".github/workflows/smoke.yml and smoke-only dependency/model provisioning configuration"
  - "Non-executable diagnostic evidence and implementation execution record"
---

# Work Item: WI-NLP-TEST-ISOLATION

## Summary

Separate native NLP integration checks into an explicit CPU smoke suite so
ordinary tests do not depend on optional models or GPU installations. Deliver
the fix in a separate PR against main, preserving Kenny's PR #548 and all
production GPU defaults.

## Problem / Context

At main commit `132c586270fe23df9f06479c523b170886eec78e`,
`tests/analysis_tests/event_role_world_test.py:22-40` and `:349-363` construct
spaCy and Stanza pipelines during import under OS-level output suppression.
`tests/analysis_tests/linguistics_test.py:1567-1598` also constructs a spaCy
backend during discovery for two real-model checks. Meanwhile,
`pyproject.toml:63-78` makes these packages optional through `[nlp]`, and the
ordinary CI workflow installs only `[test]`. Installed optional packages should
not change the resource requirements of ordinary discovery.

Kenny's 2026-11-12 diagnostic archives, `diagOutput.zip` and
`diagOutput-after.zip`, establish the following supplied evidence:

- spaCy alone passes. Stanza alone, module import, and module execution abort
  with SIGABRT when Stanza selects CUDA. The diagnostic is
  `Invalid handle. Cannot load symbol cudnnGetVersion`.
- With `CUDA_VISIBLE_DEVICES=-1`, Stanza explicitly selects CPU, loads its
  processors, and completes inference. All 123 event-role-world tests pass,
  including both real-backend checks; neither is skipped.
- Reported Python/package versions match between runs. The exact native
  library installation defect remains undiagnosed. The CPU workaround is not
  evidence of repaired GPU support or of a complete full-suite pass.

The user approved the separate smoke-test approach and bounded CPU smoke CI
workflow on 2026-11-12. Preserve
these observations in implementation evidence with archive/member provenance;
do not rely solely on temporary local paths or claim to have reproduced the
GPU failure on a different machine.

### Duplication search

- In-repo: existing fake NLP backends, capture utilities, and four real-model
  checks are related; no dedicated smoke command or equivalent isolation fix
  was found. Extend those checks rather than duplicating their assertions.
- Sibling repos: LRH's `scripts/smoke` discovers `tests/smoke/*_smoke.py`,
  separately from ordinary `*_test.py` discovery. Adopt that small convention.
- External libraries: Python unittest, subprocess, and faulthandler provide
  the necessary mechanisms; no new dependency or test framework is required.
- Recommendation: proceed with a narrow test-suite separation.

### Demand search

- Work items: WI-EVENT-0024 delivered the original backends and is resolved;
  no matching open repair item was found.
- Proposals: no matching open test-isolation proposal was found.
- Backlog: no matching native-crash repair entry was found.
- Recommendation: create this standalone item without reopening prior work.

## Scope

- Separate the four identified real-model checks from ordinary discovery.
- Add an explicit CPU smoke command, bounded child execution, and diagnostics.
- Preserve ordinary fake-backed coverage and add focused harness regressions.
- Document prerequisites, invocation, failure semantics, and validation evidence.
- Add one manual/weekly CPU smoke CI job with explicit setup and diagnostic artifacts.

## Required Changes

1. Remove native model availability probes and the two real-backend checks
   from `tests/analysis_tests/event_role_world_test.py`. Relocate those checks
   without weakening their assertions. The original coverage becomes 121
   ordinary tests plus two smoke tests, before new harness tests are counted.
2. Relocate the two checks in `LinguisticsOptionalNLPTest` from
   `tests/analysis_tests/linguistics_test.py` and remove its discovery-time
   model probe. Preserve sidecar validation and repaired-tokenization assertions.
3. Place these checks under `tests/smoke/*_smoke.py`. Add a thin
   `scripts/smoke` entry point, following LCATS script conventions, with
   documented help, check, and dry-run behavior. Keep package initializers
   free of native initialization so ordinary recursive discovery remains safe.
4. Configure each smoke child for CPU before optional native imports and invoke
   the actual LCATS backends. Prefer child-local configuration over changing
   production code. Only if strictly necessary, introduce a minimal optional
   keyword-only device seam that preserves omitted-argument behavior; justify
   and test it explicitly. Never change parent/global environment settings or
   production callers/defaults.
5. Keep assertions in the child and propagate their outcomes. Bound execution,
   capture stdout/stderr and fault output independently of suppression, and
   report failures with backend identity, exit/signal/timeout information, and
   useful diagnostics. Continue remaining smoke checks after a child fails,
   but return nonzero overall. Keep successful output concise.
6. Explicit smoke invocation requires its documented packages and models.
   Missing prerequisites and zero selected checks are non-success outcomes;
   do not return green with all checks skipped or turn arbitrary load errors
   into availability skips. Test execution must not install or download models.
7. Add `tests/analysis_tests/event_role_world_harness_test.py` covering discovery
   without optional imports, missing prerequisites, success, failed assertions,
   native-like signal termination where supported, timeout, and parent
   continuation. Exercise subprocess boundaries with small controlled fixtures;
   these harness tests must not themselves require NLP packages/models.
8. Document setup separately from execution in `docs/how-to/run-nlp-tests.md`,
   link it from the documentation index and `scripts/README.md`, and explain
   that unit success does not certify real NLP integrations or GPU support.
   Require recorded smoke results before merging changes to NLP backends or
   these smoke tests. Record library/model versions with smoke evidence.
9. Branch implementation from current main in an isolated checkout and open a
   separate implementation PR against main. Do not edit, push to, rebase, or
   resolve threads on Kenny's PR #548. Record the assertion relocation map,
   diagnostics, and validation in the implementation execution record.
10. Add `.github/workflows/smoke.yml` with `workflow_dispatch` and a weekly
    schedule, one Ubuntu 24.04 / Python 3.11 CPU job, `contents: read`, and
    concurrency cancellation for redundant runs on the same ref. Run package
    commands from `lcats/`. Set an initial 20-minute job timeout and a shorter
    test-step timeout that leaves room for diagnostics; retain child timeouts.
11. Provision the optional NLP packages, a compatible CPU PyTorch build, and
    exactly the models used by the four checks in explicit CI setup steps.
    Use a smoke-only version manifest/constraints and version-keyed dependency
    and model caches. Record effective versions and resource identities.
    Cache misses must rebuild the environment; cache hits must not substitute
    for checking prerequisites. Do not change production dependency defaults.
    Keep downloads in setup, with offline execution of `scripts/smoke`.
12. Upload useful setup/test logs and smoke diagnostics with an always-run
    artifact step when available, including on failure. Preserve nonzero
    status for missing resources, zero executed checks, assertions, native
    failures, and timeouts; do not mask failure through logging pipelines.
    Document manual invocation, the weekly schedule, artifact retrieval, and
    the fact that this workflow is not a publication gate.

## Non-Goals

- Do not repair or upgrade Kenny's CUDA, cuDNN, driver, or Python environment.
- Do not change production GPU defaults or add automatic production fallback.
- Do not modify gatherers, gettenberg, corpus outputs, or Kenny's branch.
- Do not build a general test-runner framework or GPU CI matrix.
- Do not remove coverage or hide failing checks through renaming or skipping.
- Do not reopen delivered workstreams or merge either PR.
- Do not add GPU jobs, a platform matrix, automatic PR triggers, tag triggers,
  or publication gating in this item. Relevant-path PR triggers and release
  integration may follow after CPU job cost and reliability are measured.

## Acceptance Criteria

- Ordinary discovery neither imports optional NLP packages nor initializes
  models, including on a developer machine with NLP extras already installed.
- All four real-model checks execute through `scripts/smoke` with provisioned
  models, on CPU without requiring an external shell GPU workaround. Existing
  assertions remain covered across the ordinary and smoke suites.
- Smoke checks fail clearly for missing prerequisites, zero selection, child
  crashes, failed assertions, and timeouts. A failing child does not prevent
  subsequent checks; the command still exits nonzero.
- Model installation is explicit and separate; smoke execution is offline.
- Production device-selection behavior is unchanged and verified.
- Canonical checks and smoke results are recorded; unrelated baseline failures
  are presented for review without claiming a green suite.
- Documentation and a test relocation map are included; PR #548 is untouched.
- The CPU workflow has only manual and weekly triggers, explicit versioned
  setup, safe caches, bounded execution, and retained diagnostics. A real
  GitHub Actions run demonstrates all four checks executing successfully.
  Missing-prerequisite and failed-child paths remain non-successful and retain
  useful diagnostics. Record cold/warm-cache evidence and measured runtime.

## Validation

Run from `lcats/` using the project environment. Do not uninstall a contributor's
models to test absence; use isolated fixtures/environments. Setup may provision
dependencies explicitly, but test execution must not fetch model data.

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test tests/analysis_tests/event_role_world_harness_test.py`
- `scripts/test tests/analysis_tests/event_role_world_test.py`
- `scripts/test tests/analysis_tests/linguistics_test.py`
- `scripts/test`
- `scripts/smoke`
- `actionlint ../.github/workflows/smoke.yml` (install the workflow validator explicitly if unavailable)
- `lrh validate`

Verify ordinary tests with and without NLP extras, and smoke execution with
provisioned and deliberately unavailable prerequisites. Record executed counts,
exit status, model/package versions, and exact commands. Test CPU enforcement
at the process boundary and require a confirmation run on Kenny's affected
machine without the shell workaround; report pending external confirmation
honestly rather than substituting local CPU evidence for GPU-host evidence.

Run the new workflow from the implementation ref via `workflow_dispatch` and
record the run URL, tested SHA, four executed checks, versions, artifacts, and
cold/warm-cache timings. GitHub may require the workflow file on the default
branch before dispatch is available. If so, document that platform constraint
and obtain a reviewed first-run/merge verification plan; do not add triggers or
claim execution merely to bypass it. A weekly schedule on its own does not
establish a successful run. Exercise diagnostic publication on a controlled
failure without committing an intentionally broken production test.

## Risk Notes

- CPU configuration must precede native imports in the actual smoke child;
  changing only a preliminary availability probe is insufficient.
- Smoke workers must not import the original unit modules as a shortcut if
  doing so would recreate import-time initialization or duplicate execution.
- Separating suites changes ordinary coverage percentages and test counts;
  report the split and do not lower coverage thresholds to conceal regressions.
- Bound timeouts for slower model startup without converting timeouts to skips.
- Weekly validation detects drift after it occurs; it does not replace the
  required recorded smoke evidence before merging NLP changes.
- Model/dependency caches can conceal incomplete setup or incompatible models;
  include version identities in keys and verify both cold and warm execution.
- Job-level termination can prevent artifact upload; leave diagnostic time
  within the job budget and state that hard cancellation may lose artifacts.

## Planning State

The user approved the revised smoke-test approach, then the bounded CPU smoke
CI workflow, on 2026-11-12 and authorized opening the planning PR for review.
Creating or merging this planning artifact does not implement or resolve the
work item. Implementation remains a separate PR against main.
