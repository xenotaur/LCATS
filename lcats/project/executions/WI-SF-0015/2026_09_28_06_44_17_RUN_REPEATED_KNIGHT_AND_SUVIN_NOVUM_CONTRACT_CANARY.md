---
execution_id: 2026_09_28_06_44_17_RUN_REPEATED_KNIGHT_AND_SUVIN_NOVUM_CONTRACT_CANARY
prompt_id: PROMPT(WI-SF-0015:RUN_REPEATED_KNIGHT_AND_SUVIN_NOVUM_CONTRACT_CANARY)[2026-09-28T06:16:56+00:00]
work_item: WI-SF-0015
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/457
commit: ce8e0d48af931a335eb0703a61e4da2c0d6a82d0
created_at: 2026-09-28T06:44:17+00:00
agent: codex_app
instruction_source: project/work_items/proposed/WI-SF-0015.md
session_transcript: codex-app:01a02338-d9c7-7313-8ed5-fb9c1643bef1
---

# Summary

Implement the bounded two-story Knight/Novum contract canary, persist its
trial artifacts, and produce a proceed/revise/stop report without paid calls,
human annotation, corpus writes, or larger-sample execution.

# Result

Added a dedicated `canary` runner mode, exact two-story manifest, runbook
invocation, regression coverage, and persisted trial artifacts. One no-cost
local trial ran against Ollama `gpt-oss:20b`: the positive story completed with
raw outputs, checkpoints, sidecar, and logs; the negative control produced
malformed/truncated evidence JSON, was retried once under the transient/retry
policy, and then failed with a provider 500 parsing error. The canary report
therefore recommends revise/stop before further trials, paid Opus calls, or a
larger sample.

# Validation

- Focused Worldcon suite: 35 tests passed.
- Full suite with `PYTHONPATH=src`: 2,364 tests passed.
- `lrh validate`: 0 errors, 337 pre-existing warnings.
- Manifest JSON parsing and `git diff --check`: passed.
- Direct Black check on touched Python files: passed.
- Repository wrapper checks report installed-version mismatches (Black
  26.5.1 vs required 25.11.0; Ruff 0.16.2 vs required 0.15.0).

# Follow-up

- Add a local-model-specific malformed tool-output regression and repair path.
- Re-run one two-story local canary after that fix.
- Do not approve paid Opus or 10/146-story execution until both behavioral
  expectations are met.
