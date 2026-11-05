#!/usr/bin/env python3
"""
Extract subject tags from a Standard Ebooks book or collection page.

Example:
    python extract_subjects.py \
        https://standardebooks.org/ebooks/p-g-wodehouse/short-fiction

Expected output:
    comedy
    fiction
    shorts

Dependencies:
    python -m pip install requests beautifulsoup4
"""

from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


DEFAULT_URL = (
    "https://standardebooks.org/"
    "ebooks/p-g-wodehouse/short-fiction"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(compatible; StandardEbooksSubjectExtractor/1.0)"
    ),
    "Accept": (
        "application/xhtml+xml,"
        "text/html;q=0.9,"
        "application/xml;q=0.8,"
        "*/*;q=0.5"
    ),
}


def download_page(url: str, timeout: int = 30) -> str:
    """Download a Standard Ebooks page and return its HTML."""
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()

    # Standard Ebooks pages are normally UTF-8 XHTML.
    response.encoding = response.encoding or "utf-8"

    return response.text


def subject_from_url(url: str) -> str | None:
    """
    Extract the subject slug from a Standard Ebooks subject URL.

    Examples:
        /subjects/comedy  -> comedy
        /subjects/shorts/ -> shorts
    """
    parsed = urlparse(url)
    parts = [
        unquote(part)
        for part in parsed.path.strip("/").split("/")
        if part
    ]

    if len(parts) != 2:
        return None

    if parts[0].casefold() != "subjects":
        return None

    return parts[1].strip() or None


def extract_subjects(html: str, page_url: str) -> list[str]:
    """
    Extract subjects from links whose paths begin with /subjects/.

    The subjects are returned in their original page order, with duplicates
    removed.
    """
    soup = BeautifulSoup(html, "html.parser")

    subjects: list[str] = []
    seen: set[str] = set()

    for link in soup.select("a[href]"):
        href = link.get("href")

        if not isinstance(href, str):
            continue

        absolute_url = urljoin(page_url, href)
        subject_slug = subject_from_url(absolute_url)

        if subject_slug is None:
            continue

        # Prefer the visible tag label. Fall back to the URL slug.
        visible_text = link.get_text(" ", strip=True)
        subject = visible_text or subject_slug.replace("-", " ")

        subject = " ".join(subject.split()).strip()
        key = subject.casefold()

        if subject and key not in seen:
            seen.add(key)
            subjects.append(subject)

    return subjects


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract subjects from a Standard Ebooks page."
    )

    parser.add_argument(
        "url",
        nargs="?",
        default=DEFAULT_URL,
        help=f"Standard Ebooks book URL; default: {DEFAULT_URL}",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="print the results as JSON",
    )

    parser.add_argument(
        "--comma-separated",
        action="store_true",
        help="print all subjects on one comma-separated line",
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        html = download_page(arguments.url)
        subjects = extract_subjects(html, arguments.url)

    except requests.RequestException as error:
        print(f"Download failed: {error}", file=sys.stderr)
        return 1

    if not subjects:
        print(
            "No subject tags were found on the page.",
            file=sys.stderr,
        )
        return 1

    if arguments.json:
        print(
            json.dumps(
                {
                    "url": arguments.url,
                    "subjects": subjects,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    elif arguments.comma_separated:
        print(", ".join(subjects))

    else:
        for subject in subjects:
            print(subject)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
