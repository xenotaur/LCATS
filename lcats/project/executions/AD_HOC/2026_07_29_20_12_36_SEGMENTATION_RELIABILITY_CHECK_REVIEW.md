---
execution_id: 2026_07_29_20_12_36_SEGMENTATION_RELIABILITY_CHECK_REVIEW
prompt_id: PROMPT(AD_HOC:SEGMENTATION_RELIABILITY_CHECK_REVIEW)[2026-07-29T20:01:53-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/189
commit: f38e0372
created_at: 2026-07-29T20:12:36-04:00
---

# Summary

Address 6 review comments on PR #189 (`check_segmentation_reliability.py`,
the Stage-1-only segmentation verification script for WI-EVENT-0033).
Applying fixes directly rather than through `/lrh-review-response`, per
its own "specific, minimal changes" recommendation for a small, focused
script.

# Result

Six review comments (`chatgpt-codex-connector`), all confirmed valid
against the actual code before fixing:

1. **P1 - cohort mismatch**: the baseline (11/17, 65%) came from
   `run_pilot.py`'s genre-detected, stratified `build_stratified_sample()`,
   not a shuffle over all of `corpora/`, and the baseline's exact story
   list was never persisted anywhere in this repo (confirmed: no
   `pilot_stories.jsonl` survives from any real run). Fixed with a
   `--story-list FILE` flag accepting an explicit cohort (one path per
   line, `#`-comments/blank lines ignored), plus always reporting the
   sampled cohort's word-count distribution (median/min/max) so a rate
   change can be sanity-checked against cohort skew. The docstring now
   documents this limitation honestly under a new "ABOUT THE COHORT"
   section rather than implying a strictly controlled comparison.
2. **P2 - no actual resume**: re-running overwrote every file. Fixed:
   each story's output file is checked first; if present, its cached
   outcome is reused and no `extract()` call is made.
3. **P2 - no abort on batch-fatal errors**: a bad API key would have been
   classified per-story and the run would continue, reporting a
   misleading 100% exclusion rate. Fixed: checks
   `api_error.get("should_abort_batch")` after each call and stops
   immediately, matching `run_pilot.py`'s `FatalPilotError` pattern.
4. **Unguarded file I/O**: malformed JSON would raise and kill the run;
   an empty body would still make a paid call. Fixed: both cases are
   caught before `extract()` is called and recorded as distinct outcomes
   (`story_json_error`, `empty_story_body`).
5. **Wrong exclusion-rate denominator**: `sum(counts)` included the new
   non-LLM outcomes from fix #4, understating the rate (or dividing by
   zero if every file were unreadable). Fixed: a separate
   `llm_calls_made` counter is the denominator; the full outcome
   breakdown (including non-LLM skips) is still reported for
   transparency.
6. **Misdescribed persisted output**: the file claimed to hold "raw LLM
   output" under an `llm_output` key, but that value was actually
   `extracted_output`; `raw_output` is a distinct field that is an empty
   string for every call this script makes (confirmed:
   `AnthropicBackend.complete()` sets `text=""` on the tool-use path -
   `llm_extractor.py:349`, `anthropic_backend.py:105`). Fixed: persists
   both `raw_output` and `extracted_output` under their real names, with
   a code comment explaining why `raw_output` is empty here.

# Validation

- Manual `file:line` verification of all 6 claims against
  `llm_extractor.py`/`anthropic_backend.py`/`run_pilot.py` before
  applying any fix (see Result above).
- A fresh zero-cost fake-backend harness (not reusing the earlier vet
  harness, which wipes its output dir and would defeat a resume test)
  exercising: fresh run persists `raw_output`/`extracted_output`/
  `llm_call_made`/`word_count`; a second run against the same `--output`
  makes zero new calls (resume); an auth-shaped exception on the 3rd of
  6 stories (via a real raised exception through `extract()`'s own
  `_normalize_api_error`/`_classify_api_error` path, not a mocked
  `should_abort_batch` value) stops the run after exactly 3 calls/files;
  a malformed-JSON file and an empty-body file both produce a distinct
  outcome with zero `extract()` calls, alongside one real call for a
  valid file - all assertions passed.
- Verified `--story-list` parses an explicit file list, skipping
  comment/blank lines.
- `black --check --diff` / `ruff check` on the file - clean.
- `scripts/test` (from `lcats/`) - full suite, 1505 passed (unaffected,
  confirms no regression elsewhere).
- `lrh validate` (from `lcats/`) - 0 errors.

# Follow-up

None beyond PR #189's own original follow-up (this script needs a real
API key to actually run; the WI-EVENT-0033 acceptance criterion is still
pending that live run).
