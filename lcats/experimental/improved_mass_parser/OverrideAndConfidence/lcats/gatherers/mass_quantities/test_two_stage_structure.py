"""No-network regression tests for the raw structural gate."""
import unittest
import zipfile
from pathlib import Path
from structural_screen import inspect_structure
from gutenberg_extractor import screen_and_clean_gutenberg_story

ROOT = Path(__file__).resolve().parent


class StructuralTests(unittest.TestCase):
    def test_contents_multiple_stories(self):
        raw = ('TITLE\nBy Writer\n\nCONTENTS\n\nFIRST STORY\nSECOND STORY\n\n'
               'FIRST STORY\n\nOnce upon a time the narrative began.\n')
        d = inspect_structure(raw)
        self.assertTrue(d.reject)
        self.assertEqual(d.reason, 'contents_list')

    def test_repeated_chapters(self):
        raw = ('THE WORK\nBy Writer\n\nCHAPTER I\n\nFirst story scene.\n'
               '\nCHAPTER II\n\nThe next scene.\n')
        self.assertTrue(inspect_structure(raw).reject)

    def test_italic_numbered_sections(self):
        raw = ('TITLE\nBy Writer\n\n_1. The Shadow on the Chimney_\n\n'
               'Some narrative text.\nMore narrative text.\nA third line.\n'
               'A fourth line.\n\n_2. A Passer in the Storm_\n\nMore text.\n')
        self.assertEqual(inspect_structure(raw).reason,'multiple_numbered_sections')

    def test_lone_numbered_heading_not_enough(self):
        self.assertFalse(inspect_structure('STORY\nBy A. Writer\n\nI\n\nA paragraph.').reject)

    def test_title_page_not_counted(self):
        self.assertFalse(inspect_structure('THE STORY\nBY JANE DOE\nPUBLISHED 1900\n\nSome text.').reject)

    def test_bracketed_numbered_comments_ignored(self):
        raw = ("[Transcriber's Note:\n1. First correction.\n2. Second correction.\n]"
               '\nTITLE\n\nOnce upon a time.\n')
        self.assertFalse(inspect_structure(raw).reject)

    def test_advertising_catalog_not_chapters(self):
        raw = ('MERRIAM VIOLET SERIES\n\n'
               'I.--A Man and His Model. By Anthony Hope.\n'
               'II.--The Body-Snatcher. By Robert Louis Stevenson.\n'
               'III.--The Silence. By Marie Corelli.\n\n'
               'THE SNOWBALL\n\nNarrative.\n')
        self.assertFalse(inspect_structure(raw).reject)

    def test_standalone_two_stage_rejects_before_cleaning(self):
        source='TITLE\nBy Writer\n\nCONTENTS\nFIRST STORY\nSECOND STORY\n\n' \
               'FIRST STORY\n\nIt was dark and stormy.\n'
        result=screen_and_clean_gutenberg_story(source,title=['TITLE'],authors=['Writer'])
        self.assertTrue(result['rejected'])
        self.assertIsNone(result['body'])

    def test_real_local_archive_cases_if_available(self):
        expected = {63028:True,70486:True,71109:True,39216:False}
        for sid, wanted in expected.items():
            archive = None
            for path in ROOT.parent.glob('stories*.zip'):
                with zipfile.ZipFile(path) as z:
                    if f'{sid}.txt' in z.namelist():
                        archive = path
                        break
            if archive is None:
                continue
            with zipfile.ZipFile(archive) as z:
                raw = z.read(f'{sid}.txt').decode('utf-8-sig',errors='replace')
            with self.subTest(sid=sid):
                self.assertEqual(inspect_structure(raw).reject, wanted)


if __name__ == '__main__':
    unittest.main()

class AdditionalSectionTests(unittest.TestCase):
    def test_roman_numbered_titles_ending_with_period(self):
        raw = ("MISS MEHETABEL'S SON.\nBy Thomas Bailey Aldrich\n"
               "I. THE OLD TAVERN AT BAYLEY'S FOUR CORNERS.\n\n"
               "You will not find Greenton on any map.\n" * 4 +
               "\nII. THE CASE OF SILAS JAFFREY.\n\n"
               "A man with a passion for old things.\n")
        decision = inspect_structure(raw)
        self.assertTrue(decision.reject)
        self.assertEqual(decision.reason, 'multiple_numbered_sections')

    def test_single_roman_titled_section_not_sufficient(self):
        raw = ("SINGLE STORY\nBy Writer\n\n"
               "I. THE OLD TAVERN AT BAYLEY'S FOUR CORNERS.\n\n"
               "The story begins here.\n")
        self.assertFalse(inspect_structure(raw).reject)
