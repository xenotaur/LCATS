"""Tests for the Anderson gatherer module."""

import pathlib
import tempfile
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

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        # gather() now writes a run_log.RunLog by default -- point it at a
        # throwaway directory rather than the real default (logs/gather/
        # relative to cwd), so these unit tests don't leave real files
        # behind in whatever directory happens to run them (WI-RUNLOG-0082).
        self.log_dir = pathlib.Path(self._tmp.name) / "gather_logs"

    def tearDown(self):
        self._tmp.cleanup()

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
            log_dir=self.log_dir,
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
            log_dir=self.log_dir,
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
            log_dir=self.log_dir,
        )

        args, _ = mock_gatherer_cls.call_args
        self.assertEqual(args[0], EXAMPLE_DIRECTORY)


class TestGatherExtensionPoints(unittest.TestCase):
    """WI-GATHER-0104: gather()'s three opt-in extension points
    (entry_url, extraction_strategy, name_source), tested independently
    of any specific caller (e.g. lovecraft)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.log_dir = pathlib.Path(self._tmp.name) / "gather_logs"

    def tearDown(self):
        self._tmp.cleanup()

    @patch("lcats.gatherers.gatherlib.downloaders.DataGatherer")
    def test_entry_url_overrides_shared_gutenberg_url_per_entry(
        self, mock_gatherer_cls
    ):
        """When entry_url is given, each download() call gets that
        entry's own URL instead of one shared gutenberg_url."""
        mock_instance = MagicMock()
        mock_instance.downloads = {}
        mock_gatherer_cls.return_value = mock_instance
        per_entry_urls = {
            "swineherd": "http://example.com/swineherd",
            "real_princess": "http://example.com/real_princess",
            "shoes_of_fortune": "http://example.com/shoes_of_fortune",
        }

        gatherlib.gather(
            corpus="Anderson",
            target_directory=EXAMPLE_DIRECTORY,
            description="Anderson stories from the Gutenberg Project.",
            license_text="Public domain, from Project Gutenberg.",
            author="Anderson",
            year=1911,
            headings=EXAMPLE_HEADINGS,
            entry_url=lambda raw_filename, heading, title: per_entry_urls[raw_filename],
            verbose=False,
            log_dir=self.log_dir,
        )

        # Assert the actual filename->URL mapping, not the call order, so
        # this doesn't become order-sensitive if headings are reordered
        # (review finding, PR #424).
        called_url_by_filename = {
            call.args[0]: call.args[1] for call in mock_instance.download.call_args_list
        }
        self.assertEqual(called_url_by_filename, per_entry_urls)

    @patch("lcats.gatherers.gatherlib.downloaders.DataGatherer")
    def test_extraction_strategy_replaces_paragraph_finder_entirely(
        self, mock_gatherer_cls
    ):
        """When extraction_strategy is given, the callback uses it
        instead of paragraph_finder(soup, start_heading_text)."""
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
            extraction_strategy=lambda soup: "fixed extraction result",
            verbose=False,
            log_dir=self.log_dir,
        )

        _filename, _url, callback = mock_instance.download.call_args_list[0].args
        _description, text, _metadata = callback("<html></html>")
        self.assertEqual(text, "fixed extraction result")

    @patch("lcats.gatherers.gatherlib.downloaders.DataGatherer")
    def test_name_source_overrides_the_normalized_filename_metadata_name(
        self, mock_gatherer_cls
    ):
        """When name_source is given, story_data["name"] uses it instead
        of the normalized filename."""
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
            name_source=lambda raw_filename, heading, title: f"Display: {title}",
            verbose=False,
            log_dir=self.log_dir,
        )

        _filename, _url, callback = mock_instance.download.call_args_list[0].args
        html = """
        <html><body>
        <h2>THE SWINEHERD</h2>
        <p>Once upon a time.</p>
        </body></html>
        """
        _description, _text, metadata = callback(html)
        self.assertEqual(metadata["name"], f"Display: {EXAMPLE_HEADINGS[0][2]}")
        self.assertNotEqual(metadata["name"], EXAMPLE_HEADINGS[0][0])

    @patch("lcats.gatherers.gatherlib.downloaders.DataGatherer")
    def test_extension_points_default_to_prior_behavior_when_unset(
        self, mock_gatherer_cls
    ):
        """Omitting all three extensions reproduces gather()'s original
        behavior exactly -- shared gutenberg_url, paragraph_finder, and
        normalized-filename metadata name."""
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
            log_dir=self.log_dir,
        )

        called_urls = {call.args[1] for call in mock_instance.download.call_args_list}
        self.assertEqual(called_urls, {EXAMPLE_GUTENBERG})

        _filename, _url, callback = mock_instance.download.call_args_list[0].args
        html = """
        <html><body>
        <h2>THE SWINEHERD</h2>
        <p>Once upon a time.</p>
        </body></html>
        """
        _description, text, metadata = callback(html)
        self.assertIn("Once upon a time.", text)
        self.assertEqual(metadata["name"], EXAMPLE_HEADINGS[0][0])

    def test_raises_when_neither_gutenberg_url_nor_entry_url_given(self):
        """gather() fails fast with a clear message rather than silently
        passing url=None into download() (review finding, PR #424)."""
        with self.assertRaises(ValueError):
            gatherlib.gather(
                corpus="Anderson",
                target_directory=EXAMPLE_DIRECTORY,
                description="Anderson stories from the Gutenberg Project.",
                license_text="Public domain, from Project Gutenberg.",
                author="Anderson",
                year=1911,
                headings=EXAMPLE_HEADINGS,
                verbose=False,
                log_dir=self.log_dir,
            )


class TestGatherRunLogging(unittest.TestCase):
    """WI-RUNLOG-0082: gatherlib.gather()'s download loop gets a
    crash-safe, incremental run-event log via lcats.utils.run_log.RunLog,
    written outside the protected data/ tree target_directory lives
    under."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.log_dir = pathlib.Path(self._tmp.name) / "gather_logs"

    def tearDown(self):
        self._tmp.cleanup()

    @patch("lcats.gatherers.gatherlib.downloaders.DataGatherer")
    def test_run_log_records_start_and_per_story_and_end_in_order(
        self, mock_gatherer_cls
    ):
        mock_instance = MagicMock()
        mock_instance.downloads = {}
        # download() only populates .downloads on a real (non-skipped)
        # download (downloaders.py:239-279) - simulate that here so the
        # per-story event is "story_downloaded", not "story_skipped".
        mock_instance.download.side_effect = (
            lambda filename, *a, **kw: mock_instance.downloads.__setitem__(
                filename, f"/fake/{filename}.json"
            )
        )
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
            log_dir=self.log_dir,
        )

        log_path = self.log_dir / "anderson_gather_run_log.jsonl"
        self.assertTrue(log_path.exists())
        events = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
        ]
        event_names = [e["event"] for e in events]
        self.assertEqual(event_names[0], "run_start")
        self.assertEqual(event_names[-1], "run_end")
        story_events = [e for e in events if e["event"] == "story_downloaded"]
        self.assertEqual(len(story_events), len(EXAMPLE_HEADINGS))
        self.assertEqual(story_events[0]["filename"], "swineherd")

    @patch("lcats.gatherers.gatherlib.downloaders.DataGatherer")
    def test_crash_mid_run_leaves_a_readable_partial_log(self, mock_gatherer_cls):
        """An unhandled download() failure partway through must not
        corrupt the already-written log entries, and must surface as
        run_aborted_unexpected - no per-story exception isolation existed
        here before this change, so the whole call still aborts, but now
        with a readable trail of what happened first."""
        mock_instance = MagicMock()
        mock_instance.downloads = {}

        def _download_side_effect(filename, *args, **kwargs):
            if filename == "swineherd":
                mock_instance.downloads[filename] = f"/fake/{filename}.json"
                return None
            raise RuntimeError("simulated download failure")

        mock_instance.download.side_effect = _download_side_effect
        mock_gatherer_cls.return_value = mock_instance

        with self.assertRaises(RuntimeError):
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
                log_dir=self.log_dir,
            )

        log_path = self.log_dir / "anderson_gather_run_log.jsonl"
        events = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
        ]
        event_names = [e["event"] for e in events]
        self.assertEqual(event_names[0], "run_start")
        self.assertEqual(
            event_names.count("story_downloaded"),
            1,
            "only the first (successful) download should have logged an event",
        )
        self.assertEqual(event_names[-1], "run_aborted_unexpected")

    @patch("lcats.gatherers.gatherlib.downloaders.DataGatherer")
    def test_already_downloaded_story_logs_skipped_not_downloaded(
        self, mock_gatherer_cls
    ):
        """download() leaves .downloads untouched when the canonical file
        already exists and it skips the fetch (downloaders.py:278-279) -
        the per-story event must reflect that, not falsely report every
        already-gathered story as freshly downloaded on a rerun (review
        finding, PR #404)."""
        mock_instance = MagicMock()
        mock_instance.downloads = {}
        # Real download() is a no-op on this side_effect: .downloads is
        # never populated, matching the "file already exists" branch.
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
            log_dir=self.log_dir,
        )

        log_path = self.log_dir / "anderson_gather_run_log.jsonl"
        events = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
        ]
        event_names = [e["event"] for e in events]
        self.assertNotIn("story_downloaded", event_names)
        self.assertEqual(event_names.count("story_skipped"), len(EXAMPLE_HEADINGS))


if __name__ == "__main__":
    unittest.main()
