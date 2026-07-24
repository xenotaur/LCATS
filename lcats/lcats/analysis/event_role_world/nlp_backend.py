"""NLPBackend Protocol and implementations for surface-feature extraction.

Mirrors lcats.llm.backend.LLMBackend: a structural Protocol lets callers
swap the underlying NLP toolkit (spaCy, Stanza, ...) without touching
extractor or pipeline code. Both spaCy and Stanza converge on token-level
fields defined by the Universal Dependencies / CoNLL-U schema (UPOS, XPOS,
FEATS, HEAD, DEPREL) even though their native object shapes differ, so a
single normalized token record is sufficient to represent either.
"""

from __future__ import annotations

import dataclasses

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@dataclasses.dataclass
class TokenRecord:
    """One normalized token, aligned with the CoNLL-U column set.

    Attributes:
        text: Surface form.
        lemma: Dictionary form.
        upos: Universal part-of-speech tag (e.g. "NOUN").
        xpos: Fine-grained/treebank-specific POS tag, if available.
        feats: Morphological features as a UD-style string
            (e.g. "Number=Sing|Person=3"), empty string if none.
        head_index: 1-based index of the syntactic head word within the
            sentence, or 0 for root. Normalizes spaCy's object-reference
            `Token.head` and Stanza's integer `Word.head` to the same shape.
        deprel: Universal dependency relation to the head.
    """

    text: str
    lemma: str
    upos: str
    xpos: str
    feats: str
    head_index: int
    deprel: str

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class SentenceRecord:
    """One sentence's worth of normalized tokens."""

    tokens: List[TokenRecord]


@runtime_checkable
class NLPBackend(Protocol):
    """Structural protocol for a surface-feature (syntax/morphology) backend.

    Implementations adapt a specific NLP toolkit to this normalized call
    shape so callers can switch toolkits by swapping the backend instance,
    without touching extractor or schema code.
    """

    def analyze(self, text: str) -> List[SentenceRecord]:
        """Tokenize, tag, and parse `text`.

        Args:
            text: Segment text to analyze.

        Returns:
            A list of SentenceRecord, one per detected sentence.
        """
        ...


class StanzaBackend:
    """NLPBackend implementation backed by Stanford's Stanza toolkit."""

    def __init__(
        self, lang: str = "en", processors: str = "tokenize,pos,lemma,depparse"
    ):
        """Construct a Stanza-backed NLPBackend.

        Args:
            lang: Stanza language code.
            processors: Comma-separated Stanza processor list.

        Raises:
            ImportError: If the `stanza` package is not installed.
            Exception: If the requested language model has not been
                downloaded (`stanza.download(lang)`).
        """
        import stanza

        self._pipeline = stanza.Pipeline(
            lang=lang, processors=processors, download_method=None
        )

    def analyze(self, text: str) -> List[SentenceRecord]:
        """See NLPBackend.analyze."""
        doc = self._pipeline(text)
        sentences: List[SentenceRecord] = []
        for sentence in doc.sentences:
            tokens = [
                TokenRecord(
                    text=word.text,
                    lemma=word.lemma or "",
                    upos=word.upos or "",
                    xpos=word.xpos or "",
                    feats=word.feats or "",
                    head_index=word.head or 0,
                    deprel=word.deprel or "",
                )
                for word in sentence.words
            ]
            sentences.append(SentenceRecord(tokens=tokens))
        return sentences


class SpacyBackend:
    """NLPBackend implementation backed by spaCy."""

    def __init__(self, model_name: str = "en_core_web_sm"):
        """Construct a spaCy-backed NLPBackend.

        Args:
            model_name: Name of an installed spaCy pipeline package.

        Raises:
            ImportError: If the `spacy` package is not installed.
            OSError: If `model_name` has not been downloaded
                (`python -m spacy download <model_name>`).
        """
        import spacy

        self._nlp = spacy.load(model_name)

    def analyze(self, text: str) -> List[SentenceRecord]:
        """See NLPBackend.analyze."""
        doc = self._nlp(text)
        sentences: List[SentenceRecord] = []
        for sent in doc.sents:
            # spaCy's Token.head is an object reference; head_index is the
            # head's 1-based position within the sentence (0 = root), to
            # match Stanza's integer-index convention.
            sent_tokens = list(sent)
            index_in_sent = {tok.i: pos + 1 for pos, tok in enumerate(sent_tokens)}
            tokens = [
                TokenRecord(
                    text=tok.text,
                    lemma=tok.lemma_,
                    upos=tok.pos_,
                    xpos=tok.tag_,
                    feats=str(tok.morph),
                    head_index=(
                        0 if tok.head.i == tok.i else index_in_sent.get(tok.head.i, 0)
                    ),
                    deprel=tok.dep_,
                )
                for tok in sent_tokens
            ]
            sentences.append(SentenceRecord(tokens=tokens))
        return sentences


class FakeNLPBackend:
    """Deterministic NLPBackend test double.

    Records every call in `self.calls` and always returns a fixed set of
    SentenceRecord built from the constructor arguments.
    """

    def __init__(self, sentences: Optional[List[SentenceRecord]] = None):
        self.sentences = sentences if sentences is not None else []
        self.calls: List[str] = []

    def analyze(self, text: str) -> List[SentenceRecord]:
        """Record the call and return the fixed sentences."""
        self.calls.append(text)
        return self.sentences
