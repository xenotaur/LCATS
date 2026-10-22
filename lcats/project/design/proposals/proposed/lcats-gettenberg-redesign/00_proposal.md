---
id: "PROP-LCATS-GETTENBERG-REDESIGN"
type: "design_proposal"
title: "LCATS-owned Gutenberg catalog and acquisition library"
status: "proposed"
created_on: "2026-10-13"
updated_on: "2026-10-13"
implementation_status: "not_started"
implemented_by: []
evidence: []
supersedes: []
superseded_by: null
related_design:
  - "project/design/proposals/proposed/lcats-pypi-release-readiness/00_proposal.md"
  - "project/design/proposals/adopted/lcats-story-bucket-layout/00_proposal.md"
  - "project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md"
  - "project/design/proposals/proposed/lcats-run-log/00_proposal.md"
  - "project/design/proposals/adopted/genre-evidence-sidecars/00_proposal.md"
---

## Summary

Replace LCATS's external gutenbergpy dependency with a redesigned internal
lcats.gettenberg library providing catalog ingestion, rich metadata,
predictable querying, cached resource acquisition, and conservative
Gutenberg boilerplate removal.

Preserve lcats gather as a convenient command that prepares the resources
its selected collections require, while exposing explicit library and CLI
operations for preparation, inspection, refresh, and offline use. Deliver
the replacement through an LRH workstream with measurable acceptance
criteria, documented migration dispositions, and a development-process log.

## Background / Motivation

LCATS's package metadata and development environment pin an unpublished
Git version of gutenbergpy. Its current wrapper delegates catalog building,
text retrieval, and header stripping to that dependency while depending
directly on its SQLite schema.

The user has chosen an internally owned redesign. There is no hard release
deadline, no known external consumer, and no requirement to preserve the
old Python API, SQL schema, or MongoDB backend. Waiting for upstream and
interim vendoring are outside the selected implementation path.

Source inspection at LCATS commit e0a838fb identified these requirements:

- Package and environment declarations both require migration:
  lcats/pyproject.toml:28; lcats/environment.yml:263.
- Missing metadata can trigger an implicit catalog rebuild:
  lcats/src/lcats/gettenberg/cache.py:119.
- The skip-cache path can still download ebook text:
  lcats/src/lcats/gettenberg/api.py:177.
- The wrapper expects mapping query results, while the pinned dependency
  returns integer IDs. Existing wrapper tests inject mapping results:
  lcats/src/lcats/gettenberg/api.py:113;
  lcats/tests/gettenberg_tests/api_test.py:106;
  upstream sqlitecache.py:152 [S1].
- The maintenance workflow invokes a mocked construction test and
  suppresses failure:
  .github/workflows/cache_maintenance.yml:71;
  lcats/tests/gettenberg_tests/cache_test.py:121.
- Gatherers use metadata and cleaned text to select and name stories:
  lcats/src/lcats/gatherers/parser.py:1376.
- An experiment reads the SQLite schema without importing gutenbergpy:
  experiments/05_metadata_genre_prefilter/run_prefilter.py:327.

These findings come from static inspection, not runtime reproduction.
No full-catalog performance baseline has yet been measured.

Gutenberg recommends machine-readable catalog feeds for database builders.
Its metadata describes Gutenberg ebooks, which may contain multiple LCATS
stories. Gutenberg release dates are not original print-publication dates
[S2]. The replacement must preserve these distinctions.

## Prior Art Check

### Duplication search

- In-repo: Existing gettenberg is the replacement target. gatherers already
  supplies acquisition and extraction facilities; utils.run_log and
  utils.checkpoint supply reusable operational infrastructure. No separate
  internal replacement proposal was found.
- Sibling repositories: The known xenotaur/gutenbergpy fork contains the
  current dependency. The user identified no additional consumers or
  reusable sibling implementations.
- External libraries: gutenbergpy provides the baseline capabilities.
  Gutendex provides a useful metadata/API reference but adds a web-service
  architecture [S3]. c-w/Gutenberg is archived [S4].
- Recommendation: Proceed with the authorized internal redesign, reusing
  suitable LCATS components and avoiding duplicate extraction utilities.

### Demand search

- Work items: WI-RELEASE-0037 covers the dependency blocker;
  WI-RELEASE-0039 covers verification immediately before publication.
- Proposals: PROP-LCATS-PYPI-RELEASE-READINESS governs the broader release
  work. This proposal supplies the replacement architecture.
- Workstreams: WS-RELEASE remains the release coordination workstream.
- Backlog: The upstream-release follow-up at
  lcats/project/design/backlog.md:868 overlaps the earlier wait/vendor/fork
  decision.
- Recommendation: Link and reconcile these artifacts during planning.
  Do not close release gates merely because the design is approved.

## Design Decisions

### Decision 1: Own the implementation within LCATS

Options considered: wait for upstream, publish a maintained fork, vendor
the existing implementation, adopt another service/library, or redesign
gettenberg.

Chosen: redesign lcats.gettenberg within the LCATS distribution. This
provides control over release timing, data fidelity, API quality, and
operational behavior without maintaining a separate package.

All active imports and installation requirements for gutenbergpy must be
removed. Historical records may retain references.

General-purpose dependencies remain permissible when justified and
explicitly declared. Retained third-party code, fixtures, or marker lists
must have verified provenance and appropriate attribution.

### Decision 2: Separate catalog, acquisition, and story extraction

Options considered: continue the combined wrapper or separate the
responsibilities behind explicit interfaces.

Chosen responsibilities:

| Component | Responsibility |
|---|---|
| gettenberg models | Typed metadata, resource descriptions, results, errors |
| gettenberg catalog | Local queries, batch retrieval, snapshot inspection |
| gettenberg ingestion | Archive acquisition, RDF parsing, catalog construction |
| gettenberg resources | Gutenberg resource selection, retrieval, caching, decoding |
| gettenberg cleanup | Conservative boilerplate detection and removal |
| gatherers | Collection selection, story extraction, normalization, bucket output |
| CLI orchestration | Planning, consent, progress, operational policy, exit status |

Module names may be refined during implementation; these ownership
boundaries govern the design.

Imports and ordinary local queries must not download data, create caches,
or prompt. Resource acquisition is an explicit operation whose network
policy is supplied by the caller.

Gutenberg functionality must not be initialized merely because a user
runs an unrelated LCATS command.

### Decision 3: Use bulk RDF and a versioned SQLite catalog

Options considered: CSV-only ingestion, individual-record retrieval,
a general RDF database, or bulk RDF mapped into SQLite.

Chosen: ingest bulk RDF into a normalized SQLite catalog, processing
archive members incrementally and committing bounded batches.

Read individual members without unpacking the entire archive tree.
Bound parser and archive resource use; disable external XML resolution.
Avoid retaining the full catalog in Python memory.

The importer must account for every archive record: imported, explicitly
recognized as a deletion/non-book record, or rejected with a diagnostic.
Unexpected malformed records prevent normal activation of the candidate
catalog. An incomplete diagnostic build must not masquerade as a complete
catalog.

CSV is not an initial alternate backend. Individual RDF acquisition may
support targeted operations where appropriate, but must not become the
full-catalog crawling strategy.

Retain the source archive and its hash so catalogs can be rebuilt without
another download. Support construction from an explicitly supplied local
archive.

### Decision 4: Preserve richer metadata and its scope

Options considered: reproduce the old schema, store only unstructured
records, or normalize useful fields while retaining source evidence.

Chosen: normalized records with source provenance and retained RDF
evidence.

The field inventory must cover:

- Gutenberg identifiers, primary and alternative titles.
- Contributors, roles, source identities, names, aliases, and life dates
  where supplied.
- Multiple languages, shelves, subjects, and classification schemes.
- Resource/media types, publishers, rights statements, and Gutenberg
  release dates.
- Available file URLs, media types, encodings, sizes, and modification
  information where supplied.
- Download counts, descriptions, summaries, and other useful fields
  present in the source vocabulary.

Each observed predicate receives a documented disposition: modeled and
queryable, preserved in source evidence, or intentionally excluded with
rationale. Unknown predicates produce inspectable diagnostics rather than
silent evidence loss.

Missing values remain absent or null; fabricated dates and sentinel
metadata are not public API values.

Contributor aliases remain associated with contributor identities.
Multiple files with the same media type remain distinct resources.

Metadata derived from headers is labeled separately from catalog
metadata. Volume subjects and titles must not silently become confirmed
story-level classifications or titles. LCATS bucket identity remains
independent of Gutenberg ebook identity.

### Decision 5: Provide a predictable Python API

Options considered: preserve raw SQL-shaped results or introduce a typed,
documented public API.

Chosen: context-managed catalog access, typed records, JSON serialization,
and explicit operations for:

- Get one ebook by Gutenberg ID.
- Retrieve a batch while distinguishing missing IDs.
- Iterate matching IDs or records with bounded pagination.
- Filter by the supported metadata dimensions.
- Inspect contributors, resources, provenance, and catalog status.
- Select, retrieve, decode, and clean supported textual resources.

Filters combine with AND across dimensions and OR within a dimension,
unless an explicitly named operation specifies otherwise. Exact matching
and text search are separate operations. Ordering is deterministic, with
Gutenberg ID as the default tie-breaker.

Invalid fields, malformed IDs, missing catalogs, incompatible schemas,
unavailable resources, and network restrictions have distinct documented
errors. Missing metadata must not be confused with an operational failure.

Callers do not depend on SQLite tables or undocumented row shapes.
All public nontrivial functions receive type annotations and Google-style
docstrings following LCATS conventions.

### Decision 6: Make catalog publication recoverable

Options considered: rebuild the live database in place or construct a
separate candidate and activate it after validation.

Chosen: immutable catalog generations with a manifest and an atomically
updated active-generation reference.

A generation records the archive hash, retrieval information, schema and
parser versions, record counts, diagnostics, and logical snapshot identity.
A query session remains pinned to its opened generation.

Only one writer may build or activate a catalog in a cache root at a time.
Readers may continue using the previous valid generation. Interrupted
downloads and builds leave the active generation intact.

Validate database integrity, relationships, and import accounting before
activation. Report unexpected count changes for inspection.

Setup, local rebuild, network refresh, and explicit cleanup are different
operations. Setup reuses a valid catalog; refresh does not happen merely
because a catalog is old. Network refresh uses conditional requests when
supported.

Existing archive and text caches are preserved during migration.
Legacy decoded caches are not relabeled as original download bytes.
No provenance is invented for legacy artifacts.

Honor LCATS_CACHE_DIR and expose the resolved path through status output.
Record what cache cleanup removes and what source artifacts must be
retained elsewhere for long-term reproduction.

### Decision 7: Keep gather convenient and source-aware

Options considered: mandatory global setup, invisible automatic setup,
or collection-aware planning with explicit approval of missing setup.

Chosen: lcats gather plans requirements for the selected collections and
prepares them as part of the same invocation.

| Mode or condition | Behavior |
|---|---|
| Resources already available | Reuse them and perform remaining work |
| Required catalog missing, interactive session | Explain preparation and request approval |
| --yes | Approve required preparation for the selected operation |
| Missing setup in unattended mode without approval | Fail promptly with an actionable message |
| --offline | Prohibit all network access, including refresh checks |
| --dry-run | Inspect local state only; create no files |
| Catalog not required by selected work | Do not initialize it |

Gathering authorizes retrieval of missing sources in the selected
collection. Catalog preparation is the additional first-use decision.
No per-story approval loop is introduced.

Approval does not imply catalog refresh, redownload, or replacement of
existing story outputs. Those operations require distinct controls.

If catalog-dependent selection is unresolved, the initial plan says so.
After setup, report the resolved selection. Do not invent a precise count
or download estimate before the required metadata exists.

Expose standalone catalog setup, status, refresh, and local rebuild
commands using the same library operations.

Collection requirements distinguish source acquisition from metadata
discovery or enrichment. Fixed URLs and local inputs need no full
Gutenberg catalog unless their selected workflow explicitly requires one.
Use a small explicit requirement contract; a general plugin marketplace
or arbitrary executable configuration system is unnecessary.

### Decision 8: Preserve sources and make transformations inspectable

Options considered: cache only decoded text or retain source bytes with
separate derived representations.

Chosen: preserve newly acquired source bytes, source identity, hash, and
retrieval metadata. Record decoding and cleanup versions separately.

Prefer catalog-described resources and documented Gutenberg access
routes or configured mirrors. Apply bounded timeouts and retries,
respect Retry-After, and coordinate request pacing [S5].

Avoid speculative cascades across URL patterns after throttling or access
denial. Publish cache entries atomically and prevent duplicate concurrent
downloads for the same resource.

Represent all catalog-described formats and support file retrieval
without implying that every format has a story extractor. Initial
polished extraction support covers text and HTML through gettenberg and
existing gatherers.

Cleanup must preserve the original source and return diagnostics about
detected boundaries and transformations. Ambiguous boundaries must not
silently discard content. Existing gather-time normalization and overrides
remain the story-processing authority.

### Decision 9: Migrate callers and preserve research evidence

Options considered: package-only replacement or an explicit migration
inventory covering package, CLI, CI, notebooks, and experiments.

Chosen: migrate all affected active workflows and record dispositions for
the audited research surfaces.

The initial static scan covered 112 Python/notebook files across
lcats/notebooks, lcats/KMo, lcats/experimental, and experiments. It is not
evidence that every historical program executes successfully.

| Surface | Planned disposition |
|---|---|
| Package gettenberg callers, genre utilities, parser, clean command | Migrate to supported public operations |
| CLI dispatcher and gatherer registry | Resolve requirements before initializing source-specific services |
| Notebook 01_gatherers | Simplify around existing library extraction helpers |
| Notebook 02_extractors | Replace dependency examples with supported gettenberg examples |
| Notebooks 10_debug_gutenberg and 14_fix_gettenberg | Extract useful regression cases, then archive as historical diagnostics |
| Notebook/script 15_reconcile_files | Remove obsolete imports; consolidate reusable reconciliation behavior in tested libraries |
| KMo genre entry point | Remove unused dependency imports and retain a small user-facing example |
| KMo analysis/scenes and related notebooks | Compare with current libraries; reuse or extract needed behavior; track unrelated modernization separately |
| experiments/05_metadata_genre_prefilter | Replace schema inspection and SQL with the public local catalog API; preserve offline behavior |
| lcats/experimental | Verify relevant indirect dependencies; retain unaffected experiments |
| Dependency declarations and CI cache maintenance | Remove gutenbergpy and replace implicit maintenance with supported commands |

Reusable extraction helpers already exist at
lcats/src/lcats/gatherers/extractors.py:135 and :170; do not duplicate them.

Each affected entry receives an owner work item, replacement/disposition,
and verification requirement. Archives retain historical context and
reproduction limitations but are excluded from supported entry points.
Historical experiment outputs are not regenerated merely to remove old
dependency references.

## Feature and Evidence Matrix

| Capability | Required evidence |
|---|---|
| RDF metadata fidelity | Curated fixtures and full-snapshot predicate/accounting report |
| Titles and contributor aliases | Real parser-to-SQLite regression tests for the upstream failure cases |
| Query and batch semantics | Public API tests over a real fixture database, including multilingual and multi-value records |
| Catalog lifecycle | Interrupted build/download, invalid schema, concurrent reader/writer, and activation tests |
| Resource acquisition | Cache reuse, integrity, decoding, retry, throttling, and offline tests |
| Boilerplate removal | Representative legacy/current markers and ambiguous-boundary cases |
| Smart first use | Interactive approval, refusal, --yes, noninteractive, and dry-run CLI tests |
| Source independence | Non-Gutenberg collection runs without catalog initialization |
| Corpus migration | Representative old/new outputs with every material difference explained |
| Packaging independence | Fresh wheel installation and metadata/import checks without gutenbergpy |
| Efficiency | Same-input measurements of time, memory, temporary disk, query behavior, and network bytes |
| Usability | Executed tutorial and operational examples with recorded results |

Tests follow LCATS's unittest and deterministic-testing rules. Exercise
real parser, SQLite, and public API behavior; substitute external services
at the network boundary.

Ordinary tests require no live Gutenberg requests or full catalog.
Separate explicitly invoked integration/benchmark jobs reuse recorded
inputs and report source identity.

Baseline failures are recorded as failures, not treated as correct
reference behavior. Numerical performance budgets are set from the first
measurement stage before optimization is accepted.

## Documentation

Create maintained documentation in lcats/docs following its established
Diataxis layout:

- Tutorial: first successful gather and a small Python catalog example.
- How-to: prepare or refresh a catalog, use a local archive, work offline,
  inspect/recover a cache, migrate existing data, and run selected sources.
- Reference: Python API, CLI options and exit behavior, configuration,
  metadata fields, provenance, cache formats, and compatibility policy.
- Explanation: source/volume/story distinctions, catalog generations,
  reproducibility, network policy, and acquisition/extraction boundaries.

Notebook examples remain short clients of documented libraries.
Operational examples must distinguish package-build cleanup from
LCATS data/cache cleanup.

## Non-Goals

- Preserve old gutenbergpy APIs, SQLite tables, or MongoDB support.
- Vendor gutenbergpy, wait for an upstream release, or publish a new fork.
- Implement general PDF/EPUB story extraction in this workstream.
- Build a general RDF query service or hosted catalog API.
- Implement incremental catalog synchronization before full-refresh
  measurements justify it.
- Rewrite unrelated research pipelines.
- Automatically refresh catalogs, replace story outputs, or promote data
  into corpora.
- Publish an LCATS release.
- Grant implementation, merge, or publishing authority through this
  proposal's creation.

## Implementation Plan

This is a multi-stage change. Establish a dedicated workstream, proposed
name WS-GETTENBERG, after design approval. Work item IDs are allocated when
their scopes are defined.

| Stage | Deliverable and exit evidence |
|---|---|
| 0. Planning and baseline | Reconciled control plane, feature inventory, caller dispositions, representative fixtures, baseline measurements, and agreed process charter |
| 1. Models and ingestion | Field mapping, source provenance, bounded RDF ingestion, real SQLite fixture tests |
| 2. Catalog and lifecycle | Public queries, validation, generation activation, recovery, concurrency, and local rebuild |
| 3. Acquisition and cleanup | Resource caching, network policy, decoding, conservative cleanup, regression evidence |
| 4. Gather integration | Collection requirements, smart first use, standalone catalog commands, preserved buckets and normalization |
| 5. Migration and packaging | Active callers migrated, historical tools dispositioned, dependency removed, CI corrected, fresh-install verification |
| 6. Qualification and documentation | Full-snapshot audit, performance report, corpus comparison, exercised documentation, final traceability review |

Tests and documentation accompany each stage; Stage 6 verifies the
integrated result. Use small reviewable PRs.

Before implementation, reconcile:

- WI-RELEASE-0037 with the chosen redesign and new implementing work items.
- WI-RELEASE-0039 with pre-publication verification of the internal
  replacement, preserving its requirement to run near actual publication.
- WS-RELEASE and the release-readiness proposal so they do not continue
  presenting vendor/fork/wait as the active decision.
- The upstream-status backlog entry.
- Current focus and roadmap with the approved workstream.

CI changes receive an explicitly scoped work item because the existing
release work items forbid modifying CI. Do not silently expand their
permissions.

This proposal does not supersede the entire release-readiness proposal.
Dependency removal satisfies one release concern, not all release gates.

## Development Process Experiment

After technical design approval, agree on a separate execution charter
covering autonomous decisions, escalation, review, merge authority, and
completion conditions.

Use LRH work items and execution records as the authoritative record of
scope and delivery. Maintain a proposed development log at
lcats/project/development/gettenberg-development-log.md for process
observations.

Log entries link to the governing work item and evidence, and record:

- Decision or hypothesis.
- Action and observed result.
- Verification or failure evidence.
- Unexpected intervention, friction, or rework.
- A concrete recommendation for improving the reusable LRH process.

The log is not a substitute for execution records and does not reproduce
session transcripts. Separate observations from hypotheses and proposed
process changes.

## Completion Criteria

The workstream is complete when:

1. Active installation and runtime paths no longer depend on gutenbergpy.
2. The feature/evidence matrix is satisfied with linked artifacts.
3. First-run, cached, offline, and unattended gather workflows behave as
   documented.
4. Unrelated source workflows do not initialize Gutenberg.
5. Catalog refresh failures preserve the last valid catalog.
6. Metadata and transformation provenance are inspectable.
7. All affected callers have completed migration or archival dispositions.
8. Corpus differences and resource measurements have been reviewed. The human-approved
   2026-10-22 [scope/qualification amendment](../../../../development/gettenberg-scope-causality-audit.md#approved-qualification-criteria--adopted-2026-10-22)
   defines this as stage-specific accounting for material provider effects, including
   repairs, intended changes, explicit refusals and unresolved blockers. Comprehensive
   editorial reconciliation is separate; missing evidence never establishes equivalence.
9. Required tests, lint/format, package checks, and lrh validate succeed.
10. Documentation, work items, execution records, and the development log
    accurately describe what was delivered.

Approval or filing of this proposal alone satisfies none of these
implementation criteria.

## Remaining Engineering Decisions

These are bounded implementation investigations, not unresolved product
scope:

- Exact public method signatures and concrete normalized schema.
- XML parser choice and any justified direct dependency.
- Platform-compatible locking and activation implementation.
- Benchmark-derived resource targets and fixture selection.
- Exact command spellings and structured status/error schemas.

Record the chosen answers before their implementing changes, with
evidence. Material changes to scope or agreed user behavior return to
design review.

## Cross-References and Sources

Repository file:line evidence above uses repository-root-relative paths
and the inspected LCATS commit e0a838fb.

- lcats/STYLE.md:209 — unittest and deterministic testing requirements.
- lcats/docs/README.md:3 — documentation organization.
- lcats/src/lcats/utils/run_log.py — existing run-event infrastructure.
- lcats/src/lcats/utils/checkpoint.py — existing checkpoint contracts.
- lcats/docs/reference/gather-overrides.md — replayable normalization.
- lcats/project/work_items/proposed/WI-RELEASE-0037.md.
- lcats/project/work_items/proposed/WI-RELEASE-0039.md.
- lcats/project/workstreams/proposed/WS-RELEASE.md.

[S1]: https://github.com/xenotaur/gutenbergpy/blob/60ca548232f470e7aa7c22e8fde636db644cd80e/gutenbergpy/caches/sqlitecache.py#L152
[S2]: https://www.gutenberg.org/ebooks/offline_catalogs.html
[S3]: https://github.com/garethbjohnson/gutendex
[S4]: https://github.com/c-w/Gutenberg
[S5]: https://www.gutenberg.org/policy/robot_access.html
