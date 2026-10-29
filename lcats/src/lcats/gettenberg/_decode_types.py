"""Immutable contracts for strict offline decoding, independent of acquisition."""

import dataclasses

from lcats.gettenberg import _resource_types


@dataclasses.dataclass(frozen=True, slots=True)
class DecodeDiagnostic:
    """An inspectable encoding or format decision; no source text is copied."""

    code: str
    source: str
    message: str


class ResourceDecodeError(_resource_types.ResourceError):
    """Original bytes remain intact; code and diagnostics explain decode failure.

    source_sha256 is set only after a bounded source read succeeds. Input size
    rejection happens before hashing and therefore leaves it None.
    """

    def __init__(self, code, message, *, diagnostics=(), source_sha256=None):
        self.diagnostics = tuple(diagnostics)
        self.source_sha256 = source_sha256
        super().__init__(code, message)


@dataclasses.dataclass(frozen=True, slots=True)
class DecodeOptions:
    """Explicit decoding authority and finite byte/metadata budgets.

    container is auto, none, gzip or zip. zip_member selects a safe text member
    by exact name, never a filesystem destination. Bounds apply separately to
    each inflation stage; peak memory can exceed an individual stage's bound.
    """

    encoding_override: str | None = None
    container: str = "auto"
    zip_member: str | None = None
    max_source_bytes: int = 32 * 1024**2
    max_decoded_bytes: int = 64 * 1024**2
    max_zip_entries: int = 1000
    max_metadata_bytes: int = 65536
    html_scan_bytes: int = 8192

    def __post_init__(self):
        for name in (
            "max_source_bytes",
            "max_decoded_bytes",
            "max_zip_entries",
            "max_metadata_bytes",
            "html_scan_bytes",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= 2**31 - 1:
                raise _resource_types.ResourceInputError(
                    "invalid_decode_options", f"{name} must be in 1..2147483647"
                )
        if self.container not in ("auto", "none", "gzip", "zip"):
            raise _resource_types.ResourceInputError(
                "invalid_decode_options", "unsupported container policy"
            )
        for name in ("encoding_override", "zip_member"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, str)
                or not value
                or len(value) > 8192
                or any(ord(char) < 32 for char in value)
            ):
                raise _resource_types.ResourceInputError(
                    "invalid_decode_options", f"invalid {name}"
                )


@dataclasses.dataclass(frozen=True, slots=True)
class DecodedText:
    """Strict text/HTML markup and reproducible derivation identity, never a file."""

    text: str
    media_type: str
    encoding: str
    encoding_source: str
    source_sha256: str
    source_size: int
    payload_sha256: str
    identity: str
    transformations: tuple[str, ...]
    zip_member: str | None
    diagnostics: tuple[DecodeDiagnostic, ...]
    decoder_version: str = "strict-text-v1"
