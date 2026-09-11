---
resolution: "Implemented and merged in PR #432 (commit 2655a13a1ca88e910cdc1909ad76241361103d4a)."
blocked_reason: null
blocked: false
id: WI-LINGUISTICS-0009
title: Design durable columnar storage for rich linguistic artifacts
type: investigation
status: resolved
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams:
  - WS-COMPARATIVE-LEXICAL-VISUALIZATION
related_design:
  - project/design/proposals/proposed/comparative-lexical-visualization/00_proposal.md
depends_on:
  - WI-LINGUISTICS-0007
blocked_by: []
expected_actions:
  - create_report
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - run_full_corpus
  - change_canonical_schema
  - promote_sidecars
acceptance:
  - Storage design compares JSON, JSONL, Parquet, Arrow/Feather, HDF5, SQLite/DuckDB, CoNLL-U, and release/archive retention against LCATS pilot evidence
  - Recommendation identifies canonical source format, derived analysis format, dependency policy, artifact retention policy, and full-corpus implications
  - Design cites measured WI-LINGUISTICS-0007 sizes, roundtrip evidence, and relevant external format best practices
  - No full-corpus run, canonical schema change, or corpora/ sidecar promotion occurs under this investigation
required_evidence:
  - manual_review
  - validation_output
  - lrh_validate
artifacts_expected:
  - project/work_items/proposed/WI-LINGUISTICS-0009.md
  - project/design/proposals/proposed/rich-linguistics-columnar-storage/00_proposal.md
---

# Work Item: WI-LINGUISTICS-0009

## Summary

Design LCATS's durable storage and retention policy for rich linguistic token
artifacts, using the WI-LINGUISTICS-0007 pilot's measured JSON, compressed
archive, and Parquet roundtrip evidence.

## Problem / Context

WI-LINGUISTICS-0007 showed that rich token-detail JSON is reusable but bulky:
the 146-story pilot produced hundreds of MB of expanded JSON, while a derived
Parquet package retained the token table in a much smaller analysis-friendly
form. The governing comparative lexical visualization proposal explicitly
leaves bulk-artifact retention open among checked-in files, compressed archive
storage, columnar export, and manifest-plus-derived artifacts. LCATS needs a
project-level decision before WI-LINGUISTICS-0008 applies any full-corpus
retention policy.

### Duplication search

- In-repo: Related experiment-scoped bridge exists in
  `experiments/09_rich_linguistics_genre_sample/parquet_bridge.py`; no
  project-wide storage design or first-class artifact policy exists.
- Sibling repos: No sibling repos identified.
- External libraries: Parquet/Arrow, HDF5, SQLite/DuckDB, and CoNLL-U provide
  storage/interchange primitives, but none decides LCATS's canonical schema,
  provenance, retention, and dependency policy.
- Recommendation: Proceed with a design proposal; do not promote the
  experiment bridge to a project-wide API without review.

### Demand search

- Work items: `WI-LINGUISTICS-0008` requires a selected retention policy before
  any full-corpus run.
- Proposals: `PROP-LCATS-COMPARATIVE-LEXICAL-VISUALIZATION` names ordinary Git
  files, compressed archive storage, columnar export, and
  manifest-plus-derived retention as open options.
- Backlog: No separate matching backlog entry found.
- Recommendation: Link this item as a prerequisite or design input for
  `WI-LINGUISTICS-0008`.

## Scope

- Compare storage/interchange options for rich token details and lexical
  artifacts using actual WI-LINGUISTICS-0007 size and roundtrip data.
- Define whether JSON remains canonical and whether Parquet/Arrow/HDF5 or
  another format becomes a committed or archived derived artifact.
- Decide dependency posture: hard dependency, optional extra, experiment-only
  dependency, or external conversion tool.
- Recommend artifact retention for pilot and full-corpus outputs.

## Required Changes

1. Create
   `project/design/proposals/proposed/rich-linguistics-columnar-storage/00_proposal.md`.
2. Ground the design in measured WI-LINGUISTICS-0007 artifact sizes and Parquet
   roundtrip evidence.
3. Compare JSON, JSONL, compressed archives, Parquet, Arrow/Feather, HDF5,
   SQLite/DuckDB, and CoNLL-U.
4. Recommend canonical source format, derived analysis format,
   validation/roundtrip contract, dependency policy, and archive/check-in
   policy.
5. Identify how the decision constrains `WI-LINGUISTICS-0008` full-corpus
   execution.

## Non-Goals

- Do not run the full corpus.
- Do not change the canonical token-detail-v2 or lexicon-v1 schemas.
- Do not promote generated sidecars into `corpora/`.
- Do not replace the experiment-09 Parquet bridge with a full project API in
  this investigation.

## Acceptance Criteria

- The design gives a clear go-forward recommendation for rich linguistic
  artifact storage.
- The recommendation distinguishes canonical validation artifacts from derived
  analysis artifacts.
- The design includes measured pilot size, compression, Parquet roundtrip,
  dependency, reviewability, and archive-retention tradeoffs.
- The design states what `WI-LINGUISTICS-0008` should do with full-corpus
  outputs.

## Validation

- `scripts/version tools`
- `lrh validate`
- `lrh work-items readiness WI-LINGUISTICS-0009 --format md`

## Risk Notes

- A format optimized for local analysis may be poor for archival
  reproducibility or human review.
- Adding a hard columnar dependency may make installation heavier than the
  current LCATS package.
- Full-corpus outputs may exceed what is comfortable for Git even if the
  146-story pilot Parquet package is small.
