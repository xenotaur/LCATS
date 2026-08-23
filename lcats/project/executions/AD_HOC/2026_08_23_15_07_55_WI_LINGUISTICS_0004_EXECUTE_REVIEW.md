---
execution_id: 2026_08_23_15_07_55_WI_LINGUISTICS_0004_EXECUTE_REVIEW
prompt_id: PROMPT(AD_HOC:WI_LINGUISTICS_0004_EXECUTE_REVIEW)[2026-08-23T15:07:43+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_08_23_06_45_42_WI_LINGUISTICS_0004
pr: https://github.com/xenotaur/LCATS/pull/376
commit: 73c5a2d2
created_at: 2026-08-23T15:07:55+00:00
---

# Summary

Review-response pass for PR #376 after Codex posted two issue-comment
findings.

# Result

- PR: https://github.com/xenotaur/LCATS/pull/376
- Review-fix commit: `73c5a2d2`
- Fixed the smoke-count provenance finding by recording
  `source_story_count` before applying `--smoke-count`, while keeping
  `selected_story_count` for the sliced analysis set.
- Fixed the empty-body story finding by copying empty-body story buckets for
  provenance but excluding them from linguistic analysis and reporting them in
  `analysis_exclusions`.
- Regenerated the full experiment results. The corrected run copies 1,868
  story buckets, excludes one empty-body story, writes 1,867 compact
  `linguistics.json` sidecars, and leaves the excluded copied bucket without a
  sidecar.
- Confirmed no generated sidecars were written under `corpora/`.

# Validation

- `python experiments/07_linguistics_corpora/run_linguistics_corpora_test.py`
  passed: 10 tests.
- `python experiments/07_linguistics_corpora/run_linguistics_corpora.py --backend fake --smoke-count 2 --overwrite`
  passed and reported `source_story_count: 1868`.
- `python experiments/07_linguistics_corpora/run_linguistics_corpora.py --backend spacy --smoke-count 5 --overwrite`
  passed and reported `source_story_count: 1868`.
- `python experiments/07_linguistics_corpora/run_linguistics_corpora.py --backend spacy --overwrite`
  passed: 1,867 written, 1 empty-body exclusion, 0 failures, elapsed
  3,979.96 seconds.
- `find corpora -path '*linguistics.json' -o -path '*linguistics.tokens.json' | wc -l`
  returned `0`.
- `find experiments/07_linguistics_corpora/results/copied_buckets -name linguistics.json | wc -l`
  returned `1867`.
- `test ! -e experiments/07_linguistics_corpora/results/copied_buckets/ohenry-whirligigs/madame_bo_peep_of_the_ranches/linguistics.json`
  passed.
- `PATH=<project-python-env>:$PATH scripts/format --check --diff` passed from
  `lcats/`.
- `PATH=<project-python-env>:$PATH scripts/lint` passed from `lcats/`.
- `PATH=<project-python-env>:$PATH scripts/test` passed from `lcats/`: 2,017
  tests. As before, the first attempt after code changes hit a stale editable
  install pointing at another checkout; rerunning `scripts/develop` with
  network access refreshed the install and the second run passed.
- `lrh validate` passed from `lcats/`: 0 errors, existing warnings.

# Follow-up

- Push the review-fix commit and this record, then rerun confirm-fixes against
  the new PR head.
