"""Unit tests for LCATS using its actual package imports.

Run from the LCATS repository root:
    python -m unittest discover -s tests -p '*_test.py' -v
"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import parse_qs, urlparse

from lcats.gatherers import downloaders, normalization, parser, registry
from lcats.gatherers.standard_ebooks import gatherer
from lcats.utils import names


class CaptureOutput:
    """Capture console output without relying on another test framework."""

    def __init__(self):
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()

    def readouterr(self):
        result = SimpleNamespace(
            out=self.stdout.getvalue(),
            err=self.stderr.getvalue(),
        )

        self.stdout.seek(0)
        self.stdout.truncate(0)
        self.stderr.seek(0)
        self.stderr.truncate(0)

        return result


class LCATSTestCase(unittest.TestCase):
    """Provide the same temporary-file and mock cleanup as existing LCATS tests."""

    def setUp(self):
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)

        self.tmp_path = Path(self._temporary_directory.name)
        self.capsys = CaptureOutput()

        self._stdout_capture = contextlib.redirect_stdout(self.capsys.stdout)
        self._stderr_capture = contextlib.redirect_stderr(self.capsys.stderr)

        self._stdout_capture.__enter__()
        self.addCleanup(self._stdout_capture.__exit__, None, None, None)

        self._stderr_capture.__enter__()
        self.addCleanup(self._stderr_capture.__exit__, None, None, None)

    def patch_attribute(self, target, name, replacement):
        """Patch a real module or object, restoring it after this test."""
        patcher = patch.object(target, name, replacement)
        patcher.start()
        self.addCleanup(patcher.stop)

        return replacement


SITE = "https://standardebooks.org"
COLLECTION = f"{SITE}/ebooks/example-author/collected-stories"
TOC = f"{COLLECTION}/text"
FIRST = f"{TOC}/first-story"
SECOND = f"{TOC}/second-story"
TOC_HTML = (
    f'<nav class="toc"><a href="{FIRST}">I: First Story</a>'
    f'<a href="{SECOND}">II: Second Story</a></nav>'
)
STORY_HTML = (
    "<main><article><h1>First Story</h1>"
    "<p>There was once a very unusual situation.</p>"
    "<p>It was resolved before the end of the evening.</p>"
    "</article></main>"
)


def fake_gatherer_fixture(tmp_path):
    class FakeGatherer:
        def __init__(self):
            self.path = str(tmp_path / "corpus")
            self.slugs = []

        def ensure(self, slug):
            self.slugs.append(slug)
            directory = Path(self.path) / slug
            directory.mkdir(parents=True, exist_ok=True)

            return str(directory), str(directory / "story.json")

    return FakeGatherer()


def collection_setup_fixture(module, fake_gatherer, patch_attribute, tmp_path):
    module.downloaders.DataGatherer.return_value = fake_gatherer
    patch_attribute(module, "sleep", Mock())

    cache_file = module._cache_file(
        tmp_path,
        "tables_of_contents",
        TOC,
        "html",
    )

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(TOC_HTML, encoding="utf-8")

    return tmp_path, fake_gatherer


class TestStandardEbooksGatherer(LCATSTestCase):

    def module(self, tmp_path):
        """Use the real Standard Ebooks gatherer; isolate network and disk effects."""

        def filename(title, authors, **kwargs):
            clean_title = title.replace(" ", "_")
            clean_author = authors[0].replace(" ", "_")

            return f"{clean_title}__{clean_author}.json"

        self.patch_attribute(
            names, "title_and_author_to_filename", Mock(side_effect=filename)
        )
        self.patch_attribute(
            names,
            "canonical_author",
            SimpleNamespace(
                canonical_key=lambda author: author,
                last_name=lambda author: author.split()[-1],
            ),
        )
        self.patch_attribute(downloaders, "DataGatherer", Mock())
        self.patch_attribute(normalization, "normalize_story_dict", Mock())
        self.patch_attribute(parser, "chaptered", Mock(return_value=False))
        self.patch_attribute(registry, "check_story", Mock(return_value=False))
        self.patch_attribute(registry, "add_story", Mock())
        # The original gatherer stores its counter as a function attribute.
        # Reset it to keep independent tests deterministic without re-importing.
        previous_count = getattr(gatherer.gather_story, "story", None)

        def restore_counter():
            if previous_count is None:
                if hasattr(gatherer.gather_story, "story"):
                    delattr(gatherer.gather_story, "story")
            else:
                gatherer.gather_story.story = previous_count

        self.addCleanup(restore_counter)
        gatherer.gather_story.story = 0

        self.patch_attribute(
            gatherer,
            "DEFAULT_CACHE_DIR",
            tmp_path / "default-cache" / "standard_ebooks",
        )

        return gatherer

    def test_set_page_parameter_preserves_query(self):
        for _case_index, number in enumerate([1, 2, 19]):
            with self.subTest(number=number):
                tmp_path = self.tmp_path / str(_case_index)
                tmp_path.mkdir(parents=True, exist_ok=True)
                module = self.module(tmp_path)
                address = module.set_page_parameter(
                    f"{SITE}/subjects/shorts?view=list&empty=&page=99", number
                )
                params = parse_qs(urlparse(address).query, keep_blank_values=True)
                self.assertEqual(params["page"], [str(number)])
                self.assertEqual(params["view"], ["list"])
                self.assertEqual(params["empty"], [""])

    def test_canonicalize_url(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        result = module.canonicalize_url(COLLECTION + "/?download=1#chapter")

        self.assertEqual(result, COLLECTION)

    def test_is_collection_url(self):
        for _case_index, (url, expected) in enumerate(
            [
                (COLLECTION, True),
                (COLLECTION + "/", True),
                (COLLECTION + "/text", False),
                (f"{SITE}/ebooks/one", False),
                ("https://elsewhere.org/ebooks/author/collection", False),
                ("javascript:alert(1)", False),
            ]
        ):
            with self.subTest(url=url, expected=expected):
                tmp_path = self.tmp_path / str(_case_index)
                tmp_path.mkdir(parents=True, exist_ok=True)
                module = self.module(tmp_path)
                self.assertIs(
                    module.is_collection_url(url, "standardebooks.org"), expected
                )

    def test_extract_collection_urls_filters_duplicates_and_outside_hosts(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        html = f'<a href="{COLLECTION}/?x=1">Collection</a><a href="{COLLECTION}">Duplicate</a><a href="https://elsewhere.org/ebooks/x/y">Other host</a><a href="/about">About</a>'
        result = module.extract_collection_urls(html, module.DEFAULT_URL)

        self.assertEqual(result, [COLLECTION])

    def test_extract_collection_urls_resolves_relative_links(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        html = '<a href="/ebooks/example-author/collected-stories">Stories</a>'
        result = module.extract_collection_urls(html, module.DEFAULT_URL)

        self.assertEqual(result, [COLLECTION])

    def test_extract_collection_urls_can_return_empty(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)

        self.assertEqual(
            module.extract_collection_urls("<html></html>", module.DEFAULT_URL), []
        )

    def test_get_collection_urls_paginates_and_deduplicates(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        response_one = Mock(text=f'<a href="{COLLECTION}">A</a>')
        response_two = Mock(text=f'<a href="{COLLECTION}">A again</a>')
        session = Mock()
        session.get.side_effect = [response_one, response_two]
        self.patch_attribute(module.requests, "Session", Mock(return_value=session))
        self.patch_attribute(module.time, "sleep", Mock())
        result = module.get_collection_urls(delay=0, cache_dir=tmp_path)

        self.assertEqual(result, [COLLECTION])

        self.assertEqual(session.get.call_count, 2)

        self.assertIn("page=1", session.get.call_args_list[0].args[0])

        self.assertIn("page=2", session.get.call_args_list[1].args[0])

    def test_get_collection_urls_raises_at_page_safety_limit(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        session = Mock()
        session.get.return_value = Mock(text=f'<a href="{COLLECTION}">One</a>')
        self.patch_attribute(module.requests, "Session", Mock(return_value=session))
        with self.assertRaisesRegex(RuntimeError, "safety limit"):
            module.get_collection_urls(maximum_pages=1, delay=0, cache_dir=tmp_path)

    def test_default_cache_dir_uses_lcats_cache_root(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)

        self.assertEqual(
            module.DEFAULT_CACHE_DIR, tmp_path / "default-cache" / "standard_ebooks"
        )

        self.assertEqual(module._metadata_cache_dir(False), module.DEFAULT_CACHE_DIR)

        self.assertEqual(module._metadata_cache_dir(None), module.DEFAULT_CACHE_DIR)

    def test_cache_key_is_stable_and_includes_url_query(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        one = module._cache_file(
            tmp_path, "collection_lists", "https://a.org/?page=1", "json"
        )
        same = module._cache_file(
            tmp_path, "collection_lists", "https://a.org/?page=1", "json"
        )
        other = module._cache_file(
            tmp_path, "collection_lists", "https://a.org/?page=2", "json"
        )

        self.assertEqual(one, same)

        self.assertNotEqual(one, other)

        self.assertEqual(one.parent, tmp_path / "collection_lists")

    def test_atomic_cache_write_creates_file_and_no_temp_files(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        path = tmp_path / "nested" / "cached.txt"
        module._atomic_cache_write(path, "hello")

        self.assertEqual(path.read_text(encoding="utf-8"), "hello")

        self.assertEqual(list(path.parent.glob("*.tmp")), [])

    def test_atomic_cache_write_replaces_previous_contents(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        path = tmp_path / "cached.txt"
        path.write_text("old", encoding="utf-8")
        module._atomic_cache_write(path, "new")

        self.assertEqual(path.read_text(encoding="utf-8"), "new")

    def test_invalid_metadata_mode_rejected(self):
        for _case_index, mode in enumerate(["", "offline", "CACHE", "bad"]):
            with self.subTest(mode=mode):
                tmp_path = self.tmp_path / str(_case_index)
                tmp_path.mkdir(parents=True, exist_ok=True)
                module = self.module(tmp_path)
                with self.assertRaisesRegex(ValueError, "metadata_mode"):
                    module._check_metadata_mode(mode)

    def test_collection_url_refresh_writes_cache(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        session = Mock()
        session.get.side_effect = [
            Mock(text=f'<a href="{COLLECTION}">One</a>'),
            Mock(text="<html></html>"),
        ]
        self.patch_attribute(module.requests, "Session", Mock(return_value=session))
        urls = module.get_collection_urls(delay=0, cache_dir=tmp_path)
        path = module._cache_file(
            tmp_path, "collection_lists", module.DEFAULT_URL, "json"
        )
        saved = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(urls, [COLLECTION])

        self.assertEqual(saved, {"start_url": module.DEFAULT_URL, "urls": [COLLECTION]})

    def test_cached_collection_urls_never_create_session(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        path = module._cache_file(
            tmp_path, "collection_lists", module.DEFAULT_URL, "json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"start_url": module.DEFAULT_URL, "urls": [COLLECTION]}),
            encoding="utf-8",
        )
        no_network = Mock(side_effect=AssertionError("Unexpected network access"))
        self.patch_attribute(module.requests, "Session", no_network)
        urls = module.get_collection_urls(metadata_mode="cached", cache_dir=tmp_path)

        self.assertEqual(urls, [COLLECTION])
        no_network.assert_not_called()

    def test_cached_collection_urls_missing_fails(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        with self.assertRaisesRegex(FileNotFoundError, "No saved collection URL list"):
            module.get_collection_urls(metadata_mode="cached", cache_dir=tmp_path)

    def test_bad_collection_cache_is_rejected(self):
        for _case_index, cached in enumerate(
            [
                [],
                {"start_url": "wrong", "urls": [COLLECTION]},
                {"start_url": "correct", "urls": "not a list"},
                {"start_url": "correct", "urls": [5]},
            ]
        ):
            with self.subTest(cached=cached):
                tmp_path = self.tmp_path / str(_case_index)
                tmp_path.mkdir(parents=True, exist_ok=True)
                module = self.module(tmp_path)
                path = module._cache_file(
                    tmp_path, "collection_lists", module.DEFAULT_URL, "json"
                )
                path.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(cached, dict) and cached.get("start_url") == "correct":
                    cached["start_url"] = module.DEFAULT_URL
                path.write_text(json.dumps(cached), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Invalid collection URL cache"):
                    module.get_collection_urls(
                        metadata_mode="cached", cache_dir=tmp_path
                    )

    def test_invalid_json_cache_raises_decode_error(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        path = module._cache_file(
            tmp_path, "collection_lists", module.DEFAULT_URL, "json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not json", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            module.get_collection_urls(metadata_mode="cached", cache_dir=tmp_path)

    def test_collection_refresh_failure_preserves_previous_cache(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        path = module._cache_file(
            tmp_path, "collection_lists", module.DEFAULT_URL, "json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("previous cache", encoding="utf-8")
        session = Mock()
        session.get.side_effect = requests.RequestException("network unavailable")
        self.patch_attribute(module.requests, "Session", Mock(return_value=session))
        with self.assertRaises(requests.RequestException):
            module.get_collection_urls(delay=0, cache_dir=tmp_path)

        self.assertEqual(path.read_text(encoding="utf-8"), "previous cache")

    def test_clean_title(self):
        for _case_index, (title, expected) in enumerate(
            [
                ("II: A Domiciliary Visit", "A Domiciliary Visit"),
                ("3. The Adventure", "The Adventure"),
                ("IV) Another Story", "Another Story"),
                ("I, Robot", "I, Robot"),
                ("  A   Sample\xa0Title  ", "A Sample Title"),
            ]
        ):
            with self.subTest(title=title, expected=expected):
                tmp_path = self.tmp_path / str(_case_index)
                tmp_path.mkdir(parents=True, exist_ok=True)
                module = self.module(tmp_path)
                self.assertEqual(module.clean_title(title), expected)

    def test_is_story_url(self):
        for _case_index, (slug, expected) in enumerate(
            [
                ("first-story", True),
                ("introduction", False),
                ("introduction-2", False),
                ("endnotes", False),
                ("single-page", False),
                ("first-story/part-2", False),
            ]
        ):
            with self.subTest(slug=slug, expected=expected):
                tmp_path = self.tmp_path / str(_case_index)
                tmp_path.mkdir(parents=True, exist_ok=True)
                module = self.module(tmp_path)
                self.assertIs(module.is_story_url(TOC + "/" + slug, TOC), expected)

    def test_is_story_url_rejects_other_host_and_scheme(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)

        self.assertIs(module.is_story_url("https://unrelated.org/a", TOC), False)

        self.assertIs(module.is_story_url("javascript:hello", TOC), False)

    def test_is_non_story_title(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)

        self.assertIs(module.is_non_story_title(" Introduction: "), True)

        self.assertIs(module.is_non_story_title("A Novel Introduction"), False)

    def test_choose_toc_container_prefers_nav(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        soup = BeautifulSoup(
            '<main><a href="/wrong">Wrong</a></main><nav role="doc-toc"><a href="/correct">Right</a></nav>',
            "html.parser",
        )
        container = module.choose_toc_container(soup)

        self.assertEqual(container.name, "nav")

        self.assertEqual(container.get("role"), "doc-toc")

    def test_choose_toc_container_fails_without_candidate(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        soup = BeautifulSoup("<div>Nothing</div>", "html.parser")
        with self.assertRaisesRegex(ValueError, "table of contents"):
            module.choose_toc_container(soup)

    def test_extract_story_links_numbers_and_cleans_titles(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        stories = module.extract_story_links(TOC_HTML, TOC)

        self.assertEqual([story.number for story in stories], [1, 2])

        self.assertEqual(
            [story.title for story in stories], ["First Story", "Second Story"]
        )

        self.assertEqual([story.url for story in stories], [FIRST, SECOND])

    def test_extract_story_links_ignores_non_stories_duplicates_and_external(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        html = f'<nav class="toc"><a href="{FIRST}">First Story</a><a href="{FIRST}#fragment">First Story again</a><a href="{TOC}/introduction-1">Introduction</a><a href="{TOC}/unusual-slug">Foreword</a><a href="https://different.example/outside">Outside</a></nav>'
        stories = module.extract_story_links(html, TOC)

        self.assertEqual(len(stories), 1)

        self.assertEqual(stories[0].title, "First Story")

    def test_extract_story_links_uses_slug_for_blank_link_label(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        html = f'<nav class="toc"><a href="{FIRST}"></a></nav>'
        stories = module.extract_story_links(html, TOC)

        self.assertEqual(stories[0].title, "First Story")

    def test_extract_story_links_rejects_empty_toc(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        with self.assertRaisesRegex(ValueError, "No individual story links"):
            module.extract_story_links('<nav class="toc"></nav>', TOC)

    def test_make_session_sets_headers(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        session = Mock()
        session.headers = {}
        self.patch_attribute(module.requests, "Session", Mock(return_value=session))
        result = module.make_session()

        self.assertIs(result, session)

        self.assertIn("User-Agent", session.headers)

        self.assertIn("Accept", session.headers)

    def test_download_page_decodes_text_and_checks_status(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        response = Mock(text="<p>Hello</p>")
        response.encoding = None
        session = Mock()
        session.get.return_value = response
        result = module.download_page(session, FIRST, timeout=7)

        self.assertEqual(result, "<p>Hello</p>")

        self.assertEqual(response.encoding, "utf-8")
        session.get.assert_called_once_with(FIRST, timeout=7)
        response.raise_for_status.assert_called_once()

    def test_download_page_propagates_http_failure(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        session = Mock()
        session.get.return_value.raise_for_status.side_effect = requests.HTTPError(
            "404"
        )
        with self.assertRaises(requests.HTTPError):
            module.download_page(session, FIRST)

    def test_choose_story_container_prefers_paragraph_rich_element(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        soup = BeautifulSoup(
            "<main><article><p>Short</p></article><section><p>A considerably longer paragraph of narrative text.</p></section></main>",
            "html.parser",
        )
        container = module.choose_story_container(soup)

        self.assertIn("considerably longer", container.get_text(" ", strip=True))

    def test_choose_story_container_uses_body_fallback(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        soup = BeautifulSoup("<body><div>Some prose</div></body>", "html.parser")

        self.assertEqual(module.choose_story_container(soup).name, "body")

    def test_choose_story_container_errors_without_body(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        soup = BeautifulSoup("<div>Text</div>", "html.parser")
        with self.assertRaisesRegex(ValueError, "story text"):
            module.choose_story_container(soup)

    def test_remove_unwanted_elements_excludes_notes_navigation_and_scripts(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        soup = BeautifulSoup(
            '<main><p>Words<a role="doc-noteref">1</a> remain.</p><nav>Navigation</nav><aside>Side text</aside><div class="endnotes">Extra note</div><script>evil()</script></main>',
            "html.parser",
        )
        container = soup.main
        module.remove_unwanted_elements(container)
        remaining = container.get_text(" ", strip=True)

        self.assertIn("Words", remaining)

        self.assertIn("remain", remaining)

        self.assertNotIn("Navigation", remaining)

        self.assertNotIn("Side text", remaining)

        self.assertNotIn("Extra note", remaining)

        self.assertNotIn("evil", remaining)

        self.assertNotIn("1", remaining)

    def test_block_text_normalizes_breaks_and_whitespace(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        soup = BeautifulSoup("<p>One&nbsp; two<br/>three\xad four</p>", "html.parser")
        result = module.block_text(soup.p)

        self.assertEqual(result, "One two\nthree four")

    def test_story_registry_key_uses_same_name_builder(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        filename, title, author = module._story_registry_key(
            " First   Story ", "example author"
        )

        self.assertEqual(filename, "first_story__example_author.json")

        self.assertEqual(title, "first_story")

        self.assertEqual(author, "example_author")
        module.names.title_and_author_to_filename.assert_called_once()

    def test_story_exists_only_checks_without_adding(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        module.registry.check_story.return_value = True

        self.assertIs(module._story_exists("First Story", "example author"), True)
        module.registry.check_story.assert_called_once_with(
            "first_story", "example_author"
        )
        module.registry.add_story.assert_not_called()

    def test_add_saved_story_calls_registry_with_source(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        module._add_saved_story("first_story", "example_author")
        module.registry.add_story.assert_called_once_with(
            "first_story", "example_author", source="Standard EBooks"
        )

    def test_gather_story_saves_json_and_then_registers(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        fake_gatherer = fake_gatherer_fixture(tmp_path)
        output = Path(fake_gatherer.path) / "first_story__example_author" / "story.json"

        def verify_saved(*args, **kwargs):
            self.assertTrue(output.is_file())

        module.registry.add_story.side_effect = verify_saved
        story_id, path, error = module.gather_story(
            fake_gatherer, STORY_HTML, "First Story", "example author", FIRST
        )
        content = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(story_id, 0)

        self.assertEqual(path, str(output))

        self.assertIs(error, None)

        self.assertEqual(content["name"], "first story")

        self.assertIn("very unusual", content["body"])

        self.assertEqual(content["metadata"]["url"], FIRST)

        self.assertEqual(fake_gatherer.slugs, ["first_story__example_author"])
        module.registry.check_story.assert_called_once()
        module.registry.add_story.assert_called_once()

    def test_gather_story_duplicate_skips_without_writing(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        fake_gatherer = fake_gatherer_fixture(tmp_path)
        module.registry.check_story.return_value = True
        story_id, path, error = module.gather_story(
            fake_gatherer, STORY_HTML, "First Story", "example author", FIRST
        )

        self.assertEqual(story_id, 0)

        self.assertIs(path, None)

        self.assertIn("already appears", error)

        self.assertEqual(fake_gatherer.slugs, [])
        module.registry.add_story.assert_not_called()

    def test_gather_story_prechecked_skips_second_lookup(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        fake_gatherer = fake_gatherer_fixture(tmp_path)
        module.gather_story(
            fake_gatherer,
            STORY_HTML,
            "First Story",
            "example author",
            FIRST,
            registry_checked=True,
        )
        module.registry.check_story.assert_not_called()
        module.registry.add_story.assert_called_once()

    def test_gather_story_rejects_chapters_without_registering(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        fake_gatherer = fake_gatherer_fixture(tmp_path)
        module.parser.chaptered.return_value = True
        story_id, path, error = module.gather_story(
            fake_gatherer, STORY_HTML, "First Story", "example author", FIRST
        )

        self.assertIs(path, None)

        self.assertIn("chapters", error)
        module.registry.add_story.assert_not_called()

    def test_gather_story_rejects_empty_prose_without_registering(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        fake_gatherer = fake_gatherer_fixture(tmp_path)
        with self.assertRaisesRegex(ValueError, "No prose blocks"):
            module.gather_story(
                fake_gatherer,
                "<main><nav>Navigation</nav></main>",
                "First Story",
                "example author",
                FIRST,
            )
        module.registry.add_story.assert_not_called()

    def test_gather_story_file_failure_does_not_register(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        fake_gatherer = fake_gatherer_fixture(tmp_path)

        def refuse_write(slug):
            raise OSError("disk full")

        self.patch_attribute(fake_gatherer, "ensure", refuse_write)
        with self.assertRaisesRegex(OSError, "disk full"):
            module.gather_story(
                fake_gatherer, STORY_HTML, "First Story", "example author", FIRST
            )
        module.registry.add_story.assert_not_called()

    def test_gather_story_removes_navigation_and_duplicate_blocks(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        fake_gatherer = fake_gatherer_fixture(tmp_path)
        html = "<main><article><h1>First Story</h1><nav>Next</nav><p>Repeated paragraph.</p><p>Repeated paragraph.</p><p>Another paragraph.</p></article></main>"
        _, path, _ = module.gather_story(
            fake_gatherer, html, "First Story", "example author", FIRST
        )
        body = json.loads(Path(path).read_text(encoding="utf-8"))["body"]

        self.assertEqual(body.count("Repeated paragraph."), 1)

        self.assertIn("Another paragraph.", body)

        self.assertNotIn("Next", body)

    def test_gather_story_adds_missing_title_without_losing_prose(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        fake_gatherer = fake_gatherer_fixture(tmp_path)
        html = "<main><article><p>A narrative opening.</p><p>More narration.</p></article></main>"
        _, path, _ = module.gather_story(
            fake_gatherer, html, "First Story", "example author", FIRST
        )
        body = json.loads(Path(path).read_text(encoding="utf-8"))["body"]

        self.assertTrue(body.startswith("A narrative opening."))

        self.assertIn("More narration.", body)

    def test_gather_story_calls_normalization(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        fake_gatherer = fake_gatherer_fixture(tmp_path)
        module.gather_story(
            fake_gatherer, STORY_HTML, "First Story", "example author", FIRST
        )
        kwargs = module.normalization.normalize_story_dict.call_args.kwargs

        self.assertEqual(kwargs["story_id"], "first_story__example_author")

        self.assertEqual(kwargs["collection"], fake_gatherer.path)

    def test_gather_story_counter_increments_for_successes_only(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        fake_gatherer = fake_gatherer_fixture(tmp_path)
        first_id, _, _ = module.gather_story(
            fake_gatherer, STORY_HTML, "First Story", "example author", FIRST
        )
        module.registry.check_story.return_value = True
        duplicate_id, _, _ = module.gather_story(
            fake_gatherer, STORY_HTML, "Second Story", "example author", SECOND
        )
        module.registry.check_story.return_value = False
        second_id, _, _ = module.gather_story(
            fake_gatherer, STORY_HTML, "Third Story", "example author", SECOND
        )

        self.assertEqual((first_id, duplicate_id, second_id), (0, 1, 1))

    def test_cached_collection_skips_registered_story_without_download(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        fake_gatherer = fake_gatherer_fixture(tmp_path)
        collection_setup = collection_setup_fixture(
            module, fake_gatherer, self.patch_attribute, tmp_path
        )
        cache_dir, fake_gatherer = collection_setup
        module.registry.check_story.return_value = True
        no_download = Mock(side_effect=AssertionError("Duplicate was downloaded"))
        self.patch_attribute(module, "download_page", no_download)
        result = module.gather_collection(
            COLLECTION, delay=0, metadata_mode="cached", cache_dir=cache_dir
        )

        self.assertEqual(result, {})
        no_download.assert_not_called()
        module.registry.add_story.assert_not_called()

        self.assertEqual(fake_gatherer.slugs, [])

    def test_cached_collection_downloads_only_new_story(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        fake_gatherer = fake_gatherer_fixture(tmp_path)
        collection_setup = collection_setup_fixture(
            module, fake_gatherer, self.patch_attribute, tmp_path
        )
        cache_dir, _ = collection_setup
        module.registry.check_story.side_effect = [True, False]
        fetched = []

        def download(session, url):
            fetched.append(url)
            return STORY_HTML

        self.patch_attribute(module, "download_page", download)
        result = module.gather_collection(
            COLLECTION, delay=0, metadata_mode="cached", cache_dir=cache_dir
        )

        self.assertEqual(len(result), 1)

        self.assertEqual(fetched, [SECOND])

        self.assertEqual(module.registry.add_story.call_count, 1)

        self.assertEqual(module.registry.check_story.call_count, 2)

    def test_cached_collection_missing_toc_does_not_fetch(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        no_download = Mock(side_effect=AssertionError("Unexpected download"))
        self.patch_attribute(module, "download_page", no_download)
        with self.assertRaisesRegex(FileNotFoundError, "No saved table of contents"):
            module.gather_collection(
                COLLECTION, delay=0, metadata_mode="cached", cache_dir=tmp_path
            )
        no_download.assert_not_called()

    def test_cached_collection_toc_reads_disk_and_uncached_stories_download(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        fake_gatherer = fake_gatherer_fixture(tmp_path)
        collection_setup = collection_setup_fixture(
            module, fake_gatherer, self.patch_attribute, tmp_path
        )
        cache_dir, _ = collection_setup
        requested = []

        def download(session, url):
            requested.append(url)
            return STORY_HTML

        self.patch_attribute(module, "download_page", download)
        result = module.gather_collection(
            COLLECTION, delay=0, metadata_mode="cached", cache_dir=cache_dir
        )

        self.assertEqual(len(result), 2)

        self.assertEqual(requested, [FIRST, SECOND])

        self.assertNotIn(TOC, requested)

        for url in (FIRST, SECOND):
            cached_story = module._cache_file(cache_dir, "stories", url, "html")
            self.assertEqual(cached_story.read_text(encoding="utf-8"), STORY_HTML)

    def test_refresh_collection_downloads_and_saves_toc(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        fake = Mock(path=str(tmp_path / "corpus"))
        module.downloaders.DataGatherer.return_value = fake
        requested = []

        def download(session, url):
            requested.append(url)
            return TOC_HTML if url == TOC else STORY_HTML

        self.patch_attribute(module, "download_page", download)
        self.patch_attribute(module, "sleep", Mock())
        self.patch_attribute(
            module, "gather_story", Mock(return_value=(7, "saved.json", None))
        )
        result = module.gather_collection(
            COLLECTION, delay=0, metadata_mode="refresh", cache_dir=tmp_path
        )
        cached_path = module._cache_file(tmp_path, "tables_of_contents", TOC, "html")

        self.assertEqual(requested, [TOC, FIRST, SECOND])

        self.assertEqual(cached_path.read_text(encoding="utf-8"), TOC_HTML)

        self.assertEqual(result, {7: "saved.json"})

    def test_invalid_toc_refresh_preserves_old_cache(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        cached_path = module._cache_file(tmp_path, "tables_of_contents", TOC, "html")
        cached_path.parent.mkdir(parents=True, exist_ok=True)
        cached_path.write_text(TOC_HTML, encoding="utf-8")
        self.patch_attribute(
            module, "download_page", Mock(return_value="<nav class='toc'></nav>")
        )
        result = module.gather_collection(
            COLLECTION, delay=0, metadata_mode="refresh", cache_dir=tmp_path
        )

        self.assertEqual(result, {})

        self.assertEqual(cached_path.read_text(encoding="utf-8"), TOC_HTML)

    def test_story_download_failure_continues_to_next_story(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        fake_gatherer = fake_gatherer_fixture(tmp_path)
        collection_setup = collection_setup_fixture(
            module, fake_gatherer, self.patch_attribute, tmp_path
        )
        cache_dir, _ = collection_setup

        def download(session, url):
            if url == FIRST:
                raise requests.RequestException("connection reset")
            return STORY_HTML

        self.patch_attribute(module, "download_page", download)
        result = module.gather_collection(
            COLLECTION, delay=0, metadata_mode="cached", cache_dir=cache_dir
        )

        self.assertEqual(len(result), 1)

        self.assertEqual(module.registry.add_story.call_count, 1)

    def test_story_extraction_failure_leaves_registry_unchanged(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        fake_gatherer = fake_gatherer_fixture(tmp_path)
        collection_setup = collection_setup_fixture(
            module, fake_gatherer, self.patch_attribute, tmp_path
        )
        cache_dir, _ = collection_setup
        self.patch_attribute(
            module, "download_page", Mock(return_value="<main></main>")
        )
        result = module.gather_collection(
            COLLECTION, delay=0, metadata_mode="cached", cache_dir=cache_dir
        )

        self.assertEqual(result, {})
        module.registry.add_story.assert_not_called()

    def test_gather_collection_uses_author_and_collection_path(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        fake_gatherer = fake_gatherer_fixture(tmp_path)
        collection_setup = collection_setup_fixture(
            module, fake_gatherer, self.patch_attribute, tmp_path
        )
        cache_dir, _ = collection_setup
        module.registry.check_story.return_value = True
        module.gather_collection(
            COLLECTION, delay=0, metadata_mode="cached", cache_dir=cache_dir
        )
        args = module.downloaders.DataGatherer.call_args.args

        self.assertEqual(args[0], "standard_ebooks/author-collected-stories")

    def test_gather_rejects_offline_before_any_download(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        no_download = Mock(side_effect=AssertionError("Unexpected network call"))
        self.patch_attribute(module, "get_collection_urls", no_download)
        with self.assertRaisesRegex(ValueError, "Offline story downloads"):
            module.gather(offline=True)
        no_download.assert_not_called()

    def test_gather_rejects_invalid_metadata_mode(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        no_download = Mock(side_effect=AssertionError("Unexpected network call"))
        self.patch_attribute(module, "get_collection_urls", no_download)
        with self.assertRaisesRegex(ValueError, "metadata_mode"):
            module.gather(metadata_mode="invalid")
        no_download.assert_not_called()

    def test_gather_passes_cache_options_and_prints_total(self):
        tmp_path = self.tmp_path
        module = self.module(tmp_path)
        capsys = self.capsys
        list_mock = Mock(return_value=[COLLECTION, COLLECTION + "-2"])
        collection_mock = Mock(
            side_effect=[{0: "one.json"}, {1: "two.json", 2: "three.json"}]
        )
        self.patch_attribute(module, "get_collection_urls", list_mock)
        self.patch_attribute(module, "gather_collection", collection_mock)
        module.gather(cache_dir=tmp_path, metadata_mode="cached")
        list_mock.assert_called_once_with(metadata_mode="cached", cache_dir=tmp_path)

        self.assertEqual(collection_mock.call_count, 2)

        self.assertEqual(
            collection_mock.call_args.kwargs,
            {"metadata_mode": "cached", "cache_dir": tmp_path},
        )

        self.assertIn(
            "Total stories in StandardEBooks corpus: 3", capsys.readouterr().out
        )


class TestStandardEbooksStoryCache(LCATSTestCase):
    """Cache original story HTML in the LCATS cache, without pytest."""

    def module(self):
        """Use the actual gatherer with mocks limited to external dependencies."""
        self.patch_attribute(
            gatherer, "DEFAULT_CACHE_DIR", self.tmp_path / "default-cache"
        )
        self.patch_attribute(downloaders, "DataGatherer", Mock())
        self.patch_attribute(
            names,
            "canonical_author",
            SimpleNamespace(
                canonical_key=lambda author: author,
                last_name=lambda author: author.split()[-1],
            ),
        )

        return gatherer

    def prepare_collection(self, module, *, cached_stories=False):
        """Provide a one-story table of contents in a temporary directory."""
        toc_html = f'<nav class="toc"><a href="{FIRST}">First Story</a></nav>'
        toc_path = module._cache_file(self.tmp_path, "tables_of_contents", TOC, "html")
        toc_path.parent.mkdir(parents=True, exist_ok=True)
        toc_path.write_text(toc_html, encoding="utf-8")

        if cached_stories:
            story_path = module._cache_file(self.tmp_path, "stories", FIRST, "html")
            story_path.parent.mkdir(parents=True, exist_ok=True)
            story_path.write_text(STORY_HTML, encoding="utf-8")

    def test_refresh_saves_story_and_cached_mode_reuses_it(self):
        module = self.module()
        downloaded = Mock(return_value=STORY_HTML)
        self.patch_attribute(module, "download_page", downloaded)

        fresh = module.get_story_page(object(), FIRST, cache_dir=self.tmp_path)
        cached_path = module._cache_file(self.tmp_path, "stories", FIRST, "html")

        self.assertEqual(fresh, STORY_HTML)
        self.assertEqual(cached_path.read_text(encoding="utf-8"), STORY_HTML)
        downloaded.assert_called_once()

        downloaded.reset_mock()
        cached = module.get_story_page(
            object(),
            FIRST,
            metadata_mode="cached",
            cache_dir=self.tmp_path,
        )

        self.assertEqual(cached, STORY_HTML)
        downloaded.assert_not_called()

    def test_cache_miss_downloads_and_saves_story(self):
        module = self.module()
        downloaded = Mock(return_value=STORY_HTML)
        self.patch_attribute(module, "download_page", downloaded)

        result = module.get_story_page(
            object(),
            FIRST,
            metadata_mode="cached",
            cache_dir=self.tmp_path,
        )

        self.assertEqual(result, STORY_HTML)
        downloaded.assert_called_once()
        cached_path = module._cache_file(self.tmp_path, "stories", FIRST, "html")
        self.assertTrue(cached_path.is_file())

    def test_failed_refresh_preserves_preexisting_story_cache(self):
        module = self.module()
        cached_path = module._cache_file(self.tmp_path, "stories", FIRST, "html")
        cached_path.parent.mkdir(parents=True, exist_ok=True)
        cached_path.write_text(STORY_HTML, encoding="utf-8")

        def fail_download(session, url):
            raise RuntimeError("download failed")

        self.patch_attribute(module, "download_page", fail_download)

        with self.assertRaisesRegex(RuntimeError, "download failed"):
            module.get_story_page(object(), FIRST, cache_dir=self.tmp_path)

        self.assertEqual(cached_path.read_text(encoding="utf-8"), STORY_HTML)

    def test_cached_collection_uses_saved_story_without_network(self):
        module = self.module()
        self.prepare_collection(module, cached_stories=True)
        download = Mock(side_effect=AssertionError("unexpected network access"))
        save_story = Mock(return_value=(1, "result.json", None))
        self.patch_attribute(module, "download_page", download)
        self.patch_attribute(module, "gather_story", save_story)
        self.patch_attribute(module, "_story_exists", Mock(return_value=False))
        self.patch_attribute(module, "sleep", Mock())

        result = module.gather_collection(
            COLLECTION,
            delay=0,
            metadata_mode="cached",
            cache_dir=self.tmp_path,
        )

        self.assertEqual(result, {1: "result.json"})
        save_story.assert_called_once()
        download.assert_not_called()

    def test_registry_duplicate_skips_story_cache_and_download(self):
        module = self.module()
        self.prepare_collection(module)
        download = Mock(side_effect=AssertionError("unexpected network access"))
        save_story = Mock()
        self.patch_attribute(module, "download_page", download)
        self.patch_attribute(module, "gather_story", save_story)
        self.patch_attribute(module, "_story_exists", Mock(return_value=True))

        result = module.gather_collection(
            COLLECTION,
            delay=0,
            metadata_mode="cached",
            cache_dir=self.tmp_path,
        )

        self.assertEqual(result, {})
        save_story.assert_not_called()
        download.assert_not_called()
        story_path = module._cache_file(self.tmp_path, "stories", FIRST, "html")
        self.assertFalse(story_path.exists())

    def test_cached_story_skips_network_throttling_delay(self):
        module = self.module()
        self.prepare_collection(module, cached_stories=True)
        self.patch_attribute(
            module, "download_page", Mock(side_effect=AssertionError("network"))
        )
        self.patch_attribute(
            module, "gather_story", Mock(return_value=(1, "result.json", None))
        )
        self.patch_attribute(module, "_story_exists", Mock(return_value=False))
        sleep = Mock()
        self.patch_attribute(module, "sleep", sleep)

        module.gather_collection(
            COLLECTION,
            delay=5,
            metadata_mode="cached",
            cache_dir=self.tmp_path,
        )

        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
