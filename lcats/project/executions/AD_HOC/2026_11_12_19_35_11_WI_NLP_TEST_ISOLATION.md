---
execution_id: 2026_11_12_19_35_11_WI_NLP_TEST_ISOLATION
prompt_id: "PROMPT(AD_HOC:WI_NLP_TEST_ISOLATION)[2026-11-12T18:24:28+00:00]"
work_item: AD_HOC
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/551
commit:
created_at: 2026-11-12T19:35:11+00:00
agent: codex_app
instruction_source: project/work_items/proposed/WI-NLP-TEST-ISOLATION.md
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
---

# Summary

Create the user-approved standalone work item for separating native NLP smoke
checks from ordinary unittest discovery, including bounded CPU smoke CI. This
AD_HOC record documents planning only, not implementation of the work item.

# Result

- Created `project/work_items/proposed/WI-NLP-TEST-ISOLATION.md` on isolated
  branch `codex/wi-nlp-test-isolation` from main `132c5862`.
- Incorporated the approved four-check relocation, strict smoke outcomes,
  CPU child execution, retained native diagnostics, and ordinary-test isolation.
- Incorporated the separately approved manual/weekly Ubuntu 24.04 / Python
  3.11 CPU workflow, versioned setup/caches, timeouts, and diagnostic artifacts.
  Documented the first-dispatch constraint and required real-run evidence.
- Opened planning PR [#551](https://github.com/xenotaur/LCATS/pull/551) against
  main as ready for review. Initial planning commit: `4df8c26e`.
- Left the work item proposed and Kenny's PR #548 untouched. No executable code,
  production defaults, contributor environments, or workflow files were changed.
- Resolved the Codex session identity through the metadata-only CLI; no
  transcript was exported. The work item's context records the diagnostic
  observations from the user-supplied before/after archives without treating
  CPU success as GPU repair or full-suite qualification.

The user approved the revised smoke-test approach, then CI scope, and explicitly
authorized opening the planning PR on 2026-11-12. The prior request to hold the
PR was lifted. No related resolved workstream was reopened.

# Validation

- `lrh prompt check-execution --slug wi-nlp-test-isolation --work-item AD_HOC
  --project-root .`: no prior execution record found before record creation.
- `lrh validate`: zero errors, 362 existing repository warnings; no warnings
  specific to the new work item. Rechecked with the populated execution record.
- `lrh work-items readiness WI-NLP-TEST-ISOLATION --format json`: prompt-ready,
  no blocking reasons or warnings.
- Reviewed the approved scope against main and checked patch whitespace.
- Product tests and the proposed smoke CI were not run: this PR changes only
  planning/control-plane documentation and does not implement those checks.

# Follow-up

- Review and land planning PR #551, then close out this planning execution.
  Landing this record must not resolve the unimplemented work item.
- Implement WI-NLP-TEST-ISOLATION in a separate PR against main after planning
  review, preserving the specified boundaries and recording validation.
- Obtain a post-fix confirmation on Kenny's affected machine without the shell
  workaround; the supplied CPU diagnostic runs predate the proposed fix.
- GPU installation repair, GPU/platform CI matrices, automatic PR/tag triggers,
  and release publication gating remain outside this work item.
