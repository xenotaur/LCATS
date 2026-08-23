"""Rendering functions for lcats visualize, converting analysis results to figures.

Conventional charts reuse ``lcats.analysis.graph_plotters`` (extended with
``plot_category_distribution`` for this package) rather than a parallel
Matplotlib/Seaborn plotting API. Word clouds use the ``wordcloud`` package,
which ``graph_plotters`` has no equivalent for.

Genre-specific and word-frequency-specific plotting functions are thin
wrappers around shared ``plot_wordcloud``/``plot_bar_chart`` primitives, so
adding a new visualization target never requires a new rendering primitive
-- only a new title/label wrapper.
"""

import matplotlib.pyplot as plt
from wordcloud import WordCloud

from lcats.analysis import graph_plotters

DEFAULT_WORDCLOUD_SIZE = (1600, 900)


def plot_bar_chart(
    counts: dict,
    *,
    title: str = "Distribution",
    xlabel: str = "Category",
    ylabel: str = "Count",
    save_path: str | None = None,
):
    """Conventional bar chart of a category -> count mapping, via graph_plotters."""
    return graph_plotters.plot_category_distribution(
        counts,
        title=title,
        xlabel=xlabel,
        ylabel=ylabel,
        save_path=save_path,
    )


def plot_wordcloud(
    counts: dict,
    *,
    title: str = "Word Cloud",
    seed: int = 42,
    figsize: tuple = (10, 6),
    save_path: str | None = None,
):
    """Word cloud sized by a category -> count mapping.

    Args:
        counts: Mapping of label to count.
        title: Chart title.
        seed: Deterministic random seed for word-cloud layout.
        figsize: Matplotlib figure size.
        save_path: If provided, saves the figure to this path.

    Returns:
        (fig, ax)
    """
    width, height = DEFAULT_WORDCLOUD_SIZE
    cloud = WordCloud(
        width=width,
        height=height,
        background_color="white",
        random_state=seed,
    ).generate_from_frequencies(counts)

    fig, ax = plt.subplots(figsize=figsize)
    ax.imshow(cloud, interpolation="bilinear")
    ax.axis("off")
    ax.set_title(title)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig, ax


def plot_genre_bar_chart(counts: dict, *, save_path: str | None = None):
    """Conventional bar chart of genre counts."""
    return plot_bar_chart(
        counts,
        title="Genre Distribution",
        xlabel="Genre",
        ylabel="Story count",
        save_path=save_path,
    )


def plot_genre_wordcloud(
    counts: dict,
    *,
    seed: int = 42,
    figsize: tuple = (10, 6),
    save_path: str | None = None,
):
    """Word cloud sized by genre story count."""
    return plot_wordcloud(
        counts,
        title="Genre Distribution Word Cloud",
        seed=seed,
        figsize=figsize,
        save_path=save_path,
    )


def plot_word_frequency_bar_chart(counts: dict, *, save_path: str | None = None):
    """Conventional bar chart of word frequencies."""
    return plot_bar_chart(
        counts,
        title="Word Frequency",
        xlabel="Word",
        ylabel="Frequency",
        save_path=save_path,
    )


def plot_word_frequency_wordcloud(
    counts: dict,
    *,
    seed: int = 42,
    figsize: tuple = (10, 6),
    save_path: str | None = None,
):
    """Word cloud sized by word frequency."""
    return plot_wordcloud(
        counts,
        title="Word Frequency Word Cloud",
        seed=seed,
        figsize=figsize,
        save_path=save_path,
    )


def plot_tfidf_bar_chart(scores: dict, *, save_path: str | None = None):
    """Conventional bar chart of top-ranked TF-IDF terms."""
    return plot_bar_chart(
        scores,
        title="TF-IDF Top Terms",
        xlabel="Term",
        ylabel="Mean TF-IDF score",
        save_path=save_path,
    )
