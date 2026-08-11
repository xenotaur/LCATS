---
resolution: null
blocked_reason: null
blocked: false
id: WI-LLM-0066
title: Wire run_census.py to a local OpenAI-compatible backend and evaluate gpt-oss:20b at genre-census scale
type: evaluation
status: proposed
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams: []
related_design:
  - project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md
  - lcats/experimental/model_comparison/ollama_gpt_oss_20b/README.md
  - lcats/project/work_items/proposed/WI-ASSESS-0051.md
  - lcats/project/work_items/resolved/WI-LLM-0058.md
depends_on: []
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - run_local_sample_before_user_go_ahead
  - run_full_local_census_before_evaluation
  - change_default_backend_or_model
  - modify_erw_pipeline_routing
acceptance:
  - "experiments/04_genre_census/run_census.py gains a --base-url flag (opt-in only) threaded through _build_backend so --backend openai can point at any OpenAI-compatible endpoint (e.g. Ollama's http://localhost:11434/v1) instead of api.openai.com; omitting it leaves today's default behavior (real OpenAI/Anthropic) completely unchanged"
  - "A real gpt-oss:20b sample run analogous to WI-ASSESS-0051's --sample-size 20 (same population-weighted sampling logic, same corpus, comparable N) is executed via the new flag and its results (per-story records + summary) are committed under experiments/04_genre_census/results/"
  - "The sample's measured wall-clock/latency at multi-story scale is reported - not just extrapolated from the 3 single-story benchmark-harness latencies already on record in lcats/experimental/model_comparison/ollama_gpt_oss_20b/README.md"
  - "The sample's detected_genre distribution is compared against the existing Claude 20-story sample (experiments/04_genre_census/results/census_sample_stories.jsonl on the xenotaur/chore/wi-assess-0051-sample-results branch) for agreement/plausibility - not just genre-schema-call success"
  - "A written go/no-go recommendation is produced: is gpt-oss:20b via this wiring viable for a full local genre census, and if so, a projected full-corpus (~1,868-story) wall-clock estimate"
  - "Zero real API dollar cost anywhere in this item - the sample run is 100% local compute"
  - "scripts/test passes with no new failures"
  - "lrh validate reports 0 errors"
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - experiments/04_genre_census/run_census.py
  - experiments/04_genre_census/README.md
  - experiments/04_genre_census/results/
---

## Summary

Close the gap between "gpt-oss:20b reliably calls the genre-detection
tool on one story" (proven in `lcats/experimental/model_comparison/
ollama_gpt_oss_20b/README.md`, 3/3 success via the real production
`assess_story()` path) and "gpt-oss:20b is a viable local backend for
WI-ASSESS-0051's genre census." Two parts: (1) a small, opt-in
`--base-url` flag so `run_census.py` can actually reach a local
OpenAI-compatible endpoint, and (2) a real multi-story, multi-genre
sample run through that flag to get accuracy and wall-clock evidence at
a scale closer to the actual ~1,868-story corpus, mirroring how
WI-ASSESS-0051 gated its own `--full` run behind a `--sample-size 20`
step.

## Problem / Context

`experiments/04_genre_census/run_census.py`'s `_build_backend()`
(`run_census.py:207-217`) only supports `"anthropic"`/`"openai"`, and
the `"openai"` path constructs `OpenAIBackend()` with no `base_url`,
which defaults straight to `api.openai.com`
(`lcats/src/lcats/llm/openai_backend.py:15-25`). `OpenAIBackend` itself
already supports pointing at a local runtime via `base_url` - its own
docstring names Ollama's `http://localhost:11434/v1` explicitly - but
`run_census.py` never exposes that. There is no `--base-url` (or
equivalent) CLI flag today (`run_census.py:441-453`'s full argparse
block).

Separately, `lcats/experimental/model_comparison/ollama_gpt_oss_20b/
README.md`'s "Genre detection - 3/3 success" section (via
`benchmark_genre.py`, which calls the same `corpus_assess.assess_story()`
path `run_census.py` uses, against a real whole story) found genre
detection reliable for `gpt-oss:20b`, matching `ollama_qwen3_8b`'s own
"hybrid-viable" verdict for this stage
(`project/design/proposals/proposed/erw-local-model-evaluation/
00_proposal.md:298-299`). All 3 runs used the *same* single story
(Sherlock Holmes, genre `mystery`), so this establishes reliability but
not multi-genre accuracy or corpus-scale wall-clock behavior.

### Duplication search
- In-repo: no existing `--base-url`/local-endpoint support in
  `run_census.py`, and no existing multi-story local-model sample run
  against the genre census specifically (checked via GitHub code search
  for `base-url run_census` and `gpt-oss run_census` - no hits).
- The governing proposal (`erw-local-model-evaluation/00_proposal.md`)
  explicitly lists "Does not extend the benchmark harness ... to [genre
  census] production tooling" among its own Non-Goals (`00_proposal.md`
  Non-Goals section) - this item is exactly that follow-up, not a
  duplicate.
- `WI-LLM-0065` (proposed, open) covers `gpt-oss:20b` *entity extraction*
  production-grounding specifically - a different pipeline stage,
  non-overlapping with this item's genre-only scope.
- Sibling repos / external libraries: none identified.
- Recommendation: proceed.

### Demand search
- Work items: none found requesting this beyond this session's own
  feasibility discussion (grounded against `ollama_gpt_oss_20b/README.md`
  and `run_census.py`'s current source).
- Proposals, backlog: the governing proposal's own Non-Goals name this
  exact gap as future follow-on work, not yet scoped as its own item.
- Recommendation: proceed; this is the natural next step the existing
  evidence trail points to.

## Scope

- Add a `--base-url` flag to `run_census.py`, threaded through
  `_build_backend()` so the `"openai"` backend path can be pointed at a
  local OpenAI-compatible endpoint. Omitting the flag must leave
  existing behavior (real `api.openai.com`) completely unchanged - this
  is additive, not a default-changing edit.
- Run a population-weighted `--sample-size` run (comparable N to
  WI-ASSESS-0051's 20-story sample) against `gpt-oss:20b` via the new
  flag, gated on explicit go-ahead before spending any real wall-clock
  time (see `forbidden_actions` - even though $0 API cost, a multi-story
  local run still commits real machine time and should not start
  silently).
- Compare the resulting `detected_genre` distribution against the
  existing Claude sample for plausibility/agreement, and report real
  multi-story latency (not the single-story extrapolation this item's
  Problem/Context section flags as thin evidence).
- Write a go/no-go recommendation on `gpt-oss:20b`'s viability for a
  future full local census run, including a projected full-corpus
  wall-clock estimate - explicitly not authorizing that full run itself.

## Required Changes

1. `experiments/04_genre_census/run_census.py`: add `--base-url` (default
   `None`) and thread it into `_build_backend()` - when given alongside
   `--backend openai`, construct `openai_backend.OpenAIBackend(api_key=...,
   base_url=args.base_url)` instead of the no-args default. Follow the
   existing benchmark script's convention
   (`ollama_gpt_oss_20b/benchmark_genre.py`: `api_key="ollama"`) for a
   sensible placeholder key when pointed at a keyless local runtime.
   Validate `--base-url` is only accepted with `--backend openai` (clear
   error otherwise, matching the script's existing fail-fast style for
   flag combinations).
2. `experiments/04_genre_census/README.md`: document the new flag and a
   worked example pointing at a local Ollama instance running
   `gpt-oss:20b`.
3. `experiments/04_genre_census/results/`: the `gpt-oss:20b` sample run's
   committed output (per-story records + summary), clearly named/tagged
   to avoid colliding with or overwriting the existing Claude sample's
   `census_sample_*` files (e.g. a candidate-scoped filename or
   subdirectory).
4. A written go/no-go finding, in this item's own execution record at
   minimum (a short addition to `run_census.py`'s README is also
   reasonable if it has lasting reference value).

## Non-Goals

- Do not run a `--full` local genre census - that is a separate, later,
  explicitly human-gated decision informed by this item's findings, not
  authorized here.
- Do not modify entity-extraction or segmentation production routing -
  `WI-LLM-0065` (open) owns `gpt-oss:20b`'s entity-extraction production
  readiness; this item is genre-only.
- Do not change `run_census.py`'s default backend or model - Claude
  remains the default; `--base-url`/local-model usage is strictly
  opt-in.
- Do not build a general-purpose multi-provider configuration system - a
  minimal `--base-url` flag is sufficient, matching `OpenAIBackend`'s
  own already-existing, narrowly-scoped support for this.
- Do not spend real API dollars - this item is 100% local compute by
  design.

## Acceptance Criteria

(see frontmatter `acceptance:` - kept in sync)

## Validation

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `python experiments/04_genre_census/run_census.py --sample-size 5
  --backend openai --base-url http://localhost:11434/v1 --model
  gpt-oss:20b --dry-run` (zero-cost smoke test of the new flag/validation
  logic, from the repository root)
- The real `gpt-oss:20b` sample run itself (requires a local Ollama
  instance with `gpt-oss:20b` pulled, real wall-clock time - go-ahead
  required per `forbidden_actions`)

## Risk Notes

- **Real machine-time commitment, even at $0 API cost.** A ~20-story
  local sample could take significant wall-clock time depending on
  hardware (the 3 known single-story latencies ranged 8.3-40.5s) - this
  should not start without explicit go-ahead, mirroring the discipline
  WI-ASSESS-0051 applied to its own paid sample.
- **Thin existing evidence base.** All 3 prior genre-detection runs used
  the identical single story/genre (Sherlock Holmes, `mystery`) - this
  item's own multi-story, multi-genre sample is what actually tests
  whether the "reliable" verdict holds across the corpus's real genre
  and length diversity, not an assumption to inherit uncritically.
- **`OpenAIBackend`'s `strict` tool-schema handling and Ollama's
  OpenAI-compatible endpoint may behave differently under load or across
  many sequential calls** than the single-call benchmark evidence shows -
  the sample run's own excluded/failed count is the real signal here,
  not the harness's 3/3.
