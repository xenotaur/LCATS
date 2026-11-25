import unittest
from . import _paths
import structural_screen
import gutenberg_extractor

class StructuralScreenTest(unittest.TestCase):

    def test_contents_list_rejected_before_cleanup(self):
        raw = 'STORY\nBy Writer\n\nCONTENTS\nFIRST STORY\nSECOND STORY\n\nFIRST STORY\n\nOnce upon a time.\n'
        self.assertEqual(structural_screen.inspect_structure(raw).reason, 'contents_list')
        result = gutenberg_extractor.screen_and_clean_gutenberg_story(raw, title=['STORY'], authors=['Writer'])
        self.assertTrue(result['rejected'])
        self.assertIsNone(result['body'])

    def test_two_chapters(self):
        self.assertTrue(structural_screen.inspect_structure('TITLE\nCHAPTER I\nFirst.\nCHAPTER II\nSecond.').reject)

    def test_numbered_parts(self):
        raw = 'TITLE\nBy Writer\n\n_1. The Shadow on the Chimney_\n\nSome narrative text.\nMore narrative text.\nA third line.\nA fourth line.\n\n_2. A Passer in the Storm_\n\nMore text.\n'
        self.assertEqual(structural_screen.inspect_structure(raw).reason, 'multiple_numbered_sections')

    def test_roman_numbered_headings(self):
        raw = "MISS MEHETABEL'S SON.\nBy Thomas Bailey Aldrich\nI. THE OLD TAVERN AT BAYLEY'S FOUR CORNERS.\n\n" + 'You will not find Greenton on any map.\n' * 4 + '\nII. THE CASE OF SILAS JAFFREY.\n\nA man with a passion for old things.\n'
        self.assertTrue(structural_screen.inspect_structure(raw).reject)

    def test_single_section_allowed(self):
        self.assertFalse(structural_screen.inspect_structure('TITLE\n\nI. FIRST SECTION.\n\nA paragraph.').reject)

    def test_transcriber_list_not_contents(self):
        raw = "[Transcriber's Note:\n1. Corrected typo.\n2. Fixed punctuation.\n]\nTITLE\n\nOnce upon a time."
        self.assertFalse(structural_screen.inspect_structure(raw).reject)

    def test_advertising_catalog(self):
        raw = 'MERRIAM VIOLET SERIES\nI.--A Man and His Model. By Anthony Hope.\nII.--The Body-Snatcher. By R. L. Stevenson.\n\nTHE SNOWBALL\n\nNarrative.'
        self.assertFalse(structural_screen.inspect_structure(raw).reject)
if __name__ == '__main__':
    unittest.main()
