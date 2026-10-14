# Gettenberg replacement baseline

Scope: WI-GETTENBERG-0001, run `gettenberg-20261014`, source baseline
`5cfd2d71caf6f3eedfdfc0b830b5c5ff1a74ba3b`. Citations below are repository-relative
at that base unless labeled upstream. Static audit findings are not claims that
historical programs run. This report does not qualify the replacement or resolve
a release item.

## Inputs, reproducibility and measurements

The existing cache supplied immutable read-only inputs; no bulk network download
or catalog rebuild occurred. Original retrieval URL/time and proof that the
existing database was built from this exact archive are unavailable. Matching
counts are corroboration, not a fabricated provenance link.

| Input | Bytes | SHA-256 |
|---|---:|---|
| rdf-files.tar.bz2 | 125955051 | 358f177c30818027ad93b3478da2248d7996999475d83e59288ee74423050b28 |
| gutenbergindex.db | 342450176 | 188b422247c48807459f3aedac6dad462244e91a2885543e3051555c0e0a39f5 |

[Measured evidence](../../../experiments/10_gettenberg_qualification/results/gettenberg-pilot-20261014/baseline-measurements.json):
78,937 RDF members/ebook records, 2,079,559,859 uncompressed bytes; maximum record
1,223,616 bytes. The database has 78,937 books, 84,278 titles, 29,822 aliases,
127,880 book-alias links and 2,018,879 resources. The bounded archive/XML audit
plus hashes and DB reads took 78.584 seconds, peak RSS 79,298,560 bytes on macOS
using `resource.getrusage(RUSAGE_SELF).ru_maxrss`. No tar extraction, zero bulk
network bytes; a small JSON inspection sample was saved privately. This is an
**audit measurement**, not the legacy parser's full-build performance.

Environment: Python 3.11.9, SQLite through stdlib, lxml from the LCATS environment;
Black 25.11.0, Ruff 0.15.0. `PYTHONPATH=$PWD/src` binds imports to the intended
worktree. Installed package-version metadata refers to an older shared editable
installation; it is not evidence of the current source SHA. The installed
`gutenbergpy` is 0.3.6 from exact VCS commit
`60ca548232f470e7aa7c22e8fde636db644cd80e`, verified by distribution direct_url.json.

Reproduce from `lcats/`, in the LCATS environment, using separately supplied
local input paths (never the canonical live cache as a write destination):

```bash
python ../experiments/10_gettenberg_qualification/scripts/measure_baseline.py "$ARCHIVE" "$DATABASE" /tmp/gettenberg-baseline.json
LCATS_CACHE_DIR=/tmp/gettenberg-probe PYTHONPATH="$PWD/src" python ../experiments/10_gettenberg_qualification/scripts/probe_legacy.py "$DATABASE"
LCATS_CACHE_DIR=/tmp/gettenberg-tests PYTHONPATH="$PWD/src" scripts/test
```

The measurement script imposes 256 MiB compressed, 4 GiB expanded, 8 MiB/member,
200,000 members and 180-second loop bounds. It rejects DTD/entities, uses a
network-disabled lxml parser, streams members, clears tar metadata retention,
and opens SQLite `mode=ro&immutable=1`. Inputs must remain immutable during the
run; metadata timestamps are checked afterwards. Two recorded query probes
returned a 100-ID English page in 0.000399s and ebook 84 in 0.000292s. These are
single warm-cache observations, not performance promises or statistically
representative benchmark claims.

Known audit limitation: the feature-example selector used the older relator
namespace spelling, so it selected no non-creator-role sample. The complete XML
element counter correctly records 27 role predicates in the actual
`http://id.loc.gov/vocabulary/relators/` namespace. Parser tests must use that
observed namespace; no absence of roles is inferred from the sample selector.

## Observed legacy failures and acceptance consequences

[Reproduced query probe](../../../experiments/10_gettenberg_qualification/results/gettenberg-pilot-20261014/legacy-probe.json)
uses actual upstream SQLite queries and wrapper code, substituting only the
cache acquisition factory to prevent implicit setup and provide read-only access.

- Upstream `query(languages=['en'])`: 62,689 integer IDs.
- Public wrapper `get_etexts(languages='en')`: zero IDs. The wrapper supplies
  downloadtype as a string while upstream iterates it as filter values
  (`lcats/src/lcats/gettenberg/api.py:107`; upstream `caches/sqlitecache.py:139–148`).
- A diagnostic list-valued downloadtype (outside the declared public signature)
  passes that first mismatch and reproduces the second: `TypeError: cache.query
  returned a non-mapping row at index 0: int`. See wrapper `api.py:113–119` and
  upstream `sqlitecache.py:152–154`.
- Static: upstream subject join reverses book/subject columns
  (`sqlitecache.py:128`); this was not runtime-qualified as a separate probe.
- Importing cache creates directories (`cache.py:32–36`); skip_cache metadata may
  fetch text (`api.py:177–201`); URL fallback retries patterns after HTTP failures
  (`cache.py:147–173`). New acceptance tests explicitly prohibit those surprises.

Do not use these baseline failures as correct reference outputs. The canonical
existing suite passed **2,550 tests in 63.800s**, exit 0; format/lint passed.
This demonstrates a coverage gap, not correctness of the metadata query path.

## Feature/evidence matrix and ownership

Upstream source references below are relative to the installed `gutenbergpy/`
at commit `60ca548...`; no upstream source code or marker list is copied here.

| Capability / baseline | Replacement verification | Owner |
|---|---|---|
| Build/cache controls; SQLite and Mongo user-facing metadata access (`gutenbergcache.py:25–80`) | Explicit local build/setup/status/refresh/cleanup; typed metadata superset through SQLite; old backend/API compatibility intentionally excluded | 0003, 0004 |
| Primary/alternative titles, aliases (`parse/rdfparser.py:25–34`) | Real RDF-to-SQLite multi-title associations; aliases tied to contributor identity/role | 0002, 0003 |
| Publisher, rights, type, release date, downloads (`rdfparser.py:31–65`) | Nullable typed values, no sentinel dates; queried/documented metadata | 0002, 0003 |
| Language, shelves, subjects (`rdfparser.py:27–32`) | All values retained; subject schemes distinct; no first-value truncation | 0002, 0003 |
| Contributors beyond creators and life dates | All observed relator roles, names/aliases/source IDs preserved; absent values explicit | 0002 |
| File links and download type (`parse/parseitemfile.py:21–45`) | Distinct URL identities with all formats/encodings/sizes/modifications; equal MIME type does not collapse files | 0002, 0005 |
| Native query/filter dimensions (`caches/sqlitecache.py:112–161`) | Typed safe public filters for languages, contributors, type, title, subjects, publishers, shelves, resource format; AND across/OR within; separate text matching | 0003 |
| Resource download and decoded gzip cache (`textget.py:146–166`) | Original byte cache, explicit acquisition, offline/dry-run, retry/pacing and atomic publication | 0005 |
| Boilerplate removal (`textget.py:170` and wrapper headers.py) | Conservative boundaries, source retention, diagnostic ambiguity, verified attribution if reused | 0006 |
| Rich descriptions, summaries, MARC and provenance | Per-predicate disposition below; raw source bytes/hash retained; machine-generated summaries labeled as source metadata | 0002, 0010 |
| Catalog lifecycle/recovery | Single writer, pinned readers, valid generations, crash/failure tests and offline rebuild | 0004 |
| Smart first-use and source isolation | Interactive/refusal/yes/unattended/offline/dry-run CLI tests; unrelated sources avoid catalog setup | 0007 |
| Caller, corpus and packaging migration | Inventory dispositions; side-by-side fixture corpus output; wheel install without gutenbergpy | 0008 |
| CI maintenance | Real supported commands; no mocked cache rebuild or failure suppression; offline unit CI | 0009 |
| Efficiency and documentation | Same-input old/new measurements; exercised tutorial/how-to/reference/explanation; exact-head traceability | 0010 |

Owner abbreviations mean WI-GETTENBERG-NNNN. Every row is planned evidence,
not a claim of replacement acceptance. Standard Python/lxml/SQLite utilities
are permitted; old SQL schemas, Mongo backend, vendoring and upstream waiting
are deliberately outside compatibility scope.

## Caller audit and dispositions

Audit universe: 9,054 tracked paths; 339 Python plus 16 notebooks (355 surfaces).
The named research subtrees contain 112: notebooks 17, experimental 46,
experiments 45, KMo 4. [Exact code universe](evidence/gettenberg-pilot-20261014/code-universe.txt)
SHA-256: `88df5e15802dae460024a5ba7b8193772737d626ce009dc4139c055c10fd1e48`.
All Python files parsed; the notebook audit examined 407 code and 186 Markdown
cells with zero stored outputs. Notebook citations below use one-based cell and
source-line numbers, so they do not depend on serialized JSON line wrapping.

Reproduce broad discovery with `git ls-tree -r --name-only 5cfd2d71` and case-
insensitive scans over Python lines/joined notebook cell source:

- `gutenbergpy|gettenberg|gutenbergcache|from\s+gutenberg|import\s+gutenberg`:
  23 candidate files, 93 Python matching lines, 21 notebook code cells.
- `native_query|gutenbergindex|book_subjects|book_authors|\bFROM\s+(?:books|titles|subjects|authors|languages)\b`:
  11 candidates, 70 Python lines, 13 notebook code cells.
- `BeautifulSoup|requests\.(?:get|head)|urlopen|\bdef\s+(?:extract_tags_between_ids|extract_text_from_tags|header_titles?_for|header_title|titles_for|subjects_for|authors_for|languages_for|run_rdfparser|capture_parser)`:
  27 candidates, 60 Python lines, 11 notebook code cells.

A Python AST import reverse closure from the five gettenberg module files found
8 non-test and 8 test callers. Supplementary searches covered load_etext,
strip_headers, get_metadata/get_etexts, gatherers, genre, importlib and
spec_from_file_location, plus manifests/CI/scripts. Counts include comments and
docstrings; manually classified outcomes follow. Static coverage cannot prove
arbitrary dynamic runtime imports absent.

| Surface / source evidence | Disposition and verification | Owner |
|---|---|---|
| gettenberg/api.py:19,27,57,86,140; cache.py:11,32,54,106,147,176; metadata.py:8,80–207; headers.py:5,8 | Replace implementation through typed catalog/resources/cleanup; real fixtures and import-side-effect checks. Empty __init__.py retained. | 0002–0006, 0008 |
| gatherers/parser.py:17–18,1377–1407,1498–1522,1556–1580,1630–1732 | Migrate calls; retain story extraction, naming, normalization/overrides; fixture gather comparison | 0007, 0008 |
| gatherers/mass_quantities/gatherer.py:9,89; gatherers/main.py:14,32; cli.py:9,13,33 | Migrate eager initialization/orchestration; help/dry-run/unrelated-source tests with missing catalog | 0007 |
| analysis/corpus/clean_cli.py:15–16,83–91 | Migrate explicit cleanup; targeted/data/cache-only, symlink-safe retention tests | 0008 |
| utils/genre.py:4,235,245,261–281 | Migrate subject retrieval, retain classification rules; fixture classifications and URL provenance | 0008 |
| lcats/KMo/genre.py:29–30,79–83 | Remove unused direct API import AND migrate real indirect genre metadata use; thin fixture example | 0008 |
| experiments/05_metadata_genre_prefilter/run_prefilter.py:163–181,229–373,703; run_prefilter_test.py:47,75,90,426 | Replace raw SQL/table introspection and AST workaround with explicit read-only catalog API; retain missing/unreadable/incompatible outcomes and deduplicated subjects | 0008 |
| notebooks/01_gatherers.ipynb c6:L10, c9:L1, c16:L6, c18:L4, c20:L5/L18 | Replace absent lovecraft.gutenberg import and duplicated HTML helpers with gatherers/extractors.py:135,170,189; local HTML example and extractor regressions | 0008 |
| notebooks/02_extractors.ipynb c3:L1, c5:L2, c6:L2, c8:L1 | Thin supported catalog/acquisition/cleanup tutorial; offline fixture and missing-setup outcomes | 0008 |
| notebooks/10_debug_gutenberg.ipynb c5:L5,c9:L2,c14–21,c23 | Extract deterministic metadata/status regressions, then archive upstream settings/rebuild/raw SQL diagnostics; no automatic rebuild | 0008 |
| notebooks/14_fix_gettenberg.ipynb c9,c12,c24,c26,c32,c36–47,c50–55 | Extract structured gather inspection and deterministic parser/SQLite ID-title-alias regressions, then archive upstream monkeypatch harness; IDs 24927/3115 are unverified fixture leads | 0008 |
| notebooks/15_reconcile_files.ipynb c9:L8,c11:L3,c20,c22,c26; paired .py:73–80,97–113,204,224,271 | Remove unused imports/obsolete parser path; extract reusable load/collate/join into analysis.corpus.reconciliation; test one/two-sided records, duplicate URLs, missing/list authors and deterministic output | 0008 |
| tests/gettenberg_tests/{api,cache,headers,metadata}_test.py; analysis_tests/clean_cli_test.py:8; gatherers_tests/{parser_test.py:8,mass_quantities_test.py:9}; cli_test.py:8 | Preserve behavior coverage, replace mocks of broken row shape with real fixtures; remove api_test.py:14 upstream import | 0008 |
| pyproject.toml:28; environment.yml:263 | Remove matching external pins, verify fresh distribution | 0008 |
| .github/workflows/cache_maintenance.yml:75; tests.yml; coverage.yml | Separate scoped CI correction; unit tests stay offline; no live cache deletion during validation | 0009 |

Paths in this table without a repository prefix are under `lcats/src/lcats/`
for package code, `lcats/` for notebooks/tests/manifests, and repository root for
experiments/.github. No notebook has been edited or archived in the bootstrap.

Retained research surfaces (no discovered catalog dependency): notebooks
03_datasets, 04_rag_expt, both 05_prog_llm notebooks, 06_story_analysis,
07_project_reboot, 08_cbr_rag_reboot, 09_scene_analysis, 11_analyze_corpus,
12_extract_scenes and 13_clean_corpus; KMo/analyze.py, scenes.py and testGraph.py;
all 46 experimental Python files; 43 other experiments Python files. The
independent HTML extractors used by several are not gettenberg callers.
Unrelated LLM/scene modernization remains outside this migration.

Retain tools/rewrite_genre_cache_db_path.py:35 and build_genre_seed_manifest.py:76,118:
these process historical provenance, not live catalogs; matching dev tests are
historical fixture values. Retain scripts/utils/fix_pip_vcs_pins.py:6 as a generic
helper (gutenbergpy appears only in an example). scripts/clean removes build
artifacts, distinct from data/catalog cleanup.

## Fixtures and provenance plan

The official [robot access policy](https://www.gutenberg.org/policy/robot_access.html)
grants catalog metadata to the public domain; the
[offline catalog guide](https://www.gutenberg.org/ebooks/offline_catalogs.html)
recommends machine-readable feeds rather than site crawling. Read on 2026-10-14.
Use bounded records from the hashed local archive with member name/hash/size
and retrieval provenance explicitly unknown. Do not infer that ebooks themselves
have the same rights as their catalog metadata.

Verified candidates: `cache/epub/10000/pg10000.rdf` (aliases, 17,039 bytes,
SHA 708eab35674c25d6543be161d4fdc5f35ce83d839ad534c6ee481c3abf90ae2e)
and `cache/epub/10040/pg10040.rdf` (alternative title, en+ale, 17,512 bytes,
SHA eb1f341a0b11cee6e80c8a52d21a78c8cc543f8d4860a36f6574b74dfaa66d26).
Small raw records 1 and 84 were inspected privately as additional candidates.
Before committing fixtures, record their exact hashes/rights/provenance and
keep all original bytes. Synthetic fixtures must say authored, not downloaded.

Author synthetic cases for DTD/entities, oversized/deep input, malformed IDs,
unknown predicates, duplicate fields/resources, missing optional values,
creator roles/aliases with intentionally different IDs, and deletion/non-book
records (none present in this snapshot). Later tests cover transaction rollback,
archive symlinks/path traversal, truncation, concurrent publication, stale/invalid
schema, network denial/Retry-After/redirects, ambiguous cleanup, and CLI refusal.
Full archive qualification is distinct from ordinary offline unit tests.

## Predicate dispositions and resource bounds

The complete observed XML vocabulary below maps each element to a planned
representation; XML containers are not themselves RDF predicates. Source bytes
retain every observed value and attribute. New predicates require diagnostics;
this inventory is one recorded snapshot, not a closed universal vocabulary.

| Observed element | Occurrences | Planned disposition |
|---|---:|---|
| `{http://id.loc.gov/vocabulary/relators/}adp` | 60 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}aft` | 2 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}ann` | 133 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}arr` | 12 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}art` | 42 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}aui` | 1190 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}clb` | 2 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}cmm` | 435 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}cmp` | 72 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}cnd` | 2 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}com` | 482 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}ctb` | 2313 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}dub` | 121 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}edt` | 7127 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}egr` | 86 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}frg` | 1 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}ill` | 9853 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}lbt` | 16 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}oth` | 109 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}pbl` | 67 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}pht` | 82 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}prf` | 80 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}prt` | 4 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}res` | 1 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}trc` | 3 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}trl` | 7241 | Contributor role URI + associated agent identity/metadata |
| `{http://id.loc.gov/vocabulary/relators/}unk` | 10 | Contributor role URI + associated agent identity/metadata |
| `{http://purl.org/dc/dcam/}memberOf` | 2747328 | Preserve source relationship/license/comment; subject/format schemes modeled where applicable |
| `{http://purl.org/dc/terms/}alternative` | 5340 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://purl.org/dc/terms/}creator` | 79624 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://purl.org/dc/terms/}description` | 104543 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://purl.org/dc/terms/}extent` | 2022362 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://purl.org/dc/terms/}format` | 2196609 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://purl.org/dc/terms/}hasFormat` | 2018879 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://purl.org/dc/terms/}isFormatOf` | 2018879 | Preserve source relationship/license/comment; subject/format schemes modeled where applicable |
| `{http://purl.org/dc/terms/}issued` | 78937 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://purl.org/dc/terms/}language` | 79162 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://purl.org/dc/terms/}license` | 78937 | Preserve source relationship/license/comment; subject/format schemes modeled where applicable |
| `{http://purl.org/dc/terms/}modified` | 2022372 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://purl.org/dc/terms/}publisher` | 78937 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://purl.org/dc/terms/}rights` | 78937 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://purl.org/dc/terms/}subject` | 265507 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://purl.org/dc/terms/}tableOfContents` | 8334 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://purl.org/dc/terms/}title` | 78941 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://purl.org/dc/terms/}type` | 78937 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://web.resource.org/cc/}Work` | 78937 | Structural/source evidence; nested values modeled by owner |
| `{http://web.resource.org/cc/}license` | 78937 | Preserve source relationship/license/comment; subject/format schemes modeled where applicable |
| `{http://www.gutenberg.org/2009/pgterms/}agent` | 109138 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://www.gutenberg.org/2009/pgterms/}alias` | 164426 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://www.gutenberg.org/2009/pgterms/}birthdate` | 89286 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://www.gutenberg.org/2009/pgterms/}bookshelf` | 206275 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://www.gutenberg.org/2009/pgterms/}deathdate` | 87927 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://www.gutenberg.org/2009/pgterms/}downloads` | 78937 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://www.gutenberg.org/2009/pgterms/}ebook` | 78937 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://www.gutenberg.org/2009/pgterms/}file` | 2018879 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://www.gutenberg.org/2009/pgterms/}marc010` | 13153 | Preserve MARC predicate/value as source metadata; marc520 summary explicitly source-supplied |
| `{http://www.gutenberg.org/2009/pgterms/}marc020` | 1 | Preserve MARC predicate/value as source metadata; marc520 summary explicitly source-supplied |
| `{http://www.gutenberg.org/2009/pgterms/}marc250` | 331 | Preserve MARC predicate/value as source metadata; marc520 summary explicitly source-supplied |
| `{http://www.gutenberg.org/2009/pgterms/}marc260` | 12565 | Preserve MARC predicate/value as source metadata; marc520 summary explicitly source-supplied |
| `{http://www.gutenberg.org/2009/pgterms/}marc300` | 7 | Preserve MARC predicate/value as source metadata; marc520 summary explicitly source-supplied |
| `{http://www.gutenberg.org/2009/pgterms/}marc440` | 5638 | Preserve MARC predicate/value as source metadata; marc520 summary explicitly source-supplied |
| `{http://www.gutenberg.org/2009/pgterms/}marc508` | 75952 | Preserve MARC predicate/value as source metadata; marc520 summary explicitly source-supplied |
| `{http://www.gutenberg.org/2009/pgterms/}marc520` | 76918 | Preserve MARC predicate/value as source metadata; marc520 summary explicitly source-supplied |
| `{http://www.gutenberg.org/2009/pgterms/}marc546` | 148 | Preserve MARC predicate/value as source metadata; marc520 summary explicitly source-supplied |
| `{http://www.gutenberg.org/2009/pgterms/}marc901` | 9236 | Preserve MARC predicate/value as source metadata; marc520 summary explicitly source-supplied |
| `{http://www.gutenberg.org/2009/pgterms/}marc902` | 9 | Preserve MARC predicate/value as source metadata; marc520 summary explicitly source-supplied |
| `{http://www.gutenberg.org/2009/pgterms/}marc903` | 2 | Preserve MARC predicate/value as source metadata; marc520 summary explicitly source-supplied |
| `{http://www.gutenberg.org/2009/pgterms/}marc904` | 7957 | Preserve MARC predicate/value as source metadata; marc520 summary explicitly source-supplied |
| `{http://www.gutenberg.org/2009/pgterms/}marc905` | 12252 | Preserve MARC predicate/value as source metadata; marc520 summary explicitly source-supplied |
| `{http://www.gutenberg.org/2009/pgterms/}marc906` | 12201 | Preserve MARC predicate/value as source metadata; marc520 summary explicitly source-supplied |
| `{http://www.gutenberg.org/2009/pgterms/}marc907` | 12203 | Preserve MARC predicate/value as source metadata; marc520 summary explicitly source-supplied |
| `{http://www.gutenberg.org/2009/pgterms/}marc908` | 74369 | Preserve MARC predicate/value as source metadata; marc520 summary explicitly source-supplied |
| `{http://www.gutenberg.org/2009/pgterms/}name` | 109138 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://www.gutenberg.org/2009/pgterms/}webpage` | 89631 | Typed corresponding ebook/contributor/resource field; retain original RDF evidence |
| `{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description` | 2916096 | Structural/source evidence; nested values modeled by owner |
| `{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF` | 78937 | Structural/source evidence; nested values modeled by owner |
| `{http://www.w3.org/1999/02/22-rdf-syntax-ns#}value` | 2826490 | Structural/source evidence; nested values modeled by owner |
| `{http://www.w3.org/2000/01/rdf-schema#}comment` | 78937 | Preserve source relationship/license/comment; subject/format schemes modeled where applicable |

Attributes about/resource/base determine URI identity; datatype and nodeID remain
in source evidence with modeled value semantics. No print-publication date is
fabricated from Gutenberg issued. Additional MARC print-source claims remain
source-labeled, not asserted as normalized original publication dates.

Initial next-item limits are explicit: 2 MiB per RDF record, 256 MiB compressed,
4 GiB expanded, 200,000 archive members; bounded 256-record DB batches. They
cover this measured snapshot and may be overridden explicitly. Target full-build
qualification <=512 MiB RSS / <=10 minutes / <=4 GiB temporary output must be
measured, not silently weakened. Performance acceptance still needs comparable
legacy/new builds and multiple query runs; current audit provides neither.
Future network acquisition is separately scoped: one active request, >=2-second
spacing, 30-second timeout, <=2 retries, Retry-After respected within run deadline,
explicit size bounds and no downloads merely for unit tests.

## Control-plane reconciliation and remaining gaps

WI-RELEASE-0037 now verifies the WS-GETTENBERG replacement rather than choosing
vendor/fork/wait. WI-RELEASE-0039 retains imminent-publication timing. WS-RELEASE,
its proposal, upstream-watch history, focus and roadmap are reconciled; neither
release item is resolved. WI-GETTENBERG-0002 through 0010 scope the next tranches;
0009 alone authorizes CI edits. Native prompt readiness is separate from staged
dependency acceptance under the charter.

Before downstream dispatch, independently review this report/plan and map
bootstrap acceptance to exact integrated evidence. Remaining qualification gaps:
legacy full-build cost; source retrieval provenance/DB-to-archive relationship;
real deletion fixtures; corpus output comparison; exercised replacement docs;
new library implementation and fresh install. No gap is counted as a pass.
