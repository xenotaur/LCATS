"""Bound catalog-generation provenance without coupling lifecycle to networking."""

from lcats.gettenberg import _resource_provenance
from lcats.gettenberg import _resource_types
from lcats.gettenberg import errors


def acquired(source):
    """Validate archive-kind receipt metadata before copying or building input."""
    try:
        value = _resource_provenance.artifact_value(source)
        if value["kind"] != "archive":
            raise errors.CatalogInputError(
                "catalog input requires an archive-kind SourceArtifact"
            )
        return {
            "kind": "acquired_archive",
            "receipt_sha256": source.receipt_sha256,
            "receipt": value,
        }
    except _resource_types.ResourceError as exc:
        raise errors.CatalogLifecycleError(
            f"invalid acquisition provenance: {exc}"
        ) from exc


def validate(source, sha256, size, version):
    """Enforce the same receipt/body binding on persisted manifests and new input."""
    if not isinstance(source, dict):
        raise errors.CatalogLifecycleError("missing catalog source provenance")
    if source.get("kind") == "local_archive":
        if (
            set(source) != {"kind", "input_path", "retrieved_at", "http_etag"}
            or not isinstance(source["input_path"], str)
            or source["retrieved_at"] is not None
            or source["http_etag"] is not None
        ):
            raise errors.CatalogLifecycleError("invalid local source provenance")
        try:
            source["input_path"].encode("utf-8")
        except UnicodeError as exc:
            raise errors.CatalogLifecycleError("invalid local source path") from exc
        return
    if (
        version != 2
        or source.get("kind") != "acquired_archive"
        or set(source) != {"kind", "receipt_sha256", "receipt"}
    ):
        raise errors.CatalogLifecycleError("unsupported catalog source provenance")
    try:
        receipt = _resource_provenance.validate(
            source["receipt"], source["receipt_sha256"], sha256, size
        )
        if receipt.kind != "archive":
            raise errors.CatalogLifecycleError("catalog receipt is not archive-kind")
    except _resource_types.ResourceError as exc:
        raise errors.CatalogLifecycleError(
            f"invalid acquisition provenance: {exc}"
        ) from exc
