"""Story text analysis utilities for LCATS corpus analysis."""

import ast
import collections
import re

from typing import Any, Dict, List, Optional, Sequence, Tuple

import tiktoken


# TODO(centaur): reconcile with the word counter belo.
# Minimal English stopword set (extend as needed).
_STOPWORDS: frozenset = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "had", "has", "have", "he", "her", "hers", "him", "his", "i", "if", "in",
    "into", "is", "it", "its", "me", "my", "of", "on", "or", "our", "ours",
    "she", "so", "that", "the", "their", "theirs", "them", "they", "this",
    "those", "to", "too", "us", "was", "we", "were", "what", "when", "where",
    "which", "who", "whom", "why", "will", "with", "you", "your", "yours",
})

def get_keywords(text: str) -> List[str]:
    """Tokenize to lowercase alphabetic terms, length ≥ 3, excluding stopwords.

    Args:
        text: Input text.

    Returns:
        List of normalized tokens.
    """
    # Keep letters only; split on non-letters.
    raw = re.split(r"[^A-Za-z]+", text.lower())
    return [t for t in raw if len(t) >= 3 and t not in _STOPWORDS]


def top_keywords(tokens: Sequence[str], k: int = 5) -> List[Dict[str, Any]]:
    """Return top-k terms by frequency (stable, then alphabetical for ties)."""
    if not tokens:
        return []
    counts = collections.Counter(tokens)
    # Build (term, count) and sort by (-count, term) for deterministic order.
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [{"term": term, "count": count} for term, count in items[:k]]


def coerce_text(value: Any) -> str:
    """Return a best-effort string from possibly-bytes or bytes-literal text.

    Args:
        value: Input value that may be str, bytes/bytearray, or a strified
            Python bytes literal (e.g., "b'...\\x..'").

    Returns:
        Decoded text as a str (UTF-8 with replacement on errors).
    """
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace")
    if isinstance(value, str):
        text = value
        # Detect a Python bytes literal and decode if present.
        if (len(text) >= 3 and text[0] == "b" and text[1] in {"'", '"'}
                and text[-1] == text[1]):
            try:
                b = ast.literal_eval(text)  # type: ignore[arg-type]
                if isinstance(b, (bytes, bytearray)):
                    return bytes(b).decode("utf-8", errors="replace")
            except Exception:
                pass
        return text
    return str(value)


# TODO(centaur): unify with similar logic below.
def extract_authors(author_field: Any) -> List[str]:
    """Normalize author(s) to a list of strings."""
    if isinstance(author_field, list):
        return [str(a).strip() for a in author_field if str(a).strip()]
    if isinstance(author_field, str) and author_field.strip():
        return [author_field.strip()]
    return []


# TODO(centaur): reconcile with the keyword counter above.
_WORD_RE = re.compile(r"\S+")  # simple, robust word-ish segmentation


def word_count(text: str) -> int:
    """Count words in text using a simple regex-based tokenizer."""
    return len(_WORD_RE.findall(text))


def token_count(text: str, enc: Optional["tiktoken.Encoding"] = None) -> int:
    """Count tokens in text using the specified tiktoken encoding.
    
    Note: tiktoken expects bytes/str; do not pre-split.

    Args:
        text: Input text string.
        enc: tiktoken.Encoding instance to use for tokenization.
    Returns:
        Number of tokens in the text.
    """
    if enc is None:
        enc = get_encoder()
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


def count_paragraph(text: Any) -> int:
    """Count paragraphs where a paragraph break is two (or more) blank lines.

    A "blank line" is a line containing only whitespace. Runs of two or more
    consecutive blank lines are treated as paragraph separators. Single blank
    lines are preserved inside a paragraph and do not create a new paragraph.

    Args:
        text: Body text to analyze. If not a string, it will be stringified.

    Returns:
        The number of paragraphs (0 if there is no non-whitespace content).
    """
    s = str(text) if not isinstance(text, str) else text
    # Normalize line endings to '\n'.
    s = s.replace("\r\n", "\n").replace("\r", "\n")

    # Split on two or more blank lines (whitespace-only lines).
    # ^\s*\n matches a blank line; {2,} requires two or more in a row.
    splitter = re.compile(r"(?:^\s*\n){2,}", flags=re.MULTILINE)
    chunks = splitter.split(s)

    # Count non-empty chunks (ignoring pure whitespace).
    paragraphs = [c for c in chunks if c.strip()]
    return len(paragraphs)

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







