---
id: WORKSTREAM-LLM-BACKEND
kind: planning_node
title: Unified LLM Backend Abstraction
status: resolved
stage: closed
related_design:
  - DESIGN-LLM-BACKEND
work_items:
  - WI-LLM-0007
  - WI-LLM-0008
  - WI-LLM-0009
  - WI-LLM-0010
exit_criteria:
  - All LLM API calls under lcats/lcats/ route through LLMBackend (no bare SDK calls outside lcats/llm/)
  - Model string is an injectable parameter for every call in the pipeline
  - Unit tests use FakeBackend; no live SDK calls in the test suite
  - Side-by-side comparison run (WI-LLM-0010) validates both providers produce comparable output
---

# Workstream: Unified LLM Backend Abstraction

## Purpose

Unify all LLM API access in LCATS behind a single injectable `LLMBackend`
Protocol so the provider and model become experiment parameters rather than
code changes. This is required for the WorldCon 2026 paper's model-comparison
experiments.

## Work Items

| ID | Title | Status |
|---|---|---|
| WI-LLM-0007 | Create `lcats/llm/` package with LLMBackend Protocol | resolved |
| WI-LLM-0008 | Migrate `JSONPromptExtractor` and `extraction.py` to LLMBackend | proposed |
| WI-LLM-0009 | Migrate `assess.py` / `assess_cli.py` to LLMBackend | proposed |
| WI-LLM-0010 | Side-by-side model comparison dry run | proposed |

## Governing Design

See `project/design/unified-llm-backend-design.md` (DESIGN-LLM-BACKEND).
