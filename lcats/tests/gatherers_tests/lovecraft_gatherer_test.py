"""Tests for the Lovecraft gatherer module."""

import json
import os
import tempfile
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

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


class TestEntryHelpers(unittest.TestCase):
    """Unit tests for the per-entry lookup helpers gather() wires into
    gatherlib.gather()'s entry_url/name_source/extraction_strategy
    extension points (WI-GATHER-0104)."""

    def setUp(self):
        self.ext = gatherer.THE_LOVECRAFT_FILES[0]

    def test_entry_url_returns_extractor_url(self):
        """_entry_url looks up the real per-story URL, not a shared one."""
        result = gatherer._entry_url(self.ext.file, "", self.ext.description)
        self.assertEqual(result, self.ext.url)

    def test_entry_name_returns_display_title_not_filename(self):
        """_entry_name returns the display title, matching the audit's
        3rd incompatibility finding -- not the normalized filename
        gatherlib.gather() would otherwise store as story_data["name"]."""
        result = gatherer._entry_name(self.ext.file, "", self.ext.description)
        self.assertEqual(result, self.ext.title)
        self.assertNotEqual(result, self.ext.file)

    def test_extract_story_text_finds_content_between_separator_ids(self):
        """_extract_story_text uses ID-based extraction, not heading search."""
        html = """
        <html><body>
        <div id="pg-start-separator"></div>
        <p>Cosmic horror awaits.</p>
        <div id="pg-end-separator"></div>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        result = gatherer._extract_story_text(soup)
        self.assertIn("Cosmic horror awaits.", result)


class TestGather(unittest.TestCase):
    """Unit tests for the gather() function.

    gather() is now a thin wrapper around gatherlib.gather() (WI-GATHER-0104).
    Per AGENTS.md's mocking philosophy (avoid heavy mocking; mock only at
    true boundaries) and the P1 review finding on WI-GATHER-0103's own PR
    (#421), these mock DataGatherer -- the network/external boundary
    gatherlib.gather() itself mocks in its own tests (gatherlib_test.py) --
    rather than gatherlib.gather() itself, so the real entry_url/
    name_source/extraction_strategy wiring still gets exercised end to end
    with real HTML."""

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

    @patch("lcats.gatherers.gatherlib.downloaders.DataGatherer")
    def test_gather_calls_download_for_each_story(self, mock_gatherer_cls):
        """gather() calls download once per entry in THE_LOVECRAFT_FILES."""
        mock_instance = MagicMock()
        mock_instance.downloads = {}
        mock_gatherer_cls.return_value = mock_instance

        gatherer.gather()

        self.assertEqual(
            mock_instance.download.call_count, len(gatherer.THE_LOVECRAFT_FILES)
        )

    @patch("lcats.gatherers.gatherlib.downloaders.DataGatherer")
    def test_gather_returns_downloads(self, mock_gatherer_cls):
        """gather() returns the downloads dict from the DataGatherer."""
        mock_instance = MagicMock()
        expected = {"the_call_of_cthulhu": "/some/path.json"}
        mock_instance.downloads = expected
        mock_gatherer_cls.return_value = mock_instance

        result = gatherer.gather()

        self.assertIs(result, expected)

    @patch("lcats.gatherers.gatherlib.downloaders.DataGatherer")
    def test_gather_uses_correct_target_directory(self, mock_gatherer_cls):
        """gather() instantiates DataGatherer with TARGET_DIRECTORY."""
        mock_instance = MagicMock()
        mock_instance.downloads = {}
        mock_gatherer_cls.return_value = mock_instance

        gatherer.gather()

        args, _ = mock_gatherer_cls.call_args
        self.assertEqual(args[0], gatherer.TARGET_DIRECTORY)

    @patch("lcats.gatherers.gatherlib.downloaders.DataGatherer")
    def test_gather_wires_real_extraction_and_metadata_through_the_download_callback(
        self, mock_gatherer_cls
    ):
        """The callback gather() hands to download() uses the real
        per-entry URL, ID-based extraction, and display-title metadata
        name -- not just a mocked gatherlib.gather() call."""
        mock_instance = MagicMock()
        mock_instance.downloads = {}
        mock_gatherer_cls.return_value = mock_instance

        gatherer.gather()

        first_ext = gatherer.THE_LOVECRAFT_FILES[0]
        (call_filename, call_url, callback), _ = mock_instance.download.call_args_list[
            0
        ]
        self.assertEqual(call_filename, first_ext.file)
        self.assertEqual(call_url, first_ext.url)

        html = """
        <html><body>
        <div id="pg-start-separator"></div>
        <p>Cosmic horror awaits.</p>
        <div id="pg-end-separator"></div>
        </body></html>
        """
        description, text, metadata = callback(html)

        self.assertEqual(description, first_ext.description)
        self.assertIn("Cosmic horror awaits.", text)
        self.assertEqual(metadata["name"], first_ext.title)
        self.assertEqual(metadata["author"], "H. P. Lovecraft")
        self.assertEqual(metadata["year"], 1925)
        self.assertEqual(metadata["url"], first_ext.url)
        # tests/AGENTS.md:24-27 -- serializer/extractor invariant, restored
        # after the retired TestCreateDownloadCallback's own version of
        # this check was dropped along with it (review finding, PR #424).
        json.dumps({"description": description, "body": text, "metadata": metadata})


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
