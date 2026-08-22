"""Rendering functions for lcats visualize, converting analysis results to figures.

Conventional charts reuse ``lcats.analysis.graph_plotters`` (extended with
``plot_category_distribution`` for this package) rather than a parallel
Matplotlib/Seaborn plotting API. Word clouds use the ``wordcloud`` package,
which ``graph_plotters`` has no equivalent for.
"""

import matplotlib.pyplot as plt
from wordcloud import WordCloud

from lcats.analysis import graph_plotters

DEFAULT_WORDCLOUD_SIZE = (1600, 900)


def plot_genre_bar_chart(counts: dict, *, save_path: str | None = None):
    """Conventional bar chart of genre counts, via graph_plotters."""
    return graph_plotters.plot_category_distribution(
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
    """Word cloud sized by genre story count.

    Args:
        counts: Mapping of genre label to story count.
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
    ax.set_title("Genre Distribution Word Cloud")
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig, ax
