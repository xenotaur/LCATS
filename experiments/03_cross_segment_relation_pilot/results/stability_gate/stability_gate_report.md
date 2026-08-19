# WI-PILOT-0067 Stability Gate Report

## Predeclared Run Plan

- Mode: real run
- Model: `claude-opus-4-8`
- Story count: 2 validated, well-formed fixture stories
- Story set: `king_of_the_hill`, `unwelcomed_visitor`
- Expected real call count: about 12-22 Anthropic calls (2 genre-detect + 2 segmentation + 4 ERW calls per segment + up to 1 cross-segment relation call per story)
- Expected artifacts: `pilot_stories.jsonl`, `pilot_usage.jsonl`, `pilot_summary.json`, `genre_detection_results.json`, `stability_gate_results.json`, `stability_gate_report.md`
- Checkpoint policy: isolate the run under `results/stability_gate/`; stage fingerprints include model/backend/input state, so dry-run fake checkpoints do not satisfy the real Opus run.

## Predeclared Thresholds

- `fixture_story_completion_rate`: `1.0`
- `parseable_artifacts`: `True`
- `fatal_pilot_errors`: `0`
- `schema_invalid_or_truncation_marked_final_artifacts`: `0`
- `genre_correctness_rate`: `1.0`
- `source_supported_semantic_output`: `True`
- `intended_purpose_fit`: `True`

## Mechanical Results

- Mechanical pass: `False`
- Completed stories: 1/2
- Genre correctness: 2/2
- Independent well-formedness pass: 1/2
- Fatal pilot errors: 0
- Schema/truncation-marked final artifacts: 0
- Spend evidence complete: `True`
- Total input/output tokens: 34077 / 19025
- Actual spend: $0.6460

## Genre Detection

- `fixtures__king_of_the_hill`: expected `science fiction`, detected `science fiction`, correct `True`
- `fixtures__unwelcomed_visitor`: expected `science fiction`, detected `science fiction`, correct `True`

## Validation Errors

- 1 story row(s) were excluded
- fixtures__unwelcomed_visitor: missing usage stages ['discourse', 'entity', 'event_anchor', 'relation', 'surface_feature']
- 1 genre-detection result(s) failed

Blocking failure modes:

- `fixtures__unwelcomed_visitor` did not complete the pipeline: segmentation failed: alignment failed: ValueError('alignment failed for segment_id=2: anchor text not found in story text').
- `fixtures__king_of_the_hill` was independently marked `wellformed: false`/`verdict: review`: The text appears to be only the closing scene/fragment of a longer story. It opens mid-action ('He sat down before the bombardier board') with no established beginning and relies on prior context (Gascoigne, the confrontation, ULTIMAC) that is not present, indicating this is an excerpt rather than a complete standalone narrative.

## Semantic Review

- Status: `reviewed_fail`
- Source-supported semantic output: `False`
- Intended-purpose fit: `False`

- Gate failed before full semantic acceptance because only 1/2 stories completed: fixtures__unwelcomed_visitor stopped at segmentation with alignment failed for segment_id=2.
- The separate real genre-detection assessment classified both stories as science fiction, but marked fixtures__king_of_the_hill wellformed=false/review because it reads as an excerpt with missing prior context.
- The completed fixtures__king_of_the_hill pipeline output is broadly source-supported for inspection: it identifies the station/bombardier-board scene, Peter/Joan/Joint Chiefs/ULTIMAC entities, and relations around the gun, tape, station-captain test, and possible dud bombs. However, this single completed story cannot satisfy the gate's intended-purpose threshold.

## Recommendation

`fail_no_go`
