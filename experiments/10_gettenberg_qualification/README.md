# Gettenberg offline qualification

This archival experiment preserves the baseline and full-source qualification
behind WI-GETTENBERG-0001 through WI-GETTENBERG-0004. Decisions and execution
history remain in the [control-plane runlog](../../lcats/project/development/gettenberg-development-log.md).

## Narrow delivery candidate (2026-10-22)

The current product is constructed from migration baseline
`ed20e9c297bf5e50e1911b84722e53f5db3edee3`, with narrowly justified integration
repairs. The broader extraction/editorial runtime and its dedicated tests/docs
remain preserved at `b1254805c85bc34c0924e112732822c5e1436df5` on
`codex/gettenberg-qualification` (PR #524). Historical runners and results below
are retained for provenance; their original instructions describe that revision,
not blanket compatibility with the narrow product.

Current provider entry points are `measure_baseline.py`, `probe_legacy.py`,
`probe_parser.py`, `qualify_catalog.py`, `qualify_lifecycle.py`,
`qualify_migration.py`, `qualify_snapshot.py`, `qualify_index_counts.py` and
`reproduce_scope_facts.py`. The legacy probes still require their explicitly
recorded historical environments when executed. Import/help checks do not install
the old dependency. Other historical runners, including `qualify_installed.py`,
require their recorded combined checkout; do not use them to qualify this product.

Latest review: [delivery qualification and proposed acceptance](results/gettenberg-delivery-review-20261024/README.md).

Latest correction: [per-item refusal continuation and measured batch yield](results/gettenberg-refusal-continuation-20261023/README.md). Historical fail-fast measurements remain unchanged.

New candidate-specific runners:

- `qualify_narrow_yield.py CATALOG_CACHE TEXT_CACHE NEW_OUTPUT_JSON --product-ref COMMIT`
  measures actual cold/repeated batch publication and separate one-item potential.
  Use the exact committed product revision; historical default pins are not a
  substitute for current-candidate evidence. Decoded-source fixtures, no sockets,
  temporary outputs only, POSIX 1,200-second ceiling.
- `qualify_narrow_corpus.py CATALOG_CACHE TEXT_CACHE NEW_OUTPUT_JSON` runs the
  production cleanup and migration-baseline extraction on all frozen 1,659 inputs,
  deriving cleanup identity from actual catalog resource selection. Run from
  `lcats/` with absolute `PYTHONPATH="$PWD/src"`. Requires a committed product tree;
  existing caches are read-only, sockets forbidden, POSIX ceiling600s. It compares
  body evidence, not actual batch publication or final acceptance.
- `qualify_narrow_installed.py NEW_OUTPUT_JSON` runs in an isolated wheel environment,
  outside the checkout, with `PYTHONPATH` unset. It refuses an importable/installed
  legacy package and records actual fixture-based acquisition/gather outcomes.

- `qualify_narrow_cli.py NEW_OUTPUT_JSON` extends the isolated installed check with
  the actual CLI's success/refusal/success flow twice, byte-preserving output reuse,
  per-item logs and incomplete status 2. Same isolated-wheel invocation, fresh
  output requirement, socket guard and 120-second POSIX limit as the installed runner.

- `qualify_narrow_transfer.py REPOSITORY PRODUCT_REF WHEEL NEW_OUTPUT_JSON` verifies
  the entire wheel/product closure and the unchanged component identities supporting
  dated full-snapshot evidence. Run with project Python; it refuses output inside the
  repository or an existing report, and never imports product code or uses a network.

The candidate runners write fresh evidence only. See each `--help` for exact bounds and failure
semantics and the [construction manifest](../../lcats/project/development/gettenberg-narrow-delivery.md)
for scope and remaining qualification gates.

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
inputs. Supported provider runners expose `--help`; historical combined-runtime
runners require their recorded checkout even for imports. No runner below downloads
a catalog. Example:

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
No network requests are made. POSIX alarms bound census to 600s and case checks to 180s.
The census allows 1–10000 canonical stories and the case runner 1–100 source-bound cases;
shared gzip input reads are bounded to 32MiB compressed/expanded. Operational failures
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

The eight 2026-10-20 decisions select whole paragraphs around the older anchors to
retain final dialogue punctuation. 22579 explicitly keeps an interior illustration
label; it is not silently deleted or claimed absent. No decisions are provided for
the five disputed chapter cases. 27612 also has genuine italic scene headings, so
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

## Saved-candidate review workflow qualification

`qualify_review_workflow.py` reconstructs the candidate queue from the exact inputs
of a completed readiness census and exercises `gather-review` inspection, immutable
dispositions, inventory and explicit approval export. It cannot create new approvals
from finding patterns: pass already reviewed decisions and source-bound exclude/defer
annotations. Exported decisions must equal those inputs exactly. Preview checks
verify text/offset fidelity; they are not a new source review or corpus acceptance.

From `lcats/`, in the project environment with `PYTHONPATH="$PWD/src"`:

```bash
python ../experiments/10_gettenberg_qualification/scripts/qualify_review_workflow.py \
  /tmp/catalog-cache /path/to/texts ../corpora/mass_quantities \
  /path/to/census-final.json.gz /tmp/new-review-work /tmp/new-workflow-result.json \
  --approvals /path/to/review-decisions-derivation-bound.json \
  --annotations /path/to/reviewed-annotations.json
```

Both work and output must be new, outside collection roots, with existing parent
directories. Use the same catalog snapshot and immutable historical decoded gzip
cache as the census. Baseline JSON is bounded to 64 MiB expanded, annotation JSON to
1 MiB / 100 records, and supplied approvals to 8 MiB / 10,000 records. Source IDs
must be unique and match the census exactly (1–10,000). Shared gzip source reads are
bounded to 32 MiB compressed/expanded; product review limits also apply. A POSIX
600-second alarm and 6 GiB free-space preflight bound this local experiment. The
full local 1,659-source run fits these bounds; this is not a general-scale benchmark.

Annotation objects have `gutenberg_id`, `outcome` (`exclude`/`defer`), `reviewer`,
`rationale`, and the candidate's `source_identity_sha256`, `candidate_sha256`, and
`assessment_sha256`. Duplicate/unknown fields, repeated IDs or changed identities
fail. Historical decoded-input decisions are not valid approvals for original-byte
live acquisition. Exclude/defer remain intent records, not collection edits.

No source downloads, catalog refresh, canonical corpus writes or story publication
occur. A temporary queue retains full candidates; archive the compact result,
explicit input annotations and source hashes rather than duplicating story bodies.
Operational failures exit nonzero and preserve a partial `completed:false` JSON;
preflight argument errors create no output. A completed workflow is not acceptance
of the unresolved historical body differences. Existing result paths are never
reused. The signal handler is restored after execution.

```bash
python -m unittest tests.gettenberg_tests.review_workflow_evidence_test
python -m black --check --diff ../experiments/10_gettenberg_qualification/scripts
python -m ruff check ../experiments/10_gettenberg_qualification/scripts
```

`qualify_installed.py` also runs the installed `gather-review` entry point for
list/show/approve/exclude/defer/export, checks conflicting intent remains visible,
and feeds the explicit exported approval into actual temporary publication.


## Source-disposition tranche reconciliation

`reconcile_review_tranche.py` links explicit review judgments to the immutable
readiness census, historical body comparison, exact candidate and disposition,
compressed/decoded source identities, canonical story bytes and source excerpts.
It checks evidence consistency; it cannot establish literary completeness or
authenticate a reviewer. The reviewer must inspect the source before supplying
inputs. Positive structural evidence can justify exclusion without claiming a
full-narrative review. Approval requires review of the entire selected narrative.

Run from `lcats/` in the project environment, with `PYTHONPATH="$PWD/src"`:

```bash
python ../experiments/10_gettenberg_qualification/scripts/reconcile_review_tranche.py \
  /path/to/census-final.json.gz /path/to/full-corpus-final.json.gz \
  /path/to/reviews.json /tmp/review-work/candidates /path/to/dispositions \
  /path/to/texts ../corpora/mass_quantities /tmp/new-tranche-result.json
python -m unittest tests.gettenberg_tests.disposition_tranche_evidence_test
python -m black --check --diff ../experiments/10_gettenberg_qualification/scripts/reconcile_review_tranche.py
python -m ruff check ../experiments/10_gettenberg_qualification/scripts/reconcile_review_tranche.py
```

`reviews.json` is a list of 1–100 explicit records: `id`, `candidate` and
`disposition` basenames, nonempty `review_scope` and `historical_rationale`, and
`source_anchors` (1–50 objects with `start`, `end`, `text`). Source offsets are
Unicode positions in the exact decompressed UTF-8 cache, preserving CRLF. Candidate
selection offsets have a different basis: normalized candidate Unicode text.
Each anchor is at most 4,000 characters. Candidate/disposition loaders verify the
complete identity chain; approvals are re-derived from the exact candidate.
Use a completed census and comparison with the same unique 1–10,000 source IDs.
Every comparison row must explicitly be `compared` with boolean `body_equal`, or
`cleanup_refused` with null `body_equal` and a matching census refusal. Population
source/corpus identities and any supplied summary/totals must also agree.
JSON inputs are bounded to 64 MiB expanded and gzip source inputs to 32 MiB; a POSIX
180-second alarm bounds the run. This is a trusted local experiment, not an
untrusted upload service. Original source/corpus files are read only. No network,
catalog access, disposition creation, story publication or corpus modification.
Output must be new and outside the collection. Runtime failures preserve a partial
`completed:false` report and exit nonzero; preflight failure produces no output.

The ledger lists every population ID, changed-body ID, reviewed ID, disposition-
covered changed ID, and remaining changed ID. Only approve/exclude count as covered
**by this named tranche**; defer stays unresolved. This does not combine earlier
tranches, adjudicate conflicting records, or accept the corpus. Exclusion is audit
intent only: current gathering still withholds the candidate until collection
policy changes separately. Sampling never accepts unreviewed population members.
For approvals, the report additionally checks whether the selected body is an exact
prefix of the retained body and records the remaining suffix when short enough.

Replay actual gather outcomes separately with `qualify_readiness_cases.py` and the
exported approvals. Record source-review rationale and evidence alongside results.
The first tranche is in `results/gettenberg-dispositions-20261020/`.


## Batch review qualification

`qualify_review_batch.py` measures every immutable input and reconciles existing
review intents before proposing narrowly qualified decisions. Run from `lcats/`
with the project Python and `PYTHONPATH="$PWD/src"`:

```bash
python ../experiments/10_gettenberg_qualification/scripts/qualify_review_batch.py \
  CENSUS_JSON_GZ COMPARISON_JSON_GZ CANDIDATES DISPOSITIONS TEXT_CACHE \
  COLLECTION NEW_OUTPUT_DIRECTORY \
  --prior-reviews SOURCE_REVIEWS_JSON --prior-dispositions SOURCE_DISPOSITIONS
```

The census/comparison are the completed full-population baseline; candidate and
cumulative disposition directories must match that generation. `SOURCE_REVIEWS_JSON`
is the explicit source-anchor/rationale input accepted by `reconcile_review_tranche.py`
(or an explicit empty list when no prior tranche exists). Original files are read-only.
The runner validates every source/corpus hash, exact queue/population sets, recorded
normalization and existing disposition bindings. Sidecars are not corpus members.

Outputs are `summary.json`, losslessly compressed `ledger.json.gz`, and
`proposed-decisions.json`. By default, proposed rule decisions do not enter resolved
coverage. After rule qualification and review, use a fresh output directory and
`--record-qualified` to record eligible immutable dispositions and `approvals.json`.
The rule must match, the selected text must pass stricter readiness checks, its
existing normalization must exactly reproduce the historical baseline, and no
prior intent may exist. Other differences remain unresolved; equality alone is
not approval. The ledger keeps raw selected/removal hashes and normalization
provenance separately. Every corpus input remains visible, including refusals.

No network, catalog rebuild or story publication. Existing bounded candidate/source
readers apply; at most 10,000 population rows, 6 GiB free minimum and a 600-second POSIX
alarm. Partial failures preserve `completed:false` and exit nonzero. Never consume
a partial export as acceptance evidence. Existing outputs are refused.

Smoke tests and explicit experiment checks:

```bash
python -m unittest tests.gatherers_tests.review_rules_test tests.gettenberg_tests.review_batch_evidence_test tests.gettenberg_tests.disposition_tranche_evidence_test
python -m black --check ../experiments/10_gettenberg_qualification/scripts/qualify_review_batch.py ../experiments/10_gettenberg_qualification/scripts/reconcile_review_tranche.py ../experiments/10_gettenberg_qualification/scripts/qualify_installed.py
python -m ruff check --no-cache ../experiments/10_gettenberg_qualification/scripts/qualify_review_batch.py ../experiments/10_gettenberg_qualification/scripts/reconcile_review_tranche.py ../experiments/10_gettenberg_qualification/scripts/qualify_installed.py
```


### Ordered-span qualification

The same batch invocation accepts `--rule ordered` to measure the approved interior
notice extension; omit it to retain the historical boundary-rule behavior. Use a
new output directory and cumulative dispositions including previous batch approvals.
The ledger records exact ordered ranges, each removed notice and its hash, current
assessment, normalization, prior intent and historical reconciliation. Summary
`rule_transformation_qualified` counts safe transformations independently from
`rule_readiness_eligible` and recorded historical resolutions. No general blurb
classification, new network access or corpus mutation is performed.

V2 explicit approvals use the same optional `--record-qualified` gate. A dry run's
unrecorded proposals remain unresolved, and no output is accepted merely to increase
coverage. `reconcile_review_tranche.py` validates both v1/v2 source-reviewed records.
The installed smoke exercises v2 CLI recording/export, batch gathering, noncontiguous
narrative reconstruction and exact separately preserved blurb metadata.

```bash
scripts/format --check --diff \
  ../experiments/10_gettenberg_qualification/scripts/qualify_review_batch.py \
  ../experiments/10_gettenberg_qualification/scripts/reconcile_review_tranche.py \
  ../experiments/10_gettenberg_qualification/scripts/qualify_installed.py
scripts/lint \
  ../experiments/10_gettenberg_qualification/scripts/qualify_review_batch.py \
  ../experiments/10_gettenberg_qualification/scripts/reconcile_review_tranche.py \
  ../experiments/10_gettenberg_qualification/scripts/qualify_installed.py
python -m unittest tests.gatherers_tests.ordered_review_test \
  tests.gettenberg_tests.review_batch_evidence_test \
  tests.gettenberg_tests.disposition_tranche_evidence_test
```


### Source-grounded historical reconciliation

The batch runner now supports `--historical-acceptance source-grounded` alongside
`--rule ordered`. The default remains `baseline`. Run the existing batch invocation
with these flags into a new output directory to measure the whole immutable
population. This composes the qualified notice selection with the finite
`source-preserved-typography-v1` explanation: complete source separator paragraphs
and exterior ASCII whitespace account for the entire residual difference. Nothing
is edited for publication. Different normalization or an unavailable baseline
remains explicitly unresolved. This is not a general diff suppressor.

The ledger's `historical_evidence` records exact comparison ranges and hashes even
when residual text remains. `residual_groups` partitions unresolved changed IDs,
including unrecorded proposals in measurement mode. `historical_explanation_complete`
counts explanations across all candidate rows, independently of publication and
recorded resolution. Additional boundary text is a diagnostic shape, not a blurb
label. Non-candidate/refused inputs remain visible in population accounting.

Inspect the full newly proposed cohort before recording. Preserve known exceptions
as explicit defer/exclude dispositions in the cumulative directory and include
source-review evidence through the existing `--prior-reviews` mechanism. For each
remaining non-equal proposed approval, prepare a JSON list entry with `id`,
`candidate_record_sha256`, `selected_sha256`, `historical_sha256`, nonempty
`reviewer` and `rationale`, and `candidate_anchors` (1–50 exact `{start,end,text}`
excerpts, each at most4,000 characters, in the original candidate Unicode domain).
The packet must cover exactly the new non-equal approvals. Stale hashes, wrong
anchors, missing/extra/duplicate IDs and missing attribution fail closed. The
review statement records attributable judgment; matching excerpts do not certify
literary judgment or authenticate a human. Independently review the packet.

After qualification/review, repeat into another fresh directory with
`--record-qualified --cohort-review COHORT_JSON`. The ledger embeds each validated
cohort record and its hash. Approval export contains exact source selections, never
comparison projections. Carry the new dispositions into subsequent cumulative
runs; source-grounded prior approvals are reconciled again against the verified
baseline without losing their resolution. Defer/conflict intent is never replaced.

Additional smoke coverage, from `lcats/` with project Python/PYTHONPATH:

```bash
python -m unittest tests.gatherers_tests.historical_review_test tests.gettenberg_tests.review_batch_evidence_test
```

Use the explicit format/lint commands above for the changed batch runner. Same
network prohibition,600-second POSIX alarm,6GiB free minimum and exclusive-output
semantics apply. The reusable helper bounds each text at4million characters; an
oversized input fails the run, never silently disappears from coverage. Historical
source cache attribution remains decoded/re-encoded UTF-8, not original HTTP bytes.

The ordered-publication regression also exercises both real publication evidence
runners after JSON serialization. Explicitly check those changed paths:

```bash
scripts/format --check --diff ../experiments/10_gettenberg_qualification/scripts/qualify_readiness_cases.py ../experiments/10_gettenberg_qualification/scripts/qualify_narrative_cases.py
scripts/lint ../experiments/10_gettenberg_qualification/scripts/qualify_readiness_cases.py ../experiments/10_gettenberg_qualification/scripts/qualify_narrative_cases.py
```


### Boundary residual census and terminal-notice qualification

`group_boundary_cases.py` groups unresolved `additional_boundary_text` rows from
an existing completed cumulative ledger. Labels are lexical diagnostics: an
underscore prefix is not a proven blurb, and a transcriber substring can be prose.
The runner rechecks candidate, cache and corpus identities, reruns the prior ordered
notice rule, and recomputes each historical comparison before grouping. Comparison
projection offsets are never used as source offsets.

From `lcats/`, with the project Python and `PYTHONPATH="$PWD/src"`:

```bash
python ../experiments/10_gettenberg_qualification/scripts/group_boundary_cases.py LEDGER_JSON_GZ CANDIDATE_QUEUE COLLECTION TEXT_CACHE NEW_OUTPUT
python -m unittest tests.gatherers_tests.trailing_notice_test tests.gettenberg_tests.boundary_groups_evidence_test
scripts/format --check --diff ../experiments/10_gettenberg_qualification/scripts/group_boundary_cases.py
scripts/lint ../experiments/10_gettenberg_qualification/scripts/group_boundary_cases.py
```

Outputs are `summary.json` and `groups.json.gz`, containing every boundary input's
full prefix/suffix, identity bindings, optional rule evidence in original candidate
coordinates and the residual historical explanation. Input sources are read-only
legacy decoded/re-encoded UTF-8 cache files, not authenticated original HTTP bytes.
No catalog or network is used; socket access is denied. POSIX 600-second alarm,
10,000-row/64MiB expanded ledger limit, 32MiB source/corpus limits,6GiB free minimum.
Existing output directories are refused; failures preserve `completed:false`.
An arbitrary process kill can prevent the final checkpoint write.

The opt-in pure helper `review_rules.propose_trailing_publication_notice(body)`
recognizes a complete unbracketed terminal transcriber note, at most 1,000 Unicode
characters, starting after a blank line and following nonempty retained text.
Grammar: finite known magazine names, one month/season and a 1900–1999 year,
exact copyright-research sentence, optionally the exact spelling/typography
correction sentence. Matching underscores around the magazine name, case and
whitespace variation are accepted for recognition only. Every retained character
and the exact omitted note are hash-bound; surrounding narrative is never rewritten.
Unknown publications, extra sentences, interior notes, unmatched underscores,
multi-month issues, standalone notes and post-note narrative are exceptions.

This helper does not change default extraction, the existing bracketed-notice
rule, the review decision schema, or cumulative dispositions. Transformation
qualification is distinct from historical explanation and story approval. Even a
complete explanation requires readiness checks and attributable source review
before an explicit decision can be recorded. Existing approve/defer/exclude intent
is reported unchanged. The sprint archive is
[boundary groups](results/gettenberg-boundary-20261022/README.md).


### Record reviewed terminal-note decisions

The existing `qualify_review_batch.py` accepts `--rule terminal`, composing ordered
bracketed and terminal unbracketed publication notes. Its measurement/recording,
input identity, offline, exclusive-output, time and disk limits remain unchanged.
Use the same seven positional arguments and cumulative review inputs documented
above; no additional executable runner is introduced. Record only after source
inspection, preserving known exceptions in cumulative dispositions and reviews.

```bash
python ../experiments/10_gettenberg_qualification/scripts/qualify_review_batch.py CENSUS COMPARISON QUEUE CUMULATIVE_DISPOSITIONS TEXT_CACHE COLLECTION NEW_OUTPUT --prior-reviews CUMULATIVE_REVIEWS --prior-dispositions CUMULATIVE_DISPOSITIONS --rule terminal --historical-acceptance source-grounded --record-qualified --cohort-review COHORT_JSON
python -m unittest tests.gatherers_tests.trailing_notice_test tests.gettenberg_tests.terminal_batch_evidence_test
scripts/format --check --diff ../experiments/10_gettenberg_qualification/scripts/qualify_review_batch.py
scripts/lint ../experiments/10_gettenberg_qualification/scripts/qualify_review_batch.py
```

The cohort packet format is unchanged, but terminal mode requires it for **all**
new proposals, including exact baseline equality under either historical mode.
An empty exact cohort is allowed only when there are no proposals to approve.
The batch runner never infers editorial roles from an unchanged old body.

The [terminal-decision run](results/gettenberg-terminal-20261022/README.md) inspects
all 25 history-complete inputs from the boundary census. Every one retains separate
teaser-like opening material; 13 also retain recognized editorial labels/readiness
findings. Twelve would pass mechanical gates without this source review. All 25
are explicitly deferred; no new approval is warranted under the terminal-note rule.
The nonempty success path is verified end-to-end on authored fixtures, including
source review, immutable v2 recording/export, actual temporary publication and
cumulative replay. Real cached replay verifies all 25 are withheld with their full
candidate text retained. Default modes and existing dispositions remain unchanged.


## Reviewed promotional-preface evidence

`qualify_editorial_evidence.py` measures a finite catalogue of independently reviewed
promotional spans. It reuses full-population/cumulative verification and the existing
v2 partition/metadata mechanism. It never records decisions, exports approvals,
fetches sources, or publishes stories. Existing default batch modes are unchanged.
The library verifier lives in `lcats.gatherers.editorial_evidence` and is unit tested.

From `lcats/`, in the project environment with `PYTHONPATH="$PWD/src"`:

```bash
python ../experiments/10_gettenberg_qualification/scripts/qualify_editorial_evidence.py \
  CENSUS.json.gz COMPARISON.json.gz QUEUE CUMULATIVE_DISPOSITIONS \
  TEXT_CACHE COLLECTION CUMULATIVE_SOURCE_REVIEWS.json \
  REVIEWED_PREFACES.json NEW_OUTPUT_DIRECTORY
python -m black --check --diff ../experiments/10_gettenberg_qualification/scripts/qualify_editorial_evidence.py
python -m ruff check --no-cache ../experiments/10_gettenberg_qualification/scripts/qualify_editorial_evidence.py
python -m unittest tests.gatherers_tests.editorial_evidence_test tests.gettenberg_tests.editorial_evidence_runner_test
```

Input population, queue and cumulative intent must match the earlier qualification
artifacts. Missing/stale evidence fails without network fallback. Read-only historical
cache inputs are decoded/re-encoded UTF-8, not original HTTP representations. At most
10,000 population rows and 256 explicit span reviews; bounded JSON/source readers;
POSIX 600-second alarm; at least 6GiB free. Output is exclusive and cannot be under
an input directory. Failure writes `summary.json` with `completed:false`; partial
output is not acceptance evidence. Complete output is a summary plus a lossless
compressed ledger. Successful execution never changes cumulative disposition counts.

The first [archived qualification](results/gettenberg-editorial-20261022/README.md)
finds two delimited opening labels in 1,640 candidates and independently supports
promotional roles for both (63638, 73988). Both still have readiness and historical
blockers. Mixed publisher preface 42664 is excluded; all 25 previous deferrals remain.
A valid span-role packet is neither a semantic classifier nor a story approval.
Keep the bounded discovery coverage separate from the manually reviewed catalogue.


## Scope audit: narrow terminal-notice experiment

The [2026-10-22 investigation](results/gettenberg-terminal-notice-audit-20261022/README.md)
records the fallback trace, full 1,659-input experiment-only grammar comparison, two
explicit literal counterfactuals, boundary tests and independent review. It changes no
production cleanup, gather policy or corpus approval. Use its documented commands and
pinned environment; its measurements do not qualify a future delivery candidate.


## Numeric-marker notice follow-up

The [numeric-marker investigation](results/gettenberg-numeric-notice-audit-20261022/README.md)
adds explicit source/catalog/title corroboration to the prior experiment. It reuses
pinned baseline evidence, freshly extracts all accepted inputs, preserves title
mismatches, and records scope/qualification limits. No production policy is changed.


## Scope-audit landing repairs

The [facts reproduction procedure](scope-facts-reproduction.md) regenerates the
derivable audit calculations without legacy libraries or network access. Original
archived measurements remain immutable. Current diagnostic entry points are safe to
import and expose help without gutenbergpy; the historical cleaner is required only
when explicitly running a legacy comparison. The causal replay now pins every Python
product source and validates all loaded module origins, including late imports.

The numeric runner retains its original evidence revision and explicitly binds the
reviewed helper hash after the optional legacy import moved inside the measurement
entry point. This import-only repair does not alter cleanup/extraction calculations;
the landing verification records a fresh population comparison separately.

## Narrow candidate causal accounting and operational yield

The [2026-10-23 causal/yield checkpoint](results/gettenberg-causal-yield-20261023/README.md)
accounts for the remaining 67 body differences and 13 refusals with production fixed.
It distinguishes actual fail-fast batch publication from isolated one-item yield,
records source provenance limits, and presents finite contract decisions for PR #530.
Use the documented runners and explicit experiment tests there; this evidence does
not approve editorial content, main promotion or canonical corpus publication.

### HTTP 404 continuation qualification

Run `scripts/qualify_narrow_cli.py NEW_OUTPUT_JSON --http-404` with the freshly
installed qualification wheel's Python, from outside the checkout and with
PYTHONPATH unset. It uses the sibling installed helper; no test modules or
Gutenberg network are required. A fresh disposable catalog/resource cache and
synthetic HTTP boundary exercise actual CLI success/404/success followed by
reuse/404/reuse, checking status 2, exact request order, missing-source cache
safety, ordered logs and unchanged output hashes. Real sockets are forbidden;
POSIX alarm is 120 seconds. Output must be new and outside the installed package.
The default runner scenario still verifies cleanup-refusal continuation. Neither
scenario measures live availability or full-corpus yield.

### Live ebook 1367 reproduction

`reproduce_1367.py` reads one existing catalog record read-only and builds a tiny
throwaway catalog. It invokes the real CLI with empty output/source-cache trees
and permits at most one real request to the selected default-mirror URL. It
fingerprints an existing story before/after without reusing or editing it. No
full metadata download, shared-cache write, fallback probe or corpus regeneration.
POSIX-only (120-second alarm); the evidence directory must be new. A completed
experiment can record an unsuccessful gathering result; inspect its CLI status.

From `lcats/` with the project environment and `PYTHONPATH=src`:

```sh
python ../experiments/10_gettenberg_qualification/scripts/reproduce_1367.py \
  --catalog /absolute/path/to/catalog.sqlite \
  --existing-story /absolute/path/to/findelkind__ouida/story.json \
  --output /tmp/new-1367-evidence
```

The output retains exact RDF, JSONL events and a JSON report; temporary runtime
state is removed. This is a time-specific observation, not an automated test of
Gutenberg's uptime. See [the recorded result](results/gettenberg-reporting-20261026/README.md).
