# Knight/Suvin (Novum) Contract Canary Runbook

This runbook describes the experiment-local canary governed by `WI-SF-0015`.
It is a run procedure, not a paid-run approval and not a claim of theoretical
accuracy.

## Purpose

Verify that the hardened Knight and Suvin model boundaries:

- preserve seven independent Knight criteria;
- preserve Suvin novelty, cognitive validation, and narrative hegemony separately;
- canonicalize harmless provider-specific shapes without inventing evidence;
- quarantine unsafe output;
- persist raw, normalized, repaired, checkpoint, sidecar, and log artifacts;
- remain stable across repeated two-story trials.

## Cases

| Role | Story ID | Expected behavior |
| --- | --- | --- |
| Positive | `mass_quantities/a_case_of_sunburn__fontenay` | At least one present Knight criterion and one qualified N/C/H candidate |
| Negative/adjacent | `anderson/bell` | No qualified novum; do not require an exact Knight interval |

These expectations are operational canary assertions, not gold labels or a
theoretical validation set.

## Required sequence

1. Run the deterministic unit and structural test suite.
2. Create the reviewed `contract_canary_manifest.json` with story hashes and
   the selected backend/configuration.
3. Run three local-model semantic trials first. Keep `max_failures=3`. Fixture mode may be used for structural contract tests, but it does not count as a semantic canary unless its outputs are explicitly contrastive and case-specific.
4. Inspect every trial's raw output, canonical output, normalization findings,
   quarantine records, checkpoints, sidecars, and JSONL logs.
5. Stop and replan if any output silently invents evidence, silently drops an
   invalid reference, or reports a complete analysis without seven Knight
   criteria and valid derived fields.
6. If local trials are structurally healthy, prepare a paid approval package.
7. After explicit approval, run no more than two Opus trials and no more than
   five total two-story trials.
8. Write `contract_canary_report.md` and decide proceed, revise, or stop.

## Fixture restriction

The existing deterministic spike fixture emits positive Knight and N/C/H
decisions for every story. It is therefore suitable for exercising persistence,
validation, and quarantine paths, but not for evaluating the positive/negative
semantic expectations in this runbook. A fixture-backed semantic trial must
provide case-specific contrastive outputs and document that mapping in the
manifest; otherwise use the local model backend.

## Per-trial output layout

```text
results/worldcon_spike/contract_canary/
  local/<trial-id>/
  opus/<trial-id>/
```

Each trial must retain the manifest copy, raw stage responses, normalized
records, repair/coercion findings, quarantine files, run log, checkpoints,
validated sidecars, summary, and report. Outputs remain outside `data/`,
`corpora/`, and production promotion paths.

## Stop conditions

- Any output root escapes the experiment directory.
- A story hash or effective-input fingerprint is stale or mismatched.
- A malformed result is accepted without a recorded coercion or repair.
- A present judgment lacks valid supporting evidence.
- A content-filter or deterministic validation failure is automatically retried.
- The approved paid budget, trial count, or story count would be exceeded.
- Provider-wide or infrastructure failures make the trial uninterpretable.

## Report requirements

The final report must distinguish:

- structural contract success;
- semantic canary expectation results;
- partial success and quarantined stages;
- coercions and repairs;
- input/output token usage and latency;
- estimated and actual paid cost;
- repeatability across trials;
- recommendation for the 10-story sample.

The canary must not be described as Phase 2 validation, human agreement, or
evidence of theoretical accuracy.
