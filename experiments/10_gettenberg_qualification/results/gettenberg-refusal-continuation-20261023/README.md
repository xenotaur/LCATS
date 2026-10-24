# Narrow refusal continuation — 2026-10-23

Human-authorized replacement integration correction on PR #530. Product revision:
`8c9441ddf707f4bdcd11afc4e9c4126d0976b8bc`. This is evidence for batch control flow,
not delivery acceptance, editorial approval or a repair of the refused sources.

## What was corrected

The earlier scope split at `91f1b422` removed per-item cleanup refusal continuation
already present in product code at `b1254805` (gatherer.py:91–108), alongside the
separated editorial result system. Logging and atomic writes survived, but the
batch aborted after its first refusal. This was an over-broad separation, not only
an experiment limitation. The human approved restoring narrow continuation.

Only `ResourceDecodeError(code="cleanup_refused")` continues. Refused inputs are
not published or retried. Other operational failures still abort. The small
BatchResult retains ready/skipped/refused maps; the historical gather_stories pair
remains available. CLI reports incomplete status 2 after processing remaining
inputs/collections. Logs contain each refusal, a batch_summary with incomplete=true,
and run_end for completed iteration. No cleanup, parser, selection, normalization
or publication changes; only the mass batch gatherer and coordinator changed.

## Actual frozen-cohort yield

| Invocation | Published | Reused | Refused | Unattempted |
|---|---:|---:|---:|---:|
| Previous cold batch (`91f1b422`) | 41 | 0 | 1 | 1,617 |
| Repaired cold batch | 1,646 | 0 | 13 | 0 |
| Repaired repeated batch | 0 | 1,646 | 13 | 0 |
| Separate one-item calls | 1,646 | 0 | 13 | 0 |
| Successful outputs with empty source cache | 0 | 1,646 | 0 | 0 |

Elapsed replay: 421.82 seconds. All 1,659 inputs were attempted in
configured order. No ordinary skips, other operational errors, body mismatches or
ownership collisions. All 1,646 cold-batch body hashes, owner IDs and fixture-source
hashes match the preserved pre-repair one-item census. Repeated-batch output bytes
are unchanged. The refused-ID set is exactly the same 13; every refusal has no
output and remains explicit in both result and log. `comparison-check.json`
records the cross-report checks; this is coordinator verification, not a new
independent review. The earlier causal/yield evidence is preserved unchanged.

The measurement uses real downstream catalog/resource/decoder/cleanup/parser/
normalization/publication/logging with explicit decoded-source fixture transport.
Sockets are forbidden; temporary caches/outputs are removed. No Gutenberg downloads,
canonical corpus writes or existing input-cache mutations. The cohort is the frozen
1,659-ID intersection, not all 5,492 configured IDs. It does not establish historical
wire fidelity, acquisition pacing, or editorial acceptability of the 67 differences.
The separate one-item controller remains experimental; the cold/repeated **batch**
measurements now establish actual continuation at the product batch boundary.

## Validation and reproduction

- Canonical `scripts/test`: 2,956 tests pass in 92.324s.
- Targeted integration: 46 tests pass; 26 explicit experiment tests pass.
- Package and changed-experiment Black/Ruff pass; LRH: 0 errors, 351 existing warnings.
- Authored actual coordinator tests cover success → refusal → success, truthful
  incomplete status 2, repeated-run byte preservation, fatal non-refusal decoding
  after a written prefix, empty selections and ordinary metadata skips. Existing
  missing-cache/integrity/fatal-output tests remain active.
- First full-suite invocation had 102 sandbox permission errors (loopback fixture
  servers and fixture writes). The authorized rerun passed; both logs are retained.
- No new independent review or isolated-wheel claim. Native execution remains
  in_progress pending review/integration; broader delivery gates remain open.

From `lcats/`, using the LCATS project environment and this revision's runners:

```bash
export PYTHONPATH="$PWD/src"
python ../experiments/10_gettenberg_qualification/scripts/qualify_narrow_yield.py \
  /path/to/catalog-cache /path/to/decoded-text-cache /tmp/NEW-yield.json \
  --product-ref 8c9441ddf707f4bdcd11afc4e9c4126d0976b8bc
scripts/test
python -m unittest discover \
  -s ../experiments/10_gettenberg_qualification/scripts -p '*_test.py'
```

The runner verifies the complete committed product tree and packaged data, source
hashes, catalog identity and loaded modules before/after execution. Its POSIX alarm
limits execution to 1,200 seconds. Output must be fresh and outside protected roots.
`gather-yield.json.gz` contains every per-input result, output identity and raw log
record; runner/helper hashes are embedded. The unchanged prior census is pinned at
`95ad5afd`. To check the comparison, join new cold/repeat rows with the prior
`gettenberg-causal-yield-20261023/gather-yield.json.gz` one_item_runs by ebook ID;
compare body_sha256, owner_id, fixture_source_sha256 and the refused-ID sets.

## Remaining decisions

This closes the measured fail-fast batch blocker for this frozen cohort. It does
not close overall Q5 or delivery acceptance: 13 refusals and body dispositions
remain explicit, along with evidence transfer, selection/wire scope, final
acceptance mapping and human main promotion. No broader editorial runtime restored.
