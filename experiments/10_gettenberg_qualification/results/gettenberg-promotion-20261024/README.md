# Main-promotion qualification — 2026-10-24

Product commit `0dbe9606b446be5ce34e52350947fd4911e3c89a` combines qualified internal
merge `df05525618d701be0d5a5ea2d2840774f00c1368` with main
`22a739d25c5a72359c1f8e37f54f9059876e6798`. This records promotion preparation,
not human main approval, completed native closeout or package/corpus publication.
See the [review guide](../../../../lcats/project/development/gettenberg-main-promotion.md).

## Integration and source transfer

PR #530 merged with an exact-head lock after all four checks passed and GraphQL
reported zero unresolved review threads (pagination complete). Its merged tree
exactly equals approved head c6fd5e49. No branch deletion or merge of PR #524 occurred.

All 1,763 main-only changed/deleted paths match main exactly. Two overlapping docs
merged cleanly and retain both changes. Only two product files differ from the
qualified internal candidate: llm/backend.py and llm/openai_backend.py; both exactly
match main. All gettenberg, gatherer, package and CI configuration sources are
unchanged. No manual product edit was needed. The main-merge proof pins Git blob
identities; the change inventory is the pre-promotion-documentation path inventory,
not a final GitHub file-count claim.

Prior full metadata, cleanup/body census, actual batch-yield and independent
provider review evidence transfers on these unchanged component identities. This
is not a new independent review of all historical code or a rerun of the full
catalog/publication benchmarks. The unrelated main backend changes are covered
by the fresh canonical suite and installed smoke below.

## Fresh validation

- Canonical `scripts/test`: **2,972 tests pass in 110.306s**. Main adds tests beyond
  the previously qualified 2,956-test candidate. Negative-case error messages in
  the raw log are expected test output; the final result is OK.
- Canonical format/lint pass. LRH: **0 errors /354 warnings** in the combined tree.
  This differs from the earlier 351-warning tree because main also advanced.
- Fresh isolated wheel, empty source staging: all **165 Python modules and two JSON
  files** exactly match committed source; no extra separated runtime and no
  gutenbergpy/direct URL/VCS requirement. Physical installed tree matches too.
- Fresh venv install uses the earlier recorded qualification dependency constraints;
  exact installed packages are retained here. `pip check` passes. No project-environment
  mutation, credentials change, Gutenberg acquisition or canonical corpus write.
- Installed smoke passes real catalog/resource/decode/cleanup/gather publication,
  reuse, explicit refusal and log-root protection fixtures outside the checkout.
- Actual installed CLI success → refusal → success passes twice: two outputs, one
  refusal, complete ordered event logs, unchanged repeat output bytes and status 2.
  All 70 smoke and 98 CLI loaded-module origin hashes match the committed wheel.
- Actual promotion diff against main passes whitespace checks. The intermediate
  main-merge diff exposed existing CRLF/trailing-blank whitespace in main's archived
  Worldcon report; those original bytes were preserved, not reformatted.

`artifact-manifest.json` pins all files in this bundle. It does not incorporate a
future hosted-CI result: final PR-head checks must be observed separately. Historical
acceptance artifacts and experimental outputs outside this new directory are unchanged.

## Reproduction and limits

Build fresh staging with `git archive 0dbe9606 lcats`, then `python -m build --wheel`
with normal build isolation. This qualification used
`SETUPTOOLS_SCM_PRETEND_VERSION_FOR_LCATS=0.1.0+qualification.promotion` because
archive staging has no Git metadata. It is a qualification-only label, not proof of
the eventual release version; release WIs0037/0039 retain that verification.

Install the resulting wheel in a new isolated venv using
`../gettenberg-delivery-review-20261024/qualification-constraints.txt`, then run
`pip check`. From outside the repository, with PYTHONPATH unset, invoke:

```bash
/path/to/venv/bin/python /path/to/LCATS/experiments/10_gettenberg_qualification/scripts/qualify_narrow_installed.py /tmp/NEW-smoke.json
/path/to/venv/bin/python /path/to/LCATS/experiments/10_gettenberg_qualification/scripts/qualify_narrow_cli.py /tmp/NEW-cli.json
```

Both use authored fixtures, forbid sockets, write only fresh temporary outputs and
have POSIX time bounds. Their source hashes are in the reports; unchanged existing
runners were used. Whole-wheel closure compares every package Python/JSON
member (package name `lcats`) with `git show PRODUCT_REF:lcats/src/PATH`, requiring
exact path-set and byte equality, then checks the installed physical tree and each
loaded origin. `wheel-closure.json` retains the complete SHA256 map and metadata.
The older narrow-transfer runner deliberately assumes only four changed modules
since its historical ledger; it was not weakened to ignore the two main LLM changes.

No live original-wire or full configured-collection yield claim is added. The accepted
1,659-input cohort, 13 exclusions, 67 body effects and historical decoded-cache
boundary remain as documented in GPA-A through GPA-D.
