"""Stage 2: surface-feature (lexical, syntactic, morphological) extraction.

Consumes an NLPBackend (see nlp_backend.py) — never imports spaCy or Stanza
directly, so the underlying toolkit is swappable without touching this file.
"""

from __future__ import annotations

from lcats.analysis.event_role_world import nlp_backend as nlp_backend_module
from lcats.analysis.event_role_world import schema


def extract_surface_features(
    text: str,
    backend: nlp_backend_module.NLPBackend,
    backend_name: str = "",
) -> schema.SurfaceFeatures:
    """Run one NLPBackend pass and summarize lexical/syntactic features.

    Args:
        text: Segment text to analyze.
        backend: An NLPBackend satisfying nlp_backend.NLPBackend.
        backend_name: Label recorded on the result (e.g. "stanza", "spacy").

    Returns:
        A populated SurfaceFeatures instance. On empty input, counts are
        zero and `tokens` is an empty list.
    """
    sentences = backend.analyze(text) if text.strip() else []

    all_tokens = [tok for sent in sentences for tok in sent.tokens]
    word_count = len(all_tokens)
    sentence_count = len(sentences)
    avg_sentence_length = word_count / sentence_count if sentence_count else 0.0
    total_word_chars = sum(len(tok.text) for tok in all_tokens)
    avg_word_length = total_word_chars / word_count if word_count else 0.0

    return schema.SurfaceFeatures(
        word_count=word_count,
        sentence_count=sentence_count,
        avg_sentence_length=avg_sentence_length,
        avg_word_length=avg_word_length,
        tokens=[tok.to_dict() for tok in all_tokens],
        backend_name=backend_name,
    )


def make_nlp_backend(name: str) -> nlp_backend_module.NLPBackend:
    """Construct an NLPBackend by name.

    Args:
        name: One of "stanza", "spacy".

    Returns:
        A constructed NLPBackend instance.

    Raises:
        ValueError: If `name` is not a recognized backend.
    """
    if name == "stanza":
        return nlp_backend_module.StanzaBackend()
    if name == "spacy":
        return nlp_backend_module.SpacyBackend()
    raise ValueError(f"Unknown NLP backend name: {name!r}")
