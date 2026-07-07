"""Tests for the Sherlock Holmes gatherer module."""

import json
import unittest
from unittest.mock import patch, MagicMock

from bs4 import BeautifulSoup

from lcats.gatherers.sherlock import gatherer


class TestFindParagraphsAdventures(unittest.TestCase):
    """Unit tests for find_paragraphs_adventures."""

    def _make_soup(self, html):
        return BeautifulSoup(html, "lxml")

    def test_returns_paragraphs_after_heading(self):
        """Returns joined paragraph text when heading is found."""
        html = """
        <html><body>
        <h2>A SCANDAL IN BOHEMIA</h2>
        <p>First paragraph.</p>
        <p>Second paragraph.</p>
        </body></html>
        """
        soup = self._make_soup(html)
        result = gatherer.find_paragraphs_adventures(soup, "A SCANDAL IN BOHEMIA")
        self.assertIn("First paragraph.", result)
        self.assertIn("Second paragraph.", result)

    def test_returns_none_when_heading_not_found(self):
        """Returns None when the heading is not present."""
        html = "<html><body><h2>SOMETHING ELSE</h2><p>Text.</p></body></html>"
        soup = self._make_soup(html)
        result = gatherer.find_paragraphs_adventures(soup, "A SCANDAL IN BOHEMIA")
        self.assertIsNone(result)

    def test_stops_at_next_h2(self):
        """Does not include paragraphs from following h2 sections."""
        html = """
        <html><body>
        <h2>A SCANDAL IN BOHEMIA</h2>
        <p>Bohemia text.</p>
        <h2>THE RED-HEADED LEAGUE</h2>
        <p>League text.</p>
        </body></html>
        """
        soup = self._make_soup(html)
        result = gatherer.find_paragraphs_adventures(soup, "A SCANDAL IN BOHEMIA")
        self.assertIn("Bohemia text.", result)
        self.assertNotIn("League text.", result)

    def test_stops_at_div(self):
        """Does not include content after a div sibling."""
        html = """
        <html><body>
        <h2>A SCANDAL IN BOHEMIA</h2>
        <p>Bohemia text.</p>
        <div><p>Div content.</p></div>
        </body></html>
        """
        soup = self._make_soup(html)
        result = gatherer.find_paragraphs_adventures(soup, "A SCANDAL IN BOHEMIA")
        self.assertIn("Bohemia text.", result)
        self.assertNotIn("Div content.", result)

    def test_matches_h3_heading(self):
        """Heading matching also works for h3 tags."""
        html = """
        <html><body>
        <h3>A SCANDAL IN BOHEMIA</h3>
        <p>Story text.</p>
        </body></html>
        """
        soup = self._make_soup(html)
        result = gatherer.find_paragraphs_adventures(soup, "A SCANDAL IN BOHEMIA")
        self.assertIn("Story text.", result)

    def test_partial_heading_match(self):
        """Heading matching is a substring check."""
        html = """
        <html><body>
        <h2>A SCANDAL IN BOHEMIA AND ELSEWHERE</h2>
        <p>Some content.</p>
        </body></html>
        """
        soup = self._make_soup(html)
        result = gatherer.find_paragraphs_adventures(soup, "A SCANDAL IN BOHEMIA")
        self.assertIsNotNone(result)
        self.assertIn("Some content.", result)

    def test_returns_empty_string_when_no_paragraphs(self):
        """Returns empty string when heading found but no paragraph siblings."""
        html = "<html><body><h2>A SCANDAL IN BOHEMIA</h2></body></html>"
        soup = self._make_soup(html)
        result = gatherer.find_paragraphs_adventures(soup, "A SCANDAL IN BOHEMIA")
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
        html = self._make_html_with_story(
            "A SCANDAL IN BOHEMIA", "To Sherlock Holmes she is always the woman."
        )
        callback = gatherer.create_download_callback(
            story_name="scandal_in_bohemia",
            url="http://example.com/sherlock",
            start_heading_text="A SCANDAL IN BOHEMIA",
            description="Sherlock Holmes - A Scandal in Bohemia",
        )
        description, text, metadata = callback(html)
        self.assertEqual(description, "Sherlock Holmes - A Scandal in Bohemia")
        self.assertIn("To Sherlock Holmes she is always the woman.", text)
        self.assertEqual(metadata["name"], "scandal_in_bohemia")
        self.assertEqual(metadata["author"], "Arthur Conan Doyle")
        self.assertEqual(metadata["year"], 1891)
        self.assertEqual(metadata["url"], "http://example.com/sherlock")

    def test_callback_raises_on_none_contents(self):
        """Callback raises ValueError when contents is None."""
        callback = gatherer.create_download_callback(
            story_name="scandal_in_bohemia",
            url="http://example.com/sherlock",
            start_heading_text="A SCANDAL IN BOHEMIA",
            description="Sherlock Holmes - A Scandal in Bohemia",
        )
        with self.assertRaises(ValueError):
            callback(None)

    def test_callback_raises_when_heading_not_found(self):
        """Callback raises ValueError when heading is not found in HTML."""
        html = "<html><body><h2>OTHER HEADING</h2><p>Text.</p></body></html>"
        callback = gatherer.create_download_callback(
            story_name="scandal_in_bohemia",
            url="http://example.com/sherlock",
            start_heading_text="A SCANDAL IN BOHEMIA",
            description="Sherlock Holmes - A Scandal in Bohemia",
        )
        with self.assertRaises(ValueError):
            callback(html)

    def test_metadata_structure_is_json_serializable(self):
        """Metadata returned by callback can be serialized to JSON."""
        html = self._make_html_with_story(
            "THE RED-HEADED LEAGUE", "It was in the year 1890."
        )
        callback = gatherer.create_download_callback(
            story_name="red_headed_league",
            url="http://example.com/sherlock",
            start_heading_text="THE RED-HEADED LEAGUE",
            description="Sherlock Holmes - The Red-Headed League",
        )
        description, text, metadata = callback(html)
        # Should not raise
        json.dumps({"name": description, "body": text, "metadata": metadata})


class TestGather(unittest.TestCase):
    """Unit tests for the gather() function."""

    @patch("lcats.gatherers.sherlock.gatherer.downloaders.DataGatherer")
    def test_gather_calls_download_for_each_heading(self, mock_gatherer_cls):
        """gather() calls download once per entry in ADVENTURES_HEADINGS."""
        mock_instance = MagicMock()
        mock_instance.downloads = {}
        mock_gatherer_cls.return_value = mock_instance

        gatherer.gather()

        self.assertEqual(
            mock_instance.download.call_count, len(gatherer.ADVENTURES_HEADINGS)
        )

    @patch("lcats.gatherers.sherlock.gatherer.downloaders.DataGatherer")
    def test_gather_returns_downloads(self, mock_gatherer_cls):
        """gather() returns the downloads dict from the DataGatherer."""
        mock_instance = MagicMock()
        expected = {"scandal_in_bohemia": "/some/path.json"}
        mock_instance.downloads = expected
        mock_gatherer_cls.return_value = mock_instance

        result = gatherer.gather()

        self.assertIs(result, expected)

    @patch("lcats.gatherers.sherlock.gatherer.downloaders.DataGatherer")
    def test_gather_uses_correct_target_directory(self, mock_gatherer_cls):
        """gather() instantiates DataGatherer with TARGET_DIRECTORY='sherlock'."""
        mock_instance = MagicMock()
        mock_instance.downloads = {}
        mock_gatherer_cls.return_value = mock_instance

        gatherer.gather()

        args, _ = mock_gatherer_cls.call_args
        self.assertEqual(args[0], gatherer.TARGET_DIRECTORY)


if __name__ == "__main__":
    unittest.main()
