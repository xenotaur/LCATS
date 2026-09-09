---
resolution: null
blocked_reason: null
blocked: false
id: WI-META-0096
title: Investigate missing agent/instruction_source/session_transcript defaults in lrh prompt record-execution
type: investigation
status: proposed
priority: low
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
  - create_file
  - create_pr
forbidden_actions:
  - modify_lrh_cli_source_directly
  - force_push
  - delete_branch
acceptance:
  - "A written investigation doc exists documenting the current field-population behavior of lrh prompt record-execution and lrh prompt update-execution, verified against real CLI --help output and real generated execution records, not assumption"
  - "The doc states whether adding creation-time flags or defaults (e.g. --agent, --instruction-source) to record-execution is feasible and desirable, with a concrete recommendation"
  - "The doc states whether lrh prompt update-execution should be extended to set agent:/instruction_source: (today it manages only status/pr/commit/session-transcript), with a concrete recommendation"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - lcats/project/design/lrh-record-execution-agent-fields-investigation.md
---

# WI-META-0096: Investigate missing agent/instruction_source/session_transcript defaults in lrh prompt record-execution

## Summary

`lrh prompt record-execution` creates execution records with only
`execution_id`/`prompt_id`/`work_item`/`status`/`rerun_of`/`pr`/`commit`/
`created_at` populated - `agent:`, `instruction_source:`, and
`session_transcript:` are left out of the generated frontmatter entirely,
requiring a manual edit after every call to bring the record up to the
convention documented in `project/executions/README.md`. This gap was
discovered only at `/lrh-closeout` time during `WI-SEGMENT-0102`'s
execution, after 6 execution records across the implementation,
review-response, three substitute self-review rounds, and confirm-fixes
had already been created without these fields - each had to be
back-filled by hand immediately before landing.

Investigate whether `lrh prompt record-execution` should accept flags
(e.g. `--agent`, `--instruction-source`) to populate these fields at
creation time instead of leaving them for a later manual edit, and
whether `lrh prompt update-execution` should be extended to also set
`agent:`/`instruction_source:` (today it only manages
`status`/`pr`/`commit`/`session-transcript`), so a record created without
them can be closed out without hand-editing YAML.

## Problem / Context

**Duplication search**: searched `project/work_items/` and
`project/design/` for prior coverage of this exact gap. `WI-DOCS-0013`
(resolved) covered an unrelated, older doc-drift issue - a stale
reference in `project/executions/README.md` to a `scripts/prompts/
record-execution` helper that was never built - not this gap in the real,
existing `lrh prompt record-execution` command's own field population.
No duplicate found.

**Demand search**: no open work item, proposal, or backlog entry requests
this. Not previously requested.

The `lrh` CLI (`logical_robotics_harness`) is a separate repository from
LCATS; this item cannot modify its source. The deliverable here is an
investigation and recommendation, not a code change to the tool itself.

## Scope

- Read the real current behavior of `lrh prompt record-execution --help`
  and `lrh prompt update-execution --help` directly from the installed
  `lrh` CLI, and generate at least one real execution record to confirm
  which frontmatter fields are and are not populated.
- Assess whether adding `--agent`/`--instruction-source` flags (with a
  sensible default, e.g. `agent: claude_app`) to `record-execution` is
  feasible and would close the gap without breaking existing callers.
- Assess whether `update-execution` should gain the ability to set
  `agent:`/`instruction_source:`, distinct from its current
  `status`/`pr`/`commit`/`session-transcript` fields.
- Write up findings and a concrete recommendation (implement upstream in
  `logical_robotics_harness`, or an LCATS-side wrapper/checklist if an
  upstream change is not imminent) as a design doc.

## Required Changes

1. Read `project/executions/README.md` and a sample of recent execution
   records to confirm the documented convention for `agent:`/
   `instruction_source:`/`session_transcript:`.
2. Run `lrh prompt record-execution --help` and `lrh prompt
   update-execution --help` against the installed `lrh` CLI and record
   the real, current flag set.
3. Generate a real, disposable execution record via `record-execution`
   and inspect its frontmatter directly to confirm which fields are
   populated vs. left blank.
4. Write `lcats/project/design/lrh-record-execution-agent-fields-investigation.md`
   with: the confirmed current behavior, the concrete recommendation for
   `record-execution`, the concrete recommendation for
   `update-execution`, and a plain statement of where this recommendation
   should be filed (an issue/PR against `logical_robotics_harness`, or an
   LCATS-side interim workaround).

## Non-Goals

- Do not implement or modify anything in the LRH repository
  (`logical_robotics_harness`) - this item only investigates and
  recommends.
- Do not add an LCATS-side wrapper script around `lrh prompt
  record-execution` unless the investigation doc explicitly recommends
  one as the interim path.
- Do not re-audit every past execution record for this gap - this item
  is about the CLI's future behavior, not a historical backfill sweep.

## Acceptance Criteria

- A written investigation doc exists documenting the current
  field-population behavior of `lrh prompt record-execution` and `lrh
  prompt update-execution`, verified against real CLI `--help` output and
  a real generated execution record, not assumption.
- The doc states whether adding creation-time flags or defaults (e.g.
  `--agent`, `--instruction-source`) to `record-execution` is feasible
  and desirable, with a concrete recommendation.
- The doc states whether `lrh prompt update-execution` should be
  extended to set `agent:`/`instruction_source:`, with a concrete
  recommendation.
- `lrh validate` reports 0 errors.

## Validation

- `lrh validate`
- `lrh prompt record-execution --help`
- `lrh prompt update-execution --help`

## Risk Notes

- The `lrh` CLI's version installed in this environment may drift from
  what's documented upstream (per this project's own known
  tool-version-drift issue) - confirm the installed version before
  drawing conclusions about current behavior.
- Any recommendation to change `record-execution`'s or
  `update-execution`'s flag surface must be filed against
  `logical_robotics_harness`, not implemented here.
