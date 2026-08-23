"""Pure analysis functions over genre/word-frequency data, independent of rendering."""

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
