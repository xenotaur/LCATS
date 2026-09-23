"""Comparative lexical analysis contracts for LCATS visualizations."""

from __future__ import annotations

import collections
import dataclasses
import enum
import hashlib
import re
from typing import Any, Iterable, Mapping

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from lcats.analysis import story_analysis


class MembershipMode(str, enum.Enum):
    """Supported genre-membership interpretations."""

    CANDIDATE = "candidate"
    PRIMARY = "primary"
    SELECTION = "selection"


class SelectorKind(str, enum.Enum):
    """Selector variants resolved against an explicit universe."""

    ALL = "all"
    GENRE = "genre"
    MANIFEST_GENRE = "manifest_genre"
    STORY_LIST = "story_list"
    INCLUDE_EXCLUDE = "include_exclude"
    COMPLEMENT = "complement"


class MetricName(str, enum.Enum):
    """Supported comparison metrics."""

    RAW_COUNT = "raw_count"
    PER_MILLION = "per_million"
    DOCUMENT_COUNT = "document_count"
    DOCUMENT_PERCENTAGE = "document_percentage"
    MEAN_DOCUMENT_RELATIVE_FREQUENCY = "mean_document_relative_frequency"
    MEAN_TFIDF = "mean_tfidf"
    TFIDF_CONTRAST = "tfidf_contrast"


class VocabularyPolicy(str, enum.Enum):
    """Candidate-vocabulary construction policies."""

    ALL = "all"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    TOP_DIFFERENCE = "top_difference"
    TOP_ABSOLUTE_DIFFERENCE = "top_absolute_difference"
    UNION_TOP = "union_top"
    INTERSECTION_TOP = "intersection_top"


class Ordering(str, enum.Enum):
    """Display-order controllers for an aligned comparison table."""

    LEFT_VALUE = "left_value"
    RIGHT_VALUE = "right_value"
    SIGNED_DIFFERENCE = "signed_difference"
    ABSOLUTE_DIFFERENCE = "absolute_difference"
    ALPHABETICAL = "alphabetical"
    EXPLICIT = "explicit"


class ComparisonStyle(str, enum.Enum):
    """Rendering styles whose compatibility rules affect analysis output."""

    MIRRORED = "mirrored"
    REFERENCE_OVERLAY = "reference_overlay"


class NWayVocabularyPolicy(str, enum.Enum):
    """Vocabulary ranking policies for reference-to-many comparisons."""

    REFERENCE_VALUE = "reference_value"
    MAX_ABSOLUTE_DEVIATION = "max_absolute_deviation"
    MAX_PANEL_VALUE = "max_panel_value"
    UNION_TOP = "union_top"


class NWayOrdering(str, enum.Enum):
    """Display-order controllers for an N-way aligned comparison table."""

    REFERENCE_VALUE = "reference_value"
    MAX_ABSOLUTE_DEVIATION = "max_absolute_deviation"
    MAX_PANEL_VALUE = "max_panel_value"
    ALPHABETICAL = "alphabetical"
    EXPLICIT = "explicit"


class NWayPanelMode(str, enum.Enum):
    """Whether N-way panels show their selectors or universe complements."""

    DIRECT = "direct"
    COMPLEMENT = "complement"


class NWayReferencePolicy(str, enum.Enum):
    """What each N-way panel is compared against.

    ``COMMON`` compares every panel with one declared reference selector.
    ``PER_PANEL_COMPLEMENT`` compares each panel with ``U`` minus that panel's
    own membership.  ``NONE`` reports panel values without any deviation.
    """

    NONE = "none"
    COMMON = "common"
    PER_PANEL_COMPLEMENT = "per_panel_complement"


@dataclasses.dataclass(frozen=True)
class ComparisonDocument:
    """One document available to a comparison universe."""

    story_id: str
    text: str
    candidate_genres: tuple[str, ...] = ()
    primary_genre: str | None = None
    selection_genres: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class ComparisonCorpus:
    """A deterministic corpus snapshot used by comparison analysis."""

    documents: tuple[ComparisonDocument, ...]
    source_path: str = ""
    source_revision: str = ""

    def __post_init__(self) -> None:
        ids = [document.story_id for document in self.documents]
        if len(ids) != len(set(ids)):
            raise ValueError("ComparisonCorpus story_id values must be unique.")

    @property
    def by_story_id(self) -> dict[str, ComparisonDocument]:
        return {document.story_id: document for document in self.documents}


@dataclasses.dataclass(frozen=True)
class UniverseSpec:
    """Explicit universe declaration; complements are always computed inside it."""

    kind: str = "corpus"
    story_ids: tuple[str, ...] = ()
    source_path: str = ""
    source_revision: str = ""


@dataclasses.dataclass(frozen=True)
class Selector:
    """Normalized selector algebra for comparison groups."""

    kind: SelectorKind
    genre: str | None = None
    story_ids: tuple[str, ...] = ()
    include_story_ids: tuple[str, ...] = ()
    exclude_story_ids: tuple[str, ...] = ()
    membership_mode: MembershipMode = MembershipMode.CANDIDATE
    base: "Selector | None" = None
    label: str = ""


@dataclasses.dataclass(frozen=True)
class TokenFilter:
    """Token preprocessing policy for lexical metrics."""

    include_stopwords: bool = False
    min_length: int = 3
    lowercase: bool = True


@dataclasses.dataclass(frozen=True)
class MetricSpec:
    """Metric plus normalization metadata."""

    name: MetricName
    denominator: str = "auto"


@dataclasses.dataclass(frozen=True)
class VocabularySpec:
    """Controls aligned vocabulary construction before rendering."""

    policy: VocabularyPolicy = VocabularyPolicy.TOP_ABSOLUTE_DIFFERENCE
    top_k: int | None = 20
    include_terms: tuple[str, ...] = ()
    exclude_terms: tuple[str, ...] = ()
    min_document_count: int = 1


@dataclasses.dataclass(frozen=True)
class OrderingSpec:
    """Controls deterministic row order for the aligned table."""

    by: Ordering = Ordering.ABSOLUTE_DIFFERENCE
    explicit_terms: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class ComparisonSpec:
    """Immutable specification shared by selection, analysis, and rendering."""

    universe: UniverseSpec
    left: Selector
    right: Selector
    left_metric: MetricSpec
    right_metric: MetricSpec
    token_filter: TokenFilter = dataclasses.field(default_factory=TokenFilter)
    term_form: str = "surface"
    vocabulary: VocabularySpec = dataclasses.field(default_factory=VocabularySpec)
    ordering: OrderingSpec = dataclasses.field(default_factory=OrderingSpec)
    style: ComparisonStyle = ComparisonStyle.MIRRORED
    output_formats: tuple[str, ...] = ("png", "svg")


@dataclasses.dataclass(frozen=True)
class NWayPanelSpec:
    """One named panel in a reference-to-many comparison."""

    key: str
    selector: Selector


@dataclasses.dataclass(frozen=True)
class NWayVocabularySpec:
    """Controls vocabulary construction for an N-way comparison."""

    policy: NWayVocabularyPolicy = NWayVocabularyPolicy.REFERENCE_VALUE
    top_k: int | None = 20
    include_terms: tuple[str, ...] = ()
    exclude_terms: tuple[str, ...] = ()
    min_document_count: int = 1


@dataclasses.dataclass(frozen=True)
class NWayOrderingSpec:
    """Controls deterministic row order for an N-way comparison."""

    by: NWayOrdering = NWayOrdering.REFERENCE_VALUE
    explicit_terms: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class NWayComparisonSpec:
    """Immutable specification for an ordered N-way aligned comparison.

    Every panel is resolved against the same ``universe`` and shares one metric,
    denominator, preprocessing policy, vocabulary, and term order.  ``panels``
    are declared in display order.  With ``panel_mode=COMPLEMENT`` each panel
    selector ``S`` is displayed as ``U - S``.  ``reference`` is required for
    ``reference_policy=COMMON`` and must be ``None`` otherwise.
    """

    universe: UniverseSpec
    reference: Selector | None
    panels: tuple[NWayPanelSpec, ...]
    metric: MetricSpec
    token_filter: TokenFilter = dataclasses.field(default_factory=TokenFilter)
    term_form: str = "surface"
    vocabulary: NWayVocabularySpec = dataclasses.field(
        default_factory=NWayVocabularySpec
    )
    ordering: NWayOrderingSpec = dataclasses.field(default_factory=NWayOrderingSpec)
    panel_mode: NWayPanelMode = NWayPanelMode.DIRECT
    reference_policy: NWayReferencePolicy = NWayReferencePolicy.COMMON


@dataclasses.dataclass(frozen=True)
class SelectorResolution:
    """Concrete story IDs and provenance for a resolved selector."""

    label: str
    selector: dict[str, Any]
    story_ids: tuple[str, ...]
    story_count: int


@dataclasses.dataclass(frozen=True)
class MetricSeries:
    """Metric values plus raw support data for one resolved selector."""

    values: Mapping[str, float]
    raw_counts: Mapping[str, int]
    document_counts: Mapping[str, int]
    token_denominator: int
    document_denominator: int
    metric: MetricSpec


@dataclasses.dataclass(frozen=True)
class TfidfFit:
    """One TF-IDF matrix fit over the declared universe."""

    terms: tuple[str, ...]
    matrix: Any
    index_by_id: Mapping[str, int]


@dataclasses.dataclass(frozen=True)
class ComparisonRow:
    """One authoritative aligned term row."""

    term: str
    display_order: int
    left_value: float
    right_value: float
    left_raw_count: int
    right_raw_count: int
    left_document_count: int
    right_document_count: int
    left_token_denominator: int
    right_token_denominator: int
    left_document_denominator: int
    right_document_denominator: int
    signed_difference: float
    absolute_difference: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize the row for CSV/JSON consumers."""
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class ComparisonResult:
    """Authoritative comparison table and manifest-ready provenance."""

    rows: tuple[ComparisonRow, ...]
    manifest: dict[str, Any]

    def table(self) -> list[dict[str, Any]]:
        """Return rows as serializable dictionaries."""
        return [row.to_dict() for row in self.rows]


@dataclasses.dataclass(frozen=True)
class NWayPanelValue:
    """One panel's value and signed deviation for an aligned term row.

    ``deviation`` is ``value - reference_value`` and is ``None`` when the
    comparison has no reference.  The ``reference_*`` fields describe the
    reference this particular cell was compared with, which differs by panel
    under ``NWayReferencePolicy.PER_PANEL_COMPLEMENT``.
    """

    panel_key: str
    panel_label: str
    value: float
    deviation: float | None
    raw_count: int
    document_count: int
    token_denominator: int
    document_denominator: int
    panel_order: int = 0
    reference_key: str | None = None
    reference_label: str | None = None
    reference_value: float | None = None
    reference_raw_count: int | None = None
    reference_document_count: int | None = None
    reference_token_denominator: int | None = None
    reference_document_denominator: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the cell for CSV/JSON consumers."""
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class NWayComparisonRow:
    """One authoritative aligned term row for an N-way comparison.

    Row-level ``reference_*`` fields hold the common reference and are ``None``
    unless ``reference_policy`` is ``COMMON``; per-cell reference fields are
    always authoritative.
    """

    term: str
    display_order: int
    reference_value: float | None
    reference_raw_count: int | None
    reference_document_count: int | None
    reference_token_denominator: int | None
    reference_document_denominator: int | None
    panels: tuple[NWayPanelValue, ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the row, retaining the panel-cell structure."""
        data = dataclasses.asdict(self)
        data["panels"] = [panel.to_dict() for panel in self.panels]
        return data


@dataclasses.dataclass(frozen=True)
class NWayComparisonResult:
    """Renderer-neutral N-way table and manifest-ready provenance."""

    rows: tuple[NWayComparisonRow, ...]
    manifest: dict[str, Any]

    def table(self) -> list[dict[str, Any]]:
        """Return nested rows as serializable dictionaries."""
        return [row.to_dict() for row in self.rows]

    def long_table(self) -> list[dict[str, Any]]:
        """Return one flat record per term and comparison panel.

        Records are ordered by term display order, then declared panel order.
        Reference columns come from each cell, so per-panel references are
        reported exactly as they were used.
        """
        records = []
        for row in sorted(self.rows, key=lambda item: item.display_order):
            for panel in sorted(row.panels, key=lambda cell: cell.panel_order):
                records.append(
                    {
                        "term": row.term,
                        "display_order": row.display_order,
                        **panel.to_dict(),
                    }
                )
        return records


def compare(corpus: ComparisonCorpus, spec: ComparisonSpec) -> ComparisonResult:
    """Resolve selectors, compute metrics, and return an aligned table."""
    _validate_spec(spec)
    universe_ids = _resolve_universe(corpus, spec.universe)
    left_resolution = resolve_selector(corpus, universe_ids, spec.left)
    right_resolution = resolve_selector(corpus, universe_ids, spec.right)
    tokenized = _tokenize_universe(corpus, universe_ids, spec.token_filter)
    tfidf_fit = _fit_tfidf(corpus, universe_ids, spec.token_filter)
    left_series = _metric_series(
        selected_ids=left_resolution.story_ids,
        tokenized=tokenized,
        metric=spec.left_metric,
        tfidf_fit=tfidf_fit,
    )
    right_series = _metric_series(
        selected_ids=right_resolution.story_ids,
        tokenized=tokenized,
        metric=spec.right_metric,
        tfidf_fit=tfidf_fit,
    )
    terms = _select_vocabulary(left_series, right_series, spec.vocabulary)
    rows = _build_rows(terms, left_series, right_series, spec.ordering)
    manifest = _manifest(
        corpus=corpus,
        spec=spec,
        universe_ids=universe_ids,
        left_resolution=left_resolution,
        right_resolution=right_resolution,
        rows=rows,
        warnings=_overlap_warnings(
            left_resolution.story_ids, right_resolution.story_ids
        ),
    )
    return ComparisonResult(rows=tuple(rows), manifest=manifest)


@dataclasses.dataclass(frozen=True)
class _ResolvedNWayReference:
    """A resolved reference plus the metric series computed for it."""

    key: str
    selector: Selector
    resolution: SelectorResolution
    series: MetricSeries


@dataclasses.dataclass(frozen=True)
class _ResolvedNWayPanel:
    """A resolved panel, its optional base, and the reference it is compared with."""

    order: int
    key: str
    selector: Selector
    resolution: SelectorResolution
    series: MetricSeries
    base_resolution: SelectorResolution | None
    reference: _ResolvedNWayReference | None


def compare_many(
    corpus: ComparisonCorpus, spec: NWayComparisonSpec
) -> NWayComparisonResult:
    """Compare an ordered sequence of panels using one shared vocabulary.

    Tokenization and any TF-IDF fit are computed once over the declared
    universe, so every panel and reference shares one metric, denominator, and
    preprocessing policy.  When a reference exists, signed deviations are
    always ``panel value - reference value``.  Panel selectors may overlap; the
    manifest reports every pairwise intersection and never assumes a partition.

    Args:
        corpus: Documents available to the universe.
        spec: Ordered panel, reference, metric, vocabulary, and order policy.

    Returns:
        Renderer-neutral aligned rows plus manifest-ready provenance.
    """
    validate_nway_spec(spec)
    universe_ids = _resolve_universe(corpus, spec.universe)
    tokenized = _tokenize_universe(corpus, universe_ids, spec.token_filter)
    tfidf_fit = (
        _fit_tfidf(corpus, universe_ids, spec.token_filter)
        if spec.metric.name == MetricName.MEAN_TFIDF
        else None
    )

    def resolve_reference(key: str, selector: Selector) -> _ResolvedNWayReference:
        resolution = resolve_selector(corpus, universe_ids, selector)
        return _ResolvedNWayReference(
            key=key,
            selector=selector,
            resolution=resolution,
            series=_metric_series(
                selected_ids=resolution.story_ids,
                tokenized=tokenized,
                metric=spec.metric,
                tfidf_fit=tfidf_fit,
            ),
        )

    common_reference = (
        resolve_reference("reference", spec.reference)
        if spec.reference_policy == NWayReferencePolicy.COMMON
        else None
    )
    panels = []
    for order, panel in enumerate(spec.panels, start=1):
        selector = _nway_panel_selector(panel, spec.panel_mode)
        resolution = resolve_selector(corpus, universe_ids, selector)
        base_resolution = (
            resolve_selector(corpus, universe_ids, panel.selector)
            if spec.panel_mode == NWayPanelMode.COMPLEMENT
            else None
        )
        if spec.reference_policy == NWayReferencePolicy.PER_PANEL_COMPLEMENT:
            reference = resolve_reference(
                f"{panel.key}:complement",
                _per_panel_complement_selector(panel, selector, spec.panel_mode),
            )
        else:
            reference = common_reference
        panels.append(
            _ResolvedNWayPanel(
                order=order,
                key=panel.key,
                selector=selector,
                resolution=resolution,
                series=_metric_series(
                    selected_ids=resolution.story_ids,
                    tokenized=tokenized,
                    metric=spec.metric,
                    tfidf_fit=tfidf_fit,
                ),
                base_resolution=base_resolution,
                reference=reference,
            )
        )
    panels = tuple(panels)
    terms = _select_nway_vocabulary(common_reference, panels, spec.vocabulary)
    rows = _build_nway_rows(terms, common_reference, panels, spec.ordering)
    manifest = _nway_manifest(
        corpus=corpus,
        spec=spec,
        universe_ids=universe_ids,
        common_reference=common_reference,
        panels=panels,
        rows=rows,
    )
    return NWayComparisonResult(rows=tuple(rows), manifest=manifest)


def _nway_panel_selector(panel: NWayPanelSpec, panel_mode: NWayPanelMode) -> Selector:
    if panel_mode == NWayPanelMode.DIRECT:
        return panel.selector
    return Selector(
        SelectorKind.COMPLEMENT,
        base=panel.selector,
        label=f"U - {_display_label(panel.selector)}",
    )


def _per_panel_complement_selector(
    panel: NWayPanelSpec, panel_selector: Selector, panel_mode: NWayPanelMode
) -> Selector:
    # U - (U - S) resolves to S; label it as S so the figure stays readable.
    label = (
        _display_label(panel.selector)
        if panel_mode == NWayPanelMode.COMPLEMENT
        else f"U - {_display_label(panel_selector)}"
    )
    return Selector(SelectorKind.COMPLEMENT, base=panel_selector, label=label)


def _display_label(selector: Selector) -> str:
    return selector.label or _selector_label(selector)


def validate_nway_spec(spec: NWayComparisonSpec) -> None:
    """Raise ``ValueError`` if an N-way spec is inconsistent or unsupported."""
    if spec.universe.kind not in ("corpus", "story_list", "manifest"):
        raise ValueError(f"unsupported universe kind: {spec.universe.kind!r}")
    if len(spec.panels) < 2:
        raise ValueError(
            "N-way comparison requires at least two ordered panels; use "
            "compare() for a single target/reference pair."
        )
    panel_keys = [panel.key for panel in spec.panels]
    if any(not key for key in panel_keys):
        raise ValueError("N-way panel keys must be non-empty.")
    if len(panel_keys) != len(set(panel_keys)):
        raise ValueError("N-way panel keys must be unique.")
    policy = NWayReferencePolicy(spec.reference_policy)
    if policy == NWayReferencePolicy.COMMON and spec.reference is None:
        raise ValueError("reference_policy='common' requires a reference selector.")
    if policy != NWayReferencePolicy.COMMON and spec.reference is not None:
        raise ValueError(
            f"reference_policy={policy.value!r} does not use a common reference; "
            "set reference=None."
        )
    if NWayPanelMode(spec.panel_mode) == NWayPanelMode.COMPLEMENT and any(
        panel.selector.kind == SelectorKind.COMPLEMENT for panel in spec.panels
    ):
        raise ValueError(
            "panel_mode='complement' takes base selectors S and displays U - S; "
            "do not pass complement selectors as panel bases."
        )
    if policy != NWayReferencePolicy.COMMON and (
        spec.vocabulary.policy == NWayVocabularyPolicy.REFERENCE_VALUE
        or spec.ordering.by == NWayOrdering.REFERENCE_VALUE
    ):
        raise ValueError(
            "reference_value vocabulary/order requires reference_policy='common'."
        )
    if policy == NWayReferencePolicy.NONE and (
        spec.vocabulary.policy == NWayVocabularyPolicy.MAX_ABSOLUTE_DEVIATION
        or spec.ordering.by == NWayOrdering.MAX_ABSOLUTE_DEVIATION
    ):
        raise ValueError(
            "max_absolute_deviation vocabulary/order requires a reference; "
            "reference_policy='none' has no deviations."
        )
    if spec.vocabulary.top_k is not None and spec.vocabulary.top_k < 1:
        raise ValueError("vocabulary.top_k must be >= 1 when provided.")
    if spec.vocabulary.min_document_count < 1:
        raise ValueError("vocabulary.min_document_count must be >= 1.")
    if spec.token_filter.min_length < 1:
        raise ValueError("token_filter.min_length must be >= 1.")
    if spec.term_form != "surface":
        raise ValueError(
            "only term_form='surface' is supported before lexical artifacts."
        )
    if spec.metric.name == MetricName.TFIDF_CONTRAST:
        raise ValueError(
            "N-way reference deviations do not support tfidf_contrast; use a "
            "non-contrast metric computed on the same reference and panels."
        )
    _validate_metric_denominator(spec.metric)


def resolve_selector(
    corpus: ComparisonCorpus, universe_ids: tuple[str, ...], selector: Selector
) -> SelectorResolution:
    """Resolve a selector to sorted story IDs inside ``universe_ids``."""
    universe_set = set(universe_ids)
    by_story_id = corpus.by_story_id
    if selector.kind == SelectorKind.ALL:
        selected = set(universe_ids)
    elif selector.kind in (SelectorKind.GENRE, SelectorKind.MANIFEST_GENRE):
        if not selector.genre:
            raise ValueError(f"{selector.kind} selector requires genre.")
        selected = {
            story_id
            for story_id in universe_ids
            if _document_has_genre(
                by_story_id[story_id], selector.genre, selector.membership_mode
            )
        }
    elif selector.kind == SelectorKind.STORY_LIST:
        selected = _known_story_ids(selector.story_ids, universe_set)
    elif selector.kind == SelectorKind.INCLUDE_EXCLUDE:
        selected = _known_story_ids(selector.include_story_ids, universe_set)
        selected -= set(selector.exclude_story_ids)
    elif selector.kind == SelectorKind.COMPLEMENT:
        if selector.base is None:
            raise ValueError("complement selector requires a base selector.")
        base_resolution = resolve_selector(corpus, universe_ids, selector.base)
        selected = universe_set - set(base_resolution.story_ids)
    else:
        raise ValueError(f"unsupported selector kind: {selector.kind!r}")
    ordered = tuple(story_id for story_id in universe_ids if story_id in selected)
    return SelectorResolution(
        label=selector.label or _selector_label(selector),
        selector=_selector_dict(selector),
        story_ids=ordered,
        story_count=len(ordered),
    )


def validate_reference_overlay_compatibility(spec: ComparisonSpec) -> None:
    """Raise if a reference-overlay spec would compare incommensurate values."""
    if spec.style != ComparisonStyle.REFERENCE_OVERLAY:
        return
    if spec.left_metric != spec.right_metric:
        raise ValueError(
            "reference_overlay requires identical left and right metric "
            "specifications."
        )
    if spec.term_form != "surface":
        raise ValueError("only term_form='surface' is supported before POS artifacts.")


def _validate_spec(spec: ComparisonSpec) -> None:
    if spec.universe.kind not in ("corpus", "story_list", "manifest"):
        raise ValueError(f"unsupported universe kind: {spec.universe.kind!r}")
    if spec.vocabulary.top_k is not None and spec.vocabulary.top_k < 1:
        raise ValueError("vocabulary.top_k must be >= 1 when provided.")
    if spec.vocabulary.min_document_count < 1:
        raise ValueError("vocabulary.min_document_count must be >= 1.")
    if spec.token_filter.min_length < 1:
        raise ValueError("token_filter.min_length must be >= 1.")
    if spec.term_form != "surface":
        raise ValueError(
            "only term_form='surface' is supported before lexical artifacts."
        )
    _validate_metric_denominator(spec.left_metric)
    _validate_metric_denominator(spec.right_metric)
    validate_reference_overlay_compatibility(spec)


def _validate_metric_denominator(metric: MetricSpec) -> None:
    effective = _effective_denominator(metric.name)
    if metric.denominator not in ("auto", effective):
        raise ValueError(
            f"{metric.name.value} supports denominator 'auto' or "
            f"{effective!r}; got {metric.denominator!r}."
        )


def _effective_denominator(metric_name: MetricName) -> str:
    if metric_name in (MetricName.RAW_COUNT, MetricName.DOCUMENT_COUNT):
        return "none"
    if metric_name == MetricName.PER_MILLION:
        return "included_tokens"
    if metric_name == MetricName.DOCUMENT_PERCENTAGE:
        return "documents"
    if metric_name == MetricName.MEAN_DOCUMENT_RELATIVE_FREQUENCY:
        return "included_tokens_per_document"
    if metric_name in (MetricName.MEAN_TFIDF, MetricName.TFIDF_CONTRAST):
        return "tfidf_l2_norm"
    raise ValueError(f"unsupported metric: {metric_name!r}")


def _resolve_universe(
    corpus: ComparisonCorpus, universe: UniverseSpec
) -> tuple[str, ...]:
    all_ids = tuple(document.story_id for document in corpus.documents)
    if universe.kind == "corpus" and not universe.story_ids:
        return all_ids
    all_set = set(all_ids)
    requested = _known_story_ids(universe.story_ids, all_set)
    return tuple(story_id for story_id in all_ids if story_id in requested)


def _known_story_ids(story_ids: Iterable[str], universe_set: set[str]) -> set[str]:
    requested = set(story_ids)
    unknown = sorted(requested - universe_set)
    if unknown:
        raise ValueError(
            f"selector references story_id(s) outside universe: {unknown!r}"
        )
    return requested


def _document_has_genre(
    document: ComparisonDocument, genre: str, membership_mode: MembershipMode
) -> bool:
    if membership_mode == MembershipMode.CANDIDATE:
        return genre in document.candidate_genres
    if membership_mode == MembershipMode.PRIMARY:
        return document.primary_genre == genre
    if membership_mode == MembershipMode.SELECTION:
        return genre in document.selection_genres
    raise ValueError(f"unsupported membership mode: {membership_mode!r}")


def _tokenize_universe(
    corpus: ComparisonCorpus, universe_ids: tuple[str, ...], token_filter: TokenFilter
) -> dict[str, tuple[str, ...]]:
    by_story_id = corpus.by_story_id
    return {
        story_id: tuple(_tokenize(by_story_id[story_id].text, token_filter))
        for story_id in universe_ids
    }


def _tokenize(text: str, token_filter: TokenFilter) -> list[str]:
    if not token_filter.include_stopwords and token_filter.lowercase:
        return [
            token
            for token in story_analysis.get_keywords(text)
            if len(token) >= token_filter.min_length
        ]
    tokens = re.findall(r"[A-Za-z]+", text)
    if token_filter.lowercase:
        tokens = [token.lower() for token in tokens]
    if not token_filter.include_stopwords:
        tokens = [
            token for token in tokens if token.lower() not in story_analysis._STOPWORDS
        ]
    return [token for token in tokens if len(token) >= token_filter.min_length]


def _metric_series(
    *,
    selected_ids: tuple[str, ...],
    tokenized: Mapping[str, tuple[str, ...]],
    metric: MetricSpec,
    tfidf_fit: TfidfFit | None,
) -> MetricSeries:
    raw_counts, document_counts = _support_counts(selected_ids, tokenized)
    token_denominator = sum(len(tokenized[story_id]) for story_id in selected_ids)
    document_denominator = len(selected_ids)

    if metric.name == MetricName.RAW_COUNT:
        values = {term: float(count) for term, count in raw_counts.items()}
    elif metric.name == MetricName.PER_MILLION:
        values = {
            term: (count / token_denominator * 1_000_000 if token_denominator else 0.0)
            for term, count in raw_counts.items()
        }
    elif metric.name == MetricName.DOCUMENT_COUNT:
        values = {term: float(count) for term, count in document_counts.items()}
    elif metric.name == MetricName.DOCUMENT_PERCENTAGE:
        values = {
            term: (
                count / document_denominator * 100.0 if document_denominator else 0.0
            )
            for term, count in document_counts.items()
        }
    elif metric.name == MetricName.MEAN_DOCUMENT_RELATIVE_FREQUENCY:
        values = _mean_document_relative_frequency(selected_ids, tokenized)
    elif metric.name in (MetricName.MEAN_TFIDF, MetricName.TFIDF_CONTRAST):
        if tfidf_fit is None:
            values = {}
        else:
            values = _tfidf_values(tfidf_fit, selected_ids, metric.name)
    else:
        raise ValueError(f"unsupported metric: {metric.name!r}")

    return MetricSeries(
        values=values,
        raw_counts=raw_counts,
        document_counts=document_counts,
        token_denominator=token_denominator,
        document_denominator=document_denominator,
        metric=metric,
    )


def _support_counts(
    selected_ids: tuple[str, ...], tokenized: Mapping[str, tuple[str, ...]]
) -> tuple[dict[str, int], dict[str, int]]:
    raw_counts: collections.Counter[str] = collections.Counter()
    document_counts: collections.Counter[str] = collections.Counter()
    for story_id in selected_ids:
        tokens = tokenized[story_id]
        raw_counts.update(tokens)
        document_counts.update(set(tokens))
    return dict(raw_counts), dict(document_counts)


def _mean_document_relative_frequency(
    selected_ids: tuple[str, ...], tokenized: Mapping[str, tuple[str, ...]]
) -> dict[str, float]:
    values: dict[str, float] = {}
    for story_id in selected_ids:
        tokens = tokenized[story_id]
        if not tokens:
            continue
        counts = collections.Counter(tokens)
        for term, count in counts.items():
            values[term] = values.get(term, 0.0) + count / len(tokens)
    denominator = len(selected_ids)
    if denominator == 0:
        return {}
    return {term: value / denominator for term, value in values.items()}


def _fit_tfidf(
    corpus: ComparisonCorpus,
    universe_ids: tuple[str, ...],
    token_filter: TokenFilter,
) -> TfidfFit | None:
    if not universe_ids:
        return None
    by_story_id = corpus.by_story_id
    texts = [by_story_id[story_id].text for story_id in universe_ids]
    vectorizer = TfidfVectorizer(
        tokenizer=lambda text: _tokenize(text, token_filter),
        preprocessor=lambda text: text,
        token_pattern=None,
    )
    try:
        matrix = vectorizer.fit_transform(texts)
    except ValueError as exc:
        if "empty vocabulary" in str(exc):
            return None
        raise
    return TfidfFit(
        terms=tuple(str(term) for term in vectorizer.get_feature_names_out()),
        matrix=matrix,
        index_by_id={story_id: i for i, story_id in enumerate(universe_ids)},
    )


def _tfidf_values(
    tfidf_fit: TfidfFit,
    selected_ids: tuple[str, ...],
    metric_name: MetricName,
) -> dict[str, float]:
    if not selected_ids:
        return {}
    matrix = tfidf_fit.matrix
    terms = tfidf_fit.terms
    selected_indices = [tfidf_fit.index_by_id[story_id] for story_id in selected_ids]
    selected_mean = np.asarray(matrix[selected_indices].mean(axis=0)).ravel()
    if metric_name == MetricName.TFIDF_CONTRAST:
        selected_set = set(selected_ids)
        complement_indices = [
            index
            for story_id, index in tfidf_fit.index_by_id.items()
            if story_id not in selected_set
        ]
        if not complement_indices:
            return {}
        complement_mean = np.asarray(matrix[complement_indices].mean(axis=0)).ravel()
        scores = selected_mean - complement_mean
    else:
        scores = selected_mean
    return {
        terms[i]: float(scores[i]) for i in range(len(terms)) if float(scores[i]) > 0.0
    }


def _select_vocabulary(
    left: MetricSeries, right: MetricSeries, vocabulary: VocabularySpec
) -> tuple[str, ...]:
    terms = set(left.values) | set(right.values)
    terms |= set(vocabulary.include_terms)
    terms -= set(vocabulary.exclude_terms)
    terms = {
        term
        for term in terms
        if max(left.document_counts.get(term, 0), right.document_counts.get(term, 0))
        >= vocabulary.min_document_count
    }
    if vocabulary.policy == VocabularyPolicy.ALL:
        selected = terms
    elif vocabulary.policy == VocabularyPolicy.TOP_LEFT:
        selected = _top_terms(terms, left.values, vocabulary.top_k)
    elif vocabulary.policy == VocabularyPolicy.TOP_RIGHT:
        selected = _top_terms(terms, right.values, vocabulary.top_k)
    elif vocabulary.policy == VocabularyPolicy.TOP_DIFFERENCE:
        selected = _top_terms(
            terms,
            {
                term: left.values.get(term, 0.0) - right.values.get(term, 0.0)
                for term in terms
            },
            vocabulary.top_k,
        )
    elif vocabulary.policy == VocabularyPolicy.TOP_ABSOLUTE_DIFFERENCE:
        selected = _top_terms(
            terms,
            {
                term: abs(left.values.get(term, 0.0) - right.values.get(term, 0.0))
                for term in terms
            },
            vocabulary.top_k,
        )
    elif vocabulary.policy == VocabularyPolicy.UNION_TOP:
        selected = _top_terms(terms, left.values, vocabulary.top_k) | _top_terms(
            terms, right.values, vocabulary.top_k
        )
    elif vocabulary.policy == VocabularyPolicy.INTERSECTION_TOP:
        selected = _top_terms(terms, left.values, vocabulary.top_k) & _top_terms(
            terms, right.values, vocabulary.top_k
        )
    else:
        raise ValueError(f"unsupported vocabulary policy: {vocabulary.policy!r}")
    selected |= set(vocabulary.include_terms)
    selected -= set(vocabulary.exclude_terms)
    return tuple(sorted(selected))


def _top_terms(
    terms: Iterable[str], values: Mapping[str, float], top_k: int | None
) -> set[str]:
    ranked = sorted(terms, key=lambda term: (-values.get(term, 0.0), term))
    if top_k is None:
        return set(ranked)
    return set(ranked[:top_k])


def _build_rows(
    terms: tuple[str, ...],
    left: MetricSeries,
    right: MetricSeries,
    ordering: OrderingSpec,
) -> list[ComparisonRow]:
    unsorted_rows = [
        ComparisonRow(
            term=term,
            display_order=0,
            left_value=left.values.get(term, 0.0),
            right_value=right.values.get(term, 0.0),
            left_raw_count=left.raw_counts.get(term, 0),
            right_raw_count=right.raw_counts.get(term, 0),
            left_document_count=left.document_counts.get(term, 0),
            right_document_count=right.document_counts.get(term, 0),
            left_token_denominator=left.token_denominator,
            right_token_denominator=right.token_denominator,
            left_document_denominator=left.document_denominator,
            right_document_denominator=right.document_denominator,
            signed_difference=left.values.get(term, 0.0) - right.values.get(term, 0.0),
            absolute_difference=abs(
                left.values.get(term, 0.0) - right.values.get(term, 0.0)
            ),
        )
        for term in terms
    ]
    rows = sorted(unsorted_rows, key=_row_sorter(ordering))
    return [
        dataclasses.replace(row, display_order=index + 1)
        for index, row in enumerate(rows)
    ]


def _row_sorter(ordering: OrderingSpec):
    explicit_index = {term: index for index, term in enumerate(ordering.explicit_terms)}
    if ordering.by == Ordering.LEFT_VALUE:
        return lambda row: (-row.left_value, row.term)
    if ordering.by == Ordering.RIGHT_VALUE:
        return lambda row: (-row.right_value, row.term)
    if ordering.by == Ordering.SIGNED_DIFFERENCE:
        return lambda row: (-row.signed_difference, row.term)
    if ordering.by == Ordering.ABSOLUTE_DIFFERENCE:
        return lambda row: (-row.absolute_difference, row.term)
    if ordering.by == Ordering.ALPHABETICAL:
        return lambda row: (row.term,)
    if ordering.by == Ordering.EXPLICIT:
        return lambda row: (explicit_index.get(row.term, len(explicit_index)), row.term)
    raise ValueError(f"unsupported ordering: {ordering.by!r}")


def _select_nway_vocabulary(
    common_reference: _ResolvedNWayReference | None,
    panels: tuple[_ResolvedNWayPanel, ...],
    vocabulary: NWayVocabularySpec,
) -> tuple[str, ...]:
    series_list = [panel.series for panel in panels] + [
        panel.reference.series for panel in panels if panel.reference is not None
    ]
    terms = set()
    for series in series_list:
        terms |= set(series.values)
    terms |= set(vocabulary.include_terms)
    terms -= set(vocabulary.exclude_terms)
    terms = {
        term
        for term in terms
        if max(series.document_counts.get(term, 0) for series in series_list)
        >= vocabulary.min_document_count
    }
    if vocabulary.policy == NWayVocabularyPolicy.REFERENCE_VALUE:
        reference_values = common_reference.series.values
        selected = _top_terms(
            terms & set(reference_values), reference_values, vocabulary.top_k
        )
    elif vocabulary.policy == NWayVocabularyPolicy.MAX_ABSOLUTE_DEVIATION:
        selected = _top_terms(
            terms,
            {
                term: max(
                    (abs(_panel_deviation(panel, term)) for panel in panels),
                    default=0.0,
                )
                for term in terms
            },
            vocabulary.top_k,
        )
    elif vocabulary.policy == NWayVocabularyPolicy.MAX_PANEL_VALUE:
        panel_terms = set()
        for panel in panels:
            panel_terms |= set(panel.series.values)
        selected = _top_terms(
            terms & panel_terms,
            {
                term: max(panel.series.values.get(term, 0.0) for panel in panels)
                for term in terms
            },
            vocabulary.top_k,
        )
    elif vocabulary.policy == NWayVocabularyPolicy.UNION_TOP:
        selected = set()
        if common_reference is not None:
            reference_values = common_reference.series.values
            selected = _top_terms(
                terms & set(reference_values), reference_values, vocabulary.top_k
            )
        for panel in panels:
            selected |= _top_terms(
                terms & set(panel.series.values),
                panel.series.values,
                vocabulary.top_k,
            )
    else:
        raise ValueError(f"unsupported N-way vocabulary policy: {vocabulary.policy!r}")
    selected |= set(vocabulary.include_terms)
    selected -= set(vocabulary.exclude_terms)
    return tuple(sorted(selected))


def _panel_deviation(panel: _ResolvedNWayPanel, term: str) -> float:
    return panel.series.values.get(term, 0.0) - panel.reference.series.values.get(
        term, 0.0
    )


def _build_nway_rows(
    terms: tuple[str, ...],
    common_reference: _ResolvedNWayReference | None,
    panels: tuple[_ResolvedNWayPanel, ...],
    ordering: NWayOrderingSpec,
) -> list[NWayComparisonRow]:
    unsorted_rows = []
    for term in terms:
        cells = tuple(_nway_cell(panel, term) for panel in panels)
        common = common_reference.series if common_reference is not None else None
        unsorted_rows.append(
            NWayComparisonRow(
                term=term,
                display_order=0,
                reference_value=(
                    common.values.get(term, 0.0) if common is not None else None
                ),
                reference_raw_count=(
                    common.raw_counts.get(term, 0) if common is not None else None
                ),
                reference_document_count=(
                    common.document_counts.get(term, 0) if common is not None else None
                ),
                reference_token_denominator=(
                    common.token_denominator if common is not None else None
                ),
                reference_document_denominator=(
                    common.document_denominator if common is not None else None
                ),
                panels=cells,
            )
        )
    rows = sorted(unsorted_rows, key=_nway_row_sorter(ordering))
    return [
        dataclasses.replace(row, display_order=index + 1)
        for index, row in enumerate(rows)
    ]


def _nway_cell(panel: _ResolvedNWayPanel, term: str) -> NWayPanelValue:
    value = panel.series.values.get(term, 0.0)
    reference = panel.reference
    reference_fields = {}
    deviation = None
    if reference is not None:
        reference_value = reference.series.values.get(term, 0.0)
        deviation = value - reference_value
        reference_fields = {
            "reference_key": reference.key,
            "reference_label": reference.resolution.label,
            "reference_value": reference_value,
            "reference_raw_count": reference.series.raw_counts.get(term, 0),
            "reference_document_count": reference.series.document_counts.get(term, 0),
            "reference_token_denominator": reference.series.token_denominator,
            "reference_document_denominator": reference.series.document_denominator,
        }
    return NWayPanelValue(
        panel_key=panel.key,
        panel_label=panel.resolution.label,
        value=value,
        deviation=deviation,
        raw_count=panel.series.raw_counts.get(term, 0),
        document_count=panel.series.document_counts.get(term, 0),
        token_denominator=panel.series.token_denominator,
        document_denominator=panel.series.document_denominator,
        panel_order=panel.order,
        **reference_fields,
    )


def _nway_row_sorter(ordering: NWayOrderingSpec):
    explicit_index = {term: index for index, term in enumerate(ordering.explicit_terms)}
    if ordering.by == NWayOrdering.REFERENCE_VALUE:
        return lambda row: (-row.reference_value, row.term)
    if ordering.by == NWayOrdering.MAX_ABSOLUTE_DEVIATION:
        return lambda row: (
            -max(
                (
                    abs(panel.deviation)
                    for panel in row.panels
                    if panel.deviation is not None
                ),
                default=0.0,
            ),
            row.term,
        )
    if ordering.by == NWayOrdering.MAX_PANEL_VALUE:
        return lambda row: (
            -max((panel.value for panel in row.panels), default=0.0),
            row.term,
        )
    if ordering.by == NWayOrdering.ALPHABETICAL:
        return lambda row: (row.term,)
    if ordering.by == NWayOrdering.EXPLICIT:
        return lambda row: (explicit_index.get(row.term, len(explicit_index)), row.term)
    raise ValueError(f"unsupported N-way ordering: {ordering.by!r}")


def story_id_fingerprint(story_ids: Iterable[str]) -> str:
    """Return a stable SHA-256 fingerprint for an ordered story-ID sequence."""
    digest = hashlib.sha256()
    for story_id in story_ids:
        digest.update(story_id.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _nway_manifest(
    *,
    corpus: ComparisonCorpus,
    spec: NWayComparisonSpec,
    universe_ids: tuple[str, ...],
    common_reference: _ResolvedNWayReference | None,
    panels: tuple[_ResolvedNWayPanel, ...],
    rows: list[NWayComparisonRow],
) -> dict[str, Any]:
    universe_fingerprint = story_id_fingerprint(universe_ids)
    metric = _metric_dict(spec.metric)
    overlap_records = []
    for index, left in enumerate(panels):
        for right in panels[index + 1 :]:
            intersection = sorted(
                set(left.resolution.story_ids) & set(right.resolution.story_ids)
            )
            overlap_records.append(
                {
                    "left_panel_key": left.key,
                    "right_panel_key": right.key,
                    "story_count": len(intersection),
                    "story_ids": intersection,
                }
            )
    base_overlap_records = []
    if spec.panel_mode == NWayPanelMode.COMPLEMENT:
        for index, left in enumerate(panels):
            for right in panels[index + 1 :]:
                intersection = sorted(
                    set(left.base_resolution.story_ids)
                    & set(right.base_resolution.story_ids)
                )
                base_overlap_records.append(
                    {
                        "left_panel_key": left.key,
                        "right_panel_key": right.key,
                        "story_count": len(intersection),
                        "story_ids": intersection,
                    }
                )
    overlapping_pairs = [record for record in overlap_records if record["story_count"]]
    covered = set()
    for panel in panels:
        covered |= set(panel.resolution.story_ids)

    complements = []
    for panel in panels:
        if panel.base_resolution is not None:
            complements.append(
                _complement_record(
                    role="panel",
                    panel_key=panel.key,
                    complement=panel.resolution,
                    base=panel.base_resolution,
                    universe_ids=universe_ids,
                    universe_fingerprint=universe_fingerprint,
                )
            )
        if spec.reference_policy == NWayReferencePolicy.PER_PANEL_COMPLEMENT:
            complements.append(
                _complement_record(
                    role="reference",
                    panel_key=panel.key,
                    complement=panel.reference.resolution,
                    base=panel.resolution,
                    universe_ids=universe_ids,
                    universe_fingerprint=universe_fingerprint,
                )
            )

    references = []
    if common_reference is not None:
        references.append(
            {
                "key": common_reference.key,
                "role": "common",
                "metric": metric,
                **_resolution_dict(common_reference.resolution),
            }
        )
    elif spec.reference_policy == NWayReferencePolicy.PER_PANEL_COMPLEMENT:
        for panel in panels:
            references.append(
                {
                    "key": panel.reference.key,
                    "role": "per_panel_complement",
                    "panel_key": panel.key,
                    "metric": metric,
                    **_resolution_dict(panel.reference.resolution),
                }
            )

    deviation_definition = {
        NWayReferencePolicy.NONE: None,
        NWayReferencePolicy.COMMON: "panel_value - reference_value",
        NWayReferencePolicy.PER_PANEL_COMPLEMENT: (
            "panel_value - reference_value, where each panel's reference is "
            "U - panel membership"
        ),
    }[NWayReferencePolicy(spec.reference_policy)]

    warnings = []
    if overlapping_pairs:
        warnings.append(
            f"panel selectors overlap in {len(overlapping_pairs)} pair(s); "
            "genre selectors are not assumed to be mutually exclusive."
        )
    empty_panels = [panel.key for panel in panels if not panel.resolution.story_ids]
    if empty_panels:
        warnings.append(f"panels with no member stories: {empty_panels!r}.")
    empty_references = sorted(
        {
            panel.reference.key
            for panel in panels
            if panel.reference is not None and not panel.reference.resolution.story_ids
        }
    )
    if empty_references:
        warnings.append(
            f"references with no member stories: {empty_references!r}; their "
            "deviations equal the panel values."
        )

    return {
        "schema_version": "lcats-nway-comparison-v2",
        "panel_mode": NWayPanelMode(spec.panel_mode).value,
        "reference_policy": NWayReferencePolicy(spec.reference_policy).value,
        "deviation_definition": deviation_definition,
        "corpus": {
            "source_path": corpus.source_path,
            "source_revision": corpus.source_revision,
        },
        "universe": {
            "kind": spec.universe.kind,
            "source_path": spec.universe.source_path,
            "source_revision": spec.universe.source_revision,
            "story_count": len(universe_ids),
            "fingerprint": universe_fingerprint,
            "story_ids": list(universe_ids),
        },
        "reference": (
            _resolution_dict(common_reference.resolution)
            if common_reference is not None
            else None
        ),
        "references": references,
        "panels": [
            {
                "key": panel.key,
                "order": panel.order,
                "reference_key": (
                    panel.reference.key if panel.reference is not None else None
                ),
                "base": (
                    _resolution_dict(panel.base_resolution)
                    if panel.base_resolution is not None
                    else None
                ),
                "metric": metric,
                **_resolution_dict(panel.resolution),
            }
            for panel in panels
        ],
        "panel_overlaps": overlap_records,
        "base_overlaps": base_overlap_records,
        "complements": complements,
        "membership": {
            "semantics": (
                "Panels are independent selections from one declared universe; "
                "they are not assumed to be disjoint or exhaustive."
            ),
            "partition_claim": False,
            "pairwise_disjoint": not overlapping_pairs,
            "covers_universe": covered == set(universe_ids),
        },
        "metric": metric,
        "commensurability": {
            "shared_metric": True,
            "shared_vocabulary": True,
            "shared_term_order": True,
            "shared_preprocessing": True,
            "tfidf_fit_scope": (
                "universe" if spec.metric.name == MetricName.MEAN_TFIDF else None
            ),
        },
        "preprocessing": {
            "term_form": spec.term_form,
            "token_filter": dataclasses.asdict(spec.token_filter),
            "tokenizer": (
                "lcats.analysis.story_analysis.get_keywords"
                if (
                    not spec.token_filter.include_stopwords
                    and spec.token_filter.lowercase
                    and spec.token_filter.min_length >= 3
                )
                else "lcats.visualize.comparison._tokenize"
            ),
            "stopword_policy": (
                "excluded" if not spec.token_filter.include_stopwords else "included"
            ),
        },
        "vocabulary": {
            **dataclasses.asdict(spec.vocabulary),
            "terms": [row.term for row in rows],
        },
        "ordering": dataclasses.asdict(spec.ordering),
        "warnings": warnings,
        "note": "Visual deviations are descriptive and are not significance tests.",
    }


def _complement_record(
    *,
    role: str,
    panel_key: str,
    complement: SelectorResolution,
    base: SelectorResolution,
    universe_ids: tuple[str, ...],
    universe_fingerprint: str,
) -> dict[str, Any]:
    universe_set = set(universe_ids)
    base_set = set(base.story_ids)
    complement_set = set(complement.story_ids)
    return {
        "role": role,
        "panel_key": panel_key,
        "construction": "U - S",
        "universe_fingerprint": universe_fingerprint,
        "universe_story_count": len(universe_ids),
        "base_label": base.label,
        "base_story_count": base.story_count,
        "complement_label": complement.label,
        "complement_story_count": complement.story_count,
        "verified_equals_universe_minus_base": complement_set
        == universe_set - base_set,
    }


def _manifest(
    *,
    corpus: ComparisonCorpus,
    spec: ComparisonSpec,
    universe_ids: tuple[str, ...],
    left_resolution: SelectorResolution,
    right_resolution: SelectorResolution,
    rows: list[ComparisonRow],
    warnings: list[str],
) -> dict[str, Any]:
    intersection = sorted(
        set(left_resolution.story_ids) & set(right_resolution.story_ids)
    )
    return {
        "schema_version": "lcats-comparison-v1",
        "corpus": {
            "source_path": corpus.source_path,
            "source_revision": corpus.source_revision,
        },
        "universe": {
            "kind": spec.universe.kind,
            "source_path": spec.universe.source_path,
            "source_revision": spec.universe.source_revision,
            "story_count": len(universe_ids),
            "story_ids": list(universe_ids),
        },
        "left": _resolution_dict(left_resolution),
        "right": _resolution_dict(right_resolution),
        "overlap": {
            "story_count": len(intersection),
            "story_ids": intersection,
        },
        "metrics": {
            "left": _metric_dict(spec.left_metric),
            "right": _metric_dict(spec.right_metric),
            "tfidf_fit_scope": (
                "universe"
                if (
                    spec.left_metric.name
                    in (MetricName.MEAN_TFIDF, MetricName.TFIDF_CONTRAST)
                    or spec.right_metric.name
                    in (MetricName.MEAN_TFIDF, MetricName.TFIDF_CONTRAST)
                )
                else None
            ),
        },
        "preprocessing": {
            "term_form": spec.term_form,
            "token_filter": dataclasses.asdict(spec.token_filter),
            "tokenizer": (
                "lcats.analysis.story_analysis.get_keywords"
                if (
                    not spec.token_filter.include_stopwords
                    and spec.token_filter.lowercase
                    and spec.token_filter.min_length >= 3
                )
                else "lcats.visualize.comparison._tokenize"
            ),
            "stopword_policy": (
                "excluded" if not spec.token_filter.include_stopwords else "included"
            ),
        },
        "vocabulary": {
            **dataclasses.asdict(spec.vocabulary),
            "terms": [row.term for row in rows],
        },
        "ordering": dataclasses.asdict(spec.ordering),
        "style": spec.style,
        "output_formats": list(spec.output_formats),
        "warnings": warnings,
        "note": "Visual differences and TF-IDF contrasts are not significance tests.",
    }


def _metric_dict(metric: MetricSpec) -> dict[str, Any]:
    return {
        "name": metric.name.value,
        "denominator": metric.denominator,
        "effective_denominator": _effective_denominator(metric.name),
    }


def _overlap_warnings(
    left_story_ids: tuple[str, ...], right_story_ids: tuple[str, ...]
) -> list[str]:
    overlap_count = len(set(left_story_ids) & set(right_story_ids))
    if overlap_count:
        return [
            f"left and right selectors overlap by {overlap_count} story_id(s); "
            "genre selectors are not assumed to be mutually exclusive."
        ]
    return []


def _selector_label(selector: Selector) -> str:
    if selector.kind in (SelectorKind.GENRE, SelectorKind.MANIFEST_GENRE):
        return f"{selector.membership_mode}:{selector.genre}"
    if selector.kind == SelectorKind.COMPLEMENT and selector.base is not None:
        return f"complement({selector.base.label or _selector_label(selector.base)})"
    return selector.kind.value


def _resolution_dict(resolution: SelectorResolution) -> dict[str, Any]:
    return {
        "label": resolution.label,
        "selector": resolution.selector,
        "story_ids": list(resolution.story_ids),
        "story_count": resolution.story_count,
    }


def _selector_dict(selector: Selector) -> dict[str, Any]:
    data = {
        "kind": selector.kind,
        "genre": selector.genre,
        "story_ids": list(selector.story_ids),
        "include_story_ids": list(selector.include_story_ids),
        "exclude_story_ids": list(selector.exclude_story_ids),
        "membership_mode": selector.membership_mode,
        "label": selector.label,
    }
    if selector.base is not None:
        data["base"] = _selector_dict(selector.base)
    return data
