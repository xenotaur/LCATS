---
resolution: null
blocked_reason: null
blocked: false
id: WI-EVENT-0030
title: Run stratified cross-segment relation density pilot across genres
type: evaluation
status: proposed
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams:
  - WS-PILOT-CROSS-SEGMENT-DENSITY
related_design:
  - project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md
  - project/design/event-role-world-cross-segment-relations-evaluation.md
  - project/work_items/resolved/WI-GENRE-0004.md
  - project/design/segmentation-alignment-failure-categories.md
  - project/work_items/resolved/WI-SEGMENT-0072.md
depends_on:
  - WI-EVENT-0029
  - WI-ASSESS-0031
  - WI-GENRE-0004
  - WI-EVENT-0078
  - WI-EVENT-0079
  - WI-EVENT-0080
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - modify_event_role_world_extractor
  - implement_new_architecture
  - run_real_llm_calls_without_explicit_approval
  - execute_full_run_before_wi_event_0079_and_0080_gate
  - force_push
  - delete_branch
acceptance:
  - Before this near-final paid run starts, the executor presents the selected model/backend, exact story count or manifest, expected call-count/cost estimate, output root, and checkpoint/resume plan, and receives explicit in-session human approval distinct from any approval granted for WI-EVENT-0080's smaller feasibility run
  - A stratified sample of 5-10 stories per genre (adventure capped at its real corpus availability of 6 stories - see Scope) is run through the Event-Role-World pipeline with the story-level cross-segment relation pass (WI-EVENT-0029) enabled, using all 8 VALID_GENRES lcats assess --genre now classifies (science fiction, fantasy, horror, western, romance, mystery, humor, adventure), drawn from WI-GENRE-0004's already-Opus-validated genre-balanced 146-story set (experiments/05_metadata_genre_prefilter/results/full_scan/validation_results.jsonl) - selecting stories whose model_detect.detected_genre exactly equals the metadata rule's primary target_candidates[0], not merely present anywhere in the candidate list - rather than reclassified independently
  - Per-genre cross-segment-only relation density is reported as a metric computed directly from each story's cross_segment_relations and weakly_inferred_cross_segment_relations lists (count per 1000 words), kept separate from - not folded into - the existing total relations_per_1000_words baseline.summarize_annotations already reports, since that total mixes cross-segment and same-segment counts and cannot by itself confirm or contradict a cross-segment-specific claim
  - The relation types counted toward the headline cross-segment density figure are stated explicitly (all relation_type values are counted, matching how the existing total relations_per_1000_words already counts every type without filtering)
  - Findings state plainly whether the larger sample confirms, weakens, or contradicts WI-EVENT-0028's finding that science fiction/horror shows materially more long-range cross-segment causal chains than the other strata
  - "Each genre's finding is reported alongside the exact metadata-rule/model-detect agreement rate for that genre (detected_genre == target_candidates[0], computed directly from WI-GENRE-0004's committed validation_results.jsonl: 100% fantasy/horror, 90% science fiction/mystery, 83% adventure, 80% humor, 70% romance, 40% western - not WI-GENRE-0004's own looser agrees_with_metadata_rules aggregate, which counts a detected genre appearing anywhere in the candidate list and materially overstates western's reliability (75% loose vs. 40% exact)), so a reader can weigh a low-agreement stratum's density finding against its real labeling uncertainty rather than treating all 8 strata as equally confident"
  - Stories whose run produced any segment- or story-level extraction_errors are excluded from the aggregated density figures (not silently counted as zero/partial) and are reported separately as excluded/failed runs, with a count and reason
  - Results and methodology are recorded under experiments/03_cross_segment_relation_pilot/, per the experiments/README.md numbering convention
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - experiments/03_cross_segment_relation_pilot/README.md
  - experiments/03_cross_segment_relation_pilot/run_pilot.py
  - experiments/03_cross_segment_relation_pilot/results/
---

## Summary

Run a larger, stratified empirical pilot (5-10 stories per genre across
all 8 `VALID_GENRES` — science fiction, fantasy, horror, western,
romance, mystery, humor, adventure — with adventure capped at 6 stories,
its real total corpus availability) measuring cross-segment-only relation
density across genres, using the story-level relation pass WI-EVENT-0029
implemented. This supersedes WI-EVENT-0028's 4-story convenience sample (2
Lovecraft science-fiction/horror stories vs. 1 mystery, 1 general-fiction
story — neither a validated genre stratum) with a properly stratified
measurement using the corpus's actual genre-classification tooling, sizing
the effect precisely enough to support a paper-facing density figure. The
stratified sample is drawn from `WI-GENRE-0004`'s already-produced,
Opus-validated 146-story genre-balanced set rather than independently
reclassified — see Dependencies / Order for why that item's real output
is now available and Scope for the real per-genre corpus counts and
validation-agreement rates it measured.

**Staged execution note (2026-08-22):** `WI-EVENT-0030` is now linked to
`WS-PILOT-CROSS-SEGMENT-DENSITY` as the near-final empirical run, not the
first step after planning. Earlier attempts to run `run_pilot.py` directly
surfaced expensive reliability and cost-control failures, leading to
checkpointing, pilot cost-sustainability, and pilot-improvement work. This
item therefore depends on preregistration (`WI-EVENT-0078`), readiness
(`WI-EVENT-0079`), and a small real feasibility run (`WI-EVENT-0080`) before
execution. `WI-EVENT-0078` may revise this item's exact sample scale before
new density results are observed, including whether this run remains the
5-10 stories-per-genre plan described below or expands toward the full
`WI-GENRE-0004` 146-story Worldcon-scale sample. Approval for
`WI-EVENT-0080`'s small feasibility run is not approval for this near-final
run; this item requires its own explicit in-session spend gate with model,
manifest/story count, expected call-count/cost estimate, output root, and
checkpoint/resume plan before any real LLM call begins.

## Problem / Context

WI-EVENT-0028's investigation (`project/design/event-role-world-cross-segment-relations-evaluation.md`,
merged PR #154) established — via a small, convenience-selected 4-story
reading exercise, not a pipeline run — that SF/horror material exhibits
more long-range cross-segment causal chains than mystery/general-fiction
comparison genres, and recommended building option A (a post-reconciliation
story-level relation pass) to capture them. WI-EVENT-0029 (PR #156) shipped
that architecture. Both work items explicitly flagged that a larger,
stratified pilot should still run before the Worldcon paper publishes any
cross-segment relation density figure, since the 4-story sample was
sufficient only to answer WI-EVENT-0028's yes/no acceptance criterion, not
to size the effect precisely across genres.

### Duplication search
- In-repo: No existing stratified cross-segment relation density
  measurement exists. `experiments/01_classify_corpora/` and
  `experiments/02_llm_backend_comparison/` are unrelated prior experiments
  (genre classification and LLM backend comparison, respectively) but
  establish the `experiments/NN_name/` convention this item follows.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found beyond WI-EVENT-0028's and WI-EVENT-0029's own
  "still needed" follow-up notes.
- Proposals: None found beyond the governing Event-Role-World extractor
  proposal, whose "Resulting scientific claim" section this pilot's
  findings would ground.
- Backlog: No matching entries.
- Recommendation: No action.

## Scope

- Before any real LLM call, present the selected model/backend, exact story
  count or manifest, expected call-count/cost estimate, output root, and
  checkpoint/resume plan, and receive explicit in-session human approval
  specific to this near-final run.
- Select a stratified sample of 5-10 stories per genre covering all 8
  genres `lcats assess --genre` now supports (`science fiction`,
  `fantasy`, `horror`, `western`, `romance`, `mystery`, `humor`,
  `adventure` — see `assess.py`'s `VALID_GENRES`, extended to 8 by
  `WI-ASSESS-0031`). Draw the sample **from `WI-GENRE-0004`'s
  already-produced set**
  (`experiments/05_metadata_genre_prefilter/results/full_scan/validation_results.jsonl`,
  146 stories, `genre-sidecar-v1`-validated) rather than reclassifying
  independently — that set already carries both a metadata-rule label and
  a real, Opus-validated `model_detect` label per story, so this pilot can
  reuse verified genre assessments instead of re-running classification.
  **Require an exact match — `model_detect.detected_genre ==
  gutenberg_metadata_rules.target_candidates[0]` (the primary/selection
  genre) — not `agrees_with_metadata_rules`.** That flag is a looser
  multi-label signal (true whenever `detected_genre` appears *anywhere* in
  `target_candidates`, including a secondary candidate) and materially
  overstates reliability for genres with real cross-genre overlap: of
  western's 15 "agreeing" stories, 7 are actually model-detected as a
  *different* genre entirely (6 as adventure, 1 as romance — mostly
  Jack London stories tagged both `western` and `adventure` by the
  metadata rules) — only 8/20 truly match the western stratum. Using the
  loose flag would silently place adventure/romance-detected stories into
  the western density sample and invalidate the cross-genre comparison. If
  a genre's exact-match pool is smaller than the 5-10 target (a real
  possibility for the lower-agreement genres below, especially western),
  fill the remainder from non-exact-match stories and flag which stories
  those are in the results, rather than silently treating every selected
  story as equally confident.
- **Real per-genre corpus counts and validation-agreement rates, measured
  by `WI-GENRE-0004` (2026-08-21) — use these, not the "roughly 20-40
  stories" placeholder this section previously used before real numbers
  existed. Agreement here is the exact match defined above
  (`detected_genre == target_candidates[0]`), computed directly from the
  committed `validation_results.jsonl` — not WI-GENRE-0004's own
  `agrees_with_metadata_rules` aggregate, which is looser and, for
  western, meaningfully overstates reliability (75% loose vs. 40% exact):**

  | genre | primary-genre stories in full 1,868-story corpus | exact metadata-rule/model-detect agreement |
  |---|---|---|
  | science fiction | 1,308 | 90% (18/20) |
  | fantasy | 120 | 100% (20/20) |
  | western | 46 | **40% (8/20)** |
  | horror | 43 | 100% (20/20) |
  | mystery | 34 | 90% (18/20) |
  | romance | 24 | 70% (14/20) |
  | humor | 20 | 80% (16/20) |
  | adventure | **6** | 83% (5/6) |
  | (no usable metadata signal) | 267 | n/a |

  Science fiction dominates the corpus (1,308/1,868 ≈ 70%, driven by the
  `mass_quantities` collection) — the stratified, non-corpus-proportional
  design here is intentional and necessary to get comparable per-genre
  samples; this table is corpus composition context, not a target this
  pilot's own sampling should mirror.
- **Adventure is a hard corpus-scarcity constraint, not a design
  choice**: only 6 stories in the entire corpus carry adventure as their
  primary metadata-rule genre (confirmed by `WI-GENRE-0004`'s own
  full-corpus scan, which hit exactly this shortfall trying to fill a
  20-story adventure target). This pilot cannot draw more than 6 adventure
  stories no matter the sampling method; use all 6, and report the
  adventure stratum's findings with an explicit small-*n* caveat rather
  than presenting it with the same confidence as the other 7 genres.
- Every other genre has a real candidate pool well above the 5-10 target,
  so no further shortfall handling is needed for them.
- Run the full Event-Role-World pipeline (`processor.process_segments`,
  with `include_cross_segment_relations=True`) over each sampled story
  using a real LLM backend — this pilot requires actual pipeline output,
  not a manual reading exercise like WI-EVENT-0028's.
- Compute the headline metric — cross-segment-only relation density — by
  counting each story's `cross_segment_relations` and
  `weakly_inferred_cross_segment_relations` entries directly (all
  `relation_type` values counted, no filtering) and normalizing per 1000
  words, **not** via `baseline.summarize_annotations(annotations, story)`
  alone, since that function's `relations_per_1000_words` folds
  cross-segment relations into the same total as same-segment ones and
  cannot isolate the cross-segment-specific effect this pilot measures.
  Report the existing folded total alongside the cross-segment-only figure
  for context, clearly labeled as two different metrics.
- Detect and exclude stories whose run produced any segment- or
  story-level `extraction_errors` from the aggregated per-genre figures —
  `processor.process_segments` deliberately catches and records API/
  extraction failures rather than raising, so a transient failure must not
  silently become an undercounted zero in the genre mean. Report excluded/
  failed runs (count and reason) alongside the results.
- Record cost/latency (`PassUsage` records, particularly the
  `"story_relation"` pass) alongside the density findings, since the
  proposal's Cost and baseline requirements apply to this pilot's own run
  as much as to the pipeline itself.
- Report findings plainly: confirm, weaken, or contradict WI-EVENT-0028's
  smaller-sample finding, with the density numbers to support whichever
  conclusion the data shows.

## Dependencies / Order

**Added 2026-07-26 (via `depends_on`):** this item depends on
`WI-ASSESS-0031`, which extends `VALID_GENRES` from 4 to 8 genres per
`project/design/event-role-world-genre-target-reconciliation.md` ("Gap 1").
**Resolved 2026-08-07:** `WI-ASSESS-0031` landed (PR #224) — `VALID_GENRES`
now has all 8 genres.

**Added 2026-08-08 (via `depends_on`), superseded 2026-08-20:** this item
originally depended on `WI-ASSESS-0051` ("Gap 2" — run the
current-classifier full-corpus genre survey). The design doc doesn't name
either work item directly, but its own Gap 3 sequencing
(`event-role-world-genre-target-reconciliation.md:317`) says both
follow-up items ("A", the corpus survey, and "B", this item's re-scope)
depend on Gap 1 landing first, and that A should run before B "so B's
per-genre sampling draws from an actual current genre census rather than
the stale 2025-10 numbers" - i.e. B (this item) depends on A's output,
even though the doc predates either work item's ID.

**Superseded 2026-08-20:** `WI-ASSESS-0051` no longer produces that
census, and — per review on this same PR (`chatgpt-codex-connector`,
`copilot-pull-request-reviewer`) — `WI-GENRE-0004` will not produce a
like-for-like replacement either: its acceptance criteria run
metadata-rule candidate counts/coverage across all 8 `VALID_GENRES` over
the *full* corpus (not classifier-verified — a rule-based prefilter, not
a per-story model classification), then classify only a genre-balanced
100-200 story *sample* with a real, bounded Opus validation pass. Neither
output is a full-corpus verified-classifier census in the sense the
original Gap 3 language ("an actual current genre census") meant. `depends_on`
now points at `WI-GENRE-0004` instead of `WI-ASSESS-0051` regardless —
this item's re-scope should draw on `WI-GENRE-0004`'s actual two outputs
(full-corpus metadata-rule coverage per genre, and the validated sample's
per-genre agreement/disagreement findings) as the best available
current-genre signal, not wait for a full-corpus classifier count that no
work item now plans to produce. `WI-ASSESS-0051`'s own sample-phase data
remains valid evidence but was never itself a full-corpus per-genre
census either. This was flagged as a deliberately out-of-scope follow-up
during `WI-GENRE-0004`'s own PR #305 review (see
`lcats/project/executions/AD_HOC/2026_08_19_23_23_53_WI_GENRE_0003_METADATA_SELECTION_VALIDATION_SELFREVIEW.md`
finding #3) and is resolved here.

**Resolved 2026-08-21 — content re-scoped below using `WI-GENRE-0004`'s
real output.** `WI-GENRE-0004` (`project/work_items/resolved/WI-GENRE-0004.md`)
landed with genuine, real-run evidence (not mocked): a full-corpus
metadata-rule scan (real per-genre candidate counts across all 1,868
stories), a genre-balanced 146-story selection (short only on adventure —
6 of a 20-story target, because only 6 adventure-primary stories exist in
the whole corpus), and a real, gated `claude-opus-4-8` validation pass
against that selection (87.0% overall metadata-rule/model-detect
agreement, real cost $36.32). This is exactly the "actual current genre
census" the original design doc's Gap 3 sequencing was written to wait
for — the Scope/Summary/Required Changes/Risk Notes sections below now
use those real numbers (see Scope's table) instead of the placeholder
"roughly 20-40 stories" estimate this item carried while `WI-GENRE-0004`
was still pending.

## Required Changes

1. Create `experiments/03_cross_segment_relation_pilot/run_pilot.py` (or
   equivalently named script) that selects the stratified sample by
   reading `WI-GENRE-0004`'s already-validated
   `experiments/05_metadata_genre_prefilter/results/full_scan/validation_results.jsonl`
   (all 8 `VALID_GENRES` as strata, requiring the exact-match selection
   defined in Scope — `detected_genre == target_candidates[0]`, not the
   looser `agrees_with_metadata_rules` flag — adventure capped at its real
   6-story pool), runs the Event-Role-World pipeline over each selected story,
   detects and excludes any story with segment- or story-level
   `extraction_errors` from the aggregate, and writes per-story and
   per-genre summary results — computing the cross-segment-only density
   directly from each story's
   `cross_segment_relations`/`weakly_inferred_cross_segment_relations`
   fields, not from `baseline.summarize_annotations`'s folded total alone.
2. Create `experiments/03_cross_segment_relation_pilot/results/` holding
   the raw run output (JSONL/CSV, per the existing `export.py` table
   conventions) needed to reproduce the reported figures, including which
   stories were excluded and why, and which selected stories came from
   the exact-match vs. non-exact-match pool per genre.
3. Create `experiments/03_cross_segment_relation_pilot/README.md`
   documenting the sample selection methodology (all 8 genre strata,
   sourced from `WI-GENRE-0004`'s validated set, the exact-match
   requirement, adventure's real 6-story cap), the metric definitions
   (cross-segment-only density vs. the existing folded total, reported
   side by side), the per-genre density findings alongside each genre's
   exact-match agreement rate, and the comparison against WI-EVENT-0028's
   smaller sample.
4. No changes to `lcats/lcats/analysis/event_role_world/` — this item
   consumes the existing pipeline, it does not modify it.

## Non-Goals

- Does not modify the Event-Role-World extractor's architecture or any of
  its existing passes.
- Does not implement option B or option C — option A is already shipped
  and is the only architecture this pilot measures.
- Does not choose the Worldcon paper's final statistical method — this
  item produces a density measurement input to that decision, not the
  decision itself.
- Does not re-litigate WI-EVENT-0028's yes/no need determination — that
  question is already answered; this item only sizes the effect more
  precisely.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- lrh validate
- manual review of the results README against the raw results data for consistency

## Risk Notes

- **The feasibility approval does not carry forward.** `WI-EVENT-0080` is a
  smaller paid proof-of-life; this item is the larger near-final run and
  must obtain its own explicit approval after the actual sample, model,
  expected call count, cost estimate, output root, and checkpoint/resume
  plan are known.
- Requires real LLM API calls across roughly 40-75 stories (7 genres x
  5-10 stories each, plus adventure's hard-capped 6) — a real cost/latency
  expenditure, not free; size the non-adventure strata toward the lower
  end (5 per genre) if cost becomes a concern, and say so plainly in the
  results README rather than silently shrinking the sample.
- **Adventure's small sample is a real corpus limit, not a methodology
  choice.** Only 6 stories in the entire 1,868-story corpus carry
  adventure as their primary metadata-rule genre (`WI-GENRE-0004`'s own
  full-corpus scan). The other 7 strata target only 5-10 stories each, not
  the 10x figure an earlier draft of this note claimed — adventure's n=6
  is comparably sized to, or only modestly smaller than, most of the other
  strata, not an order of magnitude smaller. Report the adventure
  stratum's findings with an explicit small-*n* caveat regardless, since 6
  is still the smallest stratum and near the low end of the target range.
- **Genre-label reliability varies sharply by genre — western is the real
  outlier, not romance.** Using the exact match this item's selection now
  requires (`detected_genre == target_candidates[0]`, not
  `WI-GENRE-0004`'s own looser `agrees_with_metadata_rules` aggregate),
  agreement ranges from 100% (fantasy, horror) down to a striking **40%
  for western** (8/20 — 7 of the other 15 "loosely agreeing" stories are
  actually model-detected as a different genre, mostly Jack London
  stories the metadata rules tag both `western` and `adventure`), 70%
  (romance), and 80% (humor/science fiction/mystery at 90% each). Roughly
  3 in 5 selected western stories may carry a genre label the model's
  independent read disagrees with — far worse than this item's earlier
  75%-loose-agreement estimate suggested. A "materially more/fewer
  cross-segment relations" finding in a low-agreement genre — especially
  western — may partly reflect genre-labeling noise rather than a pure
  genre effect; report each genre's finding alongside its exact-match
  agreement rate (per the acceptance criteria) so a reader can weigh this
  correctly, and do not treat western's result as anywhere near as solid
  as fantasy's or horror's.
- Genre strata now cover all 8 genres `lcats assess --genre` supports
  (science fiction, fantasy, horror, western, romance, mystery, humor,
  adventure) — WI-EVENT-0028's original mystery/general-fiction comparison
  stories used a different, non-tooling-validated ad hoc split and are not
  directly reproduced by this stratification; the results README should
  note this explicitly so a reader does not assume identical comparison
  genres across the two work items.
- Conflating the cross-segment-only density metric with the existing
  folded `relations_per_1000_words` total would make the pilot's headline
  finding unable to confirm or contradict WI-EVENT-0028's cross-segment-
  specific claim — the two metrics must be computed and reported
  separately, as this item's acceptance criteria require.
- If the larger sample contradicts WI-EVENT-0028's smaller-sample finding,
  that is a valid, complete, and important result — report it plainly
  rather than treating it as a failed pilot.
- **Real cost-gate sample (2026-08-22, 8 stories, `claude-haiku-4-5-20251001`,
  `experiments/03_cross_segment_relation_pilot/run_pilot.py` extended to 8
  genres for this test) — success rate and root cause, not just cost.**
  3 western + 3 adventure (the two lowest-exact-match-agreement genres) +
  2 fantasy (control) were run through the real Event-Role-World pipeline.
  **3/8 (37.5%) succeeded**; real cost **$0.97** (86 LLM-backed calls,
  247,423 input / 193,589 output tokens) — **~$0.12/story-attempted,
  ~$0.32/story-successful**. Corroborates the ~35% success rate already on
  record from the existing partial pilot run
  (`experiments/03_cross_segment_relation_pilot/results/pilot_stories.jsonl`,
  6/17 succeeded).
  - **All 5 exclusions were `segmentation failed: alignment failed:
    ValueError('alignment failed for segment_id=N: anchor text not found
    in story text')`** — not the `parsing_error` failure mode this item
    previously attributed the exclusion risk to (that mode is
    `WI-EVENT-0033`'s still-open, unrelated bug). This is the "near-miss
    anchor" bucket `project/design/segmentation-alignment-failure-categories.md`
    documents.
  - **This is not a pending bug fix — it is a deliberately accepted,
    permanent-for-now exclusion source.** `WI-SEGMENT-0072` (resolved, PR
    #343) evaluated fuzzy-matching recovery for exactly this near-miss
    bucket and explicitly recommended **defer**: a high recovery rate
    isn't worth the false-positive risk of silently moving segment
    boundaries to the wrong text. Production alignment behavior was left
    unchanged. `WI-EVENT-0033` landing would address the *other* failure
    mode but would not move this one.
  - **Practical consequence for sample-size feasibility:** applying a
    ~60-65% exclusion rate to the exact-match pools in the Scope table
    above, western (8 exact-match) and adventure (5-6) are very unlikely
    to reach the 5-10 target even after exhausting their entire pool
    (expected successes ≈3 and ≈2 respectively) — this is now a
    corroborated, real-data-based risk, not a hypothetical one from desk
    research. See closeout note / follow-up discussion for options.
- **Process note: this real-evidence work (2026-08-22/23) happened outside
  `WS-PILOT-CROSS-SEGMENT-DENSITY`'s staged gate sequence
  (`WI-EVENT-0078` preregistration → `WI-EVENT-0079` readiness gate →
  `WI-EVENT-0080` small feasibility pilot), which was independently being
  designed concurrently and landed on `main` (PR #355) partway through this
  same session.** That workstream exists specifically because "direct
  attempts to run `run_pilot.py` already led to expensive bug discovery and
  follow-on checkpointing/cost-sustainability work"
  (`WI-EVENT-0078.md`'s own Problem/Context) - a close description of what
  happened here too. This note records what was actually done, for
  reconciliation into that staged plan rather than silently duplicating or
  bypassing it:
  - Every real run was preceded by an explicit, in-session cost/scope
    presentation and approval (model, story count, estimated cost) before
    any paid call, and a running daily-spend total was tracked against an
    explicit user-set cap ($20/day, preference for far less) - consistent
    with `WI-EVENT-0079`'s and `WI-EVENT-0080`'s own approval-gating intent,
    even though it wasn't routed through their specific artifacts.
  - One real fix was made in response to a negative real result: raising
    the `_ERW_MAX_TOKENS` module constant in
    `experiments/03_cross_segment_relation_pilot/run_pilot.py` from 16384
    to 32768 after a real `event_anchor` extraction call hit the old
    ceiling. This is an
    infrastructure/config ceiling change, not prompt tuning or a threshold
    redefinition, and was independently re-verified on the exact same
    story that had failed before the fix - but it is still the general
    "found a problem via a real paid run, fixed it, re-ran to confirm"
    pattern `WI-EVENT-0079`'s Non-Goals ("does not implement... new
    segmentation fixes") and `WI-EVENT-0080`'s `forbidden_actions`
    (`tune_prompts_after_negative_gate_result`) exist to gate rather than
    leave informal.
  - Total real spend across this session's testing: ~$13.12 (see individual
    run figures above and below), against explicit per-run approval each
    time.
  - **Not yet reconciled:** whether this evidence should be treated as
    satisfying (in whole or part) `WI-EVENT-0079`'s readiness-gate
    acceptance criteria or `WI-EVENT-0080`'s feasibility-pilot acceptance
    criteria, be re-run formally through those items' own artifact
    contracts, or stand as informal input those items separately confirm -
    left as an open question for whoever picks up `WI-EVENT-0078` next,
    not decided here.
- **Follow-up real test (2026-08-22/23): stronger segmentation model +
  raised `max_tokens` ceiling, same 8-story set as above.** After raising
  `_ERW_MAX_TOKENS` to 32768 and overriding `--model-segment
  claude-opus-4-8` (rest of the pipeline stayed on
  `claude-haiku-4-5-20251001`), re-ran all 8 stories (across two real
  calls interrupted once by an exhausted account credit balance - a real
  billing block, not a code issue - and completed after a top-up):
  - **Zero `max_tokens` truncation failures across all 8 stories**,
    including a direct before/after re-test of the exact story
    (`mass_quantities/long_odds__haggard`) that had hit the truncation
    error before the fix - it succeeded cleanly afterward. The fix is
    confirmed, not just plausible.
  - Even so, the headline success rate was still **3/8 (37.5%)** - the
    same as the unfixed baseline, but for a different reason: 3/8 failed
    on the already-known alignment/near-miss category (unchanged, as
    expected), and **2/8 failed on transient infrastructure errors**
    (`overloaded_error` from Anthropic, and a network read timeout) rather
    than a real data or model problem - both hit genres (fantasy) that had
    been 100% reliable in every earlier test.
  - **`run_pilot.py` has no retry logic for transient errors today** - one
    overload or timeout permanently excludes a story from the sample, the
    same as a real alignment or truncation failure. Had those two
    transient failures been retried, this run would likely have reached
    5/8 (62.5%). Unlike the alignment category (deliberately accepted,
    `WI-SEGMENT-0072`) or the old truncation bug (needed a real ceiling
    fix), this looks like a standard, low-risk gap: a bounded
    retry-with-backoff wrapper around transient API errors, distinct from
    `WI-EVENT-0079`'s excluded `implement_batch_api_adoption` scope and not
    a change to segmentation/extractor logic - worth a feasibility look
    before committing it to any of this workstream's gate items.
  - Real cost for this follow-up test: $5.58 (first partial run, aborted
    on exhausted credit) + $4.25 (continued partial run, also hit the
    credit wall) + $2.32 (final remaining 4 stories, after account top-up)
    = **$12.15** for the full 8-story confirmation, on top of $0.97 for the
    original all-Haiku baseline test above.
- **This item is gated, not ready to execute at scale, pending
  `WI-EVENT-0079`/`WI-EVENT-0080`'s own formal readiness/feasibility
  determination (2026-08-23).** `blocked: true` cannot be set here per
  `lrh validate`'s `WORK_ITEM_BLOCKED_STATUS_INVALID` rule (only valid
  with `status: active`; this item is `status: proposed`), so the gate is
  expressed here and via `forbidden_actions`'
  `execute_full_run_before_wi_event_0079_and_0080_gate` instead. Do not
  run this item's near-final 40-75-story sample until
  `WI-EVENT-0079`'s readiness report and `WI-EVENT-0080`'s feasibility
  pilot have each produced their own recommendation
  (`proceed_to_small_feasibility`/`fix_named_blocker`/`stop` for 0079;
  `proceed_to_wi_event_0030`/`fix_named_blocker`/
  `revise_preregistration_before_results`/`stop` for 0080) - this item's
  own real evidence above (validated `max_tokens` fix, confirmed
  transient-error gap, corroborated ~35-38% success rate) is offered as
  input to that formal process, not a substitute for it. See the
  "Process note" entry above for what was and wasn't done through the
  formal gate sequence.

## Related Workstream and Designs

- Design: `project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md`
- Design: `project/design/event-role-world-cross-segment-relations-evaluation.md`
- Work item: `project/work_items/resolved/WI-GENRE-0004.md` — real per-genre
  corpus counts and validation-agreement rates this item's re-scope uses
- Design: `project/design/segmentation-alignment-failure-categories.md` —
  the near-miss anchor failure category hit by this item's cost-gate sample
- Work item: `project/work_items/resolved/WI-SEGMENT-0072.md` — evaluated
  and deferred fuzzy-matching recovery for that same failure category
