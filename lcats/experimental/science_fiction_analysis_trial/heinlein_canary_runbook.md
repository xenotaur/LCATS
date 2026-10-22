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
   and `--include-heinlein` is then rejected. For a canary, use the private
   server described under "Private server and preflight" below, not a shared one.
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

## Private server and preflight

The WI-SF-0116 rerun shared its Ollama server with another local agent, which
loaded a different model into the same server during the run, and the machine
slept for about 90 minutes inside one trial. Both obscure latency and can
disturb a stochastic run, so a canary should run on a server of its own and be
checked for both afterwards. The commands below are macOS examples, not
requirements.

### Procedure

1. Pick a loopback port that is not the default `11434` (this runbook uses
   `11435`) and confirm nothing is listening on it; no output means it is free:

   ```bash
   lsof -nP -iTCP:11435 -sTCP:LISTEN
   ```

2. Start a dedicated server in its own terminal, with its output kept in a
   file outside the repository. These are the settings the WI-SF-0116 rerun
   used, with the port changed:

   ```bash
   OLLAMA_HOST=127.0.0.1:11435 OLLAMA_NO_CLOUD=1 ollama serve > /tmp/ollama-canary-11435.log 2>&1
   ```

   A second server alongside the default one shares the same model directory
   (`~/.ollama/models` by default) and competes with it for GPU and unified
   memory, so do not load models in both at once.

3. Keep the first line of that log (`msg="server config"`). It lists the
   settings in effect, including `OLLAMA_KEEP_ALIVE`, `OLLAMA_MAX_LOADED_MODELS`
   and `OLLAMA_CONTEXT_LENGTH`, and belongs in the canary report.
4. Record the model digest and context length from the preconditions against
   the private server by pointing the `ollama` command at it, for example
   `OLLAMA_HOST=127.0.0.1:11435 ollama list` and, once the model is loaded,
   `OLLAMA_HOST=127.0.0.1:11435 ollama ps`.
5. Point the runner at it with `--base-url http://localhost:11435/v1` in every
   command below. Host `localhost` is loopback, so the run stays no-cost.
6. For a long run, keep the machine awake by wrapping the runner command in
   `caffeinate -i`, for example `caffeinate -i env OPENAI_API_KEY=ollama
   PYTHONPATH=src python experimental/science_fiction_analysis_trial/run_worldcon_spike.py ...`.
   `caffeinate` does not prevent every sleep (for example closing the lid on
   battery), so the sleep check below still applies.
7. After the run, check the server log for other clients (see below) and the
   system log for sleep (see below), and write both outcomes into the report.
8. When finished, stop only the server you started, by the process ID of that
   `ollama serve`. Never stop the default server on `11434`: another session may
   be using it.

### Isolation check after the run

`ollama ps` is necessary but not sufficient. It lists the models loaded at the
moment you run it, not who sent requests or what ran in between: in the
WI-SF-0116 rerun its before and after rows were identical while the server log
showed `gemma4:12b` swaps in the middle. The isolation check is the server log,
reviewed for the whole run window:

- **Model loads.** Each model load logs one `msg="template selection"` line
  that names the model (`model=registry.ollama.ai/library/<name>`). In the
  window, every such line must name the target model. A line for any other
  model means another client used the server.
- **Requests.** Each request logs a `[GIN]` line with its method and path.
  The runner sends only `POST /v1/chat/completions`, and since WI-SF-0120 it
  writes one request record per attempt (`request-<stage>[-attempt-N].json`,
  see the inspection checklist). Runs made before WI-SF-0120, such as the
  WI-SF-0116 rerun, have no request records, so this count cannot be checked
  for them. The OpenAI client the backend builds also retries failed requests
  (the installed SDK retries twice by default, including on HTTP 500 and
  connection errors), so one runner attempt can send up to three requests to
  the server and still write one record. The number of
  `POST /v1/chat/completions` lines in the window should therefore be at least
  the number of request records. A higher count is expected when the server
  returned errors that the client retried (the WI-SF-0116 log has 17 `500`
  responses among its 46 chat lines), so use the count as a
  cross-check, not an equality, and look at the status column. A count below
  the number of records needs an explanation (a call that failed before it
  reached the server can have a record and no log line).
  Any `POST /api/chat` or `POST /api/show` line was not sent by the runner. In
  the WI-SF-0116 server log such lines coincide with the `gemma4:12b` loads,
  which the report attributes to another local agent; the log itself does not
  say who sent them, and your own `ollama show` or `ollama run` would produce
  them too. `GET` lines (`/api/tags`, `/api/ps`, `/api/version`, `HEAD /`) can
  come from your own `ollama list` and `ollama ps` or from tools that poll the
  server; note them, and treat them as a signal only if you cannot account for
  them.
- **Limits of the check.** Every client appears as `127.0.0.1`, so client
  identity cannot be proven. A matching count and no foreign model loads is
  evidence of isolation, not proof, and the private port with its own
  `OLLAMA_HOST` is the actual control. A private server also does not remove
  run-to-run variation in the model's output.

### Sleep check

If any stage took much longer than the measured runner latency (the run log's
stage start and end times against the story's `latency_seconds`), look for a
sleep interval before suspecting the server. On macOS:

```bash
pmset -g log | grep -E "Entering Sleep|Wake from"
```

The `Sleep` and `Wake` lines carry local timestamps. Compare them with the
run log's UTC timestamps. The pattern also matches `DarkWake from ...` lines:
those are brief wakes, and a full wake can be preceded by several of them. In the WI-SF-0116 rerun the machine slept at 22:57:47 EDT and woke at
00:25:16 EDT, which is what made one stage appear to take 5710 seconds. Do not
use the latency of a stage that spans a sleep. Latency measured on a server
that other clients were using is likewise not comparable between runs.

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

The commands below use the first canary's output roots,
`results/worldcon_spike/heinlein_canary/local/...`, and the default server
`http://localhost:11434/v1`. The runner creates an output root with `exist_ok`,
so running a command unchanged against an existing root writes into it and
would append to the first canary's persisted results. For a rerun, use a new,
empty root for every trial (the WI-SF-0116 rerun used
`results/worldcon_spike/heinlein_canary_v2/local/...`) and confirm it does not
exist before the run. Use the private server's `--base-url` as described above.

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
- the request record of every model-call attempt, `request-<stage>.json` and
  `request-<stage>-attempt-N.json`, next to the raw responses under `_raw/`.
  Each holds the model, temperature, token cap, and the tool-forcing fields
  (tool schema with its `strict` value, and the `tool_choice` block). With the
  OpenAI-compatible backend `request_source` is `provider`, the request as
  built before it was sent, so these files show whether `strict` and a forced
  `tool_choice` were in the request. Other backends record `request_source:
  runner`, the runner-level call arguments only; a backend that supports
  capture also falls back to `runner` when a call fails before it builds the
  request. The records leave out the
  system prompt, the messages and the story text, and a stage reused from a
  checkpoint has none because it made no call. Commit them with the other
  persisted artifacts;
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
so about 16 minutes for a two-story trial. Timings from a shared server, or from a
run that spanned a machine sleep, are not comparable (see "Private server and
preflight"). The Heinlein stage is expected to add
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
