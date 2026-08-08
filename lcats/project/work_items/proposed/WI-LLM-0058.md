---
resolution: null
blocked_reason: null
blocked: false
id: WI-LLM-0058
title: Diagnose ASSESSMENT_TOOL schema-adjacent field corruption in forced tool-call output
type: investigation
status: proposed
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams: []
related_design:
  - project/design/event-role-world-genre-target-reconciliation.md
depends_on: []
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - run_paid_full_diagnostic_without_go_ahead
acceptance:
  - "The corruption is reproduced against a fresh, targeted sample (not just re-analysis of WI-ASSESS-0051's existing 20-story sample) and its rate/pattern is characterized: which field(s) are affected, whether it's confined to secondary_genre or reaches other adjacent fields (verdict, summary, issues), and whether it ever touches detected_genre itself"
  - "A documented root-cause hypothesis is reached and stated with its supporting evidence (e.g. schema field-adjacency, forced tool_choice generation behavior) - or a good-faith investigation finds no reproducible root cause and that is stated plainly, not left open"
  - "If a fix is identified (e.g. ASSESSMENT_TOOL field reordering, or a runtime validation check that flags malformed-looking string fields): it is implemented with a regression test, or an explicit decision not to fix now is recorded with rationale"
  - "A written go/no-go recommendation for WI-ASSESS-0051's --full corpus run: is this corruption a blocker, and if so what threshold/fix resolves it"
  - "scripts/test passes with no new failures"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - test_output
artifacts_expected:
  - lcats/src/lcats/analysis/corpus/assess.py
  - lcats/tests/analysis_tests/assess_test.py
---

## Summary

Diagnose a data-quality defect found during WI-ASSESS-0051's 20-story
real-API cost-estimate sample: 7 of 20 (35%) `assess_story()` tool-call
responses had a corrupted `secondary_genre` field containing literal
tool-call XML fragments (e.g. `"</antml：parameter>\n<parameter
name=\"specials_verdict\">author_intentional"`), invisible to
`result.error` since the JSON still parses as structurally valid. Root
cause is currently only hypothesized (schema field-adjacency); this item
investigates, characterizes scope, and fixes or explicitly defers.

## Problem / Context

`ASSESSMENT_TOOL`'s schema in `lcats/src/lcats/analysis/corpus/assess.py`
defines `secondary_genre` immediately followed by `specials_verdict`
(`assess.py:107`, `assess.py:119`, adjacent again in the `required` list
at `assess.py:168-169`). In 7/20 sample records, `secondary_genre`'s
string value contains what looks like a fragment of the *next* field's
opening tag bleeding into the current field during the model's forced
tool-call generation (via `AnthropicBackend.complete()`,
`anthropic_backend.py`). The resulting JSON is well-formed enough that
neither `TruncatedResponseError` nor `NoToolCallError` fires, so
`result.error` stays empty - this defect is currently invisible to any
caller's exclusion/validation logic, including
`experiments/04_genre_census/run_census.py`'s own exclusion counting.

`detected_genre` itself was clean in all 20 sample records - only
`secondary_genre` showed corruption. But `run_census.py`'s per-story
record doesn't currently capture `verdict`/`summary`/`issues`, so there
is no evidence the corruption is confined to `secondary_genre` - it may
reach other fields, just unobserved because they aren't recorded today.

This blocks confident approval of WI-ASSESS-0051's `--full` corpus run
(~$435, ~1,868 stories): a 35% corruption rate on one field in a 20-story
sample is a real signal worth understanding before scaling ~93x, even
though the corpus census's primary output (`detected_genre`) wasn't
observed to be affected yet.

### Duplication search
- In-repo: no prior report of this corruption pattern found (grepped
  `secondary_genre`, `antml`, "field corrupt", "adjacent field" across
  `project/`) - only hits are WI-ASSESS-0031's original introduction of
  the `secondary_genre` field itself, not this defect.
- `project/design/backlog.md` has unrelated malformed-data entries (e.g.
  the container-type-check gap in extractor `build_*()` functions) but
  nothing matching this tool-call-generation-level corruption.
- Sibling repos / external libraries: none identified.
- Recommendation: proceed.

### Demand search
- Work items: none found requesting this beyond WI-ASSESS-0051's own
  sample run surfacing it as a new finding this session.
- Proposals, backlog: no existing entry.
- Recommendation: proceed; this is new information, not yet tracked
  anywhere.

## Scope

- Reproduce the corruption against a small, fresh, targeted sample (reuse
  `assess_story()` directly, not a full `run_census.py` invocation) to
  confirm it isn't an artifact specific to the original 20-story run.
- Extend the diagnostic to capture the *full* raw tool result (not just
  the fields `run_census.py` currently records) so corruption in
  `verdict`/`summary`/`issues`/other fields can be detected if present.
- Characterize whether `detected_genre` itself is ever affected - this is
  the determining factor for whether WI-ASSESS-0051's census counts can
  be trusted at all.
- Form and document a root-cause hypothesis (schema adjacency is the
  leading candidate given the reproducible field-pair pattern, but should
  be tested, e.g. by reordering `secondary_genre`/`specials_verdict` in a
  branch and checking whether the corruption pattern shifts to whichever
  fields become newly adjacent).
- If a low-risk fix is identified, implement it with regression test
  coverage. If the right fix is unclear or high-risk, document findings
  and recommend next steps rather than forcing a fix under time pressure.

## Required Changes

1. A diagnostic script or test harness (can be a throwaway/scratch script
   documented in the PR, or a proper test fixture if it has lasting
   value) that runs `assess_story()` against a handful of real stories
   and captures the complete raw tool result for inspection.
2. `lcats/src/lcats/analysis/corpus/assess.py`: the fix, if one is
   identified and low-risk (e.g. reordering `ASSESSMENT_TOOL`'s schema
   fields so `secondary_genre` is not immediately followed by another
   required string field).
3. `lcats/tests/analysis_tests/assess_test.py`: regression test(s)
   covering the fix, or covering detection of the corruption pattern if
   a runtime guard is added instead of/alongside a schema change.
4. A written finding (in this work item's own execution record, or a
   short note appended to `project/design/event-role-world-genre-target-reconciliation.md`
   if warranted) stating the go/no-go recommendation for WI-ASSESS-0051's
   `--full` run.

## Non-Goals

- Do not run WI-ASSESS-0051's `--full` corpus run - that remains gated on
  WI-ASSESS-0051's own explicit human go-ahead, informed by this item's
  findings.
- Do not modify `experiments/04_genre_census/run_census.py`'s CLI surface
  or cost-gating logic beyond what's needed to capture full raw tool
  results for diagnosis (e.g. a diagnostic-only flag or a separate
  scratch script is preferred over expanding its committed output
  schema, unless the investigation concludes the committed per-story
  record itself should capture more fields).
- Do not change `lcats assess`'s CLI surface.
- Do not spend real API cost beyond a small, targeted diagnostic sample
  (a handful of stories, not a repeat of the full 20-story/$4.66 sample)
  without explicit go-ahead - see `forbidden_actions`.

## Acceptance Criteria

(see frontmatter `acceptance:` - kept in sync)

## Validation

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- Diagnostic reproduction run against a small real-API sample (requires
  `ANTHROPIC_API_KEY`, real but small $ cost - go-ahead required per
  `forbidden_actions`)

## Risk Notes

- **Small but real $ cost** for the diagnostic reproduction sample -
  should be a handful of stories, not a repeat of the full 20-story
  sample.
- **Schema changes carry regression risk** - `ASSESSMENT_TOOL` is used by
  `lcats assess`'s CLI and any existing checkpoint fingerprints keyed to
  `_CLASSIFIER_VERSION`; a field-reordering fix should bump that version
  marker in any caller relying on it (e.g.
  `experiments/04_genre_census/run_census.py`'s own
  `_CLASSIFIER_VERSION`) so stale pre-fix checkpoints aren't silently
  reused.
- **Root cause may not be fully resolvable** - this could be an
  underlying Anthropic API/model tool-call generation quirk outside this
  codebase's control; if so, the right outcome is a documented mitigation
  (e.g. a runtime sanity check flagging suspicious field content) rather
  than a "root cause eliminated" claim.
