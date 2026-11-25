"""Offline regression/safety tests. Uses training examples only."""
import json
import unittest
from pathlib import Path
from evaluate import reference_line, estimate

HERE = Path(__file__).resolve().parent
TRAIN = json.loads((HERE / 'training.json').read_text(encoding='utf-8'))
BY_ID = {row['gutenberg_id']: row for row in TRAIN}


class ConservativeExtractionTests(unittest.TestCase):
    def test_split_is_disjoint_and_complete(self):
        test = json.loads((HERE / 'testing.json').read_text(encoding='utf-8'))
        train_ids = {r['gutenberg_id'] for r in TRAIN}
        test_ids = {r['gutenberg_id'] for r in test}
        self.assertEqual(len(TRAIN), 1318)
        self.assertEqual(len(test), 330)
        self.assertFalse(train_ids & test_ids)
        self.assertEqual(len(train_ids | test_ids), 1648)

    def test_guard_never_shifts_boundary_forward(self):
        for entry in TRAIN:
            with self.subTest(id=entry['gutenberg_id']):
                self.assertLessEqual(estimate(entry, guarded=True),
                                     estimate(entry, guarded=False))

    def test_training_italic_prologues_are_preserved(self):
        for gutenberg_id in (59224, 60393, 64963):
            record = BY_ID[gutenberg_id]
            reference = reference_line(record)
            self.assertIsNotNone(reference)
            self.assertLessEqual(estimate(record, guarded=True), reference)

    def test_verified_records_have_expected_fields(self):
        for record in TRAIN:
            self.assertEqual(record['review_status'], 'verified')
            for key in ('original_opening','first_narrative_text',
                        'physical_lines_included','title','authors'):
                self.assertIn(key,record)


if __name__ == '__main__':
    unittest.main()
