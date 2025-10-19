"""Process headers of Gutenberg texts."""

from typing import Iterable, Union

from gutenbergpy import textget


def strip_headers(text: Union[bytes, str]) -> bytes:
    """Remove Gutenberg headers/footers and return bytes of the content.

    Accepts either bytes or str (str is encoded as UTF-8 best-effort).

    Args:
        text: The text to process (either bytes or str).
    Returns: Bytes of the content.
    """
    if isinstance(text, str):
        text = text.encode("utf-8", errors="ignore")
    return textget.strip_headers(text)


def get_text_header_lines(text: Union[bytes, str]) -> Iterable[str]:
    """Yield non-blank lines from the header of a Gutenberg text (before '*** START')."""
    pre, _, _ = text.partition(b"*** START")
    for line in pre.splitlines():
        s = line.strip().decode("utf-8", errors="ignore")
        if s:
            yield s
