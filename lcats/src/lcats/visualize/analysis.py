"""Pure analysis functions over genre/word-frequency data, independent of rendering."""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from lcats.analysis import story_analysis


def sorted_counts(counts: dict) -> list[tuple[str, int]]:
    """Return (label, count) pairs sorted by count descending, then label."""
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def counts_with_no_signal(counts: dict, no_usable_signal_count: int) -> dict:
    """Return a copy of counts with an explicit "no usable signal" category."""
    result = dict(counts)
    if no_usable_signal_count:
        result["no usable signal"] = no_usable_signal_count
    return result


def total_count(counts: dict) -> int:
    """Sum every count in the mapping."""
    return sum(counts.values())


def word_frequencies(texts: list, top_k: int = 50) -> dict:
    """Return the top-k word frequencies across a list of story texts.

    Reuses ``lcats.analysis.story_analysis.get_keywords`` (tokenize to
    lowercase alphabetic terms, length >= 3, excluding stopwords) and
    ``top_keywords`` (deterministic frequency ranking) rather than
    reimplementing tokenization.
    """
    tokens = []
    for text in texts:
        tokens.extend(story_analysis.get_keywords(text))
    ranked = story_analysis.top_keywords(tokens, k=top_k)
    return {item["term"]: item["count"] for item in ranked}


def tfidf_top_terms(corpus_texts: list, group_indices: list, top_k: int = 20) -> dict:
    """Rank terms by mean TF-IDF score within a story-index subset.

    ``corpus_texts`` is the full document set the IDF is fit against, and
    *story* is the document unit -- each element is one story's text.
    ``group_indices`` selects which of those documents form the comparison
    group whose mean TF-IDF is ranked; passing every index (the whole
    corpus) is a valid degenerate case -- a corpus-wide ranking rather than
    a subset-vs-background comparison.

    Uses scikit-learn's ``TfidfVectorizer`` for the TF-IDF computation
    itself, with ``story_analysis.get_keywords`` as its tokenizer -- the
    same lowercase/alphabetic/minimum-length-3/stopword-filtered preprocessing
    ``word_frequencies`` above uses, so preprocessing defaults stay
    consistent across the `words`/`tfidf` commands rather than diverging.

    Returns an empty mapping (not a raised exception) when ``corpus_texts``
    tokenizes to an empty vocabulary -- e.g. every document is only
    stopwords/short tokens -- translating ``TfidfVectorizer``'s own raw
    ``ValueError: empty vocabulary`` into the same "nothing to rank" result
    an empty ``corpus_texts``/``group_indices`` input already produces, so
    callers have one uniform empty-result signal to handle rather than two.
    """
    if not corpus_texts or not group_indices:
        return {}
    vectorizer = TfidfVectorizer(
        tokenizer=story_analysis.get_keywords,
        preprocessor=lambda text: text,
        token_pattern=None,
    )
    try:
        matrix = vectorizer.fit_transform(corpus_texts)
    except ValueError as exc:
        if "empty vocabulary" in str(exc):
            return {}
        raise
    terms = vectorizer.get_feature_names_out()
    mean_scores = np.asarray(matrix[group_indices].mean(axis=0)).ravel()
    ranked = sorted(
        (
            (terms[i], float(mean_scores[i]))
            for i in range(len(terms))
            if mean_scores[i] > 0
        ),
        key=lambda term_score: (-term_score[1], term_score[0]),
    )[:top_k]
    return dict(ranked)
