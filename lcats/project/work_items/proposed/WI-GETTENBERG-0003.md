---
"resolution": null
"blocked_reason": null
"blocked": false
"id": "WI-GETTENBERG-0003"
"title": "Streaming local archive ingestion and SQLite catalog queries"
"type": "deliverable"
"status": "proposed"
"owner": "xenotaur"
"contributors":
- "xenotaur"
"assigned_agents": []
"related_focus":
- "FOCUS-WORLDCON-2026"
"related_roadmap":
- "ROADMAP-CORE"
"related_workstreams":
- "WS-GETTENBERG"
"related_design":
- "project/design/proposals/proposed/lcats-gettenberg-redesign/00_proposal.md"
- "project/development/gettenberg-pilot-charter.md"
"depends_on":
- "WI-GETTENBERG-0002"
"blocked_by": []
"expected_actions":
- "create_file"
- "edit_file"
- "run_tests"
- "create_pr"
"forbidden_actions":
- "force_push"
- "delete_branch"
- "publish_package"
- "promote_canonical_corpus"
- "modify_ci_pipeline"
"acceptance":
- "Bounded tar member streaming writes normalized SQLite tables in batches and retains source RDF/provenance\
  \ without unpacking an archive tree."
- "Every archive record is imported, explicitly recognized as deletion/non-book, or rejected; any unexpected\
  \ rejection prevents a complete catalog result."
- "Context-managed read-only queries support single and batch lookups, missing IDs, bounded deterministic\
  \ iteration, AND-across/OR-within filters and separate exact/text matching."
- "Real parser-to-SQLite fixtures prove multiple-title associations, contributor aliases/roles, language/shelf\
  \ multiplicity, parameterized queries and resource fidelity; no activation or network side effects."
"required_evidence":
- "manual_review"
- "lrh_validate"
- "test_output"
- "validation_output"
"artifacts_expected":
- "src/lcats/gettenberg/ingestion.py"
- "src/lcats/gettenberg/catalog.py"
- "tests/gettenberg_tests/"
- "docs/reference/gettenberg-catalog.md"
---

## Summary

Streaming local archive ingestion and SQLite catalog queries under the approved gettenberg redesign.

## Problem / Context

See the measured baseline and caller inventory in `project/development/gettenberg-baseline.md`.

### Duplication search

- In-repo: existing gettenberg is the replacement target; no separate item for this tranche was found in the initial WI inventory. Reuse adjacent LCATS utilities where applicable.
- Sibling repositories: no known consumers or replacement implementations; LRH supplies process conventions only.
- External libraries: standard parsing/storage utilities are permitted; gutenbergpy, a fork, and a hosted replacement are outside the chosen direction.
- Recommendation: implement this bounded part of WS-GETTENBERG rather than duplicate release ownership.

### Demand search

- Governing proposal and WS-GETTENBERG request this tranche; WI-RELEASE-0037 owns the resulting release blocker verification.
- Upstream-watch backlog is historical, not a prerequisite. Link evidence; do not close release items automatically.

## Scope

Define schema/version and indexes before implementation in a linked decision record. Use separate child tables for titles, contributors/roles/aliases, languages, subjects with schemes, shelves, resources/formats and preserved RDF. Batch commits (initial 256 records), SQLite foreign keys and integrity checks. Validate positive integer IDs, query fields, pagination bounds and incompatible schema with distinct errors; avoid arbitrary SQL in public API. Full-record results must preserve source relationships and absent values. Local archive build output is an explicitly named candidate, never active merely because construction succeeds.

Initial safety bounds: compressed input 256 MiB, member 2 MiB, expanded bytes 4 GiB, at most 200,000 members, configurable explicit limits. No tar extraction; reject unsafe/nonregular entries with accounting. Budget targets to investigate: peak RSS <=512 MiB, full cached archive build <=10 minutes and temporary output <=4 GiB; report measured failure instead of weakening bounds silently. The measured audit is not a baseline for a full old-library rebuild. Do not execute a full build when the current run allowance cannot contain it.

No generation activation, automatic refresh, web requests, gather migration or CI changes.

## Required Changes

1. Bounded tar member streaming writes normalized SQLite tables in batches and retains source RDF/provenance without unpacking an archive tree.
2. Every archive record is imported, explicitly recognized as deletion/non-book, or rejected; any unexpected rejection prevents a complete catalog result.
3. Context-managed read-only queries support single and batch lookups, missing IDs, bounded deterministic iteration, AND-across/OR-within filters and separate exact/text matching.
4. Real parser-to-SQLite fixtures prove multiple-title associations, contributor aliases/roles, language/shelf multiplicity, parameterized queries and resource fidelity; no activation or network side effects.

## Acceptance Criteria

All frontmatter acceptance criteria require exact-head evidence and independent review before integration. Native execution records remain in_progress and work items nonterminal until human-approved main delivery.

## Validation

Run from `lcats/` in the project environment with imports bound to this worktree:

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `lrh work-items readiness WI-GETTENBERG-0003`
- `git diff --check`

Add focused behavior tests for the criteria above; unit tests are offline. Record commands, exit codes, fixture provenance and independent review separately from automated checks.

## Dependencies / Order

Dependencies listed above require canonical resolution or independently reviewed staged acceptance at an ancestor of the assignment base under the pilot charter. Native readiness alone does not prove dependency acceptance. No dispatch before the coordinator records that mapping and remaining budget.
