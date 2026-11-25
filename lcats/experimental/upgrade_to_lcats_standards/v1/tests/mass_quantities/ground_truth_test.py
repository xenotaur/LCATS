import json
import unittest
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / 'ground_truth.json'

class GroundTruthTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads(DATA.read_text(encoding='utf-8'))
        cls.by_id = {row['gutenberg_id']: row for row in cls.rows}

    def test_unique_1648_verified_records(self):
        self.assertEqual(len(self.rows), 1648)
        self.assertEqual(len(self.by_id), 1648)
        self.assertTrue(all((row['review_status'] == 'verified' for row in self.rows)))

    def test_required_fields(self):
        for row in self.rows:
            with self.subTest(id=row['gutenberg_id']):
                for field in ('title', 'authors', 'original_opening', 'first_narrative_text', 'physical_lines_included'):
                    self.assertIn(field, row)

    def test_24247_keeps_real_opening(self):
        self.assertTrue(self.by_id[24247]['first_narrative_text'].startswith('Joe Prantera called softly'))

    def test_63930_stray_character_removed(self):
        self.assertTrue(self.by_id[63930]['first_narrative_text'].startswith('When the Martians had built'))

    def test_27013_promotional_teaser_excluded(self):
        row = self.by_id[27013]
        self.assertTrue(row['first_narrative_text'].startswith('The paper had gone to press'))
        self.assertNotIn('Weird are the conditions', row['first_narrative_text'][:120])

    def test_29897_starts_with_dialogue(self):
        self.assertTrue(self.by_id[29897]['first_narrative_text'].lstrip().startswith('"Plato!"'))
if __name__ == '__main__':
    unittest.main()
