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

import dataclasses
import enum
import textwrap
from typing import Mapping

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


def _unsigned_tick_label(value: float) -> str:
    """Format magnitudes without rounding valid fractional metrics to zero."""
    magnitude = abs(value)
    if magnitude >= 100:
        return f"{magnitude:,.0f}"
    if magnitude >= 1:
        return f"{magnitude:,.2f}".rstrip("0").rstrip(".")
    if magnitude >= 0.01:
        return f"{magnitude:.3f}".rstrip("0").rstrip(".")
    return f"{magnitude:.3g}"


def _compact_tick_label(value: float, *, signed: bool) -> str:
    """Format N-way panel ticks compactly so narrow panels stay legible."""
    magnitude = abs(value)
    if magnitude >= 1000:
        text = f"{magnitude / 1000:.1f}".rstrip("0").rstrip(".") + "k"
    else:
        text = _unsigned_tick_label(magnitude)
    if not signed or value == 0:
        return "0" if value == 0 else text
    return f"{'+' if value > 0 else '-'}{text}"


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


class NWayLayoutPreset(str, enum.Enum):
    """Named N-way presentation presets.

    ``KABOB`` is the working name for the compact reference-deviation layout:
    reference bars point right, term labels sit on the outside right edge, and
    horizontal row guides skewer each term across every panel.
    """

    STANDARD = "standard"
    KABOB = "kabob"


class ReferenceDirection(str, enum.Enum):
    """Direction in which common-reference bars extend from zero."""

    LEFT = "left"
    RIGHT = "right"


class TermLabelPlacement(str, enum.Enum):
    """Where aligned term labels are drawn in each layout band."""

    CENTER_COLUMN = "center-column"
    OUTSIDE_LEFT = "outside-left"
    OUTSIDE_RIGHT = "outside-right"


class ScalePolicy(str, enum.Enum):
    """Panel x-scale policy; ``SHARED`` keeps bar lengths comparable."""

    SHARED = "shared"
    INDEPENDENT = "independent"


DEFAULT_NWAY_MAX_COLUMNS = 8
_NWAY_AXIS_PADDING = 1.06


@dataclasses.dataclass(frozen=True)
class NWayRenderSpec:
    """Rendering choices for an N-way reference-deviation chart.

    Every field is an independent choice; ``preset`` only records which named
    preset (if any) the other fields were derived from.  Use
    ``NWayRenderSpec.from_preset`` to start from a preset and override fields.
    Defaults reproduce the original standard layout.
    """

    preset: NWayLayoutPreset = NWayLayoutPreset.STANDARD
    reference_direction: ReferenceDirection = ReferenceDirection.LEFT
    term_labels: TermLabelPlacement = TermLabelPlacement.CENTER_COLUMN
    hatching: bool = True
    legend: bool = True
    row_guides: bool = False
    highlight: ExtremaHighlight = ExtremaHighlight.PER_GENRE
    scale: ScalePolicy = ScalePolicy.SHARED
    max_columns: int = DEFAULT_NWAY_MAX_COLUMNS

    def __post_init__(self) -> None:
        object.__setattr__(self, "preset", NWayLayoutPreset(self.preset))
        object.__setattr__(
            self, "reference_direction", ReferenceDirection(self.reference_direction)
        )
        object.__setattr__(self, "term_labels", TermLabelPlacement(self.term_labels))
        object.__setattr__(self, "highlight", ExtremaHighlight(self.highlight))
        object.__setattr__(self, "scale", ScalePolicy(self.scale))
        if isinstance(self.max_columns, bool) or not isinstance(self.max_columns, int):
            raise ValueError("max_columns must be an integer.")
        if self.max_columns < 1:
            raise ValueError(f"max_columns must be >= 1, got {self.max_columns}.")

    @classmethod
    def from_preset(
        cls, preset: NWayLayoutPreset | str = NWayLayoutPreset.STANDARD, **overrides
    ) -> "NWayRenderSpec":
        """Return the preset's field values with any explicit overrides applied."""
        preset = NWayLayoutPreset(preset)
        fields = {"preset": preset, **_NWAY_PRESET_FIELDS[preset]}
        fields.update(overrides)
        return cls(**fields)

    def to_dict(self) -> dict:
        """Serialize the spec with enum values for manifests."""
        return {
            field.name: (
                getattr(self, field.name).value
                if isinstance(getattr(self, field.name), enum.Enum)
                else getattr(self, field.name)
            )
            for field in dataclasses.fields(self)
        }


_NWAY_PRESET_FIELDS = {
    NWayLayoutPreset.STANDARD: {},
    NWayLayoutPreset.KABOB: {
        "reference_direction": ReferenceDirection.RIGHT,
        "term_labels": TermLabelPlacement.OUTSIDE_RIGHT,
        "row_guides": True,
    },
}


@dataclasses.dataclass(frozen=True)
class NWayRenderPlan:
    """Deterministic, renderer-independent layout and scale decisions.

    The plan is computed before drawing so the figure, CSV, and manifest all
    report the same bands, axis limits, and highlighted cells.
    """

    spec: NWayRenderSpec
    reference_policy: str
    plotted_quantity: str
    terms: tuple[str, ...]
    panel_keys: tuple[str, ...]
    panel_labels: Mapping[str, str]
    bands: tuple[tuple[str, ...], ...]
    panel_limits: Mapping[str, tuple[float, float]]
    panel_absolute_limits: Mapping[str, float]
    reference_limit: float | None
    highlighted: frozenset

    @property
    def has_common_reference(self) -> bool:
        """Whether a common reference panel is drawn in every band."""
        return self.reference_limit is not None

    def panel_position(self, panel_key: str) -> tuple[int, int]:
        """Return ``(band, column)`` for a panel, both 1-based."""
        for band_index, band in enumerate(self.bands, start=1):
            if panel_key in band:
                return band_index, band.index(panel_key) + 1
        raise KeyError(panel_key)

    def plotted_value(self, cell: comparison.NWayPanelValue) -> float:
        """Return the quantity drawn for one cell."""
        return cell.deviation if self.plotted_quantity == "deviation" else cell.value

    def to_manifest(self, result: comparison.NWayComparisonResult) -> dict:
        """Serialize every layout, scale, and highlight decision."""
        cells = {
            (panel.panel_key, row.term): panel
            for row in result.rows
            for panel in row.panels
        }
        return {
            "chart": "N-way reference-deviation chart",
            "render_spec": self.spec.to_dict(),
            "plotted_quantity": self.plotted_quantity,
            "highlight_mode": self.spec.highlight.value,
            "highlighted_cells": [
                {
                    "panel_key": panel_key,
                    "term": term,
                    "plotted_value": self.plotted_value(cells[(panel_key, term)]),
                }
                for panel_key, term in sorted(self.highlighted)
            ],
            "scale": {
                "policy": self.spec.scale.value,
                "kind": (
                    (
                        "joint_symmetric"
                        if self.plotted_quantity == "deviation"
                        else "joint_nonnegative"
                    )
                    if self.spec.scale == ScalePolicy.SHARED
                    else "independent_per_panel"
                ),
                "padding_factor": _NWAY_AXIS_PADDING,
                "panel_absolute_limits": dict(self.panel_absolute_limits),
                "panel_axis_limits": {
                    key: list(limits) for key, limits in self.panel_limits.items()
                },
                "note": (
                    "All panels share identical x-limits."
                    if self.spec.scale == ScalePolicy.SHARED
                    else "Panel x-limits differ; bar lengths are not comparable "
                    "across panels."
                ),
            },
            "reference_scale": (
                {
                    "kind": "independent_nonnegative",
                    "absolute_limit": self.reference_limit,
                    "direction": self.spec.reference_direction.value,
                }
                if self.has_common_reference
                else None
            ),
            "layout": {
                "max_columns": self.spec.max_columns,
                "band_count": len(self.bands),
                "bands": [list(band) for band in self.bands],
                "panel_positions": {
                    key: dict(zip(("band", "column"), self.panel_position(key)))
                    for key in self.panel_keys
                },
                "wrapping": (
                    "Panels fill bands left to right in declared order; each band "
                    "repeats the reference panel and term labels."
                ),
                "term_label_placement": self.spec.term_labels.value,
                "term_order": list(self.terms),
            },
        }


def nway_panel_bands(
    panel_keys: tuple[str, ...] | list[str], max_columns: int
) -> tuple[tuple[str, ...], ...]:
    """Split ordered panels into deterministic bands of at most ``max_columns``."""
    if max_columns < 1:
        raise ValueError(f"max_columns must be >= 1, got {max_columns}.")
    keys = tuple(panel_keys)
    return tuple(
        keys[start : start + max_columns] for start in range(0, len(keys), max_columns)
    )


def build_nway_render_plan(
    result: comparison.NWayComparisonResult,
    render_spec: NWayRenderSpec | None = None,
) -> NWayRenderPlan:
    """Validate an N-way result and compute its layout and scale decisions.

    Raises:
        ValueError: If the result has no rows, misaligned panels, missing
            deviations for a referenced comparison, or incommensurate metrics.
    """
    spec = render_spec or NWayRenderSpec()
    rows = sorted(result.rows, key=lambda row: row.display_order)
    if not rows:
        raise ValueError("N-way deviation rendering requires at least one row.")
    manifest = result.manifest
    panel_manifest = manifest["panels"]
    panel_keys = tuple(panel["key"] for panel in panel_manifest)
    panel_labels = {panel["key"]: panel["label"] for panel in panel_manifest}
    for row in rows:
        if [panel.panel_key for panel in row.panels] != list(panel_keys):
            raise ValueError(
                "Every N-way row must contain exactly the manifest panels in "
                "declared order."
            )
    _validate_nway_commensurate(manifest)

    reference_policy = manifest.get("reference_policy", "common")
    plotted_quantity = "value" if reference_policy == "none" else "deviation"
    if plotted_quantity == "deviation" and any(
        panel.deviation is None for row in rows for panel in row.panels
    ):
        raise ValueError("Referenced N-way cells must all carry a deviation.")

    def plotted(cell):
        return cell.deviation if plotted_quantity == "deviation" else cell.value

    per_panel = {
        key: max(
            (abs(plotted(row.panels[index])) for row in rows),
            default=0.0,
        )
        for index, key in enumerate(panel_keys)
    }
    if spec.scale == ScalePolicy.SHARED:
        shared = max(per_panel.values(), default=0.0) or 1.0
        absolute_limits = {key: shared for key in panel_keys}
    else:
        absolute_limits = {key: per_panel[key] or 1.0 for key in panel_keys}
    panel_limits = {
        key: (
            (-limit * _NWAY_AXIS_PADDING, limit * _NWAY_AXIS_PADDING)
            if plotted_quantity == "deviation"
            else (0.0, limit * _NWAY_AXIS_PADDING)
        )
        for key, limit in absolute_limits.items()
    }
    reference_limit = None
    if reference_policy == "common":
        reference_limit = max((row.reference_value for row in rows), default=0.0) or 1.0
    return NWayRenderPlan(
        spec=spec,
        reference_policy=reference_policy,
        plotted_quantity=plotted_quantity,
        terms=tuple(row.term for row in rows),
        panel_keys=panel_keys,
        panel_labels=panel_labels,
        bands=nway_panel_bands(panel_keys, spec.max_columns),
        panel_limits=panel_limits,
        panel_absolute_limits=absolute_limits,
        reference_limit=reference_limit,
        highlighted=frozenset(nway_extrema_cells(result, spec.highlight)),
    )


def _validate_nway_commensurate(manifest: dict) -> None:
    metric = manifest["metric"]
    entries = list(manifest["panels"]) + list(manifest.get("references", []))
    for entry in entries:
        if "metric" in entry and entry["metric"] != metric:
            raise ValueError(
                f"N-way entry {entry.get('key')!r} uses metric {entry['metric']!r}, "
                f"which is incommensurate with the shared metric {metric!r}."
            )
    if manifest.get("preprocessing", {}).get("term_form", "surface") != "surface":
        raise ValueError("N-way rendering currently supports surface terms.")


def nway_extrema_cells(
    result: comparison.NWayComparisonResult,
    mode: ExtremaHighlight | str = ExtremaHighlight.PER_GENRE,
) -> set[tuple[str, str]]:
    """Return ``(panel_key, term)`` cells highlighted under ``mode``.

    Deviations are used when present, otherwise panel values.  Ties are
    included.  A positive or negative extreme is omitted when no cell of that
    sign exists in the applicable scope.
    """
    mode = ExtremaHighlight(mode)
    if mode == ExtremaHighlight.OFF:
        return set()
    cells = [
        (
            panel.panel_key,
            row.term,
            panel.deviation if panel.deviation is not None else panel.value,
        )
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


_NWAY_REFERENCE_STYLE = {"facecolor": "#D1D5DB", "edgecolor": "#475569"}
_NWAY_BELOW_STYLE = {
    "facecolor": "#F4B6B0",
    "highlight": "#B42318",
    "edgecolor": "#7A271A",
    "hatch": "////",
}
_NWAY_ABOVE_STYLE = {
    "facecolor": "#A9C7E8",
    "highlight": "#175CD3",
    "edgecolor": "#1849A9",
    "hatch": "...",
}
_NWAY_VALUE_STYLE = {
    "facecolor": "#CBD5E1",
    "highlight": "#334155",
    "edgecolor": "#1E293B",
    "hatch": "",
}
_NWAY_ROW_GUIDE_COLOR = "#E5E7EB"


def plot_nway_deviation_comparison(
    result: comparison.NWayComparisonResult,
    *,
    title: str = "Lexical frequency by genre",
    highlight: ExtremaHighlight | str | None = None,
    save_path: str | None = None,
    figsize: tuple | None = None,
    render_spec: NWayRenderSpec | None = None,
):
    """Plot an N-way reference-deviation chart.

    With a common reference, the reference uses its own non-negative scale and
    every deviation panel uses the plan's panel scale (one joint symmetric
    scale by default), so bar lengths are directly comparable across panels.
    Direction and, when enabled, hatching redundantly encode the sign for
    readers with color-vision differences and for grayscale output.  Panels
    wrap into deterministic bands of at most ``render_spec.max_columns``.

    Args:
        result: Aligned N-way analysis result.
        title: Figure title.
        highlight: Shorthand for ``NWayRenderSpec(highlight=...)``; must not be
            combined with ``render_spec``.
        save_path: Optional output path.
        figsize: Optional figure size; derived from rows and bands otherwise.
        render_spec: Layout, label, scale, and styling choices.

    Returns:
        ``(fig, axes)`` where ``axes`` maps ``"reference"``/``"terms"`` to the
        first band's axes (or ``None``), ``"panels"`` to panel axes by key, and
        ``"bands"`` to per-band axis dictionaries.
    """
    if render_spec is None:
        render_spec = NWayRenderSpec(
            highlight=ExtremaHighlight.PER_GENRE if highlight is None else highlight
        )
    elif highlight is not None:
        raise ValueError("Pass highlight inside render_spec, not separately.")
    plan = build_nway_render_plan(result, render_spec)
    spec = plan.spec
    rows = sorted(result.rows, key=lambda row: row.display_order)
    positions = list(range(len(rows)))
    has_reference = plan.has_common_reference
    placement = spec.term_labels
    band_width = max(len(band) for band in plan.bands)
    # Term labels get their own narrow column so wrapped bands keep panel
    # columns aligned: before the reference, between reference and panels,
    # or after the widest band.
    label_column = {
        TermLabelPlacement.OUTSIDE_LEFT: 0,
        TermLabelPlacement.CENTER_COLUMN: int(has_reference),
        TermLabelPlacement.OUTSIDE_RIGHT: int(has_reference) + band_width,
    }[placement]
    first_panel_column = int(has_reference) + (
        0 if placement == TermLabelPlacement.OUTSIDE_RIGHT else 1
    )
    reference_column = 1 if placement == TermLabelPlacement.OUTSIDE_LEFT else 0
    width_ratios = [1.0] * (band_width + int(has_reference) + 1)
    width_ratios[label_column] = 0.62
    if has_reference:
        width_ratios[reference_column] = 1.25
    if figsize is None:
        band_height = 0.42 * len(rows) + 1.6
        figsize = (
            max(13.0, 4.2 + 1.75 * band_width),
            max(7.0, band_height * len(plan.bands) + 1.2),
        )

    fig = plt.figure(figsize=figsize, layout="constrained")
    grid = fig.add_gridspec(
        len(plan.bands), len(width_ratios), width_ratios=width_ratios, wspace=0.04
    )
    shared_y_axis = None
    band_axes = []
    panel_axes = {}
    for band_index, band in enumerate(plan.bands):

        def add_axis(column):
            nonlocal shared_y_axis
            axis = fig.add_subplot(grid[band_index, column], sharey=shared_y_axis)
            if shared_y_axis is None:
                shared_y_axis = axis
            return axis

        reference_ax = None
        if has_reference:
            reference_ax = add_axis(reference_column)
            _draw_nway_reference(reference_ax, rows, positions, plan, result)
        terms_ax = add_axis(label_column)
        _draw_nway_term_column(terms_ax, rows, positions, spec)
        axes_in_band = []
        for offset, panel_key in enumerate(band):
            axis = add_axis(first_panel_column + offset)
            _draw_nway_panel(axis, rows, positions, panel_key, plan)
            panel_axes[panel_key] = axis
            axes_in_band.append(axis)
        data_axes = [axis for axis in (reference_ax, *axes_in_band) if axis]
        for axis in data_axes:
            axis.set_yticks(positions)
            axis.tick_params(axis="y", left=False, labelleft=False)
            if spec.row_guides:
                for position in positions:
                    axis.axhline(
                        position,
                        color=_NWAY_ROW_GUIDE_COLOR,
                        linewidth=0.6,
                        zorder=0,
                    )
        band_axes.append(
            {"reference": reference_ax, "terms": terms_ax, "panels": axes_in_band}
        )

    shared_y_axis.set_ylim(-0.7, len(rows) - 0.3)
    shared_y_axis.invert_yaxis()
    suptitle = title
    if spec.scale == ScalePolicy.INDEPENDENT:
        suptitle = f"{title}\nIndependent panel scales: bar lengths differ by panel"
    fig.suptitle(suptitle, fontsize=14, fontweight="bold")
    if spec.legend:
        handles = _nway_legend_handles(plan, result)
        fig.legend(
            handles=handles,
            loc="outside lower center",
            ncols=min(len(handles), 5),
            frameon=False,
            fontsize=9,
        )
    if save_path:
        fig.savefig(save_path, dpi=180, bbox_inches="tight")
    return fig, {
        "reference": band_axes[0]["reference"],
        "terms": band_axes[0]["terms"],
        "panels": panel_axes,
        "bands": band_axes,
    }


def _draw_nway_reference(axis, rows, positions, plan, result) -> None:
    sign = -1 if plan.spec.reference_direction == ReferenceDirection.LEFT else 1
    axis.barh(
        positions,
        [sign * row.reference_value for row in rows],
        color=_NWAY_REFERENCE_STYLE["facecolor"],
        edgecolor=_NWAY_REFERENCE_STYLE["edgecolor"],
        linewidth=0.8,
        height=0.68,
        zorder=2,
    )
    axis.axvline(0, color="#111827", linewidth=0.9)
    limit = plan.reference_limit * _NWAY_AXIS_PADDING
    axis.set_xlim(*((-limit, 0) if sign < 0 else (0, limit)))
    axis.set_title(
        textwrap.fill(result.manifest["reference"]["label"], width=16), fontsize=10
    )
    axis.set_xlabel(
        textwrap.fill(_metric_label(result.manifest["metric"]), width=22), fontsize=9
    )
    axis.xaxis.set_major_locator(ticker.MaxNLocator(nbins=3))
    axis.xaxis.set_major_formatter(
        ticker.FuncFormatter(lambda value, _: _compact_tick_label(value, signed=False))
    )
    axis.grid(axis="x", linestyle=":", linewidth=0.5, color="#CBD5E1")


def _draw_nway_term_column(axis, rows, positions, spec) -> None:
    placement = spec.term_labels
    x_position, alignment = {
        TermLabelPlacement.CENTER_COLUMN: (0.5, "center"),
        TermLabelPlacement.OUTSIDE_LEFT: (0.95, "right"),
        TermLabelPlacement.OUTSIDE_RIGHT: (0.05, "left"),
    }[placement]
    axis.set_xlim(0, 1)
    for position, row in zip(positions, rows):
        axis.text(x_position, position, row.term, ha=alignment, va="center", fontsize=9)
    if placement == TermLabelPlacement.CENTER_COLUMN:
        axis.set_title("Word", fontsize=10)
    axis.set_xticks([])
    axis.tick_params(axis="y", left=False, labelleft=False)
    for spine in axis.spines.values():
        spine.set_visible(False)


def _draw_nway_panel(axis, rows, positions, panel_key, plan) -> None:
    spec = plan.spec
    index = plan.panel_keys.index(panel_key)
    cells = [row.panels[index] for row in rows]
    values = [plan.plotted_value(cell) for cell in cells]
    colors, edges, hatches, linewidths = [], [], [], []
    for row, value in zip(rows, values):
        is_highlighted = (panel_key, row.term) in plan.highlighted
        if plan.plotted_quantity == "value":
            style = _NWAY_VALUE_STYLE
        elif value < 0:
            style = _NWAY_BELOW_STYLE
        elif value > 0:
            style = _NWAY_ABOVE_STYLE
        else:
            style = {**_NWAY_REFERENCE_STYLE, "highlight": "#D1D5DB", "hatch": ""}
        colors.append(style["highlight"] if is_highlighted else style["facecolor"])
        edges.append(style["edgecolor"])
        hatches.append(style["hatch"] if spec.hatching else "")
        linewidths.append(1.4 if is_highlighted else 0.7)
    bars = axis.barh(
        positions,
        values,
        color=colors,
        edgecolor=edges,
        linewidth=linewidths,
        height=0.68,
        zorder=2,
    )
    for bar, hatch in zip(bars, hatches):
        bar.set_hatch(hatch)
    axis.axvline(0, color="#111827", linewidth=0.9)
    axis.set_xlim(*plan.panel_limits[panel_key])
    label = plan.panel_labels[panel_key]
    if spec.scale == ScalePolicy.INDEPENDENT:
        label = f"{label} [independent scale]"
    axis.set_title(textwrap.fill(label, width=14), fontsize=10)
    if plan.plotted_quantity == "value":
        xlabel = "Value"
    elif plan.reference_policy == "per_panel_complement":
        xlabel = textwrap.fill(f"Deviation from {cells[0].reference_label}", width=24)
    else:
        xlabel = "Deviation"
    if spec.scale == ScalePolicy.INDEPENDENT:
        xlabel = f"{xlabel} (own scale)"
    axis.set_xlabel(xlabel, fontsize=9)
    axis.xaxis.set_major_locator(
        ticker.MaxNLocator(nbins=3, symmetric=plan.plotted_quantity == "deviation")
    )
    signed = plan.plotted_quantity == "deviation"
    axis.xaxis.set_major_formatter(
        ticker.FuncFormatter(lambda value, _: _compact_tick_label(value, signed=signed))
    )
    axis.grid(axis="x", linestyle=":", linewidth=0.5, color="#CBD5E1")


def _nway_legend_handles(plan: NWayRenderPlan, result) -> list:
    hatching = plan.spec.hatching
    handles = []
    if plan.has_common_reference:
        handles.append(
            Patch(
                facecolor=_NWAY_REFERENCE_STYLE["facecolor"],
                edgecolor=_NWAY_REFERENCE_STYLE["edgecolor"],
                label="Reference value",
            )
        )
    if plan.plotted_quantity == "value":
        handles.append(
            Patch(
                facecolor=_NWAY_VALUE_STYLE["facecolor"],
                edgecolor=_NWAY_VALUE_STYLE["edgecolor"],
                label=_metric_label(result.manifest["metric"]),
            )
        )
        signed_styles = []
    else:
        signed_styles = [
            (_NWAY_BELOW_STYLE, "Below reference", "Most below"),
            (_NWAY_ABOVE_STYLE, "Above reference", "Most above"),
        ]
        for style, label, _ in signed_styles:
            handles.append(
                Patch(
                    facecolor=style["facecolor"],
                    edgecolor=style["edgecolor"],
                    hatch=style["hatch"] if hatching else None,
                    label=label,
                )
            )
    mode = plan.spec.highlight
    if mode != ExtremaHighlight.OFF:
        if plan.plotted_quantity == "value":
            handles.append(
                Patch(
                    facecolor=_NWAY_VALUE_STYLE["highlight"],
                    edgecolor=_NWAY_VALUE_STYLE["edgecolor"],
                    label=f"Highest ({mode.value})",
                )
            )
        for style, _, label in signed_styles:
            handles.append(
                Patch(
                    facecolor=style["highlight"],
                    edgecolor=style["edgecolor"],
                    hatch=style["hatch"] if hatching else None,
                    label=f"{label} ({mode.value})",
                )
            )
    return handles


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
