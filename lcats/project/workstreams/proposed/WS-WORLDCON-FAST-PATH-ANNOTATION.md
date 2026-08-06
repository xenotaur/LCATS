---
id: WS-WORLDCON-FAST-PATH-ANNOTATION
kind: planning_node
title: Fast-path annotation pipeline for the Worldcon 2026 paper dataset
status: proposed
stage: planned
origin: design_review
summary: Deliver PROP-WORLDCON-FAST-PATH-ANNOTATION's lcats annotate command (genre + scene sidecars via the mature lcats assess/scene_analysis extractors), its two prerequisite max_tokens fixes, promote/stats selector fixes, and the actual per-genre annotation run for the Worldcon 2026 paper.
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_design:
  - lcats/project/design/proposals/adopted/worldcon-fast-path-annotation/00_proposal.md
  - lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md
  - lcats/project/work_items/proposed/WI-ASSESS-0031.md
work_items: []
exit_criteria:
  - assess.py's max_tokens=2048 hardcode and scene_analysis.py's missing max_tokens override are both fixed, with real-story evidence the truncation failures no longer reproduce
  - lcats annotate exists, writes genre.json/scenes.json + per-bucket README.md, and iterates story buckets per-collection (never directly against a multi-collection corpus root)
  - lcats annotate writes each sidecar (genre.json, scenes.json) through lcats.utils.checkpoint's atomic-publication + fingerprint pattern, so an interrupted run neither repeats a paid call nor combines sidecars produced under mismatched model/prompt configurations
  - lcats promote's survey_collection validates sidecar content as part of the release gate
  - lcats stats's file-discovery selector is fixed to the canonical find_json_files, with a regression test asserting sidecars are excluded from stats
  - lcats annotate has been run over a small per-genre subset across the current 4 VALID_GENRES, output validated, and per-genre statistics collected
  - All work items resolved and lrh validate reports 0 errors
---

# Workstream: Fast-path annotation pipeline for the Worldcon 2026 paper dataset

## Purpose

This workstream delivers `PROP-WORLDCON-FAST-PATH-ANNOTATION`
(`lcats/project/design/proposals/adopted/worldcon-fast-path-annotation/00_proposal.md`,
adopted this session), which exists because the ERW event/relation
extractor was shown too slow/costly/unreliable (~$110 spent, separate
parallel session) to produce a real dataset for the Worldcon 2026 paper
within its ~10-day timeline. It coordinates building a new `lcats
annotate` command around the two extractors already mature enough to
trust — `lcats assess` (genre) and `scene_analysis` (scene/sequel
segmentation) — fixing the two live bugs that would otherwise break it
immediately, extending `lcats promote`'s release gate to validate the
new sidecars, and fixing a related `lcats stats` selector bug the new
sidecars would otherwise silently corrupt.

## Scope

- Fix `assess.py:328`'s hardcoded `max_tokens=2048` and add a
  `max_tokens` override to `scene_analysis.py`'s
  `make_segment_extractor` (currently has none — the fix must be written
  fresh, following `run_pilot.py`'s `_build_erw_extractors`
  override-pattern precedent, not lifted from anywhere; an earlier claim
  that a fix already existed elsewhere was corrected during PR #226
  review).
- Build `lcats annotate`, following `cli.py`'s existing subcommand
  registration pattern, iterating collections then calling
  `discovery.iter_collection_story_files` once per collection (mirroring
  `promote.py`'s `promote_collections`, never calling that selector
  directly against a multi-collection corpus root), writing
  `genre.json`/`scenes.json` + per-bucket `README.md`. Each sidecar write
  goes through `lcats.utils.checkpoint` (`read_checkpoint`/
  `write_checkpoint`, from the adopted, already-implemented
  `PROP-LCATS-PIPELINE-CHECKPOINTING`/`WS-PIPELINE-CHECKPOINTING`), keyed
  per story-bucket and per sidecar stage, with the model/prompt
  configuration in the fingerprint — an interruption between writing
  `genre.json` and `scenes.json` for a story must not silently pair a
  valid `genre.json` with a `scenes.json` from a resumed run under a
  different configuration, and a resumed run must not re-pay for a stage
  already completed under the same configuration (review finding, PR
  #230).
- Extend `lcats promote`'s `survey_collection` (`promote.py:70-125`)
  with sidecar-content validation as part of the release gate.
- Fix `lcats stats`'s file-discovery selector (`run_stats` currently
  calls the broad `find_corpus_stories`; must use the canonical
  `find_json_files`, matching `survey`/`assess`).
- Run `lcats annotate` over a small per-genre subset (current 4
  `VALID_GENRES`: science fiction, horror, western, romance), validate
  output, and collect per-genre statistics.
- Land all work items through the standard LRH execution lifecycle
  (`/lrh-implement` → `/lrh-review-response` → `/lrh-confirm-fixes` →
  `/lrh-closeout`).

## Prior Art Check

### Duplication search
- In-repo: No existing `lcats annotate` implementation or workstream.
  `PROP-WORLDCON-FAST-PATH-ANNOTATION` itself already ran this search in
  full (see the proposal's own Prior Art Check).
- Sibling repos: None identified.
- External libraries: None identified — this is a thin orchestration
  layer over two already-built in-repo extractors, not a
  general-purpose need.
- Recommendation: Proceed.

### Demand search
- Work items: None found requesting this workstream directly.
  `WI-ASSESS-0031` (4→8 genre extension) is related but explicitly out
  of this workstream's scope — a future dependency of a later expansion,
  not duplicated here.
- Proposals: `PROP-WORLDCON-FAST-PATH-ANNOTATION` (adopted this session)
  requests this workstream directly in its own Implementation Plan.
- Backlog (`project/design/backlog.md`): `lcats stats` selector bug
  (confirmed 2026-08-02, no WI yet) — this workstream is what resolves
  it.
- Recommendation: Proceed.

## Work Items

Not yet created — to be scoped via `/lrh-work-item` after this
workstream lands. Planned breakdown and sequencing:

1. **Prerequisite bug fixes** — `assess.py`'s and `scene_analysis.py`'s
   `max_tokens` overrides. No dependencies; blocks everything else.
2. **`lcats annotate` command** — depends on (1). Includes wiring
   per-sidecar writes through `lcats.utils.checkpoint` (see Scope).
3. **`lcats promote` sidecar validation** — depends on (2) (needs the
   real sidecar shape to validate against).
4. **`lcats stats` selector fix** — independent of (1)-(3); can run in
   parallel, but must land before (5).
5. **Run + stats collection** — depends on (2), (3), (4).

## Exit Criteria

(see frontmatter `exit_criteria:` above)

## Non-Goals

- Does not implement the specials/mojibake audit sidecar — deferred per
  the proposal's own Decision 1; whether it belongs in this project at
  all is still an open, separate design question.
- Does not implement `WI-ASSESS-0031`'s 4→8 genre extension — tracked
  and in progress in a separate parallel session/worktree; this
  workstream's item 5 only consumes it once landed, not before.
- Does not touch ERW event/relation extraction in any way — explicitly
  out of scope, per the parallel cost-sustainability finding motivating
  this whole workstream.
- Does not change `lcats survey`'s CLI-level exclusion-policy
  inconsistency (`DEFAULT_EXCLUDED_CHARS` vs. `excluded=set()`) —
  `WS-SPECIALS-CLEANUP`'s scope, not this workstream's.
- Does not adopt a schema-validation library or new dependency for item
  3's sidecar validation — depth of validation (schema check vs.
  parse-only) is left to work-item design.

## Open Questions

- Exact work-item granularity (5 items as listed above vs. further
  splitting, e.g. separating the two bug fixes) — left to
  `/lrh-work-item` scoping.
- Exact `lcats annotate` CLI flags, story-subset selection criteria, and
  stats-collection approach — left to work-item design, per the
  proposal's own Open Questions.
