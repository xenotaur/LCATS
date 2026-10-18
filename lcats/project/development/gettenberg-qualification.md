# Gettenberg replacement qualification and delivery plan

WI-GETTENBERG-0010; bounded run 2026-10-18. **In progress; not yet an acceptance
or main-delivery claim.** Integration base ed20e9c297bf5e50e1911b84722e53f5db3edee3.
The [charter](gettenberg-pilot-charter.md) governs internal acceptance; the human
retains main promotion. Native WI0005–0010 records remain nonterminal until then.

## Evidence contract

The [experiment](../../../experiments/10_gettenberg_qualification/README.md)
retains executable measurement code and results. The control plane links to it;
it contains no executable code. Each measurement identifies immutable inputs and
product source hashes. The final source ledger binds earlier unaffected-component
measurements to the reviewed candidate; a Git parent alone is not that proof.
Historical files are never rewritten to claim that new code produced old results.

Use the cached 125,955,051-byte archive SHA256
`358f177c30818027ad93b3478da2248d7996999475d83e59288ee74423050b28`.
Original retrieval time/URL remain unknown. No Gutenberg requests are needed.
The original cache and canonical corpus remain unchanged. Synthetic fixtures,
retained decoded text, original RDF and live endpoint observations are separate
classes of evidence; none substitutes for another.

## Governing design completion mapping

| Criterion | Implementation and acceptance evidence | Delivery boundary |
|---|---|---|
| 1. No active upstream dependency | pyproject/environment removal; [migration inventory](gettenberg-migration.md); fresh wheel source equality, installed import/metadata and CLI smoke | Historical experiment runners/notebooks intentionally retain legacy references; active imports/requirements do not |
| 2. Feature/evidence matrix | Capability mapping below; full snapshot fidelity/vocabulary accounting; RDF and catalog semantic regressions | No legacy API/SQL/Mongo compatibility, as approved |
| 3. First-use/cached/offline/unattended gathering | preparation/default_sources/live_gather tests; executed [gather guide](../../docs/how-to/gettenberg-gather.md), [tutorial](../../docs/tutorials/gettenberg-first-catalog.md) | Fixture transport validates behavior; published defaults have separate dated endpoint evidence |
| 4. Unrelated sources avoid catalog | preparation and live_gather source-isolation tests; executed fixed-URL collection example | Arbitrary future source adapters remain future scope |
| 5. Failed refresh preserves valid catalog | lifecycle/catalog_receipts/refresh regression suites; full local setup/reuse; executed recovery tutorial | No deliberate refresh of a production cache |
| 6. Inspectable provenance | Every snapshot record's raw bytes and reconstructed public fields/diagnostics round-trip; resource receipts/decode/cleanup tests; story source inspection | Old decoded text lacks wire receipts and is never relabeled as original bytes |
| 7. Caller dispositions complete | [Migration inventory](gettenberg-migration.md), notebook/research-client/import guard tests, archived notebook hashes | Historical material preserved; no sibling consumers known |
| 8. Corpus/resource differences reviewed | Full old/new builds, cached-corpus before/after comparison and dispositions below | No canonical corpus regeneration/promotion; no universal historical-format claim |
| 9. Required checks pass | Canonical test/format/lint/LRH, explicit experiment checks, fresh wheel, cold/hosted reviews and final-head CI | Pending until exact candidate evidence is recorded |
| 10. Docs/control plane accurate | Executed four Diataxis quadrants; this map, runlog, primary/review records and closeout plan | Main promotion/native closeout still pending; never marked accepted prematurely |

## Capability mapping

The [baseline matrix](gettenberg-baseline.md#featureevidence-matrix-and-ownership)
is a historical plan. This is its current acceptance index, subject to final
checks and review:

| Baseline capability | Current API and evidence |
|---|---|
| Cache/build/query controls | CatalogManager setup/status/rebuild/update/activate/cleanup; lifecycle and preparation suites, full snapshot build |
| Multiple titles and contributor aliases | ParsedRecord/Ebook ordered associations; real pg10000/pg10040 fixtures and full exact record round trips |
| Publisher/rights/type/issued/downloads | Typed nullable fields; RDF shape/value tests, catalog filtering and full round trips |
| Languages/shelves/subjects | Ordered multivalues and subject schemes; catalog filter matrix and snapshot counts |
| Contributor roles/life dates | All observed relator roles, linked identities and values; RDF tests, retained source and full accounting |
| Distinct resource identities/formats | Ordered Resource records, URI-preserving selection/routing, format/encoding/container tests |
| Query/filter dimensions | Catalog.Filters and keyset pagination; catalog_test; repeated full English queries |
| Acquisition/cache | ResourceStore, explicit NetworkPolicy, original bytes/receipts, resource/refresh suites |
| Boilerplate cleanup | Immutable spans and diagnostics, versioned policy, authored adversarial tests and cached real-text comparison |
| Descriptions/MARC/provenance | additional_metadata, retained original RDF, full element/attribute inventory and diagnostic accounting |
| Lifecycle/recovery | Single writer, pinned readers, failed publication/count-change approval, offline rebuild tests and tutorial |
| Smart source-aware setup | CatalogPreparation plus CLI policy; preparation/default-source/live-gather tests and executable examples |
| Caller/corpus/package migration | Inventory, five authored end-to-end preservation fixtures, cached real-text comparison, fresh installed wheel |
| CI maintenance | [Maintenance guide](../../docs/how-to/gettenberg-ci-maintenance.md),18 helper tests and PR523 accepted evidence; no CI edits in this run |
| Efficiency/docs | Measured builds/query/RSS/disk results; executable tutorial/how-to/reference/explanation tests |

## Measured resources

Full lifecycle setup passed 78,937 records, 2,018,879 resources, 109,170 contributions
and 223 diagnostics. Setup 440.847s, 89,030,656-byte process peak RSS, cached reuse
0.0024s, zero network bytes. This meets the existing 600s/512MiB targets.

The genuine historical gutenbergpy 0.3.6 unpack+parse+SQLite build on the same
archive took 191.583s and 804,323,328-byte process peak RSS. It produced exactly
the historical database hash `188b422247c48807459f3aedac6dad462244e91a2885543e3051555c0e0a39f5`.
That reproduces the existing database from this archive; it does not recover an
unknown original retrieval date. The old build retains 2,547,965,086 logical bytes
when archive and extracted RDF are kept; database alone 342,450,176 bytes.

These single local observations include concurrent light qualification work;
they are not a controlled benchmark or proof of general speedup. The new build
is slower here and uses much less peak memory while retaining a richer normalized
schema and source evidence. Report database/retained bytes separately from peak
temporary usage: neither final directory size nor RSS measures peak disk.
Repeated query results and final retained sizes appear below.

## Corpus qualification and repair

The local mass_quantities corpus has 1,659 stories; every ID has a legacy gzip
text entry. Those cache entries contain already decoded/re-encoded UTF-8. They
cannot qualify original transport bytes or encoding detection. Compare cleanup
and extraction on the exact same decoded inputs and current catalog metadata;
compare retained corpus output separately. Earlier authored live-gather fixtures
cover the original-byte store through publication without that provenance gap.

Initial census: 1,605 accepted envelopes and 54 conservative refusals. Inspection
found 31 comma-form Gutenberg banners, 17 exact END: FULL LICENSE separators,
five wrapped book marker pairs, and one mismatched title pair. Authored tests
reproduced the first two issues. Policy `gutenberg-boundaries-v2` adds those exact
historical forms while preserving unique matched book delimiters, prefix/suffix
corroboration and refusal of damaged/ambiguous markers. No old marker list or
stripping implementation was copied. Wrapped/mismatched book delimiters remain
explicit refusals under the approved conservative contract. The full comparison below and independent review establish that this criterion
is still blocked by downstream narrative loss.

## Promotion and native closeout plan

1. Finish WI0010's first three qualification gates and independent review; only
   then may the coordinator integrate its PR into codex/gettenberg-acquisition.
   Missing inputs, unexplained output differences or failed checks block that
   integration rather than weakening this work item's acceptance.
2. Prepare one promotion PR to main from the qualified integration head. Include
   this matrix, resource tradeoffs, corpus refusals/differences, final diff size,
   review/CI evidence and operational migration instructions. Human approval
   remains required before main merge. If drift requires code repair, revalidate
   the affected evidence at the new head.
3. After the human-approved main merge, verify ancestry and final checks, then
   use native LRH closeout operations to reconcile WI0005–0010 and every linked
   child execution/review record. WI0001–0004 were already delivered/resolved via
   the [offline milestone](gettenberg-offline-milestone.md); do not reopen or
   manufacture a second delivery. Preserve the internal acceptance history.
4. Evaluate WI-RELEASE-0037 against its own main-delivery criteria and link this
   evidence. Close WS-GETTENBERG/adopt the redesign only when all ten criteria and
   native records are accurate. Keep WS-RELEASE and WI-RELEASE-0039 open for their
   separate release/near-publication obligations. No PyPI publication is included.
5. Summarize LRH lessons from the runlog: source-bound evidence, honest gap/refusal
   states, expected CI inventory, bounded assignments, measured resource budgets,
   exact approval scope and resumable checkpoints. Observations from this one
   pilot do not establish causal speed or cost improvements.

## Qualification blocker and current checkpoint

**Do not merge this qualification PR into the integration branch.** The full
pre-repair corpus comparison found 892 changed normalized bodies among 1,605
compared inputs. 884 changes are suffix additions, but 8 affect earlier body
positions; two severe truncations are documented in the
[repair scope](gettenberg-corpus-repair-plan.md). Canonical tests passing does not
satisfy the real-corpus gate. The v2 banner/license-marker repair is deliberately
narrow and cannot resolve this broader composition problem.

The first WI0010 acceptance criterion is therefore **not satisfied**. The
capability table above indexes available evidence; it does not certify every row.
Tutorial/reference/CLI example execution, catalog/resource measurements and fresh
wheel independence remain useful independently qualified observations. Independent
review and hosted checks qualify the safety of this checkpoint, not completion of
WI0010 or permission to integrate it. The final corpus disposition remains pending
a focused repair and narrative-preservation review. See the runlog for exact
measurement, validation and review checkpoints.

## Measured checkpoint

[Results and hashes](../../../experiments/10_gettenberg_qualification/results/gettenberg-qualification-20261018/manifest.json)
retain the raw reports; full corpus JSON is compressed verbatim, with readable
[review index](../../../experiments/10_gettenberg_qualification/results/gettenberg-qualification-20261018/corpus-review-index.json).
[Source ledger](../../../experiments/10_gettenberg_qualification/results/gettenberg-qualification-20261018/source-ledger.json)
identifies measured product/runner bytes. The [runner repair addendum](../../../experiments/10_gettenberg_qualification/results/gettenberg-qualification-20261018/runner-repair-addendum.json)
records the later invalid-input guard change; all product bytes are unchanged. Lifecycle measurements predate the pure
cleanup change; every catalog implementation file is unchanged. The later
snapshot audit uses the current sources.

- Full snapshot: 78,937 public record reconstructions, all original bytes and
  diagnostics identical; 547.627s, 130,252,800-byte RSS. No unmodeled predicates or
  attributes; 223 diagnostics are URI whitespace normalization (222 file, 1 webpage).
  This public API reparses retained RDF; it is not by itself an audit of normalized
  query tables. A separate 40-field index multiplicity audit passes. Semantic
  fixtures complement both; no claim of independent parser implementation is made.
- New English query returns 62,726 IDs versus legacy 62,689. The 37 additions have
  English as a later language value that the old first-language schema omitted;
  no old IDs disappear. Three new paginated queries: 0.0475/0.0400/0.0412s. These
  differ in API/query shape from old SQL timings and are observations, not a
  controlled benchmark. Per-ID language evidence accompanies the index audit.
- New retained logical bytes: 2,303,344,639, including 2,177,388,544-byte database and
 125,955,051-byte archive. This is below 4 GiB retained output, but peak temporary
  disk usage was not sampled and is **not claimed**. Combined isolated experiment
  occupied about 5.2 GiB when checked, below the 15 GiB run bound.
- After the narrow v2 repair: 1,646 compared, 13 refused, 902 changed bodies, 904
  differences from retained corpus. 696 appended end notices, 122 transcriber notes,
 57 byline/separator starts, 19 other suffixes, 8 earlier-body changes, 742 identical
  bodies and 2 retained-corpus-only differences. All 1,659 cache/corpus hashes match
  before/after. The 13 remaining refusals are explicitly listed; some newly exposed
  header/marker failures follow the first corrected failure, so 54−48 is not the
  actual refusal result. No blanket acceptance is inferred from these categories.

The corpus gate remains blocked. This checkpoint can be reviewed and preserved
without being integrated. The repair plan and subsequent human decision determine
how to proceed; the current PR never claims whole-WI acceptance.

## Independent review and local validation

Cold review found no new defects in this unaccepted checkpoint, independently
reproduced all eight earlier-body differences, and verified the report/source/input
hashes, query deltas and wheel contents. The coordinator directly replayed both
severe truncations. Canonical validation passed 2,944 tests; package and all 12
experiment runners passed formatting/lint. See the [validation evidence](evidence/gettenberg-qualification-20261018/validation.json).
Hosted review and exact-head CI are recorded separately in the runlog; neither a
green test suite nor clean checkpoint review overrides the corpus acceptance gate.
