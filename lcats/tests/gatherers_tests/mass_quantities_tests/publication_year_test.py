import json
import tempfile
import unittest
import pathlib
import types
from unittest import mock
from lcats.gatherers.mass_quantities import publication_year


class PublicationYearTest(unittest.TestCase):

    def make_source(self, text):
        metadata = types.SimpleNamespace(titles=["A Story"], authors=["Writer, A."])
        return types.SimpleNamespace(
            metadata=mock.Mock(return_value=metadata),
            read=mock.Mock(
                return_value=types.SimpleNamespace(
                    cleaned=types.SimpleNamespace(text=text)
                )
            ),
        )

    def test_month_and_year(self):
        self.assertEqual(
            publication_year.get_publication_date_from_text(
                "First published in May 1952"
            ),
            ("May", "1952"),
        )

    def test_year_without_month(self):
        self.assertEqual(
            publication_year.get_publication_date_from_text("First published in 1908"),
            (None, "1908"),
        )

    def test_copyright_fallback(self):
        self.assertEqual(
            publication_year.get_publication_date_from_text("Copyright 1918"),
            (None, "1918"),
        )

    def test_magazine_transcription(self):
        self.assertEqual(
            publication_year.get_publication_date_from_text(
                "[Transcriber's Note: This etext was produced from Galaxy Science Fiction October 1950.]"
            ),
            ("October", "1950"),
        )

    def test_explicit_first_pub_over_reprint(self):
        self.assertEqual(
            publication_year.get_publication_date_from_text(
                "First published in May 1952.\nReprinted in October 1958."
            ),
            ("May", "1952"),
        )

    def test_gutenberg_release_ignored(self):
        raw = "Release Date: July 15, 2022\n*** START OF THE PROJECT GUTENBERG EBOOK 123 ***\nStory.\n"
        self.assertEqual(
            publication_year.get_publication_date_from_text(raw), (None, None)
        )

    def test_fictional_date_ignored(self):
        self.assertEqual(
            publication_year.get_publication_date_from_text(
                "October 10, 2119\nNew San Francisco\nStory."
            ),
            (None, None),
        )

    def test_missing_date(self):
        self.assertEqual(
            publication_year.get_publication_date_from_text(""), (None, None)
        )

    def test_reject_nontext(self):
        with self.assertRaises(TypeError):
            publication_year.get_publication_date_from_text(None)

    def test_id_retrieves_once_without_saving(self):
        src = self.make_source("Published, September, 1908")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                publication_year.get_publication_date_from_id(
                    42, source=src, story_dir=tmp
                ),
                ("September", "1908"),
            )
            self.assertFalse((pathlib.Path(tmp) / "year.json").exists())
        src.metadata.assert_called_once_with(42)
        src.read.assert_called_once()

    def test_id_save_writes_year_json(self):
        src = self.make_source("First published in 1908")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                publication_year.get_publication_date_from_id(
                    42, source=src, save=True, story_dir=tmp
                ),
                (None, "1908"),
            )
            self.assertEqual(
                json.loads(
                    (pathlib.Path(tmp) / "year.json").read_text(encoding="utf-8")
                ),
                {
                    "gutenberg_id": 42,
                    "title": ["A Story"],
                    "authors": ["Writer, A."],
                    "deterministic_month": None,
                    "deterministic_year": "1908",
                },
            )

    def test_missing_metadata_does_not_read_or_save(self):
        src = types.SimpleNamespace(
            metadata=mock.Mock(return_value=None), read=mock.Mock()
        )
        self.assertEqual(
            publication_year.get_publication_date_from_id(42, source=src, save=True),
            (None, None),
        )
        src.read.assert_not_called()

    def test_download_failure_never_saves(self):
        src = self.make_source("Published, May 1908")
        src.read.side_effect = RuntimeError("network")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                publication_year.get_publication_date_from_id(
                    42, source=src, save=True, story_dir=tmp
                )
            self.assertFalse((pathlib.Path(tmp) / "year.json").exists())

    def test_invalid_ids(self):
        for value in (0, -1, True, "42"):
            with self.subTest(id=value):
                with self.assertRaises(ValueError):
                    publication_year.get_publication_date_from_id(
                        value, source=self.make_source("")
                    )


if __name__ == "__main__":
    unittest.main()
