"""Tests for individual gatherer paragraph finders."""

import unittest

from bs4 import BeautifulSoup

from lcats.gatherers.wilde_happy_prince.gatherer import find_paragraphs_happyprince
from lcats.gatherers.wodehouse.gatherer import find_paragraphs_wodehouse


class TestFindParagraphsHappyPrince(unittest.TestCase):
    """Unit tests for find_paragraphs_happyprince (Wilde)."""

    def _make_soup(self, html):
        return BeautifulSoup(html, "lxml")

    def test_returns_paragraphs_after_heading_with_period(self):
        """Matches heading that includes a trailing period after the title text."""
        html = """
        <html><body>
        <h2>The Happy Prince.</h2>
        <p>High above the city.</p>
        </body></html>
        """
        soup = self._make_soup(html)
        result = find_paragraphs_happyprince(soup, "The Happy Prince")
        self.assertIn("High above the city.", result)

    def test_returns_none_when_heading_not_found(self):
        """Returns None when no matching heading with trailing period exists."""
        html = "<html><body><h2>The Happy Prince</h2><p>Text.</p></body></html>"
        soup = self._make_soup(html)
        # Heading text without period won't match since finder looks for "title."
        result = find_paragraphs_happyprince(soup, "The Selfish Giant")
        self.assertIsNone(result)

    def test_includes_table_tags(self):
        """Includes table elements (unique to this finder vs the default)."""
        html = """
        <html><body>
        <h2>The Selfish Giant.</h2>
        <table><tr><td>Table content.</td></tr></table>
        </body></html>
        """
        soup = self._make_soup(html)
        result = find_paragraphs_happyprince(soup, "The Selfish Giant")
        self.assertIn("Table content.", result)

    def test_stops_at_next_h2(self):
        """Does not include paragraphs from the following h2 section."""
        html = """
        <html><body>
        <h2>The Happy Prince.</h2>
        <p>Prince text.</p>
        <h2>The Selfish Giant.</h2>
        <p>Giant text.</p>
        </body></html>
        """
        soup = self._make_soup(html)
        result = find_paragraphs_happyprince(soup, "The Happy Prince")
        self.assertIn("Prince text.", result)
        self.assertNotIn("Giant text.", result)

    def test_stops_at_div(self):
        """Does not include content after a div sibling."""
        html = """
        <html><body>
        <h2>The Happy Prince.</h2>
        <p>Prince text.</p>
        <div><p>Div content.</p></div>
        </body></html>
        """
        soup = self._make_soup(html)
        result = find_paragraphs_happyprince(soup, "The Happy Prince")
        self.assertIn("Prince text.", result)
        self.assertNotIn("Div content.", result)


class TestFindParagraphsWodehouse(unittest.TestCase):
    """Unit tests for find_paragraphs_wodehouse."""

    def _make_soup(self, html):
        return BeautifulSoup(html, "lxml")

    def test_returns_paragraphs_after_heading(self):
        """Returns joined paragraph text when heading is found."""
        html = """
        <html><body>
        <h2>BILL THE BLOODHOUND</h2>
        <p>First paragraph.</p>
        <p>Second paragraph.</p>
        </body></html>
        """
        soup = self._make_soup(html)
        result = find_paragraphs_wodehouse(soup, "BILL THE BLOODHOUND")
        self.assertIn("First paragraph.", result)
        self.assertIn("Second paragraph.", result)

    def test_returns_none_when_heading_not_found(self):
        """Returns None when the heading is not present."""
        html = "<html><body><h2>SOMETHING ELSE</h2><p>Text.</p></body></html>"
        soup = self._make_soup(html)
        result = find_paragraphs_wodehouse(soup, "BILL THE BLOODHOUND")
        self.assertIsNone(result)

    def test_stops_at_next_h2(self):
        """Does not include paragraphs from following h2 sections."""
        html = """
        <html><body>
        <h2>BILL THE BLOODHOUND</h2>
        <p>Bill text.</p>
        <h2>THE MIXER</h2>
        <p>Mixer text.</p>
        </body></html>
        """
        soup = self._make_soup(html)
        result = find_paragraphs_wodehouse(soup, "BILL THE BLOODHOUND")
        self.assertIn("Bill text.", result)
        self.assertNotIn("Mixer text.", result)

    def test_stops_at_div(self):
        """Does not include content after a div sibling."""
        html = """
        <html><body>
        <h2>BILL THE BLOODHOUND</h2>
        <p>Bill text.</p>
        <div><p>Div content.</p></div>
        </body></html>
        """
        soup = self._make_soup(html)
        result = find_paragraphs_wodehouse(soup, "BILL THE BLOODHOUND")
        self.assertIn("Bill text.", result)
        self.assertNotIn("Div content.", result)

    def test_does_not_include_pre_tags(self):
        """Unlike the default finder, pre tags are not included."""
        html = """
        <html><body>
        <h2>BILL THE BLOODHOUND</h2>
        <pre>Preformatted text.</pre>
        </body></html>
        """
        soup = self._make_soup(html)
        result = find_paragraphs_wodehouse(soup, "BILL THE BLOODHOUND")
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
