# LCATS mass_quantities: two-stage Gutenberg extraction

This package is an **experimental replacement** for `lcats/gatherers/parser.py` plus one new helper module, `lcats/gatherers/mass_quantities/structural_screen.py`.

## Processing sequence

1. Metadata and source download (existing LCATS rules).
2. **NEW: Raw structural screening**, before any front-matter removal:
   `inspect_structure(text)` examines the entire Gutenberg body (after the
   source's standard Gutenberg wrapper handling) and records evidence for a
   contents list or multiple chapter/numbered-section headings. It preserves
   original line numbers in its diagnostic findings. Recognition supports
   `CHAPTER I`, `Part Two`, Roman numerals, italicized `1. Heading` labels,
   and actual contents lists.
3. If rejected, set `report['rejection']` and return without narrative cleaning,
   normalization, saving a story, or adding it to the registry.
4. If eligible, run the **existing** conservative `clean_gutenberg_story()`
   implementation, preserving the note/illustration/date-location safeguards.
5. Retain the original `chaptered(body)` check as a secondary defense, followed
   by the original minimum-length test and publication workflow.

`inspect_story()` reports the new `structure` object containing `reject`,
`reason`, and line-numbered `findings`. A structurally rejected work has `body`
set to `null`. `gather_story_result()` uses this same inspection path before
publishing a new result.

## Limitations

* This is **structural classification**, not proof of multiple stories. A
  contents list or repeated chapter numbering is strong evidence, but not all
  chapter styles are detected. False positives remain possible.
* The raw gate intentionally doesn't treat two uppercase lines as chapters;
  title pages and advertisements commonly contain such lines.
* An isolated chapter/section heading is **not** enough to reject a work.
* Existing saved outputs are reused without requalification (unchanged LCATS
  behavior). Run a separate corpus audit to revisit previously accepted works.
* This update does not change the ground-truth JSON data or the narrative-start
  heuristic. The archived source screen is not a held-out benchmark.
* The existing post-extraction `chaptered()` heuristic can still have its own
  false positives/negatives. The new stage is an additional precaution, not a
  wholesale replacement of that function.

## Installation

Copy `parser.py` to the location that `from lcats.gatherers import parser`
imports in your LCATS checkout. Copy `structural_screen.py` into
`lcats/gatherers/mass_quantities/`. `gatherer.py` is included unchanged as the
companion file for the package; no interface changes are required.

The standalone `gutenberg_extractor.py` also offers:

```python
from gutenberg_extractor import screen_and_clean_gutenberg_story
result = screen_and_clean_gutenberg_story(raw_text, title=["Example"], authors=["Someone"])
if not result["rejected"]:
    body = result["body"]
```

`structural_screen.py` must be next to the standalone extractor for that API.

## Tests and audit

Run from the unpacked folder:

```sh
python -m unittest -v test_conservative_parser.py test_two_stage_structure.py
python scan_archives.py
```

The archive scanner expects `stories*.zip` in the *parent* folder, each with
`<gutenberg_id>.txt` members, and writes `structural_archive_audit.csv` and
`structural_archive_summary.json`. The included audit is based on **1,660**
locally available texts, **not** all of the 5,000+ attempted extractions.
It found **13 candidate rejections**, not 13 confirmed positives. Examples:
63028 (contents), 70486 and 71109 (numbered sections); 39216 (advertising
catalog) is not rejected by the pre-cleanup screen.

## Regression result

Nineteen tests passed. They exercise note/illustration boundary safeguards,
date/location headings, real source text for 63028/70486/71109/39216 when
archives are present, and title-page/numbered-list false-positive cases.
The earlier 80/20 narrative-boundary datasets remain unchanged and are included
for reproducibility, but do **not** label chaptered works comprehensively.
