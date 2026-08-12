# ollama_gemma4_12b

Gemma-offline candidate for `model_comparison/` (`WI-LLM-0056`, tranche 1)
- `gemma4:12b` (Google's open-weight lineage - Gemini itself has no open
weights) via `lcats.llm.openai_backend.OpenAIBackend` pointed at Ollama's
OpenAI-compatible endpoint, the same pattern `ollama_qwen3_8b` uses.

## Setup

```bash
python setup.py
```

Checks Ollama is reachable and `gemma4:12b` is pulled
(`ollama pull gemma4:12b`, ~7.6GB). Does not pull it itself.

## Run

```bash
python benchmark.py
```

Runs the ERW pipeline's actual stage-3 entity-extraction tool-schema call
against the same real ~600-word scene/sequel segment `anthropic_opus`
uses (`../common/sample_segment.json`), with `max_tokens=8192`.

## Actual results (`WI-LLM-0056`)

**Failed consistently (2/2).** Both runs came back `finish_reason='stop'`
with **no tool call at all** - the exact `tool_choice` forced-function-name
gap `WI-LLM-0051` characterized on the segmentation stage, now reproduced
on entity extraction too:

| Run | Result | Latency | Output tokens |
|---|---|---|---|
| 1 | failed (`no_tool_call`) | 310.1s | 4208 |
| 2 | failed (`no_tool_call`) | 544.1s | 7528 |

Both runs' free-text `content` visibly *begins* a schema-shaped JSON
object matching `extract_entities`'s expected structure - but
`OpenAIBackend.complete()` truncates this content to 2000 characters
before raising, and both committed `results_run*.json` files cut off
mid-object (`raw_output_preview` is also `None` on this failure path, so
no fuller capture exists). Neither committed artifact can establish that
the *full* response would have been well-formed or complete - only that
the visible prefix is schema-shaped (review finding, PR #273; the same
caveat `WI-LLM-0050`'s segmentation README already applies to an
identical truncation situation). This
model was also markedly slower than every other candidate tested in this
tranche (5-9x `anthropic_opus`'s latency on the identical call), and run 2
took noticeably longer than run 1 while producing more output tokens for
essentially the same (never-materializing) answer - no retry-with-reminder
mitigation (`WI-LLM-0051`'s finding) was attempted here, out of this
tranche's own scope (Non-Goals: no quality/mitigation comparison, only
call-success/latency/entity-count).

## Follow-up: reminder-retry mitigation and a token-budget confound (`WI-LLM-0062`)

`WI-LLM-0062` tested whether `WI-LLM-0051`'s reminder-retry mitigation
(`common/harness.py`'s `run_entity_extraction(..., retry_with_reminder=True)`,
adapted from the segmentation-stage mechanism) helps this candidate's
entity-extraction failures. `benchmark_entity_reminder.py` runs this.

**A real methodological confound surfaced first, and had to be corrected
before the actual question could be tested:** the first 3 real runs at
`harness.DEFAULT_MAX_TOKENS` (8192) all failed with `error_type=
"truncated_output"` - genuinely hitting the token ceiling mid-tool-call,
not `no_tool_call` at all (see `results_entity_reminder_run{1,2,3}.json`).
This is a *different* failure mode than the one `WI-LLM-0056` originally
observed and this WI set out to test, and it masked the actual question:
`error_type != "no_tool_call"` means the retry path never even fires. Raised
`max_tokens` to 16384 (matching `harness.DEFAULT_SEGMENTATION_MAX_TOKENS`'s
precedent for a larger-output stage) to get past this confound - see
`benchmark_entity_reminder.py`'s own comment for the full rationale.

**At `max_tokens=16384`, 4 real runs** (`results_entity_reminder_run{4,5,6,7}.json`):

| Run | Baseline result | Retry attempted | Retry result | Latency |
|---|---|---|---|---|
| 4 | success (14 entities) | no (baseline succeeded) | - | 251.9s |
| 5 | **baseline itself timed out** (`Request timed out`, not `no_tool_call`) | no (retry only fires on `no_tool_call` specifically) | - | 1801.5s |
| 6 | failed (`no_tool_call`) | yes | **succeeded (17 entities)** | 1783.5s\* |
| 7 | failed (`no_tool_call`) | yes | failed (`Request timed out`) | 2798.1s |

\* Run 6 predates a review finding (PR #277) that this harness's retry
wrapper was reporting only the *retry* call's own latency/tokens,
silently discarding the failed baseline attempt's real resource use -
fixed in `common/harness.py` (now sums both calls), but run 6's own
`results_entity_reminder_run6.json` was generated before the fix and is
a known undercount for `latency_seconds`/`input_tokens`/`output_tokens`
specifically. Its qualitative outcome (baseline failed, retry succeeded)
is unaffected by this bug and stands as reported. Run 7 was generated
after the fix and its resource numbers are the true baseline+retry total.

**Verdict: the reminder mitigation can work here too** (1 of 2 applicable
retries succeeded across runs 6-7, matching the same "real, substantial,
not total effect" pattern `WI-LLM-0051` found on segmentation) - the same
1/2 ratio held up under a second, independently corrected sample, which is
itself modest further evidence it's a real effect and not a one-off. Run 5
surfaces a third distinct failure mode for this candidate beyond
`truncated_output`/`no_tool_call`: the baseline call itself can time out
outright, which the reminder mechanism has no way to address (it only
retries on `error_type="no_tool_call"` specifically). The evidence remains
smaller and noisier than segmentation's 5-sample result - this candidate's
own latency (250-2800+ seconds per call, including two genuine request
timeouts across 7 total runs) makes gathering a larger sample expensive.
The token-budget confound found first is itself a real, useful finding
independent of the reminder question: this candidate's true baseline
failure rate under `DEFAULT_MAX_TOKENS` may be inflated by truncation
rather than tool_choice being ignored - the two failure modes need to stay
analytically separate, not conflated into one "tool_choice gap" statistic.
