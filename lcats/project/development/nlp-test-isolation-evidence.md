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

## First-run decision and implementation closeout

At pre-merge review, no GitHub smoke execution was claimed. GitHub's documented manual
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

The user explicitly approved merging #552, limited execution-record closeout,
a one-closeout archive-sync exception, and cold/warm plus controlled-failure
first-run validation on 2026-11-12. PR #552 merged at
`6069a44d5b7c4c980e66fefb6a6895f21b8a3475`; the five linked execution records
were landed in main commit `69857d3ab2449effe6293e8c6fb48f8957f15474`.
The Codex session pointers were retained; no Claude archive sync was performed.
No persistent gate policy or fingerprint baseline changed.

The WI remains **proposed** pending Kenny's affected-host confirmation, even
if Ubuntu validation succeeds. The controlled failure is an explicitly
approved negative test on an isolated, unmerged branch, not an unexpected
normal-CI failure or a change to main's tests.

## Ubuntu first-run validation results

All three runs completed on 2026-11-12, Ubuntu 24.04 / Python 3.11.18.
[Retained machine-readable evidence](nlp-test-isolation-ci-evidence.json)
contains tested SHAs, job/step times, artifact identities/digests, all per-check
summaries/receipts, and the deliberate missing-model traceback. It is
non-executable data derived from GitHub and the downloaded artifacts.

| Run | Outcome | Job elapsed | Package setup | Model verify/provision | Harness + inference step | Sum of inference child times |
|---|---|---:|---:|---:|---:|---:|
| [Cold #43303671493](https://github.com/xenotaur/LCATS/actions/runs/43303671493) | Success; 4/4 smoke, 14 harness | 128 s | 66 s | 16 s | 24 s | 13.945 s |
| [Warm #43304185363](https://github.com/xenotaur/LCATS/actions/runs/43304185363) | Success; 4/4 smoke, 14 harness | 87 s | 46 s | 2 s | 18 s | 11.484 s |
| [Expected failure #43304213609](https://github.com/xenotaur/LCATS/actions/runs/43304213609) | Expected failure; 3 spaCy passes, Stanza prerequisite failure, 14 harness | 87 s | 53 s | 3 s | 14 s | 8.074 s |

Job and step times are GitHub timestamps rounded to seconds and exclude queue
wait. Child times come from the runner summaries. These are single measurements,
not a benchmark or reliability estimate. All runs were well within the
20-minute job budget.

The cold and warm runs tested main SHA
`69857d3ab2449effe6293e8c6fb48f8957f15474`. The cold log explicitly reports
no matching model cache and contains a provisioning log; the warm log reports
`Model cache hit: true`, verifies the cached files, and has no provisioning
log. Both produced four one-test, zero-skip success receipts. All three runs
used `torch==2.7.1+cpu`; the successful Stanza receipts record the pinned
resource SHA-256. Effective spaCy/Stanza/model versions match the local pins.

The negative run tested only validation commit
`759bff8a95335b41fc9d0027e009bd5dbc3411f2` on
`codex/nlp-smoke-failure-evidence`. This branch **must not be merged**. Its only
change supplies an absent `STANZA_RESOURCES_DIR` to the inference command;
setup still verifies the real cached models, and no existing data is removed.
The inference step exits nonzero, while the always-run artifact step succeeds.
The downloaded artifact contains the parent summary and Stanza stderr:

```text
FileNotFoundError: [Errno 2] No such file or directory: '/home/runner/work/_temp/lcats-expected-missing-models/resources.json'
```

There is no successful Stanza receipt. All three spaCy checks still have
one-test, zero-skip success receipts. This establishes failure propagation and
artifact retention for missing prerequisites. Native-abort diagnostics and
continuation are separately covered by the 14 harness tests, not inferred
from this missing-model run.

All three artifacts were downloaded and inspected, including setup/harness
logs and inference summaries. GitHub artifacts have a 14-day retention period;
the adjacent JSON preserves the acceptance evidence beyond that period.
The full downloaded logs also remain locally under
`/tmp/lcats-nlp-ci-evidence/{cold,warm,failure}/`, but those temporary paths are
not the durable source of record.

## Remaining external confirmation

The implementation and first-run CI evidence are complete. **Do not resolve
WI-NLP-TEST-ISOLATION yet.** Kenny must confirm ordinary tests and explicit CPU
smoke execution on his affected machine without the external CUDA-hiding
shell workaround. Use the dedicated smoke environment and setup documented in
[Run ordinary tests and CPU NLP smoke checks](../../docs/how-to/run-nlp-tests.md).
Send back the tested commit, commands, exit statuses, package/model versions,
and smoke run directory with `summary.json` and child logs. If ordinary tests
fail, include their complete output. This confirms isolation on the affected
host; it does not diagnose or certify repair of Kenny's GPU installation.

No changes to Kenny's PR #548, production GPU defaults, or persistent gate
policy were made. The WI remains in `proposed/`; its acceptance criteria have
not been weakened. No additional memory was written: the durable process
finding (default-branch prerequisite for first manual dispatch) and the
archive-sync exception are already recorded here and in the closeout note.
