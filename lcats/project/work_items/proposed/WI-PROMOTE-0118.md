---
id: WI-PROMOTE-0118
title: Decide how a seeded genre sidecar is bound to its story
type: investigation
status: proposed
priority: low
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams:
  - WS-SIDECAR-SAFE-PROMOTION
related_design:
  - project/design/genre-sidecars-in-release-workflow.md
  - tools/build_genre_seed_manifest.py
  - src/lcats/analysis/corpus/genre_sidecar.py
  - src/lcats/analysis/corpus/promote.py
  - experiments/05_metadata_genre_prefilter/results/full_scan/validation_results.jsonl
depends_on:
  - WI-PROMOTE-0115
blocked_by: []
blocked: false
blocked_reason: null
resolution: null
expected_actions:
  - read_files
  - edit_file
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - edit_corpora
  - modify_validation_evidence
  - change_genre_sidecar_schema
  - implement_fingerprint
acceptance:
  - "A written note states what a genre sidecar's validity depends on (story identity, Gutenberg source URL or id, the Gutenberg metadata cache, story text), with evidence from the sidecar fields and the seed pipeline"
  - "The note compares at least these bindings: a story-text hash, a provenance-versus-story.json check at seed time (gutenberg_url against metadata.url), and no new check, and recommends one with its check location (seed tool, promote insert, or validate_sidecar)"
  - "The note records a go/no-go on a schema change, noting that a schema change affects the 146 promoted sidecars and the immutable evidence file"
  - "No code, schema, or corpora/ change is made; lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - project/design/ note, or an update to project/design/genre-sidecars-in-release-workflow.md
---

# Work Item: WI-PROMOTE-0118

## Summary

Decide whether and how a seeded genre sidecar is bound to the story it describes,
and where that binding is checked, so a release can detect a seeded sidecar that
no longer matches its story. This is follow-up 4 of the design note
`project/design/genre-sidecars-in-release-workflow.md`.

## Problem / Context

The design note says a genre sidecar carries no story-text hash, so "once story
text changes, a replayed sidecar silently describes old text". The evidence
suggests that premise needs checking. The genre sidecar is a metadata-rule
assessment: its evidence is `raw_subjects` and `raw_rule_matches` from the
Gutenberg metadata cache, with a provenance block holding `gutenberg_id`,
`gutenberg_url`, `story_id`, `story_path` and `cache_status`. It records no story
text.

A weaker identity check already holds in the data: for all 146 promoted stories,
the sidecar's `provenance.gutenberg_url` equals the story's `metadata.url` in
`story.json` (checked, 0 mismatches). `story.json` metadata carries only `author`,
`year`, `url` and `name`, so `gutenberg_id` has no counterpart there. The real
staleness risks look like a story whose source URL or identity changed, or a
changed metadata cache; a text hash would catch neither, and would catch a text
edit the sidecar never depended on.

The seed tool's drift test already checks seeded payloads against `corpora/`, so
the practical risk today is low (priority low, optional). The release framing for
1.0 is that a seeded sidecar should be detectable when it no longer matches its
story. Any schema change would touch the 146 promoted sidecars and the immutable
evidence file, so a no-new-field option should be assessed first.

Prior art: duplication search found no existing binding or check; demand search
found only the design note's follow-up 4.

## Scope

An investigation that produces a written note: what a genre sidecar's validity
actually depends on; a comparison of a story-text hash, a seed-time provenance
check against `story.json` metadata, and no new check; a recommendation with the
check location (seed tool, `promote insert`, or `validate_sidecar`); and a go/no-go
on any schema change.

## Required Changes

- Read `genre_sidecar.py`, `build_genre_seed_manifest.py` and the evidence record
  shape to establish what each sidecar field depends on.
- Re-run the 146-record provenance-versus-`story.json` comparison and record the
  result.
- Write the note, or update the design note, and correct its "describes old text"
  premise if the evidence supports that.

## Non-Goals

- No schema change and no fingerprint implementation; this decides whether one is
  needed.
- No edit to the evidence file or `corpora/`.
- No change to other sidecar kinds; that is `WI-PROMOTE-0117`.

## Acceptance Criteria

- A written note states what a genre sidecar's validity depends on, with evidence.
- The note compares the three bindings and recommends one with its check location.
- The note records a go/no-go on a schema change.
- No code, schema or `corpora/` change is made; `lrh validate` reports 0 errors.

## Validation

- lrh validate
- git diff --stat main
- grep -n "provenance" src/lcats/analysis/corpus/genre_sidecar.py

## Risk Notes

A schema change would touch 146 promoted files and the immutable evidence file, so
prefer an option that needs no new field. Any scan over `corpora/` must be
read-only.
