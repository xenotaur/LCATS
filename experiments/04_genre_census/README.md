# Full-Corpus Genre Census

**WI-ASSESS-0051** — Run `lcats assess`'s current (8-genre) classifier in
detect mode across the full corpus (~1,868 stories) to get an authoritative
current per-genre count, gated behind a real small-sample cost estimate.

## Status

**Sample cost estimate has run; `--full` is deferred.** A real
`--sample-size 20` run (see [Results](#results-2026-08-08) below) measured
$4.66 for 20 stories, extrapolating to ~$435/~4.2 hours for the full
~1,868-story corpus. Rather than spend that immediately, a cost-free
local-model (`gpt-oss:20b`, `WI-LLM-0066`) pilot will run first as an
alternative before deciding on the `--full` run. `--full` itself has not
run — `results/` contains only the sample data. Whoever eventually runs
`--full` should append its own "Results" section, following the format
sketched in [Expected Results Format](#expected-results-format).

## Results (2026-08-08)

Sample: 20 stories, `claude-opus-4-8`, population-weighted across 12
collections (17/20 from `mass_quantities`, matching its ~89% corpus
share). $4.66 measured, 0 excluded, 161s wall clock (~8s/story).
Extrapolated: **~$435 / ~251 minutes (~4.2 hours)** for the full corpus.

| Genre | Count |
|---|---|
| science fiction | 14 |
| humor | 3 |
| horror | 1 |
| fantasy | 1 |
| other | 1 |
| western / romance / mystery / adventure | 0 |

**Note on data quality:** 7/20 records show `secondary_genre` field
corruption (leaked tool-call-syntax fragments) — the defect `WI-LLM-0058`
later diagnosed and fixed via output sanitization. This sample predates
that fix, so it's preserved as the pre-fix historical data point;
`detected_genre` (the number that matters for the counts above) was
unaffected in all 20 records. A future `--sample-size`/`--full` run
benefits from the fix automatically.

**Finding:** heavily science-fiction-skewed, as expected given
`mass_quantities`'s corpus dominance — not yet conclusive on whether
smaller genres (western, romance, mystery, adventure — all 0/20 here) are
adequately represented; that needs the full census, not a 20-story sample.

## Purpose

`project/design/event-role-world-genre-target-reconciliation.md`'s "Gap 2"
identifies this survey as a prerequisite before sizing any stratified
Event-Role-World annotation pilot for the Worldcon 2026 paper: the current
8-genre `VALID_GENRES` classifier (landed via `WI-ASSESS-0031`) has never
been run at corpus scale. The one full-corpus classification that exists,
`experiments/01_classify_corpora/results/summary.tab` (2025-10-19), used a
different, older, open-vocabulary classifier — its counts are a rough
compositional signal only and are not authoritative for the current
8-genre scheme.

## Cost gate

This script has two mutually exclusive, gated modes. **Exactly one** of
`--sample-size N` or `--full` is required on every invocation — omitting
both exits immediately with usage information rather than silently
defaulting to the expensive path.

1. **`--sample-size N`** (recommended first step): runs a small,
   population-weighted stratified sample of N stories (proportional to
   each collection's real share of the corpus — see
   [Sampling methodology](#sampling-methodology) — not equal-per-collection)
   through detect-mode `assess_story()`, measures real per-story token
   cost/latency, and extrapolates a total $ and wall-clock estimate for the
   full ~1,868-story corpus. Prints and writes that estimate; does **not**
   run the full corpus itself.
2. **`--full`** (only after reviewing a sample estimate): runs every
   discovered story, resuming from any existing checkpoints under
   `--output`. This is the real, meaningfully larger expenditure the
   sample step exists to estimate first.

**Do not run `--full` without first running `--sample-size` and reviewing
its extrapolated estimate with a human.** This is not enforced by the
script itself (there is no persistent record of "the estimate was
reviewed") — it is a process requirement on whoever runs this census.

## Sampling methodology

`build_population_weighted_sample()` in `run_census.py` allocates the
sample across collections proportionally to each collection's share of the
corpus (largest-remainder rounding), then randomly selects within each
collection. This is deliberately **not** equal-per-collection:
`mass_quantities` alone holds ~89% of the corpus (1,659 of 1,868 stories)
with the rest split across ~11 much smaller collections (5-62 stories
each), and body length (therefore token cost) varies by collection — an
equal-per-collection sample would systematically misrepresent the
corpus-wide average cost per story. At a 20-30 story sample size, this
means most of the sample (and therefore most of the measured cost signal)
legitimately comes from `mass_quantities` — that is expected, not a bug.

## Usage

From the **repository root** (not `lcats/` — see the Validation section of
WI-ASSESS-0051 for why), with the conda environment active and an API key
configured (see `docs/secrets-setup.md`):

```bash
# 1. Zero-cost smoke test (file discovery + checkpoint wiring only)
python experiments/04_genre_census/run_census.py --sample-size 20 --dry-run

# 2. Real small-sample cost estimate (requires ANTHROPIC_API_KEY)
python experiments/04_genre_census/run_census.py --sample-size 20

# 3. Only after reviewing step 2's extrapolated estimate:
python experiments/04_genre_census/run_census.py --full
```

Full flag reference is documented in `run_census.py`'s module docstring
(`python experiments/04_genre_census/run_census.py --help`). Key flags:

| Flag | Default | Purpose |
|---|---|---|
| `--data-dir` | `corpora` | Corpus directory to scan (the actual populated, committed corpus — not `run_pilot.py`'s `lcats/data` default, which doesn't exist in a fresh checkout) |
| `--sample-size` | none | Run N stories, population-weighted sample. Mutually exclusive with `--full`; one of the two is required |
| `--full` | off | Run every discovered story, resumable via checkpoint |
| `--seed` | 42 | Sample-selection shuffle seed (reproducibility) |
| `--backend` | `anthropic` | `anthropic` or `openai` |
| `--model` | provider default (`claude-opus-4-8`) | Model string |
| `--output` | `experiments/04_genre_census/results` | Results/checkpoint directory |
| `--dry-run` | off | Zero-cost smoke test using a `FakeBackend`. Must be paired with `--sample-size` or `--full` |

## Checkpointing and resume

Every story's genre-census classification is checkpointed independently
under `--output` (stage `"genre_census"`, via `lcats.utils.checkpoint`),
keyed by a collection-qualified story identity and a fingerprint of
model/backend/classifier-version plus a hash of that story's own raw text
— so a story corrected in place invalidates its own cached classification,
and a classifier prompt/schema change (bump `_CLASSIFIER_VERSION` in
`run_census.py`) invalidates every cached classification at once.

This means:

- A crash or Ctrl-C mid-run preserves every already-classified story on
  disk.
- Re-running the exact same command (same `--output`, `--data-dir`,
  `--model`/`--backend`) resumes rather than restarts: an
  already-checkpointed, successfully-completed story is served from disk
  instead of re-issuing its LLM call. A checkpoint recording a *failed*
  classification is retried on the next run, not silently skipped.
- Checkpoints live under `--output` only, never under `--data-dir`/`data/`/
  `corpora/` directly — pointing `--output` at those protected roots is
  refused (`lcats.utils.checkpoint.resolve_roots`'s write-guard), since
  `data/` is a disposable cache and `corpora/` is copied wholesale by
  `lcats promote`.

## Excluded (failed) stories

Any story whose `assess_story()` call returns a populated `error` field is
**excluded** from the per-genre census counts — never silently counted as
a genuine `"other"` classification. Excluded stories are still written to
the per-story `.jsonl` output with their `error` populated, and their
count/reasons appear in the summary JSON's `excluded_stories` and
`excluded_by_collection`. A failed-but-billed call's real token usage
still counts toward the cost estimate (the backend/`assess.py`
usage-forwarding fix in this same work item ensures that). A high
exclusion rate, or one concentrated in a specific collection rather than
spread roughly evenly, is a data-quality flag worth noting in the Results
section below, not something to silently absorb into a smaller total.

## Pricing

`run_census.py` has a small, local, documented USD-per-million-token
pricing table (`_PRICING_USD_PER_MILLION_TOKENS`) — there is no shared
pricing/cost module anywhere in this codebase
(`PROP-LCATS-PIPELINE-CHECKPOINTING`'s Category E1 was explicitly deferred
and remains unbuilt). This table is an approximation tied to the model in
use at the time it was written; check current provider pricing before
trusting a cost estimate derived from it for a real budgeting decision.

## Output files

- `results/census_sample_stories.jsonl` / `results/census_full_stories.jsonl`
  — one row per story: `story_id`, `file_path`, `detected_genre`,
  `detected_genre_confidence`, `secondary_genre`, `error`, `input_tokens`,
  `output_tokens`, `estimated_cost_usd`, `elapsed_seconds`,
  `backend_model`, `from_cache`.
- `results/census_sample_summary.json` / `results/census_full_summary.json`
  — run metadata (mode, backend, model, dry-run flag, corpus story count)
  plus `genre_counts` (all 8 `VALID_GENRES` values plus `"other"`),
  `excluded_count`/`excluded_stories`/`excluded_by_collection`, and
  cost/latency totals. The sample summary additionally includes
  `extrapolated_full_corpus_cost_usd` and
  `extrapolated_full_corpus_wall_clock_seconds`.

## Expected Results Format

Whoever runs the `--full` census for real should append a section here,
e.g.:

```markdown
## Results (YYYY-MM-DD)

Sample estimate: N stories, $X.XX measured, extrapolated to $Y.YY /
~Z minutes for the full corpus. Reviewed and approved by <name> on
<date>.

Full census: ~1,868 stories, backend=<name>, model=<name>.

| Genre | Count | Share |
|---|---|---|
| science fiction | | |
| horror | | |
| humor | | |
| western | | |
| romance | | |
| mystery | | |
| fantasy | | |
| adventure | | |
| other | | |

Excluded: N stories (X%) — [note any collection-concentration pattern].

**Finding:** [Does corpus representation look adequate per genre for the
paper's eventual stratified sampling needs? One or two sentences grounding
the claim in the actual numbers above — no sourcing/ingestion decision
here, that's a separate follow-up.]
```
