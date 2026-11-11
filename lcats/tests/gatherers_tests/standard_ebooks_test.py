"""Offline unit tests for the supplied Standard Ebooks gatherer.

Run: pytest -q test_gatherer.py

The LCATS imports are replaced with lightweight stubs at import time, so this
suite can run outside an installed LCATS checkout. All HTTP and disk writes
are intercepted or directed to pytest's tmp_path fixture.
"""

import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

import pytest
import requests
from bs4 import BeautifulSoup


SOURCE = Path(__file__).with_name("gatherer(4).py")
SITE = "https://standardebooks.org"
TOC = f"{SITE}/ebooks/example-author/collected-stories/text"
COLLECTION = f"{SITE}/ebooks/example-author/collected-stories"


@pytest.fixture
def module(monkeypatch):
    """Import the actual source without requiring the rest of LCATS."""
    lcats = types.ModuleType("lcats")
    lcats.__path__ = []
    gatherers = types.ModuleType("lcats.gatherers")
    gatherers.__path__ = []
    utils = types.ModuleType("lcats.utils")
    utils.__path__ = []
    downloaders = types.ModuleType("lcats.gatherers.downloaders")
    normalization = types.ModuleType("lcats.gatherers.normalization")
    parser = types.ModuleType("lcats.gatherers.parser")
    registry = types.ModuleType("lcats.gatherers.registry")
    names = types.ModuleType("lcats.utils.names")
    constants = types.ModuleType("lcats.constants")

    downloaders.DataGatherer = Mock()
    constants.FILE_SUFFIX = ".json"
    names.title_and_author_to_filename = lambda title, authors, **kwargs: (
        f"{title.replace(' ', '_')}__{authors[0].replace(' ', '_')}.json"
    )
    names.canonical_author = types.SimpleNamespace(
        canonical_key=lambda name: name,
        last_name=lambda name: name.split()[-1],
    )
    parser.chaptered = lambda body: False
    registry.check_and_add = lambda *args, **kwargs: True
    normalization.normalize_story_dict = lambda data, **kwargs: None

    lcats.constants = constants
    lcats.gatherers = gatherers
    lcats.utils = utils
    utils.names = names
    for name, obj in {
        "lcats": lcats,
        "lcats.constants": constants,
        "lcats.gatherers": gatherers,
        "lcats.utils": utils,
        "lcats.utils.names": names,
        "lcats.gatherers.downloaders": downloaders,
        "lcats.gatherers.normalization": normalization,
        "lcats.gatherers.parser": parser,
        "lcats.gatherers.registry": registry,
    }.items():
        monkeypatch.setitem(sys.modules, name, obj)

    spec = importlib.util.spec_from_file_location("standard_ebooks_under_test", SOURCE)
    result = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, result)
    spec.loader.exec_module(result)
    return result


@pytest.fixture
def fake_gatherer(tmp_path):
    class FakeGatherer:
        path = str(tmp_path)

        def __init__(self):
            self.slugs = []

        def ensure(self, slug):
            self.slugs.append(slug)
            bucket = tmp_path / slug
            bucket.mkdir(parents=True, exist_ok=True)
            return str(bucket), str(bucket / "story.json")

    return FakeGatherer()


@pytest.mark.parametrize("number", [1, 2, 23])
def test_set_page_parameter_preserves_existing_query(module, number):
    url = module.set_page_parameter(
        "https://standardebooks.org/subjects/shorts?view=list&page=99&x=", number
    )
    params = parse_qs(urlparse(url).query, keep_blank_values=True)
    assert params == {"view": ["list"], "page": [str(number)], "x": [""]}


def test_canonicalize_url(module):
    assert module.canonicalize_url(f"{COLLECTION}/?download=1#section") == COLLECTION


@pytest.mark.parametrize(
    "url,valid",
    [
        (COLLECTION, True),
        (COLLECTION + "/", True),
        (COLLECTION + "/text", False),
        (f"{SITE}/ebooks/only-author", False),
        ("https://other.example/ebooks/example-author/collected-stories", False),
        ("javascript:alert(1)", False),
    ],
)
def test_is_collection_url(module, url, valid):
    assert module.is_collection_url(url, "standardebooks.org") is valid


def test_extract_collection_urls_filters_and_deduplicates(module):
    html = f"""
    <a href="/ebooks/example-author/collected-stories/?ref=nav#top">first</a>
    <a href="{COLLECTION}">duplicate</a>
    <a href="/ebooks/second-author/another-book">second</a>
    <a href="/ebooks/example-author/collected-stories/text">text</a>
    <a href="https://evil.example/ebooks/foo/bar">external</a>
    """
    assert module.extract_collection_urls(html, f"{SITE}/subjects/shorts") == [
        COLLECTION,
        f"{SITE}/ebooks/second-author/another-book",
    ]


def test_get_collection_urls_stops_after_page_with_no_new_links(module, monkeypatch):
    page1 = f'<a href="{COLLECTION}">A</a>'
    page2 = f'<a href="{COLLECTION}">A again</a><a href="/ebooks/b/c">B</a>'
    page3 = '<a href="/ebooks/b/c">B again</a>'
    responses = [Mock(text=html) for html in (page1, page2, page3)]
    for response in responses:
        response.raise_for_status = Mock()
    session = Mock()
    session.headers = {}
    session.get.side_effect = responses
    monkeypatch.setattr(module.requests, "Session", lambda: session)

    result = module.get_collection_urls(delay=0, maximum_pages=5)
    assert result == [COLLECTION, f"{SITE}/ebooks/b/c"]
    assert session.get.call_count == 3
    assert [
        parse_qs(urlparse(call.args[0]).query)["page"][0]
        for call in session.get.call_args_list
    ] == ["1", "2", "3"]
    assert all(call.kwargs["timeout"] == 30 for call in session.get.call_args_list)


def test_get_collection_urls_enforces_page_limit(module, monkeypatch):
    session = Mock(headers={})
    session.get.return_value = Mock(
        text=f'<a href="{COLLECTION}">A</a>',
        raise_for_status=Mock(),
    )
    monkeypatch.setattr(module.requests, "Session", lambda: session)
    with pytest.raises(RuntimeError, match="safety limit"):
        module.get_collection_urls(delay=0, maximum_pages=1)


def test_download_page_checks_status_and_returns_text(module):
    response = Mock(text="<html>ok</html>", encoding=None)
    session = Mock()
    session.get.return_value = response
    assert (
        module.download_page(session, "https://example.test", timeout=12)
        == "<html>ok</html>"
    )
    session.get.assert_called_once_with("https://example.test", timeout=12)
    response.raise_for_status.assert_called_once_with()
    assert response.encoding == "utf-8"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("II: A Domiciliary Visit", "A Domiciliary Visit"),
        ("3. The Adventure", "The Adventure"),
        ("IV) Another Story", "Another Story"),
        ("X — The Last Story", "The Last Story"),
        ("  12 -  A Story\u00a0 Title ", "A Story Title"),
        ("I Have a Dream", "I Have a Dream"),
        ("IVORY HOUSE", "IVORY HOUSE"),
    ],
)
def test_clean_title(module, raw, expected):
    assert module.clean_title(raw) == expected


def test_normalize_inline_text(module):
    assert (
        module.normalize_inline_text("  A\u00a0  tale\u00ad\n of  two  ")
        == "A tale of two"
    )


@pytest.mark.parametrize(
    "title", ["Preface", "  TABLE OF CONTENTS: ", "Endnotes.", "Introduction"]
)
def test_non_story_titles(module, title):
    assert module.is_non_story_title(title)


def test_story_url_requires_one_child_and_rejects_front_matter(module):
    assert module.is_story_url(TOC + "/an-adventure", TOC)
    for bad in (
        TOC + "/dedication-2",
        TOC + "/endnotes",
        TOC + "/single-page",
        TOC + "/one/two",
        TOC,
        "https://other.example/ebooks/a/b/text/story",
    ):
        assert not module.is_story_url(bad, TOC)


def test_extract_story_links_uses_toc_and_removes_nonstories(module):
    html = """
    <nav role="doc-toc">
      <a href="/ebooks/example-author/collected-stories/text/an-adventure">II: An Adventure</a>
      <a href="/ebooks/example-author/collected-stories/text/an-adventure#part-2">duplicate</a>
      <a href="/ebooks/example-author/collected-stories/text/dedication-1">Dedication</a>
      <a href="/ebooks/example-author/collected-stories/text/extra-file">Preface</a>
      <a href="/ebooks/example-author/collected-stories/text/other-story"></a>
    </nav>
    <main><a href="not-in-toc">Not in TOC</a></main>
    """
    stories = module.extract_story_links(html, TOC)
    assert [(s.number, s.title, s.url) for s in stories] == [
        (1, "An Adventure", TOC + "/an-adventure"),
        (2, "Other Story", TOC + "/other-story"),
    ]


def test_extract_story_links_raises_when_no_stories(module):
    with pytest.raises(ValueError, match="No individual story links"):
        module.extract_story_links(
            '<nav class="toc"><a href="endnotes">Endnotes</a></nav>', TOC
        )


def test_choose_story_container_prefers_most_paragraph_text(module):
    soup = BeautifulSoup(
        """
        <main><article><p>short</p></article>
          <section><p>A substantially longer piece of story prose appears here.</p></section>
        </main>
    """,
        "html.parser",
    )
    assert "longer piece" in module.choose_story_container(soup).get_text()


def test_remove_unwanted_elements_preserves_prose(module):
    soup = BeautifulSoup(
        """
      <article><nav>Navigation</nav><p>Hello<a href="#note1">[1]</a> world.</p>
      <aside>Aside</aside><p>Another sentence.</p><section class="footnotes">notes</section></article>
    """,
        "html.parser",
    )
    article = soup.article
    module.remove_unwanted_elements(article)
    text = article.get_text(" ", strip=True)
    assert "Hello" in text and "world." in text and "Another sentence." in text
    assert "[1]" not in text and "Navigation" not in text and "Aside" not in text
    assert "notes" not in text


def test_block_text_preserves_line_breaks(module):
    soup = BeautifulSoup(
        "<p> One   line<br/>Two\u00a0 lines<br/>  Three </p>", "html.parser"
    )
    assert module.block_text(soup.p) == "One line\nTwo lines\nThree"


def test_gather_story_writes_expected_json_and_passes_slug(
    module, monkeypatch, fake_gatherer
):
    normalize = Mock(
        side_effect=lambda data, **kwargs: data["metadata"].update(repaired=True)
    )
    check = Mock(return_value=True)
    monkeypatch.setattr(module.normalization, "normalize_story_dict", normalize)
    monkeypatch.setattr(module.registry, "check_and_add", check)
    html = """<main><article>
        <nav>Previous</nav><h2>II: An Adventure</h2>
        <p>First paragraph.</p><p>First paragraph.</p>
        <p>Second paragraph.</p><footer>Next</footer>
    </article></main>"""
    story_id, filename, error = module.gather_story(
        fake_gatherer, html, "An Adventure", "Example Author", TOC + "/an-adventure"
    )
    assert (story_id, error) == (0, None)
    assert filename is not None
    assert fake_gatherer.slugs == ["an_adventure__Example_Author"]
    saved = json.loads(Path(filename).read_text(encoding="utf-8"))
    assert saved["name"] == "an adventure"
    assert saved["author"] == "Example Author"
    assert saved["body"] == "II: An Adventure\n\nFirst paragraph.\n\nSecond paragraph."
    assert saved["metadata"]["repaired"] is True
    assert saved["metadata"]["url"] == TOC + "/an-adventure"
    assert normalize.call_args.kwargs == {
        "collection": str(Path(fake_gatherer.path)),
        "story_id": "an_adventure__Example_Author",
    }
    check.assert_called_once_with(
        "an_adventure", "Example_Author", mode="discard", source="Standard EBooks"
    )


def test_gather_story_no_duplicate_file(module, monkeypatch, fake_gatherer):
    monkeypatch.setattr(module.registry, "check_and_add", Mock(return_value=False))
    story_id, filename, error = module.gather_story(
        fake_gatherer,
        "<main><p>Text.</p></main>",
        "A Story",
        "Someone",
        TOC + "/a-story",
    )
    assert (story_id, filename) == (0, None)
    assert "already appears" in error
    assert fake_gatherer.slugs == []


def test_gather_story_skips_chaptered_text(module, monkeypatch, fake_gatherer):
    monkeypatch.setattr(module.parser, "chaptered", lambda text: True)
    story_id, filename, error = module.gather_story(
        fake_gatherer,
        "<main><p>Chapter One</p></main>",
        "A Story",
        "Someone",
        TOC + "/a-story",
    )
    assert (story_id, filename) == (0, None)
    assert "chapters" in error
    assert fake_gatherer.slugs == []


def test_gather_story_raises_on_empty_prose(module, fake_gatherer):
    with pytest.raises(ValueError, match="No prose blocks"):
        module.gather_story(
            fake_gatherer,
            "<main><nav>Next</nav></main>",
            "Empty",
            "Someone",
            TOC + "/empty",
        )


def test_gather_collection_collects_successes_and_continues_after_error(
    module, monkeypatch
):
    stories = [
        module.Story(1, "A", TOC + "/a"),
        module.Story(2, "B", TOC + "/b"),
        module.Story(3, "C", TOC + "/c"),
    ]
    fake_dg = Mock()
    constructor = Mock(return_value=fake_dg)
    monkeypatch.setattr(module.downloaders, "DataGatherer", constructor)
    monkeypatch.setattr(module, "make_session", lambda: object())
    monkeypatch.setattr(module, "extract_story_links", lambda html, url: stories)
    monkeypatch.setattr(
        module, "download_page", lambda session, url: "<html>irrelevant</html>"
    )
    monkeypatch.setattr(module, "sleep", Mock())
    outcomes = iter(
        [(1, "/tmp/a.json", None), (2, None, "duplicate"), (3, "/tmp/c.json", None)]
    )
    monkeypatch.setattr(module, "gather_story", lambda *args: next(outcomes))
    assert module.gather_collection(COLLECTION, delay=0) == {
        1: "/tmp/a.json",
        3: "/tmp/c.json",
    }
    assert constructor.call_args.args[0] == "standard_ebooks/author-collected-stories"


def test_gather_collection_returns_empty_dict_on_toc_network_failure(
    module, monkeypatch
):
    monkeypatch.setattr(module.downloaders, "DataGatherer", Mock())
    monkeypatch.setattr(module, "make_session", lambda: object())

    def fail(*args):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(module, "download_page", fail)
    assert module.gather_collection(COLLECTION) == {}


def test_gather_collection_handles_individual_story_failure(module, monkeypatch):
    stories = [module.Story(1, "A", TOC + "/a"), module.Story(2, "B", TOC + "/b")]
    monkeypatch.setattr(module.downloaders, "DataGatherer", Mock())
    monkeypatch.setattr(module, "make_session", lambda: object())
    monkeypatch.setattr(module, "extract_story_links", lambda *args: stories)
    monkeypatch.setattr(module, "download_page", lambda *args: "html")
    monkeypatch.setattr(module, "sleep", Mock())
    calls = iter([ValueError("bad story"), (1, "/tmp/b.json", None)])

    def fake_story(*args):
        item = next(calls)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(module, "gather_story", fake_story)
    assert module.gather_collection(COLLECTION, delay=0) == {1: "/tmp/b.json"}


def test_gather_counts_all_downloads(module, monkeypatch, capsys):
    urls = [COLLECTION, f"{SITE}/ebooks/another/collection"]
    monkeypatch.setattr(module, "get_collection_urls", lambda: urls)
    monkeypatch.setattr(
        module,
        "gather_collection",
        lambda url: {1: "a", 2: "b"} if url == urls[0] else {3: "c"},
    )
    assert module.gather(offline=True, cache_dir=False) is None
    assert "Total stories in StandardEBooks corpus: 3" in capsys.readouterr().out
