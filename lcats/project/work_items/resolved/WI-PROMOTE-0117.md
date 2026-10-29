---
id: WI-PROMOTE-0117
title: Define the release rule for sidecar kinds other than genre.json
type: investigation
status: resolved
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams:
  - WS-SIDECAR-SAFE-PROMOTION
related_design:
  - project/design/genre-sidecars-in-release-workflow.md
  - src/lcats/analysis/corpus/promote.py
  - src/lcats/analysis/corpus/discovery.py
  - src/lcats/analysis/corpus/sidecar_validators.py
  - docs/reference/prepare-corpora-release.md
  - docs/reference/corpus-promotion.md
  - project/work_items/resolved/WI-PROMOTE-0115.md
  - project/work_items/resolved/WI-PROMOTE-0101.md
depends_on:
  - WI-PROMOTE-0115
blocked_by: []
blocked: false
blocked_reason: null
resolution: 'Investigated and merged in PR #499: project/design/sidecar-kinds-release-rule.md states the release rule for sidecar kinds other than genre.json (classify by production path; seed corpora-only sidecars into data/ before replace with create-only insert from a tracked source; never upsert or the override flag; do not write sidecars into corpora/), a no-go on a generic seed mechanism (insert --source already generalizes; verified on scratch copies), and two read-only preflight checks, because the guard does not cover a story missing from the regenerated data/ or an unregistered sidecar name. Found two unregistered per-story sidecars (linguistics.lexicon.json, science-fiction.json), recorded in the backlog; registering them is a code change not done here. The linguistics how-to now targets data/. Seeding of linguistics.json and linguistics.tokens.json was not reproduced (needs a spaCy run).'
expected_actions:
  - read_files
  - edit_file
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - edit_corpora
  - change_promote_replace_semantics
  - implement_generic_seed_mechanism
acceptance:
  - "A written rule states, for every sidecar kind the orphan guard registers today, every way it can be produced (pipeline-produced into `data/`, tranche-promoted into `corpora/`, or both) and what a release does to seed or regenerate it"
  - "The rule gives a go/no-go on a generic seed mechanism, with the evidence for it"
  - "The release preflight question is answered: should it assert that every corpora/ sidecar has a counterpart in data/ after seeding, given the guard dry-run already reports this"
  - "The release runbook states the rule or links it; no code or corpora/ change is made"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - project/design/ rule note, or an update to project/design/genre-sidecars-in-release-workflow.md
  - docs/reference/prepare-corpora-release.md edit, only if the rule changes operator steps
---

# Work Item: WI-PROMOTE-0117

## Summary

State the general release rule for sidecar kinds other than `genre.json`, so the
1.0 corpus release cannot silently lose a different kind of sidecar the way the
genre sidecars would have been lost. This is follow-up 3 of the design note
`project/design/genre-sidecars-in-release-workflow.md`.

## Problem / Context

`WI-PROMOTE-0115` added a runbook step that seeds the regenerated `data/` with
the 146 tranche-promoted `genre.json` sidecars before `lcats promote replace`,
because the orphaned-sidecar guard (`WI-PROMOTE-0101`) blocks a `replace` that
would delete a registered sidecar kind present only in `corpora/`.

That step covers `genre.json` only. The orphan guard consults
`sidecar_validators.registered_filenames()` (`src/lcats/analysis/corpus/sidecar_validators.py`,
`_REGISTRY`), which registers four kinds: `genre.json`, `scenes.json`,
`linguistics.json` and `linguistics.tokens.json`. (`_SIDECAR_REQUIRED_KEYS` in
`promote.py` is a separate survey-time structural check covering only genre and
scenes; it is not the guard's registry.) Today `corpora/` holds 146 `genre.json`
files and no `scenes.json` or `linguistics*.json`, and the guard's docstring cites
an imminent whole-corpus `linguistics.json` rollout. So the genre seed covers
everything that exists now. The risk is prospective: the next sidecar kind
promoted by tranche will meet the same blocked `replace`, and the release
procedure has no rule saying how to handle it.

Priority is framed around the 1.0 release: the corpus release procedure must be
complete and safe, so an operator following the runbook cannot lose evidence
sidecars. It is not driven by WorldCon timing.

Prior art: duplication search found no existing rule for non-genre kinds; demand
search found only the design note's follow-up 3.

## Scope

An investigation that produces a written rule. For every sidecar kind the guard
registers, list every production path that applies (pipeline-produced into `data/`,
tranche-promoted into `corpora/`, or both; for example `genre.json` is
tranche-promoted today and `lcats annotate` can also write it into `data/`), and
what a release does for each path.
Decide whether the existing create-only `insert --sidecar <kind>` seeding
generalizes, or whether a generic seed mechanism is needed. Answer whether a
release preflight should assert that every `corpora/` sidecar has a counterpart in
`data/` after seeding, given that the guard dry-run already reports orphans.

## Required Changes

- Read `sidecar_validators.py` (`_REGISTRY`), `promote.py` and `discovery.py` to
  confirm the registered sidecar kinds and how each is produced and promoted.
- Reproduce the guard on a scratch copy with a synthetic `scenes.json` (never the
  real `corpora/` or `data/`) to confirm the seeding approach generalizes.
- Write the rule into a design note, or into `genre-sidecars-in-release-workflow.md`.
- Add or link the rule from `docs/reference/prepare-corpora-release.md` only if it
  changes what an operator does.

## Non-Goals

- No new seed tooling and no generic seed mechanism; this decides whether one is
  needed.
- No change to `lcats promote replace` semantics or to the orphan guard.
- No edits to `corpora/` or `data/`.
- No story-text fingerprint for genre sidecars; that is a separate follow-up.

## Acceptance Criteria

- A written rule states, for every sidecar kind the orphan guard registers today,
  whether it is pipeline-produced or tranche-promoted and what a release does to
  seed or regenerate it.
- The rule gives a go/no-go on a generic seed mechanism, with the evidence for it.
- The release preflight question is answered with a stated reason.
- The release runbook states the rule or links it; no code or `corpora/` change is
  made.
- `lrh validate` reports 0 errors.

## Validation

- lrh validate
- git diff --stat main
- grep -n "_REGISTRY" src/lcats/analysis/corpus/sidecar_validators.py

## Risk Notes

The registry may be wider or narrower than the docstrings suggest, so every claim
about registered kinds must come from the code, not the design note. A scratch run
that touches the real `corpora/` or `data/` would defeat the purpose; use copies.
