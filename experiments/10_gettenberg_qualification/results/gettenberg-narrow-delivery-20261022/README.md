# Narrow delivery construction checkpoint — 2026-10-22

This is a reviewed candidate, **not Q1–Q8 acceptance or permission to merge to main**.
Product commit `91f1b42281418d613bc1744b77ada73b42405bfc` contains exactly three
runtime changes from migration seam `ed20e9c297bf5e50e1911b84722e53f5db3edee3`:
cleanup, the Gutenberg source adapter and mass gathering's log/refusal integration.
Later commits add documentation, tests and evidence without changing those bytes.
The [construction manifest](../../../../lcats/project/development/gettenberg-narrow-delivery.md)
enumerates retain/separate decisions; the combined work remains at `b1254805`/PR524.

## Results and limits

| Evidence | Observed result |
|---|---|
| `corpus-comparison.json.gz` | All 1,659 cleanup outcomes and all 1,646 non-refused bodies exactly reproduce the approved narrow experiment with actual selected-resource identities. 202.135 seconds; no network/cache/corpus writes. |
| `installed-smoke.json` | Fresh isolated wheel, no gutenbergpy: two authored stories published, one ambiguous source refused, original/reused bytes preserved, protected log roots rejected. In-memory HTTP fixture only. |
| `migration-fixtures.json` | Five authored before/after consumer fixtures preserve story results and JSON. |
| `independent-review.json` | No unresolved P0–P2; explicit finding/fix chronology, reviewed hashes and scope limits. |
| `independent-clean-wheel.json`, `wheel-data-files.json` | Wheel and installed Python closure:165 files, exact product bytes; both declared JSON data files also match Git. |
| `full-tests.log` | Canonical scripts/test: 2,955 tests pass. |
| `package-lint.log`, `experiment-lint.log` | Ruff/Black pass, including changed experiment runners explicitly. |
| `pip-check.log` | No broken requirements in isolated wheel environment. |
| `lrh-validation.log` | Zero errors; 351 existing control-plane warnings, no consent/status mutations. |

The severe 35401 and 50103 cases retain 26,080 and 31,972 normalized characters,
respectively, equal to the historical bodies. All 67 residual body differences and
13 refusals remain unresolved; none is converted into editorial approval. The
census tests cleanup/extraction/normalization, not actual full-batch publication,
selection changes or complete Q1–Q8 qualification. Decoded historical gzip inputs
are not original HTTP receipt evidence. The actual-gather smoke uses independently
authored transport fixtures, not those historical bytes.

## Repair evidence

The first full test run failed because the cleanup guide acquired a fifth example
while its executable test expected four. The example was made self-contained and
all five remain exercised; the full suite was rerun successfully.

The first non-isolated wheel build failed on outdated development-environment
`packaging`; an isolated build used the declared build requirements. That build
then exposed stale setuptools staging: its wheel contained nine separated modules.
`rejected-wheel.json` identifies the rejected artifact. The earlier installed smoke
was insufficient because those modules were present but not imported. Generated,
untracked `lcats/build` and `lcats/src/lcats.egg-info` were removed; a fresh build,
exact whole-wheel comparison and external-cwd installed smoke then passed.
The current installed runner additionally rejects all nine modules on disk.
No rejected artifact is promoted or represented as accepted qualification.

## Reproduce

From `lcats/`, use the project environment and absolute `PYTHONPATH="$PWD/src"`:

```bash
python ../experiments/10_gettenberg_qualification/scripts/qualify_narrow_corpus.py \
  /path/to/catalog-cache /path/to/decoded-text-cache /tmp/NEW-corpus.json
python ../experiments/10_gettenberg_qualification/scripts/qualify_migration.py \
  /tmp/NEW-migration.json
scripts/test
scripts/lint
scripts/lint ../experiments/10_gettenberg_qualification/scripts/qualify_migration.py \
  ../experiments/10_gettenberg_qualification/scripts/qualify_narrow_corpus.py \
  ../experiments/10_gettenberg_qualification/scripts/qualify_narrow_installed.py
```

The corpus runner requires a committed product tree and the preserved prior
comparison blobs at b1254805. It verifies all imported/disk product sources and
cached input identities. New output paths must be outside repository/cache roots.
It never bootstraps missing data or adds a legacy dependency.

Build the wheel with `python -m build --wheel` from clean generated staging (or a
clean checkout). Verify its complete Python pathset/bytes against the intended Git
tree and the two declared JSON data files. Install into a fresh venv with declared
dependencies; `pip check` must pass. From outside the checkout, run:

```bash
env -u PYTHONPATH /path/to/venv/bin/python \
  /absolute/path/qualify_narrow_installed.py /tmp/NEW-installed.json
```

The CLI rejects source/editable/legacy installations; real sockets are forbidden.
Copy fresh reports here only as new named evidence. Historical outputs and absolute
paths in reports are observations; no previous report is overwritten or relabeled.

## Published checkpoint

[Draft PR #530](https://github.com/xenotaur/LCATS/pull/530) targets the acquisition
branch. `ci-2e99ac3a.json` records four successful checks on checkpoint head
`2e99ac3aba79f02966f47f64a70cc0dbbc37e788`; runtime bytes remain those of 91f1b422.
The closing record/evidence commit is documentation only. Consult the linked PR
for its latest automatic checks. No merge or final delivery acceptance occurred.
