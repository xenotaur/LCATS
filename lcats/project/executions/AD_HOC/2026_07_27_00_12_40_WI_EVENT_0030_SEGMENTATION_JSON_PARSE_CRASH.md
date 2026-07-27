---
execution_id: 2026_07_27_00_12_40_WI_EVENT_0030_SEGMENTATION_JSON_PARSE_CRASH
prompt_id: PROMPT(AD_HOC:WI_EVENT_0030_SEGMENTATION_JSON_PARSE_CRASH)[2026-07-27T00:12:32-04:00]
work_item: AD_HOC
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/167
commit: 017346f1
agent: claude_app
instruction_source: chat session (real Step-4 run with --model haiku after PR #166 landed)
session_transcript: pending
created_at: 2026-07-27T00:12:40-04:00
---

# Summary

A real run of `run_pilot.py` with `--model claude-haiku-4-5-20251001` (a
cheaper model suggested for shakedown runs) crashed with an uncaught
`ValueError: No JSON found in the string.` on the very first story's
segmentation call, killing the whole ~$2.50 run. Root cause: a
pre-existing gap in `JSONPromptExtractor.extract()`, unrelated to PR #166's
quota/abort work - it only caught `json.JSONDecodeError` around
`utils.extract_json()`, but that function raises a plain `ValueError` (a
JSONDecodeError superclass, not a subclass) when the model's raw output has
no JSON and no fenced code block at all - exactly what happens when a
cheaper model ignores the requested JSON format and returns prose instead.

# Result

- `lcats.analysis.llm_extractor.JSONPromptExtractor.extract()`'s parse step
  (`except json.JSONDecodeError`) widened to `except ValueError` - this
  still catches `json.JSONDecodeError` (it's a `ValueError` subclass) and
  additionally catches the "no JSON found at all" / "multiple code blocks"
  / "wrong fence format" cases raised by `lcats.utils.compat.extract_json`. A
  bad model response now falls through to the existing `parsing_error`
  path (already fully supported downstream - `run_story` already turns a
  non-empty `extraction_error` into a per-story exclusion) instead of
  crashing the whole batch.
- Added `test_no_json_at_all_sets_parsing_error` (plus keeping the
  existing `test_invalid_json_sets_parsing_error` for the fenced-but-invalid
  case) to `llm_extractor_test.py`, asserting a plain-prose response
  produces `extraction_error="parsing_error"` rather than raising.
- Note on process: this fix was first drafted on the wrong branch (this
  worktree's original stale branch, which predates `run_pilot.py` and
  WI-EVENT-0030 entirely) after switching back to it post-PR-166-closeout;
  caught immediately via `lrh validate`'s test count dropping from 1439 to
  1347, discarded with `git checkout --`, and redone cleanly from
  `origin/main`.

# Validation

- `scripts/format --check --diff` / `scripts/lint` - clean.
- `scripts/test` - 1439 tests pass (1 new).
- `lrh validate` - 0 errors, 43 pre-existing unrelated warnings.
- Manual repro: constructed a `JSONPromptExtractor` with a `FakeBackend`
  returning plain prose (no JSON/fence at all) and confirmed
  `extract()` now returns `extraction_error="parsing_error"` instead of
  raising `ValueError`.

# Follow-up

- `session_transcript: pending` should be updated to `claude-app:<session-id>`
  after this session ends.
- The user's real run is still not complete - this fixes the crash but the
  actual Step-4 pilot data collection (and Steps 5-7: results write-up and
  WI-EVENT-0030 closeout) still needs a clean re-run after this lands.
- Worth revisiting later: whether `scene_analysis.make_segment_extractor`
  should pass a `tool` schema (structured tool-call output) rather than
  relying on free-text JSON parsing, which would sidestep this whole class
  of failure for models less reliable at unprompted JSON formatting - out
  of scope for this fix (forbidden_actions on WI-EVENT-0030 restrict
  touching the shared extractor/processor modules beyond what's needed).
