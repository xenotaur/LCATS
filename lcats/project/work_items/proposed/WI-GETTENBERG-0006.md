---
"resolution": null
"blocked_reason": null
"blocked": false
"id": "WI-GETTENBERG-0006"
"title": "Conservative boilerplate cleanup with diagnostics"
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
- "Cleanup retains original input and reports chosen boundaries, version and ambiguities."
- "Modern and verified historical start/end cases work while ambiguous or absent markers preserve content."
- "Regression fixtures cover false positives inside narrative, short texts, Unicode, repeated markers\
  \ and malformed boundaries."
- "Any reused marker list/code has verified license and attribution; otherwise use independently authored\
  \ rules and fixtures."
"required_evidence":
- "manual_review"
- "lrh_validate"
- "test_output"
- "validation_output"
"artifacts_expected":
- "src/lcats/gettenberg/cleanup.py"
- "tests/gettenberg_tests/"
- "docs/reference/gettenberg-cleanup.md"
---

## Summary

Conservative boilerplate cleanup with diagnostics under the approved gettenberg redesign.

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

Keep cleanup pure and separate from catalog metadata and gather-time normalization. Determine ordered start/end boundaries conservatively; do not reproduce upstream broad substring resets. Test byte/text decoding responsibility explicitly. Attribute retained third-party material before copying it. No unrelated normalization changes or corpus rewrites.

## Required Changes

1. Cleanup retains original input and reports chosen boundaries, version and ambiguities.
2. Modern and verified historical start/end cases work while ambiguous or absent markers preserve content.
3. Regression fixtures cover false positives inside narrative, short texts, Unicode, repeated markers and malformed boundaries.
4. Any reused marker list/code has verified license and attribution; otherwise use independently authored rules and fixtures.

## Acceptance Criteria

All frontmatter acceptance criteria require exact-head evidence and independent review before integration. Native execution records remain in_progress and work items nonterminal until human-approved main delivery.

## Validation

Run from `lcats/` in the project environment with imports bound to this worktree:

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `lrh work-items readiness WI-GETTENBERG-0006`
- `git diff --check`

Add focused behavior tests for the criteria above; unit tests are offline. Record commands, exit codes, fixture provenance and independent review separately from automated checks.

## Dependencies / Order

Dependencies listed above require canonical resolution or independently reviewed staged acceptance at an ancestor of the assignment base under the pilot charter. Native readiness alone does not prove dependency acceptance. No dispatch before the coordinator records that mapping and remaining budget.
