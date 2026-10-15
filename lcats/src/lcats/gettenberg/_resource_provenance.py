"""Offline receipt identity validation shared by catalog and text consumers."""

import hashlib
import json

from lcats.gettenberg import _resource_io
from lcats.gettenberg import _resource_types

RECEIPT_LIMIT = 65536


def validate(value, receipt_sha256, sha256, size):
    """Validate bounded JSON receipt evidence and its claimed body identity.

    This validates metadata only. The consumer must independently verify the
    actual bytes under its own resource limits before using the receipt.
    """
    try:
        if not isinstance(value, dict) or type(size) is not int:
            raise ValueError("invalid receipt or artifact size")
        payload = _resource_types.canonical_json(value)
        if len(payload) > RECEIPT_LIMIT:
            raise ValueError("receipt exceeds byte budget")
        request = _resource_types.SourceRequest(
            value["source_uri"],
            value["request_url"],
            value["kind"],
            value["route_policy"],
        )
        receipt = _resource_io.Cache._receipt(value, request)
        if hashlib.sha256(payload).hexdigest() != receipt_sha256 or (sha256, size) != (
            receipt.sha256,
            receipt.size,
        ):
            raise ValueError("artifact and receipt identity disagree")
        return receipt
    except (KeyError, TypeError, ValueError) as exc:
        raise _resource_types.ResourceIntegrityError(
            "receipt_identity", str(exc)
        ) from exc


def artifact_value(source):
    """Return detached validated JSON metadata without reading original bytes."""
    if not isinstance(source, _resource_types.SourceArtifact) or not isinstance(
        source.receipt, _resource_types.RetrievalReceipt
    ):
        raise _resource_types.ResourceIntegrityError(
            "receipt_schema", "invalid source receipt"
        )
    try:
        payload = _resource_types.canonical_json(
            _resource_types.receipt_value(source.receipt)
        )
        if len(payload) > RECEIPT_LIMIT:
            raise ValueError("receipt exceeds byte budget")
        value = json.loads(payload)
    except (TypeError, ValueError) as exc:
        raise _resource_types.ResourceIntegrityError(
            "receipt_schema", str(exc)
        ) from exc
    validate(value, source.receipt_sha256, source.sha256, source.size)
    return value
