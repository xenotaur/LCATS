# Heinlein Live Canary Report v2

This report covers `WI-SF-0116`: the Heinlein live canary run again, with the same manifest, model, and settings, on the code that includes the `WI-SF-0114` fail-loud fix. It is an operational check of the `sf_heinlein` stage and its neighbors. It is not a claim of theoretical accuracy, human agreement, or Phase 2 validation, and the pre-set expectations are operational checks, not gold labels. It compares against `heinlein_canary_report.md` (the `WI-SF-0113` canary, "v1"), whose results were not touched.

## Recommendation: revise

The mechanical problem the first canary found is fixed, but the stage's judgment is not yet trustworthy enough to scale.

- **Fixed:** all six flag-on Heinlein calls returned the schema's own keys with all five criteria, a rationale for every criterion, and cited evidence for every `present` criterion. There were no Heinlein quarantines or failures, no evidence-stage failures, and both stories got usable evidence in every run.
- **Not yet trustworthy:** the Bell negative control returned `qualifies` in two of three trials (all five criteria `present`), which breaks its pre-set expectation. The Vonnegut positive returned `qualifies` in all three. A stage that says yes to the control two times in three does not yet discriminate.
- **Next:** do not widen the sample. Look into why the control passes (the evidence sets were identical in all three trials, so the difference is in the Heinlein judgment itself), with more than one control story, and treat a different or larger model as a separate item.

## Setup

- Code commit `5a68c2473671fab52b11d480285933dc54f8bb45` (contains `fa33d1bb`, the `WI-SF-0114` merge). Manifest `manifests/heinlein_canary_manifest.json`, fingerprint `91b751682f0718e2aa717a0d44d4b4e0c2ad1603446995260e67e78d5e993d41` in every run, unchanged from v1. Every run's `manifest_snapshot.json` equals the manifest when both are parsed as JSON.
- Model `gpt-oss:20b`, digest `17052f91a42e` (full `17052f91a42e97930aa6e28a6c6c06a983e6a58dbb00434885a0cf5313e376f7`; 20.9B parameters, MXFP4; last modified 2026-08-08), the same as v1. Ollama server version 0.32.5, the same as v1, on `127.0.0.1:11434`, loaded context 32768 at 100% GPU. `--max-tokens 8192 --max-failures 3`, temperature 0.0. No paid call was made; every run reported estimated cost 0.0.
- The Ollama server was started for this item with `OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1` and otherwise default settings. It was not private to this run (see "Interference and limits").
- Python 3.11.8 with `PYTHONPATH` set to this checkout's `src` (the editable install points at another checkout). Before the runs: `scripts/test` passed (2550 tests), the fake-backend smoke with `--include-heinlein` processed both stories, and the CI-pinned black 25.11.0 and ruff 0.15.0 showed the runner file's known four black hunks and one ruff finding, the same as `main`.
- `ollama list` and `ollama ps` were run before the baseline and before each trial, and once after trial 3. In every record `gpt-oss:20b` was ID `17052f91a42e`, the version was 0.32.5, and the loaded model showed `gpt-oss:20b 12 GB 100% GPU 32768`:

| Check | Time (UTC) | Version | `gpt-oss:20b` ID | `ollama ps` |
| --- | --- | --- | --- | --- |
| before baseline | 2026-10-11 02:25:21 | 0.32.5 | `17052f91a42e` | nothing loaded; after start: `gpt-oss:20b 12 GB 100% GPU 32768` |
| before trial-1 | 02:32:05 | 0.32.5 | `17052f91a42e` | `gpt-oss:20b 12 GB 100% GPU 32768` |
| before trial-2 | 02:40:43 | 0.32.5 | `17052f91a42e` | `gpt-oss:20b 12 GB 100% GPU 32768` |
| before trial-3 | 02:48:05 | 0.32.5 | `17052f91a42e` | `gpt-oss:20b 12 GB 100% GPU 32768` |
| after trial-3 | 04:32:41 | 0.32.5 | `17052f91a42e` | `gpt-oss:20b 12 GB 100% GPU 32768` |

## Runs

Latency is the runner's own measure; v1 numbers are in brackets.

| Run | Stories complete | Heinlein verdicts | Latency (s) | Input / output tokens |
| --- | --- | --- | --- | --- |
| baseline (flag off) | 2 of 2 | none | 367 [781] | 30024 / 11797 [24687 / 12322] |
| trial-1 | 2 of 2 | 1 qualifies, 1 does_not_qualify | 500 [601] | 36216 / 13456 [38714 / 14707] |
| trial-2 | 2 of 2 | 2 qualifies | 422 [493] | 36216 / 12252 [38714 / 13173] |
| trial-3 | 2 of 2 | 2 qualifies | 1076 [503] (see limits) | 40708 / 13759 [38714 / 13173] |

The baselines are not directly comparable: the evidence prompt changed, and the v1 baseline's Vonnegut Knight and Suvin stages failed.

## Answers to the four questions

1. **Does the Heinlein stage now produce interpretable output from a real model? Yes, mechanically.** Of the six flag-on Heinlein calls, six returned a response with the schema's keys (`criterion_id`, `status`, `supporting_evidence_ids`, `counterevidence_ids`, `rationale`, `confidence`), five criteria, a rationale on every criterion, and at least one cited evidence record on every `present` criterion. None was quarantined or failed. "Interpretable" here means well-formed and traceable, not correct (see the Bell control below). In v1, none of the six raw Heinlein responses used the schema keys.
2. **Do both stories get usable evidence? Yes.** Vonnegut had 4 usable records in the baseline and 3 in each trial; Bell had 2 in the baseline and 3 in each trial. The candidates that were quarantined (1 to 3 per story and run) were all quarantined as `quote could not be located in prepared story`. No candidate was rejected for a missing `evidence_type`, and there were no evidence-stage failures. In v1, Vonnegut had zero usable records in all three trials.
3. **Is a key mismatch now quarantined rather than silent? It was not exercised live.** Every evidence and Heinlein response in the v2 runs used the schema's keys, so no mismatch occurred. Quarantine of mismatched keys is covered by the `WI-SF-0114` tests and fixtures, not by these runs. What the runs do show is that the silent discard did not recur, and that conformance changed from 0 of 6 Heinlein responses (v1) to 6 of 6 (v2). The only model-facing change between the two canaries was the prompt wording, so the prompt change is the likely cause; the runs cannot separate that from chance.
4. **What do the runs show about Ollama's handling of `strict` and `tool_choice`?** The runner does not persist the request it sends, so the persisted files show only whether the forced tool call was honored and whether keys conformed. They cannot show whether `strict` was forwarded to Ollama.
   - **`tool_choice`:** the forced tool call was not honored in 6 of 30 stage calls (the `no_tool_call_json_fallback` event), the same count as v1 (6 of 30). So the fix did not change this. It is consistent with Ollama's OpenAI-compatibility page listing `tool_choice` as unsupported.
   - **`strict`:** unresolved. Keys now conform in the text-fallback responses as well as in real tool calls (3 of the 6 Heinlein responses were text fallbacks). Text responses are not constrained by any tool schema, so the conformance is prompt-driven and is not evidence that `strict` is enforced. What would settle it is capturing the request payload and a run with a prompt that does not name the keys.

## Comparison with the first canary

### Evidence stage (usable records / quarantined candidates)

| Story | v1 baseline | v1 trials 1, 2, 3 | v2 baseline | v2 trials 1, 2, 3 |
| --- | --- | --- | --- | --- |
| Vonnegut | 7 / 1 | 0 / 6, 0 / 6, 0 / 6 | 4 / 1 | 3 / 2, 3 / 2, 3 / 2 |
| Bell | 3 / 2 | 4 / 2, 4 / 2, 4 / 2 | 2 / 3 | 3 / 1, 3 / 1, 3 / 1 |

### Tool call versus text fallback

Counts of `no_tool_call_json_fallback` events across all four runs of each family: v1 had 6 (evidence 3 on Vonnegut, Heinlein 3); v2 had 6 (Heinlein 3, Suvin 2, Knight 1). `fenced_json_unwrapped` events: 0 in v2 (the text fallbacks were plain JSON), so the strict fence path was not exercised live. `evidence_empty_list` events: 0.

### Heinlein results (v2)

| Trial | Vonnegut | Bell |
| --- | --- | --- |
| 1 | `qualifies` (5 `present`) | `does_not_qualify` (`human`, `plausible` present; `different`, `essential`, `causal` absent) |
| 2 | `qualifies` (5 `present`) | `qualifies` (5 `present`) |
| 3 | `qualifies` (5 `present`) | `qualifies` (5 `present`) |

In v1 the stored results were all `not_assessable` or `Unavailable` (finding 1 of the first report).

### Results against the pre-set expectations

| Story | Expectation | Trial 1 | Trial 2 | Trial 3 |
| --- | --- | --- | --- | --- |
| `mass_quantities/2_b_r_0_2_b__vonnegut` (positive) | `qualifies` or `indeterminate`; none of different, essential, human, causal `absent` | Met | Met | Met |
| `anderson/bell` (control) | `does_not_qualify` or `indeterminate`, never `qualifies` | Met | **Not met** (`qualifies`) | **Not met** (`qualifies`) |

For Vonnegut the result is now a real judgment with evidence and rationales, not the vacuous pass of v1. For Bell the model's own account differs between trials: in trial 1 it says the story "does not introduce any new invention or condition differing from present day", and in trials 2 and 3 it says the "bell is imaginary, a new condition distinct from reality" and that the imaginary bell "drives the plot". The three Bell evidence sets contained the same three records, so the evidence did not cause the difference. The `different` criterion reads a nonexistent bell as a new condition in two trials, which is a misreading a reviewer would likely flag. Whether the prompt's own worked example (a `present` item) biases the model toward `present` is a hypothesis these runs cannot test.

### Partial successes outside the Heinlein stage

- **Knight on Bell:** failed with a provider 500 (`error parsing tool call`) on the first attempt in trials 1, 2 and 3. It stayed failed in trials 1 and 2 (partial success, story complete) and succeeded on the retry in trial 3. The first canary's baseline showed the same provider error on the Vonnegut Knight stage. This is local-model behavior in the Knight stage, not a Heinlein result.
- **Suvin:** completed in every run. Knight on Vonnegut completed in every v2 run, which it did not in the v1 baseline.

## Interference and limits

- **Shared server.** The Ollama server was not private to this run. A `local_agent` process from another local worktree was using the same server with `gemma4:12b` (model loads of `gemma4:12b` appear in the server log at 20:17, 21:30 and 21:42 EDT before the runs, at 22:52, 22:54, 22:57 during trial 3, and again after). Baseline, trial 1 and trial 2 ran between 22:25 and 22:48 EDT with no other model loaded; trial 3's Bell evidence and Knight stages (about 22:50 to 22:57 EDT) overlapped the model swaps. The first Bell Knight attempt took about six minutes instead of the usual 30 seconds before failing.
- **Machine sleep.** The Bell Knight retry in trial 3 spans 5710 s of wall-clock time in the run log, but the runner's own measure for the story is 914 s. The system log (`pmset -g log`) shows the machine entering sleep at 22:57:47 EDT, 25 seconds after the first Knight attempt failed, with only brief dark wakes until a full wake at 00:25:16 EDT. So nearly all of the gap is the machine being suspended, not a hung server. I first read this as a stall caused by the other session, and that was wrong. Trial 3's latency (1076 s) should be disregarded, and trial 3's Bell Knight timing is not meaningful. Trial 3's other stages ran at normal speed and its verdicts are model outputs unaffected by queueing, though a swapped-out model's cache may differ.
- **Sample.** Three trials of one model, with a prompt-and-code confound against v1 (the prompts and the code both changed), and a single control story.
- **No request capture.** The runner does not persist the request, so `strict` forwarding cannot be observed.
- **Absolute local paths.** The committed result files contain absolute local paths, as the first canary's did (mostly `raw_response_path` fields). They were not edited. The test output, the fake smoke output, the `ollama` records quoted above, and the sleep log are reported here but not committed as files.

## Method

Every figure was read from the persisted files with short Python scripts that were not committed: `worldcon_spike_summary.json` (status, totals, plan, code commit, manifest fingerprint), `worldcon_spike_run_log.jsonl` (events `no_tool_call_json_fallback`, `fenced_json_unwrapped`, `evidence_empty_list`, `stage_retry`, stage start and end times), each story's `science-fiction.json` (`evidence_sets` records and quarantine reasons, `analyses` statuses, intervals, criteria and rationales, `partial_success`), and `_raw/**/sf_*.json` (keys of every evidence and Heinlein response, whether `text` was empty, which distinguishes a real tool call from the text fallback). The v1 figures were read from the same fields of the `heinlein_canary/local` roots, which were not modified (`git status --short` on that directory prints nothing).

## Files

Persisted under `results/worldcon_spike/heinlein_canary_v2/local/`: `baseline/`, `trial-1/`, `trial-2/`, `trial-3/` (109 files, about 0.8 MB, no database files). Each holds the manifest snapshot, raw stage responses and attempts, quarantine files, the run log, sidecars, the summary, and the per-run report.
