# Candidate review workflow — 2026-10-20

WI-GETTENBERG-0010 continuation under the approved pilot coordinator adapter.
The human requested the next run after readiness qualification. This scope makes
individual dispositions inspectable and repeatable; it does not accept the corpus.

## Scope and decisions

- Add a local `lcats gather-review` workflow and tested library for saved immutable
  candidates: list inventory, bounded exact-text preview, record explicit approve,
  exclude or defer dispositions, and export selected approvals in the existing
  `--review-decisions` format. No catalog, network or publication side effects.
- Validate candidate filename/content identity, body and assessment hashes, full
  source/derivation context, schema and spans. Reject duplicate JSON keys and malformed
  records. Artifact consistency does not establish correspondence to today's catalog;
  gathering independently revalidates against its current source as before.
- Dispositions are immutable, source-bound records outside collection roots. Approval
  requires an explicit span, reviewer and rationale. Exclude/defer record reviewer
  intent only and cannot be exported as approvals. They do not silently alter the
  collection definition or suppress a subsequent gather. Attribution is not an
  authenticated human signature. No automatic decisions from finding patterns.
- Inventory counts exact candidate generations separately. Multiple dispositions
  remain visible; conflicting outcomes/selections have an explicit conflict state.
  No last-writer-wins approval by ID, timestamp, filename sorting or majority vote.
  Export consumes explicitly named approval records, requires their exact saved
  candidates, rejects duplicate ebook IDs and never overwrites unequal output.
- Use bounded JSON input, file counts/aggregate bytes and text windows. Preview
  exposes exact Unicode character offsets, total length and omitted-text indicator.
  Never mistake a window for the whole narrative. Preserve earlier evidence.
- Reuse readiness.ReviewDecision, review_store and atomic publication. Existing
  analysis/corpus/review models bind corpus repair operations, not acquired source
  candidates; adapting them would conflate distinct identity/acceptance contracts.
  No new dependency, classifier, destructive extraction rule or generic UI framework.

## Qualification

Unit and CLI behavior tests cover corruption, stale identities, bounded reads,
conflicts, exclusion/defer, exact Unicode spans, no-overwrite and protected roots.
Exercise documented commands and the existing gather path with exported approvals.
Use the immutable cached corpus to build a temporary queue/inventory; archive only
compact source-bound reports and reviewed annotations, not copies of candidate bodies.
Verify previously reviewed eight selections remain identical and can be represented
through this workflow; exercise explicit source-grounded exclusion/defer separately.
These are publication dispositions, not automatic explanations of the 1,642 historical
body differences. Full corpus acceptance remains open.

Canonical checks, explicit experiment checks, installed package smoke and one cold
independent review are required. Record all findings and repair verification in the
runlog. No integration, corpus promotion, policy/consent changes or terminal closeout.


## Qualified tooling checkpoint

Completed in d3bdff07 under the renewed 2026-10-20 grant.
[Usage](../../docs/how-to/gettenberg-review.md), [reference](../../docs/reference/gettenberg-review.md),
and [archived evidence](../../../experiments/10_gettenberg_qualification/results/gettenberg-review-workflow-20261020/README.md)
cover the workflow and limits. Independent review is clear, with 3,027 canonical
tests and full cached-source reconstruction. This completes tooling qualification
only; corpus acceptance and integration remain open.


## Approved batch-method extension — 2026-10-20

See [batch review contract](gettenberg-batch-review-contract.md). The human approved
qualified narrow rules with per-input evidence. Repeated warning patterns alone
still cannot accept a group; exceptions stay unresolved. Historical text above
describes the initial individual-review method.
