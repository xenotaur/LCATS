# WI-SF-0015 Contract Canary Report

## Decision

**Revise/stop before repeating the canary or approving paid trials.** One
no-cost local trial was run against `gpt-oss:20b` through Ollama. It exposed a
provider/output failure on the negative control and did not establish the
behavioral expectations required by this item.

## Trial

- Manifest: `manifests/contract_canary_manifest.json`
- Backend: `openai-compatible`
- Endpoint: `http://localhost:11434/v1`
- Model: `gpt-oss:20b`
- Stories: exactly two, one expected positive and one negative/adjacent control
- Output: `results/worldcon_spike/contract_canary/local/trial-1/`
- Paid calls: none

The positive story completed and persisted raw stage outputs, a normalized
sidecar, checkpoints, the append-oriented story result, and run-log events.
The negative control failed in shared evidence extraction. The model produced
malformed/truncated tool JSON; the bounded retry policy retried once, and the
second attempt ended in a provider `500` parsing error. Both attempts and the
quarantine record were persisted.

The completed positive result reported Knight `0/0` and no qualified novum,
so it did not meet the expected positive behavior. The negative control had
no adjudication result because evidence extraction failed. This is a contract
and local-model integration failure, not evidence about theoretical accuracy.

## Persisted Evidence

- `results/worldcon_spike/contract_canary/local/trial-1/worldcon_spike_summary.json`
- `results/worldcon_spike/contract_canary/local/trial-1/worldcon_spike_story_results.jsonl`
- `results/worldcon_spike/contract_canary/local/trial-1/worldcon_spike_run_log.jsonl`
- Per-attempt raw responses and backend-error artifacts under the trial's raw
  and quarantine directories
- The positive story's `science-fiction.json` and
  `science-fiction-sidecar.json` artifacts

## Next Fixes Before Another Trial

1. Add a local-model-specific tool-call/JSON repair or response-format path
   that can handle the observed malformed nested evidence output without
   inventing evidence.
2. Add a no-cost regression fixture containing the observed truncated tool
   response and assert quarantine plus retry accounting.
3. Re-run one two-story local canary after that fix; do not run paid Opus or
   the 10-story sample until the positive/negative behavioral expectations are
   both met.

This report does not claim theoretical validation, human agreement, or a
Phase 2 result.
