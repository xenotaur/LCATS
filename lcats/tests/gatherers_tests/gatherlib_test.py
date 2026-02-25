"""Tests for the Anderson gatherer module."""

import unittest
from unittest.mock import patch, MagicMock

from bs4 import BeautifulSoup
import json

from lcats.gatherers import gatherlib


EXAMPLE_DIRECTORY = "test_example_directory"


EXAMPLE_GUTENBERG = "https://www.gutenberg.org/cache/epub/1597/pg1597-images.html"


EXAMPLE_HEADINGS = [
    ("swineherd", "THE SWINEHERD", "Anderson - The Swineherd"),
    ("real_princess", "THE REAL PRINCESS", "Anderson - The Real Princess"),
    ("shoes_of_fortune", "THE SHOES OF FORTUNE", "Anderson - The Shoes Of Fortune"),
]


class TestFindParagraphsAndersonfairytales(unittest.TestCase):
    """Unit tests for find_paragraphs_andersonfairytales."""

    def _make_soup(self, html):
        return BeautifulSoup(html, "lxml")

    def test_returns_paragraphs_after_heading(self):
        """Returns joined paragraph text when heading is found."""
        html = """
        <html><body>
        <h2>THE BELL</h2>
        <p>First paragraph.</p>
        <p>Second paragraph.</p>
        </body></html>
        """
        soup = self._make_soup(html)
        result = gatherlib.find_paragraphs(soup, "THE BELL")
        self.assertIn("First paragraph.", result)
        self.assertIn("Second paragraph.", result)

    def test_returns_none_when_heading_not_found(self):
        """Returns None when the heading is not present."""
        html = "<html><body><h2>SOMETHING ELSE</h2><p>Text.</p></body></html>"
        soup = self._make_soup(html)
        result = gatherlib.find_paragraphs(soup, "THE BELL")
        self.assertIsNone(result)

    def test_stops_at_next_h2(self):
        """Does not include paragraphs from following h2 sections."""
        html = """
        <html><body>
        <h2>THE BELL</h2>
        <p>Bell text.</p>
        <h2>THE SHADOW</h2>
        <p>Shadow text.</p>
        </body></html>
        """
        soup = self._make_soup(html)
        result = gatherlib.find_paragraphs(soup, "THE BELL")
        self.assertIn("Bell text.", result)
        self.assertNotIn("Shadow text.", result)

    def test_stops_at_div(self):
        """Does not include content after a div sibling."""
        html = """
        <html><body>
        <h2>THE BELL</h2>
        <p>Bell text.</p>
        <div><p>Div content.</p></div>
        </body></html>
        """
        soup = self._make_soup(html)
        result = gatherlib.find_paragraphs(soup, "THE BELL")
        self.assertIn("Bell text.", result)
        self.assertNotIn("Div content.", result)

    def test_includes_pre_tags(self):
        """Includes pre-formatted text blocks."""
        html = """
        <html><body>
        <h2>THE BELL</h2>
        <pre>Preformatted text.</pre>
        </body></html>
        """
        soup = self._make_soup(html)
        result = gatherlib.find_paragraphs(soup, "THE BELL")
        self.assertIn("Preformatted text.", result)

    def test_partial_heading_match(self):
        """Heading matching is a substring check."""
        html = """
        <html><body>
        <h2>THE BELL AND THE TOWER</h2>
        <p>Some content.</p>
        </body></html>
        """
        soup = self._make_soup(html)
        result = gatherlib.find_paragraphs(soup, "THE BELL")
        self.assertIsNotNone(result)
        self.assertIn("Some content.", result)

    def test_returns_empty_string_when_no_paragraphs(self):
        """Returns empty string when heading found but no paragraph siblings."""
        html = "<html><body><h2>THE BELL</h2></body></html>"
        soup = self._make_soup(html)
        result = gatherlib.find_paragraphs(soup, "THE BELL")
        self.assertEqual(result, "")


class TestCreateDownloadCallback(unittest.TestCase):
    """Unit tests for create_download_callback."""

    def _make_html_with_story(self, heading_text, para_text):
        return f"""
        <html><body>
        <h2>{heading_text}</h2>
        <p>{para_text}</p>
        </body></html>
        """

    def test_successful_callback_returns_tuple(self):
        """Callback returns (description, text, metadata) on valid HTML."""
        html = self._make_html_with_story("THE BELL", "Once upon a time.")
        callback = gatherlib.create_download_callback(
            story_name="bell",
            url="http://example.com/story",
            start_heading_text="THE BELL",
            description="Anderson - The Bell",
            author="Anderson",
            year=1911,
        )
        description, text, metadata = callback(html)
        self.assertEqual(description, "Anderson - The Bell")
        self.assertIn("Once upon a time.", text)
        self.assertEqual(metadata["name"], "bell")
        self.assertEqual(metadata["author"], "Anderson")
        self.assertEqual(metadata["year"], 1911)
        self.assertEqual(metadata["url"], "http://example.com/story")

    def test_callback_raises_on_none_contents(self):
        """Callback raises ValueError when contents is None."""
        callback = gatherlib.create_download_callback(
            story_name="bell",
            url="http://example.com/story",
            start_heading_text="THE BELL",
            description="Anderson - The Bell",
            author="Anderson",
            year=1911,
        )
        with self.assertRaises(ValueError):
            callback(None)

    def test_callback_raises_when_heading_not_found(self):
        """Callback raises ValueError when heading is not found in HTML."""
        html = "<html><body><h2>OTHER HEADING</h2><p>Text.</p></body></html>"
        callback = gatherlib.create_download_callback(
            story_name="bell",
            url="http://example.com/story",
            start_heading_text="THE BELL",
            description="Anderson - The Bell",
            author="Anderson",
            year=1911,
        )
        with self.assertRaises(ValueError):
            callback(html)

    def test_metadata_structure_is_json_serializable(self):
        """Metadata returned by callback can be serialized to JSON."""

        html = self._make_html_with_story("THE SHADOW", "A story about shadows.")
        callback = gatherlib.create_download_callback(
            story_name="shadow",
            url="http://example.com/shadow",
            start_heading_text="THE SHADOW",
            description="Anderson - The Shadow",
            author="Anderson",
            year=1911,
        )
        description, text, metadata = callback(html)
        # Should not raise
        json.dumps({"name": description, "body": text, "metadata": metadata})


class TestGather(unittest.TestCase):
    """Unit tests for the gather() function."""

    @patch("lcats.gatherers.gatherlib.downloaders.DataGatherer")
    def test_gather_calls_download_for_each_heading(self, mock_gatherer_cls):
        """gather() calls download once per entry in ANDERSON_HEADINGS."""
        mock_instance = MagicMock()
        mock_instance.downloads = {}
        mock_gatherer_cls.return_value = mock_instance

        gatherlib.gather(
            corpus="Anderson",
            target_directory=EXAMPLE_DIRECTORY,
            description="Anderson stories from the Gutenberg Project.",
            license_text="Public domain, from Project Gutenberg.",
            author="Anderson",
            year=1911,
            headings=EXAMPLE_HEADINGS,
            gutenberg_url=EXAMPLE_GUTENBERG,
            verbose=False,
        )

        self.assertEqual(mock_instance.download.call_count, len(EXAMPLE_HEADINGS))

    @patch("lcats.gatherers.gatherlib.downloaders.DataGatherer")
    def test_gather_returns_downloads(self, mock_gatherer_cls):
        """gather() returns the downloads dict from the DataGatherer."""
        mock_instance = MagicMock()
        expected = {"snow_queen": "/some/path.json"}
        mock_instance.downloads = expected
        mock_gatherer_cls.return_value = mock_instance

        result = gatherlib.gather(
            corpus="Anderson",
            target_directory=EXAMPLE_DIRECTORY,
            description="Anderson stories from the Gutenberg Project.",
            license_text="Public domain, from Project Gutenberg.",
            author="Anderson",
            year=1911,
            headings=EXAMPLE_HEADINGS,
            gutenberg_url=EXAMPLE_GUTENBERG,
            verbose=False,
        )

        self.assertIs(result, expected)

    @patch("lcats.gatherers.gatherlib.downloaders.DataGatherer")
    def test_gather_uses_correct_target_directory(self, mock_gatherer_cls):
        """gather() instantiates DataGatherer with the TARGET_DIRECTORY name."""
        mock_instance = MagicMock()
        mock_instance.downloads = {}
        mock_gatherer_cls.return_value = mock_instance

        gatherlib.gather(
            corpus="Anderson",
            target_directory=EXAMPLE_DIRECTORY,
            description="Anderson stories from the Gutenberg Project.",
            license_text="Public domain, from Project Gutenberg.",
            author="Anderson",
            year=1911,
            headings=EXAMPLE_HEADINGS,
            gutenberg_url=EXAMPLE_GUTENBERG,
            verbose=False,
        )

        args, _ = mock_gatherer_cls.call_args
        self.assertEqual(args[0], EXAMPLE_DIRECTORY)


if __name__ == "__main__":
    unittest.main()
