"""Parse canonical Gutenberg source identities without accessing the network."""

import re
import urllib.parse


_PATHS = (
    r"/ebooks/([0-9]+)(?:\.[^/]+)?/?",
    r"/files/([0-9]+)/(?:[^/]+/)*[^/]+",
    r"/cache/epub/([0-9]+)/[^/]+",
)


def ebook_id_from_url(url: str) -> int:
    """Return the ID in an official ebook, files or generated-resource URL.

    The source URL is identity, not download authority. Mirror URLs and arbitrary
    numeric paths are refused instead of assigning unrelated stories an ID.
    Nested resource directories (including HTML editions) retain the ebook ID.
    Query and fragment do not change identity. Invalid inputs raise ValueError.
    """
    if not isinstance(url, str) or not url or url != url.strip():
        raise ValueError("a Gutenberg source URL is required")
    try:
        parts = urllib.parse.urlsplit(url)
        valid = (
            parts.scheme in ("http", "https")
            and parts.hostname in ("gutenberg.org", "www.gutenberg.org")
            and parts.username is None
            and parts.password is None
            and parts.port in (None, 80 if parts.scheme == "http" else 443)
        )
    except ValueError as exc:
        raise ValueError("invalid Gutenberg source URL") from exc
    if valid:
        for pattern in _PATHS:
            match = re.fullmatch(pattern, parts.path)
            if match and 0 < int(match[1]) <= 2**63 - 1:
                return int(match[1])
    raise ValueError("unrecognized Gutenberg source URL")
