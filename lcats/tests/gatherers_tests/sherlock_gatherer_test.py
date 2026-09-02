"""Tests for the Sherlock Holmes gatherer module."""

import unittest
from unittest.mock import patch

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

    gather() is now a thin wrapper around gatherlib.gather() (WI-GATHER-0103);
    these tests replace the old direct-DataGatherer-construction tests and
    the retired create_download_callback tests, verifying gather() delegates
    with the correct sherlock-specific arguments instead.
    """

    @patch("lcats.gatherers.sherlock.gatherer.gatherlib.gather")
    def test_gather_calls_gatherlib_gather_with_expected_arguments(self, mock_gather):
        """gather() delegates to gatherlib.gather() with sherlock's arguments."""
        mock_gather.return_value = {"scandal_in_bohemia": "/some/path.json"}

        gatherer.gather()

        mock_gather.assert_called_once_with(
            corpus="Sherlock Holmes",
            target_directory=gatherer.TARGET_DIRECTORY,
            description="Sherlock Holmes stories from the Gutenberg Project.",
            license_text="Public domain, from Project Gutenberg.",
            author="Arthur Conan Doyle",
            year=1891,
            headings=gatherer.ADVENTURES_HEADINGS,
            gutenberg_url=gatherer.ADVENTURES_GUTENBERG,
            paragraph_finder=gatherer.find_paragraphs_adventures,
            verbose=False,
        )

    @patch("lcats.gatherers.sherlock.gatherer.gatherlib.gather")
    def test_gather_returns_gatherlib_gather_result(self, mock_gather):
        """gather() returns whatever gatherlib.gather() returns."""
        expected = {"scandal_in_bohemia": "/some/path.json"}
        mock_gather.return_value = expected

        result = gatherer.gather()

        self.assertIs(result, expected)


if __name__ == "__main__":
    unittest.main()
