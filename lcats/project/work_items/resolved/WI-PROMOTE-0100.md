---
id: WI-PROMOTE-0100
title: Add live-directory-scan sourcing to lcats promote's insert/upsert modes
type: deliverable
status: resolved
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams:
  - WS-PROMOTE-MODE-REDESIGN
related_design:
  - project/design/proposals/adopted/lcats-promote-mode-redesign/00_proposal.md
  - lcats/src/lcats/analysis/corpus/promote.py
  - lcats/src/lcats/analysis/corpus/promote_cli.py
  - lcats/src/lcats/analysis/corpus/discovery.py
  - lcats/src/lcats/analysis/corpus/sidecar_validators.py
depends_on:
  - WI-PROMOTE-0097
blocked_by: []
blocked: false
blocked_reason: null
resolution: "Implemented and merged in PR #411 (merge commit fafcb3d4297fa79ed4c64786fb87c1f6b81e0eb7). lcats promote insert/upsert gained an optional live-directory-scan sourcing mode (--source), mutually exclusive with the existing --tranche-manifest mode. The scan reads <collection>/<story>/<sidecar-filename> for every story bucket under a given source root, deriving lcats_id from the bucket's own relative path and payload from the sidecar file's own content, skipping buckets without the named sidecar silently. Refactored promote.py's tranche-manifest engine into a shared _promote_sidecar_records() fed by two record sources, so scanned and manifest-sourced records go through identical validation/escape-check/identity-agreement/existing-destination-file logic. Review (Copilot + Codex) independently found and fixed 1 real P2 issue before merge: adding the new scan_source parameter unintentionally made the pre-existing allow_unvalidated/dry_run parameters keyword-only too, breaking positional-call backward compatibility; fixed by narrowing the keyword-only boundary to scan_source alone. See project/executions/WI-PROMOTE-0100/ and project/executions/AD_HOC/*WI_PROMOTE_0100_SCAN_SOURCING* for the full record chain."
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - implement_replace_orphaned_sidecar_guard
  - change_promote_wholesale_replacement_default_behavior
  - extend_validator_interface_to_non_json_kinds
  - build_schema_aware_content_merging_into_promote_py
acceptance:
  - "insert and upsert both gain an optional live-directory-scan sourcing mode, alongside (not replacing) --tranche-manifest"
  - "the scan reads data/<collection>/*/<sidecar-filename> for every story bucket under a given source root, deriving each record's lcats_id from the bucket's relative path (matching the identity convention already used by --tranche-manifest envelopes) and its payload from the sidecar file's own parsed JSON content"
  - "scanned records go through exactly the same validation, escape-check, identity-agreement, and existing-destination-file handling as manifest-sourced records via _promote_sidecar_manifest - no second code path duplicating that logic"
  - "the manifest-file flag and the live-scan flag are mutually exclusive; --sidecar remains required in both cases to select the registered kind"
  - "a scanned source bucket missing the corresponding destination story.json is rejected the same way a manifest record naming a nonexistent bucket is rejected - never silently skipped"
  - "docs/reference/corpus-promotion.md and docs/reference/cli-commands.md document the new sourcing mode"
  - "scripts/test passes with no new failures"
  - "lrh validate reports 0 errors"
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - lcats/src/lcats/analysis/corpus/promote.py
  - lcats/src/lcats/analysis/corpus/promote_cli.py
  - lcats/tests/analysis_tests/promote_test.py
  - lcats/docs/reference/corpus-promotion.md
  - lcats/docs/reference/cli-commands.md
---

# Work Item: WI-PROMOTE-0100

## Summary

Extend `lcats promote insert`/`upsert` to optionally source records by
scanning `data/<collection>/*/<sidecar-filename>` directly, instead of
requiring a pre-built JSONL manifest. This is Stage 3 of
`WS-PROMOTE-MODE-REDESIGN`'s implementation plan
(`PROP-LCATS-PROMOTE-MODE-REDESIGN`, Decision 8), flagged by the
workstream as a priority given the imminent whole-corpus
`linguistics.json` rollout it directly de-risks.

## Problem / Context

Today's `insert`/`upsert` (`WI-PROMOTE-0097`) require a hand-curated
manifest file — fine for a targeted tranche, too narrow for bulk-syncing
one sidecar kind across an entire collection, which fits neither
`replace` (too broad, wholesale) nor manifest-only tranche mode (too
narrow, requires curating a manifest first). This gap was surfaced
directly by the imminent linguistics-sidecar rollout.

### Duplication search
- In-repo: No existing scan-based sourcing mechanism — `insert`/`upsert`
  are manifest-only today (`WI-PROMOTE-0097`, `WI-GENRE-0075`).
- Sibling repos: None identified.
- External libraries: None — project-specific tooling.
- Recommendation: Proceed.

### Demand search
- Work items: None open besides this one fulfilling the anticipated slot.
- Proposals: `PROP-LCATS-PROMOTE-MODE-REDESIGN` Decision 8 is the
  governing design; its own Non-Goals explicitly defer exact
  scan/manifest interop to implementation time — not a duplicate, this
  item *is* that deferred work.
- Backlog: `WS-PROMOTE-MODE-REDESIGN`'s own "Proposed Work Items" item 3
  anticipates this item ("Not yet minted").
- Recommendation: Proceed.

## Scope

- Add an optional live-directory-scan sourcing mode to `insert`/`upsert`,
  alongside (not replacing) the existing manifest-file mode.
- Scan builds the same envelope shape (`{lcats_id, payload}`) in memory
  that `_promote_sidecar_manifest()` already consumes, so
  validation/escape-check/identity-agreement/overwrite logic is shared,
  not duplicated.
- Update CLI flags and the two affected docs files.

## Required Changes

1. **`lcats/src/lcats/analysis/corpus/promote.py`**: refactor
   `_promote_sidecar_manifest()`'s entry point so it can consume either a
   manifest file or a scanned-directory generator of envelope-shaped
   records, without duplicating validation/write logic. Add the
   scan-discovery function itself (exact shape at implementation time —
   likely building on `discovery.iter_collection_story_files()`'s
   bucket-walking convention).
2. **`lcats/src/lcats/analysis/corpus/promote_cli.py`**: add a
   mutually-exclusive scan-sourcing flag to `insert`/`upsert` (exact flag
   name decided at implementation time — a natural fit is reusing
   `--source`, matching `replace`'s own naming); require exactly one of
   manifest-file or scan-sourcing.
3. **`lcats/tests/analysis_tests/promote_test.py`**: cover scan
   discovery, envelope construction, mutual-exclusivity enforcement,
   missing-destination-bucket rejection, and parity with
   manifest-sourced behavior.
4. **`lcats/docs/reference/corpus-promotion.md`**,
   **`lcats/docs/reference/cli-commands.md`**: document the new
   sourcing mode.

## Non-Goals

- Does not implement Stage 2 (`replace`'s orphaned-sidecar guard) —
  separate work item, no dependency between the two stages.
- Does not change `replace`'s own wholesale mechanism.
- Does not build schema-aware content merging into `promote.py`.
- Does not extend the validator interface to non-JSON sidecar kinds.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes

- Refactoring `_promote_sidecar_manifest()`'s file-line-iteration entry
  point to also accept a scanned generator risks subtly changing
  manifest-mode behavior (e.g. line-number-based rejection labels don't
  apply to scanned sources) — keep both entry paths sharing identical
  downstream logic with source-appropriate error labels.
- Exact scan-root scoping (whole `data/` root vs. a required
  single-collection scope) is an implementation-time decision per the
  proposal's own Non-Goals — get this right to avoid an accidental
  corpus-wide scan when the user wanted one collection.

## Dependencies / Order

Depends on `WI-PROMOTE-0097` (resolved). This is Stage 3 of
`WS-PROMOTE-MODE-REDESIGN`; no dependency on Stage 2 (they are siblings,
both depending only on Stage 1).

## Related Workstream and Designs

- Workstream: `project/workstreams/active/WS-PROMOTE-MODE-REDESIGN.md`
- Design: `project/design/proposals/adopted/lcats-promote-mode-redesign/00_proposal.md`
