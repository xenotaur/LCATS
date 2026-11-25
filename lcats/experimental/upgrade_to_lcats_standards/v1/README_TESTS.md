# LCATS mass_quantities consolidated test suite

## Scope

This consolidates all prior stages of the Gutenberg `mass_quantities` extractor into Python `unittest` tests in the LCATS naming convention (`*_test.py`). Tests run without network access or live Gutenberg catalog. The suite covers gathering/publication source contracts, raw structure rejection, boundary safety, title/author diagnostic wiring, overrides, recording, confidence, year extraction, year.json saving, and the 1,648 corrected ground-truth records.

## Install

Copy the `tests/mass_quantities/` directory into your LCATS project's `tests/` directory. The ZIP also contains a **reference copy** of the current parser collection under `lcats/gatherers/mass_quantities/` for reproducibility; do not overwrite newer application sources without comparing them. `ground_truth.json` is placed at the ZIP root for standalone tests; for LCATS installation put this file at the project root or adjust `ROOT` in the three dataset tests. Historical test copies are retained in `tests/mass_quantities/legacy_reference_tests/` but are not discovered automatically.

## Commands (run from root of this package or LCATS project)

Normal run:

```bash
python -m unittest discover -s tests -t . -p '*_test.py' -v
```

Optional exhaustive run:

```bash
LCATS_EXHAUSTIVE=1 python -m unittest discover -s tests -t . -p '*_test.py' -v
```

Optional corpus check:

```bash
LCATS_CORPUS_ZIP=/path/to/stories.zip python -m unittest tests.mass_quantities.corpus_audit_test -v
```

No test fetches Gutenberg content. The optional corpus test reads an already available ZIP and requires `extraction.json` siblings for ID mapping. The exhaustive test checks historical invariants, not universal correct alignment. The supplied ground truth was corrected for IDs 24247, 63930, and 27013.

## Design notes

- Uses `unittest.TestCase`, `setUp`, `subTest`, and mocks/tempdirs rather than production network, matching earlier LCATS conventions.
- No test writes to production data/corpora.
- Static parser wiring tests catch missing imports and save/override ordering without importing a full LCATS installation.
- The `gutenberg_extractor.py` path provides independently runnable extraction logic.
- Historical source tests retained for reference may contain **outdated expectations** and slow O(N²) corpus sweeps; use consolidated tests as the default.
- This package does **not** claim integration coverage of the actual LCATS publisher/registry. Those require an installed LCATS app and should be run with isolated mocked output directories.

## One-statement-per-line convention

All consolidated and historical test sources have been reformatted so no Python line contains more than one statement. This is checked by `test_source_style_test.py`. Production modules were not reformatted.
