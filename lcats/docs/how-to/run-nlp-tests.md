# Run ordinary tests and CPU NLP smoke checks

Run commands from `LCATS/lcats/` in a project environment. Ordinary tests use
deterministic fakes and never import spaCy, Stanza, PyTorch, or their models
during discovery, even if NLP extras are installed:

```bash
scripts/test
```

Unit success does not certify real NLP integrations or GPU support. Run and
record the smoke checks before merging changes to NLP backends or these checks.
The smoke suite preserves four existing assertions in `tests/smoke/nlp_smoke.py`:

| Previous location | Smoke check |
|---|---|
| `event_role_world_test.TestRealNLPBackends` | spaCy normalized tokens, verb and single-root assertions |
| `event_role_world_test.TestRealNLPBackends` | Stanza normalized tokens, verb and single-root assertions |
| `linguistics_test.LinguisticsOptionalNLPTest` | spaCy linguistic sidecar validation |
| `linguistics_test.LinguisticsOptionalNLPTest` | repaired-tokenization expected token sequence |

The original event-role-world suite retains 121 ordinary test methods. The two
moved tests and the two linguistics checks run only in the explicit smoke suite.
Harness regressions are ordinary tests and need no NLP dependencies. No existing
assertions were weakened, and no production GPU defaults changed.

## Provision a dedicated smoke environment

Provisioning requires network access. Use a separate environment so the pinned
smoke versions do not upgrade or downgrade your contributor environment:

```bash
python3.11 -m venv /tmp/lcats-nlp-smoke
source /tmp/lcats-nlp-smoke/bin/activate
```

On Linux, install the CPU-only PyTorch wheel first:

```bash
python -m pip install 'torch==2.7.1' --index-url https://download.pytorch.org/whl/cpu
```

On macOS, omit that Linux-specific command; the requirements file installs the
platform wheel. Then provision packages and the Stanza models explicitly:

```bash
python -m pip install -e '.[test]' -r tests/smoke/requirements.txt
export STANZA_RESOURCES_DIR="$PWD/.cache/nlp-smoke/stanza"
python -m tests.smoke.provision
scripts/smoke --check
```

`requirements.txt` pins smoke package/model versions. `models.json` pins the
Stanza resource release to an upstream commit, its SHA-256 digest, and the
selected processor/dependency model checksums. Setup fetches only those
processors and their dependencies, not the entire Stanza English bundle.
Model downloads may be hundreds of megabytes; reuse this dedicated directory.
The checks validate cache contents, not just directory existence.

`--check` verifies versions and resource files in bounded children. It does
not load pipelines or certify inference. Missing or mismatched prerequisites
are failures, not successful skips. Change the pins and expected checksums
together when intentionally updating the smoke environment, and record a new
real smoke run. These pins do not alter production dependency defaults.

## Run the four checks

```bash
scripts/smoke --dry-run
scripts/smoke
scripts/smoke --backend stanza --timeout 120
scripts/smoke --help
```

Each test runs in a fresh interpreter. The parent passes `CUDA_VISIBLE_DEVICES=-1`
before native imports; spaCy explicitly selects CPU, and the Stanza check
asserts the actual pipeline device is CPU. These settings are child-local.
The smoke worker rejects Python socket connection/DNS attempts and sets the
Hugging Face offline flags; production Stanza already uses `download_method=None`.
This prevents incidental model fetching in these checks, but is not a security
sandbox for arbitrary native code. Model setup is a separate command.

The default timeout is 120 seconds per test. Failures, native signals, missing
prerequisites, zero selected/executed tests, skipped tests, and timeouts all
produce nonzero status. Remaining checks continue after an individual failure.
POSIX timeout handling terminates the child process group; Windows terminates
the worker itself (these checks do not launch external worker processes).

## Find diagnostics

The final output prints an absolute run-directory path. By default it is under
`tmp/logs/smoke/run-*/`. Use `--log-dir /absolute/path` to choose the parent.
Each child directory contains:

- `stdout.log` and `stderr.log`, including native errors without suppression;
- `fault.log`, a separate faulthandler descriptor that survives stdout/stderr
  suppression (only created once the worker has started);
- `receipt.json` after a completed worker, including executed count and versions.

The parent writes `summary.json` after each child with test identity, backend,
exit/signal/timeout, duration, success and log paths. Exit zero alone is
insufficient: a completed, unskipped single-test receipt is required. A crash
or kill can leave no receipt; logs and the parent summary still diagnose it.
Hard process/job cancellation can prevent the last summary or artifact upload.

To send a diagnostic run back, use the exact path printed by the command:

```bash
tar -czf smoke-diagnostics.tar.gz -C /absolute/path/to/run-directory .
```

Kenny's confirmation should use `scripts/test` and `scripts/smoke` without an
external CUDA-hiding shell workaround. Include the tested commit, command,
versions, and run directory. CPU smoke success does not establish GPU repair.

## Run and inspect CPU smoke CI

`.github/workflows/smoke.yml` runs on Ubuntu 24.04 / Python 3.11 manually and
weekly (Tuesday 08:23 UTC). It has a 20-minute job limit, shorter setup/test
limits, CPU-only PyTorch, version-keyed package/model caches, and a diagnostic
artifact retained for 14 days. It has no automatic PR, tag, or release trigger.

```bash
gh workflow run smoke.yml --ref YOUR_BRANCH
gh run list --workflow smoke.yml --limit 5
gh run view RUN_ID
gh run download RUN_ID --name cpu-nlp-smoke-RUN_ID-ATTEMPT
```

GitHub requires the workflow to exist on the default branch before manual
dispatch is available. For the first implementation PR, document this constraint
and agree on the first-run/merge verification plan; do not claim an unexecuted
workflow passed or add temporary triggers to bypass review. Once available,
record the run URL, tested SHA, all four executed checks, package/model versions,
cold/warm-cache timings, and artifact diagnostics from a controlled failure.
The weekly schedule detects later drift and is not a publication gate.

See the primary documentation for [Stanza device selection](https://stanfordnlp.github.io/stanza/pipeline.html),
[spaCy CPU selection](https://spacy.io/api/top-level#require_cpu), and
[GitHub manual dispatch](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).
