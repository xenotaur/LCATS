---
id: ROADMAP-CORE
title: LCATS Corpus-to-Narrative Roadmap
status: active
---

# Roadmap

## Status Legend
- **Completed**: finished and recorded.
- **Active**: currently being executed.
- **Planned**: approved next steps, not yet active.
- **Future**: downstream direction after planned phases.

## Phase 1 — Corpus Ingestion (**Completed**)
- Build ingestion and corpus organization workflows.
- Establish baseline corpus handling paths and CLI entry points.

## Phase 2 — Survey + Classification (**Completed**)
- Deliver corpus survey workflow.
- Add classification outputs to identify Unicode/encoding/corpus quality states.

## Phase 3 — Correctness Foundations (**Completed**)
- Apply mojibake precedence fix in classification.
- Tighten correctness interpretation to reduce false-safe classifications.

## Phase 4 — Repair + Review + Application Pipeline (**Active**)
Focus: move from diagnosis to conservative correction and controlled
application.

### Phase 4A: Repair Engine
- Build deterministic, conservative repair planner/executor.
- Require dry-run output before any apply path.

### Phase 4B: Span Operations
- Add span-based transformation primitives for precise edits.
- Ensure operations are composable and traceable.

### Phase 4C: Review Loop
- Add human review/override checkpoints.
- Record decision rationale for accepted/rejected changes.

### Phase 4D: Approved Application
- Apply reviewed and approved span operations to corpus text.
- Ensure deterministic, non-destructive transformation workflow.
- Produce transformed outputs separate from original source.
- Validate that applied operations match reviewed decisions exactly.

## Phase 5 — Persistence / Corpus State (**Planned**)
- Define persistent corpus state and operation history model.
- Support replay/audit across runs and contributors.

## Phase 5.5 — Unified LLM Backend + Scientific Assessment (**Planned**)
Focus: enable model-to-model comparison experiments by unifying all LLM API
calls behind a single injectable `LLMBackend` Protocol, and deliver the
first full corpus quality and genre assessment pipeline.

### Phase 5.5A: LLM Backend Package (WI-LLM-0007)
- Create `lcats/llm/` with `LLMBackend` Protocol, `BackendResponse`,
  `OpenAIBackend`, `AnthropicBackend`, and `FakeBackend`.
- Full unit tests; no existing code changes.

### Phase 5.5B: JSONPromptExtractor Migration (WI-LLM-0008)
- Migrate `llm_extractor.py` to `LLMBackend`; update test mocks.
- Covers `scene_analysis.py` and `story_analysis.py` by transitivity.

### Phase 5.5C: Assess Pipeline Migration (WI-LLM-0009)
- Migrate `assess.py` and `assess_cli.py` to `LLMBackend`.
- `assess.py` gains no direct SDK dependency.

### Phase 5.5D: Side-by-Side Comparison Dry Run (WI-LLM-0010)
- Run `assess` pipeline on 5–10 stories per genre with both backends.
- Confirm identical output schema; record baseline agreement rates.
- Commit results to `experiments/llm_backend_comparison/`.

## Phase 6 — Narrative Structure + Reasoning (**Future**)
- Introduce structured narrative representations.
- Add reasoning workflows integrating Propp, Greimas, CBR, and RAG techniques.

## Alignment Notes
- Completed phases are logged in `project/memory/decision_log.md`.
- Active work spans Phase 4 (repair/review), story-analysis-pipeline foundations feeding the
  Medium-Term Goal, and the WS-DOCS documentation cleanup — see
  `project/focus/current_focus.md` for the current multi-priority focus.
