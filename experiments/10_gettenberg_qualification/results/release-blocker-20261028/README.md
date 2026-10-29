# WI-RELEASE-0037: verify the delivered dependency replacement

Product under test: main commit `9976242705b68c2ad239184fd260c6ce4ae74f8d`.
Date: 2026-10-28. Prompt:
`PROMPT(WI-RELEASE-0037:WI_RELEASE_0037)[2026-10-28T19:00:06+00:00]`.

**Verification passes; recommend resolving WI-RELEASE-0037 after review and merge.**
The work item remains proposed until that closeout. This is not package publication,
a release-version decision, or completion of WI-RELEASE-0039 / WS-RELEASE. Product,
package declarations, CI, tests and canonical corpora are unchanged. GPA-A–E, PR #524
and Kenny's separate gatherer work remain open.

## Acceptance-to-evidence map

| WI acceptance | Fresh evidence and retained context |
|---|---|
| Replacement delivered on main without active gutenbergpy imports/requirements | PR #534/main merge `b4ec4c45` and closeout `99762427`; [artifact closure](artifact-closure.json) parses every product Python file's static imports and inspects distribution requirements; [summary](verification-summary.json) checks all 430 conda/pip installation entries. Installed runners prohibit legacy imports/distribution presence. |
| Package/environment declarations agree; no direct URL/VCS requirements in built metadata | [Artifact closure](artifact-closure.json): wheel, sdist and installed metadata agree; every Requires-Dist is parsed as a PEP 508 requirement, including extras; no gutenbergpy name or direct URL is allowed. Source pyproject and sdist pyproject match exactly. Source environment entries separately checked. |
| Real parser-to-SQLite titles/aliases; migration, first-use/offline and corpus evidence | [Installed catalog](installed-catalog.json) round-trips seven retained real RDF fixtures plus one authored multiple-title/alias record through the installed parser/SQLite lifecycle; independent expected titles and alias queries pass. [Installed smoke](installed-smoke.json) builds a local catalog, acquires fixture originals and gathers offline. Prior [delivery decision](../../../../lcats/project/development/gettenberg-delivery-decision.md), [migration ledger](../../../../lcats/project/development/gettenberg-migration.md) and [accepted batch yield](../gettenberg-refusal-continuation-20261023/README.md) retain their measured scope. |
| Fresh wheel works without gutenbergpy; canonical checks and independent review | Fresh venv, ordinary dependency resolution, [installed versions](installed-packages.json), [pip check](pip-check.log.gz); [canonical suite](tests-unsandboxed.log.gz): 3,014 tests pass in 99.377s. Format/lint pass; seven [runner tests](artifact-runner-tests.log.gz) pass. [Independent review](independent-review.md) is recorded before PR creation. |
| LRH valid; publication/near-publication gate separate | [LRH baseline](lrh-baseline.log.gz) and final validation recorded with this PR: zero errors, 354 existing warnings. WI-RELEASE-0039 remains proposed and must run when publication is imminent. |

## Artifact and installation identity

Normal `python -m build` at the pinned Git worktree generated an sdist, then built
its wheel in an isolated build environment. No pretend-version override was used.
Both artifacts report `0.1.1.dev1253+g997624270`, the SCM-derived development version.
This is a verification artifact, not a selected PyPI release version.
[Build log](build.log.gz) and [artifact closure](artifact-closure.json) retain
filenames, SHA-256 values, dependency metadata and the complete package file map.
Binaries and the temporary venv are not committed.

All **188 tracked package files** match byte-for-byte across pinned Git, sdist,
wheel and physical installation: **165 Python, two JSON, 21 other assets**. The
normal SCM-aware build includes existing text/Ruby/HTML/README assets that earlier
empty-staging qualification wheels did not include. The new check originally
expected only Python/JSON files; it correctly refused the extra file set. It now
compares every tracked package file rather than ignoring the extras. This run
neither adds nor removes those pre-existing assets.

Build warnings mention legacy MANIFEST.in paths without `src/`. Both required JSON
files are nevertheless present and byte-identical through pyproject package data
and SCM inclusion. No manifest repair or packaging-hygiene overhaul is part of
this dependency verification. A future release should deliberately review the
additional assets and choose its release version.

The venv was created fresh without system site packages. Runtime dependencies were
resolved from current indexes (no historical constraint overlay); the exact versions
are recorded. `pip check` passes and gutenbergpy is neither installed nor importable.
All loaded LCATS module hashes in each behavioral report match the pinned artifact
closure: 70 in the gather smoke, 98 in each CLI scenario and 20 in the catalog check.

The shared development environment still has an older LCATS distribution metadata
version; [tool versions](tool-versions.log.gz) reports that observation. Source tests
explicitly pin `PYTHONPATH` to this worktree's `lcats/src`; wheel checks unset it,
run outside the checkout, and assert installed module origins. The shared editable
installation was not retargeted.

## Behavioral checks and boundaries

- [Catalog](installed-catalog.json): seven unmodified real RDF fixtures retain their
  source bytes and contributor aliases. An additional authored record preserves two
  primary titles, an alternative title and two aliases, with exact title/name/alias
  queries and offline reopen. Real-fixture provenance remains in
  [provenance.json](../../../../lcats/tests/gettenberg_tests/fixtures/provenance.json).
- [Gather smoke](installed-smoke.json): real catalog, acquisition receipts, decoding,
  conservative cleanup, parser, publication, source provenance and unchanged reuse;
  two stories published and an ambiguous envelope explicitly refused.
- [Cleanup-refusal CLI](installed-cli-refusal.json): success/refusal/success writes
  two stories, then reuses both unchanged; both runs return status 2 and complete logs.
- [HTTP-404 CLI](installed-cli-404.json): success/404/success behaves similarly;
  repeat requests only the failed input, writes no error body to source cache and
  preserves status/reason/request identity. No retries or fallback routes added.

All installed behavioral runners deny real sockets and use disposable outputs,
cache directories and authored transport responses. This run made **no Gutenberg
requests**. Dependency/build installations use network access. The initial canonical
suite in the sandbox failed on 99 local socket binds and three tokenizer-cache
network lookups; [initial log](tests.log.gz) is retained. The unsandboxed canonical
rerun passed without changing tests or product code. These existing corpus-selector
tests need an available tokenizer asset/cache; this run does not claim a hermetic
full-suite environment. The installed gettenberg checks remain socket-denied.

Coverage is Python 3.11.9 on macOS arm64 with the recorded dependency resolution.
This is not a Python 3.10/all-platform matrix, a new full catalog build or a fresh
1,659/5,492-input yield measurement. Accepted cohort limits and editorial exclusions
remain unchanged; the installed fixture checks do not expand those claims.

## Reproduction

Use a disposable worktree at the product commit, a fresh output directory and the
project Python environment. From its `lcats/` directory:

```bash
python -m build --outdir /tmp/NEW-release-dist
scripts/version tools
scripts/format --check --diff
scripts/lint
PYTHONPATH="$PWD/src" scripts/test
lrh validate
```

The package's scripts/test does not support the LRH skill's generic `--log` flag;
redirect stdout/stderr to a fresh log explicitly. Local HTTP fixture tests require
loopback sockets. Keep the existing shared editable install unchanged.

Create a fresh venv and install the newly built wheel with its runtime dependencies:

```bash
python -m venv /tmp/NEW-release-venv
/tmp/NEW-release-venv/bin/python -m pip install /tmp/NEW-release-dist/lcats-*.whl
/tmp/NEW-release-venv/bin/python -m pip check
/tmp/NEW-release-venv/bin/python -m pip list --format json
```

From outside the checkout, unset PYTHONPATH and use the installed interpreter for
all behavioral runners below. Paths are explicit arguments, not source imports:

```text
qualify_narrow_installed.py NEW-smoke.json
qualify_narrow_cli.py NEW-cli-refusal.json
qualify_narrow_cli.py NEW-cli-404.json --http-404
qualify_release_catalog.py /path/to/repo/lcats/tests/gettenberg_tests/fixtures NEW-catalog.json
```

With project Python, verify the full distribution boundary:

```text
qualify_release_artifacts.py REPO COMMIT WHEEL SDIST VENV/lib/python3.11/site-packages/lcats NEW-closure.json
```

The new runners live in [scripts](../../scripts/). They are offline and documented
with arguments, input/output behavior, failure semantics and bounds. Explicit checks:

```bash
python -m black --check qualify_release_artifacts.py qualify_release_catalog.py release_artifacts_test.py
python -m ruff check qualify_release_artifacts.py qualify_release_catalog.py release_artifacts_test.py
python -m unittest release_artifacts_test -v
```

Run those three commands from the experiment scripts directory. The catalog runner's
smoke test is its installed eight-record execution above. The artifact gate's seven
unit tests use actual tiny Git/zip/tar/install trees, rejecting changed non-Python
assets, missing files, extra installed modules, legacy requirements, direct URLs
(including inactive extras), and attempted report overwrite.

[Artifact manifest](artifact-manifest.json) fingerprints the retained machine
reports and compressed logs, excluding itself and narrative documents. Prior evidence
has not been regenerated or relabeled. The new scripts are versioned with this PR;
each generated report also records the runner hash used for its execution.
