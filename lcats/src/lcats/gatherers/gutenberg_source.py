"""Catalog-backed plain-text source for story extraction, with explicit authority.

The caller owns the pinned catalog's lifetime. No legacy cache, header metadata
fallback, guessed URL, implicit setup or implicit refresh is used here.
"""

import dataclasses

from lcats.gettenberg import cleanup
from lcats.gettenberg import models
from lcats.gettenberg import resources

_AUTHOR_ROLES = frozenset(
    (
        "http://purl.org/dc/terms/creator",
        "http://id.loc.gov/vocabulary/relators/aut",
    )
)
_PLAIN = (
    resources.ResourcePreference("text/plain", "utf-8"),
    resources.ResourcePreference("text/plain"),
)


def _unique(values):
    """Deduplicate exact text while preserving RDF order, not set iteration order."""
    return tuple(dict.fromkeys(value for value in values if value.strip()))


@dataclasses.dataclass(frozen=True, slots=True)
class StoryMetadata:
    """Consumer projection; the complete ebook remains available for selection."""

    ebook: models.Ebook
    titles: tuple[str, ...]
    authors: tuple[str, ...]
    aliases: tuple[str, ...]
    subjects: tuple[str, ...]
    languages: tuple[str, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class StoryText:
    """Decoded/cleaned derivation with original-byte identity retained."""

    gutenberg_id: int
    catalog_archive_sha256: str
    source_uri: str
    artifact: resources.SourceArtifact
    decoded: resources.DecodedText
    cleaned: cleanup.CleanupResult

    def provenance(self):
        """Return JSON-compatible evidence without copying the original text."""
        return {
            "gutenberg_id": self.gutenberg_id,
            "catalog_archive_sha256": self.catalog_archive_sha256,
            "source_uri": self.source_uri,
            "request_url": self.artifact.receipt.request_url,
            "final_url": self.artifact.receipt.final_url,
            "original_sha256": self.artifact.sha256,
            "receipt_sha256": self.artifact.receipt_sha256,
            "decode_identity": self.decoded.identity,
            "encoding": self.decoded.encoding,
            "cleanup_policy": self.cleaned.policy_version,
            "cleanup_diagnostics": [
                dataclasses.asdict(d) for d in self.cleaned.diagnostics
            ],
        }


class GutenbergStorySource:
    """Read records and acquire text using caller-selected routes and policy.

    Args:
        catalog: Open, pinned Catalog; caller closes it after gathering.
        store: ResourceStore sharing the intended cache root.
        routes: Explicit GutenbergRoutes; selecting endpoints grants no authority.
        policy: NetworkPolicy, offline by default. Every fetch receives this policy.

    Missing records return None. Only creator/author names and aliases populate
    author fields. Primary titles take precedence over alternatives. Unsupported
    formats, bad decoding or ambiguous boilerplate fail with structured errors;
    no lossy decoding, HTML fallback or alternate trial downloads occur.
    """

    def __init__(self, catalog, store, *, routes, policy=resources.NetworkPolicy()):
        if not isinstance(routes, resources.GutenbergRoutes) or not isinstance(
            policy, resources.NetworkPolicy
        ):
            raise resources.ResourceInputError(
                "invalid_story_source", "explicit routes and NetworkPolicy required"
            )
        self.catalog = catalog
        self.store = store
        self.routes = routes
        self.policy = policy

    def metadata(self, book_id):
        """Project metadata once per story without fetching source text."""
        record = self.catalog.get(book_id)
        if record is None:
            return None
        book = record.ebook
        authors = [c.agent for c in book.contributors if c.role_uri in _AUTHOR_ROLES]
        primary = [t.value.text for t in book.titles if t.kind == "primary"]
        titles = primary or [
            t.value.text for t in book.titles if t.kind == "alternative"
        ]
        return StoryMetadata(
            book,
            _unique(titles),
            _unique(n.text for a in authors for n in a.names),
            _unique(n.text for a in authors for n in a.aliases),
            _unique(t.value.text for t in book.subjects),
            _unique(t.value.text for t in book.languages),
        )

    def read(self, metadata):
        """Select, acquire, strictly decode and conservatively clean one story.

        A marker-free plain text is allowed. A damaged/ambiguous marker envelope
        is refused before the heuristic story extractor can discard evidence.
        Acquired original bytes remain cached even if derivation fails.
        """
        selected = resources.select_routable_resource(
            metadata.ebook, routes=self.routes, preferences=_PLAIN
        )
        if selected.request is None:
            raise resources.ResourceInputError(
                "no_plain_text", "no qualified plain-text resource for this ebook"
            )
        artifact = self.store.fetch(selected.request, policy=self.policy)
        resource = metadata.ebook.resources[selected.selection.source_index]
        decoded = resources.decode_text(
            artifact, catalog_formats=tuple(t.value.text for t in resource.formats)
        )
        if decoded.media_type != "text/plain":
            raise resources.ResourceDecodeError(
                "not_plain_text", "story extractor requires plain text"
            )
        cleaned = cleanup.strip_boilerplate(decoded.text)
        if not cleaned.changed and any(
            d.code != "no_markers" for d in cleaned.diagnostics
        ):
            raise resources.ResourceDecodeError(
                "cleanup_refused", ", ".join(d.code for d in cleaned.diagnostics)
            )
        return StoryText(
            metadata.ebook.gutenberg_id,
            self.catalog.info["report"]["archive_sha256"],
            resource.uri,
            artifact,
            decoded,
            cleaned,
        )
