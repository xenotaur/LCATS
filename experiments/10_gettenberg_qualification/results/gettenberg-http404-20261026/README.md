# Narrow HTTP 404 continuation — 2026-10-26

Product commit: `94d4331f1d1215b89599cb06ec197eb015e4bce3`; base:
`059f22ba1243d896f564d48611616887b4841b55`. This is a human-authorized
replacement-integration correction for PR #534, not main-promotion approval.

## Problem and scope

Kenny reported ebook 1367 aborting mass gathering because the configured PGLAF
representation returned HTTP 404. Earlier diagnostic probes reproduced GET/HEAD
404 at that mirror while Gutenberg's origin returned HEAD 200. Those probes were
in the preceding discussion, not rerun or archived as new measurements here.
This repair does not fetch 1367, change endpoints or recover its contents.

Terminal HTTP errors retain status, source URI, original request URL and final
endpoint. Only code `http_status` with status404 becomes an unavailable-item
outcome in the batch. Later inputs continue; output is incomplete (CLI2), with
separate unavailable and cleanup-refused counts. No 404 retry, mirror/format
fallback, 410 recovery, blanket exception handling or editorial change is added.
Catalog setup and direct source calls still raise. The historical two-dictionary
`gather_stories` interface retains missing-resource reasons in its error mapping.

## Validation

- 120 focused resource, batch and CLI tests pass.
- All **2,977 canonical tests** pass in **100.173 seconds**. Expected diagnostics
  are captured locally in the tests; the full output is clean.
- Canonical format/lint and explicit changed-experiment-runner checks pass.
- Independent read-only agent review: no substantive findings. Three new CLI/batch
  tests and extra in-memory identity/error-predicate probes passed independently.
  Reviewer loopback tests were sandbox-denied at setup; the coordinator's authorized
  focused suite supplies separate loopback evidence. See independent-review.json.
- Clean wheel built from committed source in empty staging, with temporary
  qualification version `0.1.0+qualification.http404`. This is not release-version
  qualification. Reused the prior isolated qualification dependency environment,
  force-reinstalling LCATS with no dependency changes; `pip check` passes.
- Whole wheel and physical installed package equal committed source: 165 Python
  modules and two JSON files, no legacy or direct-URL requirement. Every loaded
  module origin in all three installed reports matches that source map.

## Actual installed CLI outcomes

Both scenarios invoke the actual installed CLI outside the checkout with PYTHONPATH
unset, all real sockets forbidden, authored inputs and only the HTTP boundary and
collection selection substituted. The 404 scenario starts with a fresh resource
cache. It does not inherit the earlier helper's successful source receipts.

| Scenario | Cold run | Repeated run | CLI status |
|---|---|---|---|
| Success / cleanup refusal / success | Two outputs, one cleanup refusal | Both outputs byte-identical | 2, then 2 |
| Success / HTTP404 / success | Two outputs, one unavailable item | Both outputs byte-identical; only missing item requested | 2, then 2 |

The 404 scenario observes exactly four requests: three in initial order, then the
missing source alone. No error response becomes a cached source, no temporary
acquisition artifact remains, and both logs contain ordered start/ready/unavailable/
ready/summary/end events with status/source/request/final identities and accurate
incomplete counts. Unit tests additionally cover redirect-to-404 identity, 403/410/
exhausted503 fatal behavior and preserved preceding output. Existing offline,
strict-decode, policy, integrity and cleanup tests remain passing.

## Reproduce

Build from `git archive 94d4331f lcats` in empty staging with normal build isolation;
set `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_LCATS=0.1.0+qualification.http404` for the
archive-only build. Install that wheel in an isolated qualification environment,
run `pip check`, then run these from outside the checkout with PYTHONPATH unset:

```bash
/path/to/venv/bin/python /path/to/LCATS/experiments/10_gettenberg_qualification/scripts/qualify_narrow_installed.py /tmp/NEW-smoke.json
/path/to/venv/bin/python /path/to/LCATS/experiments/10_gettenberg_qualification/scripts/qualify_narrow_cli.py /tmp/NEW-refusal.json
/path/to/venv/bin/python /path/to/LCATS/experiments/10_gettenberg_qualification/scripts/qualify_narrow_cli.py /tmp/NEW-404.json --http-404
```

The runners require fresh output paths and use disposable fixtures, no Gutenberg
requests and a 120-second POSIX alarm. Runner/helper hashes and installed source
identities are in their reports. Review `wheel-closure.json` for full source and
dependency identities and `artifact-manifest.json` for archived evidence hashes.

## Evidence boundaries

These fixtures qualify failure handling, not live mirror availability or full
collection yield. The earlier 1,659-input historical cohort, A–D acceptance and
backlog remain unchanged; those cached-source measurements never established cold
network acquisition yield. Metadata, cleanup and body extraction algorithms did
not change here. No canonical corpus or existing Gutenberg cache was regenerated.
Alternate acquisition for 1367 remains a separate decision. Main promotion remains
human-gated; native records remain nonterminal until actual delivery.
