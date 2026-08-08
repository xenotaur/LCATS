---
resolution: Abandoned as redundant with WI-LLM-0058 (merged via PR #257, https://github.com/xenotaur/LCATS/pull/257), created independently and near-simultaneously by a concurrent session. WI-LLM-0058 is a strict superset -- consolidated 44-story evidence (this item's own WI-ANNOTATE-0054 trial plus WI-ASSESS-0051's 20-story sample), a root-cause hypothesis requirement, two fix candidates including the same output-sanitization approach this item proposed, a go/no-go recommendation for WI-ASSESS-0051's ~$435 full corpus run, and frontmatter-level depends_on wiring into WI-ASSESS-0051 already live on main. This item's one real technical contribution -- that a sanitization fix must not use AssessmentResult.error as its failure channel, verified against annotate.py:160-169 -- was ported into WI-LLM-0058 via PR #263 before this abandonment.
blocked_reason: null
blocked: false
id: WI-ASSESS-0060
title: Sanitize/reject leaked tool-call-syntax artifacts in assess.py's free-text output fields
type: deliverable
status: abandoned
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams: []
related_design:
  - project/work_items/resolved/WI-ANNOTATE-0054.md
depends_on: []
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - adopt_schema_validation_library
acceptance:
  - assess_story detects when a free-text tool-result field (secondary_genre and any other optional string field) contains leaked tool-call-syntax fragments (e.g. "</antml", "<parameter name=") and either strips the artifact or records a warning through a new, non-fatal channel -- never by populating AssessmentResult.error, which annotate.py's _annotate_genre already treats as an unrecoverable failure that drops genre.json entirely
  - A corrupted optional field never prevents genre.json's required fields (detected_genre, summary, etc.) from being written -- verified with a test asserting genre.json is still produced when only secondary_genre is corrupted
  - Regression test reproduces at least one real corrupted secondary_genre value from WI-ANNOTATE-0054's trial data and confirms it's caught, not silently passed through
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/src/lcats/analysis/corpus/assess.py
  - lcats/tests/analysis_tests/assess_test.py
---

## Summary

Add detection/sanitization to `assess.py`'s genre-detection call for a
real data-quality defect discovered during `WI-ANNOTATE-0054`: ~42% of
stories in that item's 24-story trial had a corrupted `secondary_genre`
field — instead of a genre tag, the field contained leaked
tool-call-syntax fragments (e.g. `</antml="secondary_genre">`,
`<parameter name="specials_verdict">`) instead of a genre tag. So a
corrupted value doesn't silently reach `genre.json` looking like valid
data.

## Problem / Context

`assess.py`'s `ASSESSMENT_TOOL` schema includes a `secondary_genre`
free-text string field (`assess.py:107-118`), populated by the model's
native tool-call JSON output and read directly via
`a.get("secondary_genre", "")` (`assess.py:416`) with no validation
beyond the plain `.get()` default. During `WI-ANNOTATE-0054`'s real API run (PR #253,
`claude-opus-4-8`), 10 of 24 stories' `secondary_genre` values contained
leaked tool-call-syntax fragments instead of genuine genre text.

Traced during that item's hand validation: not a parsing bug in
`lcats`'s own code (`anthropic_backend.py` reads the Anthropic SDK's
already-parsed native `tool_use.input` dict — the corruption is present
in the value the model itself wrote for that field) and not prompt
injection from the story text or the tool schema (`assess.py`'s system
prompts and schema descriptions contain no such tags). The corruption
was scoped entirely to `secondary_genre` in that run, and the garbage
consistently appeared right at that field's boundary with the next
schema field, `specials_verdict` — consistent with an intermittent
`claude-opus-4-8` structured-output reliability issue at that specific
field boundary, not a defect in this pipeline's own request/schema
construction. Full evidence, including the 10 affected stories' raw
values, is documented in
`lcats/experimental/annotation_feasibility_trial/stats_report.md`.

### Duplication search

- In-repo: No existing work item addresses this. `WI-ASSESS-0031`
  mentions `secondary_genre` only in the context of adding the field
  itself (the 4→8 genre extension), not this corruption.
- Sibling repos: None identified.
- External libraries: None applicable — targeted detection/sanitization,
  not a schema-validation library (matches this pipeline's existing
  "parse/shape checks only" convention, established for the sibling
  `lcats promote` sidecar-validation work in `WI-ANNOTATE-0052`).
- Recommendation: Proceed.

### Demand search

- Work items: Requested directly by `WI-ANNOTATE-0054`'s closeout note
  and `stats_report.md`'s recommended follow-up (lower priority than
  the other follow-up, `WI-SEGMENT-0059`, since this is cosmetic field
  corruption, not a correctness defect in derived offsets/boundaries).
- Proposals: No existing proposal covers this.
- Backlog: No matching entry in `project/design/backlog.md`.
- Recommendation: Proceed.

## Scope

- Detect the known leaked-tool-call-syntax pattern (e.g. substrings like
  `</antml`, `<parameter name=`) in `assess.py`'s free-text tool-result
  fields, starting with `secondary_genre` (the only field observed
  affected so far, but check other optional free-text fields —
  `exclude_reason`, `genre_suggestion` — for the same vulnerability
  since they share the same unvalidated `.get()` pattern).
- On detection: either strip the artifact (if a clean prefix/suffix can
  be confidently recovered) or flag it through a **new, non-fatal**
  channel — **must not** use `AssessmentResult.error`/`assess_story`'s
  existing failure path, which `annotate.py`'s `_annotate_genre`
  treats as an unrecoverable failure and responds to by discarding
  `genre.json` entirely (`annotate.py:160-169`). At the observed 42%
  corruption rate, routing this optional-field defect through the
  hard-failure channel would turn cosmetic corruption into widespread
  loss of `genre.json`'s required fields for a large fraction of
  stories — a materially worse outcome than the defect itself. (Review
  finding, PR #258 — P1.)
- Add a regression test using a real corrupted value from
  `WI-ANNOTATE-0054`'s trial data (or a synthetic equivalent) to confirm
  detection actually fires, and a second test confirming `genre.json`
  is still written with its required fields intact when only
  `secondary_genre` is corrupted.

## Required Changes

1. In `lcats/src/lcats/analysis/corpus/assess.py`, add a small
   sanitization/detection helper for free-text tool-result field values,
   applied at minimum to `secondary_genre` in `assess_story`
   (`assess.py:416`).
2. Decide and implement the failure mode: strip-and-continue, or
   record-and-flag through a **new** field/channel distinct from
   `AssessmentResult.error` — verify explicitly that neither choice
   causes `annotate.py`'s `_annotate_genre` to treat the story as a
   failed genre-detection call (which would discard `genre.json`
   entirely, per `annotate.py:160-169`). Whichever is chosen must keep
   `genre.json`'s existing required fields (`detected_genre`,
   `summary`, etc.) unaffected and not introduce a new class of
   silently-wrong data. (Review finding, PR #258 — P1.)
3. Add tests to `lcats/tests/analysis_tests/assess_test.py` covering a
   corrupted `secondary_genre` value (reproducing the real pattern from
   `WI-ANNOTATE-0054`'s trial), confirming it no longer passes through
   unflagged, and confirming `genre.json`'s required fields are still
   written when only the optional field is corrupted.

## Non-Goals

- Does not adopt a schema-validation library — targeted detection only,
  matching this pipeline's established Non-Goals convention.
- Does not attempt to prevent the model from generating the artifact in
  the first place — a model-behavior issue outside this codebase's
  control, not something fixable here.
- Does not re-run `WI-ANNOTATE-0054`'s trial or retroactively repair its
  already-committed `genre.json` sidecars — this item fixes the
  underlying pipeline so *future* runs are protected.
- Does not touch the separate `text_segmenter.py` scene-segmentation
  offset-corruption finding from `WI-ANNOTATE-0054` — tracked as its
  own, higher-priority follow-up (`WI-SEGMENT-0059`).

## Acceptance Criteria

- `assess_story` detects when a free-text tool-result field
  (`secondary_genre` and any other optional string field found
  vulnerable) contains leaked tool-call-syntax fragments and either
  strips the artifact or records a warning through a new, non-fatal
  channel — never by populating `AssessmentResult.error`, which
  `annotate.py`'s `_annotate_genre` already treats as an unrecoverable
  failure that drops `genre.json` entirely.
- A corrupted optional field never prevents `genre.json`'s required
  fields from being written — verified with a test asserting
  `genre.json` is still produced when only `secondary_genre` is
  corrupted.
- Regression test reproduces at least one real corrupted
  `secondary_genre` value from `WI-ANNOTATE-0054`'s trial data and
  confirms it's caught, not silently passed through.
- `genre.json`'s existing required fields are unaffected.
- `lrh validate` reports 0 errors.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes

- The detection pattern must be conservative enough not to false-positive
  on a legitimate secondary genre that happens to contain an angle
  bracket or similar character in ordinary prose — favor a narrow,
  specific pattern match (as documented in
  `lcats/experimental/annotation_feasibility_trial/collect_stats.py`'s
  own `_CORRUPTION_MARKERS`) over a broad heuristic.
- This is model-output noise, not a deterministic bug — a fix here
  reduces the blast radius of a known failure mode but cannot guarantee
  it never recurs in a different field or a different corruption shape.

## Dependencies / Order

None. Standalone fix; no other work item depends on this one yet.

## Related Workstream and Designs

- No active workstream currently owns `assess.py` maintenance; this
  item is standalone.
- Related: `project/work_items/resolved/WI-ANNOTATE-0054.md` (where this
  defect was discovered and fully documented).
