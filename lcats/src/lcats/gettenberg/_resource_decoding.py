"""Offline original-byte verification, bounded containers and strict text decoding."""

import dataclasses
import hashlib
import itertools
import pathlib

from lcats.gettenberg import _decode_types
from lcats.gettenberg import _lifecycle_io
from lcats.gettenberg import _resource_containers
from lcats.gettenberg import _resource_encoding
from lcats.gettenberg import _resource_io
from lcats.gettenberg import _resource_types


def _source(source, options):
    """Read one bounded immutable snapshot and validate its provenance binding."""
    if isinstance(source, bytes):
        if len(source) > options.max_source_bytes:
            raise _decode_types.ResourceDecodeError(
                "source_limit", "original bytes exceed source limit"
            )
        return source, ()
    if not isinstance(source, _resource_types.SourceArtifact):
        raise _resource_types.ResourceInputError(
            "invalid_decode_source", "use bytes or SourceArtifact"
        )
    receipt = source.receipt
    if not isinstance(receipt, _resource_types.RetrievalReceipt):
        raise _resource_types.ResourceIntegrityError(
            "receipt_schema", "invalid source receipt"
        )
    # Validate the same receipt schema used for cache reads, including header
    # bounds/duplicates and origin identity, before using any declaration.
    try:
        value = dataclasses.asdict(receipt)
        value["headers"] = [list(pair) for pair in receipt.headers]
        value["redirects"] = list(receipt.redirects)
        request = _resource_types.SourceRequest(
            receipt.source_uri, receipt.request_url, receipt.kind, receipt.route_policy
        )
        _resource_io.Cache._receipt(value, request)
        serialized = _resource_types.canonical_json(value)
    except (TypeError, ValueError) as exc:
        raise _resource_types.ResourceIntegrityError(
            "receipt_schema", "invalid source receipt"
        ) from exc
    if hashlib.sha256(serialized).hexdigest() != source.receipt_sha256 or (
        source.sha256,
        source.size,
    ) != (receipt.sha256, receipt.size):
        raise _resource_types.ResourceIntegrityError(
            "receipt_hash", "artifact and receipt identity disagree"
        )
    with _resource_io.translated_errors():
        path = pathlib.Path(source.path)
        with _lifecycle_io._source(path) as (stream, before):
            if before.st_size > options.max_source_bytes:
                raise _decode_types.ResourceDecodeError(
                    "source_limit", "original file exceeds source limit"
                )
            data = stream.read(options.max_source_bytes + 1)
            _lifecycle_io._stable(path, stream, before)
    if len(data) > options.max_source_bytes:
        raise _decode_types.ResourceDecodeError(
            "source_limit", "original file exceeds source limit"
        )
    if len(data) != source.size or hashlib.sha256(data).hexdigest() != source.sha256:
        raise _resource_types.ResourceIntegrityError(
            "body_hash", "original file changed before decoding"
        )
    return data, receipt.headers


def decode_text(source, *, options=_decode_types.DecodeOptions(), catalog_formats=()):
    """Decode original bytes without network, extraction writes or source mutation.

    Args:
        source: Immutable bytes or a SourceArtifact returned by ResourceStore.
        options: Immutable DecodeOptions controlling encoding/container and limits.
        catalog_formats: Tuple of original MIME claims for this resource, if known.

    Returns:
        Immutable DecodedText containing plain text or unmodified HTML markup.

    Raises:
        ResourceInputError: Invalid caller options or declaration argument shape.
        ResourceIntegrityError: Artifact bytes or receipt no longer match.
        ResourceDecodeError: Unsupported, ambiguous, corrupt or over-limit input.
    """
    if (
        not isinstance(options, _decode_types.DecodeOptions)
        or not isinstance(catalog_formats, tuple)
        or any(not isinstance(value, str) for value in catalog_formats)
    ):
        raise _resource_types.ResourceInputError(
            "invalid_decode_arguments",
            "use DecodeOptions and a tuple of catalog format strings",
        )
    data, headers = _source(source, options)
    digest = hashlib.sha256(data).hexdigest()
    diagnostics = []
    try:
        if len(catalog_formats) > options.max_metadata_bytes:
            raise _decode_types.ResourceDecodeError(
                "metadata_limit", "too many declaration fields"
            )
        metadata_size = 0
        for value in itertools.chain(catalog_formats, (value for _, value in headers)):
            if len(value) > options.max_metadata_bytes:
                raise _decode_types.ResourceDecodeError(
                    "metadata_limit", "declaration exceeds metadata byte limit"
                )
            try:
                metadata_size += 1 + len(value.encode("utf-8"))
            except UnicodeError as exc:
                raise _decode_types.ResourceDecodeError(
                    "invalid_metadata", "declaration contains invalid Unicode"
                ) from exc
            if metadata_size > options.max_metadata_bytes:
                raise _decode_types.ResourceDecodeError(
                    "metadata_limit", "declarations exceed metadata byte limit"
                )
        claims, declarations = [], []
        for name, value in headers:
            if name == "content-type":
                media, charsets = _resource_encoding.parse_media(value)
                claims.append(media)
                declarations.extend(("http", charset) for charset in charsets)
        for value in catalog_formats:
            media, charsets = _resource_encoding.parse_media(value)
            claims.append(media)
            declarations.extend(("catalog", charset) for charset in charsets)
        if any(
            media
            not in _resource_encoding.TEXT_MEDIA | _resource_encoding.CONTAINER_MEDIA
            for media in claims
        ):
            raise _decode_types.ResourceDecodeError(
                "unsupported_media", "declared format has no text extractor"
            )
        content_encoding = dict(headers).get("content-encoding", "").strip().lower()
        payload, transformations, member, member_media = _resource_containers.unwrap(
            data, content_encoding, claims, options
        )
        text_media = set(claims) & _resource_encoding.TEXT_MEDIA
        if member_media:
            media_type = member_media
        elif len(text_media) > 1:
            raise _decode_types.ResourceDecodeError(
                "ambiguous_media", "text media declarations conflict"
            )
        elif text_media:
            media_type = next(iter(text_media))
        else:
            media_type = "text/plain"
            diagnostics.append(
                _decode_types.DecodeDiagnostic(
                    "default_media",
                    "default",
                    "no text declaration; interpreting payload as plain text",
                )
            )
        text, encoding, authority = _resource_encoding.decode(
            payload, media_type, declarations, options, diagnostics
        )
        identity = hashlib.sha256(
            _resource_types.canonical_json(
                {
                    "decoder_version": "strict-text-v1",
                    "source_sha256": digest,
                    "headers": headers,
                    "catalog_formats": catalog_formats,
                    "options": dataclasses.asdict(options),
                }
            )
        ).hexdigest()
        return _decode_types.DecodedText(
            text,
            media_type,
            encoding,
            authority,
            digest,
            len(data),
            hashlib.sha256(payload).hexdigest(),
            identity,
            transformations,
            member,
            tuple(diagnostics),
        )
    except _decode_types.ResourceDecodeError as exc:
        exc.source_sha256 = digest
        if not exc.diagnostics:
            exc.diagnostics = tuple(diagnostics)
        raise
