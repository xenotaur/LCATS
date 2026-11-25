# LCATS mass_quantities: style-refined distribution

These two ZIP archives are companion archives. Extract both into the **same** LCATS project root, retaining the supplied directory structure. The code ZIP contains source files, reviewed boundary overrides and associated existing data. The tests ZIP contains the consolidated unittest suite and its ground-truth fixture.

## Tests

From the directory containing `lcats/`, `tests/` and `ground_truth.json`:

```bash
python -m unittest discover -s tests -t . -p '*_test.py' -v
```

Optional slower checks:

```bash
LCATS_EXHAUSTIVE=1 python -m unittest discover -s tests -t . -p '*_test.py' -v
LCATS_CORPUS_ZIP=/path/to/corpus.zip python -m unittest tests.mass_quantities.corpus_audit_test -v
```

The tests use `_paths.py` to load independent extraction utilities from the companion code ZIP. Application integration tests still require a full LCATS installation.

## Notes on the style-only refactor

- Import statements now use module namespaces, with their call sites updated.
- Text-reading and text-writing calls explicitly specify UTF-8 (binary I/O unchanged).
- User-facing progress prints in the production modules now use `logging.info`.
- Public extraction/evaluation entry points have docstrings.
- Historical duplicate tests and `build_suite.py` were removed; consolidated tests retained.
- Existing timestamp behavior is unchanged; boundary matching, ground truth, and reviewed overrides are unchanged.
- No Black/Ruff executables were available in the execution environment, so a Black/Ruff-clean result is **not claimed**. Run `scripts/format --check -- <paths>` and `scripts/lint <paths>` in the LCATS environment. Some historical formatting may remain.

Test result in the packaging environment: 57 tests executed; 2 optional tests skipped, 0 failures/errors.
