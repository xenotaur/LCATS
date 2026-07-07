# Project Context (Human-Oriented)

## One-line Description
- LCATS is a literary corpus toolkit with LLM-assisted analysis/extraction workflows, now paired with an initial LRH project control plane.

## Overview
- The repository includes a Python package (`lcats/`) with CLI, gathering, chunking, extraction, and analysis capabilities, plus story corpora and experiment directories.
- The new LRH `project/` directory provides structure for intent, constraints, execution focus, and evidence-backed status tracking.

## Goals and Direction
- Goal: Develop a story corpora / RAG system based on LLMs and case-based reasoning.
- Near-term focus: Establish and validate a conservative LRH baseline so future work can be interpreted and audited consistently.

## Design Snapshot
- Authoritative artifacts define intent (`principles`, `goal`, `roadmap`), execution (`focus`, `work_items`, `contributors`), constraints (`guardrails`), and truth (`evidence`, `status`, `memory`).
- Derived context files summarize, but do not define, commitments.

## Current Status Snapshot
- Health is currently **yellow**: implementation signals are present, but LRH artifacts are newly bootstrapped and some strategic details (ownership, RAG/CBR milestones) remain open.

## Known Unknowns
- Confirmed owner assignments for authoritative artifacts.
- Explicit architecture commitments for RAG/case-based reasoning layers.
- Formal evaluation criteria for retrieval/reasoning quality.

## Notes
- Derived summary only (non-authoritative).
