---
resolution: null
blocked_reason: null
blocked: false
id: WI-GENRE-0004
title: Full-corpus metadata scan, genre-balanced 100-200 story selection, and bounded Opus validation
type: evaluation
status: proposed
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
  - project/design/proposals/proposed/genre-evidence-sidecars/00_proposal.md
  - project/design/event-role-world-genre-target-reconciliation.md
  - project/work_items/proposed/WI-ASSESS-0051.md
  - project/work_items/resolved/WI-GENRE-0002.md
  - project/work_items/resolved/WI-GENRE-0003.md
  - project/work_items/resolved/WI-LLM-0066.md
  - lcats/src/lcats/analysis/corpus/genre_sidecar.py
depends_on:
  - WI-GENRE-0002
  - WI-GENRE-0003
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
  - run_network_or_cache_build_without_explicit_approval
  - run_paid_sample_before_user_go_ahead
  - write_corpus_sidecars
  - promote_sidecars
  - modify_lcats_annotate
  - modify_lcats_promote
  - change_default_backend_or_model
acceptance:
  - "The metadata-rule prefilter (extended from WI-GENRE-0002) scans the full corpus (not just the 40-story pilot) using read-only cached Gutenberg subject data, and reports per-genre candidate counts/coverage across all 8 VALID_GENRES plus stories with no usable metadata signal"
  - "A deterministic, documented selection procedure draws a genre-balanced (not corpus-proportional) 100-200 story sample from the full-corpus scan, reporting any per-genre shortfall where metadata coverage can't fill the target"
  - "The selected sample and its selection rationale are written as an experiment-local manifest BEFORE any paid model call is made"
  - "A real, gated Claude Opus (or explicitly justified alternative) validation run classifies only the selected sample (not the full corpus), requires explicit user go-ahead, and reports real measured cost (expected ~$45 based on the $0.233/story rate measured in WI-ASSESS-0051's sample)"
  - "The validation run's results are compared against the metadata-rule labels for the same stories, reporting per-genre and per-story agreement/disagreement"
  - "Findings state plainly whether metadata rules + one validation pass are sufficient for the Worldcon paper's genre-balanced sampling needs, or what gap remains"
  - "Results are written as genre.json sidecar-shaped assessment records validating against genre-sidecar-v1 (lcats.analysis.corpus.genre_sidecar, landed via WI-GENRE-0003) under the experiment output directory only - not promoted into corpora/, which remains a separately-gated later step"
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

# Work Item: WI-GENRE-0004

## Summary

Extend the metadata-rule prefilter from `WI-GENRE-0002`'s 40-story pilot to
a full-corpus scan, use it to select a genre-balanced 100-200 story sample
(not a corpus-proportional one), then run one small, gated, real Claude
Opus validation pass against only that sample (~$45 expected, not $435) to
measure whether metadata rules plus one model pass are good enough for the
Worldcon paper's sampling needs. This supersedes `WI-ASSESS-0051`'s
original full-corpus-classifier acceptance criteria with a cheaper,
sidecar-native alternative.

## Problem / Context

`WI-ASSESS-0051` originally scoped a full ~1,868-story Claude classifier
run (~$435/~4.2h). Two things argue against running that: `run_pilot.py`'s
own precedent of a $67.54 spend on real runs before cost-containment
techniques were actually wired in rather than just evaluated
(`WS-PILOT-COST-SUSTAINABILITY`), and `run_census.py`'s identical gap - no
batch/caching/tiering support exists there either
(`experiments/04_genre_census/run_census.py:37` still defaults to
`claude-opus-4-8`). `WI-LLM-0066`'s cost-free local-model alternative
(PR #298) doesn't clearly resolve this either: $0 but ~20.8h projected,
and only 18/20 exact agreement with the Claude sample (the 2
disagreements both under-count humor).

Separately, `PROP-GENRE-EVIDENCE-SIDECARS` is already building toward a
different target shape entirely: per-story append-only `genre.json`
sidecars combining metadata, model, and human evidence, rather than one
classifier's standalone summary table. `WI-GENRE-0002` (resolved, PR #301)
delivered the first real metadata-rule evidence generation, but
deliberately stopped at a 40-story pilot and explicitly forbade both
`run_full_corpus_metadata_labeling` and `implement_100_200_story_sample` -
this item is exactly that deferred next step. `WI-GENRE-0003` (resolved,
PR #314) has since defined and landed the `genre-sidecar-v1`
schema/validator (`lcats/src/lcats/analysis/corpus/genre_sidecar.py`) this
item's output should conform to - its own `forbidden_actions` explicitly
excluded `implement_100_200_story_sample` too, confirming this item as
its deliberately-deferred next step rather than a duplicate.

**Numbering note:** this item was originally drafted and opened as
`WI-GENRE-0003` (PR #305) before `WI-GENRE-0003` was independently
claimed and landed by a concurrent session for the sidecar-validator
work above - renumbered to `WI-GENRE-0004` to resolve the collision. The
two items are complementary, not competing: the validator schema landed
first, this item is the next step that produces real data conforming to
it.

### Duplication search
- In-repo: `WI-ASSESS-0051` covers full-corpus Claude classification (being
  superseded by this item's targeted approach); `WI-LLM-0066` covers local
  model evaluation (resolved, informs but doesn't replace this item);
  `WI-GENRE-0001`/`0002` cover the metadata-rule scaffold and 40-story
  pilot this item extends; `WI-GENRE-0003` defines the sidecar-shape
  validator this item's output conforms to, but explicitly excludes
  running any full-corpus scan or 100-200 story sample itself. No
  existing item combines full-corpus metadata scanning, genre-balanced
  selection, and a bounded validation run.
- Sibling repos / external libraries: none identified.
- Recommendation: proceed, extending `WI-GENRE-0002`/`0003` rather than
  duplicating either.

### Demand search
- Work items: `WI-GENRE-0002`'s own `forbidden_actions` names both
  `run_full_corpus_metadata_labeling` and `implement_100_200_story_sample`
  as deliberately out of its scope - direct demand signal for this item.
- Proposals: `PROP-GENRE-EVIDENCE-SIDECARS` requests exactly this
  trajectory (metadata prefilter -> validated sidecar evidence) as its
  Implementation Plan.
- Recommendation: proceed.

## Scope

- Extend `run_prefilter.py` (or add a new mode) to scan the full corpus's
  cached Gutenberg metadata, not just a 40-story sample.
- Implement a genre-balanced (not corpus-proportional) selection procedure
  targeting 100-200 stories across the 8 `VALID_GENRES`.
- Run one small, gated, real Claude Opus validation pass against only the
  selected sample.
- Compare metadata-rule labels against the validation run's results.
- Write output as sidecar-shaped assessment records validated against
  `genre_sidecar.py`'s `genre-sidecar-v1` schema (`WI-GENRE-0003`),
  experiment-local only.

## Non-Goals

- Do not promote sidecars into `corpora/` - that remains a separate,
  later-gated step per `WI-GENRE-0001`/`0002`'s own Non-Goals.
- Do not run any paid model call without explicit go-ahead on the exact
  sample and estimated cost first.
- Do not modify `lcats annotate` or `lcats promote`.
- Do not run a full-corpus paid classification on any backend - the whole
  point of this item is avoiding that spend.
- Do not change `lcats assess`'s default model or the ERW pipeline's
  routing.

## Acceptance Criteria

(see frontmatter `acceptance:` - kept in sync)

## Validation

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- Full-corpus metadata scan (no-cost, read-only)
- Real Opus validation run only after explicit go-ahead on the reviewed
  sample + cost estimate

## Risk Notes

- **Metadata coverage may be incomplete or uneven per genre** - some
  genres may have too few Gutenberg-sourced candidates to fill a balanced
  100-200 story target; the acceptance criteria require reporting
  shortfalls explicitly rather than silently filling gaps with
  lower-confidence picks.
- **Real $ cost, even if small** - the Opus validation pass still needs
  explicit go-ahead per `forbidden_actions`, same gate discipline as
  `WI-ASSESS-0051` and `WI-LLM-0066` used.
- **Governing proposal still `proposed`, not adopted** - `genre-sidecar-v1`
  itself is defined, tested, and landed (`WI-GENRE-0003`,
  `genre_sidecar.py`), but `PROP-GENRE-EVIDENCE-SIDECARS` remains in
  `proposals/proposed/` pending its governing workstream's closure. If the
  schema changes again before this item executes, the output shape here
  needs to track that.
