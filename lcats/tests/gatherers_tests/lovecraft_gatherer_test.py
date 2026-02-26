"""Tests for the Lovecraft gatherer module."""

import json
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from lcats.gatherers.lovecraft import gatherer


class TestMakeExtractor(unittest.TestCase):
    """Unit tests for the make_extractor helper."""

    def test_title_and_url_are_set(self):
        """make_extractor stores the title and url."""
        ext = gatherer.make_extractor("The Call of Cthulhu", "http://example.com/cc")
        self.assertEqual(ext.title, "The Call of Cthulhu")
        self.assertEqual(ext.url, "http://example.com/cc")

    def test_default_author_is_lovecraft(self):
        """make_extractor uses H. P. Lovecraft as the default author."""
        ext = gatherer.make_extractor("Some Story", "http://example.com/s")
        self.assertEqual(ext.author, "H. P. Lovecraft")

    def test_custom_author_is_used(self):
        """make_extractor respects a custom author argument."""
        ext = gatherer.make_extractor(
            "Collabor", "http://example.com/co", author="Other Author"
        )
        self.assertEqual(ext.author, "Other Author")

    def test_file_is_derived_from_title(self):
        """make_extractor computes file from title when none is supplied."""
        ext = gatherer.make_extractor("The Call of Cthulhu", "http://example.com/cc")
        self.assertEqual(ext.file, "the_call_of_cthulhu")


class TestTheLovecraftFiles(unittest.TestCase):
    """Unit tests for the THE_LOVECRAFT_FILES constant."""

    def test_list_is_nonempty(self):
        """THE_LOVECRAFT_FILES contains at least one entry."""
        self.assertGreater(len(gatherer.THE_LOVECRAFT_FILES), 0)

    def test_all_entries_have_title_and_url(self):
        """Every entry in THE_LOVECRAFT_FILES has a non-empty title and url."""
        for ext in gatherer.THE_LOVECRAFT_FILES:
            with self.subTest(title=ext.title):
                self.assertTrue(ext.title)
                self.assertTrue(ext.url)

    def test_all_entries_have_lovecraft_author(self):
        """Every entry uses H. P. Lovecraft as author."""
        for ext in gatherer.THE_LOVECRAFT_FILES:
            with self.subTest(title=ext.title):
                self.assertEqual(ext.author, "H. P. Lovecraft")

    def test_all_entries_have_file_attribute(self):
        """Every entry has a non-empty file attribute."""
        for ext in gatherer.THE_LOVECRAFT_FILES:
            with self.subTest(title=ext.title):
                self.assertTrue(ext.file)

    def test_known_story_present(self):
        """The Call of Cthulhu is in the list."""
        titles = [ext.title for ext in gatherer.THE_LOVECRAFT_FILES]
        self.assertIn("The Call of Cthulhu", titles)


class TestCreateDownloadCallback(unittest.TestCase):
    """Unit tests for create_download_callback."""

    def _make_html(self, para_text="Once upon a time."):
        """Return minimal Gutenberg-style HTML with pg-start/end separator IDs."""
        return f"""
        <html><body>
        <div id="pg-start-separator"></div>
        <p>{para_text}</p>
        <div id="pg-end-separator"></div>
        </body></html>
        """

    def setUp(self):
        """Create a simple Extractor for test use."""
        self.ext = gatherer.make_extractor(
            "The Call of Cthulhu", "http://example.com/cc"
        )
        self.callback = gatherer.create_download_callback(self.ext)

    def test_returns_callable(self):
        """create_download_callback returns a callable."""
        self.assertTrue(callable(self.callback))

    def test_callback_raises_on_none_contents(self):
        """Callback raises ValueError when contents is None."""
        with self.assertRaises(ValueError):
            self.callback(None)

    def test_callback_raises_when_text_not_found(self):
        """Callback raises an error when story text cannot be extracted."""
        html = "<html><body><p>No separators here.</p></body></html>"
        with self.assertRaises(Exception):
            self.callback(html)

    def test_callback_returns_tuple_on_valid_html(self):
        """Callback returns (description, text, metadata) for valid HTML."""
        html = self._make_html("Cosmic horror awaits.")
        result = self.callback(html)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)

    def test_callback_description_matches_extractor(self):
        """Callback description matches the extractor's description."""
        html = self._make_html("Cosmic horror awaits.")
        description, _text, _meta = self.callback(html)
        self.assertEqual(description, self.ext.description)

    def test_callback_metadata_has_required_keys(self):
        """Callback metadata contains author, year, url, and name keys."""
        html = self._make_html("Cosmic horror awaits.")
        _desc, _text, metadata = self.callback(html)
        for key in ("author", "year", "url", "name"):
            with self.subTest(key=key):
                self.assertIn(key, metadata)

    def test_callback_metadata_author_matches_extractor(self):
        """Metadata author matches the extractor's author."""
        html = self._make_html("Cosmic horror awaits.")
        _desc, _text, metadata = self.callback(html)
        self.assertEqual(metadata["author"], self.ext.author)

    def test_callback_metadata_url_matches_extractor(self):
        """Metadata url matches the extractor's url."""
        html = self._make_html("Cosmic horror awaits.")
        _desc, _text, metadata = self.callback(html)
        self.assertEqual(metadata["url"], self.ext.url)

    def test_callback_metadata_name_matches_extractor(self):
        """Metadata name matches the extractor's title."""
        html = self._make_html("Cosmic horror awaits.")
        _desc, _text, metadata = self.callback(html)
        self.assertEqual(metadata["name"], self.ext.title)

    def test_callback_metadata_is_json_serializable(self):
        """Metadata returned by callback can be serialized to JSON."""
        html = self._make_html("Cosmic horror awaits.")
        description, text, metadata = self.callback(html)
        # Should not raise
        json.dumps({"description": description, "body": text, "metadata": metadata})

    def test_callback_text_contains_paragraph(self):
        """The returned story text contains the paragraph from the HTML."""
        html = self._make_html("Eldritch abomination approaches.")
        _desc, text, _meta = self.callback(html)
        self.assertIn("Eldritch abomination approaches.", text)


class TestGather(unittest.TestCase):
    """Unit tests for the gather() function."""

    @patch("lcats.gatherers.lovecraft.gatherer.downloaders.DataGatherer")
    def test_gather_calls_download_for_each_story(self, mock_gatherer_cls):
        """gather() calls download once per entry in THE_LOVECRAFT_FILES."""
        mock_instance = MagicMock()
        mock_instance.downloads = {}
        mock_gatherer_cls.return_value = mock_instance

        gatherer.gather()

        self.assertEqual(
            mock_instance.download.call_count, len(gatherer.THE_LOVECRAFT_FILES)
        )

    @patch("lcats.gatherers.lovecraft.gatherer.downloaders.DataGatherer")
    def test_gather_returns_downloads(self, mock_gatherer_cls):
        """gather() returns the downloads dict from the DataGatherer."""
        mock_instance = MagicMock()
        expected = {"the_call_of_cthulhu": "/some/path.json"}
        mock_instance.downloads = expected
        mock_gatherer_cls.return_value = mock_instance

        result = gatherer.gather()

        self.assertIs(result, expected)

    @patch("lcats.gatherers.lovecraft.gatherer.downloaders.DataGatherer")
    def test_gather_uses_correct_target_directory(self, mock_gatherer_cls):
        """gather() instantiates DataGatherer with TARGET_DIRECTORY."""
        mock_instance = MagicMock()
        mock_instance.downloads = {}
        mock_gatherer_cls.return_value = mock_instance

        gatherer.gather()

        args, _ = mock_gatherer_cls.call_args
        self.assertEqual(args[0], gatherer.TARGET_DIRECTORY)


class TestMain(unittest.TestCase):
    """Unit tests for the main() function."""

    @patch("lcats.gatherers.lovecraft.gatherer.gather")
    def test_main_calls_gather(self, mock_gather):
        """main() invokes gather()."""
        mock_gather.return_value = {}
        with patch("sys.stdout", new_callable=StringIO):
            gatherer.main()
        mock_gather.assert_called_once()

    @patch("lcats.gatherers.lovecraft.gatherer.gather")
    def test_main_prints_count(self, mock_gather):
        """main() prints the number of downloaded stories."""
        mock_gather.return_value = {"a": 1, "b": 2}
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            gatherer.main()
        output = mock_stdout.getvalue()
        self.assertIn("2", output)


if __name__ == "__main__":
    unittest.main()
