# Conservative Gutenberg narrative extraction: 80/20 experiment

## Data

* `training.json`: 1,318 verified examples (80%), used to diagnose and modify the parser.
* `testing.json`: 330 verified examples (20%), held back during modifications.
* Split: `random.Random(20261122).shuffle(records)` and first `round(0.8 * 1648)` records assigned to training. **Split by Gutenberg ID**, not by author; author overlap is possible. All 1,648 IDs are distinct.

Data fields retain their original human-reviewed annotations and physical formatting, unchanged apart from record ordering. The input is `gutenberg_ground_truth_verified(1).json`.

## Code

* `parser.py`: based on the newer LCATS `parser_verified.py` code already present in the working files. The Gutenberg-ID-specific `_VERIFIED_NARRATIVE_OPENINGS` lookup and associated repair were removed to avoid per-record overrides. A general `_conservative_narrative_guard()` now checks for plausible prose after a book title/byline and before the automatically selected boundary; it only moves the boundary **earlier**, not later.
* `gatherer.py`: the corresponding newer `gatherer_verified.py`, retained in full. It uses `from lcats.gatherers import parser`, so the modified parser is used automatically. Its batch logging, cache/source management, and publisher behavior remain unchanged.
* `gutenberg_extractor.py`: matching standalone extraction implementation with the same general guard; useful for direct extraction and independent evaluation. The new integrated `parser.py` already includes the core extraction logic; this module is supplied for existing LCATS branches that import `lcats.gatherers.mass_quantities.gutenberg_extractor` directly.
* `evaluate.py`: offline benchmark for start-boundary errors, uses only verified JSON opening excerpts. Compare the historical boundary (without guard) against the guarded boundary.
* `test_conservative_parser.py`: basic offline tests using **training data only**, including the disjoint split and prologue regression cases.
* `training_evaluation.json`, `testing_evaluation.json`: complete per-story boundary assessments and summary metrics.

## Installing in LCATS

For the *newer* LCATS code layout where `lcats.gatherers.parser` and `lcats.gatherers.mass_quantities.gatherer` are used:

1. Replace `lcats/gatherers/parser.py` with this `parser.py` (after reviewing against your live branch).
2. Replace `lcats/gatherers/mass_quantities/gatherer.py` with this `gatherer.py` (or keep your live version if already equivalent).
3. If any other caller uses `lcats/gatherers/mass_quantities/gutenberg_extractor.py` directly, replace that with this `gutenberg_extractor.py` so the standalone API has the same conservative behavior.

**Do not blindly overlay these files onto a different LCATS revision.** The newer parser/gatherer expect the newer gettenberg source API, registry, story_output, and related LCATS modules. These are not a standalone executable copy of LCATS.

## Reproduce

From this directory, with Python 3.10+:

```bash
python evaluate.py --dataset training.json
python evaluate.py --dataset testing.json
python -m unittest -v test_conservative_parser.py
```

No network or access to the complete Gutenberg texts is required for this evaluation: the reviewed original excerpts include sufficient text to assess **start offsets**. The evaluation compares **physical source lines**, including blank lines, before whole-story normalization. It does *not* test chapter filtering, footer/end detection, acquired Gutenberg source fidelity, or word-for-word integrity of the final output after formatting transforms.

### Metrics: training (1,318 examples, 1,316 assessable)

| Metric | Historical boundary | Conservative boundary |
|---|---:|---:|
| Cases skipping narrative | 58 | 31 |
| Narrative physical lines skipped | 353 | 90 |
| Cases retaining extra front matter | 294 | 525 |
| Extra front-matter physical lines | 3,247 | 5,614 |
| Exact boundary | 964 | 760 |

Two training records could not be aligned unambiguously with their reviewed opening, and were excluded from the metrics rather than scored optimistically.

### Metrics: held-back test (330 examples, all assessable)

| Metric | Historical boundary | Conservative boundary |
|---|---:|---:|
| Cases skipping narrative | 13 | 8 |
| Narrative physical lines skipped | 137 | 31 |
| Cases retaining extra front matter | 92 | 144 |
| Extra front-matter physical lines | 922 | 1,393 |
| Exact boundary | 225 | 178 |
| Maximum lost narrative lines in one story | 41 | 12 |

The design prioritizes minimizing **narrative loss**, not maximizing exact boundary accuracy. The remaining eight loss cases require additional work; no rules were fitted to test cases after evaluation. Existing general heuristics came from prior code and may themselves have been developed with overlap to these records; therefore the test is a reproducible **hold-out for this modification**, not an entirely independent historically unseen benchmark.
