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
EXTRACTOR_NAME = "lcats.analysis.linguistics"
EXTRACTOR_VERSION = "v1"
SIDECAR_FILENAME = "linguistics.json"
TOKEN_DETAIL_FILENAME = "linguistics.tokens.json"


@dataclasses.dataclass(frozen=True)
class LinguisticsOptions:
    """Configuration that affects linguistic feature extraction."""

    backend_name: str = "spacy"
    model_name: str = ""
    include_token_detail: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend_name": self.backend_name,
            "model_name": self.model_name,
            "include_token_detail": self.include_token_detail,
        }


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
    return {**fingerprint, "schema_version": DETAIL_SCHEMA_VERSION}


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


def validate_token_detail(data: Any) -> ValidationResult:
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
