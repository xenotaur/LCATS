---
resolution: "Wiring landed in PR #349; the real 146-story gpt-oss:20b run and its three-way comparison (this PR) are both complete. Real measured results: 111.5 min wall-clock, $0 cost, 0 errors; 73.3% agreement with the metadata rules and 71.2% (104/146) directly against Opus (corrected from an initial 69.9% after a review finding - see Findings). Go/no-go: viable as a cheap first-pass filter for horror/science-fiction/mystery/adventure (83-100% agreement with Opus), not a safe substitute for fantasy/romance/humor/western (50-60%). See this file's own Findings section below."
blocked_reason: null
blocked: false
id: WI-LLM-0074
title: Wire run_prefilter.py's --validate to a local backend and run it over WI-GENRE-0004's 146-story sample
type: evaluation
status: resolved
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams:
  - WS-GENRE-EVIDENCE-SIDECARS
related_design:
  - project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md
  - project/work_items/resolved/WI-LLM-0066.md
  - project/work_items/resolved/WI-GENRE-0004.md
depends_on:
  - WI-GENRE-0004
  - WI-LLM-0066
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
  - change_default_backend_or_model
  - write_corpus_sidecars
  - promote_sidecars
  - modify_lcats_annotate
  - modify_lcats_promote
acceptance:
  - "experiments/05_metadata_genre_prefilter/run_prefilter.py's --validate mode gains an opt-in local OpenAI-compatible backend flag (e.g. --backend/--base-url), mirroring WI-LLM-0066's run_census.py wiring; omitting it leaves today's Anthropic-only behavior completely unchanged"
  - "The checkpoint fingerprint includes the effective endpoint/backend as well as model, so reusing the same --output directory against a different local endpoint cannot silently serve a cached classification from the wrong server"
  - "A real local-model run (e.g. gpt-oss:20b via Ollama) uses the exact same 146-story genre_balanced_manifest.jsonl sample WI-GENRE-0004 already validated with real claude-opus-4-8 - not a different or smaller sample - so the comparison is like-for-like on identical stories"
  - "Results are committed under experiments/05_metadata_genre_prefilter/results/ as a separate, additional output - never overwriting the existing Opus validation_results.jsonl/validation_summary.json"
  - "The written report states measured wall-clock/latency at 146-story scale (not extrapolated from a smaller sample), per-story and per-genre agreement between the local model and both the metadata-rule labels and the existing Opus results (a three-way comparison, not just local-vs-metadata), and a written go/no-go recommendation on whether this local model is a viable Opus substitute at this sample's scale"
  - "Zero real API dollar cost anywhere in this item - the committed summary reports $0 for every local-endpoint call, matching WI-LLM-0066's own zero-cost requirement"
  - "scripts/test passes with no new failures"
  - "lrh validate reports 0 errors"
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - experiments/05_metadata_genre_prefilter/run_prefilter.py
  - experiments/05_metadata_genre_prefilter/README.md
  - experiments/05_metadata_genre_prefilter/results/
---

# Work Item: WI-LLM-0074

## Summary

`run_prefilter.py`'s `--validate --run-real-validation` path currently only
supports real, billed `claude-opus-4-8` calls (`AnthropicBackend()` is
hardcoded). This item wires in an opt-in local OpenAI-compatible backend,
mirroring `WI-LLM-0066`'s `--base-url` wiring for `run_census.py`, then runs
a real local-model pass (e.g. `gpt-oss:20b` via Ollama) over the *exact
same* 146-story `genre_balanced_manifest.jsonl` sample `WI-GENRE-0004`
already validated with real Opus calls - producing a genuine three-way
comparison (metadata rules vs. Opus vs. local model) on identical stories,
at zero additional dollar cost.

## Problem / Context

`WI-LLM-0066` (PR #298) proved a local model can be wired into this
project's genre-classification tooling for free, but it ran against a
*different*, disjoint 20-story sample (chosen to match the earlier
`WI-ASSESS-0051` Claude 20-story census, not `WI-GENRE-0004`'s later
146-story genre-balanced sample). Checked directly: zero story-ID overlap
between that 20-story set and the 146-story sample. Its own result (18/20,
90% agreement) is informative but does not answer whether a local model
agrees with Opus on the specific stories this project actually selected and
paid to validate for the Worldcon paper.

`run_prefilter.py --validate` itself has no local-backend option today -
confirmed by reading the code: `_run_validate_mode()` imports and
constructs `anthropic_backend.AnthropicBackend()` unconditionally, with no
`--backend`/`--base-url` flag anywhere in `parse_args()`. `run_census.py`
already has this wiring (`WI-LLM-0066`); this item brings the same pattern
to `run_prefilter.py`, whose real Opus validation results
(`experiments/05_metadata_genre_prefilter/results/full_scan/`) already
exist as the comparison target.

### Duplication search
- In-repo: `WI-LLM-0066` covers local-backend wiring for `run_census.py`
  only, over a non-overlapping 20-story sample - it does not touch
  `run_prefilter.py` or the 146-story sample. `PROP-ERW-LOCAL-MODEL-EVALUATION`
  (still `proposed`) covers local-model infrastructure for the ERW pipeline
  broadly, not this experiment's genre-validation path specifically. No
  existing item wires a local backend into `run_prefilter.py` or runs one
  over `WI-GENRE-0004`'s specific sample.
- Sibling repos / external libraries: none identified.
- Recommendation: proceed, extending `run_prefilter.py` following
  `WI-LLM-0066`'s already-proven wiring pattern rather than inventing a new
  one.

### Demand search
- Work items: `WI-GENRE-0004`'s own Problem/Context already notes
  `WI-LLM-0066`'s local alternative "doesn't clearly resolve this either"
  precisely because of the sample mismatch - a direct signal this
  comparison was left open, not resolved.
- User request: this item originates directly from a live question in the
  session that landed `WI-GENRE-0004`'s real validation evidence - "Do we
  have a local model run paralleling the Opus run?" - answered no, with
  this item proposed as the follow-up.
- Recommendation: proceed.

## Scope

- Add an opt-in local-backend flag to `run_prefilter.py`'s `--validate`
  mode, following `run_census.py`'s existing `--base-url`/`--backend`
  pattern rather than inventing a new one.
- Extend the checkpoint fingerprint to include the effective
  endpoint/backend.
- Run a real, gated local-model validation pass over the identical
  146-story sample already used for the Opus run.
- Report a three-way agreement comparison (metadata rules / Opus / local
  model) and a go/no-go recommendation.

## Required Changes

1. **`experiments/05_metadata_genre_prefilter/run_prefilter.py`**: add a
   local-backend flag (e.g. `--backend {anthropic,openai}` plus
   `--base-url`) to `--validate`'s argument parser, threaded into
   `_run_validate_mode()`/`run_validation()` so the backend construction is
   no longer hardcoded to `AnthropicBackend()`. Omitting the new flag(s)
   must leave existing behavior (real Opus calls) completely unchanged.
   `_validation_fingerprint()` must incorporate the effective
   endpoint/backend, mirroring `run_census.py`'s own fingerprint fix for
   the identical concern (`WI-LLM-0066`).
2. **`experiments/05_metadata_genre_prefilter/run_prefilter.py`** (real
   run): a gated local-model run against the existing
   `genre_balanced_manifest.jsonl` (no new selection step - reuse
   `WI-GENRE-0004`'s manifest as-is). Writes its results as a separate,
   additional output alongside (not overwriting) the existing Opus
   `validation_results.jsonl`/`validation_summary.json` - e.g. a
   backend/model-qualified filename, following `run_census.py`'s own
   `census_gpt_oss_20b_http_localhost_11434_v1_*` naming convention for
   its analogous local-run outputs.
3. **`experiments/05_metadata_genre_prefilter/run_prefilter_test.py`**:
   tests for the new backend flag (opt-in, default-unchanged), the
   fingerprint's endpoint sensitivity, and that the local run's output
   doesn't clobber the existing Opus evidence files.
4. **`experiments/05_metadata_genre_prefilter/README.md`**: document the
   new local-backend flag and its output files.
5. A written report (in the README, the WI's own Findings, or a dedicated
   results file) stating measured wall-clock at 146-story scale, per-story
   and per-genre three-way agreement, and a go/no-go recommendation.

## Non-Goals

- Do not promote sidecars into `corpora/` - remains a separate, later-gated
  step per `WI-GENRE-0002`/`0003`/`0004`'s own Non-Goals.
- Do not change `run_prefilter.py`'s or `lcats assess`'s *default* backend
  or model - the local backend is opt-in only.
- Do not re-run or re-select the genre-balanced sample - reuse
  `WI-GENRE-0004`'s existing 146-story manifest exactly as-is.
- Do not modify `run_census.py` - its own local-backend wiring
  (`WI-LLM-0066`) is the pattern to follow, not a file to change.
- Do not run the real local-model sample without explicit user go-ahead,
  same gate discipline `WI-LLM-0066` and `WI-GENRE-0004` both used (even
  though this run is free, a full 146-story local-model run still takes
  real wall-clock time worth confirming before committing to).

## Acceptance Criteria

(see frontmatter `acceptance:` - kept in sync)

## Findings

Real, gated `gpt-oss:20b` (via Ollama, `http://localhost:11434/v1`)
validation ran against all 146 selected stories
(`--validate --run-real-validation --backend openai --base-url
http://localhost:11434/v1 --model gpt-oss:20b`), 2026-08-22: 0 errors, 0
aborts, real cost **$0**, real measured wall-clock **111.5 minutes**
(not extrapolated - `run_start`/`run_end` timestamps in
`validation_gpt_oss_20b_http_localhost_11434_v1_run_log.jsonl`).

Preceded by a 3-story smoke test (separate scratch run, not part of this
PR's diff) confirming the mechanics worked for real before committing to
the full run - 1m28s for 3 stories, output correctly written to
qualified filenames alongside (not overwriting) the Opus evidence.

**Correction (review finding, Copilot, this PR):** the first committed
version of this run's results recorded `detected_genre: "science_fiction"`
(underscore) for 3/146 stories - a real local-model quirk (`gpt-oss:20b`
via Ollama does not enforce `ASSESSMENT_TOOL`'s own JSON-schema `enum`
the way Anthropic's strict tool-calling does) that isn't the canonical
`"science fiction"` (space) `VALID_GENRES` value, so those 3 stories
silently failed the metadata-rules membership check and were miscounted
as disagreements. Fixed at the source
(`lcats.analysis.corpus.assess._canonicalize_detected_genre()`, new,
normalizes any underscore variant and falls back to `"other"` for
anything still unrecognized) and re-run for just those 3 stories
(resuming from checkpoint for the other 143 - no other story was
affected). The numbers below are the corrected ones.

**Three-way comparison** (metadata rules / Opus / local model), computed
directly from the two committed `validation_results.jsonl` files:

| | agreement |
|---|---|
| `gpt-oss:20b` vs. metadata rules | 73.3% (107/146) |
| `gpt-oss:20b` vs. Opus directly | **71.2% (104/146)** |
| (for reference) Opus vs. metadata rules | 87.0% (127/146) |

Per-genre, local-vs-Opus:

| genre | agreement |
|---|---|
| horror | 95% (19/20) |
| science fiction | 95% (19/20) |
| adventure | 83% (5/6) |
| mystery | 80% (16/20) |
| western | 60% (12/20) |
| fantasy | 60% (12/20) |
| romance | 55% (11/20) |
| humor | 50% (10/20) |

**Go/no-go recommendation**: `gpt-oss:20b` is a viable, free, fast
first-pass filter for horror/science-fiction/mystery/adventure, where it
tracks Opus closely (80-95% agreement). It is **not** a safe drop-in
substitute for fantasy/romance/humor/western (50-60% agreement) - the
disagreements there skew toward the local model defaulting to a generic
`other` label where both Opus and the metadata rules agree on something
specific (e.g. `anderson/false_collar`: rules+Opus say `fantasy`, local
says `other`), rather than confidently picking a different-but-plausible
genre. This matches `WI-LLM-0066`'s own prior finding that genre
detection is this candidate's most reliable stage, refined here with a
genre-by-genre breakdown that finding didn't have.

Per-story evidence (both the metadata-rule and local `model_detect`
assessments, `genre-sidecar-v1`-validated) is in
`experiments/05_metadata_genre_prefilter/results/full_scan/validation_gpt_oss_20b_http_localhost_11434_v1_results.jsonl`;
aggregate/per-genre numbers (local-vs-metadata-rules) in the sibling
`_summary.json`; the full event-by-event run log in `_run_log.jsonl`.

## Validation

- scripts/format --check --diff
- scripts/lint
- scripts/test
- lrh validate
- Real local-model validation run only after explicit go-ahead, same
  discipline as the existing Opus `--run-real-validation` gate

## Risk Notes

- **Local-model latency at 146-story scale is unmeasured** -
  `WI-LLM-0066`'s only multi-story measurement was at 20-story scale; this
  item's own acceptance criteria require a real 146-story measurement, not
  an extrapolation.
- **Result may simply confirm the existing 18/20 finding at larger scale,
  or may diverge** - either outcome is a valid, useful result; this item
  does not presuppose which.
- **Depends on local Ollama/model availability** - if `gpt-oss:20b` (or
  whichever local model is used) is not reachable in the execution
  environment, this item is blocked on that external dependency rather
  than a code gap; report and stop rather than substituting a different,
  unvetted local model silently.
