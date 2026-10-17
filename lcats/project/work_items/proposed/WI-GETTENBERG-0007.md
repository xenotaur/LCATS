---
"resolution": null
"blocked_reason": null
"blocked": false
"id": "WI-GETTENBERG-0007"
"title": "Source-aware gather preparation and catalog commands"
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
- "WI-GETTENBERG-0004"
- "WI-GETTENBERG-0005"
- "WI-GETTENBERG-0006"
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
- "Gather plans selected collection requirements before initialization; non-Gutenberg/local/fixed-URL\
  \ work does not require a catalog unless its workflow explicitly needs metadata."
- "Interactive missing setup requests approval; --yes approves required setup; unattended missing approval\
  \ fails promptly; --offline prohibits network; --dry-run creates nothing."
- "Standalone setup/status/refresh/local-rebuild use the same library operations; setup consent never\
  \ implies refresh, redownload or output replacement."
- "Collection selection, bucket identity, normalization and overrides remain verified through representative\
  \ integration tests."
"required_evidence":
- "manual_review"
- "lrh_validate"
- "test_output"
- "validation_output"
"artifacts_expected":
- "src/lcats/cli.py"
- "src/lcats/cli/"
- "src/lcats/gatherers/"
- "tests/"
- "docs/tutorials/"
- "docs/how-to/"
---

## Summary

Source-aware gather preparation and catalog commands under the approved gettenberg redesign.

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

Introduce a small explicit collection requirement contract, not an arbitrary executable plugin framework. Preserve existing CLI compatibility where useful while adding documented flags and exit behavior. Report unresolved selection until metadata exists. Gathering already authorizes missing source retrieval; do not add per-story prompts. Use dependency injection at I/O boundaries for CLI tests. Document command names against the actual dispatcher before adding files. No publication/corpus promotion.

## Required Changes

1. Gather plans selected collection requirements before initialization; non-Gutenberg/local/fixed-URL work does not require a catalog unless its workflow explicitly needs metadata.
2. Interactive missing setup requests approval; --yes approves required setup; unattended missing approval fails promptly; --offline prohibits network; --dry-run creates nothing.
3. Standalone setup/status/refresh/local-rebuild use the same library operations; setup consent never implies refresh, redownload or output replacement.
4. Collection selection, bucket identity, normalization and overrides remain verified through representative integration tests.

## Acceptance Criteria

All frontmatter acceptance criteria require exact-head evidence and independent review before integration. Native execution records remain in_progress and work items nonterminal until human-approved main delivery.

## Validation

Run from `lcats/` in the project environment with imports bound to this worktree:

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `lrh work-items readiness WI-GETTENBERG-0007`
- `git diff --check`

Add focused behavior tests for the criteria above; unit tests are offline. Record commands, exit codes, fixture provenance and independent review separately from automated checks.

## Dependencies / Order

Dependencies listed above require canonical resolution or independently reviewed staged acceptance at an ancestor of the assignment base under the pilot charter. Native readiness alone does not prove dependency acceptance. No dispatch before the coordinator records that mapping and remaining budget.

## Staged preparation acceptance — 2026-10-17

PR518 internally merged into codex/gettenberg-acquisition at fed5030a60e2df42a0827a87d0e412562d865309;
accepted head 4666837158149a1087cf431b66576579a1dc33f8. Canonical2943 tests and24 focused tests pass;
independent cold review and repair verification pass, all four exact-headCI checks
pass, and the one hosted P2 is resolved. Merge parents and tree match verified.
Evidence: project/development/evidence/gettenberg-preparation-20261017/integration.json.

Delivered: explicit collection requirements and lazy selection, read-only gather
planning, standalone catalog status/setup/refresh/rebuild, first-setup approval
policy, offline acquisition enforcement and Diataxis docs. Representative curated
gathering preserves bucket identities and output bytes; existing extraction,
normalization and overrides are unchanged.

Remaining before whole-item acceptance: migrate metadata-dependent gather execution
to the new catalog/resource APIs, connect preparation to that live path, enforce
gather-level --yes/--offline across actual source access, and qualify an operational
default archive/resource route before implicit online first use. Broader migrated
collection integration tests accompany that work. Explicit-source standalone
commands do not imply default mirror qualification. Dependency removal remains
WI0008; main promotion and terminal closeout still require human approval.
