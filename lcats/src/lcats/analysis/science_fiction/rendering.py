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

OutputFormat = Literal["markdown", "html", "latex"]
Detail = Literal["summary", "detailed"]

OUTPUT_FORMATS = frozenset({"markdown", "html", "latex"})
DETAIL_LEVELS = frozenset({"summary", "detailed"})


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
) -> str:
    """Render multiple sidecars as a feature-and-summary comparison table.

    Each item must contain a loaded sidecar under ``data`` and may provide
    ``title`` and ``author`` metadata.  ``named_feature_headers`` switches
    detail headers between human names such as ``Criterion 1`` and compact
    names such as ``K1``.  Detail and summary columns can be independently
    omitted for compact views.
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
    columns = _comparison_columns(
        named_feature_headers=named_feature_headers,
        include_detail_columns=include_detail_columns,
        include_summary_columns=include_summary_columns,
    )
    if output_format == "markdown":
        return _render_comparison_markdown(rows, columns)
    if output_format == "html":
        return _render_comparison_html(rows, columns)
    return _render_comparison_latex(rows, columns)


def render_comparison_table_from_json(
    paths: Sequence[str | pathlib.Path],
    *,
    output_format: OutputFormat = "markdown",
    metadata: Sequence[Mapping[str, Any]] | None = None,
    named_feature_headers: bool = True,
    include_detail_columns: bool = True,
    include_summary_columns: bool = True,
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

    criteria = _as_list(knight.get("criteria"))
    interval = knight.get("interval") or _knight_interval(criteria)
    definite = int(interval.get("definite_count", 0))
    possible = int(interval.get("possible_count", definite))
    total = int(interval.get("total_count", len(criteria) or 7))
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
    if dominant is None and qualified:
        dominant = qualified[0]

    return {
        "title": title or _fallback_title(data),
        "author": author,
        "status": _analysis_status(data, knight, suvin),
        "knight": {
            "classification": _knight_classification(definite, possible),
            "definite": definite,
            "possible": possible,
            "total": total,
            "criteria": criteria,
        },
        "suvin": {
            "classification": "Novum Present" if qualified else "Novum Absent",
            "qualified": qualified,
            "dominant": dominant,
            "dominant_id": dominant_id,
            "candidates": _as_list(suvin.get("candidates")),
        },
        "records": records,
        "evidence_ids": _referenced_evidence_ids(
            criteria, _as_list(suvin.get("candidates"))
        ),
        "provenance": _provenance(knight, suvin),
        "warnings": _warnings(data, knight, suvin),
    }


def _comparison_columns(
    *,
    named_feature_headers: bool,
    include_detail_columns: bool,
    include_summary_columns: bool,
) -> list[tuple[str, str]]:
    columns = [("story", "Story"), ("author", "Author")]
    if include_detail_columns:
        knight_names = (
            tuple(f"Criterion {index}" for index in range(1, 8))
            if named_feature_headers
            else tuple(f"K{index}" for index in range(1, 8))
        )
        columns.extend(
            (f"k{index}", name) for index, name in enumerate(knight_names, start=1)
        )
        suvin_names = (
            ("Novelty", "Cognitive validation", "Narrative hegemony")
            if named_feature_headers
            else ("N", "C", "H")
        )
        columns.extend(zip(("novelty", "cognitive", "hegemony"), suvin_names))
    if include_summary_columns:
        columns.extend(
            (("knight_summary", "Knight summary"), ("suvin_summary", "Suvin summary"))
        )
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
    else:
        suvin_summary = "Novum Absent"
    row = {
        "story": view["title"],
        "author": view.get("author") or "—",
        "knight_summary": knight_summary,
        "suvin_summary": suvin_summary,
    }
    criteria = knight["criteria"]
    for index, criterion in enumerate(criteria, start=1):
        row[f"k{index}"] = _status_marker(criterion.get("status"))
    for key, source in (
        ("novelty", "novelty"),
        ("cognitive", "cognitive_validation"),
        ("hegemony", "narrative_hegemony"),
    ):
        row[key] = _status_marker(candidate.get(source, {}).get("status"))
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
    lines.extend(["", "### Suvin candidates", ""])
    for candidate in suvin["candidates"]:
        lines.append(
            f"#### {_md(candidate.get('candidate_id', 'Unnamed candidate'))} "
            f"({'qualified' if candidate.get('qualified_novum') else 'not qualified'})"
        )
        lines.extend(["", _md(candidate.get("description", "")), ""])
        lines.append("| Dimension | Status | Confidence |")
        lines.append("|---|---|---:|")
        for name in ("novelty", "cognitive_validation", "narrative_hegemony"):
            dimension = candidate.get(name, {})
            lines.append(
                f"| {_md(_dimension_label(name))} | {_md(dimension.get('status', ''))} | "
                f"{_confidence(dimension.get('confidence'))} |"
            )
        if candidate.get("estrangement", {}).get("rationale"):
            lines.extend(
                ["", f"**Estrangement:** {_md(candidate['estrangement']['rationale'])}"]
            )

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
    lines.append("</tbody></table><h3>Suvin candidates</h3>")
    for candidate in suvin["candidates"]:
        lines.extend(
            [
                f"<h4>{_html(candidate.get('candidate_id', 'Unnamed candidate'))} ({'qualified' if candidate.get('qualified_novum') else 'not qualified'})</h4>",
                f"<p>{_html(candidate.get('description', ''))}</p>",
                "<table><thead><tr><th>Dimension</th><th>Status</th><th>Confidence</th></tr></thead><tbody>",
            ]
        )
        for name in ("novelty", "cognitive_validation", "narrative_hegemony"):
            dimension = candidate.get(name, {})
            lines.append(
                f"<tr><td>{_html(_dimension_label(name))}</td><td>{_html(dimension.get('status', ''))}</td><td>{_html(_confidence(dimension.get('confidence')))}</td></tr>"
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
        lines.append("\\end{description}")
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
    return (
        f"The Knight profile has an interval of {knight['definite']}–{knight['possible']} "
        f"affirmative criteria out of {knight['total']}; no qualified Suvin Novum was identified."
    )


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
        for group in _as_list(candidate.get("estrangement", {}).values()):
            for reference in _as_list(group):
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
    if current_id:
        for item in items:
            if item.get(key) == current_id:
                return item
    return items[-1] if items else {}


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
    return "Complete"


def _knight_classification(definite: int, possible: int) -> str:
    if definite > 0:
        return "Science Fiction"
    if possible > 0:
        return "Indeterminate"
    return "Not Science Fiction"


def _knight_interval(criteria: list[Mapping[str, Any]]) -> dict[str, int]:
    present = sum(item.get("status") == "present" for item in criteria)
    possible = sum(item.get("status") in {"present", "ambiguous"} for item in criteria)
    return {
        "definite_count": present,
        "possible_count": possible,
        "total_count": len(criteria),
    }


def _provenance(knight: Mapping[str, Any], suvin: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "knight": knight.get("provenance", {}),
        "suvin": suvin.get("provenance", {}),
    }


def _warnings(
    data: Mapping[str, Any], knight: Mapping[str, Any], suvin: Mapping[str, Any]
) -> list[str]:
    warnings = []
    validation = data.get("validation", {})
    if validation.get("valid") is False:
        warnings.append("Sidecar validation reported errors.")
    for analysis in (knight, suvin):
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
    for old, new in (
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ):
        text = text.replace(old, new)
    return text.replace("\n", " ")
