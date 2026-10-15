---
"resolution": null
"blocked_reason": null
"blocked": false
"id": "WI-GETTENBERG-0005"
"title": "Bounded resource acquisition and original-byte cache"
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
- "Explicit policy controls all network access, including offline and dry-run; valid cached sources are\
  \ reused without refresh requests."
- "Atomic cache entries preserve original bytes, source URL, content hash and retrieval metadata; decoding\
  \ is a separately versioned result."
- "Bounded timeout/retries, Retry-After, pacing and resource locking avoid duplicate concurrent downloads\
  \ and speculative fallback after denial."
- "Catalog-described formats remain available for retrieval; supported text/HTML selection and decoding\
  \ errors are documented and tested."
"required_evidence":
- "manual_review"
- "lrh_validate"
- "test_output"
- "validation_output"
"artifacts_expected":
- "src/lcats/gettenberg/resources.py"
- "tests/gettenberg_tests/"
- "docs/reference/gettenberg-network.md"
---

## Summary

Bounded resource acquisition and original-byte cache under the approved gettenberg redesign.

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

Record transport, cache-key, redirect, size and pacing decisions before implementation. Begin with conservative explicit bounds: one active request, at least two seconds between Gutenberg requests, 30-second request timeout, at most two retries, 256 MiB archive and 32 MiB story resource limits with caller overrides. Respect longer Retry-After without exceeding run deadlines. Do not live-download merely to test; use deterministic local network-boundary fixtures. Share immutable archive input with lifecycle ingestion. Preserve old decoded .txt/.txt.gz caches as legacy derived representations, never relabel as originals. No per-story prompts or general PDF/EPUB extraction.

## Required Changes

1. Explicit policy controls all network access, including offline and dry-run; valid cached sources are reused without refresh requests.
2. Atomic cache entries preserve original bytes, source URL, content hash and retrieval metadata; decoding is a separately versioned result.
3. Bounded timeout/retries, Retry-After, pacing and resource locking avoid duplicate concurrent downloads and speculative fallback after denial.
4. Catalog-described formats remain available for retrieval; supported text/HTML selection and decoding errors are documented and tested.

## Acceptance Criteria

All frontmatter acceptance criteria require exact-head evidence and independent review before integration. Native execution records remain in_progress and work items nonterminal until human-approved main delivery.

## Validation

Run from `lcats/` in the project environment with imports bound to this worktree:

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `lrh work-items readiness WI-GETTENBERG-0005`
- `git diff --check`

Add focused behavior tests for the criteria above; unit tests are offline. Record commands, exit codes, fixture provenance and independent review separately from automated checks.

## Dependencies / Order

Dependencies listed above require canonical resolution or independently reviewed staged acceptance at an ancestor of the assignment base under the pilot charter. Native readiness alone does not prove dependency acceptance. No dispatch before the coordinator records that mapping and remaining budget.


## Acquisition design checkpoint

The [acquisition contract](../../development/gettenberg-acquisition-design.md)
records transport/cache/redirect/pacing/decoding decisions and acceptance scenarios
A01–A22 under the 2026-10-15 planning grant. It is a coordinator-authored handoff,
not implementation acceptance or an independent review. Qualify the concrete
mirror route mapping and document timeout semantics before implementing. Preserve
these criteria when splitting work into resumable tranches; this WI remains open.


## Staged conditional-refresh acceptance — 2026-10-15

A14 is independently reviewed and internally integrated through
[PR513](https://github.com/xenotaur/LCATS/pull/513), merge 0a5ccd426b07511a535ab9172fc8418818c89da6,
verified head 0454e6affcd1f3ed8df5594aea2780ba894b1647. Explicit304/changed200 refresh, receipt history,
validator binding, failure safety and schema-1 compatibility have 156 focused tests,
2851 canonical tests and four passing exact-head CI checks.
[Integration evidence](../../development/evidence/gettenberg-refresh-20261015/integration.json)
contains the acceptance mapping, review/repair records and source identities.
This is staged delivery only: status remains proposed until human-approved main
promotion. A15/A16 catalog composition and qualified automatic routing remain;
this checkpoint does not claim whole-WI or workstream completion.


## Staged catalog-composition acceptance — 2026-10-15

A15/A16 are independently reviewed and internally integrated through
[PR514](https://github.com/xenotaur/LCATS/pull/514), merge 0f36cfc16e3da18d97047daa6ae055343551571b,
verified head bfc3598576bfbe7291e46a7e4e8e256267a6786d. Receipt/body binding and embedded
provenance, local/schema compatibility, unchanged-byte reuse, count approval and
failure/pinned-reader safety are covered by 2868 canonical tests, independent
review and four passing final-head CI checks.
[Integration evidence](../../development/evidence/gettenberg-catalog-20261015/integration.json)
records the exact source identities and review disposition. This supersedes the
earlier checkpoint's pending A15/A16 status. Qualified automatic routing remains;
consumer/CLI migration follows in its planned work. Status remains proposed
until human-approved main delivery; whole-WI completion is not claimed.
