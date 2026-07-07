# Phase 4 repair/review/application integration audit — LCATS

- Prompt ID used: `PROMPT(AD_HOC:PHASE_4_INTEGRATION_AUDIT)[2026-06-18T00:00:00+00:00]`
- Audit date: 2026-06-18
- Scope: targeted Phase 4 integration path from classification to approved application.
- Source checklist: `project/audits/2026-06-16-special-character-cleanup-workstream-audit.md`.

## 1. Summary

The completed Phase 4 library components compose for a controlled, non-mutating
pipeline:

`classification -> repair proposal -> span operation -> review decision -> approved application`

The composition is sufficient to execute the June 16 PR A-D cleanup plan with
modifications: the plan should use canonical span operations and the new
application layer for PR B/D, but PR A/C still need the manifest, expanded
sequence-aware survey categories, and release-gate tests identified on June 16.

No code fixes or corpus rewrites were made in this PR.

## 2. Scope and source material

Reviewed required project guidance and source material:

- `STYLE.md`
- `project/executions/README.md`
- `project/audits/2026-06-16-special-character-cleanup-workstream-audit.md`
- `project/roadmap/roadmap.md`
- `project/focus/current_focus.md`
- `project/work_items/resolved/WI-REPAIR-0001.md`
- `project/work_items/active/WI-SPANOPS-0002.md`
- `project/work_items/active/WI-REVIEW-0003.md`
- `project/work_items/active/WI-APPLY-0005.md`
- `lcats/analysis/corpus/README.md`
- Phase 4 implementation modules under `lcats/analysis/corpus/`
- Targeted tests under `tests/analysis_tests/`

`PROMPTS.md` and `scripts/prompts/record-execution` were searched for but are
not present in this repository snapshot. Per `project/executions/README.md`, the
execution record for this task was added manually.

## 3. Phase 4 components reviewed

- Classification and survey support:
  - `lcats/analysis/corpus/specials.py`
  - `lcats/analysis/corpus/detectors/unicode.py`
  - `lcats/analysis/corpus/output.py`
- Repair proposal support:
  - `lcats/analysis/corpus/repairs.py`
  - `lcats/analysis/corpus/repairs_cli.py`
- Span operation support:
  - `lcats/analysis/corpus/span_ops.py`
- Review and override support:
  - `lcats/analysis/corpus/review.py`
- Approved application support:
  - `lcats/analysis/corpus/application.py`
- Test coverage reviewed:
  - `tests/analysis_tests/specials_test.py`
  - `tests/analysis_tests/specials_cli_test.py`
  - `tests/analysis_tests/corpus_survey_test.py`
  - `tests/analysis_tests/repairs_test.py`
  - `tests/analysis_tests/repairs_cli_test.py`
  - `tests/analysis_tests/span_ops_test.py`
  - `tests/analysis_tests/review_test.py`
  - `tests/analysis_tests/application_test.py`

## 4. End-to-end composition findings

Status: **composes cleanly at library level; needs workflow/product glue for the
June 16 release cleanup.**

Findings:

- Repair proposals can become canonical span operations through
  `repairs.suggestions_to_canonical_span_operations(...)`, which delegates to
  `span_ops.from_repair_suggestions(...)`.
- Span operations are reviewable because `review.SpanOperationReviewDecision`
  stores the reviewed operation, decision identity, reviewer, rationale, state,
  audit metadata, and optional override.
- Review decisions determine application eligibility through
  `review.is_span_operation_review_eligible_for_application(...)` and
  `review.operation_for_application(...)`.
- The application layer consumes approved decisions as-is and overridden
  decisions through reviewer replacement operations via
  `application.apply_reviewed_operations(...)`.
- Pending and rejected decisions are explicitly skipped by the application layer
  and included in the application report.

Seams to carry into follow-up PRs:

- The pipeline is currently library-first. There is no single CLI command that
  loads a manifest, emits canonical operations, loads review decisions, and
  writes approved transformed corpus outputs.
- `RepairSuggestion` does not include a source path or story identifier, so
  follow-up workflow artifacts must carry file/story identity outside the current
  suggestion object or extend the model deliberately.
- Canonical operation IDs are deterministic within a suggestion set, but they are
  ordinal (`spanop-000000-...`). They are suitable for one generated operation
  set, but not globally stable across different manifests or filtered subsets
  unless the surrounding workflow pins the input set.
- The older `repairs.apply_span_operations(...)` helper remains separate from
  the canonical reviewed application path. Follow-up cleanup PRs should use
  `application.apply_reviewed_operations(...)` after review, not the older helper
  as the release mutation path.

## 5. Metadata preservation findings

Status: **core repair/review/application metadata is preserved; source/story
identity remains external.**

| Metadata | Status | Notes |
| --- | --- | --- |
| source path or story identifier | **Gap** | Not present in `RepairSuggestion`, `SpanOperation`, or `ApplicationResult`; must be carried by the workflow/manifest or added intentionally. |
| offset/span | **Preserved** | Repair suggestions and span operations carry `start`/`end`; application reports operation identity rather than repeating offsets. |
| original text | **Preserved** | Suggestions and span operations carry `original_text`; application validates it against input text before transformation. |
| proposed replacement | **Preserved** | Suggestions and span operations carry `replacement_text`. |
| rule ID or rationale | **Preserved** | Suggestions carry `rule_id`, `evidence`, `confidence`, and `rationale`; canonical operations preserve them in provenance. |
| repair proposal identity | **Partial** | Suggestions do not have a separate proposal ID; identity is effectively rule/span/text metadata until converted to a span operation. |
| span operation identity | **Preserved** | `SpanOperation.operation_id` is serialized and used by review/application. |
| review decision identity | **Preserved** | `SpanOperationReviewDecision.decision_id` is serialized and reported by application. |
| reviewer/rationale | **Preserved** | Review decisions and application reports include reviewer and rationale. |
| override replacement | **Preserved** | Overrides carry a replacement `SpanOperation` and override rationale; application uses the replacement operation. |
| application result status | **Preserved** | `ApplicationResult` records success, original/transformed text, considered/applied/skipped reports, and failures. |

## 6. Application safety findings

Status: **approved/overridden application is safe and deterministic at library
level.**

- Approved operations apply as proposed.
- Overridden operations apply with the reviewer replacement operation.
- Pending and rejected operations do not apply and are reported as skipped.
- Invalid spans fail safely with `success=False` and `transformed_text` equal to
  the original input.
- Source-text mismatches fail safely before any successful transformation is
  returned.
- Overlapping/conflicting operations fail safely through canonical operation-set
  validation.
- Application order is deterministic and applies validated operations from right
  to left.
- Source text is not mutated by default; the result returns `original_text` and a
  separate `transformed_text`.

Audit note: this safety finding applies to the reviewed canonical application
path. It does not mean corpus files are rewritten safely by an end-user workflow;
that workflow still needs to be assembled in PR B/D.

## 7. June 16 PR A-D plan status

| PR | Status | Assessment |
| --- | --- | --- |
| PR A: correction ledger / manifest | **Executable with modifications** | Still needed. The manifest should now include or deterministically derive canonical span-operation inputs and stable source/story identity because the application layer expects reviewed span operations. |
| PR B: deterministic fixer / normalization tool using the manifest | **Executable with modifications** | The completed span/review/application pieces provide the safe apply path. PR B should avoid the older direct helper as the release path and instead generate canonical span operations plus review decisions. |
| PR C: survey improvements for release gating | **Executable as written** | This remains primarily a classification/survey release-gate task. Completed Phase 4 application does not supersede the need for sequence-aware categories and severity reporting. |
| PR D: targeted corpus cleanup and tests | **Executable with modifications** | Cleanup can proceed after PR A-C artifacts exist. The actual apply step should run through reviewed canonical operations and write transformed outputs separately before any explicit corpus replacement. |

Overall: the June 16 PR A-D plan should **proceed with modifications**, not be
superseded. Completed Phase 4 reduces the integration risk for PR B/D, while the
June 16 manifest, survey-gate, and missing-test work remains relevant.

## 8. Missing-test checklist status

Using the June 16 missing-test list as the checklist:

| Missing-test area | Status | Notes |
| --- | --- | --- |
| Sequence-aware classification fixtures for `√©`, `√®`, `√∂`, `√≤`, `√º`, `√±`, `Ã©`, `Ã«`, `Ãª`, `Ã¶`, `Ã¯`, `Â¢`, `째`, and `U+FEFF` before Gutenberg markers | **Partially covered** | Existing tests cover some `√©`, `Ã©`, and detector-level mojibake examples, but not the full June 16 sequence set or the `U+FEFF` marker case. |
| Preservation tests for legitimate `é`, `ö`, `è`, `ë`, `ê`, `ï`, `ñ`, `ü`, `ò`, `°`, `¢`, `¶`, `✠`, `❦`, `·`, `●`, `○`, and `■` where source-confirmed or allowed | **Still missing** | Allowlist/review suppression has tests, but the source-confirmed preservation matrix from June 16 is not covered as a release-cleanup fixture set. |
| Manifest parser/validator tests if a machine-readable correction ledger exists or is added | **Not applicable yet** | No machine-readable correction ledger was found in this audit scope. Add these tests with PR A if the ledger is code-backed. |
| Survey release-gate tests proving `mojibake_sequence` is `error`, while allowed/source-confirmed cases are `info` or suppressed only by documented review/allow decisions | **Partially covered** | Detector tests cover `mojibake-sequence` error behavior, but the exact June 16 `mojibake_sequence` release-gate model and allowed/source-confirmed distinction is not fully encoded. |
| Lightweight before/after survey snapshot workflow coverage | **Still missing** | The June 16 workflow is documented, but no lightweight before/after snapshot test or fixture workflow was found. |

## 9. Recommended next steps

1. Keep the June 16 PR A-D plan, but update PR B/D acceptance criteria to require
   canonical span operations, span-operation review decisions, and
   `application.apply_reviewed_operations(...)` for approved application.
2. Add source path/story identity to the manifest/workflow artifact before
   generating reviewable operations.
3. Add the full missing-test checklist during PR A-C rather than after corpus
   cleanup.
4. Treat operation IDs as generated artifacts tied to a particular manifest/run,
   unless a follow-up deliberately introduces globally stable operation IDs.
5. Add CLI/product glue only after manifest and release-gate behavior are clear.

## 10. Explicit deferrals

- No code fixes were implemented.
- No corpus text was rewritten.
- No persistence system was added.
- No broad roadmap rewrite was performed.
- No unrelated execution records were changed.
- No README updates were needed because `project/audits/` has no README/index in
  this repository snapshot and the corpus-analysis README already documents the
  completed application stage.

## 11. Validation performed

- Confirmed this audit file was created under `project/audits/`.
- Confirmed referenced project paths exist, except for the requested but missing
  `PROMPTS.md` and `scripts/prompts/record-execution` helper.
- Ran targeted documentation/path checks with shell commands listed in the
  execution record.
- Ran the focused Phase 4 application unit tests.

## 12. Soft idempotence check

- Searched for the exact prompt ID
  `PROMPT(AD_HOC:PHASE_4_INTEGRATION_AUDIT)[2026-06-18T00:00:00+00:00]`.
- Searched for substantially similar Phase 4 integration audits and
  repair/review/application audit names.
- Found the June 16 special-character cleanup workstream audit and the June 18
  WI-APPLY-0005 execution record, but no existing Phase 4 integration audit for
  this prompt.
- Proceeded by adding this new targeted audit rather than duplicating an existing
  artifact.
