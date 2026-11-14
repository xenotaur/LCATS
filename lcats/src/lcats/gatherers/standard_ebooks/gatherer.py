"""Corpus extractor for the StandardEBooks collection."""

from __future__ import annotations

from dataclasses import dataclass
from time import sleep
from urllib.parse import parse_qs, urlencode, urlunparse, unquote, urljoin, urlparse
import re
import sys
import os
import json
import hashlib
import tempfile
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag
import time

import lcats.gatherers.downloaders as downloaders
from lcats import constants
from lcats.utils import names
from lcats.utils import env
from lcats.gatherers import normalization
from lcats.gatherers import parser
from lcats.gatherers import registry

DEFAULT_URL = "https://standardebooks.org/subjects/shorts" "?per-page=48&view=list"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 " "(compatible; StandardEbooksCollectionExtractor/1.0)")
}


# Cache collection lists, tables of contents, and original story HTML.
DEFAULT_CACHE_DIR = env.cache_root() / "standard_ebooks"
METADATA_MODES = {"refresh", "cached"}


def _metadata_cache_dir(cache_dir) -> Path:
    """Resolve an optional cache directory without creating it on reads."""
    return (
        DEFAULT_CACHE_DIR
        if cache_dir is False or cache_dir is None
        else Path(cache_dir)
    )


def _cache_file(cache_dir, kind: str, url: str, extension: str) -> Path:
    """Use a stable URL-derived name (including URL query parameters)."""
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return _metadata_cache_dir(cache_dir) / kind / f"{digest}.{extension}"


def _atomic_cache_write(path: Path, content: str) -> None:
    """Avoid leaving incomplete cache entries if writing is interrupted."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(content)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _check_metadata_mode(mode: str) -> None:
    if mode not in METADATA_MODES:
        raise ValueError(f"metadata_mode must be one of {sorted(METADATA_MODES)}")


def get_story_page(
    session: requests.Session,
    url: str,
    *,
    metadata_mode: str = "refresh",
    cache_dir=False,
) -> str:
    """Read cached story HTML or download and cache the original page.

    In cached mode, a missing story page is downloaded and saved. This is
    intentional: older caches contain only collection lists and TOCs, and
    skipped or previously registered stories might not yet have HTML copies.
    """
    _check_metadata_mode(metadata_mode)

    cached_path = _cache_file(cache_dir, "stories", url, "html")

    if metadata_mode == "cached" and cached_path.is_file():
        print(f"Reading saved story: {url}")
        return cached_path.read_text(encoding="utf-8")

    print(f"Downloading story: {url}")
    html = download_page(session, url)
    _atomic_cache_write(cached_path, html)

    return html


def set_page_parameter(url: str, page_number: int) -> str:
    """Return the URL with its page parameter set to page_number."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)

    query["page"] = [str(page_number)]

    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def canonicalize_url(url: str) -> str:
    """Remove query strings, fragments, and trailing slashes."""
    parsed = urlparse(url)

    return urlunparse(
        parsed._replace(
            query="",
            fragment="",
            path=parsed.path.rstrip("/"),
        )
    )


def is_collection_url(url: str, site_host: str) -> bool:
    """
    Return True for URLs having this structure:

        https://standardebooks.org/ebooks/author-slug/book-slug
    """
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        return False

    if parsed.netloc.casefold() != site_host.casefold():
        return False

    path_parts = [part for part in parsed.path.strip("/").split("/") if part]

    return len(path_parts) == 3 and path_parts[0].casefold() == "ebooks"


def extract_collection_urls(
    html: str,
    page_url: str,
) -> list[str]:
    """Extract collection URLs from one results page."""
    soup = BeautifulSoup(html, "html.parser")
    site_host = urlparse(page_url).netloc

    urls: list[str] = []
    seen: set[str] = set()

    for link in soup.select("a[href]"):
        href = link.get("href")

        if not isinstance(href, str):
            continue

        absolute_url = canonicalize_url(urljoin(page_url, href))

        if not is_collection_url(absolute_url, site_host):
            continue

        comparison_key = absolute_url.casefold()

        if comparison_key in seen:
            continue

        seen.add(comparison_key)
        urls.append(absolute_url)

    return urls


def get_collection_urls(
    start_url: str = DEFAULT_URL,
    delay: float = 0.5,
    maximum_pages: int = 1000,
    *,
    metadata_mode: str = "refresh",
    cache_dir=False,
) -> list[str]:
    """
    Return all collection URLs from every results page.

    Pagination ends when a page contains no collection URLs that have not
    already appeared on an earlier page.
    """
    _check_metadata_mode(metadata_mode)
    cached_path = _cache_file(cache_dir, "collection_lists", start_url, "json")
    if metadata_mode == "cached":
        if not cached_path.is_file():
            raise FileNotFoundError(f"No saved collection URL list: {cached_path}")
        stored = json.loads(cached_path.read_text(encoding="utf-8"))
        if (
            not isinstance(stored, dict)
            or stored.get("start_url") != start_url
            or not isinstance(stored.get("urls"), list)
            or not all(isinstance(url, str) for url in stored["urls"])
        ):
            raise ValueError(f"Invalid collection URL cache: {cached_path}")
        return stored["urls"]

    session = requests.Session()
    session.headers.update(HEADERS)

    all_urls: list[str] = []
    seen_urls: set[str] = set()

    for page_number in range(1, maximum_pages + 1):
        page_url = set_page_parameter(start_url, page_number)

        response = session.get(page_url, timeout=30)
        response.raise_for_status()

        page_urls = extract_collection_urls(
            response.text,
            page_url,
        )

        new_urls = [url for url in page_urls if url.casefold() not in seen_urls]

        if not new_urls:
            break

        for url in new_urls:
            seen_urls.add(url.casefold())
            all_urls.append(url)

        if delay > 0:
            time.sleep(delay)

    else:
        raise RuntimeError(f"Reached the safety limit of {maximum_pages} pages.")

    _atomic_cache_write(
        cached_path,
        json.dumps({"start_url": start_url, "urls": all_urls}, indent=2),
    )
    return all_urls


USER_AGENT = "Mozilla/5.0 (compatible; StandardEbooksStoryExtractor/1.0)"


@dataclass(frozen=True)
class Story:
    """A story discovered in the table of contents."""

    number: int
    title: str
    url: str


def make_session() -> requests.Session:
    """Create a requests session with appropriate headers."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": (
                "application/xhtml+xml,"
                "text/html;q=0.9,"
                "application/xml;q=0.8,"
                "*/*;q=0.5"
            ),
        }
    )
    return session


def download_page(
    session: requests.Session,
    url: str,
    timeout: int = 30,
) -> str:
    """Download a webpage and return its decoded text."""
    response = session.get(url, timeout=timeout)
    response.raise_for_status()

    # Standard Ebooks serves XHTML. UTF-8 is the normal encoding, but
    # requests can use the declared encoding when one is present.
    response.encoding = response.encoding or "utf-8"

    return response.text


def normalize_inline_text(text: str) -> str:
    """Normalize whitespace inside a heading or paragraph."""
    text = text.replace("\xa0", " ")
    text = text.replace("\u00ad", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_title(text: str) -> str:
    """Clean the visible title from a table-of-contents entry.

    Standard Ebooks sometimes prefixes story titles with chapter/section
    numbers such as ``II: A Domiciliary Visit``, ``3. The Adventure``, or
    ``IV) Another Story``.  Those prefixes are structural metadata rather
    than part of the story title, so remove them before the title is used
    for filenames or stored metadata.
    """
    text = normalize_inline_text(text)

    # Remove a leading Arabic or Roman numeral followed by common TOC
    # punctuation.  Requiring punctuation avoids damaging titles that
    # legitimately begin with a Roman-numeral-looking word.
    text = re.sub(
        r"^\s*(?:\d+|[IVXLCDM]+)\s*(?:[.):]|[-\u2013\u2014])\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return text.strip()


# Common Standard Ebooks front matter, back matter, and navigational items
# that can appear as peers of actual stories in a collection TOC.
NON_STORY_SLUGS = {
    "acknowledgements",
    "acknowledgments",
    "afterword",
    "bibliography",
    "colophon",
    "copyright-page",
    "dedication",
    "endnotes",
    "epigraph",
    "foreword",
    "glossary",
    "halftitlepage",
    "imprint",
    "index",
    "introduction",
    "landmarks",
    "loi",
    "lot",
    "preface",
    "single-page",
    "table-of-contents",
    "titlepage",
    "toc",
    "uncopyright",
}

NON_STORY_TITLES = {
    "acknowledgements",
    "acknowledgments",
    "afterword",
    "bibliography",
    "colophon",
    "copyright",
    "copyright page",
    "dedication",
    "endnotes",
    "epigraph",
    "foreword",
    "glossary",
    "half title page",
    "imprint",
    "index",
    "introduction",
    "landmarks",
    "preface",
    "table of contents",
    "title page",
    "titlepage",
    "uncopyright",
}


def is_non_story_title(title: str) -> bool:
    """Return True for common non-story TOC labels."""
    normalized = normalize_inline_text(title).casefold().strip(" .:\t\r\n")
    return normalized in NON_STORY_TITLES


# def canonicalize_url(url: str) -> str:
#    """Remove fragments and trailing slashes from a URL."""
#    parsed = urlparse(url)

#    return parsed._replace(
#        fragment="",
#        query="",
#        path=parsed.path.rstrip("/"),
#    ).geturl()


def is_story_url(url: str, toc_url: str) -> bool:
    """
    Return True when a URL appears to be an individual story page.

    A story URL must:

    * use the same host as the table of contents;
    * be a descendant of the TOC URL;
    * contain exactly one additional path component;
    * not point to the single-page edition.
    """
    candidate = urlparse(canonicalize_url(url))
    toc = urlparse(canonicalize_url(toc_url))

    if candidate.scheme not in {"http", "https"}:
        return False

    if candidate.netloc != toc.netloc:
        return False

    toc_path = toc.path.rstrip("/")
    candidate_path = candidate.path.rstrip("/")

    if not candidate_path.startswith(toc_path + "/"):
        return False

    relative_path = candidate_path[len(toc_path) + 1 :]

    if not relative_path:
        return False

    # Individual stories have one slug after /text/.
    if "/" in relative_path:
        return False

    slug = relative_path.casefold()

    if slug in NON_STORY_SLUGS:
        return False

    # Some editions number front/back-matter files (for example,
    # dedication-1 or introduction-2).  Treat a numeric suffix on a known
    # non-story slug as the same item.
    base_slug = re.sub(r"-\d+$", "", slug)
    return base_slug not in NON_STORY_SLUGS


def choose_toc_container(soup: BeautifulSoup) -> Tag:
    """Find the element most likely to contain the table of contents."""
    selectors = [
        "nav[epub\\:type~='toc']",
        "nav[role='doc-toc']",
        "nav.toc",
        "#toc",
        ".toc",
        "main",
        "article",
        "body",
    ]

    for selector in selectors:
        container = soup.select_one(selector)
        if container is not None:
            return container

    raise ValueError("Could not locate the table of contents.")


def extract_story_links(html: str, toc_url: str) -> list[Story]:
    """Extract story titles and URLs from the table of contents."""
    soup = BeautifulSoup(html, "html.parser")
    container = choose_toc_container(soup)

    found: list[tuple[str, str]] = []
    seen_urls: set[str] = set()

    for link in container.select("a[href]"):
        href = link.get("href")

        if not isinstance(href, str):
            continue

        absolute_url = canonicalize_url(urljoin(toc_url, href))

        if not is_story_url(absolute_url, toc_url):
            continue

        title = clean_title(link.get_text(" ", strip=True))

        if not title:
            # Use the URL slug only as a fallback.
            slug = unquote(urlparse(absolute_url).path.rsplit("/", 1)[-1])
            title = slug.replace("-", " ").title()

        # Slug filtering handles the normal Standard Ebooks names, while
        # title filtering catches unusual filenames whose visible label is
        # still clearly front/back matter.
        if is_non_story_title(title):
            continue

        if absolute_url in seen_urls:
            continue

        seen_urls.add(absolute_url)
        found.append((title, absolute_url))

    if not found:
        raise ValueError(
            "No individual story links were found in the table of contents."
        )

    return [
        Story(number=index, title=title, url=url)
        for index, (title, url) in enumerate(found, start=1)
    ]


def choose_story_container(soup: BeautifulSoup) -> Tag:
    """
    Locate the element most likely to contain the story.

    When several candidates exist, choose the one containing the largest
    amount of paragraph text.
    """
    selectors = [
        "main article",
        "article",
        "main section",
        "main",
        "[role='main']",
    ]

    candidates: list[Tag] = []

    for selector in selectors:
        candidates.extend(soup.select(selector))

    # Remove duplicate Tag objects while preserving their order.
    unique_candidates: list[Tag] = []
    candidate_ids: set[int] = set()

    for candidate in candidates:
        candidate_id = id(candidate)

        if candidate_id not in candidate_ids:
            candidate_ids.add(candidate_id)
            unique_candidates.append(candidate)

    if not unique_candidates:
        body = soup.find("body")

        if isinstance(body, Tag):
            return body

        raise ValueError("Could not locate the story text.")

    def prose_score(element: Tag) -> int:
        paragraphs = element.find_all("p")
        return sum(len(paragraph.get_text(" ", strip=True)) for paragraph in paragraphs)

    return max(unique_candidates, key=prose_score)


def remove_unwanted_elements(container: Tag) -> None:
    """Remove navigation, scripts, notes, and other non-story elements."""
    selectors = [
        "script",
        "style",
        "noscript",
        "nav",
        "header",
        "footer",
        "aside",
        "form",
        "button",
        "svg",
        "figure",
        ".breadcrumbs",
        ".navigation",
        ".pager",
        ".pagination",
        ".next",
        ".previous",
        ".endnotes",
        ".footnotes",
        "[role='navigation']",
        "[role='doc-endnotes']",
        "[epub\\:type~='endnotes']",
        "[epub\\:type~='footnotes']",
        "[aria-hidden='true']",
    ]

    for selector in selectors:
        for element in list(container.select(selector)):
            element.decompose()

    # Remove footnote reference markers while leaving the sentence intact.
    note_selectors = [
        "a[epub\\:type~='noteref']",
        "a[role='doc-noteref']",
        "a[href^='#note']",
        "a[href^='#footnote']",
        "sup a",
    ]

    for selector in note_selectors:
        for element in list(container.select(selector)):
            element.decompose()


def block_text(element: Tag) -> str:
    """Extract readable text from one block-level element."""
    # Convert line breaks within poems, addresses, or similar blocks.
    for br in element.find_all("br"):
        br.replace_with("\n")

    text = element.get_text(" ", strip=False)
    text = text.replace("\xa0", " ")
    text = text.replace("\u00ad", "")

    lines = []

    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()

        if line:
            lines.append(line)

    return "\n".join(lines).strip()


def _story_registry_key(title: str, author: str) -> tuple[str, str, str]:
    """Return filename and registry keys using the same rules as gather_story."""
    title_key = normalize_inline_text(title).casefold()
    file_name = names.title_and_author_to_filename(
        title_key, [author], ext=constants.FILE_SUFFIX, max_len=50
    )
    title_db, author_part = file_name.split("__", 1)
    author_db = author_part.rsplit(".", 1)[0]
    return file_name, title_db, author_db


def _story_exists(title: str, author: str) -> bool:
    """Check for a previously registered story without modifying the registry."""
    _, title_db, author_db = _story_registry_key(title, author)
    return registry.check_story(title_db, author_db)


def _add_saved_story(title_db: str, author_db: str) -> None:
    """Record a story only after its output has been written successfully."""
    registry.add_story(title_db, author_db, source="Standard EBooks")


def gather_story(
    gatherer,
    html: str,
    expected_title: str,
    author: str,
    url: str,
    *,
    registry_checked: bool = False,
):
    """Extract and save a story; register it only after successful publication."""

    # Initialize the variable if it doesn't exist yet
    if not hasattr(gather_story, "story"):
        gather_story.story = 0

    # Ensure that each output file has its TOC title. Some story pages may
    # display it in the body, while others may not.
    title_key = normalize_inline_text(expected_title).casefold()

    file_name, title_db, author_db = _story_registry_key(expected_title, author)

    # gather_collection checks before downloading; direct callers check here.
    # Neither path registers a story until the JSON file has been saved.
    if not registry_checked and _story_exists(expected_title, author):
        return gather_story.story, None, "Standard EBooks -- Story already appears"

    soup = BeautifulSoup(html, "html.parser")
    container = choose_story_container(soup)

    remove_unwanted_elements(container)

    blocks: list[str] = []

    block_names = {
        "h1",
        "h2",
        "h3",
        "h4",
        "p",
        "blockquote",
        "pre",
    }

    for element in container.find_all(list(block_names)):
        # Do not extract a child paragraph separately when its containing
        # blockquote or preformatted block will also be extracted.
        if element.name == "p" and element.find_parent(["blockquote", "pre"]):
            continue

        # Avoid headings nested inside another selected block.
        parent = element.find_parent(block_names)

        if parent is not None and parent is not container:
            continue

        text = block_text(element)

        if not text:
            continue

        if text.casefold() in {
            "previous",
            "next",
            "contents",
            "table of contents",
        }:
            continue

        blocks.append(text)

    if not blocks:
        raise ValueError("No prose blocks were found on the story page.")

    # Remove consecutive duplicates.
    deduplicated: list[str] = []

    for block in blocks:
        if not deduplicated or block != deduplicated[-1]:
            deduplicated.append(block)

    first_blocks = {
        normalize_inline_text(block).casefold() for block in deduplicated[:3]
    }

    if title_key not in first_blocks:
        deduplicated.insert(0, expected_title)

    body = "\n\n".join(deduplicated[1:])
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    # if contains chapters, we skip it.

    if parser.chaptered(body):
        print("Story contains chapters..., skipping")
        return (gather_story.story, None, "Story has chapters, skipping.")

    if title_db == "endnotes":
        return (gather_story.story, None, "Endnotes are not gathered")
    if title_db == "epigraph":
        return (gather_story.story, None, "Epigraphs are not gathered")

    # The story's canonical slug (no extension): names the bucket
    # subdirectory (Decision 8 of PROP-LCATS-STORY-BUCKET-LAYOUT) and is
    # threaded straight through as the overrides story_id -- never
    # re-derived from the write path's leaf name, which is always the
    # reserved canonical filename post-migration (Decision 7).
    story_slug = os.path.splitext(file_name)[0]

    print(f"Gathering story {title_key}")
    print(f" - File name: {file_name}")

    # Structure the data into a dictionary
    data_to_save = {
        "name": title_key,
        "author": author,
        "body": body,
        "metadata": {
            "author": author,
            "year": "Unknown",
            "url": url,
            "name": file_name,
        },
    }

    path = gatherer.path

    # Apply replayable gather-time repairs (rules + per-story overrides) before
    # the first write so the fix is reproduced on every regeneration, not stored
    # as a one-off.
    normalization.normalize_story_dict(
        data_to_save, collection=path, story_id=story_slug
    )

    # Ensure the file path exists.
    _, file_path = gatherer.ensure(story_slug)

    # Write data to JSON file
    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(data_to_save, json_file, indent=4)

    _add_saved_story(title_db, author_db)
    gather_story.story = gather_story.story + 1
    return gather_story.story - 1, file_path, None


def get_author_from_standard_ebooks_url(url):
    return url.split("/")[4].replace("-", " ")


def get_title_from_standard_ebooks_url(url):
    return url.split("/")[5]


def gather_collection(toc_url, delay=5, *, metadata_mode="refresh", cache_dir=False):
    """Run DataGatherers for one collection of stories from StandardEBooks."""

    full_toc_url = toc_url + "/text"
    author = get_author_from_standard_ebooks_url(toc_url)
    author_last_name = names.canonical_author.last_name(
        names.canonical_author.canonical_key(author)
    )
    title = get_title_from_standard_ebooks_url(toc_url)

    target_directory = "standard_ebooks/" + author_last_name + "-" + title

    gatherer = downloaders.DataGatherer(
        target_directory,
        description=title + " by " + author + " stories from standardEBooks.",
        license="Public domain, from standardEBooks",
    )

    _check_metadata_mode(metadata_mode)
    cached_path = _cache_file(cache_dir, "tables_of_contents", full_toc_url, "html")
    session = make_session()

    try:
        if metadata_mode == "cached":
            if not cached_path.is_file():
                raise FileNotFoundError(f"No saved table of contents: {cached_path}")
            print(f"Reading saved table of contents: {full_toc_url}")
            toc_html = cached_path.read_text(encoding="utf-8")
        else:
            print(f"Downloading table of contents: {full_toc_url}")
            toc_html = download_page(session, full_toc_url)
        stories = extract_story_links(toc_html, full_toc_url)
        if metadata_mode == "refresh":
            _atomic_cache_write(cached_path, toc_html)
    except (FileNotFoundError, OSError) as error:
        # Cached mode is intentionally strict: never fall back to the network.
        if metadata_mode == "cached":
            raise
        print(f"Could not cache the table of contents: {error}", file=sys.stderr)
        return {}
    except requests.RequestException as error:
        print(
            f"Could not download the table of contents: {error}",
            file=sys.stderr,
        )
        return {}
    except ValueError as error:
        print(f"Could not parse the table of contents: {error}", file=sys.stderr)
        return {}

    print(f"Found {len(stories)} story links.")
    print(stories)

    failures: list[tuple[Story, str]] = []

    gathered_stories = {}
    failed_stories = {}

    for story in stories:
        # Use the TOC title and author to check the registry without changing it.
        # Missing stories are added only after successful extraction and saving.
        if _story_exists(story.title, author):
            print(
                f"[{story.number:03d}/{len(stories):03d}] "
                f"Skipping previously registered story: {story.title}"
            )
            continue

        print(f"[{story.number:03d}/{len(stories):03d}] Processing: {story.title}")

        # Cached pages need no network throttling delay.
        uses_cached_story = (
            metadata_mode == "cached"
            and _cache_file(cache_dir, "stories", story.url, "html").is_file()
        )

        try:
            html = get_story_page(
                session,
                story.url,
                metadata_mode=metadata_mode,
                cache_dir=cache_dir,
            )
            story_id, filename, error = gather_story(
                gatherer,
                html,
                story.title,
                author,
                story.url,
                registry_checked=True,
            )
            if filename:
                gathered_stories[story_id] = filename
            if error:
                failed_stories[story_id] = error

        except (requests.RequestException, ValueError, OSError) as error:
            failures.append((story, str(error)))
            print(
                f"    Failed: {error}",
                file=sys.stderr,
            )

        if not uses_cached_story and delay > 0:
            sleep(delay)

    if failures:
        print()
        print(f"{len(failures)} stories failed:", file=sys.stderr)

        for story, error in failures:
            print(
                f"    {story.title}: {error}",
                file=sys.stderr,
            )

        return gathered_stories

    return gathered_stories


# def gather():
def gather(*, offline=False, cache_dir=False, metadata_mode="refresh"):
    """Extract the StandardEBooks collections of stories.
    ``metadata_mode="refresh"`` downloads and saves collection lists, TOCs,
    and story pages. ``metadata_mode="cached"`` reuses cached copies; missing
    story pages are downloaded and cached on demand, while missing lists and
    TOCs remain errors. ``offline=True`` is unsupported because story pages
    can still need network access.
    """
    if offline:
        raise ValueError("Offline story downloads are not supported by this gatherer")
    _check_metadata_mode(metadata_mode)
    print("Gathering StandardEBooks stories.")

    total = 0
    collection_urls = get_collection_urls(
        metadata_mode=metadata_mode,
        cache_dir=cache_dir,
    )

    for collection_url in collection_urls:
        downloads = gather_collection(
            collection_url,
            metadata_mode=metadata_mode,
            cache_dir=cache_dir,
        )
        total = total + len(downloads)

    print(f" - Total stories in StandardEBooks corpus: {total}")


# if __name__ == "__main__":
#    main()
