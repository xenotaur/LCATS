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
a composition-date interval, lists the story's material factual premises with the windows in
which each one's truth changed, and reports date-aware plausibility, an outcome relation to
today for each premise, and two flags, all combined by deterministic rules into a profile
instead of a score. The existing `heinlein-five-v1` record, its prompt, and its checkpoints
are not changed.

## Background / Motivation

Two of Heinlein's five conditions compare a story with "the world" without saying which one.
The `different` condition says the conditions "must be different from here-and-now"
(`lcats/src/lcats/analysis/science_fiction/rubric/definitions.py:130`), and the `plausible`
condition says "No established fact shall be violated"
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
   [14 December 1962](https://www.nasa.gov/history/60-years-ago-mariner-2-first-to-explore-venus/),
   and radar showed in 1965 that Mercury does not keep one face to the Sun
   ([Pettengill](https://en.wikipedia.org/wiki/Gordon_Pettengill),
   [a summary of the earlier view](https://astro.if.ufrgs.br/solar/eng/mercury.htm)).
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

The first nine decisions below were made by the owner in conversation and are fixed inputs.
Decisions 10 to 13 are this proposal's recommendations. The wording of each field is a
proposal; names may change in implementation.

### Fixed inputs

**D1. Reference frame.** All five conditions are judged against the author's world at the time
of writing ("the here-and-now in which the story was written"). A today-reading is rejected.
Reasons: the `different` slot says the difference "may lie only in an invention made in the
course of the story" (`definitions.py:130-139`), and an invention is new relative to the
writer's world; a today-reading penalizes successful predictions; the Suvin prompt already uses
the authorial norm. "Written" means composition, not publication, translation, or later
revision; a text revised decades later is recorded with a caveat.

**D2. Premise-first, date-second.** The stage lists the story's material factual premises
first, then asks for a date only when a premise's truth changes inside the story's plausible
date window. A premise is a factual claim about the world that the plot relies on. Decorative
technology and settings that change nothing about the problem are excluded, matching the
existing exclusion in the prompt (`run_worldcon_spike.py:2568-2569`). Materiality reuses the
repository's vocabulary: `central`, `substantial`, `incidental`
(`models.py:49-55`). Only `central` and `substantial` premises count.

**D3. Change windows.** Knowledge changes over a window, from the first credible evidence to a
settled consensus, not on a single date. Each premise carries a window `{start, end}`, a
source for each end, and a basis: `model_asserted`, `table_confirmed`, or `owner_supplied`.
A stable fact has no window. A premise that was never established at any date (for example,
talking animals in a fairy tale) has no start. A date inside the window is `ambiguous`.

**D4. Composition-date interval.** The stage records an interval `{earliest, latest}` built
from sources, strongest first:

1. owner-supplied;
2. a bibliographic first-publication record (ISFDB is the natural candidate; its coverage and
   terms have not been checked);
3. the author's lifespan and career: death is a hard upper bound; birth plus adulthood and
   first publication give lower bounds. The caveats are disputed attribution, collaboration,
   posthumous revision, and translation (the original composition date applies);
4. internal evidence the model can see.

The sources are intersected. Each source is recorded with its kind, value, basis, and a
confidence, and an owner override replaces the result. With no basis at all, the interval is
absent, not guessed.

**D5. Interval-to-status rules.** For one premise with a change window and a composition
interval:

- `present` if the whole interval falls before the window start (the premise held, or was at
  least not contradicted, throughout);
- `absent` if the whole interval falls after the window end (the premise was contradicted
  throughout), or if the premise was never established;
- `ambiguous` if the interval overlaps the window or straddles it;
- `not_assessable` if there is no interval and no window can be placed.

A stable premise is `present` at every date. When the status is `ambiguous` because the date
is uncertain, the output states the condition, for example "present if composed before
1965-07", so a reader knows exactly what to find out. These reuse the existing status
vocabulary (`models.py:41-46`).

**D6. Combining premises.** The story-level status is `absent` if any counted premise is
`absent`, `present` if all counted premises are `present`, and `ambiguous` otherwise. This
mirrors the verdict logic in `heinlein_verdict` (`models.py:362-377`).

**D7. Outcome relation to today, and the calendar-expired flag.** Each premise also gets an
outcome relation to the world today: `stable` (unchanged between composition and today,
whether it held or never did), `still_open`, `realized`, `falsified`, or `not_assessable` (for
example when the model's knowledge cutoff cannot support a judgment). Separately, a premise
that is a dated prediction whose date has passed carries `calendar_expired: true`. The flag is
independent of the relation, because an expired prediction can be falsified or realized.
Calendar-expired claims are reported through the flag and do not count toward the
"plausible now" reading. The analysis date and the model's knowledge cutoff are recorded with
every result.

**D8. Stories with no speculative premises.** Such a story has `plausible` present (derived
by Python, with no evidence required), and the record carries a `speculative_premises` flag:
false, or true with the counts by materiality.

**D9. A profile, not a score.** The result is a profile derived by Python rules. It never
reports a count or a probability, consistent with `heinlein.py:5-8` and the prompt's rule
against scores (`run_worldcon_spike.py:2532-2533`).

### Recommendations

**D10. Derived profile categories.** Python derives a category from the as-written and
as-today plausibility:

| Category | Rule |
|---|---|
| plausible when written | plausibility as written is `present` |
| evergreen | as written `present` and today `present` |
| overtaken | as written `present` and today `absent` |
| fails when written | as written `absent` |
| undetermined | as written `ambiguous` or `not_assessable` |

The names are recommendations (see Open Questions).

**D11. A second derived verdict.** The new record also carries a derived verdict "as
written": the conjunction in `heinlein_verdict` with `different` and `plausible` taken from
the new stage, and `human`, `essential` and `causal` taken from the existing record. The
existing record and its verdict are not changed. A consistency check flags a story whose
existing `essential` or `causal` rests on premises the new stage classifies as not novel
relative to the author's world.

**D12. A separate, opt-in stage.** The new stage is flag-gated like `include_heinlein`
(`run_worldcon_spike.py:163`), with its own prompt version (as `HEINLEIN_PROMPT_VERSION`,
`run_worldcon_spike.py:63`), its own tool schema, and its own analysis kind. It runs after the
evidence stage and consumes the same story text and evidence as the existing stage.

**D13. Handling the model's weak points.** The stage must name each fact and the date it was
established, and mark the claim `model_asserted`. A curated table of known cases (Mars 1965,
Venus 1962, Mercury 1965) is the audit layer in a later phase; it marks matching claims
`table_confirmed` and flags disagreements. For the outcome relation, a fact beyond the
model's knowledge cutoff is `not_assessable`.

### Options considered

| # | Option | Pros | Cons |
|---|---|---|---|
| O1 | Keep the prompt and report `plausible` separately | Nothing to build | Leaves today's knowledge as the implicit reading, which D1 rejects |
| O2 | One as-of date input to the existing stage; run it twice for two readings | Simple | One call per reading; no premise-level audit trail; needs a date up front, which the corpus lacks (`parser.py:1457`) |
| O3 | Put sub-readings inside `plausible` | One record | Changes `HeinleinCriterion` and `HeinleinAnalysis`, which are pinned to `heinlein-five-v1` and exactly five criteria (`models.py:311-345`, `models.py:394-420`); invalidates existing records |
| O4 | **A separate opt-in stage with a premise-first record (chosen)** | Leaves the existing record untouched; follows the optional-stage pattern; reuses the status vocabulary (`models.py:41-46`) | One more model call; relies on the model's recall of dates |
| O5 | A curated fact table alone | Fully auditable and reproducible | Cannot cover a fact it does not list; needs upkeep |
| O6 | O4 plus O5 as an audit layer | Auditability where facts are known | Most to build; phased after O4 |

O4 is chosen because it is the only option that gives the profile and the audit trail
without changing a pinned contract. O1 is rejected by D1, O3 touches a pinned contract, O5
cannot stand alone, and O2 cannot give a premise-level profile. This is a design judgment
based on the repository state described here, not a proof.

## Compatibility

- **Unchanged:** the `heinlein-five-v1` rubric (`models.py:21`), `HeinleinCriterion` and
  `HeinleinAnalysis`, the existing stage's prompt and prompt version, its tool schema, the
  stage fingerprint inputs (`run_worldcon_spike.py:1100`), and existing checkpoints. A
  stage's fingerprint includes its system prompt, tool schema, and payload hash, so the new
  stage has its own and cannot invalidate the old one.
- **Changed, and it must be stated:** the sidecar learns a new optional analysis kind. That
  touches `PARTIAL_SUCCESS_STAGE_NAMES` and the optional-analysis validation in
  `lcats/src/lcats/analysis/science_fiction/sidecar.py:16-26, 145`, and the serialization in
  `models.py:832-846`. These are the same places the Heinlein stage touched when it was
  added, and the existing pattern (omit when empty so earlier sidecars and their
  fingerprints do not change) applies. The sidecar schema version
  (`models.SCIENCE_FICTION_SIDECAR_VERSION`) should be reviewed in the implementing work item.
- **Request records:** the per-attempt request records added by WI-SF-0120 apply to the new
  stage unchanged.

## Non-Goals

- No implementation, prompt, rubric, fingerprint, or contract change in this proposal.
- No claim that the design is validated: the evidence is six hand-classified stories by one
  rater, not a measurement and not a corpus sample.
- No change to the five-criterion prompt.
- No decision on the open questions below; each has a recommendation for the owner.

## Implementation Plan

Recommended work items, in order, none created by this proposal:

1. **Contract and validators.** The premise, change-window, interval, relation and flag
   records, the interval-to-status and combination rules, the profile categories, and the
   sidecar optional kind. Depends on this proposal's adoption.
2. **Stage, prompt and tool schema.** The opt-in flag, prompt version, payload with date
   inputs, fake-backend support, and no-cost tests. Depends on 1.
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

1. **Backward differences and historical fiction for `different`.** A 1950 story set in 1800
   differs from its author's here-and-now just as a story set in 2150 does. The rubric text
   does not say whether a backward difference counts, and the existing prompt excludes only
   "a different setting that changes nothing about the problem" (`run_worldcon_spike.py:2568-2569`).
   Recommendation: do not decide in code; ask the owner, and in the first implementation treat
   a period setting as `different` only if the setting is essential to the plot, recording that
   as the stage's reading.
2. **Coherence with a story's own premises.** A fantasy can be consistent with its own premises,
   so coherence does not test the relation to established facts. Recommendation: do not report
   it as a condition; if wanted, report it as a separate, labelled field after the first live
   run.
3. **Profile category names.** Recommendation: the names in D10, to be reviewed by the owner
   before implementation.
4. **Whether the five-criterion prompt later changes.** Recommendation: no change until the
   live run shows how the existing prompt behaves on the period stories.
5. **Essential and causal in the author's frame.** D11 keeps them from the existing record and
   adds a consistency check. Recommendation: accept for the first implementation; revisit if
   the check fires often.
6. **Model knowledge cutoff and recall.** Recommendation: record the cutoff and the analysis
   date with every result, require the stage to name each fact and date, and add the fact
   table as an audit layer (work item 4).
7. **What a first live run must show.** Recommendation: the model's premise lists match the
   hand trial closely enough that the owner accepts the disagreements; the lists are stable
   across three trials; and model-asserted dates are reviewed against the table where it
   covers them.
8. **Date sources.** ISFDB coverage and terms have not been checked; two dates in the trial
   rest on sources I did not open. Recommendation: work item 3 evaluates a bibliographic source
   before it is relied on, and the owner's override always wins.
9. **Cost.** One additional call per story. Recommendation: measure it in the live run; it is
   not estimated here.
