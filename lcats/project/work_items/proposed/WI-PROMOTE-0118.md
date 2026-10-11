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
  - "A written note states what a genre sidecar's validity depends on for each of its two assessments separately (the metadata-rule assessment: story identity, Gutenberg URL or id, metadata cache; the model assessment: story text, backend model, run), with evidence from the sidecar fields and the seed pipeline"
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
text changes, a replayed sidecar silently describes old text". The sidecar has no
text-hash field, but what it depends on is not one thing: every one of the 146
evidence records holds two assessments (checked), and they depend on different
inputs.

- **`gutenberg_subject_rules`** is a metadata-rule assessment: `raw_subjects` and
  `raw_rule_matches` from the Gutenberg metadata cache, with provenance
  `gutenberg_id`, `gutenberg_url`, `story_id`, `story_path`, `cache_status` and
  `cache_db_path`. It depends on the story's Gutenberg identity and the cache, not
  on the story text.
- **`lcats.analysis.corpus.assess.assess_story`** is a model assessment, with
  provenance `backend_model`, `input_tokens`, `output_tokens`, `run_id`,
  `story_id` and `story_path`. `run_prefilter.py` produces it by calling
  `assess_story()` on the story file (`run_prefilter.py:1206-1211`), so it depends
  on the story text, the backend model and the run. The experiment's own resume
  cache already fingerprints the story file for exactly this reason
  (`run_prefilter.py:1026-1030`): an assessment must not silently describe an
  earlier version of the story text. The seed pipeline carries no such fingerprint.

An identity check already holds in the data for the first assessment: for all 146
promoted stories, `provenance.gutenberg_url` equals the story's `metadata.url` in
`story.json` (checked, 0 mismatches). `story.json` metadata carries only `author`,
`year`, `url` and `name`, so `gutenberg_id` has no counterpart there. That check
would not detect a story-text edit that stales the model assessment.

A drift unit test, `test_payloads_equal_current_corpora_sidecars`
(`tests/dev_tests/build_genre_seed_manifest_test.py:105`), asserts in CI that the
seed reproduces the current `corpora/` sidecars. It is a CI-time test, not a
release-time check, and the seed tool itself never reads `corpora/`. The practical
risk today is low (priority low, optional). The release framing for 1.0 is that a
seeded sidecar should be detectable when it no longer matches its story. Any
schema change would touch the 146 promoted sidecars and the immutable evidence
file, so a no-new-field option should be assessed first.

Prior art: duplication search found no existing binding or check; demand search
found only the design note's follow-up 4.

## Scope

An investigation that produces a written note: what each of a genre sidecar's
two assessments actually depends on; a comparison of a story-text hash, a seed-time provenance
check against `story.json` metadata, and no new check; a recommendation with the
check location (seed tool, `promote insert`, or `validate_sidecar`); and a go/no-go
on any schema change.

## Required Changes

- Read `genre_sidecar.py`, `build_genre_seed_manifest.py` and the evidence record
  shape to establish what each sidecar field depends on.
- Re-run the 146-record provenance-versus-`story.json` comparison and record the
  result.
- Write the note, or update the design note, recording that the metadata
  assessment and the model assessment depend on different inputs.

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
