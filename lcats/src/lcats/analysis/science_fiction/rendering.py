"""Human-facing renderers for science-fiction analysis sidecars.

The renderer is deliberately read-only and source-neutral: it consumes a
loaded ``science-fiction-sidecar-v1`` JSON object and does not alter or
promote the sidecar.  The same view model feeds Markdown, HTML, and LaTeX
outputs so that the formats expose the same conclusions and evidence.
"""

from __future__ import annotations

import html
import json
import pathlib
import re
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from lcats.analysis.science_fiction import models
from lcats.analysis.science_fiction.rubric import definitions

OutputFormat = Literal["markdown", "html", "latex"]
Detail = Literal["summary", "detailed"]

OUTPUT_FORMATS = frozenset({"markdown", "html", "latex"})
DETAIL_LEVELS = frozenset({"summary", "detailed"})

COMPARISON_COLUMN_SETS = {
    "identity": ("title", "author"),
    "knight_evaluation": ("knight_label", "knight_score", "knight_interval"),
    "knight_detail": tuple(f"knight_criterion_{index}" for index in range(1, 8)),
    "suvin_evaluation": ("suvin_novum", "suvin_evidence"),
    "suvin_detail": (
        "suvin_novelty",
        "suvin_cognitive_validation",
        "suvin_narrative_hegemony",
    ),
    "summaries": ("knight_summary", "suvin_summary"),
    "heinlein_evaluation": ("heinlein_verdict", "heinlein_interval"),
    "heinlein_detail": tuple(
        f"heinlein_{criterion_id}" for criterion_id in models.HEINLEIN_CRITERION_IDS
    ),
    "heinlein_summaries": ("heinlein_summary",),
}

HEINLEIN_SHORT_LABELS = {
    "different": "Different",
    "essential": "Essential",
    "human": "Human",
    "causal": "Causal",
    "plausible": "Plausible",
}
HEINLEIN_COMPACT_LABELS = {
    "different": "Dif",
    "essential": "Ess",
    "human": "Hum",
    "causal": "Cau",
    "plausible": "Pla",
}
HEINLEIN_VERDICT_LABELS = {
    "qualifies": "Meets all five conditions",
    "indeterminate": "Indeterminate",
    "does_not_qualify": "Does not meet all five conditions",
}

COMPARISON_COLUMN_LABELS = {
    "title": "Title",
    "story": "Title",
    "author": "Author",
    "knight_label": "Knight Label",
    "knight_score": "Knight Score",
    "knight_interval": "Knight Interval",
    "suvin_novum": "Suvin Novum",
    "suvin_evidence": "Suvin Evidence",
    "knight_summary": "Knight summary",
    "suvin_summary": "Suvin summary",
    "suvin_novelty": "Novelty",
    "suvin_cognitive_validation": "Cognitive validation",
    "suvin_narrative_hegemony": "Narrative hegemony",
}
COMPARISON_COLUMN_LABELS.update(
    {
        f"knight_{slot.slot_id}": slot.label
        for slot in definitions.KNIGHT_SEVEN.text_slots
    }
)
COMPARISON_COLUMN_LABELS.update(
    {
        "heinlein_verdict": "Heinlein Verdict",
        "heinlein_interval": "Heinlein Interval",
        "heinlein_summary": "Heinlein summary",
    }
)
COMPARISON_COLUMN_LABELS.update(
    {
        f"heinlein_{criterion_id}": HEINLEIN_SHORT_LABELS[criterion_id]
        for criterion_id in models.HEINLEIN_CRITERION_IDS
    }
)


def render_json(
    path: str | pathlib.Path,
    *,
    output_format: OutputFormat = "markdown",
    detail: Detail = "summary",
    title: str | None = None,
    author: str | None = None,
) -> str:
    """Load one sidecar JSON file and render it for a human reader."""

    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return render_sidecar(
        data,
        output_format=output_format,
        detail=detail,
        title=title,
        author=author,
    )


def render_sidecar(
    data: Mapping[str, Any],
    *,
    output_format: OutputFormat = "markdown",
    detail: Detail = "summary",
    title: str | None = None,
    author: str | None = None,
) -> str:
    """Render a loaded science-fiction sidecar.

    ``summary`` contains the compact decision header.  ``detailed`` adds the
    Knight scorecard, Suvin candidate dimensions, supporting rationales, and
    the anchored evidence records used by those analyses.
    """

    _require_choice(output_format, OUTPUT_FORMATS, "output_format")
    _require_choice(detail, DETAIL_LEVELS, "detail")
    if not isinstance(data, Mapping):
        raise TypeError("data must be a JSON object")

    view = _build_view(data, title=title, author=author)
    if output_format == "markdown":
        return _render_markdown(view, detail)
    if output_format == "html":
        return _render_html(view, detail)
    return _render_latex(view, detail)


def render_comparison_table(
    items: Sequence[Mapping[str, Any]],
    *,
    output_format: OutputFormat = "markdown",
    named_feature_headers: bool = True,
    include_detail_columns: bool = True,
    include_summary_columns: bool = True,
    columns: Sequence[str] | None = None,
    column_sets: Sequence[str] | None = None,
) -> str:
    """Render multiple sidecars as a feature-and-summary comparison table.

    Each item must contain a loaded sidecar under ``data`` and may provide
    ``title`` and ``author`` metadata.  ``named_feature_headers`` switches
    detail headers between canonical feature names such as ``Science`` and compact
    names such as ``K1``.  Detail and summary columns can be independently
    omitted for compact views.  For more explicit layouts, pass ``columns``
    with individual column IDs or ``column_sets`` with names from
    :data:`COMPARISON_COLUMN_SETS`; these override the legacy toggles.
    """

    _require_choice(output_format, OUTPUT_FORMATS, "output_format")
    rows = [
        _build_view(
            item["data"],
            title=item.get("title"),
            author=item.get("author"),
        )
        for item in items
    ]
    resolved_columns = _comparison_columns(
        named_feature_headers=named_feature_headers,
        include_detail_columns=include_detail_columns,
        include_summary_columns=include_summary_columns,
        columns=columns,
        column_sets=column_sets,
        include_heinlein=any(view.get("heinlein") for view in rows),
    )
    if output_format == "markdown":
        return _render_comparison_markdown(rows, resolved_columns)
    if output_format == "html":
        return _render_comparison_html(rows, resolved_columns)
    return _render_comparison_latex(rows, resolved_columns)


def render_comparison_table_from_json(
    paths: Sequence[str | pathlib.Path],
    *,
    output_format: OutputFormat = "markdown",
    metadata: Sequence[Mapping[str, Any]] | None = None,
    named_feature_headers: bool = True,
    include_detail_columns: bool = True,
    include_summary_columns: bool = True,
    columns: Sequence[str] | None = None,
    column_sets: Sequence[str] | None = None,
) -> str:
    """Load sidecars from paths and render a comparison table."""

    metadata = metadata or ({},) * len(paths)
    if len(metadata) != len(paths):
        raise ValueError("metadata must contain one item per path")
    items = []
    for path, item_metadata in zip(paths, metadata):
        items.append(
            {
                "data": json.loads(pathlib.Path(path).read_text(encoding="utf-8")),
                **item_metadata,
            }
        )
    return render_comparison_table(
        items,
        output_format=output_format,
        named_feature_headers=named_feature_headers,
        include_detail_columns=include_detail_columns,
        include_summary_columns=include_summary_columns,
        columns=columns,
        column_sets=column_sets,
    )


def _build_view(
    data: Mapping[str, Any], *, title: str | None, author: str | None
) -> dict[str, Any]:
    evidence_sets = _as_list(data.get("evidence_sets"))
    evidence_set = _select_current(
        evidence_sets, data.get("current", {}).get("evidence_set_id"), "evidence_set_id"
    )
    records = {
        item.get("evidence_id"): item
        for item in _as_list(evidence_set.get("records"))
        if item.get("evidence_id")
    }

    analyses = data.get("analyses", {})
    knight = _select_current(
        _as_list(analyses.get("knight")),
        data.get("current", {}).get("knight_analysis_id"),
        "analysis_id",
    )
    suvin = _select_current(
        _as_list(analyses.get("suvin_novum")),
        data.get("current", {}).get("suvin_novum_analysis_id"),
        "analysis_id",
    )

    heinlein_items = _as_list(analyses.get("heinlein"))
    heinlein = _select_current(
        heinlein_items,
        data.get("current", {}).get("heinlein_analysis_id"),
        "analysis_id",
    )
    # A failed or otherwise non-current Heinlein analysis has no pointer, so it
    # is never shown as a verdict; it is surfaced as unavailable with a warning.
    heinlein_latest = heinlein or (heinlein_items[-1] if heinlein_items else {})
    if heinlein:
        heinlein_view = _heinlein_view(heinlein)
    elif heinlein_items:
        heinlein_view = _heinlein_unavailable_view()
    else:
        heinlein_view = None

    criteria = _as_list(knight.get("criteria"))
    interval = knight.get("interval") or _knight_interval(criteria)
    definite = int(interval.get("definite_count", 0))
    possible = int(interval.get("possible_count", definite))
    total = int(interval.get("total_count", len(criteria)))
    qualified = [
        candidate
        for candidate in _as_list(suvin.get("candidates"))
        if candidate.get("qualified_novum") is True
    ]
    dominant_id = suvin.get("dominant_novum_id")
    dominant = next(
        (
            candidate
            for candidate in qualified
            if candidate.get("candidate_id") == dominant_id
        ),
        None,
    )
    return {
        "title": title or _fallback_title(data),
        "author": author,
        "status": _analysis_status(data, knight, suvin),
        "knight": {
            "classification": _knight_classification(definite, possible, total),
            "definite": definite,
            "possible": possible,
            "total": total,
            "criteria": criteria,
        },
        "suvin": {
            "classification": _suvin_classification(suvin, qualified),
            "qualified": qualified,
            "dominant": dominant,
            "dominant_id": dominant_id,
            "candidates": _as_list(suvin.get("candidates")),
        },
        "heinlein": heinlein_view,
        "records": records,
        "evidence_ids": _referenced_evidence_ids(
            criteria + (heinlein_view["criteria"] if heinlein_view else []),
            _as_list(suvin.get("candidates")),
        ),
        "provenance": _provenance(knight, suvin, heinlein_latest),
        "warnings": _warnings(data, knight, suvin, heinlein_latest)
        + (
            ["Heinlein analysis is not current and is not shown as a verdict."]
            if heinlein_items and not heinlein
            else []
        ),
    }


def _heinlein_view(heinlein: Mapping[str, Any]) -> dict[str, Any]:
    criteria = _as_list(heinlein.get("criteria"))
    statuses = {
        str(item.get("criterion_id")): str(item.get("status")) for item in criteria
    }
    interval = heinlein.get("interval") or {}
    definite = int(
        interval.get(
            "definite_count",
            sum(status == "present" for status in statuses.values()),
        )
    )
    possible = int(
        interval.get(
            "possible_count",
            sum(status in {"present", "ambiguous"} for status in statuses.values()),
        )
    )
    total = int(interval.get("total_count", len(models.HEINLEIN_CRITERION_IDS)))
    verdict = heinlein.get("verdict")
    if verdict not in models.HEINLEIN_VERDICTS:
        verdict = (
            models.heinlein_verdict(statuses)
            if set(models.HEINLEIN_CRITERION_IDS) <= set(statuses)
            else None
        )
    return {
        "verdict": verdict,
        "label": HEINLEIN_VERDICT_LABELS.get(str(verdict), "Unavailable"),
        "definite": definite,
        "possible": possible,
        "total": total,
        "criteria": criteria,
        # Counts are only meaningful alongside a verdict; without one the
        # header would show "Unavailable (2 / 5 conditions)".
        "count_text": (
            ""
            if verdict is None
            else (
                f" ({definite}–{possible} / {total} conditions)"
                if possible != definite
                else f" ({definite} / {total} conditions)"
            )
        ),
    }


def _heinlein_unavailable_view() -> dict[str, Any]:
    return {
        "verdict": None,
        "label": "Unavailable",
        "definite": 0,
        "possible": 0,
        "total": len(models.HEINLEIN_CRITERION_IDS),
        "criteria": [],
        "count_text": "",
    }


def _heinlein_row(heinlein: Mapping[str, Any] | None) -> dict[str, str]:
    if not heinlein or heinlein.get("verdict") is None:
        row = {
            "heinlein_verdict": "Unavailable",
            "heinlein_interval": "—",
            "heinlein_summary": "Heinlein unavailable",
        }
        row.update(
            {f"heinlein_{criterion_id}": "—" for criterion_id in HEINLEIN_SHORT_LABELS}
        )
        return row
    row = {
        "heinlein_verdict": heinlein["label"],
        "heinlein_interval": f"{heinlein['definite']}–{heinlein['possible']}",
        "heinlein_summary": (
            f"{heinlein['label']} ({heinlein['definite']}/{heinlein['total']}; "
            f"interval {heinlein['definite']}–{heinlein['possible']})"
        ),
    }
    markers = {
        str(item.get("criterion_id")): _status_marker(item.get("status"))
        for item in heinlein["criteria"]
    }
    row.update(
        {
            f"heinlein_{criterion_id}": markers.get(criterion_id, "—")
            for criterion_id in HEINLEIN_SHORT_LABELS
        }
    )
    return row


def _comparison_columns(
    *,
    named_feature_headers: bool,
    include_detail_columns: bool,
    include_summary_columns: bool,
    columns: Sequence[str] | None,
    column_sets: Sequence[str] | None,
    include_heinlein: bool = False,
) -> list[tuple[str, str]]:
    if columns is not None and column_sets is not None:
        raise ValueError("pass either columns or column_sets, not both")
    if columns is not None or column_sets is not None:
        requested = columns if columns is not None else column_sets or ()
        resolved: list[str] = []
        for value in requested:
            if value in COMPARISON_COLUMN_SETS:
                resolved.extend(COMPARISON_COLUMN_SETS[value])
            elif value in COMPARISON_COLUMN_LABELS:
                resolved.append(value)
            else:
                raise ValueError(f"unknown comparison column or set: {value!r}")
        if len(set(resolved)) != len(resolved):
            raise ValueError("comparison columns must be unique after set expansion")
        return [(key, COMPARISON_COLUMN_LABELS[key]) for key in resolved]

    columns = [("title", "Title"), ("author", "Author")]
    if include_detail_columns:
        knight_names = (
            tuple(
                COMPARISON_COLUMN_LABELS[f"knight_criterion_{index}"]
                for index in range(1, 8)
            )
            if named_feature_headers
            else tuple(f"K{index}" for index in range(1, 8))
        )
        columns.extend(
            (f"knight_criterion_{index}", name)
            for index, name in enumerate(knight_names, start=1)
        )
        suvin_names = (
            ("Novelty", "Cognitive validation", "Narrative hegemony")
            if named_feature_headers
            else ("N", "C", "H")
        )
        columns.extend(
            zip(
                (
                    "suvin_novelty",
                    "suvin_cognitive_validation",
                    "suvin_narrative_hegemony",
                ),
                suvin_names,
            )
        )
        if include_heinlein:
            labels = (
                HEINLEIN_SHORT_LABELS
                if named_feature_headers
                else HEINLEIN_COMPACT_LABELS
            )
            columns.extend(
                (f"heinlein_{criterion_id}", labels[criterion_id])
                for criterion_id in models.HEINLEIN_CRITERION_IDS
            )
    if include_summary_columns:
        columns.extend(
            (("knight_summary", "Knight summary"), ("suvin_summary", "Suvin summary"))
        )
        if include_heinlein:
            columns.append(("heinlein_summary", "Heinlein summary"))
    return columns


def _comparison_row(view: Mapping[str, Any]) -> dict[str, str]:
    knight = view["knight"]
    suvin = view["suvin"]
    candidate = suvin.get("dominant") or (
        suvin["candidates"][0] if suvin["candidates"] else {}
    )
    interval = f"{knight['definite']}–{knight['possible']}"
    knight_summary = (
        f"{knight['classification']} ({knight['definite']}/{knight['total']}; "
        f"interval {interval})"
    )
    if suvin["qualified"] and suvin.get("dominant"):
        suvin_summary = "Novum Present — qualified and dominant"
    elif suvin["qualified"]:
        suvin_summary = "Novum Present — qualified"
    elif suvin["classification"] == "Unavailable":
        suvin_summary = "Novum unavailable"
    else:
        suvin_summary = "Novum Absent"
    row = {
        "title": view["title"],
        "story": view["title"],
        "author": view.get("author") or "—",
        "knight_label": knight["classification"],
        "knight_score": f"{knight['definite']}/{knight['total']}",
        "knight_interval": f"{knight['definite']}–{knight['possible']}",
        "suvin_novum": (
            "Present"
            if suvin["qualified"]
            else "Unavailable" if suvin["classification"] == "Unavailable" else "Absent"
        ),
        "suvin_evidence": (
            "Qualified, Dominant"
            if suvin["qualified"] and suvin.get("dominant")
            else "Qualified" if suvin["qualified"] else "Not qualified"
        ),
        "knight_summary": knight_summary,
        "suvin_summary": suvin_summary,
        **_heinlein_row(view.get("heinlein")),
    }
    criteria = knight["criteria"]
    for criterion in criteria:
        criterion_id = str(criterion.get("criterion_id", ""))
        if not criterion_id.startswith("criterion_"):
            continue
        index = criterion_id.removeprefix("criterion_")
        marker = _status_marker(criterion.get("status"))
        row[f"knight_criterion_{index}"] = marker
    for key, source in (
        ("novelty", "novelty"),
        ("cognitive", "cognitive_validation"),
        ("hegemony", "narrative_hegemony"),
    ):
        marker = _status_marker(candidate.get(source, {}).get("status"))
        row[f"suvin_{source}"] = marker
    return row


def _render_comparison_markdown(
    views: Sequence[Mapping[str, Any]], columns: Sequence[tuple[str, str]]
) -> str:
    headers = [name for _, name in columns]
    lines = [
        "| " + " | ".join(_md(header) for header in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for view in views:
        row = _comparison_row(view)
        lines.append("| " + " | ".join(_md(row[key]) for key, _ in columns) + " |")
    lines.extend(["", "Legend: `P` = present, `A` = absent, `?` = ambiguous."])
    return "\n".join(lines) + "\n"


def _render_comparison_html(
    views: Sequence[Mapping[str, Any]], columns: Sequence[tuple[str, str]]
) -> str:
    lines = [
        '<table class="science-fiction-comparison"><thead><tr>',
        *[f"<th>{_html(name)}</th>" for _, name in columns],
        "</tr></thead><tbody>",
    ]
    for view in views:
        row = _comparison_row(view)
        lines.append(
            "<tr>"
            + "".join(f"<td>{_html(row[key])}</td>" for key, _ in columns)
            + "</tr>"
        )
    lines.extend(
        [
            "</tbody></table>",
            "<p>Legend: <code>P</code> = present, <code>A</code> = absent, <code>?</code> = ambiguous.</p>",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_comparison_latex(
    views: Sequence[Mapping[str, Any]], columns: Sequence[tuple[str, str]]
) -> str:
    alignment = "l" * len(columns)
    lines = [f"\\begin{{longtable}}{{{alignment}}}"]
    lines.append(" & ".join(_latex(name) for _, name in columns) + r" \\")
    lines.append(r"\hline")
    for view in views:
        row = _comparison_row(view)
        lines.append(" & ".join(_latex(row[key]) for key, _ in columns) + r" \\")
    lines.extend(
        [
            r"\end{longtable}",
            r"\emph{Legend:} P = present, A = absent, ? = ambiguous.",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_markdown(view: Mapping[str, Any], detail: Detail) -> str:
    title = _md(view["title"])
    if view.get("author"):
        title += f" — {_md(view['author'])}"
    knight = view["knight"]
    suvin = view["suvin"]
    dominant = suvin.get("dominant")
    qualified_suffix = (
        " — qualified and dominant"
        if dominant
        else " — qualified" if suvin["qualified"] else ""
    )
    lines = [
        f"## {title}",
        "",
        f"**Analysis status:** {view['status']}",
        f"**Knight Score:** {knight['classification']} ({knight['definite']} / {knight['total']} criteria)",
        f"**Suvin Score:** {suvin['classification']}{qualified_suffix}",
    ]
    if view.get("heinlein"):
        heinlein = view["heinlein"]
        lines.append(
            f"**Heinlein Verdict:** {heinlein['label']}{heinlein['count_text']}"
        )
    if dominant:
        lines.append(
            f"**Dominant Novum:** {_md(dominant.get('description', dominant.get('candidate_id', '')))}"
        )
    if detail == "summary":
        return "\n".join(lines) + "\n"
    lines.extend(["", "### Summary", "", _md(_summary_text(view))])
    lines.extend(_markdown_detail(view))
    return "\n".join(lines) + "\n"


def _markdown_detail(view: Mapping[str, Any]) -> list[str]:
    knight = view["knight"]
    suvin = view["suvin"]
    lines = [
        "",
        "### Knight scorecard",
        "",
        "| Criterion | Status | Materiality | Confidence | Evidence |",
        "|---|---|---|---:|---:|",
    ]
    for criterion in knight["criteria"]:
        lines.append(
            "| {criterion} | {status} | {materiality} | {confidence} | {evidence} |".format(
                criterion=_md(_criterion_label(criterion.get("criterion_id", ""))),
                status=_md(criterion.get("status", "")),
                materiality=_md(criterion.get("materiality") or "—"),
                confidence=_confidence(criterion.get("confidence")),
                evidence=len(_as_list(criterion.get("supporting_evidence"))),
            )
        )
        lines.append(f"  Rationale: {_md(criterion.get('rationale') or '—')}")
    lines.extend(["", "### Suvin candidates", ""])
    for candidate in suvin["candidates"]:
        lines.append(
            f"#### {_md(candidate.get('candidate_id', 'Unnamed candidate'))} "
            f"({'qualified' if candidate.get('qualified_novum') else 'not qualified'})"
        )
        lines.extend(["", _md(candidate.get("description", "")), ""])
        lines.append("| Dimension | Status | Confidence | Rationale |")
        lines.append("|---|---|---:|---|")
        for name in ("novelty", "cognitive_validation", "narrative_hegemony"):
            dimension = candidate.get(name, {})
            lines.append(
                f"| {_md(_dimension_label(name))} | {_md(dimension.get('status', ''))} | "
                f"{_confidence(dimension.get('confidence'))} | {_md(dimension.get('rationale') or '—')} |"
            )
        if candidate.get("estrangement", {}).get("rationale"):
            lines.extend(
                ["", f"**Estrangement:** {_md(candidate['estrangement']['rationale'])}"]
            )

    if (view.get("heinlein") or {}).get("criteria"):
        lines.extend(
            [
                "",
                "### Heinlein conditions",
                "",
                "| Condition | Status | Confidence | Evidence |",
                "|---|---|---:|---:|",
            ]
        )
        for criterion in view["heinlein"]["criteria"]:
            lines.append(
                "| {criterion} | {status} | {confidence} | {evidence} |".format(
                    criterion=_md(_heinlein_label(criterion.get("criterion_id", ""))),
                    status=_md(criterion.get("status", "")),
                    confidence=_confidence(criterion.get("confidence")),
                    evidence=len(_as_list(criterion.get("supporting_evidence"))),
                )
            )
            lines.append(f"  Rationale: {_md(criterion.get('rationale') or '—')}")

    lines.extend(["", "### Supporting evidence", ""])
    for record in _selected_records(view):
        anchor = (
            ", ".join(record.get("anchor", {}).get("paragraph_ids", []))
            or "anchor unavailable"
        )
        lines.extend(
            [
                f"**{_md(record.get('evidence_type', 'evidence'))}** · `{record.get('evidence_id', '')}` · {anchor}",
                "",
                f"> {_md(record.get('quote', ''))}",
                "",
                _md(record.get("paraphrase", "")),
                "",
            ]
        )
    lines.extend(_markdown_provenance(view))
    return lines


def _render_html(view: Mapping[str, Any], detail: Detail) -> str:
    title = _html(view["title"])
    if view.get("author"):
        title += f" — {_html(view['author'])}"
    knight = view["knight"]
    suvin = view["suvin"]
    dominant = suvin.get("dominant")
    suffix = (
        " — qualified and dominant"
        if dominant
        else " — qualified" if suvin["qualified"] else ""
    )
    lines = [
        f'<article class="science-fiction-analysis"><h2>{title}</h2>',
        f"<p><strong>Analysis status:</strong> {_html(view['status'])}<br>",
        f"<strong>Knight Score:</strong> {_html(knight['classification'])} ({knight['definite']} / {knight['total']} criteria)<br>",
        f"<strong>Suvin Score:</strong> {_html(suvin['classification'] + suffix)}</p>",
    ]
    if view.get("heinlein"):
        heinlein = view["heinlein"]
        lines.append(
            f"<p><strong>Heinlein Verdict:</strong> {_html(heinlein['label'])}"
            f"{heinlein['count_text']}</p>"
        )
    if dominant:
        lines.append(
            f"<p><strong>Dominant Novum:</strong> {_html(dominant.get('description', dominant.get('candidate_id', '')))}</p>"
        )
    if detail == "detailed":
        lines.extend([f"<h3>Summary</h3><p>{_html(_summary_text(view))}</p>"])
        lines.extend(_html_detail(view))
    lines.append("</article>")
    return "\n".join(lines) + "\n"


def _html_detail(view: Mapping[str, Any]) -> list[str]:
    knight = view["knight"]
    suvin = view["suvin"]
    lines = [
        "<h3>Knight scorecard</h3>",
        "<table><thead><tr><th>Criterion</th><th>Status</th><th>Materiality</th><th>Confidence</th><th>Evidence</th></tr></thead><tbody>",
    ]
    for criterion in knight["criteria"]:
        lines.append(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                _html(_criterion_label(criterion.get("criterion_id", ""))),
                _html(criterion.get("status", "")),
                _html(criterion.get("materiality") or "—"),
                _html(_confidence(criterion.get("confidence"))),
                len(_as_list(criterion.get("supporting_evidence"))),
            )
        )
        lines.append(
            f'<tr><td colspan="5"><strong>Rationale:</strong> '
            f"{_html(criterion.get('rationale') or '—')}</td></tr>"
        )
    lines.append("</tbody></table><h3>Suvin candidates</h3>")
    for candidate in suvin["candidates"]:
        lines.extend(
            [
                f"<h4>{_html(candidate.get('candidate_id', 'Unnamed candidate'))} ({'qualified' if candidate.get('qualified_novum') else 'not qualified'})</h4>",
                f"<p>{_html(candidate.get('description', ''))}</p>",
                "<table><thead><tr><th>Dimension</th><th>Status</th><th>Confidence</th><th>Rationale</th></tr></thead><tbody>",
            ]
        )
        for name in ("novelty", "cognitive_validation", "narrative_hegemony"):
            dimension = candidate.get(name, {})
            lines.append(
                f"<tr><td>{_html(_dimension_label(name))}</td><td>{_html(dimension.get('status', ''))}</td><td>{_html(_confidence(dimension.get('confidence')))}</td><td>{_html(dimension.get('rationale') or '—')}</td></tr>"
            )
        lines.append("</tbody></table>")
    if (view.get("heinlein") or {}).get("criteria"):
        lines.extend(
            [
                "<h3>Heinlein conditions</h3>",
                "<table><thead><tr><th>Condition</th><th>Status</th><th>Confidence</th><th>Evidence</th></tr></thead><tbody>",
            ]
        )
        for criterion in view["heinlein"]["criteria"]:
            lines.append(
                "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                    _html(_heinlein_label(criterion.get("criterion_id", ""))),
                    _html(criterion.get("status", "")),
                    _html(_confidence(criterion.get("confidence"))),
                    len(_as_list(criterion.get("supporting_evidence"))),
                )
            )
            lines.append(
                f'<tr><td colspan="4"><strong>Rationale:</strong> '
                f"{_html(criterion.get('rationale') or '—')}</td></tr>"
            )
        lines.append("</tbody></table>")
    lines.append("<h3>Supporting evidence</h3>")
    for record in _selected_records(view):
        anchor = (
            ", ".join(record.get("anchor", {}).get("paragraph_ids", []))
            or "anchor unavailable"
        )
        lines.extend(
            [
                f"<section class=\"evidence\"><h4>{_html(record.get('evidence_type', 'evidence'))}</h4>",
                f"<p><code>{_html(record.get('evidence_id', ''))}</code> · {_html(anchor)}</p>",
                f"<blockquote>{_html(record.get('quote', ''))}</blockquote>",
                f"<p>{_html(record.get('paraphrase', ''))}</p></section>",
            ]
        )
    return lines


def _render_latex(view: Mapping[str, Any], detail: Detail) -> str:
    title = _latex(view["title"])
    if view.get("author"):
        title += f" --- {_latex(view['author'])}"
    knight = view["knight"]
    suvin = view["suvin"]
    dominant = suvin.get("dominant")
    suffix = (
        " --- qualified and dominant"
        if dominant
        else " --- qualified" if suvin["qualified"] else ""
    )
    lines = [
        f"\\section*{{{title}}}",
        f"\\textbf{{Analysis status:}} {_latex(view['status'])}\\\\",
        f"\\textbf{{Knight Score:}} {_latex(knight['classification'])} ({knight['definite']} / {knight['total']} criteria)\\\\",
        f"\\textbf{{Suvin Score:}} {_latex(suvin['classification'] + suffix)}",
    ]
    if view.get("heinlein"):
        heinlein = view["heinlein"]
        lines.append(
            f"\\\\\\textbf{{Heinlein Verdict:}} {_latex(heinlein['label'])}"
            f"{_latex(heinlein['count_text'])}"
        )
    if dominant:
        lines.append(
            f"\\\\\\textbf{{Dominant Novum:}} {_latex(dominant.get('description', dominant.get('candidate_id', '')))}"
        )
    if detail == "detailed":
        lines.append(f"\\subsection*{{Summary}}\n{_latex(_summary_text(view))}")
        lines.extend(_latex_detail(view))
    return "\n\n".join(lines) + "\n"


def _latex_detail(view: Mapping[str, Any]) -> list[str]:
    knight = view["knight"]
    suvin = view["suvin"]
    lines = [
        "\\subsection*{Knight scorecard}",
        "\\begin{longtable}{llllr}",
        "Criterion & Status & Materiality & Confidence & Evidence \\\\",
        "\\hline",
    ]
    for criterion in knight["criteria"]:
        lines.append(
            "{} & {} & {} & {} & {} \\\\".format(
                _latex(_criterion_label(criterion.get("criterion_id", ""))),
                _latex(criterion.get("status", "")),
                _latex(criterion.get("materiality") or "-"),
                _latex(_confidence(criterion.get("confidence"))),
                len(_as_list(criterion.get("supporting_evidence"))),
            )
        )
        lines.append(
            f"\\multicolumn{{5}}{{l}}{{\\textbf{{Rationale:}} "
            f"{_latex(criterion.get('rationale') or '-')}}} \\\\",
        )
    lines.append("\\end{longtable}")
    lines.append("\\subsection*{Suvin candidates}")
    for candidate in suvin["candidates"]:
        lines.extend(
            [
                f"\\subsubsection*{{{_latex(candidate.get('candidate_id', 'Unnamed candidate'))}}}",
                _latex(candidate.get("description", "")),
                "",
                "\\begin{description}",
            ]
        )
        for name in ("novelty", "cognitive_validation", "narrative_hegemony"):
            dimension = candidate.get(name, {})
            lines.append(
                f"\\item[{_latex(_dimension_label(name))}] {_latex(dimension.get('status', ''))} ({_latex(_confidence(dimension.get('confidence')))})"
            )
            lines.append(
                f"\\item[Rationale] {_latex(dimension.get('rationale') or '-')}"
            )
        lines.append("\\end{description}")
    if (view.get("heinlein") or {}).get("criteria"):
        lines.extend(
            [
                "\\subsection*{Heinlein conditions}",
                "\\begin{longtable}{llll}",
                "Condition & Status & Confidence & Evidence \\\\",
                "\\hline",
            ]
        )
        for criterion in view["heinlein"]["criteria"]:
            lines.append(
                "{} & {} & {} & {} \\\\".format(
                    _latex(_heinlein_label(criterion.get("criterion_id", ""))),
                    _latex(criterion.get("status", "")),
                    _latex(_confidence(criterion.get("confidence"))),
                    len(_as_list(criterion.get("supporting_evidence"))),
                )
            )
            lines.append(
                f"\\multicolumn{{4}}{{l}}{{\\textbf{{Rationale:}} "
                f"{_latex(criterion.get('rationale') or '-')}}} \\\\",
            )
        lines.append("\\end{longtable}")
    lines.append("\\subsection*{Supporting evidence}")
    for record in _selected_records(view):
        anchor = (
            ", ".join(record.get("anchor", {}).get("paragraph_ids", []))
            or "anchor unavailable"
        )
        lines.extend(
            [
                f"\\paragraph{{{_latex(record.get('evidence_type', 'evidence'))} ({_latex(record.get('evidence_id', ''))}; {_latex(anchor)})}}",
                f"\\begin{{quote}}{_latex(record.get('quote', ''))}\\end{{quote}}",
                _latex(record.get("paraphrase", "")),
            ]
        )
    return lines


def _selected_records(view: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        view["records"][key] for key in view["evidence_ids"] if key in view["records"]
    ]


def _summary_text(view: Mapping[str, Any]) -> str:
    text = _core_summary_text(view)
    heinlein = view.get("heinlein")
    if heinlein and heinlein.get("verdict") is None:
        text += " Heinlein: Unavailable."
    elif heinlein:
        text += (
            f" Heinlein: {heinlein['label']}; {heinlein['definite']}–"
            f"{heinlein['possible']} of {heinlein['total']} conditions."
        )
    return text


def _core_summary_text(view: Mapping[str, Any]) -> str:
    knight = view["knight"]
    suvin = view["suvin"]
    dominant = suvin.get("dominant")
    if dominant:
        return (
            f"The analysis identifies {dominant.get('candidate_id', 'the dominant Novum')} "
            f"as a qualified Novum. {dominant.get('description', '')} "
            f"The Knight profile has an interval of {knight['definite']}–{knight['possible']} "
            f"affirmative criteria out of {knight['total']}."
        )
    if suvin["qualified"]:
        return (
            f"The analysis identifies a qualified Novum but no dominant Novum was designated. "
            f"The Knight profile has an interval of {knight['definite']}–{knight['possible']} "
            f"affirmative criteria out of {knight['total']}."
        )
    if suvin["classification"] == "Unavailable":
        return (
            f"The Knight profile has an interval of {knight['definite']}–{knight['possible']} "
            f"affirmative criteria out of {knight['total']}; Suvin analysis is unavailable."
        )
    return (
        f"The Knight profile has an interval of {knight['definite']}–{knight['possible']} "
        f"affirmative criteria out of {knight['total']}; no qualified Suvin Novum was identified."
    )


def _heinlein_label(value: Any) -> str:
    return HEINLEIN_SHORT_LABELS.get(str(value), str(value or ""))


def _criterion_label(value: Any) -> str:
    text = str(value or "")
    match = re.fullmatch(r"criterion_(\d+)", text)
    return f"Criterion {match.group(1)}" if match else text


def _referenced_evidence_ids(
    criteria: list[Mapping[str, Any]], candidates: list[Mapping[str, Any]]
) -> list[str]:
    ids: list[str] = []
    for criterion in criteria:
        for reference in _as_list(criterion.get("supporting_evidence")) + _as_list(
            criterion.get("counterevidence")
        ):
            _append_id(ids, reference)
    for candidate in candidates:
        for reference in _as_list(candidate.get("evidence")):
            _append_id(ids, reference)
        for name in ("novelty", "cognitive_validation", "narrative_hegemony"):
            dimension = candidate.get(name, {})
            for reference in _as_list(dimension.get("supporting_evidence")) + _as_list(
                dimension.get("counterevidence")
            ):
                _append_id(ids, reference)
        estrangement = candidate.get("estrangement", {})
        for field in (
            "character_reaction_evidence",
            "reader_facing_evidence",
            "storyworld_consequence_evidence",
        ):
            for reference in _as_list(estrangement.get(field)):
                _append_id(ids, reference)
    return ids


def _append_id(ids: list[str], reference: Any) -> None:
    evidence_id = (
        reference.get("evidence_id") if isinstance(reference, Mapping) else None
    )
    if evidence_id and evidence_id not in ids:
        ids.append(evidence_id)


def _select_current(
    items: list[Mapping[str, Any]], current_id: Any, key: str
) -> Mapping[str, Any]:
    if not current_id:
        return {}
    for item in items:
        if item.get(key) == current_id:
            return item
    return {}


def _analysis_status(
    data: Mapping[str, Any], knight: Mapping[str, Any], suvin: Mapping[str, Any]
) -> str:
    if knight.get("status") == "failed" or suvin.get("status") == "failed":
        return "Failed"
    if (
        data.get("partial_success")
        or knight.get("status") == "partial"
        or suvin.get("status") == "partial"
    ):
        return "Partial"
    if not knight and not suvin:
        return "Unavailable"
    if not knight or not suvin:
        return "Partial"
    return "Complete"


def _knight_classification(definite: int, possible: int, total: int) -> str:
    if total == 0:
        return "Unavailable"
    if definite > 0:
        return "Science Fiction"
    if possible > 0:
        return "Indeterminate"
    return "Not Science Fiction"


def _suvin_classification(
    suvin: Mapping[str, Any], qualified: list[Mapping[str, Any]]
) -> str:
    if not suvin:
        return "Unavailable"
    return "Novum Present" if qualified else "Novum Absent"


def _knight_interval(criteria: list[Mapping[str, Any]]) -> dict[str, int]:
    present = sum(item.get("status") == "present" for item in criteria)
    possible = sum(item.get("status") in {"present", "ambiguous"} for item in criteria)
    return {
        "definite_count": present,
        "possible_count": possible,
        "total_count": len(criteria),
    }


def _provenance(
    knight: Mapping[str, Any],
    suvin: Mapping[str, Any],
    heinlein: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    provenance = {
        "knight": knight.get("provenance", {}),
        "suvin": suvin.get("provenance", {}),
    }
    if heinlein:
        provenance["heinlein"] = heinlein.get("provenance", {})
    return provenance


def _warnings(
    data: Mapping[str, Any],
    knight: Mapping[str, Any],
    suvin: Mapping[str, Any],
    heinlein: Mapping[str, Any] | None = None,
) -> list[str]:
    warnings = []
    validation = data.get("validation", {})
    if validation.get("valid") is False:
        warnings.append("Sidecar validation reported errors.")
    for analysis in (knight, suvin, *([heinlein] if heinlein else [])):
        if analysis.get("failures"):
            warnings.append(
                f"{analysis.get('stage', analysis.get('analysis_id', 'Analysis'))} contains failure records."
            )
    return warnings


def _markdown_provenance(view: Mapping[str, Any]) -> list[str]:
    lines = ["", "### Provenance"]
    for label, provenance in view["provenance"].items():
        if provenance:
            model = provenance.get("model") or "unknown model"
            rubric = provenance.get("rubric_version") or "unknown rubric"
            lines.append(f"- {label.title()}: {model}; rubric `{rubric}`")
    for warning in view["warnings"]:
        lines.append(f"- Warning: {warning}")
    return lines


def _fallback_title(data: Mapping[str, Any]) -> str:
    value = str(
        data.get("lcats_id") or data.get("story_path") or "Science-fiction analysis"
    )
    value = value.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    value = re.sub(r"[_-]+", " ", value).strip()
    return value.title()


def _dimension_label(name: str) -> str:
    return {
        "cognitive_validation": "Cognitive validation",
        "narrative_hegemony": "Narrative hegemony",
    }.get(name, name.title())


def _as_list(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value or [] if isinstance(item, Mapping)]


def _confidence(value: Any) -> str:
    return "—" if value is None else f"{float(value):.2f}"


def _status_marker(value: Any) -> str:
    return {"present": "P", "absent": "A", "ambiguous": "?"}.get(str(value), "—")


def _require_choice(value: str, choices: set[str] | frozenset[str], name: str) -> None:
    if value not in choices:
        raise ValueError(f"{name} must be one of {sorted(choices)!r}")


def _md(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def _html(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _latex(value: Any) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    text = re.sub(r"[\\&%$#_{}~^]", lambda match: replacements[match.group()], text)
    return text.replace("\n", " ")
