---
execution_id: 2026_08_22_06_24_04_WI_LINGUISTICS_0002_REVIEW
prompt_id: PROMPT(AD_HOC:WI_LINGUISTICS_0002_REVIEW)[2026-08-22T06:23:59+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_08_22_06_12_51_WI_LINGUISTICS_0002
pr: https://github.com/xenotaur/LCATS/pull/353
commit: fd050d710e83330cc2eec7d0724d1dd17af158b7
created_at: 2026-08-22T06:24:04+00:00
agent: codex_app
instruction_source: prompt://lrh-review-response PR-353 round-2
session_transcript: pending
---

# Summary

Responded to a newly surfaced Copilot review finding on PR #353 for
`WI-LINGUISTICS-0002`.

# Result

Addressed the corpus-sidecar reporting finding. `build_report()` no longer
scans the entire configured corpus with a broad `**/linguistics*.json` glob.
It now checks only the selected source story buckets and looks for both
`linguistics.json` and `linguistics.tokens.json`, avoiding full-corpus cost and
false positives from unrelated pre-existing sidecars.

Pushed fix commit `540411da` to PR #353.

# Validation

- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin python experiments/06_linguistics_genre_sample/run_linguistics_sample_test.py`
  -> OK, 7 tests.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin ruff check experiments/06_linguistics_genre_sample`
  -> OK.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin python -m black --check --diff experiments/06_linguistics_genre_sample`
  -> OK, 2 files unchanged.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin scripts/version tools`
  -> OK (`lcats 0.1.1.dev691+ga13ced159` before the second fix and
  `lcats 0.1.1.dev695+g25dbfeb14.d20260822` after refreshing the editable
  install, Python 3.11.8, Ruff 0.15.0, Black 25.11.0).
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin scripts/format --check --diff`
  -> OK, 198 files unchanged.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin scripts/lint`
  -> OK.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin scripts/test`
  -> OK, 1833 tests after refreshing the editable install for this checkout.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin lrh validate`
  -> 0 errors, 178 pre-existing warnings.

# Follow-up

Continue the PR #353 landing chain: push this review-response record, wait for
updated CI/review state, confirm fixes, and merge only after the gates are
clear.
