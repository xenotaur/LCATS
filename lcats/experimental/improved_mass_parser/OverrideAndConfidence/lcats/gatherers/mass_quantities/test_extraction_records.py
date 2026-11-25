import json
import tempfile
import unittest
from pathlib import Path
from extraction_records import (
    apply_override, extraction_record, load_override, save_extraction_record,
    opening_lines, _line_anchor
)


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.override = {
            'gutenberg_id': 42, 'title': ['A Story'], 'authors': ['Writer'],
            'original_opening': 'TITLE\n\nFirst narrative sentence here today.\n',
            'first_narrative_text': 'First narrative sentence here today.\n\nAnother sentence about the story now.\n',
            'override_datetime': '2026-11-24T00:00:00+00:00'
        }
        self.body = 'A promotional blurb.\n\nFirst narrative sentence here today.\n\nAnother sentence about the story now.\n\nEnd.\n'

    def test_override_removes_only_prefix(self):
        body = apply_override(self.body, self.override, gutenberg_id=42, title='A Story')
        self.assertEqual(body, 'First narrative sentence here today.\n\nAnother sentence about the story now.\n\nEnd.\n')

    def test_no_false_short_heading_match(self):
        override=dict(self.override,first_narrative_text='SCENE\n')
        with self.assertRaises(ValueError):
            apply_override(self.body, override, gutenberg_id=42,title='A Story')

    def test_broken_anchor_does_not_publish(self):
        with self.assertRaises(ValueError):
            apply_override('Something completely different.\n',self.override,gutenberg_id=42,title='A Story')

    def test_wrong_id_fails(self):
        with self.assertRaises(ValueError):
            apply_override(self.body,self.override,gutenberg_id=43,title='A Story')

    def test_duplicate_anchor_fails(self):
        with self.assertRaises(ValueError):
            apply_override(self.body+self.body,self.override,gutenberg_id=42,title='A Story')

    def test_read_and_write(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t); (d/'override.json').write_text(json.dumps(self.override))
            self.assertEqual(load_override(d,gutenberg_id=42,title='A Story')['gutenberg_id'],42)
            self.assertEqual((d/'override.json').read_text(),json.dumps(self.override))
            record=extraction_record(gutenberg_id=42,title='A Story',authors=['Writer'],raw_text='\n\nFirst\nSecond\n',extracted_body=self.body,overridden=True,raw_lines=3,extracted_lines=2)
            self.assertEqual(record['original_opening'],'\n\nFirst\n')
            self.assertEqual(record['first_narrative_text'],'A promotional blurb.\n\n')
            self.assertIn('extraction_datetime',record)
            self.assertEqual(record['confidence'], 'low')
            with self.assertRaises(FileNotFoundError):
                save_extraction_record(d,record)
            (d/'story.json').write_text('{}')
            p=save_extraction_record(d,record)
            self.assertEqual(json.loads(p.read_text()),record)
            self.assertEqual((d/'override.json').read_text(),json.dumps(self.override))

    def test_confidence_values_and_validation(self):
        kwargs=dict(gutenberg_id=42,title='A Story',authors=['Writer'],
                    raw_text='Title\n', extracted_body=self.body, overridden=False)
        for level in ('high','medium','low'):
            self.assertEqual(extraction_record(**kwargs,confidence=level)['confidence'], level)
        for invalid in ('unknown', 'HIGH', None, ''):
            with self.assertRaises(ValueError):
                extraction_record(**kwargs,confidence=invalid)

    def test_missing_override_is_normal(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertIsNone(load_override(t,gutenberg_id=42,title='A Story'))

    def test_original_newlines_untouched(self):
        self.assertEqual(opening_lines('\n\na\n\nb\n',4),'\n\na\n\n')


if __name__ == '__main__': unittest.main()
