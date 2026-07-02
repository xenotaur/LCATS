---
execution_id: 2026_07_02_12_49_29_WI_LLM_0010_BACKEND_COMPARISON
prompt_id: PROMPT(WI-LLM-0010:WI_LLM_0010_BACKEND_COMPARISON)[2026-07-02T12:49:14-04:00]
work_item: WI-LLM-0010
status: landed
agent: claude_app
instruction_source: lcats/project/work_items/proposed/WI-LLM-0010.md
session_transcript: claude-app:d400d14b-0041-4827-8ef9-a8da8fdba9d6
rerun_of: 
pr: "103"
commit: 7865324
created_at: 2026-07-02T12:49:29-04:00
---

# Summary

Implement WI-LLM-0010: side-by-side Anthropic vs. OpenAI backend comparison experiment
for the assess pipeline. Creates `experiments/02_llm_backend_comparison/` with
`run_comparison.py`, `compare_results.py`, `smoke_test.py`, and `README.md`. Also fixes
a breaking API change in `AnthropicBackend`: `temperature` is rejected with HTTP 400 by
`claude-opus-4-8` and later models.

# Result

- Created `experiments/02_llm_backend_comparison/` with full experiment infrastructure
- Created `experiments/README.md` documenting the numbered-experiment convention
- Fixed `AnthropicBackend.complete()` to omit `temperature` for Opus 4.7+/Fable 5 models
- Ran baseline comparison (5 stories each, horror/Lovecraft + western/London):
  - Horror: verdict agreement 3/5 (60%), genre-match agreement 5/5 (100%)
  - Western: verdict agreement 4/5 (80%), genre-match agreement 4/5 (80%)
- Results written to `experiments/02_llm_backend_comparison/results/`

# Validation

- `scripts/test`: 1229 tests, all passed
- `scripts/lint`: no errors in changed files
- `scripts/format --check`: no issues in changed files (pre-existing drift in metadata.py)
- Smoke test confirmed both backends produce real assessments without errors

# Follow-up

- Run `lrh validate` and address any schema drift (tracked separately)
- Close out WORKSTREAM-LLM-BACKEND once WI-LLM-0010 PR is merged
