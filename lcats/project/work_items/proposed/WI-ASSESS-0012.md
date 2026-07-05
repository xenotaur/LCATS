---
resolution: null
blocked_reason: null
blocked: false
id: WI-ASSESS-0012
title: Extend lcats assess with optional --genre and always-on genre detection
type: deliverable
status: proposed
priority: medium
owner: xenotaur
contributors:
  - xenotaur
assigned_agents: []
related_focus: []
related_roadmap:
  - ROADMAP-CORE
related_workstreams: []
related_design: []
depends_on: []
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - implement_two_api_calls
  - add_new_genre_to_valid_genres
acceptance:
  - "lcats assess <files> (without --genre) returns detected_genre and detected_genre_confidence in every result with genre_verdict: detected"
  - "lcats assess <files> --genre horror returns genre_verdict in [confirmed, disputed, wrong] plus detected_genre and detected_genre_confidence"
  - "TSV output column headers are identical whether or not --genre is passed"
  - "detected_genre values are constrained to VALID_GENRES + [\"other\"]"
  - "genre_verdict enum is [confirmed, disputed, wrong, detected]"
  - "detected_genre_confidence replaces genre_confidence as the sole numeric genre confidence field"
  - "scripts/test passes with no new failures"
  - "lrh validate reports 0 errors"
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - lcats/lcats/analysis/corpus/assess.py
  - lcats/lcats/analysis/corpus/assess_cli.py
---

# Work Item: WI-ASSESS-0012

## Summary

Extend `lcats assess` so that `--genre` is optional: omitting it enters
detect-only mode, while providing it preserves lens mode (current behavior).
Both modes always return `detected_genre` and `detected_genre_confidence`;
`genre_match` is renamed `genre_verdict` and gains a `"detected"` value for
detect-only mode.

## Problem / Context

The current `lcats assess` requires `--genre` (one of four fixed values),
forcing the user to choose a curation lens before running. When the genre
distribution of a story set is unknown, this is a chicken-and-egg problem:
you need an assessment to determine the genre, but you need a genre to get
an assessment. Kenneth Moorman's parallel genre classification work and the
WorldCon 2026 analysis require identifying genre from mixed-provenance story
sets without prejudging them.

The `genre_suggestion` field partially addresses this when `genre_match: wrong`,
but it is conditional — a story correctly classified returns no independent
genre signal. A design analysis (2026-07-03) conclusively selected Option D
(unified single-call detect + confirm) over two-phase sequential approaches,
to avoid model self-contradiction across separate API calls with different
framing.

## Scope

- Make `--genre` optional in `assess_cli.py` (detect mode when omitted, lens
  mode when provided).
- Add `detected_genre` (always-required; one of VALID_GENRES or `"other"`) and
  `detected_genre_confidence` (always-required; 0.0–1.0) to the tool schema
  and `AssessmentResult`.
- Rename `genre_match` → `genre_verdict` (add `"detected"` sentinel value) and
  `genre_confidence` → `detected_genre_confidence`.
- Add a detect-mode system prompt alongside the existing lens-mode template.
- Update TSV columns to reflect the renamed and new fields.

## Required Changes

1. **`lcats/lcats/analysis/corpus/assess.py`** — tool schema and logic:
   - Add `detected_genre: enum(VALID_GENRES + ["other"])` as always-required.
   - Add `detected_genre_confidence: number` (0.0–1.0) as always-required.
   - Rename `genre_match` → `genre_verdict`; add `"detected"` to the enum.
   - Remove old `genre_confidence` field (replaced by `detected_genre_confidence`).
   - Add `DETECT_SYSTEM_PROMPT` constant (no `{genre}` placeholder) with
     detection-focused framing; model instructed to return `genre_verdict:
     "detected"` and populate `detected_genre`.
   - Update `SYSTEM_PROMPT_TEMPLATE` (lens mode) to instruct the model to
     independently detect genre *first*, then evaluate the claim — reducing
     anchoring bias.
   - Make `genre` parameter of `assess_story()` default to `""` (empty = detect
     mode).
   - Branch on `genre` in `assess_story()`: use `DETECT_SYSTEM_PROMPT` when
     empty, `SYSTEM_PROMPT_TEMPLATE.format(genre=genre)` when set.
   - Include `"Claimed genre: {genre}"` in the user message only when `genre`
     is non-empty.
   - Update `AssessmentResult` dataclass: rename `genre_match` → `genre_verdict`
     (default `"detected"`), rename `genre_confidence` → `detected_genre_confidence`
     (default `0.0`), add `detected_genre: str = "other"`. Use `"other"` (not
     `""`) as the default so error-path results (preflight failure, backend
     exception, missing tool result) satisfy the always-required enum constraint
     without special-casing every call site.
   - Update `assess_story()` result-building code to use new field names.

2. **`lcats/lcats/analysis/corpus/assess_cli.py`** — CLI surface:
   - Remove `required=True` from `--genre`; default to `""`.
   - Update `TSV_COLUMNS`: rename `genre_match` → `genre_verdict`, rename
     `genre_confidence` → `detected_genre_confidence`, add `detected_genre`.
   - Update `_result_to_tsv_row()` for new field names; add `detected_genre`.
   - Update `_write_human()` to display `detected_genre` alongside `genre_verdict`.
   - Update `_dry_run_preview()`: show `(detect mode)` when genre is empty.
   - Update epilog examples to demonstrate both usage patterns.

## Non-Goals

- Do not implement two-API-call detection (detect-then-confirm). The design
  explicitly rejected this for model self-contradiction reasons.
- Do not add new genres to `VALID_GENRES`. The four target genres are fixed for
  WorldCon 2026.
- Do not update historical result artifacts in
  `experiments/02_llm_backend_comparison/results/` for renamed fields — those
  JSONL files are point-in-time records and should remain unchanged.
  **Note:** `experiments/02_llm_backend_comparison/compare_results.py` currently
  reads `genre_match` when computing agreement rates; after the rename it will
  silently report incorrect results. The implementor should update
  `compare_results.py` to use `genre_verdict` as part of this work item, or
  file a follow-up if out of scope.
- Do not run a full corpus re-assessment with the new schema — that is a future
  activity.
- Do not modify `lcats/llm/` or the backend abstraction layer.

## Acceptance Criteria

- `lcats assess <files>` (without `--genre`) completes without error, every
  result has `detected_genre` and `detected_genre_confidence`, and
  `genre_verdict` is `"detected"`.
- `lcats assess <files> --genre horror` returns `genre_verdict` in
  `["confirmed", "disputed", "wrong"]` plus `detected_genre` and
  `detected_genre_confidence` in every result.
- TSV output column headers are identical whether or not `--genre` is passed.
- `detected_genre` values are constrained to VALID_GENRES + `"other"`.
- `genre_verdict` enum values are `["confirmed", "disputed", "wrong", "detected"]`.
- `detected_genre_confidence` is the sole numeric genre confidence field.
- `scripts/test` passes with no new failures.
- `lrh validate` reports 0 errors.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `lcats assess lcats/tests/ --dry-run`
- `lcats assess lcats/tests/ --genre horror --dry-run`

## Risk Notes

- **Breaking schema change**: `genre_match` → `genre_verdict` and
  `genre_confidence` → `detected_genre_confidence` will invalidate any
  downstream consumer reading old JSONL field names. The assess command was
  added in PR #98 (recent); existing outputs are in
  `experiments/02_llm_backend_comparison/results/` and are historical records.
- **Prompt quality**: Both modes require new or modified system prompts.
  Validate manually on 2–3 stories per mode before landing.
- **Detect mode verdict logic**: In detect mode, `detected_genre: "other"`
  should drive `verdict: "exclude"`. The detect-mode prompt must make this
  rule explicit so the model does not include non-target-genre stories.
