---
id: PROP-LCATS-HEINLEIN-TEMPORAL-REFERENCE
type: design_proposal
title: Judge the Heinlein Conditions Against the Author's World at the Time of Writing
status: proposed
created_on: 2026-10-22
updated_on: 2026-10-22
implementation_status: not_started
implemented_by: []
supersedes: []
superseded_by: null
related_design:
  - lcats/project/work_items/proposed/WI-SF-0123.md
  - lcats/experimental/science_fiction_analysis_trial/heinlein_temporal_premise_trial.md
  - lcats/experimental/science_fiction_analysis_trial/heinlein_canary_followup_bell_control.md
  - lcats/project/design/proposals/adopted/knight-novum-analysis-sidecar/00_proposal.md
  - lcats/src/lcats/analysis/science_fiction/rubric/definitions.py
  - lcats/src/lcats/analysis/science_fiction/models.py
  - lcats/src/lcats/analysis/science_fiction/heinlein.py
  - lcats/experimental/science_fiction_analysis_trial/run_worldcon_spike.py
---

## Summary

Judge each of Heinlein's five conditions against the world the author lived in when the story
was written, not the world of the day the analysis runs. An optional, separate stage estimates
a composition-date interval, lists the story's material factual premises, and records for each
a timeline of how well established the claim was over time. Deterministic rules then derive
date-aware plausibility, an outcome relation to today, and two flags, and combine them into a
profile instead of a score. The existing `heinlein-five-v1` record, its prompt, and its
checkpoints are not changed.

## Background / Motivation

Two of Heinlein's five conditions compare a story with "the world" without saying which one.
The `different` condition says the conditions "must be different from here-and-now"
(`lcats/src/lcats/analysis/science_fiction/rubric/definitions.py:133-137`), and the
`plausible` condition says "No established fact shall be violated"
(`definitions.py:167-176`). The Heinlein prompt tells the model to judge plausibility "against
established facts available to a general reader"
(`lcats/experimental/science_fiction_analysis_trial/run_worldcon_spike.py:2566`), and a model
reads that with today's knowledge. The verdict is a conjunction, not a count
(`lcats/src/lcats/analysis/science_fiction/models.py:362-377`, and
`lcats/src/lcats/analysis/science_fiction/heinlein.py:5-8`), so a single failure on the date
question changes the whole verdict.

Three failure modes follow from a today-reading:

1. **Falsified premises.** A story written before the 1965 Mariner 4 flyby, with a Mars that
   has a protective atmosphere and canals, fails `plausible` even though it respected the
   knowledge of its time. The first close-up images of Mars came on
   [15 July 1965](https://nssdc.gsfc.nasa.gov/imgcat/html/object_page/m04_01d.html). Venus
   follows the same pattern: Mariner 2 flew past on
   [14 December 1962](https://www.nasa.gov/history/60-years-ago-mariner-2-first-to-explore-venus/).
   Radar showed that Mercury's day is 59 Earth days, not 88 as had been thought
   ([Pettengill](https://en.wikipedia.org/wiki/Gordon_Pettengill), which I opened; it states
   the result but gives no year, and the year 1965 comes from search-result summaries that I
   did not open).
2. **Successful predictions.** A story about a technology that later came true stops being
   "different" under a today-reading, so the story is penalized for being right.
3. **Period stories.** A realist story set in its author's present, such as a 1910 detective
   story, differs from today's here-and-now and could be rated "different" with no speculation
   in it at all.

The question came out of WI-SF-0119, whose finding
(`lcats/experimental/science_fiction_analysis_trial/heinlein_canary_followup_bell_control.md`)
showed that the Bell control gave different answers to identical inputs, and out of a manual
trial on its six control stories
(`lcats/experimental/science_fiction_analysis_trial/heinlein_temporal_premise_trial.md`). In
that trial one of six stories needs a date for a plot-central physical premise (A Case of
Sunburn), two carry dated predictions that have since expired, and the two realist stories
show the `different` condition has the same problem. The trial is one rater and six
hand-picked controls, so it says nothing about how often dates matter in the corpus. The
corpus also does not record story years: the `year` field is "Unknown"
(`lcats/src/lcats/gatherers/parser.py:1457`).

## Prior Art Check

### Duplication search
- In-repo: No existing implementation found. No source file, proposal, or work item handles
  dates or temporal reference. The Suvin prompt already measures novelty against "the
  authorial or implied empirical norm" (`run_worldcon_spike.py:2587-2588`), which is precedent
  for an author-relative frame.
- Sibling repos: None identified.
- External libraries: None identified. The relevant design idea is the valid-time versus
  transaction-time split from [bitemporal data modeling](https://tdwi.org/blogs/data-101/2026/05/the-bitemporal-problem.aspx):
  the story's composition date is the valid time and the analysis date is the transaction time.
- Recommendation: Proceed.

### Demand search
- Work items: Found: WI-SF-0123, the work item that asked for this proposal.
- Proposals: None found.
- Backlog: No matching entries.
- Recommendation: No action; this proposal satisfies WI-SF-0123.

## Design Decisions

Decisions D1 to D9 were made by the owner in conversation and are fixed inputs, stated here
precisely enough to implement. Where a fixed decision needs a definition the owner did not
give, the definition is marked as this proposal's recommendation in section "Definitions
recommended by this proposal". Field names are proposals and may change in implementation.

### Fixed inputs

**D1. Reference frame.** All five conditions are judged against the author's world at the time
of writing ("the here-and-now in which the story was written"). A today-reading is rejected.
Reasons: the `different` slot says the difference "may lie only in an invention made in the
course of the story" (`definitions.py:133-137`), and an invention is new relative to the
writer's world; a today-reading penalizes successful predictions; the Suvin prompt already uses
the authorial norm. "Written" means composition, not publication, translation, or later
revision; a text revised decades later is recorded with a caveat.

**D2. Premise-first, date-second.** The stage lists the story's material factual premises
first, then asks for a date only when a premise's standing changes inside the story's plausible
date window. A premise is a factual claim about the world that the plot relies on. Decorative
technology and settings that change nothing about the problem are excluded, matching the
existing exclusion in the prompt (`run_worldcon_spike.py:2568-2569`). Materiality reuses the
repository's vocabulary: `central`, `substantial`, `incidental` (`models.py:49-55`). Only
`central` and `substantial` premises count.

**D3. Change windows, not change dates.** Knowledge changes over a window, from the first
credible evidence to a settled consensus, not on a single date. The window is represented by
the standing timeline defined under "Definitions recommended by this proposal". A date inside
the window is `ambiguous`.

**D4. Composition-date interval.** The stage records an interval from sources, strongest
first:

1. owner-supplied;
2. a bibliographic first-publication record (ISFDB is the natural candidate; its coverage and
   terms have not been checked). The story's own first publication is an upper bound on its
   composition, not a lower bound;
3. the author's lifespan: death is a hard upper bound and birth is the lower bound. Career
   milestones (adulthood, the date of the author's first publication) are contextual evidence
   only, not bounds, because a debut may have been written years before it was published or
   while the author was a minor; they become a bound only when a story-specific source says so.
   The caveats are disputed attribution, collaboration, posthumous revision, and translation
   (the original composition date applies);
4. internal evidence the model can see.

The sources are intersected. Each source is recorded with its kind, value, basis, and a
confidence, and an owner override replaces the result. With no basis at all the interval is
unbounded, not guessed (see D5).

**D5. Premise status over the interval, and the combination rule.** A premise has a status
over the composition interval with the existing vocabulary (`models.py:41-46`): `present` if
the claim was `supported` or `open` at every date in the interval, `absent` if it was
`contradicted` at every date, `ambiguous` otherwise, and `not_assessable` if the timeline
cannot be determined at all. When the status is `ambiguous` because the date is uncertain, the
output states the condition, for example "present if composed before 1965-07". The story-level
status is `absent` if any counted premise is `absent`, `present` if all counted premises are
`present`, and `ambiguous` otherwise; this mirrors `heinlein_verdict` (`models.py:362-377`).

**D6. Outcome relation to today, and the calendar-expired flag.** Each premise also has an
outcome relation to the world today: `stable`, `still_open`, `realized`, `falsified`, or
`not_assessable`. Separately, a premise that is a dated prediction whose date has passed
carries a `calendar_expired` flag, independent of the relation, because an expired prediction
can also be falsified or realized. Calendar-expired claims do not count toward the "plausible
now" reading. The analysis date and the model's knowledge cutoff are recorded with every
result.

**D7. Stories with no speculative premises.** A story with no speculative premises (see R6 for
the definition) has `plausible` present, derived by Python: its counted premises, if any, are
all supported, so R2 gives `present`, and with no counted premises at all the status is
`present` vacuously. The record carries a `speculative_premises` flag.

**D8. A profile, not a score.** The result is a profile derived by Python rules. It never
reports a count or a probability, consistent with `heinlein.py:5-8` and the prompt's rule
against scores (`run_worldcon_spike.py:2532-2533`).

**D9. A separate, opt-in stage.** The new stage is flag-gated like `include_heinlein`
(`run_worldcon_spike.py:163`), with its own prompt version (as `HEINLEIN_PROMPT_VERSION`,
`run_worldcon_spike.py:63`), its own tool schema, and its own analysis kind, leaving the
existing record untouched. The direction is phased toward a curated fact table as an audit
layer.

### Definitions recommended by this proposal

These define terms the fixed decisions use. They are recommendations for owner review.

**R1. Standing timeline.** Each premise carries an ordered list of periods
`{from, to, standing, basis, source}` that covers all time. `standing` is one of `supported`
(established), `open` (speculative but not contradicted by established fact), `contested`
(evidence has appeared but consensus has not settled), or `contradicted`. Boundaries are
closed and given as a year or a year and month (for example 1965 or 1965-07); unbounded ends are null. Two boundaries are compared at the finer granularity both give, and a bare year covers all twelve months. `basis` is `model_asserted`,
`table_confirmed`, or `owner_supplied`. A fact that never changed is one period. A premise
that is contradicted at every date (for example, talking animals in a fairy tale) is one
`contradicted` period. A claim accepted only later is simply a timeline that changes
direction, so the model needs no separate direction field. The window of D3 is the
`contested` period.

A premise has a `kind`: `ordinary`, or `counterfactual_divergence`, a stipulated point at which
the story's world departs from the author's real history (for example, antibiotics invented a
century early). A divergence contradicts the historical record by definition, so its timeline
describes the standing of its *enabling mechanism* (what the departure would require, judged by
what was established or open at composition), never the record, and the divergence is not
reported as `falsified` merely because history did not go that way. The consequences the story
draws from the divergence are separate premises with ordinary timelines.

**R2. Status of a premise over an interval.** Take the closed interval `[a, b]` (unbounded if
absent, and ending at the analysis date). Collect the standings of every period that overlaps
it; touching boundaries overlap. If all are `supported` or `open`, the status is `present`; if
all are `contradicted`, `absent`; otherwise `ambiguous`. A missing interval is just the widest
interval, so a stable premise is `present` or `absent` by its single period and a
time-sensitive one is `ambiguous` with its condition. A premise whose standing is `contested` at composition (for example, a recognized
but not widely accepted scientific theory) therefore yields `ambiguous`, and the stage states
the condition; the proposal does not try to resolve `open` versus `contested` by rule, because
the boundary has to be judged case by case (the owner's decision). `not_assessable` is used only when the
model cannot state the timeline at all. "Today" is the point interval at the analysis date;
when the model cannot state today's standing (beyond its knowledge cutoff) the status is
`not_assessable`.

**R3. Derived outcome relation.** Python derives the relation from the standing at composition
and the standing today, when both are unambiguous: (`supported`, `supported`) and
(`contradicted`, `contradicted`) are `stable`; (`open`, `open`) is `still_open`; (`open`,
`supported`) and (`contradicted`, `supported`) are `realized`; (`supported` or `open`,
`contradicted`) is `falsified`. Any other pair, or any `contested` or unknown standing, is
`not_assessable`. Because the status as written is `ambiguous` while the composition interval is
unknown or straddles a change, the relation of such a premise is `not_assessable` until the
interval is known, and a report states the interval it used. The model never asserts the
relation directly.

**R4. Novelty and `different`.** Each premise carries `novel_at_composition`: `true`, `false`
or `unknown`, judged against the author-time empirical world of D1, never against the story's
own world: talking animals or spirits in a folktale are `true` however ordinary they are to its
characters, and `unknown` is only for a claim the stage cannot place. `different` as written is
`present` if any counted premise is novel; `absent` if there are counted premises and every one
is explicitly `false`, or if no counted premises exist; and `ambiguous` if no counted premise is
`true` and at least one is `unknown`. Whether a fantastic condition passes `plausible` is a separate matter.

The time of a story's setting is never itself a difference, in either direction. A premise is
novel only if it is not true of the author's real world, and that world includes the author's
real past. A story set in an earlier period that faithfully reflects the author's own history
(historical fiction, a realist period piece) has no novel premise from its setting, so
`different` is `absent`; a story set in the future that changes nothing is likewise `absent`. A
past setting becomes different only through a premise that departs from the real world: a
`counterfactual_divergence` (R1), a time-travel element, or any other novel condition. This is
the owner's decision on the former Open Question 1.

**R5. Calendar-expired and counting.** A premise with a `dated_prediction` date earlier than
the analysis date has `calendar_expired: true`, derived by Python. For the "as written"
reading all counted premises are used; for the "today" reading, calendar-expired premises are
excluded. If there are no counted premises at all, the "today" status is `present` vacuously
(D7). If counted premises exist but every one is excluded as calendar-expired, the "today"
status is `not_assessable` with `today_reason: all_counted_expired`, so a story whose only
speculative premise has been overtaken by the calendar is not reported as evergreen.

**R6. Speculative premises and the flag.** A *speculative* premise is a counted premise that
is novel at composition (`novel_at_composition` true) or whose standing is anything other than
`supported` at some date in the composition interval (so an invention, a contested claim and a
fantastic one are all speculative, and a supported claim in a realist story is not). The flag is `{has: bool, counted: int, by_materiality}`,
computed before any calendar-expired exclusion, so a story whose only speculative premises are
expired is reported as having them.

**R7. Profile categories.** Python derives a category from plausibility as written (P1) and
today (P3), only when `speculative_premises.has` is true; otherwise the category is
`not_applicable`. Categories describe plausibility, not whether the story qualifies:

| P1 as written | P3 today | Category |
|---|---|---|
| present | present | evergreen |
| present | absent | overtaken |
| present | ambiguous or not_assessable | plausible when written, today undetermined |
| absent | present | plausible only in retrospect |
| absent | absent, ambiguous or not_assessable | fails when written |
| ambiguous or not_assessable | any | undetermined, with the condition |

**R8. A second derived verdict.** The new record carries `verdict_as_written`: the conjunction
in `heinlein_verdict` (`models.py:362-377`) over five statuses in the author's frame.
`different` comes from R4 and `plausible` from D5. The stage assesses `essential` and `causal`
itself, against its author-time premises, because the existing record's two statuses depend on
a today-relative `different`: when a once-novel condition has since become ordinary, the existing
prompt can mark `different` absent, and its rule that `essential` and `causal` cannot be present
then (`run_worldcon_spike.py:2560-2564`) would carry the same today-relative error into the
as-written verdict. Each of the two statuses cites the premise IDs the plot depends on. Only
`human` is taken from the existing record, because it does not depend on the reference frame.
Because a sidecar can hold several Heinlein analyses while its current pointer moves
(`models.py:662-678`, `pipeline.py:263-280`), the source is selected by rule: the current Heinlein
analysis whose `story_hash` and `evidence_set_id` match the temporal record's and whose status
is `complete`. The record persists `source_heinlein_analysis_id` and the borrowed `human`
status, and the source ID is part of the new stage's fingerprint inputs, so a different source
invalidates the saved result and the verdict can be recomputed and audited.
The prerequisite rules (`HEINLEIN_PREREQUISITES`, `models.py:35`, used by
`heinlein_dependency_violations`, `models.py:379`) apply within the new record: if a violation
appears, for example `essential` present while `different` is absent, the record reports
`consistency: inconsistent` with the pair and `verdict_as_written: indeterminate`, and does not
silently force a verdict. If the existing record is missing or failed, `human` is unavailable
and the field is `not_computed`. The record also reports, for information only, where its five
statuses differ from the existing record's.

**R9. Evidence for derived values.** The existing record requires evidence for a `present`
criterion (`models.py:328-329`). The new record is a different kind: statuses derived by
Python from premises, including a vacuous `present`, need no supporting evidence, but each
premise carries its text anchor (offset and quote) so a reader can audit it. The two statuses the
model assesses, `essential` and `causal`, follow the existing rule: a `present` cites the
premise IDs it depends on. This is deliberate and does not change the existing invariant.

**R10. Handling the model's weak points.** The stage must name each fact and the date it
became established or contested, and mark the claim `model_asserted`. A curated table of known
cases (Mars 1965, Venus 1962, Mercury 1965) is the audit layer in a later phase; it marks
matching claims `table_confirmed` and flags disagreements.

### Record shapes

One `heinlein_temporal` analysis record per story, serialized only when the stage ran:

- `analysis_id`, `story_hash`, `evidence_set_id`, `provenance` (with its own provenance version,
  below), `status`, `failures`, `analysis_date`, `model_knowledge_cutoff`.
- `composition`: `{earliest, latest, sources: [{kind, value, hard_bound, basis, confidence}],
  override, caveats}`.
- `premises`: list of `{premise_id, kind, claim, anchor: {offset, quote}, materiality,
  novel_at_composition, dated_prediction, timeline: [...]}`, where `dated_prediction` is null or
  `{date: year or year-month, claim}` and `calendar_expired` is derived by Python from it (never
  asserted by the model) and appears in the assessment.
- `assessment`: `{plausible_as_written, plausible_today, different_as_written, condition,
  per_premise: [{premise_id, status_as_written, status_today, relation, calendar_expired}],
  essential_as_written, causal_as_written (each with status, supporting premise IDs and
  rationale), human (`{status, source_heinlein_analysis_id}`, from the existing record),
  comparison_with_existing, today_reason, speculative_premises, category, verdict_as_written,
  consistency}`.

### Options considered

| # | Option | Pros | Cons |
|---|---|---|---|
| O1 | Keep the prompt and report `plausible` separately | Nothing to build | Leaves today's knowledge as the implicit reading, which D1 rejects |
| O2 | One as-of date input to the existing stage; run it twice for two readings | Simple | Adding the date to the payload (`_heinlein_payload`, `run_worldcon_spike.py:2400`) changes `payload_sha256`, which `_model_stage_fingerprint` computes (`run_worldcon_spike.py:1100-1125`), which invalidates the existing stage's fingerprint and checkpoints; one call per reading; no premise-level audit trail; needs a date up front, which the corpus lacks (`parser.py:1457`) |
| O3 | Put sub-readings inside `plausible` | One record | Changes `HeinleinCriterion` and `HeinleinAnalysis`, which are pinned to `heinlein-five-v1` and exactly five criteria (`models.py:311-345`, `models.py:394-420`); invalidates existing records |
| O4 | A separate opt-in stage with a premise-first record | Leaves the existing record untouched; follows the optional-stage pattern; reuses the status vocabulary (`models.py:41-46`) | One more model call; relies on the model's recall of dates |
| O5 | A curated fact table alone | Fully auditable and reproducible | Cannot cover a fact it does not list; needs upkeep |
| O6 | O4 plus O5 as an audit layer | Auditability where facts are known | Most to build |

Chosen: **O4 now, with O5 added as the audit layer in a later phase, which is O6 built in
phases.** This matches owner decision 9, which describes the fact table phased in. O1 is
rejected by D1, O3 touches a pinned contract, O5 cannot stand alone because it cannot cover a
fact it does not list, O2 cannot give a premise-level profile and invalidates the existing
stage's checkpoints, and O6 is not chosen as a single step only because it is the most to
build before the first live evidence exists. This is a design judgment based on the repository
state described here, not a proof.

## Compatibility

- **Unchanged:** the `heinlein-five-v1` rubric (`models.py:21`), `HeinleinCriterion` and
  `HeinleinAnalysis`, the existing stage's prompt, prompt version and tool schema, the stage
  fingerprint inputs (`run_worldcon_spike.py:1100`), and existing checkpoints. A stage's
  fingerprint includes its own system prompt, tool schema, and payload hash, so the new stage
  has its own and cannot invalidate the old one. The per-attempt request records added by
  WI-SF-0120 apply to the new stage unchanged.
- **The sidecar schema version must not be bumped.** It is checked for strict equality
  (`sidecar.py:58`, `models.py:681`) and hashed into the assembly fingerprint (`pipeline.py:51`),
  so a bump would reject every existing sidecar and invalidate every assembly checkpoint. The
  Heinlein stage added an optional key without a bump, and the new kind follows that pattern:
  omit the key when empty.
- **A new analysis kind forces changes in these places**, each as the Heinlein kind was added:
  - `sidecar.py`: `PARTIAL_SUCCESS_STAGE_NAMES` (16-26), the optional-analysis validation (145),
    the current-pointer parsing and validation (82-105, 175-178), the label dispatch and a new
    validator beside the Heinlein one;
  - `models.py`: the pointers record (`heinlein_analysis_id` at 633 and its validation), the
    envelope field and `_validate_analyses` (716), `_iter_analyses` (947), the serialization
    (832-846). The evidence-reference iteration (`_iter_criterion_references`, 973, and
    `_iter_evidence_references`, 1001) assumes records with `.criteria`; a premise-based record
    needs its own iteration over premise anchors;
  - `pipeline.py`: `SidecarAssemblyInputs` (34), the optional-when-empty fingerprint (66),
    `assemble_sidecar` (92), and current selection (255);
  - `rendering.py`: a view and columns for the new profile;
  - the runner: `RunnerOptions` and the flag, `StoryResult` (186), `_sidecar_configuration`
    (1892), the completed-stage lists (2064), the fake backend (2900), the run summary (3170),
    and the paid-run gate (`run_worldcon_spike.py:2991`), which rejects the Heinlein stage on
    any paid-call backend and needs its own rule;
  - the new kind needs its own rubric or provenance version string, because
    `HeinleinAnalysis` pins `heinlein-five-v1` (`models.py:410`); and
  - tests beside `heinlein_test.py`, `rendering_test.py` and `worldcon_spike_test.py`, including
    omitted-when-empty tests for the new key and pointer, like the ones that assert the absence of
    the Heinlein key (`heinlein_test.py:259-260, 331`; `worldcon_spike_test.py:1480-1481`); and
  - documentation that enumerates the Heinlein stage: `experimental/science_fiction_analysis_trial/README.md`,
    `definitions.md` and `heinlein_canary_runbook.md`.

## Non-Goals

- No implementation, prompt, rubric, fingerprint, or contract change in this proposal.
- No claim that the design is validated: the evidence is six hand-classified stories by one
  rater, not a measurement and not a corpus sample.
- No change to the five-criterion prompt.
- No decision on the open questions below; each has a recommendation for the owner.

## Implementation Plan

Recommended work items, in order, none created by this proposal:

1. **Contract and validators.** The premise, timeline, interval, relation and flag records, the
   rules R2 to R8, the profile table, the provenance version, and the sidecar optional kind
   with the changes listed under Compatibility. Depends on this proposal's adoption.
2. **Stage, prompt and tool schema.** The opt-in flag, prompt version, a prompt and schema that
   produce the premises, the date inputs, and the author-frame `essential` and `causal`,
   payload with date
   inputs, the paid-run gate rule, fake-backend support, and no-cost tests. Depends on 1.
3. **Date-source tooling.** Loading owner-supplied dates and an owner override; evaluating a
   bibliographic source's coverage and terms before relying on it. Depends on 1.
4. **Fact table seed.** The small audit table of known cases with cited sources. Depends on 2.
5. **Rendering and report integration.** Show the profile, the conditions, and the flags.
   Depends on 1 and 2.
6. **Live validation run.** The seven-story, three-trial design from WI-SF-0119 on a private
   server with request records, comparing the model's premise lists with the hand trial.
   Depends on 2 to 4 and on WI-SF-0120 and WI-SF-0121 (both resolved).
7. **Decide whether the five-criterion prompt later changes.** Only after the live run.

## Cross-References

- `lcats/project/work_items/proposed/WI-SF-0123.md`, the work item that asked for this.
- `lcats/experimental/science_fiction_analysis_trial/heinlein_temporal_premise_trial.md`, the
  six-story trial this design rests on.
- `lcats/experimental/science_fiction_analysis_trial/heinlein_canary_followup_bell_control.md`,
  the WI-SF-0119 finding and the control stories.
- `lcats/project/design/proposals/adopted/knight-novum-analysis-sidecar/00_proposal.md`, the
  governing design for the analysis sidecar.
- WI-SF-0120 (request records) and WI-SF-0121 (private-server runbook), prerequisites for the
  live validation run.

## Open Questions

Each has a recommendation; none is decided here.

1. **Backward differences and historical fiction for `different`.** *Resolved by the owner.*
   The time of the setting is not a difference in either direction; a premise is novel only if
   it departs from the author's real world, including the author's real past. Historical fiction
   faithful to the author's history is not different, while an alternate history, a time-travel
   element, or any other novel condition is. Stipulated departures from history are modelled as
   `counterfactual_divergence` premises (R1, R4). The remaining question is how the stage tells a
   faithful period setting from a quiet departure; the first live run should include a
   historical-fiction control and an alternate-history control to check it.
2. **Coherence with a story's own premises.** A fantasy can be consistent with its own premises,
   so coherence does not test the relation to established facts. Recommendation: do not report
   it as a condition; if wanted, report it as a separate, labelled field after the first live
   run.
3. **Profile category names.** Recommendation: the names in R7, to be reviewed by the owner
   before implementation.
4. **Whether the five-criterion prompt later changes.** Recommendation: no change until the
   live run shows how the existing prompt behaves on the period stories.
5. **Essential and causal in the author's frame.** R8 has the new stage assess them against its
   author-time premises, and takes only `human` from the existing record. Remaining question:
   whether `human` also needs reassessment. Recommendation: copy it in the first
   implementation, and compare the two records' statuses in the live run to see whether any
   differ for a reason the frame explains.
6. **Model knowledge cutoff and recall.** Recommendation: record the cutoff and the analysis
   date with every result, require the stage to name each fact and date, and add the fact
   table as an audit layer (work item 4).
7. **What a first live run must show.** Recommendation: the model's premise lists match the
   hand trial closely enough that the owner accepts the disagreements; the lists are stable
   across three trials; and model-asserted dates are reviewed against the table where it
   covers them.
8. **Date sources.** ISFDB coverage and terms have not been checked; several dates in the trial
   rest on sources I did not open. Recommendation: work item 3 evaluates a bibliographic source
   before it is relied on, and the owner's override always wins.
9. **Where the new record lives.** Recommendation: a new optional analysis kind in the same
   sidecar (`analyses.heinlein_temporal`), omitted when empty, with the changes under
   Compatibility. The alternative is a separate sidecar file, which would avoid touching the
   sidecar contract but split a story's analyses across two files; decide before work item 1.
10. **Cost.** One additional call per story. Recommendation: measure it in the live run; it is
    not estimated here.
