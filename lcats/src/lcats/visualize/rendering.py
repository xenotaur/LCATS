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

import enum
import textwrap

import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib.patches import Patch
from wordcloud import WordCloud

from lcats.analysis import graph_plotters
from lcats.visualize import comparison

DEFAULT_WORDCLOUD_SIZE = (1600, 900)


class ExtremaHighlight(str, enum.Enum):
    """Extrema-highlighting scope for N-way deviation panels."""

    OFF = "off"
    PER_GENRE = "per-genre"
    GLOBAL = "global"


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


def nway_extrema_cells(
    result: comparison.NWayComparisonResult,
    mode: ExtremaHighlight | str = ExtremaHighlight.PER_GENRE,
) -> set[tuple[str, str]]:
    """Return ``(panel_key, term)`` cells highlighted under ``mode``.

    Ties are included.  A positive or negative extreme is omitted when no cell
    of that sign exists in the applicable scope.
    """
    mode = ExtremaHighlight(mode)
    if mode == ExtremaHighlight.OFF:
        return set()
    cells = [
        (panel.panel_key, row.term, panel.deviation)
        for row in result.rows
        for panel in row.panels
    ]
    scopes = (
        {panel[0]: [cell for cell in cells if cell[0] == panel[0]] for panel in cells}
        if mode == ExtremaHighlight.PER_GENRE
        else {"global": cells}
    )
    highlighted = set()
    for scoped_cells in scopes.values():
        negatives = [cell[2] for cell in scoped_cells if cell[2] < 0]
        positives = [cell[2] for cell in scoped_cells if cell[2] > 0]
        if negatives:
            minimum = min(negatives)
            highlighted.update(
                (panel_key, term)
                for panel_key, term, deviation in scoped_cells
                if deviation == minimum
            )
        if positives:
            maximum = max(positives)
            highlighted.update(
                (panel_key, term)
                for panel_key, term, deviation in scoped_cells
                if deviation == maximum
            )
    return highlighted


def plot_nway_deviation_comparison(
    result: comparison.NWayComparisonResult,
    *,
    title: str = "Lexical frequency by genre",
    highlight: ExtremaHighlight | str = ExtremaHighlight.PER_GENRE,
    save_path: str | None = None,
    figsize: tuple | None = None,
):
    """Plot reference frequencies and N signed-deviation panels.

    The reference uses its own non-negative scale and points left.  Every
    deviation panel uses one joint symmetric scale, so bar lengths are directly
    comparable across panels.  Direction, hatching, and color redundantly encode
    the sign for readers with color-vision differences.
    """
    rows = sorted(result.rows, key=lambda row: row.display_order)
    if not rows:
        raise ValueError("N-way deviation rendering requires at least one row.")
    panel_manifest = result.manifest["panels"]
    panel_keys = [panel["key"] for panel in panel_manifest]
    panel_labels = {panel["key"]: panel["label"] for panel in panel_manifest}
    row_cells = {
        row.term: {panel.panel_key: panel for panel in row.panels} for row in rows
    }
    if any(set(row_cells[row.term]) != set(panel_keys) for row in rows):
        raise ValueError("Every N-way row must contain exactly the manifest panels.")

    highlighted = nway_extrema_cells(result, highlight)
    deviations = [
        row_cells[row.term][panel_key].deviation
        for row in rows
        for panel_key in panel_keys
    ]
    deviation_limit = max((abs(value) for value in deviations), default=0.0) or 1.0
    reference_limit = max((row.reference_value for row in rows), default=0.0) or 1.0
    positions = list(range(len(rows)))
    if figsize is None:
        figsize = (
            max(13.0, 4.2 + 1.75 * len(panel_keys)),
            max(7.0, 0.42 * len(rows) + 2.8),
        )

    fig = plt.figure(figsize=figsize, layout="constrained")
    grid = fig.add_gridspec(
        1,
        len(panel_keys) + 2,
        width_ratios=[1.25, 0.62, *([1.0] * len(panel_keys))],
        wspace=0.04,
    )
    reference_ax = fig.add_subplot(grid[0, 0])
    terms_ax = fig.add_subplot(grid[0, 1], sharey=reference_ax)
    panel_axes = [
        fig.add_subplot(grid[0, index + 2], sharey=reference_ax)
        for index in range(len(panel_keys))
    ]

    reference_ax.barh(
        positions,
        [-row.reference_value for row in rows],
        color="#D1D5DB",
        edgecolor="#475569",
        linewidth=0.8,
        height=0.68,
    )
    reference_ax.axvline(0, color="#111827", linewidth=0.9)
    reference_ax.set_xlim(-reference_limit * 1.06, 0)
    reference_ax.set_title(
        textwrap.fill(result.manifest["reference"]["label"], width=16), fontsize=10
    )
    reference_ax.set_xlabel(_metric_label(result.manifest["metric"]), fontsize=9)
    reference_ax.set_yticks(positions)
    reference_ax.tick_params(axis="y", left=False, labelleft=False)
    reference_ax.xaxis.set_major_formatter(
        ticker.FuncFormatter(lambda value, _: f"{abs(value):,.0f}")
    )
    reference_ax.grid(axis="x", linestyle=":", linewidth=0.5, color="#CBD5E1")

    terms_ax.set_xlim(0, 1)
    terms_ax.set_ylim(-0.7, len(rows) - 0.3)
    for position, row in zip(positions, rows):
        terms_ax.text(0.5, position, row.term, ha="center", va="center", fontsize=9)
    terms_ax.set_title("Word", fontsize=10)
    terms_ax.set_xticks([])
    terms_ax.set_yticks([])
    for spine in terms_ax.spines.values():
        spine.set_visible(False)

    for panel_key, axis in zip(panel_keys, panel_axes):
        values = [row_cells[row.term][panel_key].deviation for row in rows]
        colors = []
        edges = []
        hatches = []
        linewidths = []
        for row, value in zip(rows, values):
            is_highlighted = (panel_key, row.term) in highlighted
            if value < 0:
                colors.append("#B42318" if is_highlighted else "#F4B6B0")
                edges.append("#7A271A")
                hatches.append("////")
            elif value > 0:
                colors.append("#175CD3" if is_highlighted else "#A9C7E8")
                edges.append("#1849A9")
                hatches.append("...")
            else:
                colors.append("#D1D5DB")
                edges.append("#64748B")
                hatches.append("")
            linewidths.append(1.4 if is_highlighted else 0.7)
        bars = axis.barh(
            positions,
            values,
            color=colors,
            edgecolor=edges,
            linewidth=linewidths,
            height=0.68,
        )
        for bar, hatch in zip(bars, hatches):
            bar.set_hatch(hatch)
        axis.axvline(0, color="#111827", linewidth=0.9)
        axis.set_xlim(-deviation_limit * 1.06, deviation_limit * 1.06)
        axis.set_title(textwrap.fill(panel_labels[panel_key], width=14), fontsize=10)
        axis.set_xlabel("Deviation", fontsize=9)
        axis.tick_params(axis="y", left=False, labelleft=False)
        axis.xaxis.set_major_locator(ticker.MaxNLocator(nbins=3, symmetric=True))
        axis.xaxis.set_major_formatter(
            ticker.FuncFormatter(
                lambda value, _: "0" if value == 0 else f"{value:+,.0f}"
            )
        )
        axis.grid(axis="x", linestyle=":", linewidth=0.5, color="#CBD5E1")

    reference_ax.invert_yaxis()
    fig.suptitle(title, fontsize=14, fontweight="bold")
    fig.legend(
        handles=[
            Patch(
                facecolor="#D1D5DB", edgecolor="#475569", label="Reference frequency"
            ),
            Patch(
                facecolor="#F4B6B0",
                edgecolor="#7A271A",
                hatch="////",
                label="Below reference",
            ),
            Patch(
                facecolor="#A9C7E8",
                edgecolor="#1849A9",
                hatch="...",
                label="Above reference",
            ),
            Patch(
                facecolor="#B42318",
                edgecolor="#7A271A",
                label=f"Most below ({ExtremaHighlight(highlight).value})",
            ),
            Patch(
                facecolor="#175CD3",
                edgecolor="#1849A9",
                label=f"Most above ({ExtremaHighlight(highlight).value})",
            ),
        ],
        loc="outside lower center",
        ncols=5,
        frameon=False,
        fontsize=9,
    )
    if save_path:
        fig.savefig(save_path, dpi=180, bbox_inches="tight")
    return fig, {
        "reference": reference_ax,
        "terms": terms_ax,
        "panels": dict(zip(panel_keys, panel_axes)),
    }


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
