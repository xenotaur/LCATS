# Phase 2 Science-Fiction Feasibility Pilot Preregistration

This preregistration freezes the Phase 2 pilot plan for
`PROP-LCATS-KNIGHT-NOVUM-ANALYSIS-SIDECAR` before any Phase 2 pilot output is
produced. It is a planning artifact for `WI-SF-0007`; it does not authorize a
paid model call, run the pilot, publish corpus sidecars, or change production
annotation and promotion commands.

The companion manifest is
`experimental/science_fiction_analysis_trial/manifests/phase2_sample_manifest.json`.
Its strata are sampling targets only. Human annotation and adjudication create
the gold record; the manifest does not encode pilot results or final genre
truth.

## Preconditions

- Phase 1 work through `WI-SF-0006` has landed, including the no-cost fixture
  runner and sidecar assembly checks.
- `WI-SF-0008` must not execute this pilot until this preregistration and its
  manifest have landed through review.
- Any non-fixture backend run requires a reviewed run manifest, pinned model
  and generation parameters, estimated budget, and explicit paid-run approval.
- The pilot must write only to an explicit experiment output root outside
  corpus and production promotion paths.

## Sample

The deterministic sample contains 30 stories:

| Stratum | Count | Purpose |
|---|---:|---|
| `clear_sf_positive` | 10 | Exercise obvious science-fiction positives across future, space, alien-contact, and technical/extrapolative cases. |
| `boundary_or_adjacent` | 10 | Stress SF-adjacent cases such as cosmic horror, fairy-tale fantasy, catastrophe, and ambiguous cognition. |
| `negative_control` | 10 | Verify that mystery, humor, romance, adventure, and western controls do not pass merely because they contain inquiry, danger, or strong narrative structure. |

The selection rule is deterministic: use the manifest order exactly as written,
with stable `sample_id`, `story_id`, `story_path`, `stratum`, and source
artifact fields. Suitable entries from the 24-story annotation-feasibility trial
are reused where available, and additional candidates are drawn from the
checked-in metadata genre prefilter manifest or local corpus inventory.

## Annotation Protocol

Two human annotators independently label a stratified calibration subset of at
least 12 stories before seeing model output. The preferred protocol is for both
annotators to label all 30 stories. If time requires the minimum subset, sample
four stories from each stratum using manifest order positions 1, 4, 7, and 10.

Annotators record:

- Knight criterion state for each of the seven criteria:
  `present`, `absent`, `ambiguous`, or `not_assessable`.
- Evidence materiality for each supported Knight criterion:
  `central`, `substantial`, or `incidental`; absent and not-assessable
  criteria have no materiality value.
- Knight `definite_count` and `possible_count` values are deterministic
  aggregate fields computed from the criterion evidence, not annotator labels
  for individual criteria.
- Novum candidate records, including novelty, cognitive validation, narrative
  hegemony, dominant-novum status, and optional system membership.
- Estrangement separately from novum qualification.
- Evidence anchors or notes explaining why a label is unsupported.
- Pipeline-independent notes about ambiguity, story length, and whether the
  whole-story or chunked mode is expected to be safer.

Annotators must not use model outputs, checkpoint files, generated sidecars, or
pilot metrics while labeling. Disagreements are adjudicated into one gold
record per story, preserving the original annotator labels and an adjudication
note.

## Execution Plan For WI-SF-0008

The Phase 2 run will use the experiment-local science-fiction analysis runner
against the preregistered sample. The execution work item must record the exact
code commit, backend, model, generation parameters, chunk configuration,
manifest checksum, estimated cost, output root, retry policy, and concurrency.

The pilot must include:

- one recommended pipeline run for all 30 stories;
- independent Knight-only and Suvin-only extraction on a stratified 9-story
  audit subset, selecting manifest positions 2, 5, and 8 from each stratum;
- repeated-run stability checks on 6 stories, selecting positions 1 and 10 from
  each stratum;
- whole-story versus chunked comparison on every story whose Phase 1 preparation
  marks both modes as safe, plus every long story that requires chunking;
- explicit quarantine for malformed model output, stale story hashes, invalid
  evidence anchors, and partial Knight/Novum failures.

No failed story may be silently dropped. A story can have a pipeline-failure
state for one analysis while the other analysis completes.

## Metrics

The Phase 2 report must publish machine-readable metrics and a narrative
summary for:

- completion rate by stratum and by analysis;
- evidence-anchor validity;
- sidecar validation success;
- shared-evidence recall on the independent audit subset;
- Knight criterion agreement against adjudicated gold labels;
- Suvin novelty, cognitive-validation, hegemony, and conjunction agreement;
- false-positive patterns for fantasy, supernatural, horror, and incidental
  technology controls;
- repeated-run stability of deterministic fields and model-dependent labels;
- whole-story versus chunked mode differences;
- latency, token counts, dollar cost, retry counts, and review time;
- failure taxonomy and quarantine counts.

## Predeclared Gates

The pilot passes only if all required gates pass. A failed or revise outcome
blocks `WI-SF-0009` until a separately reviewed revision or scale decision is
recorded.

| Gate | Pass threshold |
|---|---|
| Completion | At least 90% of stories complete both Knight and Novum analyses; every incomplete analysis has an explicit failure or partial-success record. |
| Structural validation | 100% of published `science-fiction.json` outputs validate with story-hash checks, referential integrity, current pointers, and deterministic Python-computed counts/conjunctions. |
| Evidence anchors | 100% of accepted evidence quotations locate against stable anchors; unlocatable evidence is quarantined and excluded from adjudication metrics. |
| Shared-evidence audit recall | Shared extraction recall on the independent audit subset is no more than 5 absolute percentage points below independent Knight-only or Suvin-only extraction for material evidence. |
| Knight agreement | Macro-averaged exact agreement for seven criterion states is at least 0.75 against adjudicated gold labels, and no individual criterion falls below 0.60 without a revise decision. |
| Novum conjunction agreement | Conjunctive Suvin novum qualification agrees with adjudicated gold labels on at least 0.80 of assessable stories. Novelty, cognitive validation, and hegemony must also be reported separately. |
| Negative controls | No more than one negative-control story may receive a qualified dominant novum; any such case requires error analysis before scaling. |
| Boundary controls | Fantasy or supernatural boundary stories must not repeatedly pass cognitive validation because of non-cognitive magic or occult explanation. |
| Repeated-run stability | With nondeterministic provenance fields normalized, deterministic output fields are byte-stable across repeated runs; model-dependent adjudication state changes are reported and must not alter more than 10% of assessable story-level decisions. |
| Whole-story versus chunked comparison | No material evidence class may show systematic loss in chunked mode without a revise decision; any loss above 5 absolute percentage points blocks scaling. |
| Failure rate | Pipeline failures, malformed outputs, and stale-hash quarantines together affect no more than 10% of stories. |
| Cost and token budget | Actual dollar cost is at or below both the approved budget and 120% of the approved estimate. Total model input plus output tokens are at or below 120% of the approved estimate, with median tokens per story at or below 75,000 and p90 tokens per story at or below 150,000. |
| Latency and human review time | Median end-to-end pipeline latency is at or below 8 minutes per story and p90 latency is at or below 20 minutes per story, excluding queued human time but including retries. Median human review time is at or below 20 minutes per story, p90 human review time is at or below 45 minutes per story, and adjudication time is at or below 30 minutes per disagreed story. |

## Reporting Requirements

The `WI-SF-0008` report must include:

- the exact manifest checksum and output root;
- the exact run command and backend configuration;
- the count of stories per stratum actually attempted;
- pass, fail, or revise status for every predeclared gate;
- a machine-readable metrics file;
- a failure taxonomy;
- a cost report;
- a human-review time report;
- a decision record stating whether to revise Phase 1, rerun Phase 2, proceed
  to Phase 3 planning, or terminate the workstream.

The report must not claim Phase 3 readiness unless every gate passes or an
explicit reviewed scale decision explains why a failed non-critical gate is not
material to the paper claim.

## Non-Goals

- Do not run the Phase 2 pilot in this work item.
- Do not make paid model calls.
- Do not inspect or summarize pilot results.
- Do not write `science-fiction.json` into corpus buckets.
- Do not alter `lcats annotate`, `lcats promote`, corpus promotion, or the
  Worldcon Phase 3 sample gate.
