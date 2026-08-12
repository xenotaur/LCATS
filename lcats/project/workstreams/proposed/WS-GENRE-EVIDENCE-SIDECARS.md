---
id: WS-GENRE-EVIDENCE-SIDECARS
kind: planning_node
title: Genre Evidence Sidecars for LCATS Corpus Sampling
status: proposed
stage: designed
origin: design_review
summary: Deliver PROP-GENRE-EVIDENCE-SIDECARS through an experiment-first genre metadata prefilter, append-only genre.json sidecar schema, tranche promotion, append-mode annotation, model and human assessment layers, and sample promotion for the Worldcon paper.
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_design:
  - lcats/project/design/proposals/proposed/genre-evidence-sidecars/00_proposal.md
  - lcats/project/design/design.md
  - lcats/project/design/event-role-world-genre-target-reconciliation.md
  - lcats/project/design/proposals/adopted/worldcon-fast-path-annotation/00_proposal.md
  - lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md
  - lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md
  - lcats/project/work_items/proposed/WI-ASSESS-0051.md
  - lcats/project/work_items/proposed/WI-LLM-0066.md
work_items: []
exit_criteria:
  - Gutenberg metadata cache preflight exists and refuses cache build/download unless explicitly approved
  - experiments/05_metadata_genre_prefilter produces reviewed 40-story pilot manifests with LCATS IDs and metadata-rule assessment evidence
  - genre-sidecar-v1 append-only assessments schema is validated and supports metadata, model, and human assessment records with timestamps and provenance
  - lcats promote can promote selected genre.json sidecar tranches without wholesale collection replacement
  - lcats annotate can append model/human genre assessments to existing genre.json without discarding prior evidence
  - Pilot and expanded sample genre.json sidecars are promoted to corpora/ and validated for the Worldcon paper workflow
  - All work items resolved and lrh validate reports 0 errors
---

# Workstream: Genre Evidence Sidecars for LCATS Corpus Sampling

## Purpose

This workstream coordinates implementation of PROP-GENRE-EVIDENCE-SIDECARS. It turns the design from an experiment-first metadata prefilter into permanent append-only `genre.json` evidence sidecars that can support the Worldcon sample, later local-model genre assessments, human adjudication, and downstream analysis.

## Scope

- Sync or locate the existing Gutenberg metadata cache and add a no-network preflight path.
- Build `experiments/05_metadata_genre_prefilter` for metadata-rule evidence and a heterogeneous 40-story tooling pilot.
- Define and validate `genre-sidecar-v1` as an append-only `assessments[]` schema keyed by LCATS story ID.
- Define legacy flat-sidecar conversion so append mode preserves existing `AssessmentResult.to_dict()` evidence instead of replacing it.
- Upgrade promotion semantics so selected `genre.json` sidecar tranches can be promoted without wholesale directory replacement.
- Upgrade annotation semantics so `lcats annotate` can read existing sidecars and append new model or human assessments.
- Expand from the 40-story pilot to the 100-200 story Worldcon sample.
- Add local-model genre assessment as a later layer, preserving repeated runs for downstream voting.
- Add explicit run identity for independent repeated model assessments while preserving checkpoint resumability within a run.
- Keep event extraction and paper analysis as follow-on work once the genre evidence pipeline is stable.

## Prior Art Check

This is related to existing Worldcon and annotation planning, but it is not a duplicate. `WS-WORLDCON-FAST-PATH-ANNOTATION` covers the broader paper-oriented fast path, while this workstream owns the narrower genre evidence sidecar path: metadata prefilter, sidecar schema, promotion tranche semantics, append-mode annotation, and model/human genre layers.

Relevant prior work includes the current genre census experiment, existing `lcats annotate` and `lcats promote` behavior, `WI-ASSESS-0051`, `WI-LLM-0066`, and the model evaluation proposal. Those should inform the work items rather than be replaced by this workstream.

## Proposed Work Items

1. Create cache preflight and `experiments/05_metadata_genre_prefilter` scaffold.
2. Produce the 40-story metadata-evidence pilot across heterogeneous collections.
3. Define and validate `genre-sidecar-v1`.
4. Add legacy flat-sidecar conversion and validation coverage.
5. Add sidecar-tranche promotion support.
6. Promote and check in the 40-story pilot sidecars.
7. Expand metadata evidence to the 100-200 story sample.
8. Add append-mode genre assessment support to `lcats annotate`.
9. Add local-model genre assessment as an append-only evidence source with explicit run identity.
10. Add human review/adjudication support for genre evidence.
11. Reassess event extraction and analysis work items after genre sidecars are stable.

## Non-Goals

- This workstream does not implement the genre tooling directly.
- It does not download or rebuild Gutenberg metadata without explicit approval.
- It does not replace the existing genre census or local-model evaluation work.
- It does not make local-model ERW entity extraction or segmentation production-ready.
- It does not define the final Worldcon paper statistical analysis.
- It does not create child work items in this PR.

## Open Questions

- What exact work item IDs should be minted for each implementation slice?
- What exact LCATS story ID string should become canonical in sidecars?
- What should the CLI surface look like for sidecar-tranche promotion and append-mode annotation?
- Should whole-corpus Gutenberg metadata labels be committed if the metadata path proves high-quality and very fast?
- Should adjudication point to assessment IDs, normalized labels, or both?
