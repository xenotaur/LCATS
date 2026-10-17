# WI0008 caller migration and disposition ledger

Base: `003c2e08523c9360fdda3a2bfd69b42505c4c51f`. Governing scope:
WI-GETTENBERG-0008 and the approved pilot charter. This ledger implements the
[baseline inventory](gettenberg-baseline.md), not a new API-compatibility promise.
The fresh [static scan](evidence/gettenberg-migration-20261017/inventory.json)
records every Python/notebook path, matching lines and intentional exceptions.

## Implemented dispositions

| Baseline surface | Disposition | Verification |
|---|---|---|
| gettenberg/api, cache, headers, metadata | Remove obsolete upstream API/SQL adapters; use catalog, lifecycle, resources, cleanup. Empty package initializer retained. | Catalog/RDF/lifecycle/acquisition/decoding/cleanup suites; migration import guard; wheel smoke |
| gatherers/parser | Explicit source required; retain filters/extraction/normalization/naming; remove duplicated print-only helpers and expose shared structured inspect_story | live_gather_test; five-case before/after comparison |
| mass_quantities, main, cli | Retain previously accepted migrated orchestration | live_gather/default_sources/preparation tests; installed-wheel CLI previews |
| analysis/corpus/clean_cli | Clear new managed catalog/resource store and legacy remnants only on explicit command | clean_cli_test: targeted/data/cache-only, top-level/nested symlink and legacy-file handling |
| utils/genre | Require caller-owned Catalog for enrichment; rules unchanged; strict canonical URL ID parser | migration_test: real RDF/catalog/classification, missing records, errors, host/ID validation |
| KMo/genre.py | Replace machine-specific exploratory program with thin explicit catalog/corpus CLI | research_clients_test uses a real fixture catalog and temporary corpus |
| experiments/05_metadata_genre_prefilter | Remove raw SQL/schema introspection and AST extraction; read-only Catalog API, explicit errors, normal genre module import | 60 experiment/bridge tests; changed-path format/lint; original outputs unchanged |
| notebooks/01_gatherers | Replace absent Lovecraft module and duplicated HTML extraction with local HTML tutorial using existing extractors | Every code cell executes offline; existing extractor suite retained |
| notebooks/02_extractors | Replace implicit upstream downloads/cache with temporary local catalog and cleanup tutorial, linking explicit acquisition/decoding | Every code cell executes offline, real RDF fixture, missing-state preview |
| notebooks/10_debug_gutenberg and 14_fix_gettenberg | Archive byte-for-byte under experiments/10_gettenberg_qualification/legacy-notebooks; explicitly unsupported | Original Git bytes/hash checked; real catalog ID/title/alias and lifecycle regressions; structured inspect_story |
| notebooks/15_reconcile_files (.ipynb + .py) | Thin clients of new analysis.corpus.reconciliation; canonical buckets, source URL groups, preserved duplicates and strict author/body comparisons | Empty/one/two-sided, duplicates, missing/list authors, sidecars, deterministic/no-write tests; notebook/script execute against local fixture collections |
| tests/gettenberg_tests/{api,cache,headers,metadata}_test | Retire tests of old upstream call delegation, row/SQL shapes, fallback and implicit setup contracts | Replacement behavior mapping below; no failing test suppressed/skipped |
| tests/gatherers_tests/parser_test | Keep pure heuristic tests; replace old mocked legacy/debug client tests with real source inspection/gather tests | live_gather_test and research_clients_test |
| tests/analysis_tests/clean_cli_test; mass_quantities_test; cli_test | Migrate cleanup fixtures, retain already migrated gather/CLI tests | Canonical suite |
| pyproject.toml + environment.yml | Remove the matching VCS dependency pin | Wheel metadata/content inspection, fresh isolated dependency-resolved installation, public imports and offline smoke |
| .github/workflows/cache_maintenance.yml; tests.yml; coverage.yml | Retain unchanged for separate scoped WI0009 | No CI edits in this run; dependency removal does not qualify maintenance workflow |

## Retained and newly discovered surfaces

All other baseline notebooks (03–09, 11–13), KMo/analyze.py, scenes.py and
 testGraph.py, experimental Python files and unrelated experiment runners retain
their prior disposition. Fresh scans include new replacement modules/tests and
qualification runners added since the baseline. No new active legacy consumer was
found outside this ledger. `tools/rewrite_genre_cache_db_path.py`,
`build_genre_seed_manifest.py` and their tests handle historical provenance;
`scripts/utils/fix_pip_vcs_pins.py` retains its generic example. These do not load
the old package. No unrelated LLM/scene work was included.

The newly identified `experiments/10_gettenberg_qualification/scripts/probe_legacy.py`
is intentional historical code. Its measurement requires the recorded historical
checkout/environment. Imports moved inside the explicit measurement entry point so
help/import remain usable without the retired dependency. Archived measurement
bytes were not changed. Current qualification runners remain supported for their
stated bounded inputs. CI's historical cache rebuild is explicitly deferred to WI0009.

## Test-contract replacement

Removed tests predominantly asserted delegation to upstream APIs, wrong row shapes,
old SQL/schema, guessed URL fallback, implicit setup, or lossy header decoding.
These contracts are expressly replaced, not silently claimed compatible:

- Query values, IDs, relations and errors: catalog_test, rdf_test, migration_test.
- Setup/status/rebuild and cache reuse: lifecycle_test, preparation_test,
  default_sources_test; destructive clearing: clean_cli_test.
- Original bytes, receipts, cache reuse and network failures: resources_test and
  routing/refresh suites. No guessed-URL retries remain.
- Strict decoding and conservative boilerplate boundaries: decoding_test and
  cleanup_test. Implicit header-metadata fallback is intentionally removed.
- Story eligibility, source errors, output reuse, atomic publication and extraction:
  live_gather_test. Debug output/positional CSV helpers become structured inspection
  and reconciliation with real fixture tests.

Authored records using IDs 24927/3115 exercise distinct ebook/contributor identities,
titles and aliases; they make no claim about those real ebooks' contents. The two
historical notebooks' values remain investigation leads, not regression truth.

## Comparison and packaging scope

The documented `qualify_migration.py` runner compares the pinned pre-migration
parser's explicit-source path to the current parser on authored LF/CRLF/CR, short
and chaptered fixtures. It retains input/source hashes and output identity groups.
All five agree in result and story JSON. This proves consumer preservation on
those cases, not correctness of the old wrapper or equivalence of the whole corpus.
Existing provenance, catalog and original-byte improvements were already present
at the comparison base. No canonical or archival corpus output is rewritten.

Fresh wheel qualification uses a new temporary venv with normal dependency
resolution, no inherited site-packages and no PYTHONPATH. It checks absence of
upstream/VCS requirements and installed gutenbergpy, imports outside the checkout,
packaged override/allowlist JSON, offline catalog/genre/cleanup/source operations
and CLI previews. This is not package publication or WI-RELEASE-0037 closeout.
Exact results/hashes are captured in the run evidence before acceptance.


## Review repair and acceptance boundary

Cold review found48 nested HTML URLs rejected by the initial identity parser.
After repair, the read-only corpus identity scan covers1868 Gutenberg stories,
including all48 nested URLs, with zero failures. The reviewer independently
repeated it. New tests use actual Sherlock/O. Henry/Chesterton URL shapes and
retain wrong-host rejection. No stored story was changed.

The baseline feature/caller matrix explicitly assigns side-by-side fixture corpus
output and fixture gather comparison to WI0008 (gettenberg-baseline.md lines104
and143). The five authored cases implement that bounded comparison, supplemented
by real-corpus source identity coverage. Full-snapshot/content corpus qualification
remains WI0010, as the governing design's qualification tranche specifies. No
claim of whole-corpus regenerated text equivalence is made.
