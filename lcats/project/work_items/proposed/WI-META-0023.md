---
resolution: null
blocked_reason: null
blocked: false
id: WI-META-0023
title: Remove LRH meta-registry duplication from LCATS codebase and docs
type: operation
status: proposed
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams: []
related_design: []
depends_on: []
blocked_by: []
expected_actions:
  - delete_file
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - modify_ci_pipeline
  - run_lrh_agentic
acceptance:
  - lcats/lcats/meta_registry.py no longer exists
  - lcats/lcats/cli.py has no `meta`/`meta register` subcommand, handler, or `meta_registry` import
  - lcats/tests/meta_registry_test.py is removed and lcats/tests/cli_test.py has no meta-register test cases
  - README.md, lcats/README.md, lcats/project/roadmap/roadmap.md, lcats/docs/reference/cli-commands.md, and lcats/docs/reference/cli-status.md no longer document `lcats meta register` as an LCATS command
  - WI-META-0006 is moved to project/work_items/abandoned/ with status abandoned and a resolution note pointing to WI-META-0023 and `lrh meta register`
  - lcats/project/work_items/README.md reflects WI-META-0023 under Proposed Items and WI-META-0006's move out of Active Items
  - lrh validate reports 0 errors
  - scripts/test passes
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/lcats/meta_registry.py
  - lcats/lcats/cli.py
  - lcats/tests/meta_registry_test.py
  - lcats/tests/cli_test.py
  - README.md
  - lcats/README.md
  - lcats/project/roadmap/roadmap.md
  - lcats/docs/reference/cli-commands.md
  - lcats/docs/reference/cli-status.md
  - lcats/project/work_items/README.md
  - lcats/project/work_items/abandoned/WI-META-0006.md
---

# Work Item: WI-META-0023

## Summary
Remove the `lcats meta register` command and its `meta_registry.py` implementation from LCATS, along with all documentation that presents it as an LCATS feature, since it duplicates functionality that already exists natively in the LRH CLI (`lrh meta register`).

## Problem / Context
Commits `009b0c0` and `9d36ad8` (2026-04-21) added a "workspace project registry" slice (`lcats/lcats/meta_registry.py`, wired into the CLI as `lcats meta register`) under WI-META-0006. Investigation shows this duplicates LRH's own `meta` subsystem (`lrh meta {init,list,where,config,register,refresh,inspect,set,unset}`, ~2,929 lines in `src/lrh/meta/workspace.py` + `local_state_model.py`) almost field-for-field: `repo_locator`, `project_dir`, TOML registry records under `projects/`, duplicate-detection via `--force`. Nothing in the LCATS version touches LCATS's actual domain (corpora, texts, gathering, story analysis) -- it is pure workspace bookkeeping that belongs in LRH, which already implements it more completely. A broader repo sweep for other LRH-flavored fingerprints (`work_item`, `workstream`, `execution record`, `.lrh/config`, `LRH_WORKSPACE`, etc.) found no further contamination -- this is an isolated, self-contained slice from a single two-commit session.

## Scope
- Remove the `meta_registry` module and its CLI wiring from the `lcats` Python package.
- Remove or update all tests referencing `meta register`/`meta_registry`.
- Remove documentation of `lcats meta register` from the repo-root README, `lcats/README.md`, roadmap, and `docs/reference/`.
- Move WI-META-0006 to `abandoned/` with a resolution note, and update the work-item index accordingly.

## Required Changes
1. Delete `lcats/lcats/meta_registry.py`.
2. In `lcats/lcats/cli.py`: remove the `meta_registry` import, the `_handle_meta_register` handler function, and the `meta`/`meta register` subparser registration (including its `set_defaults(handler=_handle_meta_register)` wiring).
3. Delete `lcats/tests/meta_registry_test.py`; remove the meta-register test cases from `lcats/tests/cli_test.py`.
4. In the repo-root `README.md`: remove the `lcats meta register <repo_locator>` row from the CLI Commands table.
5. In `lcats/README.md`: remove the `lcats meta register <repo_locator>` line from the Building section.
6. In `lcats/project/roadmap/roadmap.md`: remove or rephrase the Phase 5 bullet referencing delivery of the workspace meta registry slice (`meta register`).
7. In `lcats/docs/reference/cli-commands.md`: remove the `## meta register` section.
8. In `lcats/docs/reference/cli-status.md`: remove `meta register` from the Implemented commands list.
9. Move `lcats/project/work_items/active/WI-META-0006.md` to `lcats/project/work_items/abandoned/WI-META-0006.md`, set `status: abandoned`, `resolution:` explaining it is superseded by native LRH functionality (`lrh meta register`) and reversed by WI-META-0023.
10. In `lcats/project/work_items/README.md`: remove the `active/WI-META-0006.md` entry from Active Items, add an Abandoned Items section (or bucket description) listing `abandoned/WI-META-0006.md`, and add `proposed/WI-META-0023.md` to Proposed Items.

## Non-Goals
- Do not implement or modify anything in the LRH repository (`logical_robotics_harness`) -- this item only removes the duplicate from LCATS.
- Do not add a pointer/wrapper command in LCATS that shells out to `lrh meta register` -- users who need workspace registration should use `lrh` directly.
- Do not re-audit for other contamination -- that sweep was already done in the conversation that produced this item and found nothing further.

## Acceptance Criteria
- `lcats meta register` no longer exists as a CLI command (`lcats --help` shows no `meta` subcommand).
- `grep -rIl "meta_registry\|meta register" lcats/lcats lcats/tests README.md lcats/README.md lcats/docs lcats/project/roadmap` returns no matches (excluding WI-META-0006/WI-META-0023 themselves).
- `lcats/project/work_items/README.md` lists WI-META-0023 under Proposed Items and no longer lists WI-META-0006 under Active Items.
- `lrh validate` reports 0 errors.
- `scripts/test` passes.

## Validation
- `lrh validate`
- `scripts/test`
- `scripts/lint`
- `lcats --help`
- `grep -rIl "meta_registry\|meta register" lcats/lcats lcats/tests README.md lcats/README.md lcats/docs lcats/project/roadmap`

## Risk Notes
- `lcats/lcats/cli.py` mixes this handler with unrelated subcommands in one file; the removal diff must be scoped carefully to avoid touching other command wiring.
- If any external doc or script (outside this repo) references `lcats meta register`, it will break -- none were found in this repo's sweep, but this wasn't checked outside LCATS.
