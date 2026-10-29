# Source-grounded historical reconciliation — 2026-10-22

WI-GETTENBERG-0010 / PR524, continuation from e368255c. The human approved the
source-grounded historical-acceptance path with exceptions unresolved and a first
run within one hour. Start00:00:59 UTC, hard stop01:00:59. Feature work stopped at
38% weekly account usage; substantive work stopped at40% (36% launch). Account
usage is shared, not task-exclusive. No integration, main promotion or corpus write.

## Outcome

| Measurement | Result |
|---|---:|
| Immutable source/corpus inputs |1,659|
| Historically changed bodies |1,642|
| Historical resolutions, before → after |8 →14|
| Historical differences unresolved |1,628|
| New explicit approvals |3|
| Existing approvals newly explained |3|
| New explicit deferrals |8|
| Final full cumulative replay |29.090 seconds|

New approvals:69213,69257,70217. Prior approvals newly reconciled:23148,32655,35401.
The exact whole-text proofs retain26 source scene separators in the new cohort
and11 in the prior cohort. Existing eight resolutions remain intact. The final
[ledger](ledger.json.gz) rechecks cumulative decisions; [recording ledger](recorded-ledger.json.gz)
binds each new approval to its explicit source-bound [cohort review](cohort-review.json).
The [cohort inspection](cohort-inspection.json) covers all11 initially proposed inputs,
not a representative sample. Eight teaser-like openings already present in old
bodies are deferred:32484,50796,50800,50892,51258,51589,51597,51713.

Final candidate inventory:1,610 unreviewed,13 approve,7 exclude,10 defer;19 population
members have no candidate. Historical resolution is a separate count. The remaining
18 typography-explained candidate bodies still lack a complete approval path; the
method does not convert explanation alone into publication. No general blurb
classification or claim of complete literary reading is made.

## What scales next

[Coverage](coverage.json) partitions all1,628 unresolved changed inputs:
1,477 additional boundary text;97 mixed/unclassified;18 explained typography but
unresolved;32 normalization requiring review;2 no candidate;2 unavailable historical
baseline bodies. Of the1,477 boundary cases,1,013 have prefix only,408 both ends,
and56 suffix only;673 already have a qualified notice removal and804 do not.
These are exact diagnostic comparison relationships, not1,477 confirmed blurbs.
The next high-yield task is to classify these boundary groups and qualify bounded
source/metadata-supported rules, preserving ambiguous framing and all exceptions.

## Proof and qualification

The comparison-only `source-preserved-typography-v1` projection ignores only exact
interior five-star paragraphs and exterior ASCII space/tab/LF. It reproduces a
bounded part of the old parser's omission behavior without using its broader
substring-based paragraph deletion. See parser.py at335855c04cd7ba936815d2635969d94fdd278c71,
`body_of_text`'s separator block. Every other character must match exactly. Both
input hashes, every comparison range/text/hash and projection hashes are retained.
The actual published selection preserves source separators. Current normalization
must leave selected text unchanged, and stored body must match historical hash.

A verified historical relationship cannot establish that existing opening prose
is desirable. Non-equal new approvals therefore require a separate reviewed cohort
packet with exact source selection/baseline identities, excerpts and attribution.
Cumulative defer/exclude/conflict decisions remain protected. Default recording mode
still requires baseline equality; the new path is explicit and independently reviewed.

3,091 canonical tests pass in103.885 seconds. Package and all four changed experiment
runners pass format/lint. One focused regression reproduces both real publication
runners' tuple/list provenance comparison failures before repair and passes after
complete canonical-JSON identity comparison. The [failed replay](publication-before-repair.json)
and raw logs remain historical evidence. [Final publication](publication-final.json)
publishes six reviewed cases in disposable outputs and withholds all eight deferred
cases, preserving candidates and existing-output bytes. No canonical output changes.

[Independent review](independent-review.json) repeated the full1,659-input evaluation
and inspected all11 cohort cases plus the three earlier approvals. [Repair recheck](independent-recheck.json)
independently reproduces the old runner failures and verifies the fix. Both report
no blocking findings. [Coordinator re-verification](coordinator-reverification.json)
reconstructs every comparison projection in the six newly reconciled cases.

A fresh isolated build/install passes installed smoke and pip check with no
`gutenbergpy`. All173 Python modules and2 JSON resources match source/wheel/install
exactly; [wheel evidence](wheel.json) binds every file. The dirty SCM version names
the starting commit; hashes bind actual qualified content. Initial no-isolation
build failed because development packaging lacked `packaging.licenses`; isolated
build succeeded without changing the development environment. PyPI was used for
build/install dependencies; no Gutenberg requests. Replays forbid sockets.
[Preservation](preservation-final.json) rechecks all original identities after tests.

## Replay

Use the [documented batch runner](../../README.md#source-grounded-historical-reconciliation)
with the original readiness census/comparison, regenerated exact candidate queue,
read-only decoded source cache and retained corpus. Materialize the cumulative
intent directory by copying each referenced file in [disposition manifest](disposition-manifest.json)
under its `filename`, verifying its hash. Existing archived records are referenced;
ten earlier temporary intent records are now preserved byte-for-byte under
`inherited-dispositions/`, and eleven new records under `new-dispositions/`.
No historical disposition is rewritten.

For the recording replay, include only launch records plus the eight new deferrals,
use `cumulative-reviews.json` for prior source evidence, `--rule ordered
--historical-acceptance source-grounded --record-qualified --cohort-review
cohort-review.json`, and a new output directory. For final cumulative replay include
all30 manifest records and omit recording/cohort flags. It yields no new proposals
and preserves14 historical resolutions. Keep full source/corpus inputs outside this
archive; it stores bounded excerpts and identity/evidence, not another source corpus.

The original queue/cache paths in logs identify the measured environment; they are
not an alternative artifact authority. See validation.json for exact limits/failures.
This tranche does not accept the corpus, satisfy all WI0010 gates, integrate PR524,
promote main or perform terminal native closeout.
