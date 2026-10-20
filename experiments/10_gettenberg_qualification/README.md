# Gettenberg offline qualification

This archival experiment preserves the baseline and full-source qualification
behind WI-GETTENBERG-0001 through WI-GETTENBERG-0004. Decisions and execution
history remain in the [control-plane runlog](../../lcats/project/development/gettenberg-development-log.md).

## Historical results and relocation

`results/` contains original measurements, preserved byte-for-byte.
[relocation.json](relocation.json) maps old control-plane paths to these paths,
records original SHA256 values, and identifies the pre-relocation revision.
Embedded source paths, commits, hashes and absolute machine-local paths are
historical observations, not commands or portable defaults. Do not overwrite
these results during a rerun; choose a new output directory outside tracked data.
The revised runners were not used to produce the historical measurements.

| Runner | Purpose and outputs |
|---|---|
| `scripts/measure_baseline.py` | Read-only legacy archive/SQLite inventory; writes OUTPUT_JSON and adjacent rdf_samples.json. |
| `scripts/probe_legacy.py` | Actual historical gutenbergpy and LCATS-wrapper queries through a substituted read-only cache factory; prints JSON. |
| `scripts/probe_parser.py` | Stream-only RDF parsing, source hashes, counts, bounded diagnostic examples and timing; writes JSON. |
| `scripts/qualify_catalog.py` | Build a new private SQLite candidate, compare pinned snapshot counts, enumerate/query and round-trip fixtures; writes success/failure JSON. |
| `scripts/qualify_lifecycle.py` | Build/activate a new private cache, verify pinned counts and fixture queries, exercise reuse/readers/cleanup; writes success/failure JSON. |

The first three runners are historical observations, not release acceptance
commands. The latter two intentionally qualify the recorded snapshot (SHA256
358f177c30818027ad93b3478da2248d7996999475d83e59288ee74423050b28). A different
snapshot should fail qualification rather than silently redefine acceptance.
They call the production parser/catalog/lifecycle; they are not a second library.

## Run explicitly

Use the LCATS project Python environment and run from `lcats/`, with local cached
inputs. Every runner supports `--help`; no runner downloads a catalog. Example:

```bash
export PYTHONPATH="$PWD/src"
python ../experiments/10_gettenberg_qualification/scripts/qualify_catalog.py \
  /path/to/rdf-files.tar.bz2 /tmp/new-candidate.sqlite /tmp/catalog-result.json
python ../experiments/10_gettenberg_qualification/scripts/qualify_lifecycle.py \
  /path/to/rdf-files.tar.bz2 /tmp/new-cache /tmp/lifecycle-result.json
```

Output parents must exist. Candidate/database and cache paths must be new; never
point a qualification run at the canonical corpus or an existing live cache.
Catalog paths are resolved before SQLite URI conversion, including relative ones.
Archive limits come from BuildLimits; the lifecycle run additionally requires
6 GiB free space and POSIX SIGALRM for a 900-second whole-run ceiling. Fixture
qualification is intentionally offline; lifecycle blocks socket creation.
`qualified` records semantic acceptance; `peak_rss_target_pass` separately records
the 512 MiB resource target. Accept a full result only if both pass and the process
exits zero. The parser/baseline/catalog RSS figures use macOS ru_maxrss bytes;
those runners' historical performance comparisons require macOS. The lifecycle
runner normalizes Linux/macOS units. These are measurements, not timing guarantees.

Legacy runners require the dependency/schema of their original recorded LCATS
revision. After gutenbergpy removal, use that historical checkout/environment to
reproduce them; do not restore the production dependency for archival convenience.

## Diagnostics interpretation

Repeated Gutenberg predicate URLs are one entry per diagnostic occurrence, not
repeat network requests. For example, the original parser recorded 223 URI
normalizations: 222 file predicates and 1 webpage predicate. A book with multiple
normalized resources repeats the file predicate. Keep raw multiplicity in the
historical JSON; use diagnostic_predicates/diagnostic_codes for aggregate counts.
The diagnostic sampling code records up to 20 example records.

## Validate changes

From `lcats/` in the project environment:

```bash
scripts/format --check --diff -- ../experiments/10_gettenberg_qualification/scripts
scripts/lint ../experiments/10_gettenberg_qualification/scripts
scripts/test tests/gettenberg_tests
```

The offline helper regression suite under `tests/gettenberg_tests/` checks import
safety, CLI usage, relative URI paths and optimized-Python acceptance behavior.
Full-archive runs are explicit qualification, not unit-test side effects. Any
change to measurement/acceptance logic requires affected checks and accurately
attributed new evidence; old results do not become measurements of new code.

## Caller migration comparison

`qualify_migration.py` compares the parser at integration base `003c2e085` with
the current parser using five authored fixture cases and the same explicit
catalog/source adapter. Run from `lcats/`, with the development environment and
`PYTHONPATH="$PWD/src"`:

```bash
python ../experiments/10_gettenberg_qualification/scripts/qualify_migration.py /tmp/new-migration-result.json
```

The pinned Git commit must be available locally (a shallow clone may need that
history fetched first). The runner reuses the source checkout's test fixture
builders and in-memory HTTP boundary. It blocks real sockets, creates only
temporary catalogs/caches/output buckets, and refuses to overwrite the result
file. Compare JSON includes source hashes and one/two-sided source groups. Five
matching fixtures establish consumer preservation, not whole-corpus equivalence
or qualification of the old wrapper's known failures. No historical result is
rewritten. [Legacy notebooks](legacy-notebooks/README.md) record the relocation
and supported replacements for upstream-specific diagnostics.

## Final replacement qualification (WI-GETTENBERG-0010)

Run from `lcats/` with the project environment and this checkout's `src` on
`PYTHONPATH`. These commands consume retained local inputs only; they never fetch
Gutenberg data or modify existing corpus/cache files. Choose new output paths.

```bash
python ../experiments/10_gettenberg_qualification/scripts/qualify_lifecycle.py ARCHIVE NEW_CACHE LIFECYCLE_JSON
python ../experiments/10_gettenberg_qualification/scripts/qualify_snapshot.py ARCHIVE NEW_CACHE SNAPSHOT_JSON
python ../experiments/10_gettenberg_qualification/scripts/qualify_legacy_build.py ARCHIVE NEW_LEGACY_DIRECTORY LEGACY_JSON
python ../experiments/10_gettenberg_qualification/scripts/qualify_cached_corpus.py NEW_CACHE LEGACY_TEXTS ../corpora/mass_quantities CORPUS_JSON
```

The lifecycle and snapshot runners require the recorded archive SHA. Snapshot
qualification checks **every** catalog record against the current parser's typed
values, diagnostics and original RDF bytes, then compares complete ID sets and
inventories every XML element/attribute. This checks storage fidelity, not an
independent implementation of RDF semantics; the semantic fixture suite remains
necessary. Its three English query timings use bounded public pagination.

The historical build runner requires an environment **already containing** the
recorded `gutenbergpy`; do not add that dependency back to LCATS. It fingerprints
the actual historical source, copies the pinned archive to a new directory and
runs upstream unpack/parse/SQLite creation unchanged, with progress output sent
to the null device. The pinned archive was previously audited as regular bounded
RDF files; the old extractor must never receive arbitrary archives. It preserves
its extracted files and records retained logical disk bytes, database hash/counts
and normalized process peak RSS. Input copying and network time are excluded from
its build time. Retained files are useful evidence, not a production cache.

Cached corpus comparison reads legacy `<id>.txt.gz` files: these contain text
already decoded and re-encoded as UTF-8 by the old downloader. They **cannot prove
wire-byte or encoding equivalence**. No invented HTTP receipts are written. On
identical cached decoded input/current catalog metadata, the runner compares old
and new cleanup followed by the same real extractor and normalization. Retained
corpus bodies are a separate comparison, because editorial changes and catalog
snapshot differences may intervene. Missing inputs, metadata rejections and
cleanup refusals stay explicit; `completed` means the experiment ran, not that
all outputs matched. Review every material difference before acceptance. The
runner writes hashes and bounded difference excerpts, not duplicate story files.

All new runners refuse existing output files. POSIX alarms bound snapshot work to
900 seconds, historical build to1,200 and corpus comparison to600; expanded member
and text limits are separate. At least6 GiB free is needed before a full build;
allow15 GiB for the combined isolated experiment and wheel environment. Run one
bulk build at a time. Process RSS uses bytes on macOS and KiB conversion on Linux;
these are single local observations, not controlled performance claims. Failures
retain JSON and partial isolated output for diagnosis. Inspect results and exit
status together. Do not overwrite historical results when retrying.

For packaging, build a wheel normally, install it into a fresh virtual environment
with declared dependencies, and run the installed smoke outside the checkout:

```bash
env -u PYTHONPATH /path/to/venv/bin/python /absolute/path/to/qualify_installed.py NEW_JSON
/path/to/venv/bin/python -m pip check
```

`qualify_installed.py` requires no legacy dependency, makes no requests, checks
installed imports and metadata, builds a temporary authored catalog and exercises
queries, raw-source fidelity, genre, cleanup and packaged JSON. Separately compare
wheel source bytes with the candidate checkout, run installed CLI previews, and
record exact hashes. A smoke pass alone does not establish wheel/source identity.
The runner imports safely and supports `--help` in an ordinary environment.

`summarize_corpus.py INPUT_JSON NEW_SUMMARY_JSON` produces a compact per-story
review index, preserving refusals/missing inputs and distinguishing appended
suffixes from earlier body differences. Its labels are mechanical triage, never
narrative-safety acceptance. Full reports may be archived as gzip-compressed
verbatim JSON to keep review diffs manageable; the result manifest records both
compressed and decompressed hashes. Decompression recovers the original report
bytes exactly. No story source files or canonical outputs are copied into results.

`qualify_index_counts.py SNAPSHOT_JSON NEW_DATABASE LEGACY_DATABASE NEW_JSON`
complements raw-source replay with40 aggregate normalized-index checks, including
all observed MARC fields, and a source-attributed English query comparison. It
opens both databases read-only, verifies the new database's archive identity and
records database hashes. Aggregate multiplicity does not prove each indexed value;
semantic query fixtures remain necessary. `Catalog.get()` reparses retained RDF,
so the snapshot replay alone must not be described as a normalized-table audit.

The cached-corpus runner rejects missing/non-directory collections and empty
canonical story selections, writes `completed: false` with an error, and exits
nonzero. A directory containing only flat JSON is empty under the canonical
bucket selector. Existing full reports retain their original runner hashes;
`results/gettenberg-qualification-20261018/runner-repair-addendum.json` records
the later invalid-input guard repair and confirms the measured selection still
contains exactly the same 1,659 paths. No historical report is rewritten.

## Narrative preservation repair qualification

Use `qualify_cached_corpus.py` with
`--baseline-parser-ref 335855c04cd7ba936815d2635969d94fdd278c71` to compare old
cleanup plus the pinned pre-repair parser against current cleanup/extraction.
The local Git object must exist; this option never fetches it. The baseline source
hash is recorded separately. Omitting the option retains the cleanup-only
comparison (the same current extractor on both sides). Neither comparison alone
proves narrative correctness.

`qualify_narrative_cases.py CATALOG_CACHE TEXT_CACHE CASES_JSON NEW_OUTPUT_JSON`
checks complete narrative spans between coordinator-reviewed source anchors, then
runs real inspection, normalization and publication into temporary buckets. Input
hashes must match, both anchors must be unique and ordered, and every character
between them must survive extraction. Published provenance explicitly says
`historical_decoded_utf8_cache`; no HTTP receipt is invented. Reusing the temporary
output must leave its bytes unchanged. The runner blocks sockets, removes its
temporary collection and enforces a120-second POSIX alarm. A missing/mismatched
input or lost span aborts with failure JSON. Eligibility rejections remain failed
publication checks while other cases continue; `completed: true` means the audit
finished, and exit status1 / `all_publication_checks_passed: false` remains a
failure. Results and anchors are under `results/gettenberg-narrative-20261018/`.

Run the documented commands from `lcats/` with `PYTHONPATH="$PWD/src"` and the
project environment. The same explicit experiment format/lint commands above
cover both changed runners. Their offline tests are in
`tests/gettenberg_tests/qualification_evidence_test.py`; the real eight-case replay
is additional evidence, not a replacement for those tests. Source anchors are
coordinator annotations, not independent literary ground truth. Preserving those
eight spans does not accept all1,659 corpus outputs or editorial interpretations.

The current corpus replay records `chapter_assessment` from the same metadata-aware
policy used by actual publication. `new_rejection` describes body eligibility;
`metadata_rejection` remains separate, and `publication_rejection` combines them
in the live path's precedence. A changed body rejection is not necessarily a
changed publication outcome. Earlier reports retain their original meanings and
bytes; do not reinterpret their body-only counts as final publication eligibility.


## Publication-readiness qualification

The readiness policy separates preserved candidates from publication. From `lcats/`
with this worktree on `PYTHONPATH`, use the existing read-only catalog and decoded
UTF-8 cache. All output paths below must be new; input corpus/cache are never written.
No network requests are made. POSIX alarms bound census to600s and case checks to180s.
The census allows1–10000 canonical stories and the case runner1–100 source-bound cases;
shared gzip input reads are bounded to32MiB compressed/expanded. Operational failures
save `completed:false` partial JSON and exit nonzero; cleanup refusals are explicit
census rows. A completed census is measurement, not corpus acceptance.

```bash
python ../experiments/10_gettenberg_qualification/scripts/assess_cached_readiness.py \
  /tmp/catalog-cache /path/to/texts ../corpora/mass_quantities /tmp/new-readiness.json

python ../experiments/10_gettenberg_qualification/scripts/qualify_readiness_cases.py \
  /tmp/catalog-cache /path/to/texts /path/to/readiness-cases.json /tmp/new-cases.json \
  --review-decisions /path/to/review-decisions.json

python ../experiments/10_gettenberg_qualification/scripts/qualify_narrative_cases.py \
  /tmp/catalog-cache /path/to/texts \
  ../experiments/10_gettenberg_qualification/results/gettenberg-narrative-20261018/narrative-cases.json \
  /tmp/new-narratives.json --review-decisions /path/to/review-decisions.json
```

The case manifest binds each ID/decoded hash to an expected raw status; the runner
verifies actual temporary publication or preserved review candidates, provenance
and unchanged reuse. The narrative runner separately verifies every character
between independently selected opening/closing anchors. A raw needs_review case
is not a successful publication check without a valid explicit decision. Decisions
are reviewed input data, never generated automatically by these runners. Historical
decoded-cache identities do not authorize live original-byte publication.

The eight2026-10-20 decisions select whole paragraphs around the older anchors to
retain final dialogue punctuation.22579 explicitly keeps an interior illustration
label; it is not silently deleted or claimed absent. No decisions are provided for
the five disputed chapter cases.27612 also has genuine italic scene headings, so
its false counted evidence does not establish that it is unchaptered.

`qualify_installed.py` now also exercises withheld editorial content, explicit
reviewed selection/publication and runtime log guards outside a source checkout.
The historical `qualify_migration.py` equality runner still asserts old/new equality;
new provenance intentionally makes it fail, with results preserved as differences.
Do not reinterpret that failure as replacement readiness acceptance.

Changed runner checks (explicit experiment coverage):

```bash
python -m black --check --diff ../experiments/10_gettenberg_qualification/scripts
python -m ruff check ../experiments/10_gettenberg_qualification/scripts
python -m unittest tests.gettenberg_tests.qualification_evidence_test
```
