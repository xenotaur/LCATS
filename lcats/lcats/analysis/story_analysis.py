"""Story text analysis utilities for LCATS corpus analysis."""

import ast
import collections
import re

from typing import Any, Dict, List, Optional, Sequence, Tuple

from lcats.analysis import llm_extractor

import tiktoken


# TODO(centaur): reconcile with the word counter belo.
# Minimal English stopword set (extend as needed).
_STOPWORDS: frozenset = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "her",
        "hers",
        "him",
        "his",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "me",
        "my",
        "of",
        "on",
        "or",
        "our",
        "ours",
        "she",
        "so",
        "that",
        "the",
        "their",
        "theirs",
        "them",
        "they",
        "this",
        "those",
        "to",
        "too",
        "us",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "whom",
        "why",
        "will",
        "with",
        "you",
        "your",
        "yours",
    }
)


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
        if (
            len(text) >= 3
            and text[0] == "b"
            and text[1] in {"'", '"'}
            and text[-1] == text[1]
        ):
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


DOC_CLASSIFY_SYSTEM_PROMPT = """
You are a careful document diagnostician. Given a single narrative text,
you must assess: integrity, completeness, primary type, series relation,
and genre. Use ONLY the provided text. Output JSON ONLY.

DEFINITIONS & DECISION RULES
----------------------------

Integrity (intact | corrupted)
- corrupted: strong evidence of encoding/OCR damage or file breakage:
  • mojibake (e.g., �, â€™, Ã, â€”), control chars beyond \\n/\\t,
  • pervasive OCR artifacts: co-\\noperation hyphen breaks, ﬁ/ﬂ ligatures,
    0/O/1/l swaps, mid-word newlines across lines,
  • truncation markers: [TRUNCATED], <<cut>>, partial trailers,
  • glyph/table junk; broken paragraphing on long texts.
- intact: normal letters/whitespace/punctuation; sentences/paragraphs parse.

Completeness (complete | missing_start | missing_end | missing_middle | unknown)
- missing_start: opens mid-sentence/word; references earlier content not present;
  early chapter number not “1”; opens with “…” cut-in.
- missing_end: ends mid-sentence/word; dangling dialogue/emdash; final header
  without content; explicit cut markers.
- missing_middle: large numbering jump or abrupt discontinuity without bridge;
  duplicated blocks implying an omitted chunk.
- complete: plausible opening, coherent middle, and closure (ending cue or
  narrative resolution).

Type (primary content type)
- fiction: prose narrative with invented events, characters, scenes, dialogue.
- poetry: dominant verse with deliberate line breaks/stanzas; pervasive enjambment.
- nonfiction: expository/informational prose (essays, memoir, history,
  journalism, academic writing with sections/citations/data).
- drama: play/screenplay format: CHARACTER: lines, stage directions
  (e.g., [Aside], (Exit)), acts/scenes, or screenplay cues (INT./EXT., CUT TO:).
- mixed: substantial interleaving of ≥2 types with no clear majority.
- paratext: file is predominantly paratext (license, ToC, transcriber/publisher
  notes, advertisements/catalogs). If a dominant main type exists, classify by
  that type and note paratext in evidence; use paratext only when paratext
  dominates or is the only content.
- other: true fallback when none of the above fit (e.g., dictionary, code dump).

Tie-breakers:
- Prose with occasional embedded verse → fiction (note poetry presence).
- Anthology of short stories → fiction; set series="collection".
- A play with long preface → drama (note paratext presence).
- If two clear types with no dominance → mixed.
- If only ToC/license/notes → paratext.

Series (standalone | series_entry | collection | unknown)
- series_entry: explicit numbering (“Book II”, “Vol. 3”, “Part of …”), or clear
  reliance on recurring setting/characters assumed known (episodic cases).
- standalone: self-contained; introduces premise/characters; no numbering.
- collection: anthology of discrete pieces (stories/poems/essays) with separate
  titles.
- unknown: no signal.

Genre / Domain
- Fiction genres: fantasy, science fiction, mystery/detective, thriller, horror,
  romance, historical, adventure, literary, western, satire, children’s, etc.
  Base on concrete cues (magic/secondary worlds; advanced tech/space/time;
  investigation + clues; sustained peril; supernatural dread; courtship/HEA;
  period detail; etc.).
- Nonfiction domains: memoir, biography, history, science, travel, journalism,
  philosophy, essay collection, etc.
- If unclear: "unknown" with a brief reason.

EVIDENCE & CONFIDENCE
- Use short, concrete quotes/phrases (≤120 chars each) for evidence lists.
- Provide confidence ∈ [0,1] for each dimension.
- Consider paratext for integrity; ignore paratext when deciding type/genre
  unless the entire file is paratext.
- Use only the provided text; do not rely on external knowledge.

OUTPUT SHAPE (JSON ONLY)
Return exactly:
{
  "classification": {
    "integrity": "intact | corrupted",
    "integrity_evidence": ["..."],
    "completeness": "complete | missing_start | missing_end | missing_middle | unknown",
    "completeness_evidence": ["..."],
    "type": "fiction | poetry | nonfiction | drama | mixed | paratext | other",
    "type_evidence": ["..."],
    "series": "standalone | series_entry | collection | unknown",
    "series_title": "",
    "series_evidence": ["..."],
    "genre_primary": "fantasy | science fiction | ... | unknown",
    "genre_secondary": "",
    "genre_evidence": ["..."],
    "confidence": {
      "integrity": 0.0,
      "completeness": 0.0,
      "type": 0.0,
      "series": 0.0,
      "genre": 0.0
    }
  }
}
"""

DOC_CLASSIFY_USER_PROMPT_TEMPLATE = """
You will receive a STORY. Read ONLY the text and produce the JSON object
described in the system instructions under the single key "classification".

Procedure (internally):
1) Skim for obvious encoding/OCR issues; decide integrity (with evidence).
2) Mentally set aside paratext; assess completeness of the main narrative.
3) Decide the primary type (fiction/poetry/nonfiction/drama/mixed/paratext/other).
4) Determine whether it is standalone, a series entry, a collection, or unknown,
   and capture any series title if stated.
5) Assign a best-fit genre (or domain for nonfiction); allow a secondary label
   only if it’s clearly warranted.
6) Fill all fields, include brief evidence lists and per-dimension confidences.
7) Output JSON ONLY, no commentary.

STORY:
\"\"\"{story_text}\"\"\"
"""


def make_doc_classification_extractor(client: Any) -> llm_extractor.JSONPromptExtractor:
    """Create a JSONPromptExtractor for whole-text document classification.

    Args:
        client: OpenAI-like client (e.g., openai.OpenAI()).

    Returns:
        Configured JSONPromptExtractor that emits a dict under key "classification".
    """
    return llm_extractor.JSONPromptExtractor(
        client,
        system_prompt=DOC_CLASSIFY_SYSTEM_PROMPT,
        user_prompt_template=DOC_CLASSIFY_USER_PROMPT_TEMPLATE,  # uses {story_text}
        output_key="classification",
        default_model="gpt-4o",
        temperature=0.1,
        force_json=True,
        text_indexer=None,  # not needed for whole-text classification
        result_aligner=None,  # no offsets to align
    )
