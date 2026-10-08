# Heinlein Live Canary Report

This report covers `WI-SF-0113`: one flag-off baseline and three flag-on local trials of the optional `sf_heinlein` stage, run as `heinlein_canary_runbook.md` describes. It is an operational check of the stage and its failure handling. It is not a claim of theoretical accuracy, human agreement, or Phase 2 validation, and the pre-set expectations are operational checks, not gold labels.

## Recommendation: revise

Do not proceed to a larger sample yet. The stage ran without crashing and failed safely, but against this model its output cannot be interpreted, because the pipeline silently discarded the model's decisions in every run (finding 1 below). Fix that first, then rerun this canary.

## Setup

- Code commit `8540a93845aa3f0dd68218e763842bbd0ee031f4` (the tip of `main` after `WI-SF-0113` was planned). Manifest `manifests/heinlein_canary_manifest.json`, fingerprint `91b751682f0718e2aa717a0d44d4b4e0c2ad1603446995260e67e78d5e993d41`, identical in all four runs.
- Model `gpt-oss:20b`, digest `17052f91a42e` (`ollama list`), loaded with a 32768-token context at 100% GPU (`ollama ps`). Server: Ollama on `http://localhost:11434/v1` (loopback), `--max-tokens 8192`, `--max-failures 3`, temperature 0.0. The Ollama process was started by another session and was left running.
- Python 3.11.8 with `PYTHONPATH=$PWD/src`; the editable install pointed at another checkout and was bypassed. The full suite passed first (2465 tests, OK), and the fake-backend smoke with `--include-heinlein` processed both stories and published 2 verdicts.
- Every run's `manifest_snapshot.json` equals the manifest when both are parsed as JSON. No paid call was made, and every run reported estimated cost 0.0.

## Runs

| Run | Stories complete | Heinlein verdicts | Latency (s) | Input / output tokens |
| --- | --- | --- | --- | --- |
| baseline (flag off) | 2 of 2 | none | 781 | 24687 / 12322 |
| trial-1 | 2 of 2 | 1 indeterminate, 1 unavailable | 601 | 38714 / 14707 |
| trial-2 | 2 of 2 | 2 indeterminate | 493 | 38714 / 13173 |
| trial-3 | 2 of 2 | 2 indeterminate | 503 | 38714 / 13173 |

The Heinlein stage alone used about 4589 input tokens on `anderson/bell` and 5237 on the Vonnegut story, and between 934 and 1814 output tokens per call. Latency is not comparable across runs, because the baseline's Vonnegut story spent time on a failed Knight call.

## Results against the pre-set expectations

| Story | Expectation | Stored result, trials 1 / 2 / 3 | Read |
| --- | --- | --- | --- |
| `mass_quantities/2_b_r_0_2_b__vonnegut` (positive) | `qualifies` or `indeterminate`; none of different, essential, human, causal `absent` | indeterminate / indeterminate / indeterminate, all five criteria `not_assessable` | Met, but only vacuously: `not_assessable` is not `absent`, and the model gave no rationale or evidence. |
| `anderson/bell` (control) | `does_not_qualify` or `indeterminate`, never `qualifies` | unavailable / indeterminate / indeterminate | Trial 1 is not evaluated: the Heinlein stage failed and the story was `Unavailable`, which the expectation does not allow as a result. Trials 2 and 3 are met, but only because the pipeline discarded the model's answer (finding 2). |

## Findings

1. **The pipeline silently discards the model's decisions (main finding).** The tool schema names the keys `criterion_id`, `status`, and `supporting_evidence_ids` (`run_worldcon_spike.py:2473-2501`), and the normalizer reads those keys (`run_worldcon_spike.py:1966-1990`). In all six raw Heinlein responses, `gpt-oss:20b` used other key names: `criterion`, plus `decision` or `decision_state`, plus `evidence_ids`. The Knight stage in the same runs used the schema keys. The normalizer then finds no `criterion_id`, defaults every criterion to `not_assessable` with an empty rationale, and still reports the stage `complete`. No quarantine, failure, or coercion record is written. This contradicts the stage's own rule that decisions are never repaired quietly. The schema evidently was not enforced for this model through Ollama (not separately confirmed), so the prompt's "return exactly the schema keys" is the only control.
2. **The model's raw answers disagree with the stored verdicts.** For `anderson/bell` in trials 2 and 3 the raw response marks all five criteria `present` with one or two evidence IDs each, and the trial 1 fenced text does the same (all five `present`, one or two evidence IDs each). The stored result is `not_assessable` because of finding 1. The negative-control expectation is therefore satisfied by accident in trials 2 and 3, and trial 1 is not evaluable. If the keys had been read as written, the control would most likely have been `qualifies`, which would break its expectation; this is an inference from the raw decisions, not a computed result. For the Vonnegut story the model itself returned `not_assessable` for all five criteria in all three trials.
3. **Fenced JSON text instead of a tool call (trial 1, Bell).** The model answered with a Markdown-fenced JSON block and no tool result, giving a `JSONDecodeError` at character 0. This is the designed failure path and it worked: the stage was quarantined (`_quarantine/…/sf_heinlein.json`), the raw response was kept, the story rendered as `Unavailable`, the story still completed, and its Knight and Suvin results were unaffected. Trials 2 and 3 did not repeat it. Rendering was checked afterwards with `render_json(..., detail='detailed')` and `render_comparison_table` on the trial 1 sidecars: the Bell story shows `Heinlein Verdict: Unavailable` with the warnings "contains failure records" and "Heinlein analysis is not current and is not shown as a verdict", and the comparison table shows "Heinlein unavailable"; the Vonnegut story shows `Indeterminate (0 / 5 conditions)`.
4. **Partial successes elsewhere.** In the baseline, the Vonnegut Knight stage failed with a provider 500 (tool-call parse error, two attempts, both persisted) and its Suvin stage was quarantined for a `present` dimension without evidence. Both stages passed in all three flag-on trials. This is local-model variation in the Knight and Suvin stages, not a Heinlein result.
5. **Evidence-stage failures: none.** The shared evidence stage succeeded in all four runs, so the intermittent failure seen in `WI-SF-0015` did not recur. That is one observation and does not show it is fixed.
6. **Repeatability.** Trials 2 and 3 produced identical Heinlein output at temperature 0.0, with the same token counts. Trial 1 differed in the Bell response shape. Three trials of one model are not decision-grade.
7. **No stop condition fired.** No stored `present` Heinlein decision lacked evidence (there were none), no dependency violation was accepted, every attempt has a persisted artifact, and no run was uninterpretable at the infrastructure level. The uninterpretability in finding 1 is semantic and is reported here, not as a runbook stop.

## What to do next

- Decide how the Heinlein stage should treat a response whose criterion keys do not match: fail loudly into quarantine, or accept the observed alias keys explicitly with a recorded coercion. Silent defaulting should not remain. Also decide whether to strip Markdown fences, and whether the prompt or a stricter local-backend schema forwarding should enforce the key names.
- After that change, rerun this canary: a baseline and three trials, with the pre-set expectations unchanged, and compare the Bell control and the Vonnegut positive again.
- Separately, the all-`not_assessable` answer for the Vonnegut story may reflect the evidence supplied or the prompt, and is not explained by this canary.
- Results apply to the current `heinlein-five-v1` rubric wording and prompt, and to this model and digest only.

## Files

Persisted under `results/worldcon_spike/heinlein_canary/local/`: `baseline/`, `trial-1/`, `trial-2/`, `trial-3/`. Each holds the manifest snapshot, raw stage responses and attempts, quarantine files, the run log, sidecars, the summary, and the per-run report. No `.db` file was produced, so nothing was left out of the commit.
