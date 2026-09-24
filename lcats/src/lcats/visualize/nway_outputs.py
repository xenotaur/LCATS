"""Write N-way comparison figures with authoritative CSV and manifest evidence.

The writer is shared by ``lcats visualize compare-many`` and experiment
wrappers so every N-way figure is accompanied by the same long-form CSV and
manifest contract: selectors, references, differences, denominators, order,
layout decisions, overlaps, complement construction, and output hashes.
"""

import csv
import hashlib
import json
import pathlib
import re
from typing import Any, Sequence

import matplotlib.pyplot as plt

from lcats.visualize import comparison
from lcats.visualize import rendering

SUPPORTED_FORMATS = ("png", "svg", "pdf")
DEFAULT_DPI = 180

# Strip timestamps and version stamps so re-rendering the same inputs yields
# byte-identical files where the backend allows it.
_DETERMINISTIC_METADATA = {
    "png": {"Software": None},
    "svg": {"Date": None},
    "pdf": {"CreationDate": None, "ModDate": None},
}
_SVG_HASH_SALT = "lcats-nway"
_STEM_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def sha256_file(path: pathlib.Path) -> str:
    """Return the SHA-256 hex digest of a file's bytes."""
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nway_long_records(
    result: comparison.NWayComparisonResult, plan: rendering.NWayRenderPlan
) -> list[dict[str, Any]]:
    """Return long-form records extended with the plotted layout decisions.

    Each record is one term x panel cell: the analysis fields from
    ``result.long_table()`` plus the drawn quantity, its axis limits, the
    panel's band/column position, and whether the cell was highlighted.
    """
    records = []
    for record in result.long_table():
        panel_key = record["panel_key"]
        band, column = plan.panel_position(panel_key)
        axis_min, axis_max = plan.panel_limits[panel_key]
        plotted_value = (
            record["deviation"]
            if plan.plotted_quantity == "deviation"
            else record["value"]
        )
        records.append(
            {
                **record,
                "plotted_quantity": plan.plotted_quantity,
                "plotted_value": plotted_value,
                "axis_min": axis_min,
                "axis_max": axis_max,
                "scale_policy": plan.spec.scale.value,
                "layout_band": band,
                "layout_column": column,
                "highlighted": (panel_key, record["term"]) in plan.highlighted,
            }
        )
    return records


def write_nway_outputs(
    result: comparison.NWayComparisonResult,
    *,
    output_dir: str | pathlib.Path,
    stem: str,
    render_spec: rendering.NWayRenderSpec | None = None,
    formats: Sequence[str] = ("png", "svg"),
    title: str = "Lexical frequency by genre",
    figsize: tuple | None = None,
    dpi: int = DEFAULT_DPI,
    extra_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Render one N-way figure and write its CSV and manifest beside it.

    Args:
        result: Aligned N-way analysis result.
        output_dir: Directory to write into; created if missing.
        stem: File stem shared by ``<stem>.<format>``, ``<stem>.csv``, and
            ``<stem>_manifest.json``.
        render_spec: Layout and styling choices; defaults to the standard spec.
        formats: Figure formats drawn from ``SUPPORTED_FORMATS``.
        title: Figure title.
        figsize: Optional figure size.
        dpi: Raster resolution.
        extra_manifest: Caller provenance merged under the ``"generator"`` key.

    Returns:
        The manifest that was written.  Output paths are relative to
        ``output_dir``; hashes are computed from the written bytes.  The
        manifest does not hash itself.
    """
    formats = list(formats)
    if not formats:
        raise ValueError("at least one figure format is required.")
    unsupported = sorted(set(formats) - set(SUPPORTED_FORMATS))
    if unsupported:
        raise ValueError(
            f"unsupported figure format(s) {unsupported!r}; "
            f"choose from {SUPPORTED_FORMATS!r}."
        )
    if len(formats) != len(set(formats)):
        raise ValueError("figure formats must not repeat.")
    if not _STEM_PATTERN.match(stem):
        raise ValueError(f"stem must be a simple file stem, got {stem!r}.")

    render_spec = render_spec or rendering.NWayRenderSpec()
    plan = rendering.build_nway_render_plan(result, render_spec)
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, _ = rendering.plot_nway_deviation_comparison(
        result, title=title, figsize=figsize, render_spec=render_spec
    )
    figure_size = [float(value) for value in fig.get_size_inches()]
    figure_paths = []
    try:
        with plt.rc_context({"svg.hashsalt": _SVG_HASH_SALT}):
            for output_format in formats:
                path = output_dir / f"{stem}.{output_format}"
                fig.savefig(
                    path,
                    dpi=dpi,
                    bbox_inches="tight",
                    metadata=_DETERMINISTIC_METADATA[output_format],
                )
                figure_paths.append((output_format, path))
    finally:
        plt.close(fig)

    records = nway_long_records(result, plan)
    csv_path = output_dir / f"{stem}.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    manifest_path = output_dir / f"{stem}_manifest.json"
    manifest = {
        **result.manifest,
        "rendering": {
            **plan.to_manifest(result),
            "title": title,
            "figure_size_inches": figure_size,
            "dpi": dpi,
            "deterministic_metadata": {
                output_format: {
                    key: value
                    for key, value in _DETERMINISTIC_METADATA[output_format].items()
                }
                for output_format in formats
            },
        },
        "outputs": {
            "csv": {
                "path": csv_path.name,
                "row_count": len(records),
                "sha256": sha256_file(csv_path),
            },
            "figures": [
                {
                    "format": output_format,
                    "path": path.name,
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
                for output_format, path in figure_paths
            ],
            "manifest": {
                "path": manifest_path.name,
                "hash_policy": (
                    "The manifest does not hash itself; every other output is "
                    "hashed after it is written."
                ),
            },
        },
    }
    if extra_manifest:
        manifest["generator"] = extra_manifest
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest
