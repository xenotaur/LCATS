# Scope adoption and landing verification — 2026-10-22

The human approved the four decisions in PR528 and requested recording/correction/
internal landing before11:20 PDT. This archive binds substantive repair commit
`141e151bca8d716e8b239ac5364d35dcaac48257`. Later evidence-only checkpoints do not
change reviewed code. No product sources or original measurement archives changed.

## Repairs and verification

- Import-safe diagnostic main functions; optional historical cleaner loaded only for
  actual legacy measurement. All29 helpers import and25 CLI help paths work without
  gutenbergpy; helper/test modules retain import coverage without a fabricated CLI.
- Causal runner binds174 Python product modules and validates loaded origins before
  and after computation. New regression fixtures reject changed/missing/added sources
  and shadow imports. Independent review caught and corrected a test that would have
  incorrectly frozen future product sources; the final test uses a temporary package.
- [Facts reproduction](../../scope-facts-reproduction.md) matches18 derivable fields.
  Three historical investigator-parity observations remain explicitly unreproduced.
- Eight causal rows, two literal-counterfactual rows and all1,659 numeric rows plus
  the numeric summary match their original archived values exactly. Numerical evidence
  remains67 unresolved body comparisons and13 refusals, not product/corpus acceptance.
- Full canonical suite passes3,120 tests; package and explicit experiment format/lint
  pass; LRH has0errors/351existing warnings. Independent review binds12file hashes.

`validation.json` records exact scope and commands; `independent-review.json` binds
reviewed sources and new numeric replay. The gzip files are lossless copies of fresh
reports/logs, not edits to older reports. `manifest.json` binds archive file bytes.

## Reproduction

Use the project Python environment from `lcats/`, with absolute
`PYTHONPATH="$PWD/src"` and `PYTHONDONTWRITEBYTECODE=1`. Existing inputs are catalog
`/tmp/gettenberg-dispositions-20261020/cache` and historical decoded text cache
`/Users/centaur/Tempspace/Projects/LCATS/cache/texts`; no downloads/setup are permitted.

```bash
scripts/test
scripts/format --check --diff
scripts/lint
lrh validate
python ../experiments/10_gettenberg_qualification/scripts/reproduce_scope_facts.py /tmp/NEW_FACTS.json
python ../experiments/10_gettenberg_qualification/scripts/audit_cleanup_causality.py CATALOG_CACHE TEXT_CACHE /tmp/NEW_CAUSAL.json
python ../experiments/10_gettenberg_qualification/scripts/trace_literal_terminal_notices.py CATALOG_CACHE TEXT_CACHE /tmp/NEW_LITERAL.json
python ../experiments/10_gettenberg_qualification/scripts/audit_numeric_notices.py CATALOG_CACHE TEXT_CACHE /tmp/NEW_NUMERIC.json
```

Causal and full legacy comparison paths require the historical measurement cleaner;
imports/help and facts/numeric-only measurement do not add a product dependency.
The numeric runner preserves the historical evidence revision and explicitly hashes
its repaired helper. No cleanup/extraction computation changed. See each runner's
help and earlier archive README for time/output/input limits. Existing outputs are
refused; choose fresh paths. The suite requires permission to bind local test servers.

The first suite invocation used relative PYTHONPATH and imported another editable
checkout in subprocesses (six failures). The second corrected the import path but
ran under a sandbox denying loopback binds (102errors). Both failed logs are preserved;
the final unchanged command with loopback permission passes. An initial format command
used repository rather than package cwd and failed before running; corrected package
invocations pass. A lint attempt also needed task-worktree cache permission.

Hosted CI and actual integration are recorded separately in the PR and runlog. No
main promotion, PR524 merge, package/corpus publication or terminal closeout is inferred.
