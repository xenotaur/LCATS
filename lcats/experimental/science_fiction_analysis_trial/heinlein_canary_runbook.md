# Heinlein Live Canary Runbook

This runbook describes the experiment-local, no-cost live canary of the
optional `sf_heinlein` stage, governed by `WI-SF-0111`. It is a run procedure,
not a paid-run approval, not a claim of theoretical accuracy, and not
Phase 2 validation. The Knight/Suvin canary runbook
(`contract_canary_runbook.md`) is a separate procedure and is not changed by
this one.

## Purpose

Verify, against a real local model and with every artifact persisted, that the
Heinlein stage:

- returns exactly the five criteria (different, essential, human, causal,
  plausible) with valid evidence for every `present` decision;
- has Python derive the verdict and interval, with dependency-rule violations
  quarantined and never repaired;
- never alters Knight or Suvin results, and degrades to a recorded partial
  success when it fails;
- renders correctly, including as `Unavailable` with a warning after a failure.

## Cases and expectations

The manifest `manifests/heinlein_canary_manifest.json` holds exactly two canary
stories. Each carries an operational expectation, loaded by the runner as data,
included in the manifest fingerprint, and copied into every trial's output root
as `manifest_snapshot.json`, so a trial shows which expectations were evaluated.
These are operational checks written before any trial. They are not gold labels
and not evidence of theoretical accuracy.

| Role | Story ID | Operational expectation |
| --- | --- | --- |
| Expected positive | `mass_quantities/2_b_r_0_2_b__vonnegut` | Verdict is `qualifies` or `indeterminate`; none of `different`, `essential`, `human`, `causal` is `absent` |
| Negative control | `anderson/bell` | Verdict is `does_not_qualify` or `indeterminate`, never `qualifies` |

Rationale for each case is recorded in the manifest. `qualifies` is allowed but
not demanded for the positive case because a single local-model run varies.
The control is the same story used as the negative control in the Knight/Suvin
canary, which keeps the two canaries comparable. If either expectation is
changed, the manifest fingerprint changes and a resumed run is refused.

## Preconditions

1. A local Ollama server started with `ollama serve`, reached through a
   **loopback** URL such as `http://localhost:11434/v1`. The runner treats an
   `openai-compatible` endpoint as no-cost only when its host is loopback
   (`localhost` or a loopback IP address). Any other host takes the paid path,
   and `--include-heinlein` is then rejected.
2. Model: `gpt-oss:20b` by default. It is the most vetted local candidate in the
   repository and matches the earlier Knight/Suvin trial. `qwen3:30b-a3b` may be
   run as a separate, clearly labeled candidate. One canary uses one model.
3. Record, before the first trial: the model digest (`ollama list`) and the
   context length the server reports (`ollama ps` once the model is loaded).
   The repository docs do not state a context length, and a small default would
   silently truncate long inputs.
4. Canonical corpora available in the checkout, and the pinned black, ruff and
   test tooling used by CI.
5. Use `--max-tokens 8192` in every local command. At the default 4096-token
   cap the evidence stage has been observed to truncate on its first attempt and
   succeed only on the runner's doubled-limit retry.

## Required sequence

1. Run the deterministic test suite (`scripts/test`).
2. Run the fake-backend smoke with the flag. It must process both smoke stories
   and publish a Heinlein verdict for each; zero stories processed is a failure.
3. Run a **flag-off local baseline** on the two canary stories. It doubles as the
   evidence-stage precondition: an evidence-stage failure here is recorded as an
   infrastructure result, not a Heinlein result.
4. Run **three local trials** with the flag on, each in a new output root, with
   `--max-failures 3`. A single trial is not decision-grade.
5. Inspect every trial using the checklist below before starting the next.
6. For an interrupted trial, pass `--resume` with the same output root. A stage
   is reused only when its story, prompt, schema, backend/model, generation
   settings and payload fingerprint match a successful checkpoint, and a changed
   manifest is refused.
7. Apply the bounded retry policy: truncation is retried once with doubled
   `max_tokens`, transient provider or network failures once, content-filter
   failures never, and deterministic validation failures never. Every attempt and
   its usage must remain on disk.
8. Write `heinlein_canary_report.md` and decide proceed, revise, or stop.

## Commands

Fake-backend smoke (no model):

```bash
PYTHONPATH=src python experimental/science_fiction_analysis_trial/run_worldcon_spike.py --manifest experimental/science_fiction_analysis_trial/manifests/heinlein_canary_manifest.json --mode smoke --backend fake --include-heinlein --output-root /tmp/lcats-heinlein-canary-smoke
```

Flag-off local baseline:

```bash
OPENAI_API_KEY=ollama PYTHONPATH=src python experimental/science_fiction_analysis_trial/run_worldcon_spike.py --manifest experimental/science_fiction_analysis_trial/manifests/heinlein_canary_manifest.json --mode canary --backend openai-compatible --base-url http://localhost:11434/v1 --model gpt-oss:20b --max-tokens 8192 --max-failures 3 --output-root experimental/science_fiction_analysis_trial/results/worldcon_spike/heinlein_canary/local/baseline
```

Local trial with the flag (change `trial-1` for each attempt):

```bash
OPENAI_API_KEY=ollama PYTHONPATH=src python experimental/science_fiction_analysis_trial/run_worldcon_spike.py --manifest experimental/science_fiction_analysis_trial/manifests/heinlein_canary_manifest.json --mode canary --backend openai-compatible --base-url http://localhost:11434/v1 --model gpt-oss:20b --include-heinlein --max-tokens 8192 --max-failures 3 --output-root experimental/science_fiction_analysis_trial/results/worldcon_spike/heinlein_canary/local/trial-1
```

The canary gate caps every invocation at two stories and authorizes no paid
calls.

## Inspection checklist

For every trial, read and record:

- the raw `sf_heinlein` response and every persisted attempt, and any
  quarantine record, under `_raw/` and `_quarantine/`;
- `analyses.heinlein` in each sidecar: all five criteria present, the verdict
  and interval, and each rationale against its cited evidence;
- that no `present` decision lacks valid supporting evidence, and that none was
  filled in by the runner;
- dependency-rule violations (`essential` or `causal` present while a
  prerequisite is absent): each must be quarantined, and their frequency is a
  prompt-quality signal worth noting;
- that Knight and Suvin results are consistent with the flag-off baseline,
  allowing for ordinary model variation;
- `manifest_snapshot.json` is present and identical to the manifest used;
- the detailed rendering and comparison table of the trial's sidecars, with a
  failed story showing `Unavailable` and a warning, never a verdict.

## Resource note

Observed on one flag-off story with `gpt-oss:20b`: about 8 minutes per story,
so about 16 minutes for a two-story trial. The Heinlein stage is expected to add
roughly 15 percent, so plan on 18 to 20 minutes per trial and about 80 minutes
for the baseline plus three trials. These figures come from a single uncommitted
probe and are planning estimates, not measurements.

## Per-trial output layout

```text
results/worldcon_spike/heinlein_canary/
  local/baseline/
  local/trial-1/ trial-2/ trial-3/
```

Each trial retains the manifest snapshot, raw stage responses, normalized
records, quarantine files, run log, checkpoints, validated sidecars, summary,
and report. Outputs stay outside `data/`, `corpora/`, and production promotion
paths.

## Stop conditions

- The corpora are unavailable, or the server is not reachable through a loopback
  URL.
- Any story fails structural sidecar assembly, or any output escapes the
  experiment output root.
- A `present` Heinlein criterion lacks valid supporting evidence, or a dependency
  violation is accepted without quarantine.
- A retry occurs without a persisted attempt artifact and usage record.
- Any paid model call would be made.
- A trial is not persisted before the next trial starts.
- Provider-wide or infrastructure failures make a trial uninterpretable.
- The runner's persisted stage decision is operational guidance only; it is not
  evidence of theoretical accuracy, human agreement, or production readiness.

## Report requirements

`heinlein_canary_report.md` must distinguish:

- structural contract success;
- results against the pre-set expectations for each case;
- partial successes, quarantined stages, and coercions or repairs;
- input and output token usage and latency;
- repeatability across the three trials and agreement with the baseline;
- evidence-stage failures, kept separate from Heinlein-stage results;
- a proceed, revise, or stop recommendation.

The canary must not be described as Phase 2 validation, human agreement, or
evidence of theoretical accuracy.

## Paid backends are excluded

The Heinlein stage adds one model call per story that no reviewed paid-run
estimate covers, so the runner rejects `--include-heinlein` whenever a paid call
would be made. Covering a fourth call in a paid run needs separate work: a
reviewed estimate, the Heinlein prompt and schema in the approval snapshot's
fingerprints, and an explicit relaxation of the rejection. `WI-SF-0016` is the
closest existing item.

## Invalidation

Results apply to the current `heinlein-five-v1` rubric wording. If a later
comparison finds a difference that changes the meaning of a condition and a
`heinlein-five-v2` rubric is minted, rerun the canary. A wording-only change to
the rubric text changes the Heinlein stage prompt, so earlier Heinlein
checkpoints are not reused.
