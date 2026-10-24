# Delivery review and proposed acceptance — 2026-10-24

Review of PR #530 at `823f33c23836aff220fab80046ab84b80584c063` against
`ed20e9c297bf5e50e1911b84722e53f5db3edee3`. Product behavior is unchanged in this
run. These artifacts support a human decision; no delivery/editorial acceptance,
integration, main promotion or package/corpus publication occurred.

The [decision sheet](../../../../lcats/project/development/gettenberg-delivery-decision.md)
maps Q1–Q8 and all ten design criteria. `proposed-acceptance.json` names all 80
residual inputs with source/metadata/body identities and **proposed** dispositions.
Historical causal and yield reports are preserved unchanged.

## Fresh checks

- Independent review: no unresolved P0–P2 findings in the four-module product delta.
  112 canonical focused tests and 26 experiment tests pass. Fresh independent replay
  reproduces all 1,659 cleanup results and all 67 differing body hashes. All 1,646
  prior cold/repeated publication records, source/owner identities and 13 refusals
  reconcile; the reviewer did not rerun the full publication benchmark.
- Fresh isolated wheel: all 165 Python modules and both declared JSON data files
  match the reviewed Git tree, with no extra installed product modules. No
  gutenbergpy/VCS dependency. `pip check` passes. Installed acquisition, publication,
  refusal, reuse and log-root protections pass outside the checkout without
  PYTHONPATH or source-tree imports.
- Fresh installed CLI: success → refusal → success twice; two outputs retained
  byte-for-byte, one distinct refusal, complete event sequence and truthful exit 2
  both times. The socket guard permits zero source-network bytes. This is an authored
  fixture test, not another 1,659-input publication run.
- 41 documentation/live-gather tests pass (overlap the reviewer's 112; do not sum).
- Historical full-snapshot/lifecycle evidence transfers for unchanged measured
  components: 161/165 product modules identical; exactly the four reviewed cleanup/
  gather modules differ. Each snapshot/lifecycle source ledger has 27 identical
  modules plus changed cleanup, which is outside the measured catalog import path.
  Fresh cleanup/gather evidence replaces old cleanup conclusions. Static import
  analysis is supporting evidence, not proof about arbitrary dynamic plugins.

## Build environment and failures

`build.log.gz`: initial nonisolated build failed because the project environment's
packaging module lacked `packaging.licenses`. `build-isolated.log.gz`: normal isolated
build succeeds. The source was extracted from reviewed Git into fresh staging,
avoiding stale build modules. The version override
`SETUPTOOLS_SCM_PRETEND_VERSION_FOR_LCATS=0.1.0+qualification.g823f33c2` labels this
qualification artifact only; this is not release-version qualification.

`install.log.gz`: first unconstrained fresh-venv install hit a PyPI download timeout.
`install-constrained.log.gz`: a single retry using recorded versions from the prior
qualification venv succeeds in a fresh isolated environment; exact constraints and
installed package inventory are preserved. This demonstrates the recorded supported
configuration, not every dependency-version combination. Nothing was changed in
the project environment to bypass the failure. Package downloads occurred; Gutenberg
and story-source downloads did not.

Old full-snapshot measurements used Python 3.11.9, SQLite 3.46.0, lxml 5.2.2 and
libxml2 2.12.6. Historical timings are carried as dated measurements, not rerun
benchmarks or performance claims for the freshly resolved wheel environment.

## Reproduction

Use the current committed experiment runners with the reviewed product wheel.
Create a fresh venv, install the wheel with `qualification-constraints.txt`, run
`python -m pip check`, then from outside the checkout with PYTHONPATH unset:

```bash
env -u PYTHONPATH /path/to/venv/bin/python \
  /path/to/LCATS/experiments/10_gettenberg_qualification/scripts/qualify_narrow_installed.py \
  /tmp/NEW-installed.json
env -u PYTHONPATH /path/to/venv/bin/python \
  /path/to/LCATS/experiments/10_gettenberg_qualification/scripts/qualify_narrow_cli.py \
  /tmp/NEW-cli.json
```

The new CLI runner delegates fixture creation/cache isolation to the existing
installed runner; it imports real product CLI code and patches only fixture selection.
It uses a POSIX 120-second alarm and exclusively creates its report. Existing outputs
are refused. Temporary input/output directories are removed on success or failure.

For full-cohort replay, use the commands in the adjacent causal/yield and refusal-
continuation READMEs with this unchanged product tree and immutable local caches.
Independent ad-hoc probes are described in `independent-review.json`; their recorded
results, identities, hashes and exact conclusions are archived here. They are
supplementary review evidence, not a new public qualification API.

`wheel-and-transfer.json` records the complete source/data closure and previous
report hashes. `artifact-manifest.json` pins every archived evidence file. Absolute
paths and timestamps in raw outputs preserve the observed environment; they are not
portable defaults. Compressed files expand to the exact original tool output.

## Final packet checks

The same independent review assignment also checked the decision sheet, all 80
proposed dispositions and the new installed CLI runner/report: no P0–P2 findings.
`final-packet-review.json` verifies the four green hosted checks archived in
`pr530-before.json`. The transfer runner was subsequently extracted from the
coordinator's probe; its result is byte-for-byte equivalent as JSON to the original
report except for the added runner hash. It is not separately independently reviewed;
the original transfer result and wheel bytes were independently checked.

Reproduce the transfer from the repository with project Python:

```bash
python experiments/10_gettenberg_qualification/scripts/qualify_narrow_transfer.py \
  /path/to/LCATS 823f33c23836aff220fab80046ab84b80584c063 \
  /path/to/lcats-0.1.0+qualification.g823f33c2-py3-none-any.whl \
  /tmp/NEW-transfer.json
```

Package Ruff and Black pass, with explicit checks for both new experiment runners.
Canonical Black invocations failed when its worker manager tried to bind a
sandbox-restricted local socket, including a single-worker attempt. An authorized
rerun of the unchanged package and explicit experiment checks passes. All failure
and success logs are preserved. The CLI runner also refuses
an existing report before running fixtures; its original report hash is unchanged.
No full-suite rerun is claimed in this documentation/evidence-only pass: the 2,956-test
result applies to identical product/test/config bytes and the reviewed head already
has four green hosted checks. Final evidence-commit CI is checked separately.


Final user-guide correction: removed the stale statement that dependency removal
remained future work and explicitly described retained source paratext. All 11
documentation-example tests pass again (`final-docs-tests.log.gz`). Product behavior
and pending human acceptance are unchanged. This prose correction follows the
independent packet review; it adds no new qualification or editorial approval claim.
