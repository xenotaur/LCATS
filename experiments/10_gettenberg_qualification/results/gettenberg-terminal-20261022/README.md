# Terminal-note decisions: complete workflow, unresolved editorial openings

Human grant: 45-minute target /60-minute maximum from 2026-10-22 05:22:16 UTC.
Starting commit `c54d17eb`; continuation of PR #524, no integration/main promotion.

The qualified terminal-note rule now composes with ordered bracketed notices and
explicit v2 decisions. Original candidate coordinates, exact retained characters,
source/context identities and strict omission partitioning remain mandatory. Default
extraction and existing proposal modes are unchanged. Terminal-mode recording
requires a source-bound review packet for every proposal, including exact baseline
equality. Historical preservation alone cannot establish editorial roles.

## Results

All 25 history-complete cases from the previous census retain teaser-like opening
material that was already present in old output. Thirteen also retain detected
editorial labels/readiness findings. Twelve passed mechanical eligibility and
historical checks but were rejected by explicit source inspection. All 25 are now
`defer`, with exact candidate/raw-source anchors and attributable reasons. These
judgments are boundary/context reviews, not complete literary readings. No opening
is deleted or automatically classified as a publisher blurb.

The complete population replay verifies 1,659 inputs, 14 resolved historical changes
and 1,628 unresolved, with zero new approval proposals after the deferrals. Candidate
inventory: 1,585 unreviewed, 13 approve, 7 exclude, 35 defer; zero conflicts. The 19
non-candidate inputs remain accounted for. All 30 inherited dispositions are unchanged;
25 new immutable deferrals bring the cumulative record count to 55. The source-review
input has 41 records. Intent counts and historical resolutions are separate measures.

The combined mode recognizes terminal notes in 134 population inputs (133 were in
the earlier boundary group), without asserting their publication readiness. Combined
notice transformations qualify in 868 inputs; 234 are mechanically eligible. These
are broad measurement counts, not approvals or newly resolved cases.

Actual cached replay withholds all 25 deferred cases and preserves their full review
candidates. The nonempty success path is tested on authored source fixtures: explicit
cohort review, immutable recording/export, exact v2 selection, actual disposable
publication and cumulative reconciliation. Real corpus approval count is zero.

## Evidence and reproduction

- `measurement-*` captures the pre-review proposals; `ledger.json.gz` and
  `summary.json` capture the final cumulative replay with the 25 deferrals.
- `cohort-inspection.json` records all source/candidate anchors, exact notice and
  history proofs, and each deferral. `review-context-clarifications.json` corrects
  one narrow wording issue for three entries: credits or a motto intervene before
  narrative paragraphs. Original immutable disposition bytes are preserved.
- `disposition-manifest.json` locates and hashes all 55 records: 30 in existing
  archives and 25 under `new-dispositions/`. `cumulative-reviews.json` preserves the
  previously reviewed intents and adds these 25 exceptions.
- `withholding.json` records actual cached publication outcomes. `independent-review.json`
  and `coordinator-reverification.json` document separate checks.
- `wheel.json`, `installed.json`, `validation.json` and compressed logs preserve
  validation evidence, including the initial failing test-fixture log and its repair.

From `lcats/`, use project Python with `PYTHONPATH="$PWD/src"`. Assemble a temporary
cumulative disposition directory by copying each exact `repository_path` named in
`disposition-manifest.json`, verifying its SHA256 first. Supply the same external
candidate queue and historical decoded/re-encoded UTF-8 source cache as prior runs;
they are not original HTTP bytes. Missing or stale inputs fail rather than fetch.

```bash
python ../experiments/10_gettenberg_qualification/scripts/qualify_review_batch.py ../experiments/10_gettenberg_qualification/results/gettenberg-readiness-20261020/census-final.json.gz ../experiments/10_gettenberg_qualification/results/gettenberg-readiness-20261020/full-corpus-final.json.gz QUEUE CUMULATIVE_DISPOSITIONS TEXT_CACHE ../corpora/mass_quantities NEW_OUTPUT --prior-reviews ../experiments/10_gettenberg_qualification/results/gettenberg-terminal-20261022/cumulative-reviews.json --prior-dispositions CUMULATIVE_DISPOSITIONS --rule terminal --historical-acceptance source-grounded --record-qualified --cohort-review ../experiments/10_gettenberg_qualification/results/gettenberg-terminal-20261022/cohort-review.json
python -m unittest tests.gatherers_tests.trailing_notice_test tests.gettenberg_tests.terminal_batch_evidence_test
```

The empty cohort packet is correct because final recording has no new approval
proposals. The batch runner is offline, uses an exclusive output directory and the
existing bounded readers, 600-second POSIX alarm and 6GiB free-space minimum. See the
parent README for publication replay and explicit experiment format/lint commands.

## Validation and next step

3,108 canonical tests pass in 105.086s; focused 11 tests; independent 32 tests. Package
and changed batch runner format/lint pass. Fresh wheel/install has all 173 Python
modules and 2 JSON resources byte-identical to source, no gutenbergpy; installed smoke,
pip check and all 11 focused tests pass. All 1,659 source/corpus identities and 30 prior
dispositions remain unchanged. Independent review reproduced every final ledger row,
checked all 25 judgments and both historical modes’ cohort gate. No blocking findings. LRH validation: zero errors, 351 existing warnings.

Next substantive work should establish positive source-grounded evidence for opening
editorial material, deliberate separate-metadata selections and full historical
accounting. Repeated terminal-note-only tranches will not resolve these openings.
Preserve known deferrals; do not turn formatting/position into a blurb classifier.
No corpus acceptance, default extraction change, main promotion or terminal closeout.
