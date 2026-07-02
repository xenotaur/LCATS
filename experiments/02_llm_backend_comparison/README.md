# LLM Backend Comparison Experiment

**WI-LLM-0010** — Side-by-side model comparison dry run for the assess pipeline.

## Purpose

Validate that the `LLMBackend` abstraction produces consistent, comparable
output across providers. This is the baseline experiment for the WorldCon 2026
model-comparison work.

## Scripts

### `run_comparison.py`

Runs `assess_story` on the first N stories (alphabetically) from a corpus
directory using one backend/model pair, writing results as JSONL.

```
python experiments/02_llm_backend_comparison/run_comparison.py \
  --backend anthropic|openai \
  --model MODEL_STRING \
  --genre GENRE \
  --corpus-dir lcats/data/lovecraft \
  --sample N \
  --output experiments/02_llm_backend_comparison/results/
```

Output file: `results/<backend>-<model>-<genre>-<N>.jsonl`
Each line: a JSON-serialised `AssessmentResult` dict.

### `compare_results.py`

Prints a per-story comparison table and verdict/genre_match agreement rates.

```
python experiments/02_llm_backend_comparison/compare_results.py \
  results/anthropic-*.jsonl results/openai-*.jsonl
```

## Sample Selection

Stories are selected as the first N `.json` files in `--corpus-dir` sorted
alphabetically. This ensures reproducibility without a random seed dependency.

## Baseline Run (2026-07-02)

### Horror — Lovecraft corpus (`lcats/data/lovecraft/`, 5 stories)

Stories assessed (first 5 alphabetically):
1. `at_the_mountains_of_madness.json`
2. `cool_air.json`
3. `he.json`
4. `the_call_of_cthulhu.json`
5. `the_case_of_charles_dexter_ward.json`

| Story | Anthropic verdict | OpenAI verdict | Genre match (A/O) |
|---|---|---|---|
| At the Mountains of Madness | exclude | exclude | confirmed / confirmed ✓ |
| Cool Air | review | exclude | confirmed / confirmed ✓ |
| He | review | review | confirmed / confirmed ✓ |
| The Call of Cthulhu | review | exclude | confirmed / confirmed ✓ |
| The Case of Charles Dexter Ward | exclude | exclude | confirmed / confirmed ✓ |
| **Agreement** | — | — | **Verdict 3/5 (60%) · Genre 5/5 (100%)** |

Both backends correctly identify all five stories as horror. Verdict divergence
(Anthropic: `review` where OpenAI: `exclude`) reflects the models' different
calibration on borderline quality/completeness cases, not genre disagreement.

### Western — London corpus (`lcats/data/london/`, 5 stories)

Jack London's Yukon/frontier stories assessed as western. These stories are
adventure/outdoor fiction set in the frontier; genre disagreement is expected
and informative — it tests whether both backends detect the same edge cases.

Stories assessed (first 5 alphabetically):
1. `brown_wolf.json`
2. `day_s_lodging.json`
3. `love_of_life.json`
4. `negore_the_coward.json`
5. `story_of_keesh.json`

| Story | Anthropic verdict | OpenAI verdict | Genre match (A/O) |
|---|---|---|---|
| Brown Wolf | exclude | exclude | wrong / wrong ✓ |
| A Day's Lodging | exclude | exclude | wrong / wrong ✓ |
| Love of Life | exclude | exclude | wrong / wrong ✓ |
| Negore, the Coward | review | exclude | disputed / wrong ✗ |
| The Story of Keesh | exclude | exclude | wrong / wrong ✓ |
| **Agreement** | — | — | **Verdict 4/5 (80%) · Genre 4/5 (80%)** |

Both backends correctly reject London's frontier fiction as non-western in
four of five stories. "Negore, the Coward" is the one edge case: Anthropic
calls it `disputed` (frontier elements present, genre ambiguous) while OpenAI
calls it `wrong` outright.

## Interpreting Results

- **Verdict agreement ≥ 70%**: backends are broadly consistent; safe to use
  either for bulk corpus assessment.
- **Verdict agreement < 70%**: investigate whether prompt wording is the cause
  before scaling up; consider prompt tuning.
- **Genre match agreement**: expected to be high for Lovecraft/horror
  (unambiguous) and lower for London/western (frontier ≠ genre-western).
  Disagreement here tests whether both backends detect the same edge cases.

## Running the smoke test

The quickest way to run both backends across both genres is the orchestrator
script (run from the repo root):

```bash
# Activate conda env and set both API keys first:
#   cd lcats && scripts/develop && cd ..
#   export ANTHROPIC_API_KEY=sk-ant-...
#   export OPENAI_API_KEY=sk-...

python experiments/02_llm_backend_comparison/smoke_test.py
```

Optional flags:

```
--sample N              Stories per leg (default: 5)
--output DIR            Results directory (default: experiments/02_llm_backend_comparison/results)
--anthropic-model MODEL Anthropic model string (default: claude-opus-4-8)
--openai-model MODEL    OpenAI model string (default: gpt-4o-2024-08-06)
```

The script checks for a working `lcats` install and both API keys before
running anything, and prints an agreement-rate summary at the end.

---

## Manual smoke test

If you prefer to run each step individually — for debugging, partial reruns,
or adapting to a new corpus — here are the equivalent bash commands (run from
the repo root):

```bash
# Prerequisites
# 1. Activate your conda environment and install lcats:
#    cd lcats && scripts/develop && cd ..
#
# 2. Export API keys:
#    export ANTHROPIC_API_KEY=sk-ant-...
#    export OPENAI_API_KEY=sk-...

# --- Horror legs (Lovecraft corpus) ---

python experiments/02_llm_backend_comparison/run_comparison.py \
  --backend anthropic --model claude-opus-4-8 \
  --genre horror --corpus-dir lcats/data/lovecraft \
  --sample 5 --output experiments/02_llm_backend_comparison/results

python experiments/02_llm_backend_comparison/run_comparison.py \
  --backend openai --model gpt-4o-2024-08-06 \
  --genre horror --corpus-dir lcats/data/lovecraft \
  --sample 5 --output experiments/02_llm_backend_comparison/results

# --- Western legs (London corpus) ---

python experiments/02_llm_backend_comparison/run_comparison.py \
  --backend anthropic --model claude-opus-4-8 \
  --genre western --corpus-dir lcats/data/london \
  --sample 5 --output experiments/02_llm_backend_comparison/results

python experiments/02_llm_backend_comparison/run_comparison.py \
  --backend openai --model gpt-4o-2024-08-06 \
  --genre western --corpus-dir lcats/data/london \
  --sample 5 --output experiments/02_llm_backend_comparison/results

# --- Compare results ---

python experiments/02_llm_backend_comparison/compare_results.py \
  experiments/02_llm_backend_comparison/results/anthropic-claude-opus-4-8-horror-5.jsonl \
  experiments/02_llm_backend_comparison/results/openai-gpt-4o-2024-08-06-horror-5.jsonl

python experiments/02_llm_backend_comparison/compare_results.py \
  experiments/02_llm_backend_comparison/results/anthropic-claude-opus-4-8-western-5.jsonl \
  experiments/02_llm_backend_comparison/results/openai-gpt-4o-2024-08-06-western-5.jsonl
```

## Environment

- `ANTHROPIC_API_KEY` — required for Anthropic legs
- `OPENAI_API_KEY` — required for OpenAI legs
- Conda env: `base` (via `lcats/scripts/develop`)
