# LCATS Gutenberg: structural-boundary feature study and parser revision

This package builds on the **two-stage** mass_quantities parser. All parser
source is provided; the `training.json` and `testing.json` are unchanged.

## Research questions

### A. Does blank-line structure predict narrative starts?

Measured **only on 1,318 training records**; 1,316 had alignable verified
openings. Here `gap` means the number of completely empty physical lines
between the preceding nonempty line and the first verified narrative line.

| Gap | Training records |
|---:|---:|
| 1 | 60 |
| 2 | 1,086 |
| 3 | 24 |
| 4 | 143 |
| 5 or more | 3 |

Two blank lines are common but **not sufficiently diagnostic**: books also
use two empty lines between ordinary front-matter blocks. Conditional
measurements for the immediately preceding block:

| Block just before narrative | Examples | Gap >= 2 | Gap >= 3 |
|---|---:|---:|---:|
| Byline | 96 | 92 | 27 |
| Publication/illustration credit | 52 | 52 | 8 |
| All-caps heading | 182 | 162 | 91 |
| Other prose/front matter | 986 | 950 | 44 |

The combination of short paragraphs with credits, scene labels,
viewpoint headings and dated headings is more informative than blank lines
alone. The new `boundary_features.py` applies that information as a
**conservative backward-only** guard; no rule fires on spacing alone.

Generalized rules address: abbreviated narrative after unbracketed
illustration credit (26772); short first sentences after a byline (21279);
short dialogue after publication credit (23003); POV character + date heading
(29632); SCENE after a repeated title (33608); and prose following an
italic teaser near an illustration credit (29889). No Gutenberg-ID branches.

### B. Why was 23357 accepted?

`structural_screen.py` formerly ignored **Roman-numeral titled section
headings ending in a period**, e.g. `I. THE OLD TAVERN AT BAYLEY'S FOUR
CORNERS.`. The generic fix lets the `ROMAN` heading grammar override the
sentence-ending-punctuation exclusion. Two sufficiently separated
section headings (`I.` and `II.`) trigger structural rejection; one does not.

The reviewed 23357 opening only includes section I, **not the full text**.
The original 23357 text was missing from the local ZIP archives, so this
revision is verified using a **synthetic two-section regression** and the
published Gutenberg HTML confirms that sections I and II exist. Do not
interpret the synthetic test as a full live-source integration test.

## Narrative-boundary evaluation

The earlier baseline is the **date/location two-stage parser with guards**;
comparison uses exactly the same training/testing records, without any
annotation changes. Positive offset = late start / potential narrative loss.
Negative offset = extra introductory material retained.

| Metric | Original training | Revised training | Original test | Revised test |
|---|---:|---:|---:|---:|
| Alignable records | 1,316 | 1,316 | 330 | 330 |
| Narrative-loss cases | 11 | **3** | 1 | **1** |
| Narrative lines lost | 29 | **6** | 12 | **12** |
| Front matter cases | 619 | 654 | 165 | 176 |
| Extra front-matter lines | 6,087 | 6,332 | 1,489 | 1,558 |

Note that 23357 is one of the three remaining training boundary
mismatches but would be rejected if the full source has two sections.
The other two training mismatches are Gutenberg 26956 and 23367. The
remaining test mismatch is Gutenberg 63028, an intended structural reject.

These metrics come from short **opening excerpts** and assess beginning
boundaries only; they do not measure paragraph segmentation in full stories,
complete structural recall among the >5,000 attempts, or the existing
post-cleanup `chaptered()` check. The prior test set has already been
inspected during multiple rounds of development, so it is **not a fresh
independent generalization test**.

## Local archive structural audit

The old and revised structural detectors both flagged 13 / 1,660 locally
archived originals; there were no changed decisions. This does not
contradict the 23357 fix because the 23357 original is absent from those
archives. See `structural_audit_updated.csv` for each ID and evidence.

## Install

- Replace `lcats/gatherers/parser.py` with `parser.py`.
- Put `structural_screen.py` and **NEW** `boundary_features.py` in
  `lcats/gatherers/mass_quantities/`.
- `gatherer.py` is included for completeness; it was not otherwise modified.
- Standalone `gutenberg_extractor.py` needs `boundary_features.py` and
  `structural_screen.py` alongside it.

No saved LCATS outputs are retroactively rechecked. Run these tests before
integrating into production:

```
python -m unittest -v test_conservative_parser test_two_stage_structure test_boundary_features
python evaluate.py --dataset training.json --out training_after.json
python evaluate.py --dataset testing.json --out testing_after.json
python analyze_features.py
```

For full LCATS integration, run your existing gathering tests in your
project environment. This package was only tested offline against the
provided archive and JSON excerpts.
