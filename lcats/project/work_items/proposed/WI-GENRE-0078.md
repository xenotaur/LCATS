---
id: WI-GENRE-0078
title: Generate three-way genre-evidence comparison report
type: evaluation
status: proposed
priority: medium
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
  - project/design/proposals/adopted/genre-evidence-sidecars/00_proposal.md
  - project/work_items/resolved/WI-GENRE-0004.md
  - project/work_items/resolved/WI-LLM-0074.md
  - experiments/05_metadata_genre_prefilter/run_prefilter.py
  - experiments/04_genre_census/run_census.py
depends_on:
  - WI-GENRE-0004
  - WI-LLM-0074
blocked_by: []
blocked: false
blocked_reason: null
resolution: null
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_report
  - create_pr
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - run_network_or_cache_build_without_explicit_approval
  - rerun_model_assessments
  - modify_existing_validation_evidence
  - modify_corpora
  - promote_any_label_to_ground_truth
  - create_current_adjudication
  - perform_human_adjudication
  - silently_drop_input_errors
acceptance:
  - "The comparison verifies that the Gutenberg/metadata, Claude Opus, and local-model inputs refer to the same 146 story IDs, and fails clearly on missing, duplicate, malformed, or mismatched records"
  - "The comparison verifies that the Opus input contains a uniform provenance.backend_model of claude-opus-4-8, the local-model input contains a uniform provenance.backend_model of gpt-oss:20b, and the two source files have different hashes"
  - "A machine-readable JSONL report contains one record per story with Gutenberg candidates and primary label, Claude Opus label/confidence, local-model label/confidence, pairwise agreement flags, and an explicit three-way agreement category"
  - "Multi-label Gutenberg metadata is represented by an orthogonal metadata_multi_label flag and summary statistic, while every valid row receives exactly one candidate-set-aware agreement category"
  - "A summary JSON reports aggregate agreement counts, per-genre counts, disagreement categories, input errors, provenance, and source-file hashes"
  - "A Markdown report explains the methodology and presents aggregate results, per-genre results, and every disagreement category without treating any source as ground truth"
  - "Tests cover agreement categories, metadata multi-label handling, genre canonicalization, malformed input, duplicate IDs, missing IDs, and mismatched story sets"
  - "Existing validation JSONL files and the tracked corpora/ tree remain unchanged"
  - "scripts/test passes with no new failures"
  - "lrh validate reports 0 errors"
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - experiments/05_metadata_genre_prefilter/compare_validation.py
  - experiments/05_metadata_genre_prefilter/compare_validation_test.py
  - experiments/05_metadata_genre_prefilter/results/full_scan/three_way_genre_comparison.jsonl
  - experiments/05_metadata_genre_prefilter/results/full_scan/three_way_genre_comparison_summary.json
  - experiments/05_metadata_genre_prefilter/results/full_scan/three_way_genre_comparison_report.md
---

# Work Item: WI-GENRE-0078

## Summary

Create a reproducible three-way comparison of the existing 146-story genre
evidence sample:

1. Gutenberg subject/rule labels;
2. Claude Opus `model_detect` assessments; and
3. the local `gpt-oss:20b` model assessments.

The comparison will produce machine-readable and human-readable reports that
show agreement, disagreement, per-genre patterns, input integrity, and
provenance. It will not rerun either model, change existing validation
evidence, modify `corpora/`, assign ground truth, or perform human
adjudication.

## Problem / Context

The 146-story experiment already contains separate genre evidence sources.
The sample itself is selected by `run_full_scan()` in
`experiments/05_metadata_genre_prefilter/run_prefilter.py:1503-1553`, using
`select_genre_balanced_rows()` at lines 611-686.

The primary validation run produces one sidecar record per selected story.
`run_validation()` invokes `assess_story(..., genre="")` at
`experiments/05_metadata_genre_prefilter/run_prefilter.py:1206-1211`, which
creates a `model_detect` assessment rather than evaluating against a
preselected genre. The model wrapper is implemented by
`build_model_assessment()` at lines 466-514.

The linked Opus run contains 146 records and used `claude-opus-4-8`. The
comparison local-model run contains the same 146 story IDs and used
`gpt-oss:20b` through the local OpenAI-compatible endpoint. However, the
results currently exist as separate JSONL files without one consolidated
story-level comparison artifact.

The repository already has comparison precedent in
`experiments/04_genre_census/run_census.py:284-317`, where detected genres
are joined by story ID and summarized as matches, disagreements, missing
records, and extra records. This work item applies that established pattern
to the three available sources while preserving the evidence distinction
between metadata rules, model assessments, and future human judgments.

### Duplication search

- In-repo: No existing artifact was found that compares all three sources
  for this 146-story sample.
- Existing related code: `run_census.py:284-317` provides reusable
  comparison precedent, but it compares a different experiment and does not
  produce this three-way report.
- Existing work items: `WI-GENRE-0004` produced the 146-story selected
  sample and Opus validation evidence; `WI-LLM-0074` produced the local-model
  infrastructure and comparison run. Neither creates this consolidated
  comparison.
- External libraries: None required; the comparison is native analysis code
  over existing JSONL artifacts.
- Verdict: Proceed. This is a bounded evaluation that consumes existing
  evidence and does not duplicate a completed deliverable.

### Demand search

- `WS-GENRE-EVIDENCE-SIDECARS` and
  `project/design/proposals/adopted/genre-evidence-sidecars/00_proposal.md`
  identify comparison across multiple evidence methods as a required
  foundation for later evidence use and possible adjudication.
- The proposal specifically describes an append-only evidence ledger that
  supports comparing multiple methods and later human review
  (`00_proposal.md:119-124`).
- The proposal's implementation plan separately identifies local-model
  comparison and future human review (`00_proposal.md:331-361,
  419-425`).
- No existing work item was found for this exact three-way comparison.
- Verdict: Proceed. The work item satisfies an identified comparison need
  while keeping human adjudication out of scope.

## Scope

- Add a standalone comparison script under
  `experiments/05_metadata_genre_prefilter/`.
- Read, without modifying:

  - `genre_balanced_manifest.jsonl`;
  - the 146-story Claude Opus validation JSONL;
  - the 146-story local-model validation JSONL.

- Join records by stable story ID.
- Validate input integrity before producing results.
- Normalize known genre aliases consistently with existing repository
  conventions.
- Compare:

  - Gutenberg candidate labels and primary candidate;
  - Claude Opus detected genre;
  - local-model detected genre.

- Produce JSONL, summary JSON, and Markdown report artifacts under the
  existing experiment output directory.
- Add focused tests for classification, validation, and failure modes.

## Required Changes

1. Add `experiments/05_metadata_genre_prefilter/compare_validation.py`.

2. Implement explicit input validation:

   - reject malformed JSONL records;
   - reject duplicate story IDs within an input;
   - reject missing story IDs;
   - reject mismatched story-ID sets between inputs;
   - require a uniform `provenance.backend_model` of `claude-opus-4-8` for
     the Opus input;
   - require a uniform `provenance.backend_model` of `gpt-oss:20b` for the
     local-model input;
   - reject identical source hashes;
   - fail clearly rather than silently dropping records.

3. Implement stable genre normalization using the repository's existing genre
   vocabulary and alias conventions.

4. Emit one JSONL record per story containing at minimum:

   - story ID and identifying metadata;
   - Gutenberg metadata candidates;
   - Gutenberg primary candidate;
   - an orthogonal `metadata_multi_label` boolean;
   - Claude Opus detected genre and confidence;
   - local-model detected genre and confidence;
   - metadata/Opus agreement;
   - metadata/local agreement;
   - Opus/local agreement;
   - all-three agreement;
   - an explicit comparison category.

5. Use explicit comparison categories:

   - `all_three_agree`
   - `metadata_opus_only`
   - `metadata_local_only`
   - `models_agree_metadata_differs`
   - `all_three_differ`
   - `input_error`

   Multi-label Gutenberg metadata is not an agreement category. Every valid
   row receives exactly one agreement category using candidate-set-aware
   semantics, and the orthogonal `metadata_multi_label` flag is reported
   separately in per-story output and aggregate statistics.

6. Emit summary JSON containing:

   - input record counts;
   - matched story count;
   - category counts;
   - pairwise agreement counts and rates;
   - per-genre counts;
   - disagreement counts by category and genre;
   - metadata multi-label statistics;
   - input-error statistics;
   - source paths;
   - source SHA-256 hashes;
   - verified model names and run identifiers where present;
   - generation timestamp and comparison version.

7. Emit a Markdown report containing:

   - methodology and limitations;
   - input provenance;
   - aggregate agreement results;
   - per-genre results;
   - complete disagreement listings;
   - explicit statement that no source is treated as ground truth.

8. Add `experiments/05_metadata_genre_prefilter/compare_validation_test.py`
   covering:

   - all-three agreement;
   - each disagreement category;
   - metadata multi-label cases;
   - genre alias normalization;
   - malformed JSON;
   - duplicate IDs;
   - missing IDs;
   - mismatched input sets;
   - deterministic output behavior.

9. Verify that the comparison is read-only with respect to existing
   validation outputs and `corpora/`.

## Non-Goals

- Does not rerun Claude Opus, `gpt-oss:20b`, or any other model.
- Does not modify `validation_results.jsonl`, the local-model comparison
  JSONL, the manifest, or other existing evidence.
- Does not modify files under `corpora/`.
- Does not promote a metadata or model label to ground truth.
- Does not adjudicate disagreements.
- Does not create `current_adjudication`.
- Does not add human labels.
- Does not change the validation pipeline or `model_detect` implementation.
- Does not decide which model should be used for future production labeling.
- Does not promote any evidence into permanent corpus sidecars.

## Acceptance Criteria

See the `acceptance` frontmatter list above. In particular, completion
requires:

- exact 146-story ID alignment across all inputs;
- one complete machine-readable record per story;
- aggregate and per-genre comparison reporting;
- explicit disagreement reporting;
- provenance and source hashes;
- tests for normal and failure paths;
- no changes to existing evidence or corpus data;
- successful repository and LRH validation.

## Validation

- From `lcats/`: `scripts/version tools`
- From `lcats/`: `scripts/format --check --diff -- ../experiments/05_metadata_genre_prefilter/compare_validation.py ../experiments/05_metadata_genre_prefilter/compare_validation_test.py`
- From `lcats/`: `scripts/lint ../experiments/05_metadata_genre_prefilter/compare_validation.py ../experiments/05_metadata_genre_prefilter/compare_validation_test.py`
- From `lcats/`: `scripts/test ../experiments/05_metadata_genre_prefilter`
- From `lcats/`: `lrh validate`
- From the repository root: `git diff --check`
- Manual verification that existing validation JSONL files and `corpora/`
  are unchanged.

## Risk Notes

- A comparison can appear precise while hiding input misalignment. Exact
  story-ID validation and fail-closed behavior are therefore required.
- Gutenberg metadata is potentially multi-label, while model outputs are
  single detected genres. The report must preserve that asymmetry rather than
  presenting all sources as equivalent classifiers.
- Genre aliases can create false disagreements if normalization is
  inconsistent. The implementation must reuse repository conventions and
  test representative aliases.
- Swapped or duplicated model inputs can produce plausible but invalid
  agreement rates because both runs contain the same story IDs. Uniform
  backend-model provenance checks and distinct source hashes are therefore
  required before comparison.
- Agreement is not accuracy. The Markdown report must not describe any
  source as ground truth or imply that the majority label is correct.
- Source files are experiment evidence. The comparison must be append-only
  and read-only with respect to those inputs.

## Dependencies / Order

Depends on:

- `WI-GENRE-0004`, which produced the 146-story manifest and Claude Opus
  validation evidence.
- `WI-LLM-0074`, which produced the local-model comparison run.

No blocking dependency is currently known. This item should be completed
before any future human adjudication or production promotion decision based
on the three-way comparison.

## Related Workstream and Designs

- Workstream:
  `project/workstreams/resolved/WS-GENRE-EVIDENCE-SIDECARS.md`
- Design proposal:
  `project/design/proposals/adopted/genre-evidence-sidecars/00_proposal.md`
- Related implementation precedent:
  `experiments/04_genre_census/run_census.py:284-317`
- Primary evidence-generation code:
  `experiments/05_metadata_genre_prefilter/run_prefilter.py:466-514`
  and `:1206-1211`
