"""Schema helpers for standalone LCATS linguistic sidecars."""

from __future__ import annotations

import dataclasses
import hashlib
import importlib.metadata
import json
import os
import pathlib
import tempfile
from typing import Any, Optional

from lcats.analysis.event_role_world import surface_feature_extractor
from lcats import stories

SCHEMA_VERSION = "linguistics-sidecar-v1"
DETAIL_SCHEMA_VERSION = "linguistics-token-detail-v1"
DETAIL_V2_SCHEMA_VERSION = "linguistics-token-detail-v2"
EXTRACTOR_NAME = "lcats.analysis.linguistics"
EXTRACTOR_VERSION = "v1"
SIDECAR_FILENAME = "linguistics.json"
TOKEN_DETAIL_FILENAME = "linguistics.tokens.json"
TOKEN_DETAIL_VERSION_V1 = "v1"
TOKEN_DETAIL_VERSION_V2 = "v2"

VALID_UPOS_TAGS = frozenset(
    {
        "ADJ",
        "ADP",
        "ADV",
        "AUX",
        "CCONJ",
        "DET",
        "INTJ",
        "NOUN",
        "NUM",
        "PART",
        "PRON",
        "PROPN",
        "PUNCT",
        "SCONJ",
        "SPACE",
        "SYM",
        "VERB",
        "X",
    }
)


@dataclasses.dataclass(frozen=True)
class LinguisticsOptions:
    """Configuration that affects linguistic feature extraction."""

    backend_name: str = "spacy"
    model_name: str = ""
    include_token_detail: bool = False
    token_detail_version: str = TOKEN_DETAIL_VERSION_V1

    def __post_init__(self) -> None:
        if self.token_detail_version not in {
            TOKEN_DETAIL_VERSION_V1,
            TOKEN_DETAIL_VERSION_V2,
        }:
            raise ValueError(
                "token_detail_version must be "
                f"{TOKEN_DETAIL_VERSION_V1!r} or {TOKEN_DETAIL_VERSION_V2!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        data = {
            "backend_name": self.backend_name,
            "model_name": self.model_name,
            "include_token_detail": self.include_token_detail,
        }
        if (
            self.include_token_detail
            and self.token_detail_version != TOKEN_DETAIL_VERSION_V1
        ):
            data["token_detail_version"] = self.token_detail_version
        return data


@dataclasses.dataclass(frozen=True)
class ValidationFinding:
    """One structural validation finding for a linguistic sidecar."""

    path: str
    severity: str
    kind: str
    message: str


@dataclasses.dataclass(frozen=True)
class ValidationResult:
    """Validation outcome for one loaded linguistic sidecar value."""

    valid: bool
    findings: tuple[ValidationFinding, ...]


def analyze_story(
    story: stories.Story,
    backend: Any,
    options: Optional[LinguisticsOptions] = None,
) -> dict[str, Any]:
    """Analyze one loaded story and return aggregate linguistic data.

    This pure operation intentionally stops at story-level aggregate data.
    Token/dependency records remain available to the writer through the
    ``tokens`` key when requested, but callers that build the default compact
    sidecar should omit them.
    """
    options = options or LinguisticsOptions()
    features = surface_feature_extractor.extract_surface_features(
        story.body, backend, backend_name=options.backend_name
    )
    data = {
        "metrics": _metrics_from_features(features),
    }
    if options.include_token_detail:
        data["tokens"] = list(features.tokens)
        data["sentences"] = list(getattr(features, "sentence_records", ()))
    return data


def build_sidecar(
    *,
    story_data: dict[str, Any],
    story_path: pathlib.Path,
    backend: Any,
    options: LinguisticsOptions,
) -> tuple[dict[str, Any], Optional[dict[str, Any]]]:
    """Build compact sidecar data and optional token detail for one story."""
    story = stories.Story.from_dict(story_data)
    story.body = _coerce_text(story.body)
    analysis = analyze_story(story, backend, options)
    provenance = _provenance(
        story_path=story_path,
        body=story.body,
        backend=backend,
        options=options,
    )
    sidecar = {
        "schema_version": SCHEMA_VERSION,
        "lcats_id": story_identity(story_path),
        "story_path": _stable_path(story_path),
        "extractor": {
            "name": EXTRACTOR_NAME,
            "version": EXTRACTOR_VERSION,
        },
        "backend": provenance["backend"],
        "input": provenance["input"],
        "options": options.to_dict(),
        "metrics": analysis["metrics"],
    }
    detail = None
    if options.include_token_detail:
        if options.token_detail_version == TOKEN_DETAIL_VERSION_V2:
            detail = _build_v2_detail(
                sidecar=sidecar,
                sentences=analysis.get("sentences", []),
                body=story.body,
                options=options,
            )
        else:
            detail = {
                "schema_version": DETAIL_SCHEMA_VERSION,
                "lcats_id": sidecar["lcats_id"],
                "story_path": sidecar["story_path"],
                "extractor": sidecar["extractor"],
                "backend": sidecar["backend"],
                "input": sidecar["input"],
                "options": sidecar["options"],
                "tokens": analysis.get("tokens", []),
            }
    return sidecar, detail


def fingerprint_for_sidecar(sidecar: dict[str, Any]) -> dict[str, Any]:
    """Return the reproducibility fingerprint encoded by a sidecar."""
    return {
        "schema_version": sidecar.get("schema_version"),
        "extractor": sidecar.get("extractor"),
        "backend": sidecar.get("backend"),
        "input": sidecar.get("input"),
        "options": sidecar.get("options"),
    }


def expected_fingerprint(
    *,
    story_data: dict[str, Any],
    story_path: pathlib.Path,
    backend: Any,
    options: LinguisticsOptions,
) -> dict[str, Any]:
    """Return the fingerprint for current input/options without NLP analysis."""
    body = _coerce_text(story_data.get("body", ""))
    provenance = _provenance(
        story_path=story_path,
        body=body,
        backend=backend,
        options=options,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "extractor": {
            "name": EXTRACTOR_NAME,
            "version": EXTRACTOR_VERSION,
        },
        "backend": provenance["backend"],
        "input": provenance["input"],
        "options": options.to_dict(),
    }


def expected_detail_fingerprint(
    *,
    story_data: dict[str, Any],
    story_path: pathlib.Path,
    backend: Any,
    options: LinguisticsOptions,
) -> dict[str, Any]:
    """Return the token-detail fingerprint for current input/options."""
    fingerprint = expected_fingerprint(
        story_data=story_data,
        story_path=story_path,
        backend=backend,
        options=options,
    )
    schema_version = (
        DETAIL_V2_SCHEMA_VERSION
        if options.token_detail_version == TOKEN_DETAIL_VERSION_V2
        else DETAIL_SCHEMA_VERSION
    )
    return {**fingerprint, "schema_version": schema_version}


def validate_token_detail(
    data: Any,
    *,
    source_body: Optional[str] = None,
    compact_sidecar: Optional[dict[str, Any]] = None,
) -> ValidationResult:
    """Validate one loaded token-detail artifact.

    Both v1 and v2 remain readable. When ``source_body`` and
    ``compact_sidecar`` are supplied for v2, validation enforces source-span
    matching and compact count reconciliation.
    """
    if (
        isinstance(data, dict)
        and data.get("schema_version") == DETAIL_V2_SCHEMA_VERSION
    ):
        return validate_token_detail_v2(
            data, source_body=source_body, compact_sidecar=compact_sidecar
        )
    return validate_token_detail_v1(data)


def validate_token_detail_v1(data: Any) -> ValidationResult:
    """Validate one loaded ``linguistics-token-detail-v1`` object."""
    findings: list[ValidationFinding] = []
    if not isinstance(data, dict):
        findings.append(
            _finding(
                "$",
                "wrong_type",
                f"expected a JSON object, got {type(data).__name__}",
            )
        )
        return _result(findings)

    schema_version = data.get("schema_version")
    _require_string(data, "schema_version", "$.schema_version", findings)
    if _is_non_empty_string(schema_version) and schema_version != DETAIL_SCHEMA_VERSION:
        findings.append(
            _finding(
                "$.schema_version",
                "invalid_schema_version",
                f"expected {DETAIL_SCHEMA_VERSION!r}",
            )
        )

    for key in ("lcats_id", "story_path"):
        _require_string(data, key, f"$.{key}", findings)
    for key in ("extractor", "backend", "input", "options"):
        _require_mapping(data, key, f"$.{key}", findings)
    if "tokens" not in data:
        findings.append(_missing("$.tokens"))
    elif not isinstance(data["tokens"], list):
        findings.append(
            _finding(
                "$.tokens",
                "wrong_type",
                f"expected list, got {type(data['tokens']).__name__}",
            )
        )
    return _result(findings)


def validate_token_detail_v2(
    data: Any,
    *,
    source_body: Optional[str] = None,
    compact_sidecar: Optional[dict[str, Any]] = None,
) -> ValidationResult:
    """Validate one loaded ``linguistics-token-detail-v2`` object."""
    findings: list[ValidationFinding] = []
    if not isinstance(data, dict):
        findings.append(
            _finding(
                "$",
                "wrong_type",
                f"expected a JSON object, got {type(data).__name__}",
            )
        )
        return _result(findings)

    schema_version = data.get("schema_version")
    _require_string(data, "schema_version", "$.schema_version", findings)
    if (
        _is_non_empty_string(schema_version)
        and schema_version != DETAIL_V2_SCHEMA_VERSION
    ):
        findings.append(
            _finding(
                "$.schema_version",
                "invalid_schema_version",
                f"expected {DETAIL_V2_SCHEMA_VERSION!r}",
            )
        )

    for key in ("lcats_id", "story_path"):
        _require_string(data, key, f"$.{key}", findings)
    for key in ("extractor", "backend", "input", "options", "source", "provenance"):
        _require_mapping(data, key, f"$.{key}", findings)
    _validate_source_identity(data, source_body, compact_sidecar, findings)
    _validate_capabilities(data.get("provenance"), findings)

    sentences = data.get("sentences")
    if "sentences" not in data:
        findings.append(_missing("$.sentences"))
        return _result(findings)
    if not isinstance(sentences, list):
        findings.append(
            _finding(
                "$.sentences",
                "wrong_type",
                f"expected list, got {type(sentences).__name__}",
            )
        )
        return _result(findings)

    seen_global_indices: set[int] = set()
    last_global_index = 0
    last_sentence_end: Optional[int] = None
    token_count = 0
    expected_global_index = 1
    for expected_sentence_index, sentence in enumerate(sentences, start=1):
        sentence_path = f"$.sentences[{expected_sentence_index - 1}]"
        if not isinstance(sentence, dict):
            findings.append(
                _finding(
                    sentence_path,
                    "wrong_type",
                    f"expected object, got {type(sentence).__name__}",
                )
            )
            continue
        _validate_sentence_record(
            sentence,
            sentence_path,
            expected_sentence_index,
            source_body,
            findings,
        )
        sentence_start = sentence.get("start_char")
        sentence_end = sentence.get("end_char")
        if (
            isinstance(sentence_start, int)
            and last_sentence_end is not None
            and sentence_start < last_sentence_end
        ):
            findings.append(
                _finding(
                    f"{sentence_path}.start_char",
                    "non_monotonic_sentence_span",
                    "sentence spans must be in source order",
                )
            )
        if isinstance(sentence_end, int):
            last_sentence_end = sentence_end
        tokens = sentence.get("tokens")
        if not isinstance(tokens, list):
            continue
        _validate_sentence_contains_tokens(
            sentence,
            sentence_path,
            findings,
        )
        token_count += len(tokens)
        for expected_token_index, token in enumerate(tokens, start=1):
            token_path = f"{sentence_path}.tokens[{expected_token_index - 1}]"
            if not isinstance(token, dict):
                findings.append(
                    _finding(
                        token_path,
                        "wrong_type",
                        f"expected object, got {type(token).__name__}",
                    )
                )
                continue
            global_index = _validate_token_record(
                token,
                token_path,
                expected_sentence_index,
                expected_token_index,
                len(tokens),
                source_body,
                findings,
            )
            if global_index is None:
                continue
            if global_index != expected_global_index:
                findings.append(
                    _finding(
                        f"{token_path}.global_token_index",
                        "non_monotonic_global_token_index",
                        f"expected global_token_index {expected_global_index}",
                    )
                )
            if global_index in seen_global_indices:
                findings.append(
                    _finding(
                        f"{token_path}.global_token_index",
                        "duplicate_global_token_index",
                        f"duplicate global token index {global_index}",
                    )
                )
            if global_index <= last_global_index:
                findings.append(
                    _finding(
                        f"{token_path}.global_token_index",
                        "non_monotonic_global_token_index",
                        "global token indices must increase monotonically",
                    )
                )
            seen_global_indices.add(global_index)
            last_global_index = max(last_global_index, global_index)
            expected_global_index += 1

    if compact_sidecar is not None:
        metrics = compact_sidecar.get("metrics")
        if isinstance(metrics, dict) and isinstance(metrics.get("token_count"), int):
            expected = metrics["token_count"]
            if token_count != expected:
                findings.append(
                    _finding(
                        "$.sentences",
                        "compact_token_count_mismatch",
                        "v2 token count "
                        f"{token_count} does not match compact token_count {expected}",
                    )
                )
    return _result(findings)


def validate_sidecar(data: Any) -> ValidationResult:
    """Validate one loaded ``linguistics-sidecar-v1`` object."""
    findings: list[ValidationFinding] = []
    if not isinstance(data, dict):
        findings.append(
            _finding(
                "$",
                "wrong_type",
                f"expected a JSON object, got {type(data).__name__}",
            )
        )
        return _result(findings)

    schema_version = data.get("schema_version")
    _require_string(data, "schema_version", "$.schema_version", findings)
    if _is_non_empty_string(schema_version) and schema_version != SCHEMA_VERSION:
        findings.append(
            _finding(
                "$.schema_version",
                "invalid_schema_version",
                f"expected {SCHEMA_VERSION!r}",
            )
        )

    for key in ("lcats_id", "story_path"):
        _require_string(data, key, f"$.{key}", findings)
    for key in ("extractor", "backend", "input", "options", "metrics"):
        _require_mapping(data, key, f"$.{key}", findings)

    metrics = data.get("metrics")
    if isinstance(metrics, dict):
        for key in ("word_count", "sentence_count", "token_count"):
            _require_int(metrics, key, f"$.metrics.{key}", findings)
        for key in ("avg_sentence_length", "avg_word_length"):
            _require_number(metrics, key, f"$.metrics.{key}", findings)

    input_data = data.get("input")
    if isinstance(input_data, dict):
        _require_string(input_data, "body_sha256", "$.input.body_sha256", findings)
        _require_int(input_data, "body_char_count", "$.input.body_char_count", findings)

    extractor = data.get("extractor")
    if isinstance(extractor, dict):
        _require_string(extractor, "name", "$.extractor.name", findings)
        _require_string(extractor, "version", "$.extractor.version", findings)

    backend = data.get("backend")
    if isinstance(backend, dict):
        _require_string(backend, "name", "$.backend.name", findings)

    return _result(findings)


def _build_v2_detail(
    *,
    sidecar: dict[str, Any],
    sentences: list[Any],
    body: str,
    options: LinguisticsOptions,
) -> dict[str, Any]:
    cursor = 0
    sentence_rows: list[dict[str, Any]] = []
    global_token_index = 1
    for sentence_index, sentence in enumerate(sentences, start=1):
        token_rows: list[dict[str, Any]] = []
        sentence_start = getattr(sentence, "start_char", None)
        sentence_end = getattr(sentence, "end_char", None)
        for token_index, token in enumerate(getattr(sentence, "tokens", ()), start=1):
            token_start = getattr(token, "start_char", None)
            token_end = getattr(token, "end_char", None)
            if not isinstance(token_start, int) or not isinstance(token_end, int):
                token_start, token_end = _find_token_span(
                    body, getattr(token, "text", ""), cursor
                )
            if isinstance(token_end, int):
                cursor = token_end
            if not isinstance(sentence_start, int) and isinstance(token_start, int):
                sentence_start = token_start
            if isinstance(token_end, int):
                sentence_end = token_end
            token_rows.append(
                {
                    "token_index": token_index,
                    "global_token_index": global_token_index,
                    "start_char": token_start,
                    "end_char": token_end,
                    "text": getattr(token, "text", ""),
                    "lemma": getattr(token, "lemma", ""),
                    "upos": getattr(token, "upos", ""),
                    "xpos": getattr(token, "xpos", ""),
                    "feats": getattr(token, "feats", ""),
                    "head_index": getattr(token, "head_index", 0),
                    "deprel": getattr(token, "deprel", ""),
                }
            )
            global_token_index += 1
        sentence_rows.append(
            {
                "sentence_index": sentence_index,
                "start_char": (
                    sentence_start if isinstance(sentence_start, int) else None
                ),
                "end_char": sentence_end if isinstance(sentence_end, int) else None,
                "tokens": token_rows,
            }
        )

    capabilities = _capabilities_for_v2(sentence_rows)
    return {
        "schema_version": DETAIL_V2_SCHEMA_VERSION,
        "lcats_id": sidecar["lcats_id"],
        "story_path": sidecar["story_path"],
        "extractor": sidecar["extractor"],
        "backend": sidecar["backend"],
        "input": sidecar["input"],
        "options": options.to_dict(),
        "source": {
            "lcats_id": sidecar["lcats_id"],
            "body_sha256": sidecar["input"]["body_sha256"],
            "body_char_count": sidecar["input"]["body_char_count"],
            "source_path": sidecar["input"]["source_path"],
        },
        "provenance": {
            "backend": {
                **sidecar["backend"],
                "config": _backend_config(options),
            },
            "capabilities": capabilities,
        },
        "sentences": sentence_rows,
    }


def _find_token_span(
    body: str, text: str, cursor: int
) -> tuple[Optional[int], Optional[int]]:
    if not text:
        return None, None
    start = body.find(text, cursor)
    if start < 0:
        return None, None
    return start, start + len(text)


def _backend_config(options: LinguisticsOptions) -> dict[str, Any]:
    config = {"requested_model": options.model_name}
    if options.backend_name == "stanza":
        config["processors"] = "tokenize,pos,lemma,depparse"
    return config


def _capabilities_for_v2(sentences: list[dict[str, Any]]) -> dict[str, str]:
    has_sent_offsets = all(
        isinstance(sentence.get("start_char"), int)
        and isinstance(sentence.get("end_char"), int)
        for sentence in sentences
    )
    tokens = [token for sentence in sentences for token in sentence["tokens"]]
    has_token_offsets = all(
        isinstance(token.get("start_char"), int)
        and isinstance(token.get("end_char"), int)
        for token in tokens
    )
    return {
        "sentence_offsets": "required" if has_sent_offsets else "unavailable",
        "token_offsets": "required" if has_token_offsets else "unavailable",
        "lemma": "required",
        "upos": "required",
        "xpos": "optional",
        "morphology": "optional",
        "dependency_heads": "required",
        "dependency_relations": "required",
    }


def _validate_source_identity(
    data: dict[str, Any],
    source_body: Optional[str],
    compact_sidecar: Optional[dict[str, Any]],
    findings: list[ValidationFinding],
) -> None:
    source = data.get("source")
    if not isinstance(source, dict):
        return
    if source.get("lcats_id") != data.get("lcats_id"):
        findings.append(
            _finding(
                "$.source.lcats_id",
                "source_identity_mismatch",
                "source lcats_id must match top-level lcats_id",
            )
        )
    input_data = data.get("input")
    if isinstance(input_data, dict):
        for key in ("body_sha256", "body_char_count", "source_path"):
            if source.get(key) != input_data.get(key):
                findings.append(
                    _finding(
                        f"$.source.{key}",
                        "source_identity_mismatch",
                        f"source {key} must match input.{key}",
                    )
                )
    if source_body is not None:
        if source.get("body_sha256") != body_sha256(source_body):
            findings.append(
                _finding(
                    "$.source.body_sha256",
                    "source_hash_mismatch",
                    "source body hash does not match supplied body text",
                )
            )
        if source.get("body_char_count") != len(source_body):
            findings.append(
                _finding(
                    "$.source.body_char_count",
                    "source_length_mismatch",
                    "source body length does not match supplied body text",
                )
            )
    if compact_sidecar is not None:
        for key in ("lcats_id", "story_path", "input", "backend", "extractor"):
            if data.get(key) != compact_sidecar.get(key):
                findings.append(
                    _finding(
                        f"$.{key}",
                        "compact_identity_mismatch",
                        f"v2 {key} must match compact sidecar {key}",
                    )
                )


def _validate_capabilities(provenance: Any, findings: list[ValidationFinding]) -> None:
    if not isinstance(provenance, dict):
        return
    capabilities = provenance.get("capabilities")
    if not isinstance(capabilities, dict):
        findings.append(_missing("$.provenance.capabilities"))
        return
    for key in (
        "sentence_offsets",
        "token_offsets",
        "lemma",
        "upos",
        "xpos",
        "morphology",
        "dependency_heads",
        "dependency_relations",
    ):
        value = capabilities.get(key)
        if value not in {"required", "optional", "unavailable"}:
            findings.append(
                _finding(
                    f"$.provenance.capabilities.{key}",
                    "invalid_capability_status",
                    "expected required, optional, or unavailable",
                )
            )


def _validate_sentence_record(
    sentence: dict[str, Any],
    path: str,
    expected_sentence_index: int,
    source_body: Optional[str],
    findings: list[ValidationFinding],
) -> None:
    _require_int(sentence, "sentence_index", f"{path}.sentence_index", findings)
    _require_optional_int(sentence, "start_char", f"{path}.start_char", findings)
    _require_optional_int(sentence, "end_char", f"{path}.end_char", findings)
    if sentence.get("sentence_index") != expected_sentence_index:
        findings.append(
            _finding(
                f"{path}.sentence_index",
                "non_monotonic_sentence_index",
                f"expected sentence_index {expected_sentence_index}",
            )
        )
    _validate_span(
        sentence,
        path,
        source_body,
        allow_empty=not bool(sentence.get("tokens")),
        expected_text=None,
        findings=findings,
    )
    if "tokens" not in sentence:
        findings.append(_missing(f"{path}.tokens"))
    elif not isinstance(sentence["tokens"], list):
        findings.append(
            _finding(
                f"{path}.tokens",
                "wrong_type",
                f"expected list, got {type(sentence['tokens']).__name__}",
            )
        )
    elif sentence["tokens"]:
        root_count = sum(
            1
            for token in sentence["tokens"]
            if isinstance(token, dict) and token.get("head_index") == 0
        )
        if root_count != 1:
            findings.append(
                _finding(
                    f"{path}.tokens",
                    "invalid_root_count",
                    "each non-empty sentence must contain exactly one root token",
                )
            )


def _validate_token_record(
    token: dict[str, Any],
    path: str,
    expected_sentence_index: int,
    expected_token_index: int,
    sentence_token_count: int,
    source_body: Optional[str],
    findings: list[ValidationFinding],
) -> Optional[int]:
    for key in ("token_index", "global_token_index"):
        _require_int(token, key, f"{path}.{key}", findings)
    for key in ("start_char", "end_char"):
        _require_optional_int(token, key, f"{path}.{key}", findings)
    _require_string_field(token, "text", f"{path}.text", findings, allow_empty=False)
    _require_string_field(token, "lemma", f"{path}.lemma", findings, allow_empty=True)
    _require_string_field(token, "upos", f"{path}.upos", findings, allow_empty=False)
    _require_string_field(token, "xpos", f"{path}.xpos", findings, allow_empty=True)
    _require_string_field(token, "feats", f"{path}.feats", findings, allow_empty=True)
    _require_string_field(token, "deprel", f"{path}.deprel", findings, allow_empty=True)
    _require_int(token, "head_index", f"{path}.head_index", findings)
    if token.get("token_index") != expected_token_index:
        findings.append(
            _finding(
                f"{path}.token_index",
                "non_monotonic_token_index",
                f"expected token_index {expected_token_index}",
            )
        )
    if token.get("sentence_index") not in (None, expected_sentence_index):
        findings.append(
            _finding(
                f"{path}.sentence_index",
                "sentence_identity_mismatch",
                "token sentence_index must match containing sentence",
            )
        )
    upos = token.get("upos")
    if isinstance(upos, str) and upos and upos not in VALID_UPOS_TAGS:
        findings.append(
            _finding(
                f"{path}.upos",
                "invalid_upos",
                f"unrecognized UPOS value {upos!r}",
            )
        )
    head_index = token.get("head_index")
    if isinstance(head_index, int) and (
        head_index < 0 or head_index > sentence_token_count
    ):
        findings.append(
            _finding(
                f"{path}.head_index",
                "invalid_head_index",
                "head_index must be 0 or a sentence-local token index",
            )
        )
    _validate_span(
        token,
        path,
        source_body,
        allow_empty=False,
        expected_text=token.get("text"),
        findings=findings,
    )
    global_index = token.get("global_token_index")
    return global_index if isinstance(global_index, int) else None


def _validate_sentence_contains_tokens(
    sentence: dict[str, Any],
    path: str,
    findings: list[ValidationFinding],
) -> None:
    sentence_start = sentence.get("start_char")
    sentence_end = sentence.get("end_char")
    if not isinstance(sentence_start, int) or not isinstance(sentence_end, int):
        return
    tokens = sentence.get("tokens")
    if not isinstance(tokens, list):
        return
    for token_index, token in enumerate(tokens):
        if not isinstance(token, dict):
            continue
        token_start = token.get("start_char")
        token_end = token.get("end_char")
        if not isinstance(token_start, int) or not isinstance(token_end, int):
            continue
        if token_start < sentence_start or token_end > sentence_end:
            findings.append(
                _finding(
                    f"{path}.tokens[{token_index}].start_char",
                    "token_span_outside_sentence_span",
                    "token span must be contained by its sentence span",
                )
            )


def _validate_span(
    record: dict[str, Any],
    path: str,
    source_body: Optional[str],
    *,
    allow_empty: bool,
    expected_text: Optional[Any],
    findings: list[ValidationFinding],
) -> None:
    start = record.get("start_char")
    end = record.get("end_char")
    if start is None and end is None:
        return
    if start is None or end is None:
        findings.append(
            _finding(
                f"{path}.start_char",
                "invalid_span",
                "start_char and end_char must both be integers or both be null",
            )
        )
        return
    if not isinstance(start, int) or not isinstance(end, int):
        return
    if start < 0 or end < start or (start == end and not allow_empty):
        findings.append(
            _finding(
                f"{path}.start_char",
                "invalid_span",
                "span must be non-negative and end at or after start",
            )
        )
        return
    if source_body is None:
        return
    if end > len(source_body):
        findings.append(
            _finding(
                f"{path}.end_char",
                "span_out_of_bounds",
                "span end exceeds source body length",
            )
        )
        return
    if isinstance(expected_text, str) and source_body[start:end] != expected_text:
        findings.append(
            _finding(
                f"{path}.text",
                "source_span_mismatch",
                "token text does not match source span",
            )
        )


def dumps_json(data: Any) -> str:
    """Serialize JSON deterministically for sidecar files and summaries."""
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_json_atomic(path: pathlib.Path, data: Any) -> None:
    """Atomically publish deterministic JSON text at ``path``."""
    _atomic_write_text(path, dumps_json(data))


def load_json(path: pathlib.Path) -> Any:
    """Load JSON from ``path`` using UTF-8."""
    return json.loads(path.read_text(encoding="utf-8"))


def story_identity(story_path: pathlib.Path) -> str:
    """Return a stable LCATS story identity from bucket path components."""
    path = pathlib.Path(story_path)
    if path.name == "story.json" and not path.parent.name:
        return pathlib.Path.cwd().name
    if path.parent.parent.name:
        return f"{path.parent.parent.name}/{path.parent.name}"
    return path.parent.name


def body_sha256(body: str) -> str:
    """Return a deterministic SHA-256 hash for normalized story body text."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _provenance(
    *,
    story_path: pathlib.Path,
    body: str,
    backend: Any,
    options: LinguisticsOptions,
) -> dict[str, Any]:
    return {
        "backend": {
            "name": options.backend_name,
            "model": _backend_model(backend, options),
            "package_version": _backend_package_version(options.backend_name),
        },
        "input": {
            "body_sha256": body_sha256(body),
            "body_char_count": len(body),
            "source_path": _stable_path(story_path),
        },
    }


def _metrics_from_features(features: Any) -> dict[str, Any]:
    return {
        "word_count": features.word_count,
        "sentence_count": features.sentence_count,
        "avg_sentence_length": features.avg_sentence_length,
        "avg_word_length": features.avg_word_length,
        "token_count": len(features.tokens),
    }


def _backend_model(backend: Any, options: LinguisticsOptions) -> str:
    if options.model_name:
        return options.model_name
    if options.backend_name == "stanza":
        return "en"
    nlp = getattr(backend, "_nlp", None)
    meta = getattr(nlp, "meta", None)
    if isinstance(meta, dict) and meta.get("name"):
        version = meta.get("version", "")
        return f"{meta['name']}@{version}" if version else str(meta["name"])
    return ""


def _backend_package_version(backend_name: str) -> str:
    package_name = {"spacy": "spacy", "stanza": "stanza"}.get(backend_name)
    if package_name is None:
        return ""
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return ""


def _stable_path(path: pathlib.Path) -> str:
    return pathlib.Path(path).as_posix()


def _coerce_text(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    return str(value)


def _atomic_write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def _result(findings: list[ValidationFinding]) -> ValidationResult:
    return ValidationResult(valid=not findings, findings=tuple(findings))


def _finding(path: str, kind: str, message: str) -> ValidationFinding:
    return ValidationFinding(path=path, severity="error", kind=kind, message=message)


def _missing(path: str) -> ValidationFinding:
    return _finding(path, "missing_required_field", "missing required field")


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _require_string(
    data: dict[str, Any], key: str, path: str, findings: list[ValidationFinding]
) -> None:
    if key not in data:
        findings.append(_missing(path))
    elif not _is_non_empty_string(data[key]):
        findings.append(
            _finding(
                path,
                "wrong_type",
                f"expected non-empty string, got {type(data[key]).__name__}",
            )
        )


def _require_string_field(
    data: dict[str, Any],
    key: str,
    path: str,
    findings: list[ValidationFinding],
    *,
    allow_empty: bool,
) -> None:
    if key not in data:
        findings.append(_missing(path))
        return
    if not isinstance(data[key], str):
        findings.append(
            _finding(
                path,
                "wrong_type",
                f"expected string, got {type(data[key]).__name__}",
            )
        )
    elif not allow_empty and not data[key]:
        findings.append(
            _finding(
                path,
                "empty_string",
                "expected non-empty string",
            )
        )


def _require_mapping(
    data: dict[str, Any], key: str, path: str, findings: list[ValidationFinding]
) -> None:
    if key not in data:
        findings.append(_missing(path))
    elif not isinstance(data[key], dict):
        findings.append(
            _finding(
                path, "wrong_type", f"expected object, got {type(data[key]).__name__}"
            )
        )


def _require_int(
    data: dict[str, Any], key: str, path: str, findings: list[ValidationFinding]
) -> None:
    if key not in data:
        findings.append(_missing(path))
    elif not isinstance(data[key], int):
        findings.append(
            _finding(
                path, "wrong_type", f"expected int, got {type(data[key]).__name__}"
            )
        )


def _require_optional_int(
    data: dict[str, Any], key: str, path: str, findings: list[ValidationFinding]
) -> None:
    if key not in data:
        findings.append(_missing(path))
    elif data[key] is not None and not isinstance(data[key], int):
        findings.append(
            _finding(
                path,
                "wrong_type",
                f"expected int or null, got {type(data[key]).__name__}",
            )
        )


def _require_number(
    data: dict[str, Any], key: str, path: str, findings: list[ValidationFinding]
) -> None:
    if key not in data:
        findings.append(_missing(path))
    elif not isinstance(data[key], (int, float)):
        findings.append(
            _finding(
                path, "wrong_type", f"expected number, got {type(data[key]).__name__}"
            )
        )
