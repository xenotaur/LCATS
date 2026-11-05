#!/usr/bin/env python3
"""
Return all collection URLs from a paginated Standard Ebooks subject page.

Install:
    python -m pip install requests beautifulsoup4
"""

from __future__ import annotations

import time
from urllib.parse import (
    parse_qs,
    urlencode,
    urljoin,
    urlparse,
    urlunparse,
)

import requests
from bs4 import BeautifulSoup


DEFAULT_URL = (
    "https://standardebooks.org/subjects/shorts"
    "?per-page=48&view=list"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(compatible; StandardEbooksCollectionExtractor/1.0)"
    )
}




if __name__ == "__main__":
    collection_urls = get_collection_urls()

    # collection_urls is now a list of strings.
    # Use it elsewhere in your program as needed.
