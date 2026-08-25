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
from matplotlib import ticker
from wordcloud import WordCloud

from lcats.analysis import graph_plotters
from lcats.visualize import comparison

DEFAULT_WORDCLOUD_SIZE = (1600, 900)


def _metric_label(metric: dict) -> str:
    name = metric["name"].replace("_", " ")
    denominator = metric.get("effective_denominator")
    if denominator and denominator != "none":
        return f"{name} ({denominator.replace('_', ' ')})"
    return name


def _comparison_rows(result: comparison.ComparisonResult):
    return sorted(result.rows, key=lambda row: row.display_order)


def _metric_specs_match(result: comparison.ComparisonResult) -> bool:
    return result.manifest["metrics"]["left"] == result.manifest["metrics"]["right"]


def plot_mirrored_comparison(
    result: comparison.ComparisonResult,
    *,
    title: str = "Lexical comparison",
    save_path: str | None = None,
    figsize: tuple = (10, 7),
):
    """Plot a mirrored horizontal bar chart from an aligned comparison table."""
    if not _metric_specs_match(result):
        return _plot_mirrored_comparison_independent_scales(
            result, title=title, save_path=save_path, figsize=figsize
        )

    rows = _comparison_rows(result)
    terms = [row.term for row in rows]
    positions = list(range(len(rows)))
    left_values = [-row.left_value for row in rows]
    right_values = [row.right_value for row in rows]

    fig, ax = plt.subplots(figsize=figsize)
    ax.barh(
        positions,
        left_values,
        color="#d9d9d9",
        edgecolor="black",
        hatch="//",
        label=result.manifest["left"]["label"],
    )
    ax.barh(
        positions,
        right_values,
        color="#4d4d4d",
        edgecolor="black",
        label=result.manifest["right"]["label"],
    )
    ax.axvline(0, color="black", linewidth=1)
    ax.set_yticks(positions)
    ax.set_yticklabels(terms)
    ax.invert_yaxis()

    left_metric = _metric_label(result.manifest["metrics"]["left"])
    right_metric = _metric_label(result.manifest["metrics"]["right"])
    ax.set_xlabel(f"Left: {left_metric} | Right: {right_metric}")
    ax.set_title(title)
    ax.legend(loc="best")
    ax.grid(axis="x", linestyle=":", linewidth=0.6, color="#bdbdbd")

    ax.xaxis.set_major_formatter(
        ticker.FuncFormatter(lambda value, _: f"{abs(value):g}")
    )
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig, ax


def _plot_mirrored_comparison_independent_scales(
    result: comparison.ComparisonResult,
    *,
    title: str,
    save_path: str | None,
    figsize: tuple,
):
    rows = _comparison_rows(result)
    terms = [row.term for row in rows]
    positions = list(range(len(rows)))
    left_values = [row.left_value for row in rows]
    right_values = [row.right_value for row in rows]

    fig, (left_ax, right_ax) = plt.subplots(
        ncols=2,
        sharey=True,
        figsize=figsize,
        layout="constrained",
        gridspec_kw={"wspace": 0.02},
    )
    left_ax.barh(
        positions,
        left_values,
        color="#d9d9d9",
        edgecolor="black",
        hatch="//",
        label=result.manifest["left"]["label"],
    )
    right_ax.barh(
        positions,
        right_values,
        color="#4d4d4d",
        edgecolor="black",
        label=result.manifest["right"]["label"],
    )

    left_ax.set_yticks(positions)
    left_ax.set_yticklabels(terms)
    left_ax.invert_yaxis()
    right_ax.tick_params(axis="y", left=False, labelleft=False)

    left_metric = _metric_label(result.manifest["metrics"]["left"])
    right_metric = _metric_label(result.manifest["metrics"]["right"])
    left_ax.set_xlabel(f"Left: {left_metric}")
    right_ax.set_xlabel(f"Right: {right_metric}")
    fig.suptitle(title)

    left_limit = max(left_values, default=0.0) * 1.05 or 1.0
    right_limit = max(right_values, default=0.0) * 1.05 or 1.0
    left_ax.set_xlim(left_limit, 0)
    right_ax.set_xlim(0, right_limit)
    for ax in (left_ax, right_ax):
        ax.grid(axis="x", linestyle=":", linewidth=0.6, color="#bdbdbd")

    handles = [
        left_ax.patches[0] if left_ax.patches else None,
        right_ax.patches[0] if right_ax.patches else None,
    ]
    handles = [handle for handle in handles if handle is not None]
    labels = [result.manifest["left"]["label"], result.manifest["right"]["label"]]
    if handles:
        fig.legend(handles, labels[: len(handles)], loc="upper right")

    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig, left_ax


def plot_reference_overlay_comparison(
    result: comparison.ComparisonResult,
    *,
    title: str = "Lexical comparison",
    save_path: str | None = None,
    figsize: tuple = (10, 7),
):
    """Plot a gray reference plus target/excess/deficit overlay chart."""
    _validate_overlay_result(result)
    rows = _comparison_rows(result)
    terms = [row.term for row in rows]
    positions = list(range(len(rows)))
    reference_values = [row.left_value for row in rows]
    target_values = [row.right_value for row in rows]
    overlap_values = [min(row.left_value, row.right_value) for row in rows]
    excess_values = [max(row.right_value - row.left_value, 0.0) for row in rows]
    deficit_values = [max(row.left_value - row.right_value, 0.0) for row in rows]

    fig, ax = plt.subplots(figsize=figsize)
    ax.barh(
        positions,
        reference_values,
        color="#d9d9d9",
        edgecolor="black",
        label=f"reference: {result.manifest['left']['label']}",
    )
    ax.barh(
        positions,
        overlap_values,
        height=0.46,
        color="#737373",
        edgecolor="black",
        hatch="..",
        label=f"target overlap: {result.manifest['right']['label']}",
    )
    ax.barh(
        positions,
        excess_values,
        left=overlap_values,
        height=0.46,
        color="#252525",
        edgecolor="black",
        hatch="xx",
        label="target excess",
    )
    ax.barh(
        positions,
        deficit_values,
        left=target_values,
        height=0.46,
        color="white",
        edgecolor="black",
        hatch="\\\\",
        label="target deficit",
    )
    ax.set_yticks(positions)
    ax.set_yticklabels(terms)
    ax.invert_yaxis()
    ax.set_xlabel(_metric_label(result.manifest["metrics"]["right"]))
    ax.set_title(title)
    ax.legend(loc="best")
    ax.grid(axis="x", linestyle=":", linewidth=0.6, color="#bdbdbd")
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig, ax


def _validate_overlay_result(result: comparison.ComparisonResult) -> None:
    left_metric = result.manifest["metrics"]["left"]
    right_metric = result.manifest["metrics"]["right"]
    if left_metric != right_metric:
        raise ValueError(
            "reference-overlay rendering requires identical metric and "
            "denominator provenance."
        )
    if result.manifest["preprocessing"]["term_form"] != "surface":
        raise ValueError(
            "reference-overlay rendering currently supports surface terms."
        )


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


def plot_topic_bar_chart(
    term_weights: dict, *, topic_label: str, save_path: str | None = None
):
    """Conventional bar chart of a single topic's top-weighted terms."""
    return plot_bar_chart(
        term_weights,
        title=f"Topic: {topic_label}",
        xlabel="Term",
        ylabel="Weight",
        save_path=save_path,
    )
