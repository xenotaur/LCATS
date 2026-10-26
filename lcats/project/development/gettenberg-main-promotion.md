# Gettenberg promotion to main: review guide

Status: **[PR #534](https://github.com/xenotaur/LCATS/pull/534) is open for human
main-promotion review; not delivered to main**.
The human authorized landing PR #530 internally and preparing this promotion.
That instruction does not authorize merging the promotion or publishing a package
or corpus. A–D acceptance is already recorded and need not be requested again.

## Review correction — HTTP 404 continuation (2026-10-26)

Kenny's cold acquisition of ebook 1367 exposed a missing representation on the
configured mirror and collection-wide abortion. The human approved a narrow
replacement-integration correction: structured HTTP status/endpoint diagnostics,
per-item 404 continuation, distinct unavailable counts and incomplete CLI status 2.
No retry, mirror failover, alternative representation, 410 continuation or
editorial behavior is added. This does not recover ebook 1367.

The earlier 1,659-input yield evidence used cached historical decoded sources;
it establishes neither live mirror coverage nor cold acquisition yield. Historical
A–D acceptance and evidence remain unchanged. The new authored HTTP/batch/installed
CLI checks qualify the changed failure path separately; see the
[404 repair evidence](../../../experiments/10_gettenberg_qualification/results/gettenberg-http404-20261026/README.md).
Main review and promotion remain human-gated.

## Candidate and provenance

- Internal [PR #530](https://github.com/xenotaur/LCATS/pull/530) merged into
  `codex/gettenberg-acquisition` at `df05525618d701be0d5a5ea2d2840774f00c1368`.
  Its entire merged tree exactly matches approved head `c6fd5e49410feb02f58e0e5f2a1d60b7d04dcb52`.
  All four checks passed and there were no unresolved review threads at landing.
- Promotion branch: `codex/gettenberg-promotion`, based on that integration merge.
  Recorded main base `22a739d25c5a72359c1f8e37f54f9059876e6798` was merged cleanly at
  `0dbe9606b446be5ce34e52350947fd4911e3c89a` before promotion qualification.
- At that merge every one of 1,763 main-only changed/deleted tree paths was
  preserved exactly. The later test-output fix adds capture to two inherited
  genre-tool test files without changing their production code or assertions.
  The two documents changed on both sides merged cleanly: release preparation
  instructions and the shared backlog. Both contributions were inspected and retained.
- At the original promotion qualification, only two product files differed from
  the internally approved product:
  `llm/backend.py` and `llm/openai_backend.py`, both byte-identical to that main base.
  At that checkpoint all gettenberg/gatherer code, package and CI configuration
  matched the qualified integration. The 404 correction above subsequently changes
  four acquisition/batch modules; its evidence supplements the original packet.
- Preserved broader editorial/extraction work remains on
  `codex/gettenberg-qualification` / [PR #524](https://github.com/xenotaur/LCATS/pull/524).
  This promotion does not merge that branch or install its separated review runtime.

## What this delivers

The internal provider replaces the external gutenbergpy/VCS installation dependency.
It provides a richer queryable SQLite metadata catalog, controlled setup/refresh,
original-source caching and receipts, resource selection/routing, strict decoding,
conservative boilerplate cleanup and inspectable transformation provenance.

`lcats gather` remains a smart, source-aware command: prepare a missing Gutenberg
catalog when needed and approved; reuse ready catalogs and cached originals; support
offline/unattended policies; avoid Gutenberg setup for unrelated selected sources.
Narrow cleanup refusals and selected-resource HTTP 404s are logged separately per
input, leave that input unpublished and allow
subsequent inputs to proceed; an incomplete run reports status 2. Other operational
failures remain distinct. Existing story outputs are reused without overwriting them.

The migration includes active callers, thin research/notebook clients, byte-preserved
archives of upstream-internal notebooks and the separately qualified CI-maintenance
work. No compatibility promise for the old Python API, raw SQL schema or MongoDB is
introduced. No canonical `corpora/` paths change relative to the main review base.

## Read the review in this order

1. [Accepted scope and Q1–Q8 / ten-criterion map](gettenberg-delivery-decision.md),
   [acceptance record](gettenberg-adoption-acceptance.json), and
   [post-adoption backlog](gettenberg-post-adoption-backlog.md). The 13 exclusions,
   55 retained notices, 12 specific body effects and evidence boundary are accepted
   for replacement delivery; they remain open follow-up, not editorial approval.
2. [User migration guide](../../docs/how-to/gettenberg-migration.md),
   [gather guide](../../docs/how-to/gettenberg-gather.md), and
   [architecture](../../docs/explanation/gettenberg-architecture.md). These describe
   first use, cache reuse, refusal reporting and known text limitations.
3. [Provider implementation](../../src/lcats/gettenberg/),
   [gather integration](../../src/lcats/gatherers/),
   [provider tests](../../tests/gettenberg_tests/), and
   [gather tests](../../tests/gatherers_tests/). Relative to the reviewed main base,
   49 product paths and 30 test paths change (including retired legacy adapters/tests).
   Foundation WIs0001–0004 are already delivered on main; this PR completes the remainder.
4. [Caller disposition ledger](gettenberg-migration.md), package/environment dependency
   changes, and [CI maintenance guide](../../docs/how-to/gettenberg-ci-maintenance.md).
   Three workflow changes belong to the previously scoped WI0009; this promotion
   does not modify their behavior anew.
5. [Promotion verification](../../../experiments/10_gettenberg_qualification/results/gettenberg-promotion-20261024/README.md),
   [independent delivery review](../../../experiments/10_gettenberg_qualification/results/gettenberg-delivery-review-20261024/README.md),
   [actual batch yield](../../../experiments/10_gettenberg_qualification/results/gettenberg-refusal-continuation-20261023/README.md), and
   [full catalog qualification](gettenberg-qualification.md). Historical results are
   retained rather than regenerated merely to refresh timestamps.

Most of the large file count is evidence and planning history: before adding this
promotion record, 670 experiment paths and 204 control-plane paths differed from main
(without rename detection). Old experiment runners may require their recorded broader
checkout; their preservation does not make them part of the installed API. Use the
experiment README's supported narrow-candidate entry points. Review the product and
current acceptance map first, then follow evidence links for individual claims.

## Qualification and limits

The original main-synchronized tree passed 2,972 canonical tests, format/lint and LRH validation
(0 errors, 354 warnings from the combined control plane). The previously reviewed
candidate passed 2,956 tests; additional tests arrive unchanged from main. Promotion
wheel and installed smoke evidence is recorded in the linked verification bundle;
final main-target hosted checks must pass at the actual PR head before merging.

The installed wheel is built in empty staging from committed source, preventing stale
separated modules from leaking into packaging. Qualification uses an explicit temporary
version label, not a release-version claim. Near-publication metadata/version checks
remain a release task. The provider source identity match permits carrying its prior
full-snapshot, cleanup, 67-body and actual batch-yield evidence at that checkpoint;
the incorporated main LLM changes received fresh canonical and installed checks.
The subsequent 404 repair passes 2,977 canonical tests, explicit runner checks,
LRH validation and both installed CLI continuation scenarios. Its clean wheel and
installed package match all 165 Python/two JSON files at product94d4331f. The prior
metadata/cleanup/extraction algorithms and historical evidence are unchanged; new
HTTP and batch evidence qualifies the changed acquisition-error seam separately.

Measured normal-batch yield remains 1,646 published/reused, 13 refused and zero
unattempted in the frozen 1,659-input cohort. This does not establish yield for all
5,492 configured IDs. Historical decoded UTF-8 lacks original wire receipts. The
separate 78,937-record metadata snapshot and authored acquisition tests retain their
own evidence boundaries. Retained notices/paratext remain documented limitations.

## Human decision and post-main closeout

The requested next human decision is **whether to promote this reviewed candidate
to main**. A–D and the required durable backlog are already approved and recorded.
Main approval authorizes only the reviewed promotion and its separately previewed
closeout; it does not authorize canonical corpus regeneration or package publication.

After an approved main merge actually lands:

1. Verify the delivered head, ancestry, checks and complete dependency/acceptance map.
   Record the actual main merge SHA; do not infer delivery from PR #530's internal merge.
2. Reconcile WI-GETTENBERG-0005 through WI-GETTENBERG-0010 and their primary/side
   execution records using native LRH closeout. Resolve/land only verified delivered
   scope; retain distinct failed/superseded history and truthful session pointers.
   WIs0001–0004 and their existing landed records are already on main and stay intact.
3. Reconcile WS-GETTENBERG and the redesign proposal against all ten completion
   criteria, retaining GPA-A through GPA-D as open follow-up. Workstream completion
   does not silently implement or close those backlog entries.
4. Verify [WI-RELEASE-0037](../work_items/proposed/WI-RELEASE-0037.md) against actual
   main delivery and its own wheel/sdist metadata requirements. It is not resolved by
   this promotion-preparation run. [WI-RELEASE-0039](../work_items/proposed/WI-RELEASE-0039.md)
   remains a separate check immediately before actual PyPI publication.
5. Preserve PR #524 and coordinate its gather/editorial work with Kenny separately.
   Record any later reconciliation as scoped work, not an automatic merge of that PR.

No new native terminal statuses are set while this promotion is awaiting review.
