"""Pure analysis functions over genre/word-frequency data, independent of rendering."""

import numpy as np
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer

from lcats.analysis import story_analysis
from lcats.visualize import comparison

DEFAULT_N_TOPICS = 8


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


def tfidf_top_terms(
    corpus_texts: list, group_indices: list, top_k: int = 20, contrast: bool = False
) -> dict:
    """Rank terms by TF-IDF score within a story-index subset.

    ``corpus_texts`` is the full document set the IDF is fit against, and
    *story* is the document unit -- each element is one story's text.
    ``group_indices`` selects which of those documents form the comparison
    group; passing every index (the whole corpus) is a valid degenerate case
    for the default mode -- a corpus-wide ranking rather than a
    subset-vs-background comparison.

    Uses scikit-learn's ``TfidfVectorizer`` for the TF-IDF computation
    itself, with ``story_analysis.get_keywords`` as its tokenizer -- the
    same lowercase/alphabetic/minimum-length-3/stopword-filtered preprocessing
    ``word_frequencies`` above uses, so preprocessing defaults stay
    consistent across the `words`/`tfidf` commands rather than diverging.

    Two modes, selected by ``contrast``:

    - ``contrast=False`` (default, unchanged since this function's original
      delivery): ranks terms by the selected group's own mean TF-IDF only
      (``matrix[group_indices].mean(axis=0)``) -- a within-group *salience*
      measure. It never looks at documents outside ``group_indices``, so a
      term common everywhere in the corpus can still rank highly here simply
      because it is also common within the group.
    - ``contrast=True``: ranks terms by ``group_mean - complement_mean``,
      where ``complement_mean`` is the mean TF-IDF over every document *not*
      in ``group_indices`` (all computed over the same corpus-wide-fit
      matrix). This is a genuine group-vs-background comparison: a term
      common only within the group scores highly, a term equally common in
      both scores near zero, and a term more common in the complement scores
      negatively (and is filtered out, per the ``> 0`` cutoff below, the
      same as any other non-positive score). This is a simple mean-difference
      baseline, not a statistical significance test -- log-odds/chi-square-
      style weighting is deliberately deferred. Calling with an empty
      complement (``group_indices`` covering every document) returns ``{}``,
      since there is nothing to contrast against.

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
    group_set = set(group_indices)
    if contrast:
        complement_indices = [i for i in range(matrix.shape[0]) if i not in group_set]
        if not complement_indices:
            return {}
        group_mean = np.asarray(matrix[group_indices].mean(axis=0)).ravel()
        complement_mean = np.asarray(matrix[complement_indices].mean(axis=0)).ravel()
        scores = group_mean - complement_mean
    else:
        scores = np.asarray(matrix[group_indices].mean(axis=0)).ravel()
    ranked = sorted(
        ((terms[i], float(scores[i])) for i in range(len(terms)) if scores[i] > 0),
        key=lambda term_score: (-term_score[1], term_score[0]),
    )[:top_k]
    return dict(ranked)


DEFAULT_NMF_MAX_ITER = 400
DEFAULT_NMF_INIT = "nndsvda"
NMF_INIT_CHOICES = ("nndsvd", "nndsvda", "nndsvdar", "random")


def topic_model(
    corpus_texts: list,
    n_topics: int = DEFAULT_N_TOPICS,
    top_k: int = 10,
    seed: int = 42,
    max_iter: int = DEFAULT_NMF_MAX_ITER,
    init: str = DEFAULT_NMF_INIT,
) -> dict:
    """Fit a classical NMF topic-model baseline and return top terms per topic.

    A classical baseline, not a final technique choice: embedding-based
    topic models (e.g. BERTopic) are explicitly deferred per
    ``PROP-LCATS-CORPUS-TEXT-VISUALIZATION`` until a concrete paper need
    and evaluation criteria exist.

    Uses the same ``TfidfVectorizer`` + ``story_analysis.get_keywords``
    tokenizer as ``tfidf_top_terms`` for input features, then decomposes
    via scikit-learn's ``NMF``. ``init`` selects the initialization
    strategy (``nndsvda`` by default) and is an explicit, documented
    parameter -- not hardcoded. ``random_state=seed`` genuinely affects
    every ``init`` choice here, including ``nndsvd*``: scikit-learn's
    NNDSVD-family initializers compute their starting point via a
    *randomized* SVD seeded by ``random_state``, so changing ``seed`` can
    change the initial factorization and the resulting topics even under
    ``nndsvda`` -- confirmed empirically (two runs of this function with
    different seeds on the same corpus produced different topic-term
    assignments). Earlier revisions of this docstring incorrectly
    described ``nndsvda`` as having "no randomness in initialization";
    that was wrong and has been corrected here.

    Returns ``{"topic_0": {term: weight, ...}, "topic_1": {...}, ...}``,
    one entry per fitted topic in index order, each inner mapping ranked
    by weight descending with a deterministic ``(-weight, term)``
    tie-break and limited to ``top_k`` terms. Returns ``{}`` for an empty
    corpus, an empty tokenized vocabulary, or when no topic can be fit
    (fewer documents or terms than requested topics after clamping).
    """
    if not corpus_texts:
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

    n_topics_actual = min(n_topics, matrix.shape[0], matrix.shape[1])
    if n_topics_actual < 1:
        return {}

    model = NMF(
        n_components=n_topics_actual,
        init=init,
        random_state=seed,
        max_iter=max_iter,
    )
    model.fit(matrix)

    topics = {}
    for topic_idx, component in enumerate(model.components_):
        ranked = sorted(
            (
                (terms[i], float(component[i]))
                for i in range(len(terms))
                if component[i] > 0
            ),
            key=lambda term_weight: (-term_weight[1], term_weight[0]),
        )[:top_k]
        topics[f"topic_{topic_idx}"] = dict(ranked)
    return topics


def compare_lexical(
    corpus: comparison.ComparisonCorpus,
    spec: comparison.ComparisonSpec,
) -> comparison.ComparisonResult:
    """Return an authoritative aligned lexical comparison table.

    This keeps the analysis-module entry point stable while the comparison
    contract itself lives in ``lcats.visualize.comparison``.
    """
    return comparison.compare(corpus, spec)
