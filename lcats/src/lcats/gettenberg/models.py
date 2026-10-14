"""Immutable, source-scoped Gutenberg metadata; no cache or network setup.

Tuples preserve source order and multiplicity. Dates remain source literals;
Gutenberg issuance is not an original print-publication date. These records
refer to ebooks/volumes, not to the individual stories LCATS extracts.
"""

import base64
import dataclasses


@dataclasses.dataclass(frozen=True, slots=True)
class Literal:
    """A source literal, including its language and datatype when supplied."""

    text: str
    language: str | None = None
    datatype: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class Title:
    """One primary or alternative title, without discarding additional titles."""

    value: Literal
    kind: str


@dataclasses.dataclass(frozen=True, slots=True)
class Term:
    """A value and zero or more classification/vocabulary scheme URIs."""

    value: Literal
    schemes: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class Agent:
    """Contributor identity and associated source names, aliases and life dates."""

    uri: str
    names: tuple[Literal, ...] = ()
    aliases: tuple[Literal, ...] = ()
    birth_dates: tuple[Literal, ...] = ()
    death_dates: tuple[Literal, ...] = ()
    webpages: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class Contribution:
    """An agent's contribution under a full source predicate URI."""

    role_uri: str
    agent: Agent


@dataclasses.dataclass(frozen=True, slots=True)
class Resource:
    """An available file; equal media types do not imply equal resources.

    Multiple size/modification claims are retained instead of arbitrarily
    choosing one. Selection and downloading belong to the resource layer.
    """

    uri: str
    formats: tuple[Term, ...] = ()
    sizes: tuple[int, ...] = ()
    modified: tuple[Literal, ...] = ()
    is_format_of: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class MetadataValue:
    """Source-supplied additional metadata, such as MARC summaries/print notes."""

    predicate_uri: str
    value: Literal


@dataclasses.dataclass(frozen=True, slots=True)
class Ebook:
    """Metadata about one Gutenberg ebook, never inferred story metadata."""

    gutenberg_id: int
    uri: str
    titles: tuple[Title, ...] = ()
    contributors: tuple[Contribution, ...] = ()
    languages: tuple[Term, ...] = ()
    subjects: tuple[Term, ...] = ()
    shelves: tuple[Term, ...] = ()
    types: tuple[Term, ...] = ()
    resources: tuple[Resource, ...] = ()
    publishers: tuple[Literal, ...] = ()
    rights: tuple[Literal, ...] = ()
    issued: tuple[Literal, ...] = ()
    descriptions: tuple[Literal, ...] = ()
    contents: tuple[Literal, ...] = ()
    licenses: tuple[str, ...] = ()
    downloads: int | None = None
    additional_metadata: tuple[MetadataValue, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class Diagnostic:
    """An inspectable source-preservation notice for an unmodeled construct."""

    code: str
    path: str
    predicate_uri: str
    message: str


@dataclasses.dataclass(frozen=True, slots=True)
class SourceEvidence:
    """Exact input bytes and their identity; no invented retrieval provenance."""

    source_name: str
    sha256: str
    data: bytes
    parser_version: str = "1"


@dataclasses.dataclass(frozen=True, slots=True)
class ParsedRecord:
    """One ebook with original evidence and ordered parser diagnostics."""

    ebook: Ebook
    source: SourceEvidence
    diagnostics: tuple[Diagnostic, ...] = ()

    def to_dict(self) -> dict:
        """Return a detached JSON-compatible representation of all fields.

        Tuples become JSON arrays. Source bytes use an explicitly labeled
        base64 object, which recovers the exact original bytes, not re-encoded
        XML. This is an export schema (version 1), not an object constructor.
        """
        return {"schema_version": 1, **_json_value(self)}


def _json_value(value):
    if dataclasses.is_dataclass(value):
        return {
            field.name: _json_value(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, bytes):
        return {"encoding": "base64", "value": base64.b64encode(value).decode("ascii")}
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    return value
