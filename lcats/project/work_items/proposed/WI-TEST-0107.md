---
resolution: null
blocked_reason: null
blocked: false
id: WI-TEST-0107
title: Survey and suppress extraneous LCATS test output
type: deliverable
status: proposed
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams: []
related_design: []
depends_on: []
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - suppress_output_globally
  - modify_scripts_test_for_global_suppression
  - weaken_test_assertions
acceptance:
  - A baseline survey identifies the unwanted output produced by scripts/test and traces each in-scope source to specific test code.
  - In-scope noisy tests suppress Python-level output at their individual call sites using lcats.utils.capture, while tests that assert output continue using capture_output; child-process output is handled with subprocess/file-descriptor capture where supported or explicitly classified as out of scope.
  - scripts/test retains its normal dot/F/E reporting and does not receive a global output-suppression mechanism.
  - The full test suite, formatting, linting, and lrh validation pass after the changes.
required_evidence:
  - manual_review
  - test_output
  - validation_output
  - lrh_validate
artifacts_expected:
  - lcats/tests/
---

# Work Item: WI-TEST-0107

## Summary

Survey the output emitted by `scripts/test`, distinguish useful test-runner and
failure diagnostics from unwanted test-body printing, and suppress the unwanted
output at the individual test call sites. Use LCATS's existing capture utilities
so normal debugging remains available and tests that intentionally inspect output
retain that behavior.

## Problem / Context

`STYLE.md` requires tests to use the `capture` library to suppress print output
([`STYLE.md:28-32`](../../../STYLE.md#L28-L32) and
[`STYLE.md:218-223`](../../../STYLE.md#L218-L223)). `tests/AGENTS.md` likewise says
not to add or expand test debug output ([`tests/AGENTS.md:35-37`](../../../tests/AGENTS.md#L35-L37)).
LCATS already provides `capture_output()` and `suppress_output()` for this purpose
([`src/lcats/utils/capture.py:20-56`](../../../src/lcats/utils/capture.py#L20-L56)).

A baseline `scripts/test` run on 2026-09-23 completed successfully with 2,264
tests, but emitted dependency logs, JSON records, progress bars, processing
messages, warnings, expected error diagnostics, and model-validation progress.
`scripts/test` itself also emits a header and shell tracing through `echo` and
`set -x` ([`scripts/test:4-8`](../../../scripts/test#L4-L8)). The work item should
first classify these sources, then address unwanted test-body output without
globally suppressing output or hiding genuine failures.

### Duplication search

- In-repo: Existing capture utilities and many compliant test examples exist; no existing work item was found for this cleanup.
- Sibling repos: None identified.
- External libraries: No external library needed; LCATS already provides the required capture helpers.
- Recommendation: Proceed using the existing LCATS capture library.

### Demand search

- Work items: No matching proposed work item found.
- Proposals: No matching proposal found.
- Backlog: No matching entry found.
- Recommendation: No action.

## Scope

- Run and record a representative baseline of `scripts/test` output.
- Classify output as runner-generated, test-generated, dependency-generated, intentional assertion output, or failure/error diagnostics.
- Find the test call sites responsible for unwanted output.
- Suppress Python-level output locally with `capture.suppress_output()` or capture it with `capture.capture_output()` when assertions require inspection. For child processes, use subprocess/file-descriptor capture where supported; otherwise record the source as out of scope rather than implying that Python stream redirection captures it.
- Verify that normal test progress and failure/error signals remain visible.

## Required Changes

1. Survey `scripts/test` output and document the categories of unwanted output.
2. Trace each in-scope output source to the responsible test file and call site.
3. Update individual tests to use the existing capture utilities.
4. Preserve tests whose purpose is to assert stdout or stderr.
5. For output produced by child processes, apply subprocess/file-descriptor capture when the test and available helpers support it, or document the source as out of scope with the reason.
6. Avoid modifying `scripts/test` to suppress output globally.
7. Run the full validation sequence and record the before/after output behavior.

## Non-Goals

- Do not globally redirect or suppress stdout/stderr in `scripts/test`.
- Do not remove useful failure, error, warning, or assertion diagnostics.
- Do not weaken test assertions merely to make output quieter.
- Do not claim that Python-level stream redirection suppresses output emitted by child processes; those sources require subprocess/file-descriptor handling or an explicit out-of-scope decision.
- Do not change production behavior unrelated to test output.
- Do not add a new output-capture dependency.

## Acceptance Criteria

- A baseline inventory identifies the unwanted output and its source locations.
- Every confirmed noisy test call site is handled with the existing LCATS capture utilities.
- Child-process output is either suppressed with an appropriate subprocess/file-descriptor mechanism or explicitly listed as out of scope with its source and rationale.
- Tests that intentionally inspect output still assert against captured content.
- `scripts/test` still reports normal test progress and exposes failures/errors.
- No global suppression mechanism is added to `scripts/test`.
- Formatting, linting, tests, and `lrh validate` pass.

## Validation

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes

- Some output may originate in third-party libraries rather than test code; those cases must be distinguished before changing tests.
- `capture.suppress_output()` and `capture.capture_output()` redirect Python streams only; subprocess output may require a different mechanism and must not be silently treated as handled.
- Broad suppression could hide useful diagnostics, so each context manager should be scoped narrowly.
- The baseline may reveal that some noise comes from `scripts/test` itself; that should be documented separately from the requested per-test cleanup.
