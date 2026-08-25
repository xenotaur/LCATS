"""Derived lexical materialized views for rich linguistic token detail."""

from __future__ import annotations

import collections
import dataclasses
import hashlib
import time
from typing import Any, Iterable, Optional

from lcats.analysis.linguistics import sidecar

SCHEMA_VERSION = "linguistics-lexicon-v1"
DERIVATION_NAME = "lcats.analysis.linguistics.lexicon"
DERIVATION_VERSION = "v1"
LEXICON_FILENAME = "linguistics.lexicon.json"


@dataclasses.dataclass(frozen=True)
class LexiconIndex:
    """Query helper over a materialized lexical artifact."""

    tuple_counts: dict[tuple[str, str, str], int]
    surface_counts: dict[str, int]
    lemma_counts: dict[str, int]
    upos_counts: dict[str, int]

    @classmethod
    def from_artifact(cls, data: dict[str, Any]) -> "LexiconIndex":
        tuple_counts: dict[tuple[str, str, str], int] = {}
        surface_counts: dict[str, int] = {}
        lemma_counts: dict[str, int] = {}
        upos_counts: dict[str, int] = {}
        for row in data.get("counts", []):
            if not isinstance(row, dict):
                continue
            surface = row.get("surface")
            lemma = row.get("lemma")
            upos = row.get("upos")
            count = row.get("count")
            if (
                not isinstance(surface, str)
                or not isinstance(lemma, str)
                or not isinstance(upos, str)
                or not _is_integer(count)
            ):
                continue
            key = (surface, lemma, upos)
            tuple_counts[key] = tuple_counts.get(key, 0) + count
            surface_counts[surface] = surface_counts.get(surface, 0) + count
            lemma_counts[lemma] = lemma_counts.get(lemma, 0) + count
            upos_counts[upos] = upos_counts.get(upos, 0) + count
        return cls(
            tuple_counts=tuple_counts,
            surface_counts=surface_counts,
            lemma_counts=lemma_counts,
            upos_counts=upos_counts,
        )

    def tuple_count(self, surface: str, lemma: str, upos: str) -> int:
        return self.tuple_counts.get((surface, lemma, upos), 0)

    def surface_count(self, surface: str) -> int:
        return self.surface_counts.get(surface, 0)

    def lemma_count(self, lemma: str) -> int:
        return self.lemma_counts.get(lemma, 0)

    def upos_count(self, upos: str) -> int:
        return self.upos_counts.get(upos, 0)


def build_lexicon(token_detail: dict[str, Any]) -> dict[str, Any]:
    """Build deterministic ``linguistics-lexicon-v1`` data from v2 detail."""
    if token_detail.get("schema_version") != sidecar.DETAIL_V2_SCHEMA_VERSION:
        raise ValueError("linguistics lexicon requires token-detail-v2 input")

    counter: collections.Counter[tuple[str, str, str]] = collections.Counter()
    token_count = 0
    sentences = token_detail.get("sentences", [])
    for sentence in sentences:
        if not isinstance(sentence, dict):
            continue
        tokens = sentence.get("tokens", [])
        if not isinstance(tokens, list):
            continue
        for token in tokens:
            if not isinstance(token, dict):
                continue
            surface = _string_field(token, "text")
            lemma = _string_field(token, "lemma")
            upos = _string_field(token, "upos")
            counter[(surface, lemma, upos)] += 1
            token_count += 1

    rows = [
        {
            "surface": surface,
            "lemma": lemma,
            "upos": upos,
            "count": count,
        }
        for (surface, lemma, upos), count in sorted(counter.items())
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "lcats_id": token_detail["lcats_id"],
        "story_path": token_detail["story_path"],
        "source_token_detail": _source_token_detail_record(token_detail),
        "derivation": {
            "name": DERIVATION_NAME,
            "version": DERIVATION_VERSION,
            "generation_policy": "no_stopword_or_pos_filtering",
        },
        "denominators": {
            "token_count": token_count,
            "sentence_count": len(sentences) if isinstance(sentences, list) else 0,
            "lexical_row_count": len(rows),
        },
        "counts": rows,
    }


def validate_lexicon(
    data: Any,
    *,
    source_token_detail: Optional[dict[str, Any]] = None,
) -> sidecar.ValidationResult:
    """Validate a loaded ``linguistics-lexicon-v1`` artifact."""
    findings: list[sidecar.ValidationFinding] = []
    if not isinstance(data, dict):
        findings.append(
            _finding(
                "$", "wrong_type", f"expected a JSON object, got {type(data).__name__}"
            )
        )
        return _result(findings)

    if data.get("schema_version") != SCHEMA_VERSION:
        findings.append(
            _finding(
                "$.schema_version",
                "invalid_schema_version",
                f"expected {SCHEMA_VERSION!r}",
            )
        )
    for key in ("lcats_id", "story_path"):
        if not isinstance(data.get(key), str) or not data.get(key):
            findings.append(
                _finding(f"$.{key}", "wrong_type", "expected non-empty string")
            )
    for key in ("source_token_detail", "derivation", "denominators"):
        if not isinstance(data.get(key), dict):
            findings.append(_finding(f"$.{key}", "wrong_type", "expected object"))

    _validate_source_token_detail(data, source_token_detail, findings)
    _validate_derivation(data.get("derivation"), findings)
    rows = _validate_rows(data.get("counts"), findings)
    _validate_denominators(data.get("denominators"), rows, findings)

    if source_token_detail is not None:
        try:
            regenerated = build_lexicon(source_token_detail)
        except Exception as error:  # noqa: BLE001 - report as validation finding.
            findings.append(
                _finding(
                    "$",
                    "source_regeneration_failed",
                    f"could not regenerate from source token detail: {error}",
                )
            )
        else:
            if sidecar.dumps_json(data) != sidecar.dumps_json(regenerated):
                findings.append(
                    _finding(
                        "$",
                        "regeneration_mismatch",
                        "lexicon does not exactly regenerate from source token detail",
                    )
                )

    return _result(findings)


def fingerprint_for_lexicon(data: dict[str, Any]) -> dict[str, Any]:
    """Return the reproducibility fingerprint encoded by a lexicon artifact."""
    return {
        "schema_version": data.get("schema_version"),
        "source_token_detail": data.get("source_token_detail"),
        "derivation": data.get("derivation"),
    }


def expected_fingerprint(token_detail: dict[str, Any]) -> dict[str, Any]:
    """Return the expected lexicon fingerprint for one v2 token-detail value."""
    return {
        "schema_version": SCHEMA_VERSION,
        "source_token_detail": _source_token_detail_record(token_detail),
        "derivation": {
            "name": DERIVATION_NAME,
            "version": DERIVATION_VERSION,
            "generation_policy": "no_stopword_or_pos_filtering",
        },
    }


def benchmark_queries(
    data: dict[str, Any],
    queries: Iterable[dict[str, str]],
) -> dict[str, Any]:
    """Run representative indexed count lookups and return timing metadata."""
    query_list = tuple(queries)
    start_ns = time.perf_counter_ns()
    index = LexiconIndex.from_artifact(data)
    results: list[int] = []
    for query in query_list:
        field = query.get("field")
        value = query.get("value", "")
        if field == "surface":
            results.append(index.surface_count(value))
        elif field == "lemma":
            results.append(index.lemma_count(value))
        elif field == "upos":
            results.append(index.upos_count(value))
        else:
            results.append(0)
    elapsed_ns = time.perf_counter_ns() - start_ns
    denominators = data.get("denominators", {})
    token_count = (
        _non_negative_integer(denominators.get("token_count"))
        if isinstance(denominators, dict)
        else 0
    )
    counts = data.get("counts", [])
    row_count = len(counts) if isinstance(counts, list) else 0
    token_scan_row_visits = token_count * len(query_list)
    indexed_row_visits = row_count + len(query_list)
    return {
        "query_count": len(query_list),
        "token_row_count": token_count,
        "lexicon_row_count": row_count,
        "token_scan_row_visits": token_scan_row_visits,
        "indexed_row_visits": indexed_row_visits,
        "estimated_row_visits_saved": token_scan_row_visits - indexed_row_visits,
        "elapsed_ns": elapsed_ns,
        "results": results,
    }


def token_detail_sha256(token_detail: dict[str, Any]) -> str:
    """Return a content hash for canonical token-detail JSON."""
    return hashlib.sha256(sidecar.dumps_json(token_detail).encode("utf-8")).hexdigest()


def _non_negative_integer(value: Any) -> int:
    if _is_integer(value) and value >= 0:
        return value
    return 0


def _source_token_detail_record(token_detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": token_detail.get("schema_version"),
        "sha256": token_detail_sha256(token_detail),
        "lcats_id": token_detail.get("lcats_id"),
        "story_path": token_detail.get("story_path"),
        "extractor": token_detail.get("extractor"),
        "backend": token_detail.get("backend"),
        "input": token_detail.get("input"),
        "options": token_detail.get("options"),
    }


def _validate_source_token_detail(
    data: dict[str, Any],
    source_token_detail: Optional[dict[str, Any]],
    findings: list[sidecar.ValidationFinding],
) -> None:
    source = data.get("source_token_detail")
    if not isinstance(source, dict):
        return
    for key in ("schema_version", "sha256", "lcats_id", "story_path"):
        if not isinstance(source.get(key), str) or not source.get(key):
            findings.append(
                _finding(
                    f"$.source_token_detail.{key}",
                    "wrong_type",
                    "expected non-empty string",
                )
            )
    for key in ("extractor", "backend", "input", "options"):
        if not isinstance(source.get(key), dict):
            findings.append(
                _finding(
                    f"$.source_token_detail.{key}", "wrong_type", "expected object"
                )
            )
    if source.get("schema_version") != sidecar.DETAIL_V2_SCHEMA_VERSION:
        findings.append(
            _finding(
                "$.source_token_detail.schema_version",
                "invalid_source_schema_version",
                f"expected {sidecar.DETAIL_V2_SCHEMA_VERSION!r}",
            )
        )
    if source.get("lcats_id") != data.get("lcats_id"):
        findings.append(
            _finding(
                "$.source_token_detail.lcats_id",
                "source_identity_mismatch",
                "source lcats_id must match top-level lcats_id",
            )
        )
    if source.get("story_path") != data.get("story_path"):
        findings.append(
            _finding(
                "$.source_token_detail.story_path",
                "source_identity_mismatch",
                "source story_path must match top-level story_path",
            )
        )
    if source_token_detail is not None:
        expected = _source_token_detail_record(source_token_detail)
        if source != expected:
            findings.append(
                _finding(
                    "$.source_token_detail",
                    "source_token_detail_mismatch",
                    "source token-detail fingerprint does not match supplied detail",
                )
            )


def _validate_derivation(
    derivation: Any, findings: list[sidecar.ValidationFinding]
) -> None:
    if not isinstance(derivation, dict):
        return
    expected = {
        "name": DERIVATION_NAME,
        "version": DERIVATION_VERSION,
        "generation_policy": "no_stopword_or_pos_filtering",
    }
    for key, value in expected.items():
        if derivation.get(key) != value:
            findings.append(
                _finding(
                    f"$.derivation.{key}",
                    "invalid_derivation",
                    f"expected {value!r}",
                )
            )


def _validate_rows(
    rows: Any, findings: list[sidecar.ValidationFinding]
) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        findings.append(_finding("$.counts", "wrong_type", "expected list"))
        return []
    valid_rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    previous_key: Optional[tuple[str, str, str]] = None
    for index, row in enumerate(rows):
        path = f"$.counts[{index}]"
        if not isinstance(row, dict):
            findings.append(
                _finding(
                    path, "wrong_type", f"expected object, got {type(row).__name__}"
                )
            )
            continue
        for key in ("surface", "lemma", "upos"):
            if not isinstance(row.get(key), str):
                findings.append(
                    _finding(f"{path}.{key}", "wrong_type", "expected string")
                )
        count = row.get("count")
        if not _is_integer(count):
            findings.append(_finding(f"{path}.count", "wrong_type", "expected integer"))
            continue
        if count < 0:
            findings.append(
                _finding(
                    f"{path}.count", "negative_count", "count must be non-negative"
                )
            )
        if all(isinstance(row.get(key), str) for key in ("surface", "lemma", "upos")):
            sort_key = (row["surface"], row["lemma"], row["upos"])
            if sort_key in seen:
                findings.append(
                    _finding(path, "duplicate_count_key", "duplicate lexical count key")
                )
            if previous_key is not None and sort_key < previous_key:
                findings.append(
                    _finding(
                        path, "non_monotonic_count_key", "counts must be sorted by key"
                    )
                )
            seen.add(sort_key)
            previous_key = sort_key
            valid_rows.append(row)
    return valid_rows


def _validate_denominators(
    denominators: Any,
    rows: list[dict[str, Any]],
    findings: list[sidecar.ValidationFinding],
) -> None:
    if not isinstance(denominators, dict):
        return
    for key in ("token_count", "sentence_count", "lexical_row_count"):
        if not _is_integer(denominators.get(key)):
            findings.append(
                _finding(f"$.denominators.{key}", "wrong_type", "expected integer")
            )
        elif denominators[key] < 0:
            findings.append(
                _finding(
                    f"$.denominators.{key}",
                    "negative_denominator",
                    "denominator must be non-negative",
                )
            )
    token_total = sum(
        row.get("count", 0) for row in rows if _is_integer(row.get("count"))
    )
    if (
        _is_integer(denominators.get("token_count"))
        and denominators["token_count"] != token_total
    ):
        findings.append(
            _finding(
                "$.denominators.token_count",
                "token_count_mismatch",
                "token_count must equal the sum of lexical row counts",
            )
        )
    if _is_integer(denominators.get("lexical_row_count")) and denominators[
        "lexical_row_count"
    ] != len(rows):
        findings.append(
            _finding(
                "$.denominators.lexical_row_count",
                "lexical_row_count_mismatch",
                "lexical_row_count must equal the number of count rows",
            )
        )


def _string_field(data: dict[str, Any], key: str) -> str:
    value = data.get(key, "")
    return value if isinstance(value, str) else ""


def _is_integer(value: Any) -> bool:
    return type(value) is int


def _result(
    findings: list[sidecar.ValidationFinding],
) -> sidecar.ValidationResult:
    return sidecar.ValidationResult(valid=not findings, findings=tuple(findings))


def _finding(path: str, kind: str, message: str) -> sidecar.ValidationFinding:
    return sidecar.ValidationFinding(
        path=path, severity="error", kind=kind, message=message
    )
