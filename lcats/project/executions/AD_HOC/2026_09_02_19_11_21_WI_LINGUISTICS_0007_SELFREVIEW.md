---
execution_id: 2026_09_02_19_11_21_WI_LINGUISTICS_0007_SELFREVIEW
prompt_id: PROMPT(AD_HOC:WI_LINGUISTICS_0007_SELFREVIEW)[2026-09-02T19:11:14+00:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/423
commit: ede5d004338917e383369f3b98d49ee7beb7baa7
created_at: 2026-09-02T19:11:21+00:00
agent: codex_app
instruction_source: project/work_items/proposed/WI-LINGUISTICS-0007.md
session_transcript: pending
---

# Summary

Diff-mode `/lrh-self-review` for `WI-LINGUISTICS-0007`, run from
`/lrh-implement` Step 7.5 before opening the PR. The cold-context subagent
reviewed the in-progress experiment-09 rich-linguistics pilot, generated
evidence, Parquet bridge, and follow-on storage-design work item against the
work item's requirements.

# Result

The report-only self-review found one real P1 issue: the original POS audit
sampler sorted machine `NOUN` candidates ahead of every other row and took the
first 24 rows per genre, so the generated audit CSV contained only machine
`NOUN` rows and many punctuation-like tokens. That made the preregistered
noun-family recall gate impossible to evaluate because false negatives require
machine-negative candidates.

Independently re-verified the finding by inspecting
`experiments/09_rich_linguistics_genre_sample/run_rich_linguistics_sample.py`
and summarizing
`experiments/09_rich_linguistics_genre_sample/results/pos_audit_sample.csv`
with `csv.DictReader`: the pre-fix CSV had 192 rows, all machine `NOUN`, and
153/192 rows had no alphabetic characters.

Fixed the issue before first PR push by:

- excluding non-letter tokens from POS audit candidates;
- splitting each genre's 24 audit rows into 8 machine `NOUN`, 8 machine
  `PROPN`, and 8 machine-negative `OTHER` rows when candidates are available;
- adding `audit_bucket` and `audit_features` fields to make the sampling
  rationale reviewable;
- round-robin selecting within each POS bucket across contractions/possessives,
  hyphenated tokens, archaic candidates, noun/verb ambiguity, proper-name
  candidates, and ordinary tokens; and
- adding a regression test for balanced per-genre POS bucket selection.

Rechecked the regenerated audit CSV after the fix: 192 rows total, exactly 64
rows in each `NOUN`/`PROPN`/`OTHER` audit bucket, 8 rows per bucket for each of
the eight genres, 0 non-letter tokens, and feature coverage across
proper-name candidates, contractions/possessives, hyphenation, archaic
candidates, noun/verb ambiguity, and ordinary tokens.

# Validation

- Subagent self-review reported one P1 audit-sampling issue.
- Main session independently re-verified the finding and fixed it before PR
  creation.
- `python -m unittest experiments/09_rich_linguistics_genre_sample/run_rich_linguistics_sample_test.py` — 6 tests OK after the sampler fix.
- `python experiments/09_rich_linguistics_genre_sample/run_rich_linguistics_sample.py --overwrite` — fresh 146-story run completed cleanly after the fix, with 146 written outputs and a regenerated balanced audit packet.
- `python experiments/09_rich_linguistics_genre_sample/parquet_bridge.py export experiments/09_rich_linguistics_genre_sample/results/copied_buckets experiments/09_rich_linguistics_genre_sample/results/parquet` — refreshed the compact Parquet package after the fresh run.
- `git diff --exit-code -- ../corpora` from `lcats/` — no corpus-tree changes.

# Follow-up

- No further self-review findings remain from this diff-mode pass.
- The human POS audit labels are still pending; downstream POS figures and the
  full-corpus run remain deferred until that human evidence is supplied and
  scored.
