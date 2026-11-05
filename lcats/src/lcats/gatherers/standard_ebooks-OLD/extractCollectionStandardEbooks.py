#!/usr/bin/env python3
"""
Download every story listed in a Standard Ebooks table of contents.

Source:
    https://standardebooks.org/ebooks/p-g-wodehouse/short-fiction/text

Output:
    wodehouse-short-fiction/
        001 - The Man Upstairs.txt
        002 - Something to Worry About.txt
        ...
        manifest.tsv

"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import sleep
from urllib.parse import unquote, urljoin, urlparse
import argparse
import re
import sys
import unicodedata

import requests
from bs4 import BeautifulSoup, Tag


TOC_URL = (
    "https://standardebooks.org/"
    "ebooks/p-g-wodehouse/short-fiction/text"
)

USER_AGENT = (
    "Mozilla/5.0 (compatible; StandardEbooksStoryExtractor/1.0)"
)


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
    """Clean the visible title from a table-of-contents entry."""
    text = normalize_inline_text(text)

    # Remove leading numbering should the TOC display entries such as
    # "1. The Man Upstairs" or "I. The Man Upstairs".
    text = re.sub(
        r"^\s*(?:\d+|[IVXLCDM]+)[.)]\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return text.strip()


def canonicalize_url(url: str) -> str:
    """Remove fragments and trailing slashes from a URL."""
    parsed = urlparse(url)

    return parsed._replace(
        fragment="",
        query="",
        path=parsed.path.rstrip("/"),
    ).geturl()


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

    excluded_slugs = {
        "single-page",
        "colophon",
        "imprint",
        "titlepage",
        "halftitlepage",
        "uncopyright",
    }

    return relative_path.casefold() not in excluded_slugs


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
        return sum(
            len(paragraph.get_text(" ", strip=True))
            for paragraph in paragraphs
        )

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


def extract_story_text(html: str, expected_title: str) -> str:
    """Extract the readable text of an individual story page."""
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
        if element.name == "p" and element.find_parent(
            ["blockquote", "pre"]
        ):
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

    # Ensure that each output file has its TOC title. Some story pages may
    # display it in the body, while others may not.
    title_key = normalize_inline_text(expected_title).casefold()

    first_blocks = {
        normalize_inline_text(block).casefold()
        for block in deduplicated[:3]
    }

    if title_key not in first_blocks:
        deduplicated.insert(0, expected_title)

    text = "\n\n".join(deduplicated)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def safe_filename(title: str) -> str:
    """
    Convert a TOC title into a safe filename.

    The title itself is retained as closely as possible. Characters forbidden
    in Windows filenames are replaced with typographically similar or safe
    alternatives.
    """
    title = unicodedata.normalize("NFC", title)
    title = title.replace(":", " —")
    title = title.replace("/", "／")
    title = title.replace("\\", "＼")
    title = title.replace("*", "＊")
    title = title.replace("?", "？")
    title = title.replace('"', "”")
    title = title.replace("<", "‹")
    title = title.replace(">", "›")
    title = title.replace("|", "｜")

    # Remove control characters and collapse repeated spaces.
    title = "".join(
        character
        for character in title
        if unicodedata.category(character) != "Cc"
    )
    title = re.sub(r"\s+", " ", title).strip()
    title = title.rstrip(". ")

    return title or "Untitled"


def unique_output_path(
    output_directory: Path,
    story: Story,
    used_names: set[str],
    include_numbers: bool,
) -> Path:
    """Construct a unique output path for a story."""

    title = safe_filename(story.title)
    base_name = title

    candidate_name = f"{base_name}.txt"
    counter = 2

    while candidate_name.casefold() in used_names:
        candidate_name = f"{base_name} ({counter}).txt"
        counter += 1

    used_names.add(candidate_name.casefold())

    return output_directory / candidate_name


def write_manifest(
    output_directory: Path,
    records: list[tuple[Story, Path]],
) -> None:
    """Write a TSV manifest connecting titles, URLs, and files."""
    manifest_path = output_directory / "manifest.tsv"

    lines = ["number\ttitle\turl\tfilename"]

    for story, path in records:
        title = story.title.replace("\t", " ").replace("\n", " ")
        lines.append(
            f"{story.number}\t{title}\t{story.url}\t{path.name}"
        )

    manifest_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )




def extract_all_stories(toc_url, delay=1):
    """Download and extract the collection."""

    author_last_name = toc_url.split("/")[5].split("-")[-1]
    
    session = make_session()

    try:
        print(f"Downloading table of contents: {toc_url}")
        toc_html = download_page(session, toc_url)
        stories = extract_story_links(toc_html, toc_url)
    except requests.RequestException as error:
        print(
            f"Could not download the table of contents: {error}",
            file=sys.stderr,
        )
        return 1
    except ValueError as error:
        print(f"Could not parse the table of contents: {error}", file=sys.stderr)
        return 1

    print(f"Found {len(stories)} story links.")

    failures: list[tuple[Story, str]] = []
    used_names: set[str] = set()

    for story in stories:
        print(
            f"[{story.number:03d}/{len(stories):03d}] "
            f"Downloading: {story.title}"
        )

        try:
            html = download_page(session, story.url)
            text = extract_story_text(html, story.title)

            # We have the author and the text, can save a proper json

            
        except (requests.RequestException, ValueError, OSError) as error:
            failures.append((story, str(error)))
            print(
                f"    Failed: {error}",
                file=sys.stderr,
            )

        sleep(delay)
            
    if failures:
        print()
        print(f"{len(failures)} stories failed:", file=sys.stderr)

        for story, error in failures:
            print(
                f"    {story.title}: {error}",
                file=sys.stderr,
            )

        return 1

    return 0


