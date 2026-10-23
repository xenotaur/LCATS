# Narrow candidate causal accounting and gather yield — 2026-10-23

This is evidence for [PR #530](https://github.com/xenotaur/LCATS/pull/530), not
release acceptance or authorization to change production behavior. Runtime Python
and package data remain those of product `91f1b422`; the run starts from candidate
`95ad5afd`. The [approved Q1–Q8 gates](../../../../lcats/project/development/gettenberg-scope-causality-audit.md#approved-qualification-criteria--adopted-2026-10-22)
and [candidate manifest](../../../../lcats/project/development/gettenberg-narrow-delivery.md)
remain governing. Historical results and the broader PR #524 are preserved.

## What was measured

`causal-ledger.json.gz` accounts for all **67 body differences and 13 refusals**
from the prior 1,659-input census. Both cleaner paths use identical decoded source,
metadata, unchanged parser and normalization. All 67 legacy-control body hashes
reproduce; a separate comparison confirms these also equal the checked-in corpus
bodies. The 1,579 equal non-refused cases retain their prior full-census evidence.
This is a controlled cleaner substitution, not an old/new live download replay.

| Mechanism among the 67 differences | Count | Meaning |
|---|---:|---|
| Entire old body plus terminal notice only | 55 | Exact old body preserved; retained text is still boilerplate, not automatically acceptable. |
| Entire old body plus notice and preceding content | 9 | Six transcriber notes, one author signature, one illustration, one final narrative paragraph. |
| Leading newline only | 1 | ID 32655; bodies otherwise identical. |
| Source prefix restored | 1 | ID 70645, Sam Bass: 16,465 characters restored before the entire old body. |
| Frontmatter/tail interaction | 1 | ID 42640: 166 characters of frontmatter/title removed; 230 characters of colophon/notice added; central narrative retained. |

There are zero body-eligibility changes among these 67; 66 preserve the entire old
body verbatim. Moving only the observed legacy footer boundary into the candidate
path reproduces the old body in all 65 applicable probes. **That does not establish
that this would be a safe repair.** For ID 23552, it removes a source-backed
387-character final narrative paragraph again. An independent probe of unchanged
`fix_body`, using an authored sentinel plus that exact paragraph and neither
cleaner, reproduces the loss: the paragraph matches the title. This is controlled
evidence of a separate gather defect, not an inference from the code's age.

The 13 refusals have explicit source evidence: six physically wrapped markers,
three interior `*END*` candidates, three unsupported first-line headers, and one
mismatched truncated end identifier. None was bypassed or silently accepted.
Every residual has causal accounting; delivery/editorial acceptance remains false.

## Actual gathering, with an explicit source boundary

`gather-yield.json.gz` exercises the real source adapter, resource cache, strict
decoder, cleanup, parser, normalization, output publisher and run log. It uses the
**configured order restricted to the frozen 1,659 IDs**. The complete configured
collection contains 5,492 IDs; the other 3,833 were not executed here.

| Invocation | Published | Reused | Refused | Unattempted |
|---|---:|---:|---:|---:|
| Cold cohort batch | 41 | 0 | 1 | 1,617 |
| Repeat of that batch | 0 | 41 | 1 | 1,617 |
| Separate one-item calls, fresh shared output collection | 1,646 | 0 | 13 | 0 |
| Reuse of all successful outputs with an empty source cache | 0 | 1,646 | 0 | 0 |

The first refusal is ID 3699. The batch raises `cleanup_refused`, retains its 41
previous outputs, records an abort and does not progress further on repetition.
All 1,659 inputs pass current metadata eligibility; the isolated census has no
metadata/body skips or other operational errors, 1,646 unique outputs, no owner
collisions, and no body differences from the prior candidate census. The 13 refused
IDs exactly match the causal ledger. Empty-cache reuse preserves existing JSON.
Publication means the actual product wrote a file, not editorial approval.

The one-item controller is **experiment isolation**, not a new product continuation
policy. Its 1,646 publications (99.2% of this cohort) cannot be advertised as normal
batch yield: the cold batch reaches only 41 (2.5%). Nor are these full configured
collection or original-network-acquisition yield measurements.

Both supplied existing cache roots have zero matching verified resource receipts.
The historical sources are already decoded UTF-8 gzip files. We therefore seed a
disposable cache through actual `ResourceStore.fetch` using an explicit
`decoded-source-fixture.invalid` transport response. Receipts identify those fixture
bytes, not original Gutenberg responses. The transport clock advances virtually
only during seeding; acquisition latency/pacing is not measured. Actual gathering
then runs offline with the normal clock. Socket creation is denied. Source hashes
are rechecked; temporary outputs/cache/logs are removed on exit. No Gutenberg
requests, persistent cache writes or canonical corpus publication occur.

## Decisions this evidence supports

1. **Address batch usability before declaring delivery.** Recommend a separately
   approved, narrow collection-boundary policy for explicit per-input refusals,
   retaining strict source cleanup and visible incomplete-run reporting. The exact
   return/exit/log contract needs a decision and regression tests; do not silently
   swallow errors or apply continuation to every exception. Changing marker grammar
   is a distinct alternative, with a different risk of removing narrative.
2. **Replace the unexplained residual queue with finite dispositions.** The 55
   notice-only cases can receive one explicit body-contract decision backed by all
   55 input records: accept documented conservative retention, or require a narrowly
   qualified repair. The whitespace-only case and source restoration have separate
   evidence. The nine richer suffixes and mixed frontmatter case need their own
   bounded dispositions; they must not inherit a notice-only approval.
3. **Keep the independently reproduced gather defect separate.** Preserve ID 23552
   as a regression anchor and a follow-up for reconciliation with Kenny. Any future
   cleanup repair must demonstrate it does not recreate this loss. Do not use exact
   historical equality as the universal success criterion.
4. **Keep the evidence boundary and final gates explicit.** This run accounts for
   the frozen residuals and measures downstream gathering. It does not establish
   missing historical wire fidelity, full configured selection, Q1 evidence transfer,
   final acceptance or human main promotion. The current fail-fast effect is a known
   Q5 blocker, not an unknown cause or an excuse to reopen broad editorial redesign.

No decision above has been applied to production. This report recommends the next
bounded decision; it does not authorize one automatically.

## Validation, repairs and reproduction

Canonical LCATS tests: **2,955 pass**. Four yield-observer tests exercise actual
fixture gathering: abort/prefix preservation/reuse, metadata skip, filename
collision, and offline source-cache error. Fourteen causal helper tests cover exact
change intervals, grouping, source-line offsets and bounded counterfactual behavior.
Explicit experiment lint and independent review are recorded alongside this file.

An authored collision test initially failed: a before-batch snapshot counted a
same-path reuse as another publication. The observer now snapshots immediately
before each yielded input. The real cohort has no such collisions. Independent
review then found missing JSON/helper stability guards in the durable yield runner;
both packaged JSON inputs and measurement helpers are now pinned at start/end.
Earlier yield reports are retained as **superseded measurements**, not qualification.
A sandbox-local Ruff cache write failed; explicit lint was rerun with its cache in
`/tmp`. No test failure was suppressed and no production change was needed.

From `lcats/`, use the project environment and absolute worktree imports:

```bash
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/src"
python ../experiments/10_gettenberg_qualification/scripts/qualify_narrow_causality.py \
  /path/to/catalog-cache /path/to/decoded-text-cache /tmp/NEW-causal.json
python ../experiments/10_gettenberg_qualification/scripts/qualify_narrow_yield.py \
  /path/to/catalog-cache /path/to/decoded-text-cache /tmp/NEW-yield.json
python -m unittest discover \
  -s ../experiments/10_gettenberg_qualification/scripts -p '*_test.py'
scripts/lint ../experiments/10_gettenberg_qualification/scripts/qualify_narrow_causality.py \
  ../experiments/10_gettenberg_qualification/scripts/qualify_narrow_causality_test.py \
  ../experiments/10_gettenberg_qualification/scripts/qualify_narrow_yield.py \
  ../experiments/10_gettenberg_qualification/scripts/narrow_yield_test.py
```

The causal comparator requires the already-installed SHA-pinned historical
`gutenbergpy` cleaner in the experiment environment only. The yield runner does not
import it. Neither changes package dependencies. POSIX alarms bound causal/yield
runs to 900/1,200 seconds; gzip input expansion is capped at 32 MiB. Existing output
paths, changed pins, missing inputs or failed guards produce no completed report.
Per-input data, source/runner identities, timestamps, events and limitations are in
the JSON reports; `sha256.json` inventories archived evidence. Prior construction
wheel/source closure is preserved and no new installed-wheel claim is made here.

Independent review reports no unresolved P0–P2. Its separate 53-second causal
replay reproduces every row. A P3 experiment-only limitation is documented: if a
caller imports `main()` and catches an early data-guard exception, the yield
command's alarm cleanup is not guaranteed. Supported standalone CLI invocation
exits on that error; no product or completed-measurement behavior is affected.
Do not reuse this entry point as an in-process library API without that cleanup.
