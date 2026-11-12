# NLP test-isolation implementation evidence

Work item: [WI-NLP-TEST-ISOLATION](../work_items/proposed/WI-NLP-TEST-ISOLATION.md).
Planning PR: [#551](https://github.com/xenotaur/LCATS/pull/551).
Implementation base: `34ddb3b0a35edd10b9d0c7b74d0c554e045b9c76`.
Recorded: 2026-11-12. This document is non-executable evidence; runners live in
`tests/smoke/`, ordinary regressions in `tests/analysis_tests/`.

## Original supplied diagnostic evidence

These are Kenny's results, not a reproduction of his GPU failure on another
machine. The user supplied both archives; the following archive/member
identities preserve provenance without committing personal paths or raw logs.

| Archive | SHA-256 |
|---|---|
| `diagOutput.zip` | `0dad65dd1550070ed28e05f55e4bbd47ef939ebf33813881e061c6ebb66773ae` |
| `diagOutput-after.zip` | `9b1f77aa1996717bfc5f76b6e9cd245acddf7aa8cd474f7183d35abac241d8d9` |

Each member prefix below contains `report.json`, `console.log`, and `faults.log`.

| Archive | Member prefix | Mode and outcome |
|---|---|---|
| Before | `tmp/lcats-nlp-diagnostics-ripug2fq/` | spaCy, exit 0 |
| Before | `tmp/lcats-nlp-diagnostics-q0nfm1cn/` | Stanza, SIGABRT / return code -6 |
| Before | `tmp/lcats-nlp-diagnostics-1hue43hr/` | module import, SIGABRT / -6 |
| Before | `tmp/lcats-nlp-diagnostics-1kec6vlo/` | module execution, SIGABRT / -6 |
| After | `tmp/lcats-nlp-diagnostics-j_zj39ej/` | Stanza on CPU, exit 0 |
| After | `tmp/lcats-nlp-diagnostics-n26h0x8e/` | module on CPU, 123 tests, exit 0 |

Before/after package versions match: Python 3.11.0, spaCy 3.8.15, Stanza 1.14.0,
PyTorch 2.11.0, and `en_core_web_sm` 3.8.0 on Linux x86_64. The original native
error was `Invalid handle. Cannot load symbol cudnnGetVersion`; the supplied
CPU workaround was `CUDA_VISIBLE_DEVICES=-1`. It demonstrates CPU viability,
not repaired CUDA support or a pre-existing full-suite pass.

## Assertion relocation and production boundary

The two `TestRealNLPBackends` methods move from `event_role_world_test.py` to
`tests/smoke/nlp_smoke.py`; 121 ordinary methods remain. The two
`LinguisticsOptionalNLPTest` methods move from `linguistics_test.py`; 64 ordinary
methods remain. Original token, verb, single-root, sidecar-validity and exact
repaired-tokenization assertions are retained. Native output suppression and
availability skips are removed from those four explicit checks.

`DiscoveryIsolationTest` imports the full ordinary suite in a fresh process
with an import guard that raises `BaseException` on optional NLP imports; old
`except Exception` probes cannot hide a violation. Harness tests also exercise
real child processes for environment isolation, assertion failures, skipped or
zero executed checks, missing receipts, missing prerequisites, signals,
timeouts, continuation, and network rejection. A controlled abort inside FD
suppression verifies the separate `fault.log` captures the native traceback.

There are no production source changes. CPU controls are child-local and the
actual Stanza pipeline device is asserted. No changes were made to Kenny's PR
#548, contributor GPU environments, or production dependency defaults.

## Local qualification

Commands ran from `lcats/` on macOS arm64 / Python 3.11.9. A dedicated venv
inherited the existing LCATS environment's native packages for the with-extras
run; a second clean venv installed only `.[dev]` and was explicitly checked to
contain no spaCy, Stanza, PyTorch, or spaCy model before the no-extras run.
Editable LCATS installation in both environments points at this checkout.

| Check | Evidence |
|---|---|
| Black 25.11.0 / Ruff 0.15.0 | `scripts/format --check --diff` and `scripts/lint` passed |
| Targeted harness | 14 tests passed, including native-abort diagnostics |
| Original event-role-world module | 121 tests passed |
| Ordinary linguistics module | 64 tests passed |
| Full suite with NLP extras | 3,161 tests passed in 110.754 seconds |
| Full suite without NLP extras | 3,161 tests passed in 96.844 seconds |
| Workflow syntax | actionlint 1.7.12 passed |
| Control plane | `lrh validate`: 0 errors, 362 pre-existing warnings |
| Production behavior | `git diff origin/main -- lcats/src` empty |

The first sandboxed no-extras run had 99 `PermissionError` exceptions from
localhost HTTP test servers, not NLP failures. Black's multiprocessing manager
also could not bind a local socket under the sandbox. These commands were
rerun with approved execution permissions; no assertions were suppressed.
`scripts/version tools` emitted no useful version listing, so versions above
were also read directly from installed package metadata. Output was captured
externally because LCATS's `scripts/test` does not implement LRH's `--log` flag.

### Real smoke checks and cache evidence

Pinned versions: spaCy 3.8.14, Stanza 1.14.0, PyTorch 2.7.1,
`en_core_web_sm` 3.8.0. The Stanza resource commit, SHA-256, and all eight model
identities are recorded in `tests/smoke/models.json`.

- Fresh setup with empty Stanza **and Hugging Face** cache directories completed
  in 43.53 seconds, and verified all eight model checksums. Earlier setup from
  an empty Stanza directory alone reused the existing Hugging Face cache and
  is not counted as a network-cold run.
- All four real checks passed after fresh setup in 18.01 seconds. Individual
  child times were 3.339, 2.663, 3.079, and 8.200 seconds.
- Warm offline prerequisite validation passed in 1.52 seconds. An earlier
  warm inference run also passed all four checks (3.034, 2.903, 2.842, and 6.741
  seconds per child). No model provisioning occurs in these checks.
- A deliberate missing Stanza directory produced three spaCy passes, one
  Stanza failure, and aggregate exit 1. Its stderr retained the missing-file
  traceback; no successful Stanza receipt was fabricated.
- Fresh provisioning caught a mismatch between the contributor's existing
  resource index and the pinned upstream revision. Selected model hashes were
  unchanged. The final manifest pins the verified upstream bytes, and the
  original contributor cache was preserved.

## Outstanding acceptance evidence and first-run decision

No new GitHub smoke execution is claimed here. GitHub's documented manual
dispatch requirement is that the workflow first exist on the default branch:
[manual workflow documentation](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).
The implementation uses only approved manual and weekly triggers.

The live first-dispatch attempt after opening implementation
[PR #552](https://github.com/xenotaur/LCATS/pull/552) was:

```bash
gh workflow run smoke.yml --repo xenotaur/LCATS --ref xenotaur/feat/wi-nlp-test-isolation
```

GitHub refused with `HTTP 404: workflow smoke.yml not found on the default
branch`. No smoke run was created; this is a platform prerequisite, not a
failed smoke test or evidence that the Ubuntu job works.

Before resolving this work item, obtain:

1. A reviewed first-run/merge verification plan if branch dispatch is unavailable.
2. A real Ubuntu CPU workflow success with all four checks, tested SHA and run
   URL, cold/warm-cache timings, and artifact verification on controlled failure.
3. Kenny's affected-host confirmation without the external CUDA workaround.

Recommended first-run plan: review and merge the implementation while keeping
the WI open, dispatch immediately, verify the cold and warm runs and diagnostic
artifact path, then resolve only after acceptance evidence is complete. A
failed smoke job becomes follow-up repair work, not a silent green closeout.
This is a recommendation for human review, not authorization to merge.
