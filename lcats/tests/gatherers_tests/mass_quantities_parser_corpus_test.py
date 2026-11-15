"""Optional real-text regression tests for Gutenberg parser boundaries.

The ordinary parser unit tests are self-contained. This file uses archived
Gutenberg source texts and the old new.zip metadata as optional fixtures.

Set LCATS_GUTENBERG_FIXTURES to the directory containing stories1.zip through
stories7.zip, stories89.zip, and new.zip to enable these tests. Without that
environment variable this module skips cleanly (no network access).
"""

import json
import os
import re
import unittest
import zipfile
from pathlib import Path

from lcats.gatherers.mass_quantities import parser


FIXTURE_DIR = os.environ.get("LCATS_GUTENBERG_FIXTURES")


@unittest.skipUnless(FIXTURE_DIR, "Set LCATS_GUTENBERG_FIXTURES for source-based tests")
class GutenbergCorpusRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = Path(FIXTURE_DIR)
        cls.sources = {}
        cls.records = {}
        archive_names = ["stories%s.zip" % n for n in range(1, 8)]
        archive_names.append("stories89.zip")
        for archive_name in archive_names:
            with zipfile.ZipFile(cls.directory / archive_name) as archive:
                for entry in archive.namelist():
                    if re.fullmatch(r"\d+\.txt", entry):
                        story_id = int(entry.removesuffix(".txt"))
                        cls.sources[story_id] = archive.read(entry).decode(
                            "utf-8", "replace"
                        )
        with zipfile.ZipFile(cls.directory / "new.zip") as archive:
            for entry in archive.namelist():
                if not entry.endswith("story.json"):
                    continue
                record = json.loads(archive.read(entry))
                url = record.get("metadata", {}).get("url", "")
                match = re.search(r"/ebooks/(\d+)", url)
                if match is not None:
                    cls.records[int(match.group(1))] = record

    def extract(self, story_id):
        source = self.sources[story_id]
        record = self.records[story_id]
        title = [record["name"]]
        authors = record["author"]
        cleaned = parser.clean_gutenberg_story(source, title, authors)
        return parser._repair_verified_opening(
            story_id, source, title, authors, [], cleaned
        )

    def test_six_source_verified_narrative_openings(self):
        beginnings = {
            65347: "El outer-thought",
            24566: "JULY 18, 1949 A.D.",
            50940: "Numb with the terror that had dogged him",
            31964: "I never thought I'd like circus life",
            60393: "The first of the morons, as they were popularly called",
            65241: "Rick Mason's ship was still high over Mordarga",
        }
        for story_id, beginning in beginnings.items():
            with self.subTest(gutenberg_id=story_id):
                output = self.extract(story_id)
                self.assertTrue(output.startswith(beginning), repr(output[:150]))

    def test_limited_edition_printing_statements_removed(self):
        cases = {
            42640: "NINE HUNDRED AND FIFTY COPIES",
            69601: "TWO HUNDRED COPIES OF THIS BOOK",
        }
        for story_id, statement in cases.items():
            with self.subTest(gutenberg_id=story_id):
                output = self.extract(story_id)
                self.assertNotIn(statement, output)

    def test_previous_good_openings_are_not_discarded(self):
        openings = {
            26956: '"You are General James Rothwell?"',
            49767: '"Time," said the Grandmaster',
            51570: '"Baby Doll," George called',
            42640: "Life on this earth, my children",
        }
        for story_id, opening in openings.items():
            with self.subTest(gutenberg_id=story_id):
                output = self.extract(story_id)
                self.assertTrue(output.startswith(opening), repr(output[:150]))

    def test_verified_repairs_do_not_change_other_story_ids(self):
        sample = [19005, 19122, 22538, 2328, 26956, 49767, 51570, 51006, 63009]
        for story_id in sample:
            with self.subTest(gutenberg_id=story_id):
                original = self.sources[story_id]
                record = self.records[story_id]
                title = [record["name"]]
                authors = record["author"]
                base = parser.clean_gutenberg_story(original, title, authors)
                after = parser._repair_verified_opening(
                    story_id, original, title, authors, [], base
                )
                self.assertEqual(after, base)


if __name__ == "__main__":
    unittest.main()
