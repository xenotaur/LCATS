---
id: GOAL-CORE
title: LCATS Narrative Reasoning Goal on a Trustworthy Corpus Substrate
status: active
owner: unassigned
time_horizon: long
---

# Project Goal

## Objective
Build LCATS as a narrative reasoning system grounded in a trustworthy, auditable literary corpus substrate.

## Near-Term Goal (Now)
Establish corpus correctness and operational trust through a conservative, non-destructive repair/review pipeline.

### Near-Term Emphasis
- Corpus correctness and encoding hygiene.
- Auditability for every corpus-changing operation.
- Repair + review workflows that preserve provenance and allow human override.

## Medium-Term Goal (WorldCon 2026)
Create a story feature-extraction pipeline for digital-humanities analysis, targeting the
WorldCon 2026 Academic Track paper on "The Shape of Science Fiction."

### Medium-Term Emphasis
- Extract structured, comparable features from story text at scale.
- Build on `lcats assess` (genre/quality verdicts) and the `scene_analysis.py` / `story_analysis.py`
  modules as foundations.
- The feature library is not yet decided — under active design discussion outside this repo
  (external design threads); not yet ready for a `project/design/proposals/` entry.

### Status
- No design proposal, workstream, or work items exist yet for this goal, intentionally. Formalize
  once the feature-extraction library is decided.
- Related existing work: `lcats assess` (`WI-LLM-0009`, `WI-ASSESS-0012`), scene/story analysis
  module migration (`WI-LLM-0008`).

## Long-Term Goal (Later)
Layer structured narrative representation and reasoning capabilities on top of the trustworthy corpus substrate.

### Long-Term Emphasis
- Structured narrative representation (scene/sequence/case oriented).
- Reasoning frameworks and methods:
  - Propp-inspired narrative functions.
  - Greimas-inspired actant/role structures.
  - Case-Based Reasoning (CBR).
  - Retrieval-Augmented Generation (RAG).

## Intended Outcome
- A corpus that is inspectable, repairable, and safe to evolve.
- A reproducible pipeline where proposed corpus changes are explainable before application.
- A foundation that supports higher-order narrative reasoning without sacrificing data integrity.

## In Scope
- Corpus survey and classification-driven repair planning.
- Repair engine, span operations, and human review loop.
- Evidence-backed project governance via LRH artifacts.
- Exploratory foundations for story feature extraction (not yet a formal design).

## Out of Scope (Current Horizon)
- Full narrative reasoning engine implementation in the current focus window.
- Production SLAs or model-provider lock-in.
- Unreviewed destructive corpus rewrites.
