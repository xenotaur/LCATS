"""Regression examples are taken from TRAINING, not from held-back testing."""
import json, unittest
from pathlib import Path
from evaluate import reference_line, estimate
from structural_screen import inspect_structure

DATA = {r['gutenberg_id']:r for r in json.loads((Path(__file__).parent/'training.json').read_text())}

class BoundaryFeatureTests(unittest.TestCase):
    def test_training_recoveries(self):
        for sid in (26772,21279,23003,29632,33608,29889):
            with self.subTest(gutenberg_id=sid):
                row=DATA[sid]
                self.assertLessEqual(estimate(row,guarded=True),reference_line(row))

    def test_only_moves_earlier(self):
        for row in DATA.values():
            with self.subTest(id=row['gutenberg_id']):
                self.assertLessEqual(estimate(row,guarded=True),estimate(row,guarded=False))

    def test_blank_lines_alone_not_a_rule(self):
        from boundary_features import preserve_structural_opening
        lines=['A paragraph that resembles narrative but lacks structural anchor.', '', '',
               'This is another paragraph.', '', '', 'The next one.']
        self.assertEqual(preserve_structural_opening(
            lines,6,len(lines),[],[],title_match=lambda *a:None,
            author_match=lambda *a:None,warnings=[]),6)

    def test_single_section_not_rejected(self):
        row=DATA[23357]
        self.assertFalse(inspect_structure(row['original_opening']).reject)
        # The reviewed excerpt stops before the next section. Full-source
        # screening should see additional Roman headings if present.
