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

    def test_training_post_transcriber_markers(self):
        # Only training examples are used to establish this regression.
        for gutenberg_id in (64795, 71589, 60871, 73304, 60401,
                             65730, 58730, 71109, 65874, 49767,
                             60582, 64530, 65676):
            entry = BY_ID[gutenberg_id]
            reference = reference_line(entry)
            self.assertIsNotNone(reference)
            self.assertLessEqual(estimate(entry, guarded=True), reference,
                                 msg=f'Gutenberg {gutenberg_id}')

    def test_sidenote_and_illustration_synthetic_openings(self):
        import gutenberg_extractor as parser
        cases = [
            ['STORY NAME', 'By Sample Writer',
             '[Sidenote: A brief aside.]', '', '',
             '"Come closer," she whispered.', '', 'Something happened.'],
            ['STORY NAME', 'By Sample Writer',
             '[Illustration:', '  A sample picture', ']', '',
             '_There was a cry in the night._', '', 'The next paragraph.'],
        ]
        for lines in cases:
            with self.subTest(marker=lines[2]):
                warnings = []
                found = parser._bracketed_marker_narrative_guard(
                    lines, len(lines)-1, len(lines), ['Story Name'],
                    ['Writer, Sample'], [], warnings)
                self.assertEqual(found, next(i for i, v in enumerate(lines)
                                            if '"Come closer' in v or '_There was a cry' in v))

    def test_marker_followed_by_title_is_not_narrative(self):
        import gutenberg_extractor as parser
        lines = ['[Transcriber\'s Note: End of note.]', '',
                 'STORY NAME', '', 'By Sample Writer', '',
                 'The story really starts here.', '', 'The next sentence.']
        self.assertEqual(parser._bracketed_marker_narrative_guard(
            lines, 8, len(lines), ['Story Name'],
            ['Writer, Sample'], [], []), 8)

    def test_verified_records_have_expected_fields(self):
        for record in TRAIN:
            self.assertEqual(record['review_status'], 'verified')
            for key in ('original_opening','first_narrative_text',
                        'physical_lines_included','title','authors'):
                self.assertIn(key,record)


if __name__ == '__main__':
    unittest.main()

class DatedSceneHeadingTests(unittest.TestCase):
    def test_date_and_location_synthetic(self):
        import gutenberg_extractor as parser
        cases = [
            (['SAMPLE STORY', 'By Sample Writer', '', 'October 10, 2119',
              'New San Francisco', '', 'The fictional narrative begins.'], 3),
            (['SAMPLE STORY', 'By Sample Writer', '', 'Sandeman, 2624 CE',
              '', 'The fictional narrative begins.'], 3),
        ]
        for lines, expected in cases:
            with self.subTest(lines=lines):
                self.assertEqual(parser._dated_scene_opening_guard(
                    lines, len(lines)-1, len(lines), ['Sample Story'],
                    ['Writer, Sample'], [], []), expected)

    def test_no_fictional_date_no_change(self):
        import gutenberg_extractor as parser
        lines = ['SAMPLE STORY', 'By Sample Writer', '', 'A promotional summary',
                 '', 'The narrative starts here.']
        self.assertEqual(parser._dated_scene_opening_guard(
            lines, 5, len(lines), ['Sample Story'],
            ['Writer, Sample'], [], []), 5)

    def test_human_correction_27013(self):
        test = json.loads((HERE / 'testing.json').read_text(encoding='utf-8'))
        story = next(r for r in test if r['gutenberg_id'] == 27013)
        self.assertTrue(story['first_narrative_text'].startswith(
            'The paper had gone to press'))
        self.assertEqual(estimate(story, guarded=True), reference_line(story))
