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
  - lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md
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
  - "A real gpt-oss:20b sample run uses the exact same story IDs (same --seed against the same corpus state, or an explicitly pinned story list) as the existing Claude 20-story sample - not just a comparable-N sample of possibly different stories - and its results (per-story records + summary) are committed under experiments/04_genre_census/results/"
  - "The sample's measured wall-clock/latency at multi-story scale is reported - not just extrapolated from the 3 single-story benchmark-harness latencies already on record in lcats/experimental/model_comparison/ollama_gpt_oss_20b/README.md"
  - "Per-story detected_genre agreement/disagreement against the existing Claude 20-story sample is reported story-by-story (e.g. N/20 exact matches, with each disagreement named) - matching aggregate genre-distribution counts alone is not sufficient, since two runs can have identical counts while disagreeing on every individual story"
  - "A written go/no-go recommendation is produced: is gpt-oss:20b via this wiring viable for a full local genre census, and if so, a projected full-corpus (~1,868-story) wall-clock estimate"
  - "Zero real API dollar cost anywhere in this item - the sample run is 100% local compute, and the committed summary must actually report $0 for every local-endpoint call rather than falling through to run_census.py's existing (non-local) pricing table's default price"
  - "run_census.py's checkpoint fingerprint includes the effective endpoint (e.g. --base-url) as well as model/backend, so reusing the same --output directory against a different local endpoint cannot silently serve a cached classification from the wrong server"
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
(`lcats/project/design/proposals/proposed/erw-local-model-evaluation/
00_proposal.md:298-299`). All 3 runs used the *same* single story
(Sherlock Holmes, genre `mystery`), so this establishes reliability but
not multi-genre accuracy or corpus-scale wall-clock behavior.

**The existing Claude 20-story sample this item compares against is not
on `main`.** `census_sample_stories.jsonl`/`census_sample_summary.json`
exist only on the unmerged `xenotaur/chore/wi-assess-0051-sample-results`
branch (commit `8431780b`, no open PR) - an implementer must fetch that
branch's data explicitly (or re-derive the same story set via the same
`--seed`) before the per-story comparison acceptance criteria can be
satisfied; it will not simply be present in a fresh checkout of `main`.

### Duplication search
- In-repo: no existing `--base-url`/local-endpoint support in
  `run_census.py`, and no existing multi-story local-model sample run
  against the genre census specifically (checked via GitHub code search
  for `base-url run_census` and `gpt-oss run_census` - no hits).
- The governing proposal (`lcats/project/design/proposals/proposed/
  erw-local-model-evaluation/00_proposal.md:698-699`) explicitly declined
  to add local-backend wiring to a production script as part of its own
  scope - "Does not change `run_pilot.py`'s default model or add a
  `--backend local`/similar flag" - leaving that as deliberately
  unscoped future work, not something already covered elsewhere. This
  item is the `run_census.py` analog of that same deferred wiring, not a
  duplicate of anything the proposal itself did.
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
- Fold the effective endpoint into `_fingerprint()` alongside
  model/backend/classifier-version/raw-text-hash, so a checkpoint from
  one `--base-url` is never silently reused for a different one under
  the same `--output` directory.
- Ensure a local-endpoint call's reported cost is genuinely $0, not
  `run_census.py`'s existing pricing table's fallback default (currently
  the most expensive known tier, meant for an *unrecognized real
  provider model*, not a local/free one) - either add local model names
  to the pricing table at `(0.0, 0.0)`, or special-case any call routed
  through `--base-url` to report zero cost regardless of model name.
- Run a `--sample-size` run against `gpt-oss:20b` via the new flag that
  draws the *same* stories as the existing Claude 20-story sample (same
  `--seed`, or an explicitly pinned story list) - a comparable-N sample
  of different stories cannot establish per-story agreement, only
  coincidental aggregate-count similarity - gated on explicit go-ahead
  before spending any real wall-clock time (see `forbidden_actions` -
  even though $0 API cost, a multi-story local run still commits real
  machine time and should not start silently).
- Report per-story `detected_genre` agreement/disagreement against the
  Claude sample (not just aggregate distribution comparison, which two
  runs can share while disagreeing on every individual story), and
  report real multi-story latency (not the single-story extrapolation
  this item's Problem/Context section flags as thin evidence).
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
   flag combinations). Also: (a) fold `base_url` into `_fingerprint()`'s
   returned dict so checkpoints are endpoint-scoped, and (b) ensure any
   call routed through `--base-url` reports $0 cost rather than falling
   through to `_price_for_model()`'s existing default (currently the most
   expensive known real-provider tier) - both are correctness bugs in the
   naive implementation, not follow-up polish.
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

- **Reference data lives on an unmerged branch, not `main`.** The
  existing Claude sample this item compares against
  (`xenotaur/chore/wi-assess-0051-sample-results`, commit `8431780b`) has
  no open PR - fetch it explicitly, or note in the go/no-go finding if it
  was re-derived instead (e.g. re-running the same `--seed` against
  `main`'s current corpus state, which should reproduce the same story
  set deterministically per `build_population_weighted_sample`).
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
