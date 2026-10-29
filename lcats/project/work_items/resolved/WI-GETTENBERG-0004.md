---
"resolution": "Delivered offline milestone on main in PR #508 (35f80fb53c1820ff70708df0ab049266f25dc3c7); original internal review https://github.com/xenotaur/LCATS/pull/507."
"blocked_reason": null
"blocked": false
"id": "WI-GETTENBERG-0004"
"title": "Recoverable catalog generations and offline lifecycle"
"type": "deliverable"
"status": "resolved"
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
- "project/design/proposals/adopted/lcats-gettenberg-redesign/00_proposal.md"
- "project/development/gettenberg-pilot-charter.md"
"depends_on":
- "WI-GETTENBERG-0003"
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
- "Setup reuses a valid generation; local rebuild uses a retained archive; refresh and cleanup are separate\
  \ explicit operations."
- "Single-writer locking, atomic activation and pinned reader generations survive interrupted build/activation\
  \ without replacing the prior valid generation."
- "Manifest records archive/source identity, schema/parser versions, counts and diagnostics; integrity,\
  \ relationships and count changes are checked before activation."
- "LCATS_CACHE_DIR is honored; legacy artifacts are preserved without fabricated provenance; offline operations\
  \ make no network calls."
"required_evidence":
- "manual_review"
- "lrh_validate"
- "test_output"
- "validation_output"
"artifacts_expected":
- "src/lcats/gettenberg/"
- "tests/gettenberg_tests/"
- "docs/how-to/gettenberg-catalog.md"
---

## Summary

Recoverable catalog generations and offline lifecycle under the approved gettenberg redesign.

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

Implement manifest/generation protocol with writer-lock acquisition/release, bounded timeout, atomic same-filesystem pointer replacement and recoverable candidate cleanup. Pin query sessions to their opened generation. Validate source hash, format/schema and import accounting. Explicitly classify legacy caches and document migration/cleanup retention. Test two readers plus competing writer, interruption at each publication boundary and unsupported schema. Use real files/SQLite, network-boundary substitution only. Coordinate archive acquisition through WI-GETTENBERG-0005; no duplicate downloader. No automatic age-based refresh or canonical corpus mutation.

## Required Changes

1. Setup reuses a valid generation; local rebuild uses a retained archive; refresh and cleanup are separate explicit operations.
2. Single-writer locking, atomic activation and pinned reader generations survive interrupted build/activation without replacing the prior valid generation.
3. Manifest records archive/source identity, schema/parser versions, counts and diagnostics; integrity, relationships and count changes are checked before activation.
4. LCATS_CACHE_DIR is honored; legacy artifacts are preserved without fabricated provenance; offline operations make no network calls.

## Acceptance Criteria

All frontmatter acceptance criteria require exact-head evidence and independent review before integration. Native execution records remain in_progress and work items nonterminal until human-approved main delivery.

## Validation

Run from `lcats/` in the project environment with imports bound to this worktree:

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `lrh work-items readiness WI-GETTENBERG-0004`
- `git diff --check`

Add focused behavior tests for the criteria above; unit tests are offline. Record commands, exit codes, fixture provenance and independent review separately from automated checks.

## Dependencies / Order

Dependencies listed above require canonical resolution or independently reviewed staged acceptance at an ancestor of the assignment base under the pilot charter. Native readiness alone does not prove dependency acceptance. No dispatch before the coordinator records that mapping and remaining budget.
