"""Targeted historical bug regressions using reviewed original openings (no network)."""
import json
import unittest
import pathlib
from . import _paths
import evaluate
import study_frontmatter
ROOT = pathlib.Path(__file__).resolve().parents[2]
ROWS = {r['gutenberg_id']: r for r in json.loads((ROOT / 'ground_truth.json').read_text(encoding='utf-8'))}

class HistoricalRegressionTest(unittest.TestCase):

    def test_structural_opening_recoveries(self):
        for sid in (21279, 23003, 26772, 29632, 29889, 33608):
            with self.subTest(gutenberg_id=sid):
                row = ROWS[sid]
                start = evaluate.reference_line(row)
                self.assertIsNotNone(start)
                self.assertLessEqual(evaluate.estimate(row, guarded=True), start)

    def test_italicized_prologues_protected(self):
        for sid in (59224, 64963):
            with self.subTest(gutenberg_id=sid):
                row = ROWS[sid]
                before, _ = study_frontmatter.predict(row, apply_precision=False)
                after, _ = study_frontmatter.predict(row, apply_precision=True)
                self.assertEqual(before, after)

    def test_promotional_separator_examples(self):
        for sid in (32143, 31841, 33969, 31736, 32040, 32104):
            with self.subTest(gutenberg_id=sid):
                row = ROWS[sid]
                before, _ = study_frontmatter.predict(row, apply_precision=False)
                after, _ = study_frontmatter.predict(row, apply_precision=True)
                self.assertLess(before, after)
if __name__ == '__main__':
    unittest.main()
