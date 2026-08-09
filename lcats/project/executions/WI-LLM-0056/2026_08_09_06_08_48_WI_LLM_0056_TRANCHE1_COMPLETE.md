---
execution_id: 2026_08_09_06_08_48_WI_LLM_0056_TRANCHE1_COMPLETE
prompt_id: PROMPT(WI-LLM-0056:WI_LLM_0056_TRANCHE1_COMPLETE)[2026-08-09T06:08:39+00:00]
work_item: WI-LLM-0056
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/273
commit: c3174191f25d02122f173ac162c6fb16a982e8e1
created_at: 2026-08-09T06:08:48+00:00
agent: claude_app
instruction_source: project/work_items/proposed/WI-LLM-0056.md
session_transcript: claude-app:6d988910-ee4a-4ccc-af0b-2fb13d91ddc5
---

# Summary

Complete WI-LLM-0056's tranche 1 by running the two candidates
(`ollama_gemma4_12b`, `ollama_deepseek_r1_14b`) left pending at PR #270's
landing, whose Ollama model pulls had been interrupted by unreliable
cafe wifi at the time. This is a direct continuation of the same PR #270
work, split across a network-availability gap rather than a re-scoping.

# Result

Once the user was back on reliable network, both models pulled
successfully (`gemma4:12b` 7.6GB, `deepseek-r1:14b` 9.0GB). Ran each
candidate twice (per this session's decision-grade-evidence standard for
stochastic LLM calls) via a real live local Ollama server:

- `ollama_gemma4_12b`: **failed 2/2** - `tool_choice` never invoked
  (`error_type=no_tool_call`) despite well-formed, schema-shaped JSON
  free text in both responses. Slowest candidate across this entire
  tranche (310.1s/544.1s, 4208/7528 output tokens).
- `ollama_deepseek_r1_14b`: **failed 2/2** - `tool_choice` never invoked;
  unlike `gemma4:12b`'s JSON-shaped output, both responses were plain
  prose (a numbered entity list), a distinct failure signature. Faster
  than `gemma4:12b` (86.7s/109.8s).

Both failures reproduce the exact `tool_choice`-silently-ignored gap
`WI-LLM-0051` characterized on the segmentation stage - now confirmed on
entity extraction too, across 2 different local Ollama models. The
initial draft of this commit described this as one combined "3-provider
tool_choice pattern" together with `gemini_flash`'s failure (landed in
PR #270). The automatic first-push review on this PR (Codex) correctly
caught that this conflates two genuinely different failure mechanisms:
`gemma4:12b`/`deepseek-r1:14b` silently ignore `tool_choice` and return
free text (`finish_reason='stop'`), while `gemini_flash`'s own compat
layer *attempts* the call and its internal filter actively rejects it
(`finish_reason` contains `'function_call_filter:
MALFORMED_FUNCTION_CALL'`, empty content) - a provider-side validation
rejection, not a silent ignore. Verified this distinction directly
against both candidates' committed `results.json` files before applying
the fix (not just trusting the bot's claim), then corrected
`model_comparison/README.md`'s tranche 1 section to describe these as
two separate patterns needing separate follow-up investigation, not one
combined gap.

Wrote real README updates for both candidates (numeric claims traced to
committed `results.json`/`results_run{1,2}.json`), and updated the
top-level tranche-1 summary table and cross-cutting-pattern note.

All 6 tranche 1 cells (Anthropic 2nd tier, OpenAI online, OpenAI offline,
Gemini online, Gemma offline, second open-weight family offline) now
have real, committed, multi-run evidence - 3 succeeded
(`anthropic_haiku`, `ollama_gpt_oss_20b`, and `openai_gpt55` in the
narrower sense of "exercised for real" though it surfaced a schema bug
rather than a clean success), 3 documented failures
(`gemini_flash`, `ollama_gemma4_12b`, `ollama_deepseek_r1_14b`). Per the
user's explicit decision, `WI-LLM-0056` is being resolved with this PR's
landing - the WI's deeper intent (real, committed, per-cell evidence,
not "one working candidate lands for each cell" read completely
literally) is satisfied.

# Validation

- `pip install -e .` - fixed a stale editable install pointing at a
  different worktree (recurring environment issue this session).
- `python -m pytest tests/llm_tests -q` - 52 passed (higher count than
  PR #270's 44 due to concurrent unrelated work merged into `main` in the
  interim - `WI-PILOT-0057`'s prompt-caching tests).
- `black --check --diff` / `ruff check` (CI-pinned versions) on all
  changed files - clean.
- `lrh validate` - 0 errors, pre-existing warnings only.
- 4 real, live Ollama benchmark calls (2 per candidate, not simulated),
  all committed as evidence regardless of the (consistent) failure
  outcome.

# Follow-up

- File a dedicated investigation WI for the two distinct `tool_choice`
  failure patterns found here (Gemma/DeepSeek-R1 silently ignoring
  `tool_choice`, Gemini's own filter actively rejecting an attempted
  call) - now confirmed on entity extraction, not just segmentation -
  treating them as two separate questions, not one combined gap. Per the
  user's explicit decision, this is separate from this evaluation WI.
- Whether `WI-LLM-0051`'s reminder-retry mitigation (40% recovery on
  segmentation) also helps entity extraction is untested - relevant
  input for that follow-up investigation.
- `deepseek-r1:14b`'s default sampling settings were never checked
  against `ollama show deepseek-r1:14b --parameters` (unlike
  `ollama_qwen3_8b`'s candidate-specific temperature override) - whether
  a tuned temperature changes this candidate's outcome is untested.
