# model_comparison

Lightweight, checked-in infrastructure for comparing LLM backends/models
against the Event-Role-World (ERW) pipeline's actual tool-schema extraction
path - not a one-off script, meant to be reused whenever a new candidate
model or runtime shows up. Lives under `lcats/experimental/` (Google's
`experimental/` convention: real, runnable code that isn't a production
dependency yet) - not `notebooks/` (exploratory, not meant to be re-run as
a suite) or `KMo/` (a collaborator's separate test code).

Context: `experiments/03_cross_segment_relation_pilot/run_pilot.py` costs
$10-40+ per real run against the default frontier model
(`claude-opus-4-8`). See
`project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`'s
Category E and `project/design/backlog.md`'s "ERW pipeline audit's
Category E ... never promoted to a proposal" entry for the full cost
history and the audit's own recommendation: a cheap, targeted spike
(run one story through the real tool-schema path against a candidate
model) before assuming any cost-reduction lever is viable.

## Layout

```
model_comparison/
  common/harness.py               - shared single-stage benchmark logic, reused by every candidate
  common/sample_segment.json      - real scene/sequel segment, the actual benchmark input
  common/generate_sample_segment.py - regenerates sample_segment.json (real stage-1 segmentation call)
  benchmark_summary.py            - prints a comparison table across every candidate/results.json
  anthropic_opus/                 - frontier baseline (claude-opus-4-8, AnthropicBackend)
  ollama_qwen3_8b/                - local "cheap tier" candidate (qwen3:8b via Ollama, OpenAIBackend+base_url)
  ollama_qwen3_30b_a3b/           - local "quality tier" MoE candidate (qwen3:30b-a3b via Ollama, OpenAIBackend+base_url)
  <new_candidate>/                - add more by copying an existing candidate's shape
```

Each candidate directory has:
- `README.md` - what it is, expected cost/setup, what a good/bad result looks like
- `setup.py` - prerequisite check only (API key present, or local server
  reachable + model pulled). Never downloads/installs anything itself -
  downloading model weights or a new runtime is a deliberate step a human
  (or an agent with explicit permission) takes, documented in the
  candidate's own README, not a side effect of running a check.
- `benchmark.py` - runs `common.harness.run_entity_extraction()` with that
  candidate's backend + model, writes `results.json` in its own directory
- Optionally `benchmark_genre.py`/`benchmark_segmentation.py` - same
  shape, calling `common.harness.run_genre_detection()`/
  `run_segmentation()`, writing `results_genre.json`/
  `results_segmentation.json` (`WI-LLM-0050`; see
  `ollama_qwen3_8b/benchmark_genre.py` for an example)

## Adding a new candidate

1. `mkdir model_comparison/<candidate_name>/`
2. Write `setup.py` (prerequisite check - no downloads)
3. Write `benchmark.py` that builds an `LLMBackend` instance
   (`lcats.llm.anthropic_backend.AnthropicBackend`,
   `lcats.llm.openai_backend.OpenAIBackend` - works for any OpenAI-
   compatible local server via its `base_url` parameter, e.g. Ollama,
   vLLM, LM Studio - or a new backend implementing the
   `lcats.llm.backend.LLMBackend` protocol) and calls
   `common.harness.run_entity_extraction(candidate=..., backend_kind=..., backend=..., model=...)`
4. `python <candidate_name>/setup.py && python <candidate_name>/benchmark.py`
5. `python benchmark_summary.py` to compare against existing candidates

## Current scope (deliberately narrow - widen once this proves useful)

- **Three stages**: stage-3 entity extraction
  (`lcats.analysis.event_role_world.entity_extractor`), genre detection
  (`lcats.analysis.corpus.assess.assess_story()`'s detect mode), and
  scene/sequel segmentation (`lcats.analysis.scene_analysis.make_segment_extractor()`)
  - the same real tool schemas and call paths the real pipeline uses, not
  synthetic schemas (`WI-LLM-0050` added the latter two). Event/relation/
  discourse extraction and the cross-segment relation pass are not yet
  covered; add stages to `common/harness.py` the same way if/when needed.
- **One fixed sample segment**: `common/sample_segment.json` - a real
  ~600-word scene/sequel segment drawn from
  `corpora/sherlock/five_orange_pips/story.json` by an actual run of the
  real stage-1 segmenter (`common/generate_sample_segment.py`), not the
  whole story. This corrects an earlier version of this harness that fed
  entity_extractor.py the entire ~7,300-word story - inflating cost/
  latency for every candidate and mismatching entity_extractor.py's own
  system prompt, which describes its input as "a segment of a story." See
  `ollama_qwen3_8b/README.md`'s "Methodology fix" section for the before/
  after comparison this caused. Not a stratified sample; see
  `run_pilot.py`'s own stratified genre sampling for that. Genre
  detection and segmentation (`WI-LLM-0050`) correctly use the whole
  story instead (`common.harness.DEFAULT_SAMPLE_STORY`) - unlike entity
  extraction, both operate over an entire story in the real pipeline, so
  a single segment would be the wrong input size for them.
- **What's measured**: did the call succeed at all, did it return a
  well-formed `tool_result` matching the schema, latency, token counts, and
  entity count as a crude sanity signal - not extraction *quality*
  (precision/recall against ground-truth entities). Quality comparison
  needs human review of the actual extracted entities, which this harness
  surfaces via `results.json` but does not itself judge. `results.json`
  also includes a truncated `raw_output_preview` of the model's free-text
  response when no valid tool call was made, so a failure can be
  diagnosed from the file alone rather than needing a live rerun.
- **Sampling parameters**: `common.harness.DEFAULT_TEMPERATURE` (0.2)
  matches the real pipeline's own `entity_extractor.py` default, tuned for
  Anthropic/OpenAI. Candidates for a model with its own documented
  sampling recommendation should override `temperature=` in their
  `benchmark.py` rather than inherit this default silently - see
  `ollama_qwen3_8b/benchmark.py` for an example (Qwen3 recommends 0.6,
  not 0.2).

## Research context (no download/execution - see individual candidates for real runs)

A web survey of the local-model landscape (Aug 2026) found:

- **Runtimes**: Ollama and vLLM both have first-class OpenAI-compatible
  tool-calling support; Ollama additionally does grammar-constrained JSON-
  schema decoding (XGrammar-backed since 0.3+), which is the actual
  mechanism analogous to Anthropic's/OpenAI's `strict: true`. MLX
  (Apple-Silicon-native, via `mlx-lm`) also has native tool-calling support
  and several OpenAI-compatible-server wrappers exist for it. llama.cpp is
  the engine under Ollama/many other tools; direct tool-calling support
  varies by which wrapper is used.
- **Model sizing**: Qwen3 ships Ollama-library sizes from 0.6b up through
  235b, including an 8b (fits comfortably in 8GB+ VRAM/unified memory - the
  "cheap tier" target for lighter stages) and 30b-a3b (a mixture-of-experts
  model, ~30B total/~3B active params - lower compute cost than a dense 30B
  while still targeting a higher quality ceiling). **Update:** now tested
  (`ollama_qwen3_30b_a3b/`, `WI-LLM-0049`) - the "narrows the recall gap"
  hypothesis was **not supported**: 2 of 3 real runs returned
  near-empty/malformed results despite structural success, worse
  reliability than the smaller `qwen3:8b`. See
  `ollama_qwen3_30b_a3b/README.md`'s "Actual results" for the real,
  surprising findings. Similar tiers exist for Gemma 4 and Llama 4, not
  yet tested.
- **Caveat**: most "2026 benchmark" search results were SEO-farm content
  with suspiciously precise, hard-to-verify numbers (e.g. specific BFCL/
  SWE-bench percentages) - treated as landscape orientation only, not as a
  substitute for this directory's own real, checked-in benchmark runs. Per
  this repo's own standing guidance to ground external claims rather than
  cite benchmark-leaderboard position uncritically.

This is orientation for choosing which candidates to add next, not a
substitute for actually running `benchmark.py` against a real local model -
that step (installing Ollama, pulling model weights) is a deliberate,
explicit action taken separately, per each candidate's own README.
