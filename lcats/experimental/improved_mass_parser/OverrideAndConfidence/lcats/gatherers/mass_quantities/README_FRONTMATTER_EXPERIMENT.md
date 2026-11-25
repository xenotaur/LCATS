# LCATS mass_quantities: Conservative front-matter refinement experiment

## Purpose and conclusion

This package extends the existing *two-stage* Gutenberg extraction pipeline:

1. `structural_screen.py` examines the original story BEFORE narrative cleanup to reject multi-story/multichapter books.
2. `parser.py` performs narrative extraction using the earlier conservative safeguards.
3. `frontmatter_precision.py` applies **one narrowly supported forward-trimming rule** to remove a short italicized magazine promo blurb immediately before a decorative separator and an ordinary prose paragraph.

The extra rule was selected using the 1,318 training records only, without retuning it to the previously held-back testing JSON. The previously held-back set has, however, been examined during previous development and must not be considered independent in future work.

## Measured training results

| Metric | Previous version | Revised version |
|---|---:|---:|
| Training records | 1,318 | 1,318 |
| Alignable | 1,316 | 1,316 |
| Exact starts | 659 | 682 |
| Stories retaining front matter | 654 | 631 |
| Excess front-matter physical lines | 6,332 | 6,125 |
| Stories with late starts (narrative loss) | 3 | 3 |
| Narrative physical lines lost | 6 | 6 |

23 specific training examples improved, 207 excess physical lines were removed, with no new or increased narrative loss in the assessable training data. **The rule covers only a minority of the 654 extra-front-matter cases.** This is intentional; aggressive rules caused real narrative loss during prototyping. The first, broader rule additionally skipped original narrative in Gutenberg 59224 and 64963; the final narrow rule avoids both. A synthetic multi-paragraph prologue regression was also added.

The counts measure *narrative starting points* in excerpts, not full-story accuracy or rejection precision. Some 1,648 verified examples can actually be ineligible multistory works; screening needs complete original texts.

## Installing into LCATS

Place these files inside `lcats/gatherers/mass_quantities/` (keep a backup of existing code):

- `parser.py` (updated)
- `gatherer.py` (included, unchanged from previous two-stage release)
- `structural_screen.py` (unchanged)
- `boundary_features.py` (unchanged)
- **`frontmatter_precision.py` (new)**

`parser.py` now includes:

```python
from frontmatter_precision import refine_promotional_blurb_boundary
# ... after all conservative boundary guards, before output cleanup:
lo = refine_promotional_blurb_boundary(lines, lo, hi, title, authors, warnings)
```

The modified LCATS parser supports package-relative imports as well as direct-file imports, so the helper modules can be found in a normal `lcats.gatherers.mass_quantities` installation.

`gutenberg_extractor.py` is a standalone version that uses top-level imports and can be exercised without installing LCATS.

**Important:** The `parser.py` shipped here relies on the LCATS package and cannot be imported in a standalone folder without LCATS installed. Its syntax was compiled successfully; the `gutenberg_extractor.py` version was executed against a training story.

## Reproducing the study

From the package directory, run:

```bash
python study_frontmatter.py
python -m unittest test_frontmatter_precision test_two_stage_structure -v
```

`study_frontmatter.py` writes `frontmatter_training_summary.json` and `frontmatter_training_results.csv`. Files `training.json` and `testing.json` preserve the previous split unchanged. The testing records are included for repeatability but are not used in this experiment.

**Safety:** This new rule moves a boundary *forward*, unlike the earlier backtracking safeguards, so it is inherently riskier. It applies only when the special combination of teaser, nearby separator, candidate prose, and preceding title-page/credit formatting is present. For ambiguous text, it makes no change. Use independent new annotations to validate further changes before production rollout.
