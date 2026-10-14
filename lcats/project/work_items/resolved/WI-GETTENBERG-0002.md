---
"resolution": "Delivered offline milestone on main in PR #508 (35f80fb53c1820ff70708df0ab049266f25dc3c7); original internal review https://github.com/xenotaur/LCATS/pull/505."
"blocked_reason": null
"blocked": false
"id": "WI-GETTENBERG-0002"
"title": "Typed metadata and bounded RDF record parser"
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
- "project/design/proposals/proposed/lcats-gettenberg-redesign/00_proposal.md"
- "project/development/gettenberg-pilot-charter.md"
"depends_on":
- "WI-GETTENBERG-0001"
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
- "Immutable typed records preserve all titles, contributor identities/roles/aliases, multilingual values,\
  \ subject schemes, resources and provenance; JSON serialization is lossless for modeled fields."
- "A pure parser accepts one bounded RDF record, rejects DTD/entity declarations and malformed IDs, never\
  \ performs I/O, and reports unmodeled predicates without discarding original source bytes."
- "Real cached public-domain RDF fixtures and authored hostile/edge fixtures cover aliases, multiple titles/languages,\
  \ contributor roles, repeated media types, missing values, unknown predicates and size limits."
- "Documentation exercises actual parser examples; imports create no caches or network requests; existing\
  \ caller behavior remains unchanged."
"required_evidence":
- "manual_review"
- "lrh_validate"
- "test_output"
- "validation_output"
"artifacts_expected":
- "src/lcats/gettenberg/models.py"
- "src/lcats/gettenberg/rdf.py"
- "src/lcats/gettenberg/errors.py"
- "tests/gettenberg_tests/"
- "docs/reference/gettenberg-records.md"
- "pyproject.toml"
---

## Summary

Typed metadata and bounded RDF record parser under the approved gettenberg redesign.

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

Implement additive models.py, errors.py and rdf.py without switching legacy callers. Public entry point parse_record(data: bytes, *, source_name: str, max_bytes: int = 2 * 1024**2) returns a parsed ebook plus diagnostics and source evidence. Source bytes/hash stay available; serialize byte evidence explicitly as base64 rather than claiming re-encoded XML is original. Resolve RDF identities with XML base and preserve resource identities even for equal MIME types. Use frozen dataclasses and tuples; use explicit nullable source values, not legacy sentinels. Keep title kind and contributor role, subject scheme and resource format values. Preserve unmodeled MARC values/source evidence and report unknown predicates. Distinguish source-volume metadata from story claims.

Use lxml with entity resolution, DTD loading and network access disabled, and reject any DOCTYPE; declare lxml directly in pyproject.toml (already present in the conda environment) rather than relying on gutenbergpy transitively. Limit record size to 2 MiB by default (observed maximum 1,223,616 bytes) with an explicit override. Reject invalid/ambiguous record identities and unsupported record shapes diagnostically. Do not claim the complete RDF standard is supported; document the observed Gutenberg RDF/XML profile. Parser root/imports must have no cache side effects. Synthetic deletion/invalid/unknown records test disposition separately from full archive accounting.

No SQL catalog, lifecycle, network acquisition, CLI, legacy caller migration, dependency removal or CI changes in this item.

## Required Changes

1. Immutable typed records preserve all titles, contributor identities/roles/aliases, multilingual values, subject schemes, resources and provenance; JSON serialization is lossless for modeled fields.
2. A pure parser accepts one bounded RDF record, rejects DTD/entity declarations and malformed IDs, never performs I/O, and reports unmodeled predicates without discarding original source bytes.
3. Real cached public-domain RDF fixtures and authored hostile/edge fixtures cover aliases, multiple titles/languages, contributor roles, repeated media types, missing values, unknown predicates and size limits.
4. Documentation exercises actual parser examples; imports create no caches or network requests; existing caller behavior remains unchanged.

## Acceptance Criteria

All frontmatter acceptance criteria require exact-head evidence and independent review before integration. Native execution records remain in_progress and work items nonterminal until human-approved main delivery.

## Validation

Run from `lcats/` in the project environment with imports bound to this worktree:

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `lrh work-items readiness WI-GETTENBERG-0002`
- `git diff --check`

Add focused behavior tests for the criteria above; unit tests are offline. Record commands, exit codes, fixture provenance and independent review separately from automated checks.

## Dependencies / Order

Dependencies listed above require canonical resolution or independently reviewed staged acceptance at an ancestor of the assignment base under the pilot charter. Native readiness alone does not prove dependency acceptance. No dispatch before the coordinator records that mapping and remaining budget.
