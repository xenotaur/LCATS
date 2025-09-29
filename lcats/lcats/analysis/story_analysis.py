"""Story text analysis utilities for LCATS corpus analysis."""

import ast
import re

from typing import Any, Dict, List, Tuple

import tiktoken


_WORD_RE = re.compile(r"\S+")  # simple, robust word-ish segmentation


def word_count(text: str) -> int:
    """Count words in text using a simple regex-based tokenizer."""
    return len(_WORD_RE.findall(text))


def token_count(text: str, enc: "tiktoken.Encoding") -> int:
    """Count tokens in text using the specified tiktoken encoding.
    
    Note: tiktoken expects bytes/str; do not pre-split.

    Args:
        text: Input text string.
        enc: tiktoken.Encoding instance to use for tokenization.
    Returns:
        Number of tokens in the text.
    """
    return len(enc.encode(text, disallowed_special=()))


def get_encoder() -> "tiktoken.Encoding":
    """Prefer GPT-4o-ish tokens; fallback to cl100k_base."""
    for name in ("o200k_base", "cl100k_base"):
        try:
            return tiktoken.get_encoding(name)
        except Exception:
            continue
    # As a last resort, use the default encoding for cl100k_base-compatible models
    try:
        return tiktoken.encoding_for_model("gpt-4")
    except Exception as e:
        raise RuntimeError("No suitable tiktoken encoding found.") from e


def extract_title_authors_body(data: Dict[str, Any]) -> Tuple[str, List[str], str]:
    """Extract title, authors, and body text from a story metadata dictionary.

    Handles various possible field names and formats.
    Returns (title, authors, body).

    Args:
        data: Dictionary with possible keys like 'name', 'author', 'body', etc.
    Returns:
        Tuple of (title, authors, body), where:
            title : str
            authors : List[str]
            body : str
    """
    # Title
    title = (data.get("name") or data.get("metadata", {}).get("name") or "").strip()
    if not title:
        title = "<Untitled>"

    # Authors (list of strings)
    authors = data.get("author")
    if not authors:
        authors = data.get("metadata", {}).get("author", [])
    if isinstance(authors, str):
        authors = [authors]
    authors = [a.strip() for a in (authors or []) if str(a).strip()]

    # Body
    body = data.get("body", "")
    if isinstance(body, (bytes, bytearray)):
        body = bytes(body).decode("utf-8", errors="replace")
    else:
        body = decode_possible_bytes_literal(str(body))
    return title, authors, body


def normalize_title(s: str) -> str:
    """Normalize a title string for consistent comparison."""
    return re.sub(r"\s+", " ", s).strip().lower()


def decode_possible_bytes_literal(s: str) -> str:
    """Safely decode strings that look like Python bytes literals: b'...'/b"...".

    If s looks like a bytes literal, decode it as UTF-8 with replacement for errors.
    Otherwise return the string unchanged.

    Args:
        s: Input string, possibly a bytes literal.
    Returns:
        Decoded string if input was a bytes literal, else original string.
    """
    if not isinstance(s, str):
        return str(s)
    t = s.strip()
    if len(t) >= 3 and t[0] == "b" and t[1] in ("'", '"'):
        try:
            b = ast.literal_eval(t)
            if isinstance(b, (bytes, bytearray)):
                return bytes(b).decode("utf-8", errors="replace")
        except Exception:
            pass
    return s







