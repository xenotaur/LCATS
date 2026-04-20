# Design

## Purpose
- Provide an LRH-compatible control plane for LCATS, a toolkit for story corpora management and LLM-assisted analysis/extraction.

## Scope
- Define interpretation and execution artifacts without changing existing source implementation.
- Capture currently observable architecture and boundaries from repository documentation and layout.

## Core Structure
- Intent layer: principles/goal/roadmap
- Execution layer: focus/work_items/contributors
- Constraint layer: guardrails
- Truth layer: evidence/status/memory

## Precedence and Interpretation Notes
- `principles → goal → roadmap → focus → work_items → guardrails/runtime context`
- Evidence, status, and memory provide auditable state but should not override higher-level intent.

## Current Implementation Boundary
- Existing implementation includes a Python package (`lcats/`) with CLI/tooling, gatherers, chunking, extraction, analysis utilities, and scripts for test/lint/format workflows.
- Corpus assets and experiments exist at repository root (`corpora/`, `experiments/`).
- Current LRH bootstrap does not define runtime orchestration code; it defines project-level governance artifacts.

## Future Extensions (Non-binding)
- Add explicit artifact links from work items to concrete modules/tests as priorities stabilize.
- Add clearer RAG/CBR architecture sections once repository docs include canonical component contracts.
- Add contributor-role mapping after maintainers/ownership metadata is explicitly documented.
