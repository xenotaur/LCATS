# Cross-Segment Relation Density Pilot

**WI-EVENT-0030** — Run a stratified, cross-genre pilot measuring
cross-segment relation density, superseding WI-EVENT-0028's 4-story
convenience sample with a properly stratified measurement.

## Status

**Tooling only — not yet run.** This directory currently contains the pilot
script and this usage doc. No results exist yet: the session that wrote this
tooling had no `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` configured, and this
pilot's headline findings require real LLM pipeline output, not a fake
backend. Whoever runs this pilot for real should follow
[`running_the_pilot.md`](running_the_pilot.md)'s step-by-step runbook and
append a "Results" section below this one, following the format sketched in
[Expected Results Format](#expected-results-format).

## Purpose

WI-EVENT-0028's investigation (`project/design/event-role-world-cross-segment-relations-evaluation.md`)
established — via a small, convenience-selected 4-story reading exercise,
not a pipeline run — that SF/horror material exhibits more long-range
cross-segment causal chains than mystery/general-fiction comparison
material, and recommended the story-level relation pass WI-EVENT-0029
shipped. This pilot runs that pass over a larger, genre-stratified sample
to size the effect precisely enough to support a paper-facing density
figure.

## Genre strata

Genre strata are pinned to the original four genres this pilot was scoped
against: `science fiction`, `horror`, `western`, `romance` (the module-level
`GENRES` constant in `run_pilot.py`, deliberately independent of
`lcats.analysis.corpus.assess.VALID_GENRES`, which has since grown to 8
genres via `WI-ASSESS-0031` — see that work item's PR for why re-scoping
this pilot is separate follow-up, not an implicit side effect). WI-EVENT-0028's own informal
comparison genres (mystery, general fiction) are **not** used here. This is
a deliberate scope choice, not a classifier limitation as of
`WI-ASSESS-0031`: `mystery` is now a classifiable `VALID_GENRES` value (it
would no longer fall back to `"other"` in detect mode), but this pilot's
`GENRES` constant remains pinned to the original four strata regardless —
"general fiction" is still not classifiable by the corpus's existing
genre-detection tooling either way. Noted so a reader does not assume the
two work items compare identical genre sets, and does not assume `mystery`'s
absence here means it can't be classified.

Genre is detected per-candidate story via `assess_story()` in detect mode
(one real LLM call per candidate scanned) — the corpus carries no
pre-existing genre metadata, so this pilot cannot skip that step.

## Metric definitions

Two distinct metrics are computed and reported side by side — conflating
them was a review-caught error in this work item's original planning doc:

- **Cross-segment-only density** (the headline metric): counted directly
  from each story's `cross_segment_relations` /
  `weakly_inferred_cross_segment_relations` fields (all `relation_type`
  values counted, unfiltered), normalized per 1000 words. This is the only
  metric that can actually confirm or contradict WI-EVENT-0028's
  cross-segment-specific claim.
- **Folded total density**: cross-segment relations added into the same
  total as every segment's own same-segment relations — mirrors what
  `baseline.summarize_annotations(annotations, story)` would report, but
  computed directly from the pipeline's own output dicts here (not by
  calling that function, to avoid needing to reconstruct
  `SegmentWorldAnnotation`/`StoryWorldAnnotation` dataclasses from
  `process_segments`' already-serialized dict output). Reported for
  context only — two genres could differ solely in same-segment links, and
  this metric alone cannot isolate a cross-segment-specific effect.

The `weakly_inferred` certainty partition is preserved throughout: a
`weakly_inferred` relation is never mixed into the primary (`explicit`/
`strongly_implied`) density figure for either metric.

## Excluded stories

Any story whose run produced a segment- or story-level `extraction_errors`
entry (a transient API/backend failure, per
`processor.process_segments`'s error-handling contract) is **excluded**
from the aggregated per-genre figures, not silently counted as zero or
partial. Excluded stories are still written to `pilot_stories.jsonl` with
`excluded: true` and an `exclude_reason`, and their count is included in
`pilot_summary.json`'s per-genre `excluded_count`.

## Usage

From the repo root, with the conda environment active and an API key
configured (see `docs/secrets-setup.md`):

```bash
python experiments/03_cross_segment_relation_pilot/run_pilot.py \
    --sample-size 5 \
    --output experiments/03_cross_segment_relation_pilot/results
```

Defaults to `--data-dir lcats/data` — populate it first via `lcats gather`
if your checkout doesn't have it yet, or pass `--data-dir corpora` to use
the released snapshot instead (see `running_the_pilot.md` for full
environment-setup detail).

Full flag reference is documented in `run_pilot.py`'s module docstring
(`python experiments/03_cross_segment_relation_pilot/run_pilot.py --help`).
Key flags:

| Flag | Default | Purpose |
|---|---|---|
| `--data-dir` | `lcats/data` | Corpus directory to sample from |
| `--sample-size` | 5 | Target stories per genre (WI-EVENT-0030 asks for 5-10) |
| `--max-candidates` | 200 | Cap on genre-detection scanning before giving up on an under-filled stratum |
| `--seed` | 42 | Shuffle seed for candidate scan order (reproducibility) |
| `--backend` | `anthropic` | `anthropic` or `openai` |
| `--model` | provider default | Model string |
| `--nlp-backend` | `spacy` (`fake` under `--dry-run`) | Stage-2 surface-feature NLP backend: `spacy`, `stanza`, or `fake` (zero dependencies) |
| `--dry-run` | off | Zero-cost smoke test using fake LLM and (by default) fake NLP backends — produces meaningless (empty) results, never a real finding |

### Try it with zero API cost first

```bash
python experiments/03_cross_segment_relation_pilot/run_pilot.py --dry-run \
    --data-dir corpora --sample-size 2 --output /tmp/pilot_dry_run
```

(`--data-dir corpora` is needed on a fresh checkout — `lcats/data`, the
default, is gitignored working-corpus state and won't exist until you
generate it. See `running_the_pilot.md` for details.)

This exercises the full script — sample selection, a stubbed single-segment
stage-1 segmentation (stages 2-7 of the Event-Role-World pipeline), and
output writing — with fake LLM and NLP backends and **no real API calls or
extra dependencies**, so you can confirm the script runs end to end in your
environment before installing anything or spending real cost. It does
**not** exercise the story-level cross-segment relation pass, which needs
events in at least 2 distinct segments. Dry-run stories are not excluded,
so you'll see real output rows with zero counts everywhere — the point is
verifying the control flow and output files, not producing real numbers.

**For the full developer runbook** — environment setup, smoke-testing a
real spaCy or Stanza install with zero API cost, the real run, and closing
out `WI-EVENT-0030` — see
[`running_the_pilot.md`](running_the_pilot.md) in this directory. This
README is the reference for what the pilot measures and how to interpret
its output; that runbook is for actually executing it.

## Cost note

This script makes real LLM API calls for genre detection (one call per
candidate story scanned — could be well more than the final sample size,
depending on how the corpus's genre distribution lines up with the four
target strata), scene/sequel segmentation (one call per sampled story),
and the full Event-Role-World pipeline (4 calls per segment — entities,
events, relations, discourse; the optional stage-8 hypothesis pass is
disabled since this pilot doesn't use hypothesis data — plus one
story-level cross-segment-relation call per story). Across 4 genres x
5-10 stories each (WI-EVENT-0030's target), this is a real cost and
latency expenditure — size toward the lower end of the 5-10 range first
if cost is a concern, and note the actual sample size used in the Results
section rather than silently shrinking it without comment.

`--model` (and the `--backend`-specific default) is propagated to every
call the script makes, including the Event-Role-World pipeline's own
extractors — those extractors normally hardcode `default_model="gpt-4o"`
internally when built by `processor.process_segments()`, which would send
an invalid model ID to a non-OpenAI backend; this script instead builds
the same extractors itself (see `_build_erw_extractors`/`_run_erw_pipeline`
in `run_pilot.py`) so their model can be overridden, without modifying
`processor.py` or any `event_role_world` module (forbidden by
WI-EVENT-0030's scope).

## Checkpointing and resume (WI-PIPELINE-0041)

Every story's genre-detection, segmentation, ERW-extraction, and
cross-segment-relation stages are checkpointed independently under
`--output` (via `lcats.utils.checkpoint`), each keyed by model/backend
configuration plus a hash of that stage's own relevant input: the raw
story text for genre-detection, the segmentation input text for
segmentation, and the upstream stage's own output for the two downstream
stages (ERW-extraction's fingerprint also includes the NLP backend
choice, since that affects its output too) — so correcting a story, or
its output at an earlier stage, under an unchanged model configuration
still invalidates every stage that depended on it.

This means:

- A crash or Ctrl-C mid-run preserves every already-completed stage's
  output on disk, not just whatever made it into `pilot_stories.jsonl` at
  the very end.
- Re-running the exact same command (same `--output`, `--data-dir`,
  `--seed`, `--model`/`--backend`) resumes rather than restarts: every
  already-checkpointed, successfully-completed stage is served from disk
  instead of re-issuing its LLM call. A checkpoint recording a *failed*
  stage is not treated as done — it is retried on the next run, not
  silently skipped.
- Checkpoints live under `--output` only, never under `--data-dir`/`data/`/
  `corpora/` directly — pointing `--output` at those protected roots is
  refused (see `run_pilot.py`'s own error message) since `data/` is a
  disposable, regenerable cache and `corpora/` is copied wholesale by
  `lcats promote`.

## Output files

- `results/pilot_stories.jsonl` — one row per sampled story: `path`,
  `story_id`, `genre`, `word_count`, `segment_count`,
  `cross_segment_relation_count`,
  `weakly_inferred_cross_segment_relation_count`,
  `cross_segment_density_per_1000_words`,
  `weakly_inferred_cross_segment_density_per_1000_words`,
  `folded_relations_per_1000_words`,
  `folded_weakly_inferred_relations_per_1000_words`, `excluded`,
  `exclude_reason`, `elapsed_seconds`.
- `results/pilot_usage.jsonl` — one row per pipeline `PassUsage` record
  (model, input/output tokens, elapsed time), tagged with `story_id` and
  `genre`, preserved even for excluded stories so cost/latency on a failed
  paid run is never lost. This is the raw data needed for the proposal's
  Cost and baseline reporting requirement — `pilot_summary.json` does not
  aggregate cost, only density.
- `results/pilot_summary.json` — run metadata (sample size target,
  candidates scanned, backend/model, dry-run flag) plus a `by_genre` dict:
  `included_count`, `excluded_count`,
  `mean_cross_segment_density_per_1000_words`,
  `mean_weakly_inferred_cross_segment_density_per_1000_words`,
  `mean_folded_relations_per_1000_words`,
  `mean_folded_weakly_inferred_relations_per_1000_words`.

## Expected Results Format

Whoever runs this pilot for real should append a section here, e.g.:

```markdown
## Results (YYYY-MM-DD)

Sample: N stories per genre (actual: science fiction=N, horror=N,
western=N, romance=N — note any genre that fell short of the target and
why), backend=<name>, model=<name>.

| Genre | Included | Excluded | Cross-segment density (mean, /1000 words) | Folded total (mean, /1000 words) |
|---|---|---|---|---|
| science fiction | | | | |
| horror | | | | |
| western | | | | |
| romance | | | | |

**Finding:** [confirms / weakens / contradicts] WI-EVENT-0028's smaller-sample
finding that science fiction/horror shows materially more long-range
cross-segment causal chains than the other strata. [One or two sentences
grounding the claim in the actual numbers above, not just the raw sample
size.]
```
