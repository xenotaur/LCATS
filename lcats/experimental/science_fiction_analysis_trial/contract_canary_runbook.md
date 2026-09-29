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
5. For a resumable run, pass `--resume`. The runner reuses a stage only when
   the story input, prompt, schema, backend/model, generation settings, and
   effective payload fingerprint match a successful checkpoint; failed or stale
   checkpoints are recomputed.
6. Apply the bounded retry policy: retry truncation once with doubled
   `max_tokens`, retry transient provider/network failures once, never retry
   content-filter failures, and never blindly retry deterministic validation
   failures. Every attempt and its reported usage must remain on disk.
7. Stop and replan if any output silently invents evidence, silently drops an
   invalid reference, or reports a complete analysis without seven Knight
   criteria and valid derived fields.
8. If local trials are structurally healthy, have the agent resolve the paid
   stage fields from the user's explicit authorization and persist the
   resulting `approval_snapshot.json` before any paid call. For sample/full
   stages, provide prior cumulative spend explicitly; the runner verifies the
   pinned source manifest and records prompt/schema fingerprints and all stop
   restrictions in the snapshot.
9. After explicit approval, run no more than two Opus trials and no more than
   five total two-story trials.
10. Write `contract_canary_report.md` and decide proceed, revise, or stop.

The runner invocation for a local trial is:

```bash
OPENAI_API_KEY=ollama PYTHONPATH=src python \
  experimental/science_fiction_analysis_trial/run_worldcon_spike.py \
  --manifest experimental/science_fiction_analysis_trial/manifests/contract_canary_manifest.json \
  --mode canary --backend openai-compatible \
  --base-url http://localhost:11434/v1 --model gpt-oss:20b \
  --output-root experimental/science_fiction_analysis_trial/results/worldcon_spike/contract_canary/local/trial-1 \
  --max-failures 3
```

Change the trial output directory for each repeated attempt. The manifest's
canary gate caps every invocation at two stories; it does not authorize paid
calls.

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
- A retry occurs without a persisted attempt artifact and usage record.
- The approved paid budget, trial count, or story count would be exceeded.
- Provider-wide or infrastructure failures make the trial uninterpretable.
- The runner's persisted stage decision is operational guidance only; it is
  not evidence of theoretical accuracy, human agreement, or production
  readiness.

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
