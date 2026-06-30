---
execution_id: 2026_06_30_02_06_30_CREATE_LLM_BACKEND_PACKAGE
prompt_id: PROMPT(WI-LLM-0007:CREATE_LLM_BACKEND_PACKAGE)[2026-06-30T02:06:15-04:00]
work_item: WI-LLM-0007
status: in_progress
rerun_of: 
pr: 
commit: 
created_at: 2026-06-30T02:06:30-04:00
agent: claude_app
instruction_source: conversation
session_transcript: claude-app:d400d14b-0041-4827-8ef9-a8da8fdba9d6
---

# Summary

Implemented WI-LLM-0007: created the `lcats/lcats/llm/` package containing
the `LLMBackend` Protocol, `BackendResponse` dataclass, `FakeBackend` test
double, `OpenAIBackend`, and `AnthropicBackend`, per
`project/design/unified-llm-backend-design.md` (DESIGN-LLM-BACKEND).

# Result

All planned files were created:
- `lcats/lcats/llm/__init__.py`
- `lcats/lcats/llm/backend.py` — `LLMBackend` Protocol (`@runtime_checkable`)
  and `BackendResponse` dataclass
- `lcats/lcats/llm/openai_backend.py` — `OpenAIBackend`
- `lcats/lcats/llm/anthropic_backend.py` — `AnthropicBackend`
  (`use_streaming=True` by default)
- `lcats/lcats/llm/fake_backend.py` — `FakeBackend`
- `tests/llm_tests/backend_test.py`, `openai_backend_test.py`,
  `anthropic_backend_test.py` (19 tests total)
- `pyproject.toml` — added `"openai"` dependency

Two deviations from the work item as originally written, both documented in
the WI-LLM-0007 Scope section:

1. `lcats/llm/__init__.py` does not re-export symbols. `STYLE.md` section 3
   requires "always import modules, not symbols" for LCATS code; the
   originally planned re-export list (`from lcats.llm import LLMBackend`,
   etc.) would have violated this. Callers instead do
   `from lcats.llm import backend` and use `backend.LLMBackend`.
2. Test files use the project's `*_test.py` suffix convention
   (`tests/AGENTS.md`: "Follow existing naming: `*_test.py`"), not the
   `test_*.py` prefix form originally specified in the work item.

Also discovered and fixed in passing: `anthropic` had been added to
`pyproject.toml` in PR #98 but never installed (`scripts/develop` was not
re-run), so it was missing from the active Anaconda environment. Running
`pip install -e ".[dev]"` after adding `openai` picked up both.

# Validation

```
python --version        — Python 3.11.8 (Anaconda environment)
black --version         — black, 26.3.1
ruff --version           — ruff 0.15.12
black --check lcats/llm/ tests/llm_tests/   — all clean (after one
                                               `black lcats/llm/ tests/llm_tests/`
                                               formatting pass on the new test files)
ruff check lcats/llm/ tests/llm_tests/      — all checks passed
python -m unittest discover -s tests/llm_tests -p "*_test.py"  — 19 tests OK
python -m unittest discover -s tests -p "*_test.py"            — 1207 tests OK (full suite)
lrh validate             — 55 errors / 5 warnings (unchanged error count from
                            pre-implementation baseline; +1 warning is the
                            same PLANNING_ORPHANED_ACTIVE_WORK_ITEM pattern
                            already present on the other 4 active/ work items,
                            now also present on WI-LLM-0007 after its move to
                            active/)
```

`scripts/format --check --diff` was run but flagged pre-existing drift in
unrelated files (`lcats/gettenberg/metadata.py` and others) caused by a
Black version mismatch unrelated to this change; the new files were checked
directly with `black --check` instead and are clean.

# Follow-up

- WI-LLM-0008 (migrate `JSONPromptExtractor` and `extraction.py`) and
  WI-LLM-0009 (migrate `assess.py`/`assess_cli.py`) can now proceed in
  parallel, both depending only on this package.
- The repo-wide pre-existing `lrh validate` schema drift (missing
  `type`/`blocked`/`blocked_reason`/`resolution` fields on all work items,
  `contributors.md` gaps) remains untouched, as previously logged in the
  PR #99 closeout follow-up.
- `pr:` and `commit:` fields above are blank pending PR creation; will be
  filled in once a PR is opened and merged.
