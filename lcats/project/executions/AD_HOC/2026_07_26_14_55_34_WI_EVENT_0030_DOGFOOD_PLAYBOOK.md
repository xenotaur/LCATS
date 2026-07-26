---
execution_id: 2026_07_26_14_55_34_WI_EVENT_0030_DOGFOOD_PLAYBOOK
prompt_id: PROMPT(AD_HOC:WI_EVENT_0030_DOGFOOD_PLAYBOOK)[2026-07-26T14:52:57-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/164
commit: 960f26ed
agent: claude_app
instruction_source: ad-hoc user request to save the WI-EVENT-0030 dogfood playbook and expand its smoke-test step into zero-dependency/spaCy/Stanza subsections
session_transcript: pending
created_at: 2026-07-26T14:55:34-04:00
---

# Summary

Save the WI-EVENT-0030 pilot dogfood playbook as a proper Diátaxis how-to runbook, split its smoke-test step into three subsections (zero-dependency, spaCy, Stanza), and fix the real bug found while writing the zero-dependency subsection: `--dry-run` still required a real spaCy/stanza install.

# Result

- Created `experiments/03_cross_segment_relation_pilot/running_the_pilot.md` — a developer runbook (env setup, 3-way smoke test, real run, results write-up, WI-EVENT-0030 closeout, troubleshooting), structured like `docs/reference/prepare-corpora-release.md`, per the earlier session decision to use this location + one link from `docs/index.md` rather than folding it into the pilot's own viewer-facing README.
- Found and fixed a real bug: `_run_erw_pipeline` unconditionally called `erw_surface.make_nlp_backend(nlp_backend_name)` for stage-2 surface features even under `--dry-run`, reproducing the exact `ModuleNotFoundError: No module named 'spacy'` the user hit — PR #158's FakeBackend fix only covered LLM calls, not this separate NLP-toolkit dependency. Fixed by adding `"fake"` as a real `--nlp-backend` choice (`nlp_backend.FakeNLPBackend`, already existed in the codebase but was unused), defaulted under `--dry-run` unless the user explicitly overrides it with `spacy`/`stanza` — enabling the playbook's 2b/2c subsections to smoke-test a real NLP toolkit install with zero API cost.
- Trimmed `README.md`'s dry-run section to point to the new runbook; linked the runbook from `lcats/docs/index.md`'s "How-to guides" section.

# Validation

- `black --check`/`ruff check` on `run_pilot.py` — clean.
- `scripts/test` — 1436 tests pass. `lrh validate` — 0 errors, 43 pre-existing unrelated warnings.
- Scripted assertion that `--dry-run`'s default path never calls `make_nlp_backend` (patched it to raise if called; confirmed never hit).
- Real end-to-end runs of `--dry-run --nlp-backend spacy` and `--dry-run --nlp-backend stanza` (both installed in this environment), producing real non-zero word counts with zero LLM API cost.

# Follow-up

- `session_transcript: pending` should be updated to `claude-app:<session-id>` after this session ends.
- Wait for reviewer comments and run `/lrh-review-response https://github.com/xenotaur/LCATS/pull/164` to address them, then `/lrh-confirm-fixes` before merge. After merging, run `/lrh-closeout` to land this record.
