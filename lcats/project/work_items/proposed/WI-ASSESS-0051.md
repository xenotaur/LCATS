---
resolution: null
blocked_reason: null
blocked: false
id: WI-ASSESS-0051
title: Run current-classifier full-corpus genre survey (Gap 2)
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
  - project/design/event-role-world-genre-target-reconciliation.md
depends_on:
  - WI-LLM-0058
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - implement_pilot_rescope
  - run_full_corpus_before_cost_approval
  - run_paid_sample_before_user_go_ahead
acceptance:
  - "A small, population-weighted stratified real-API sample (~20-30 stories, sampled proportionally to each collection's real share of the corpus, not equally per collection) is run through detect-mode assess_story() and per-story token counts, latency, and $ cost are measured"
  - "The sample's measured per-story cost/latency is extrapolated to the full ~1,868-story corpus via the population-weighted sample mean and reported to the user as a total $ and wall-clock estimate BEFORE any full-corpus run begins"
  - "The full-corpus run proceeds only after explicit user go-ahead on the cost estimate - a human checkpoint inside this work item's own execution, not implicit"
  - "The full-corpus survey uses a resumable, checkpointed design via lcats.utils.checkpoint, so an interruption doesn't require redoing already-completed stories"
  - "Failed assessments (result.error populated) are excluded from genre/classification counts only (both the cost-estimate sample's and the final census's), never counted as a genuine other classification, and the excluded count/reasons are reported explicitly rather than silently absorbed - but a failed-but-billed call's real token usage (forwarded via the generalized backend/assess.py fix, see Non-Goals carve-out) still counts toward the cost estimate"
  - "Final output includes both an aggregate per-genre story count across all 8 VALID_GENRES values plus other, AND a per-story record (identity, detected genre, confidence, classifier/model identity, failure status), committed under experiments/04_genre_census/results/"
  - "Findings state plainly whether corpus representation is adequate per genre for the paper's eventual stratified sampling needs, without deciding sourcing/ingestion follow-up"
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
  - experiments/README.md
  - lcats/src/lcats/analysis/corpus/assess.py
  - lcats/src/lcats/llm/backend.py
  - lcats/src/lcats/llm/anthropic_backend.py
  - lcats/src/lcats/llm/openai_backend.py
---

# Work Item: WI-ASSESS-0051

## Summary

Run `lcats assess`'s current (8-genre) classifier in detect mode across
the full corpus (~1,868 stories) to get an authoritative current per-genre
count, gated behind a real small-sample cost estimate and a resumable
checkpointed design given the real API cost and wall-clock duration
involved.

## Problem / Context

`project/design/event-role-world-genre-target-reconciliation.md`'s "Gap 2"
identifies this survey as a prerequisite before sizing any stratified
Event-Role-World annotation pilot for the Worldcon 2026 paper: the current
8-genre `VALID_GENRES` classifier (landed via `WI-ASSESS-0031`, PR #224)
has never been run at corpus scale. The one full-corpus classification
that exists, `experiments/01_classify_corpora/results/summary.tab`
(2025-10-19), used a different, older, open-vocabulary classifier — its
counts are a rough compositional signal only and must not be reused as
authoritative for the current 8-genre scheme.

### Duplication search
- In-repo: no existing full-corpus survey under the current 8-genre
  classifier found. `experiments/01_classify_corpora/` uses a different,
  older classifier (see above) — not a duplicate to extend, a distinct
  historical artifact.
- Sibling repos: none identified.
- External libraries: none identified.
- Recommendation: proceed.

### Demand search
- Work items: none found requesting this beyond the reconciliation
  design doc's own Gap 2 pointer (`project/design/backlog.md`).
- Proposals: none found.
- Backlog: `project/design/backlog.md`'s "`VALID_GENRES` still has 4
  genres" entry (now marked fixed) lists this as one of two genuinely
  unscoped follow-ups. This work item resolves that backlog pointer for
  Gap 2 specifically; Gap 3 (re-scoping `WI-EVENT-0030`'s pilot) remains
  separately unscoped, depends on this item.
- Recommendation: proceed; this is the backlog's own recommended next
  step.

## Scope

- Build a small survey script that runs `assess.assess_story()` in detect
  mode (no `--genre`) across the corpus, using the canonical bucket-story
  discovery (`discovery.find_json_files`) already used by `lcats assess`
  and `run_pilot.py`.
- Measure real per-story cost/latency from a small sample before
  committing to a full run.
- Make the full run resumable via the project's existing checkpoint
  helper, since ~1,868 sequential API calls carries real duration and
  interruption risk.
- Report per-genre counts across the 8 `VALID_GENRES` values plus
  `"other"`.

## Required Changes

1. **`experiments/04_genre_census/run_census.py`** (new): following
   `experiments/03_cross_segment_relation_pilot/run_pilot.py`'s
   established house style, **except** for its `--data-dir` default —
   `run_pilot.py`'s own default (`"lcats/data"`) does not exist in this
   checkout (`data/` regenerates from cache and isn't checked in). The
   actual populated corpus (1,868 canonical `story.json` files, confirmed
   via `find corpora -iname story.json | wc -l`) lives at `corpora/`
   (repo-root-relative). This script's own `--data-dir` must default to
   `corpora` (or the equivalent path from wherever it's actually invoked
   from — see the Validation section below for the exact invocation
   directory), and must validate the discovered story count is nonzero
   (and roughly matches the expected ~1,868) before proceeding with any
   paid sample or full run — a silent zero-story discovery must never be
   allowed to "succeed" with an empty result.
   - Story discovery via `discovery.find_json_files`, not the broader
     `discovery.find_corpus_stories` (per this project's own established
     convention — the broader selector is wrong whenever "is this a real
     story" is the actual question).
   - One stage, `"genre_census"`, checkpointed via `lcats.utils.checkpoint`
     (`read_checkpoint`/`write_checkpoint`), keyed by a collection-qualified
     story identity (matching `run_pilot.py`'s own `_story_identity` fix
     for the bucket-layout stem-collision problem — every bucket file is
     literally named `story.json`, so `path.stem` alone is useless as an
     identity).
   - Fingerprint includes model, backend, a hash of the raw story text
     (per the existing "hash actual input, not just config" pattern — see
     `feedback_checkpoint_fingerprint_must_hash_actual_input`), so a story
     corrected in place invalidates its own cached classification, **and**
     a classifier-version marker analogous to `run_pilot.py`'s own
     `_CLASSIFIER_VERSION` (`experiments/03_cross_segment_relation_pilot/run_pilot.py:226`),
     folded in the same way its `genre_detect` fingerprint does
     (`run_pilot.py:390-396`) — so a prompt/schema change to `assess.py`'s
     classifier between runs correctly invalidates stale cached
     classifications instead of silently mixing old- and new-classifier
     results in what's supposed to be a single-classifier-version census.
   - Calls `assess.assess_story()` with `genre=""` (detect mode). Checks
     `result.error` on every call — `assess_story()` does not raise on
     preflight/API/tool-parsing failure; it returns an `AssessmentResult`
     with `error` populated and `detected_genre` silently defaulted to
     `"other"` (`assess.py:368-377,401-410`). A failed call must be
     recorded as a failure (retry candidate or excluded run, matching
     `run_pilot.py`'s own established `extraction_errors`-exclusion
     pattern — not a hard requirement that every one of ~1,868 sequential
     calls succeeds before the census can be finalized, which is stricter
     than this project's own established convention for exactly this kind
     of batch operation) and must **never** be counted as a genuine
     `"other"` classification in the per-genre census. The excluded/failed
     count and reasons must be reported explicitly alongside the final
     census (not silently absorbed into a smaller total), and a high
     exclusion rate — or any pattern suggesting failures aren't
     reasonably random (e.g. correlated with a specific collection or
     story length) — must itself be flagged as a data-quality concern in
     the findings, since a biased exclusion pattern could skew the
     per-genre counts.
   - A `--sample-size N` mode that runs only N stories, stratified by
     collection **and population-weighted** — not an equal count per
     collection, since `mass_quantities` alone holds 1,659 of the corpus's
     1,868 stories (89%) with the rest split across 11 much smaller
     collections (5-62 stories each); an equal-per-collection sample would
     systematically misrepresent the corpus-wide average cost per story,
     particularly given body length (and therefore token cost) varies by
     collection. Reports measured cost ($ and latency) extrapolated to the
     full corpus via this population-weighted mean — this is the
     acceptance-gating output, meant to be reviewed before a full run.
   - A separate, **mandatory** `--full` flag is required to run the
     complete corpus (resuming from any existing checkpoints). Invoking
     the script with neither `--sample-size` nor `--full` must exit
     immediately with usage information — omitting both flags must never
     silently default to starting the ~1,868-call paid run, since that
     would bypass the cost gate this item exists to enforce.
   - A small, local, documented pricing constant for the model in use
     (there is no shared pricing/cost module anywhere in this codebase —
     `PROP-LCATS-PIPELINE-CHECKPOINTING`'s Category E1,
     model-invocation-cost tracking, was explicitly deferred and remains
     unbuilt) — do not build a shared pricing module as part of this item,
     a local constant scoped to this script is sufficient.
2. **`experiments/04_genre_census/README.md`** (new): usage, the
   cost-estimation methodology and how to read its output, expected
   results format, and a note that the full run must not proceed without
   reviewing the sample-based cost estimate first.
3. **`experiments/README.md`**: register the new `04_genre_census`
   experiment, per the existing table's convention.
4. **`experiments/04_genre_census/results/`**: the actual census output,
   populated once the full run executes and is committed. Must include
   **both** an aggregate per-genre summary table AND a per-story record
   (stable story identity, detected genre, confidence, classifier/model
   identity, failure status) for every discovered story — an aggregate-only
   summary is not sufficient, since
   `project/design/event-role-world-genre-target-reconciliation.md:274-277`
   requires the eventual stratified pilot (Gap 3) to draw its per-genre
   sample *from this census*, which is impossible from counts alone
   without re-running ~1,868 paid classifications or inspecting
   undocumented checkpoint internals.
5. **`lcats/src/lcats/llm/backend.py`, `anthropic_backend.py`,
   `openai_backend.py`, and `lcats/src/lcats/analysis/corpus/assess.py`**
   (generalized fix, see Non-Goals carve-out): review found three separate
   post-response failure paths that each discard already-available billed
   usage data the same way — `assess_story()`'s no-tool-result branch
   (`assess.py:368-376`); `TruncatedResponseError`, which both backends
   raise after hitting `max_tokens` and which already carries
   `input_tokens`/`output_tokens` by design (`backend.py:10-39`); and the
   plain `ValueError` both backends raise when no tool-use block/tool call
   comes back (`anthropic_backend.py:98-110`, `openai_backend.py:87-103`),
   which does *not* carry usage despite a real response having already
   been received at that point. Patching each path individually as review
   keeps finding new ones does not converge — implement a **general**
   fix instead: every exception the backend layer raises after a real
   response has already come back must carry that response's
   `input_tokens`/`output_tokens` forward (attach them to the exception
   instance, whether via a shared base/mixin or consistent attributes —
   exact mechanism is an implementation decision, not fixed here), and
   `assess_story()`'s exception handling must generically check for and
   forward usage data from *any* caught exception that carries it, rather
   than special-casing exception types one at a time. The fully generic
   fallback (exceptions with no reliable usage data at all, e.g. a network
   error before any response arrived) still defaults to zero usage — this
   fix is about not discarding data that already exists, not inventing
   data that doesn't. Audit the backend layer for any other post-response
   failure path beyond the three found here before considering this
   complete. Include tests covering all three known paths plus the
   generic forwarding mechanism itself.

## Non-Goals

- Do not re-scope or execute `WI-EVENT-0030`'s stratified pilot — that is
  Gap 3, a separate follow-up item that depends on this one.
- Do not modify `lcats assess`'s CLI surface, schema, or classifier
  prompts — those are already correct as of `WI-ASSESS-0031`.
  **Generalized carve-out:** review found three separate places (and
  possibly more not yet found) where the LLM backend layer or
  `assess_story()` discards real, already-available billed usage data on
  a post-response failure path — patching each one individually as review
  keeps surfacing new instances does not converge. In scope: a general
  fix ensuring every exception raised by the backend layer *after* a real
  API response has already been received carries that response's
  `input_tokens`/`output_tokens` forward, and `assess_story()`'s
  exception handling generically forwards usage from any caught exception
  that carries it (see Required Changes #5 for the specific known paths
  and the audit requirement). This carve-out does not extend to the
  fully generic no-response-at-all failure case (e.g. a network error
  before any request completed, which genuinely has no usage data to
  recover) or to any classifier/schema/prompt logic — it is about not
  discarding data that already exists, not inventing new instrumentation.
- Do not decide or implement any corpus-sourcing/ingestion follow-up even
  if a genre turns out under-represented by this survey's findings — that
  is a further, separately-scoped decision for a human to make from the
  results.
- Do not modify the Event-Role-World extractor pipeline.
- Do not build a shared, reusable cost/pricing-tracking module — that is
  `PROP-LCATS-PIPELINE-CHECKPOINTING`'s explicitly-deferred Category E1,
  out of scope here; a script-local pricing constant is sufficient for
  this one-off survey.
- Do not run the full corpus survey without first presenting the
  small-sample cost estimate to the user and getting explicit go-ahead —
  the sample step and the full-run step are gated, not one atomic action.

## Acceptance Criteria

- A small, population-weighted stratified real-API sample (~20-30 stories
  across multiple collections and body lengths, sampled proportionally to
  each collection's real share of the corpus, not equally per collection)
  is run and measured for real per-story token counts, latency, and $
  cost.
- The measured per-story cost/latency is extrapolated to the full
  ~1,868-story corpus via the population-weighted sample mean and reported
  as a total $ and wall-clock estimate before any full-corpus run begins.
- The full-corpus run proceeds only after explicit user go-ahead on that
  estimate.
- The full-corpus survey is resumable via `lcats.utils.checkpoint` —
  an interruption does not require redoing already-completed stories.
- Failed assessments (`result.error` populated) are excluded from
  **genre/classification counts** (both the cost-estimate sample's and
  the final census's) — never silently counted as a genuine `"other"`
  classification. They are **not** excluded from cost statistics: a
  failed-but-billed call's real token usage still counts toward the cost
  estimate, per the generalized backend/`assess.py` fix (see Non-Goals
  carve-out). The excluded/failed story count and reasons are reported
  explicitly alongside the final census, and a high or non-random-looking
  exclusion rate is flagged as a data-quality concern, not silently
  absorbed into a smaller total.
- Final output, committed under `experiments/04_genre_census/results/`,
  includes both an aggregate per-genre story count across all 8
  `VALID_GENRES` plus `"other"`, AND a per-story record (identity,
  detected genre, confidence, classifier/model identity, failure status)
  for every discovered story — required so the eventual stratified pilot
  (Gap 3) can draw its per-genre sample from this census directly.
- Findings state plainly whether corpus representation looks adequate per
  genre for the paper's eventual stratified sampling needs, without
  deciding sourcing/ingestion follow-up.
- `scripts/test` passes with no new failures.
- `lrh validate` reports 0 errors.

## Validation

`scripts/format`, `scripts/lint`, `scripts/test`, and `lrh validate` run
from the repository's `lcats/` directory, per `AGENTS.md`. `experiments/`
is a sibling of `lcats/`, not nested inside it — the census script
commands below are therefore given relative to the repository root, not
the `lcats/` working directory the commands above use:

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `python experiments/04_genre_census/run_census.py --sample-size 20
  --dry-run` (run from the repository root; zero-cost smoke test of file
  discovery and checkpoint wiring — `--dry-run` must be paired with a
  bounded mode like `--sample-size`, since `--dry-run` alone supplies
  neither `--sample-size` nor `--full` and the Required Changes above
  require that exact combination to exit immediately with usage
  information, not run anything)
- `python experiments/04_genre_census/run_census.py --sample-size 20`
  (run from the repository root; real API cost — requires
  `ANTHROPIC_API_KEY` and explicit go-ahead before running)
- Full-corpus run (`python experiments/04_genre_census/run_census.py
  --full`, from the repository root) only after the sample-size estimate
  above has been reviewed and approved

## Risk Notes

- **Real $ cost.** The small sample step itself costs real money; the
  full run costs meaningfully more (~1,868 calls at whatever the sample
  measures per-story). Do not run beyond the approved sample without a
  reviewed estimate — this is the entire reason this work item exists as
  a gated two-phase item rather than "just run `lcats assess` on
  `corpora/`."
- **Model choice affects cost meaningfully.** `lcats assess`'s own
  default model is `claude-opus-4-8`. Whether a cheaper model is
  acceptable for a classification-only census (versus the curation-lens
  use case the default was presumably chosen for) is worth flagging in
  the cost-estimate report, not deciding unilaterally in this item.
- **Wall-clock duration**, not just cost, is a real risk for ~1,868
  sequential calls (rate limits, network latency) — checkpointing
  mitigates data loss on interruption but not total runtime. Concurrency/
  batching is a reasonable stretch goal if the sample estimate shows
  duration is a practical blocker, but is not required by this item's
  acceptance criteria.
- **No existing pricing/cost-tracking utility.** Confirmed via repo-wide
  grep (`pricing`, `cost_per_token`, `PRICE`, `dollars_per` — zero hits
  outside this item's own planned script). The local pricing constant
  this item adds should be clearly documented as an approximation tied to
  the model in use at the time, not treated as a durable, reusable source
  of truth for future cost estimates.
- **`WI-LLM-0058` dependency.** A real, gated `--sample-size 20` run
  surfaced `ASSESSMENT_TOOL` `secondary_genre`-field corruption in 7/20
  stories (35%), consistent with an independent 24-story reproduction
  (`WI-ANNOTATE-0054`, 10/24 = 42%). `detected_genre` was clean in both
  runs, but a ~39% combined corruption rate on any field is a real signal
  worth a fix/mitigation decision before scaling ~93x to the full corpus
  — see `WI-LLM-0058` (`depends_on`), which must resolve (fix, mitigate,
  or an explicit documented decision not to) before `--full` proceeds.
