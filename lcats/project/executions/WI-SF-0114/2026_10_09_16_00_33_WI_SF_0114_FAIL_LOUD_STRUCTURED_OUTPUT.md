---
execution_id: 2026_10_09_16_00_33_WI_SF_0114_FAIL_LOUD_STRUCTURED_OUTPUT
prompt_id: PROMPT(WI-SF-0114:WI_SF_0114_FAIL_LOUD_STRUCTURED_OUTPUT)[2026-10-09T05:49:14+00:00]
work_item: WI-SF-0114
status: in_progress
pr: https://github.com/xenotaur/LCATS/pull/490
commit: a30b4b36750fd6580ec1c2a17fed4528fdcd69a5
created_at: 2026-10-09T16:00:33+00:00
agent: claude_app
instruction_source: project/work_items/proposed/WI-SF-0114.md
session_transcript: pending
---

# Summary

Executed WI-SF-0114 through /lrh-execute: the structured-output stages of the Worldcon spike runner now fail loudly on mismatched or empty model output. Heinlein criteria with the wrong keys, missing fields or an invalid status quarantine the Heinlein stage; an evidence response with a missing or non-list evidence key, or whose candidates are all quarantined, fails the story; an explicit empty evidence list stays valid with a run-log warning; the shared text fallback parses through the new default-off strict_fence option of lcats.utils.extract_json and logs each fenced-JSON unwrap; and the evidence and Heinlein prompts now use the tool schema's key names.

# Result

- Changed experimental/science_fiction_analysis_trial/run_worldcon_spike.py, src/lcats/utils/compat.py, tests/utils_tests/compat_test.py, tests/analysis_tests/science_fiction/worldcon_spike_test.py, and added tests/analysis_tests/science_fiction/fixtures/canary_raw_responses.json (the WI-SF-0113 canary's raw responses with absolute paths removed). PR 490. The live canary was not rerun.
- One existing test encoded the old silent default and was rewritten as test_missing_criteria_fail_the_heinlein_stage_loudly; this follows from Required Changes 1 and 2 but conflicts with the acceptance wording that existing tests pass unchanged.
- A pre-push diff-mode review by a cold subagent found a quadratic regex in the strict fence (replaced with a linear check), untyped optional Heinlein fields (now checked when present), and weak tests (an old zero-record checkpoint resume test was added and mutation-checked, and the empty-list test now asserts the event). Reported but not changed: _existing_evidence_ids still silently drops unknown evidence IDs, and supporting_evidence_ids and rationale may still be omitted.
- Required Change 4, answered without a live call: openai_backend.py forwards strict and the closed schema, Ollama's OpenAI-compatibility page lists tool_choice as unsupported and does not mention strict, and the canary shows the schema was not enforced for gpt-oss:20b (wrong keys in real tool calls and in all six text-fallback stages of trials 1 to 3). Whether a newer Ollama enforces strict is unresolved and deferred to the canary rerun.
- The text fallback is shared by every stage, so any non-JSON text (not only a fenced reply) now fails as a ValueError instead of a JSONDecodeError in Knight and Suvin too; retry and failure classification are unchanged, but anything grouping failures by kind sees the label change.
- Earlier checkpoints for the evidence and Heinlein stages are invalidated by the prompt changes; Knight and Suvin checkpoints are invalidated only where their evidence input differs.

# Validation

- scripts/test: 2544 tests, OK. scripts/format --check --diff and scripts/lint passed with the CI-pinned black 25.11.0 and ruff 0.15.0. The runner file (skipped by scripts/format) shows the same four black hunks and one ruff finding (F601) as main.
- Fake-backend smoke with --include-heinlein processed both manifest stories. lrh validate reported 0 errors; git diff --check was clean.
- Local interpreter Python 3.11.8 with PYTHONPATH set to this checkout's src, because the editable install points at another checkout.

# Follow-up

- Land this PR with /lrh-land, which also resolves WI-SF-0114.
- Rerun the Heinlein canary as its own step (baseline plus three local trials, manifest expectations unchanged), and count fenced_json_unwrapped, no_tool_call_json_fallback and evidence-stage failures in the new report.
- Consider a follow-up on _existing_evidence_ids and the still-optional supporting_evidence_ids and rationale fields.
- Update session_transcript from pending at closeout.
