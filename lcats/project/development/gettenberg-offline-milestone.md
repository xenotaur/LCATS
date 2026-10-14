# Human milestone: gettenberg offline foundation

Review PR: [#508](https://github.com/xenotaur/LCATS/pull/508), targeting main.

Status amendment: the human approved the repository-layout repair plan and
instructed it to proceed, including stabilization and landing. Main merge and
partial closeout follow passing current-head gates. Publication and further
implementation runs are outside that approval.

## Decision requested

Approve promotion of the qualified offline foundation, WI-GETTENBERG-0001 through
WI-GETTENBERG-0004, to main after the promotion PR's current-head checks and
review are clear. The original milestone source was integration checkpoint
`6970d504cead927fa566eecd5187bb2f51eab174`, with the review repairs described below now included on
`codex/gettenberg-offline-milestone`. Main base is
`5cfd2d71caf6f3eedfdfc0b830b5c5ff1a74ba3b`, verified as an ancestor.

The human requested this milestone presentation after run 3. This is a separate
presentation/validation task; it does not renew the completed bounded run.

## Why promote at this point

The [charter](gettenberg-pilot-charter.md) permits an earlier milestone for review
size, integration risk, or a design issue. The offline parser, database and
recoverable lifecycle now form a coherent, independently reviewed subsystem.
Before this packet, code/tests/docs alone spanned 26 files and 8,024 added lines,
including real RDF fixtures; planning, evidence and execution records add more.
Promoting this boundary bounds the next review before network acquisition and
caller migration introduce different risks. No fundamental design change is
being proposed.

## Delivered scope and evidence

| Item | Delivered capability | Internal review and acceptance evidence |
|---|---|---|
| WI-0001 | Baseline measurements, caller/notebook/experimental/Kmo inventory and dispositions, feature matrix, fixture provenance, release-plan reconciliation and scoped downstream work | [PR #504](https://github.com/xenotaur/LCATS/pull/504), [baseline](gettenberg-baseline.md), [run 1 integration](evidence/gettenberg-pilot-20261014/integration-evidence.json) |
| WI-0002 | Typed metadata, bounded RDF parsing, original source/provenance and diagnostics, bounded exports | [PR #505](https://github.com/xenotaur/LCATS/pull/505), [record reference](../../docs/reference/gettenberg-records.md), [parser qualification](../../../experiments/10_gettenberg_qualification/results/gettenberg-pilot-20261014/parser-full-source.json) |
| WI-0003 | Streaming local-archive ingestion, SQLite storage, typed queries, predicates and pagination | [PR #506](https://github.com/xenotaur/LCATS/pull/506), [catalog reference](../../docs/reference/gettenberg-catalog.md), [run 2 integration](evidence/gettenberg-pilot-run2-20261014/integration.json) |
| WI-0004 | Offline setup/rebuild, verified candidates, count-change approval, atomic activation, writer coordination, pinned readers and recovery/cleanup | [PR #507](https://github.com/xenotaur/LCATS/pull/507), [how-to](../../docs/how-to/gettenberg-catalog.md), [acceptance map](evidence/gettenberg-pilot-run3-20261014/qualification-map.json), [run 3 integration](evidence/gettenberg-pilot-run3-20261014/integration.json) |

Read the how-to first for the usable local workflow. Then review the record and
catalog references, lifecycle error/retention contracts, and the linked evidence.
The package adds an explicit `lxml>=5.2.2` dependency for its parser. Existing
Gutenberg callers and `lcats gather` still use the previous path; their migration
is a later tranche. No existing corpus is transformed by this promotion.

## Qualification and its limits

The original integration source passed **2,668 canonical tests**, including **190 gettenberg
tests**, formatting, lint, readiness and LRH validation (zero errors, 351 existing
warnings). Each internal PR passed its exact-head CI and independent review.
The final integration checkpoint's [branch test](https://github.com/xenotaur/LCATS/actions/runs/38632264115)
also passed. These are historical source-qualified results; the new main-target
PR must pass its own current-head checks and review before landing.

One cached full-source setup imported **78,937 ebooks**, **2,018,879 resources**
and **223 diagnostics** in **453 seconds**, peaking at **76 MiB RAM**, without
network requests. Setup reuse took about **4 ms**. These measurements belong to
`8bccd4c4`, as recorded in [full-source evidence](../../../experiments/10_gettenberg_qualification/results/gettenberg-pilot-run3-20261014/full-source.json).
Later filesystem-boundary repairs were independently tested; final-source full
hash/integrity/accounting verification and activation passed in about 22 seconds.
Parser/ingestion/store/query source remained unchanged. The
[qualification map](evidence/gettenberg-pilot-run3-20261014/qualification-map.json)
preserves this distinction; there is no claim of final-head fresh-import timing.

Important operating limits for approval:

- Published generations and source archives are conservatively retained. There
  is no whole-cache quota or automatic garbage collection of those objects.
- Use a local filesystem with reliable SQLite locking, hard links and atomic
  replacement. POSIX durability requires directory opens/fsync through the cache's
  containing hierarchy; unsupported operations fail explicitly. Windows provides
  process-interruption recovery, without a power-loss durability guarantee.
- Fault-injection and real process-interruption tests cover publication/recovery
  boundaries. Physical power-loss durability was not experimentally tested.
- Invalid active metadata fails closed. These APIs are a cooperative local cache,
  not protection against a malicious process able to modify its files.
- Full-source qualification reused one identified cached snapshot. It is not a
  fresh upstream download, release qualification or proof of every future format.

## Remaining work

WI-0005 through WI-0010 cover bounded network acquisition, original-byte story
caching/decoding, conservative boilerplate cleanup, source-aware smart gather and
catalog commands, caller/notebook dispositions, `gutenbergpy` dependency removal,
CI cache migration, and complete replacement/corpus/release qualification.
The PyPI release blocker remains open. The redesign and workstream are only
partially implemented. Another bounded implementation run needs a separate grant.

## Main gate and closeout plan

Before landing, verify the exact promotion head and intended main base, all
required CI checks, and no unresolved P0-P2 findings. Human approval is required
by the charter's Roles and authority and Branch and lifecycle protocol sections.
If review exposes a material implementation issue, record it and scope the next
repair instead of treating this presentation as an unlimited implementation run.

After explicit approval and an actual verified main merge, reconcile the four
WIs and their 15 primary/side execution records against the main merge SHA.
The [closeout map](evidence/gettenberg-offline-milestone-20261014/closeout-map.json)
lists every record, original internal PR and integration commit. Preserve those
internal PR links and append main-promotion evidence; do not silently replace
historical review attribution. The promotion execution record links this main PR.
Only verified delivered WIs may become resolved, and only then may corresponding
records become landed. Workstream, redesign and downstream release gates remain
open. No native lifecycle status is changed by preparing this packet.

If deferred, the qualified checkpoint and this fixed review branch remain
available. A later source change requires fresh affected evidence and a new head
review; approval of this packet should not silently cover later feature work.


## Human review repairs

The approved repository convention is now documented in STYLE.md and root/package
agent guidance. Qualification runners and archival measurements reside in
[experiment 10](../../../experiments/10_gettenberg_qualification/README.md).
The relocation map preserves original identities; historical results are not
relabelled as runs of revised code. Current runner tests cover import-safe CLIs,
relative paths, wrong-snapshot failure under normal/optimized Python and tiny
fixture measurements. The lifecycle rejects non-UTF-8 input paths before bulk
copy/build; existing strict JSON encoding is unchanged. The how-to uses fenced
Python-console blocks, verified through GitHub rendering and doctest execution.

Current review repairs pass **2,676 canonical tests**, including **198 gettenberg
tests**, canonical and explicit experiment formatting/lint, and LRH validation
(0 errors, 351 existing warnings). Nine historical result hashes and 24 current
local links were verified. Current-head CI and independent review remain landing
gates; historical full-source measurements have not been rerun or relabelled.
