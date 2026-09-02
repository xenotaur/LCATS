"""Tests for the Sherlock Holmes gatherer module."""

import os
import tempfile
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


class TestGather(unittest.TestCase):
    """Unit tests for the gather() function.

    gather() is now a thin wrapper around gatherlib.gather() (WI-GATHER-0103).
    Per AGENTS.md's mocking philosophy (avoid heavy mocking; mock only at
    true boundaries), these mock DataGatherer -- the network/external
    boundary gatherlib.gather() itself mocks in its own tests
    (gatherlib_test.py) -- rather than gatherlib.gather() itself, so the
    real create_download_callback/find_paragraphs_adventures interaction
    still gets exercised end to end with real HTML (review finding,
    PR #421 -- mocking gatherlib.gather() directly, as an earlier version
    of this file did, only verifies mock calls and would not have caught a
    broken interaction between Sherlock's custom paragraph finder, the
    shared callback, and DataGatherer, which the retired
    TestCreateDownloadCallback tests used to cover)."""

    def setUp(self):
        # gather() delegates to gatherlib.gather() without overriding
        # log_dir, so it writes a real run log relative to the current
        # working directory by default (gatherlib.DEFAULT_GATHER_LOG_DIR).
        # Run each test from a throwaway directory so these unit tests
        # don't leave real log files behind in the repo checkout.
        self._tmp = tempfile.TemporaryDirectory()
        self._original_cwd = os.getcwd()
        os.chdir(self._tmp.name)

    def tearDown(self):
        os.chdir(self._original_cwd)
        self._tmp.cleanup()

    def _make_html_with_story(self, heading_text, para_text):
        return f"""
        <html><body>
        <h2>{heading_text}</h2>
        <p>{para_text}</p>
        </body></html>
        """

    @patch("lcats.gatherers.gatherlib.downloaders.DataGatherer")
    def test_gather_calls_download_for_each_heading(self, mock_gatherer_cls):
        """gather() calls download once per entry in ADVENTURES_HEADINGS."""
        mock_instance = MagicMock()
        mock_instance.downloads = {}
        mock_gatherer_cls.return_value = mock_instance

        gatherer.gather()

        self.assertEqual(
            mock_instance.download.call_count, len(gatherer.ADVENTURES_HEADINGS)
        )

    @patch("lcats.gatherers.gatherlib.downloaders.DataGatherer")
    def test_gather_returns_downloads(self, mock_gatherer_cls):
        """gather() returns the downloads dict from the DataGatherer."""
        mock_instance = MagicMock()
        expected = {"scandal_in_bohemia": "/some/path.json"}
        mock_instance.downloads = expected
        mock_gatherer_cls.return_value = mock_instance

        result = gatherer.gather()

        self.assertIs(result, expected)

    @patch("lcats.gatherers.gatherlib.downloaders.DataGatherer")
    def test_gather_uses_correct_target_directory(self, mock_gatherer_cls):
        """gather() instantiates DataGatherer with TARGET_DIRECTORY='sherlock'."""
        mock_instance = MagicMock()
        mock_instance.downloads = {}
        mock_gatherer_cls.return_value = mock_instance

        gatherer.gather()

        args, _ = mock_gatherer_cls.call_args
        self.assertEqual(args[0], gatherer.TARGET_DIRECTORY)

    @patch("lcats.gatherers.gatherlib.downloaders.DataGatherer")
    def test_gather_wires_real_paragraph_finder_through_the_download_callback(
        self, mock_gatherer_cls
    ):
        """The callback gather() hands to download() uses
        find_paragraphs_adventures on real HTML, not just a mocked
        gatherlib.gather() call -- the interaction the P1 review finding
        on PR #421 flagged as unverified."""
        mock_instance = MagicMock()
        mock_instance.downloads = {}
        mock_gatherer_cls.return_value = mock_instance

        gatherer.gather()

        first_filename, first_heading, first_title = gatherer.ADVENTURES_HEADINGS[0]
        (call_filename, call_url, callback), _ = mock_instance.download.call_args_list[
            0
        ]
        self.assertEqual(call_filename, first_filename)
        self.assertEqual(call_url, gatherer.ADVENTURES_GUTENBERG)

        html = self._make_html_with_story(
            first_heading, "To Sherlock Holmes she is always the woman."
        )
        description, text, metadata = callback(html)

        self.assertEqual(description, first_title)
        self.assertIn("To Sherlock Holmes she is always the woman.", text)
        self.assertEqual(metadata["name"], first_filename)
        self.assertEqual(metadata["author"], "Arthur Conan Doyle")
        self.assertEqual(metadata["year"], 1891)
        self.assertEqual(metadata["url"], gatherer.ADVENTURES_GUTENBERG)


if __name__ == "__main__":
    unittest.main()
