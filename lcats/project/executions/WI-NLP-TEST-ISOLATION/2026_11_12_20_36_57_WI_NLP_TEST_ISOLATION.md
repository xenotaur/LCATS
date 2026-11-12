---
execution_id: 2026_11_12_20_36_57_WI_NLP_TEST_ISOLATION
prompt_id: PROMPT(WI-NLP-TEST-ISOLATION:WI_NLP_TEST_ISOLATION)[2026-11-12T20:09:19+00:00]
work_item: WI-NLP-TEST-ISOLATION
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/552
commit:
created_at: 2026-11-12T20:36:57+00:00
agent: codex_app
instruction_source: project/work_items/proposed/WI-NLP-TEST-ISOLATION.md
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
---

# Summary

Implement WI-NLP-TEST-ISOLATION on a separate branch from main: isolate four
real NLP checks from ordinary discovery, retain assertions, add bounded CPU
smoke execution and diagnostics, document usage, and add manual/weekly CPU CI.

# Result

The user approved the run plan, completion/stop conditions, and clone-local
skip-consent grant. Consent was verified valid against the unchanged policy;
all 18 watched installed-target fingerprints remained fresh. The approved
plan satisfied the inlined implementation gate without material divergence.
No restamp or repository policy change was made. Prior-art and demand checks
were present in the WI; dependencies were empty, readiness passed, and the
pre-mint execution-history check found no prior implementation.

Created branch `xenotaur/feat/wi-nlp-test-isolation` from refreshed main
`34ddb3b0a35edd10b9d0c7b74d0c554e045b9c76`. Implementation commit `7392fef5`
removes the import-time model probes and relocates the four real-model tests
to `tests/smoke/nlp_smoke.py`. It introduces a test-only bounded child runner,
separate fault/stdout/stderr logs, strict completion receipts, offline execution,
CPU controls, pinned resource provisioning and checksum validation, 14 harness
regressions, docs, and the approved CPU workflow. Production source and defaults
are unchanged. No writes or review actions targeted Kenny's PR #548.

Opened [PR #552](https://github.com/xenotaur/LCATS/pull/552) against main. The
required independent diff review found no actionable defects and independently
passed the harness and real smoke checks; its linked record documents scope
and evidence. The PR's automatic review remains a separate signal.

Detailed diagnostic archive/member provenance, assertion relocation, validation,
timings, and outstanding acceptance evidence are recorded in
[NLP test-isolation evidence](../../development/nlp-test-isolation-evidence.md).

# Validation

- Python 3.11.9; Black 25.11.0; Ruff 0.15.0; actionlint 1.7.12.
- `scripts/format --check --diff`, `scripts/lint`, and
  `actionlint ../.github/workflows/smoke.yml`: passed.
- `scripts/test tests/analysis_tests/event_role_world_harness_test.py`: 14 passed.
- Targeted event-role-world and linguistics modules: 121 and 64 passed.
- `scripts/test`: 3,161 passed with NLP extras (110.754 seconds), and 3,161
  passed in a clean environment without them (96.844 seconds).
- `scripts/smoke`: all four real CPU tests passed. Fresh setup with empty Stanza
  and Hugging Face caches: 43.53 seconds; subsequent inference: 18.01 seconds;
  warm offline prerequisite validation: 1.52 seconds.
- Deliberately missing Stanza models: three spaCy passes, one refusal, exit 1,
  retained traceback, no Stanza receipt. Expected failure was not counted green.
- Independent reviewer reran all 14 harness and four real checks successfully.
- `lrh validate`: 0 errors, 362 existing warnings. `git diff --check`: clean.
- Earlier sandbox runs could not bind local sockets (Black manager / 99 HTTP
  fixture errors); approved execution outside the sandbox passed. No tests
  were skipped to hide those errors. Full output was captured externally because
  LCATS `scripts/test` lacks the LRH `--log` flag. `scripts/version tools` gave
  no useful listing, so actual tool versions were also read from package metadata.
- New workflow execution is not yet claimed: live GitHub lookup before first
  push returned HTTP 404 for `smoke.yml`; default-branch dispatch prerequisites
  and the required first-run plan are documented. Existing PR CI is separate
  from real NLP smoke CI.

# Follow-up

Account for hosted review and PR CI, and present the reviewed first-run/merge
verification plan if the workflow cannot dispatch from the implementation ref.
Keep the work item proposed until real Ubuntu cold/warm smoke runs, failure
artifact verification, and Kenny's affected-host confirmation are accounted
for. No merge or WI resolution is authorized merely by local validation.
