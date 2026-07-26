---
resolution: null
blocked_reason: null
blocked: false
id: WI-ASSESS-0031
title: Extend VALID_GENRES from 4 to 8 target genres
type: deliverable
status: proposed
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams: []
related_design:
  - project/design/event-role-world-genre-target-reconciliation.md
depends_on: []
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - implement_corpus_survey
  - implement_pilot_rescope
acceptance:
  - "VALID_GENRES in lcats/lcats/analysis/corpus/assess.py equals the 8-tuple (science fiction, horror, humor, western, romance, mystery, fantasy, adventure)"
  - "_GENRE_DEFINITIONS includes a defining line for each of the 4 new genres (humor, mystery, fantasy, adventure), matching the existing style"
  - "All 'four genres'/'four target genres' wording in assess.py's prompts and schema descriptions is updated to reflect 8"
  - "A new open (non-enum) secondary-genre field exists on the assessment schema and AssessmentResult, populated regardless of genre_verdict - not just for wrong/disputed lens results like genre_suggestion"
  - "lcats/tests/analysis_tests/assess_test.py is updated for the 8-genre list and the new field, with no hardcoded 4-genre assumptions remaining"
  - "scripts/test passes with no new failures"
  - "lrh validate reports 0 errors"
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - lcats/lcats/analysis/corpus/assess.py
  - lcats/lcats/analysis/corpus/assess_cli.py
  - lcats/tests/analysis_tests/assess_test.py
---

# Work Item: WI-ASSESS-0031

## Summary

Extend `assess.py`'s `VALID_GENRES` from the current 4 genres (science
fiction, horror, western, romance) to the 8 genres confirmed as the Worldcon
2026 paper's real extraction-priority target (adds humor, mystery, fantasy,
adventure), and add an open secondary-genre field so non-priority
categories (war, medical, etc.) remain representable instead of collapsing
into `"other"`.

## Problem / Context

`project/design/event-role-world-genre-target-reconciliation.md` (PR #161,
merged 2026-07-26) resolved a three-way discrepancy over the Worldcon 2026
paper's target genre list and confirmed the real list is 8 genres, not the
4 `VALID_GENRES` currently implements. That document's "Gap 1" identifies
this exact change as the first, unblocking follow-up: `VALID_GENRES` must
grow before any corpus survey (Gap 2) or stratified annotation pilot
re-scope (Gap 3) can target the right genres. Notably, `WI-ASSESS-0012` —
the item that built this classifier — explicitly forbade
`add_new_genre_to_valid_genres`, on the basis that "the four target genres
are fixed for WorldCon 2026." That constraint is now superseded by the
user's 2026-07-26 decision recorded in the reconciliation doc.

### Duplication search
- In-repo: No existing implementation found for an 8-genre `VALID_GENRES`
  or a secondary-genre field. `WI-ASSESS-0012` (resolved) is the prior
  4-genre implementation this item extends, not a duplicate.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: `WI-EVENT-0030` (proposed) references `VALID_GENRES`'s current
  4-genre set as its stratified-pilot sample basis and will need re-scoping
  to 8 genres once this item lands - that re-scoping is Gap 3 in the
  reconciliation doc, a separate follow-up work item, not this one.
- Proposals: None found.
- Backlog: No `project/design/backlog.md` file exists in this repo.
- Recommendation: No action beyond noting the WI-EVENT-0030 dependency above.

## Scope

- Extend `VALID_GENRES` to 8 genres and update all classifier prompt/schema
  text that assumes 4.
- Add an open (non-enum) secondary-genre field so non-priority
  classificatory values survive detect-mode runs.
- Update the existing test file and any other in-repo consumer that
  hardcodes the 4-genre assumption.

## Required Changes

1. **`lcats/lcats/analysis/corpus/assess.py`**:
   - Extend `VALID_GENRES` to `("science fiction", "horror", "humor",
     "western", "romance", "mystery", "fantasy", "adventure")`.
   - Add a definition line to `_GENRE_DEFINITIONS` for each of the 4 new
     genres, matching the existing one-line style.
   - Update the "other" description strings (currently "does not fit any
     of the four target genres", two occurrences) and the classifier
     prompts at `assess.py:149,153,181` (all currently say "four
     genres"/"four target genres") to reflect 8.
   - Add a new open (non-enum) string field to `ASSESSMENT_TOOL`'s
     `input_schema` - e.g. `secondary_genre` - populated in both detect and
     lens mode regardless of `genre_verdict`, distinct from
     `genre_suggestion` (which is schema-gated to only populate for
     `wrong`/`disputed` lens results, per its existing description at
     `assess.py:85-91`). Add the corresponding field to the
     `AssessmentResult` dataclass with a safe empty-string default, and
     populate it in `assess_story()`'s result-building code.
2. **`lcats/lcats/analysis/corpus/assess_cli.py`**:
   - `--genre` choices/help text update automatically from `VALID_GENRES`;
     verify the epilog examples and help wording still read correctly for
     8 genres.
   - Add the new secondary-genre field to `TSV_COLUMNS`,
     `_result_to_tsv_row()`, and `_write_human()`.
3. **`lcats/tests/analysis_tests/assess_test.py`**: update any fixture or
   assertion that hardcodes the 4-genre list, the "four genres" wording, or
   the old field set, and add coverage for the new secondary-genre field
   and at least one of the 4 new genres.

## Non-Goals

- Do not run `lcats assess` at corpus scale (detect or lens mode) - that is
  Gap 2 in the reconciliation doc, a separate work item with its own real
  API-cost estimate.
- Do not re-scope or execute `WI-EVENT-0030`'s stratified pilot - that is
  Gap 3, depends on this item and on Gap 2, and is out of scope here.
- Do not implement a full open-vocabulary genre taxonomy - the new field is
  a single free-text secondary-genre tag, not a structured category system.
- Do not modify the Event-Role-World extractor pipeline itself.
- Do not update historical experiment result artifacts
  (`experiments/01_classify_corpora/`, `experiments/02_llm_backend_comparison/results/`)
  - these are point-in-time records, per the same convention `WI-ASSESS-0012`
  established.

## Acceptance Criteria

- `VALID_GENRES` equals the 8-tuple above.
- `_GENRE_DEFINITIONS` and all classifier prompt text reflect 8 genres, with
  no remaining "four genres"/"four target genres" wording.
- A new open secondary-genre field exists on the schema, `AssessmentResult`,
  and TSV/human output, populated regardless of `genre_verdict`.
- `lcats/tests/analysis_tests/assess_test.py` passes with updated fixtures/
  assertions for 8 genres and the new field.
- `scripts/test` passes with no new failures.
- `lrh validate` reports 0 errors.

## Validation

Run from the repository's `lcats/` directory, per `AGENTS.md`:

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `lcats assess tests/ --dry-run`
- `lcats assess tests/ --genre mystery --dry-run`

## Risk Notes

- **Additive schema change, but verify don't assume**: adding enum values
  and a new field should not break existing consumers, but any downstream
  code with its own hardcoded 4-genre allowlist (e.g.
  `experiments/02_llm_backend_comparison/compare_results.py`, which reads
  genre fields per `WI-ASSESS-0012`'s own risk notes) should be checked.
- **Genre-boundary ambiguity**: the new genres overlap semantically with
  existing ones (mystery vs. horror, fantasy vs. science fiction, humor vs.
  general "literary" material per the old classifier's categories in the
  reconciliation doc) - prompt definitions should be written precisely
  enough to reduce classifier confusion, and validated manually on a
  handful of sample stories per new genre before considering this
  structurally sound (not at corpus scale - see Non-Goals).
