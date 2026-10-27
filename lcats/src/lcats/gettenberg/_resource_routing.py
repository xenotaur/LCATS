"""Offline Gutenberg URL conventions, independently implemented from upstream rules.

Qualification and pinned sources: project/development/gettenberg-route-qualification.md.
No HTTP discovery, fallback guessing or permission grants occur here.
"""

import dataclasses
import re
from urllib import parse

from lcats.gettenberg import _resource_selection
from lcats.gettenberg import _resource_types
from lcats.gettenberg import models

_POLICY = "gutenberg-mirror-v1"
_CATALOG = "https://www.gutenberg.org/cache/epub/feeds/rdf-files.tar.bz2"
_ID = r"[1-9][0-9]*"
# Published format identifiers and filename suffixes are URL protocol facts, not
# MIME guesses. Keep this finite: an unknown alias must never cause a trial GET.
_SUFFIXES = {
    "txt.utf-8": ".txt",
    "html.images": "-images.html",
    "html.noimages": ".html",
    "epub.images": "-images.epub",
    "epub.noimages": ".epub",
    "epub3.images": "-images-3.epub",
    "kindle.images": "-images.mobi",
    "kindle.noimages": ".mobi",
    "kf8.images": "-images-kf8.mobi",
    "pdf.images": "-images.pdf",
    "pdf.noimages": ".pdf",
    "rdf": ".rdf",
    "rst.gen": ".rst",
    "cover.small": ".cover.small.jpg",
    "cover.medium": ".cover.medium.jpg",
    "qrcode": ".qrcode.png",
    "zip": "-h.zip",
}


def _safe_path(path: str) -> bool:
    """Reject alternate separator/traversal encodings before prefix composition.

    Decoded percent signs are refused too: a second decoder must not turn a safe
    segment into a separator or dot segment. Preserve the original escaping.
    """
    if not path.startswith("/") or "//" in path:
        return False
    for segment in path.split("/"):
        decoded = parse.unquote_to_bytes(segment)
        if decoded in (b".", b"..") or any(
            byte < 32 or byte == 127 or byte in b"/\\%?#" for byte in decoded
        ):
            return False
    return True


def _root(value: str) -> str:
    """Validate a directory URL; concatenation will stay under this exact prefix."""
    canonical = _resource_types.canonical_url(value)
    parts = parse.urlsplit(canonical)
    if "?" in value or "#" in value or not _safe_path(parts.path):
        raise _resource_types.ResourceInputError(
            "invalid_route_root",
            "use a directory URL without traversal, query or fragment",
        )
    return canonical.rstrip("/") + "/"


@dataclasses.dataclass(frozen=True, slots=True)
class RouteResolution:
    """A qualified request or a stable rejection code and explanation.

    Unsupported/unsafe input is data, not a reason to try another URL. No raw
    input is echoed in diagnostics, since it might contain credentials.
    """

    request: _resource_types.SourceRequest | None
    code: str
    message: str


@dataclasses.dataclass(frozen=True, slots=True)
class GutenbergRoutes:
    """Explicit endpoint layout, independent of network permission and MIME types.

    Args:
        main_root: Directory containing digit-sharded main ebook paths.
        generated_root: Directory containing generated ebook-ID directories;
            for a combined mirror this commonly ends in /cache/epub/.
        catalog_url: Exact catalog archive endpoint, independently configurable.

    Construction, resolve() and catalog_request() perform no I/O. No mirror is
    selected by default and no operational availability is promised.
    """

    main_root: str
    generated_root: str
    catalog_url: str = _CATALOG

    def __post_init__(self):
        object.__setattr__(self, "main_root", _root(self.main_root))
        object.__setattr__(self, "generated_root", _root(self.generated_root))
        canonical = _resource_types.canonical_url(self.catalog_url)
        if "#" in self.catalog_url:
            raise _resource_types.ResourceInputError(
                "invalid_catalog_url", "catalog URL must not have a fragment"
            )
        object.__setattr__(self, "catalog_url", canonical)

    def catalog_request(self) -> _resource_types.SourceRequest:
        """Describe the exact archive URL; fetching still requires online policy."""
        return _resource_types.SourceRequest(
            self.catalog_url, self.catalog_url, kind="archive", route_policy=_POLICY
        )

    def resolve(self, source_uri: str) -> RouteResolution:
        """Map a qualified Gutenberg resource URI without fetching anything.

        Only www.gutenberg.org HTTP(S), default ports, and known /files, /ebooks,
        /cache/epub and /cache/generated layouts qualify. Queries/fragments,
        leading-zero IDs, historical etext layouts and unknown aliases do not.
        The complete original URI is retained in a successful request.
        """
        try:
            canonical = _resource_types.canonical_url(source_uri)
        except _resource_types.ResourceInputError:
            return RouteResolution(None, "invalid_source", "Invalid source URL")
        parts = parse.urlsplit(canonical)
        if parts.netloc != "www.gutenberg.org":
            return RouteResolution(
                None, "unsupported_origin", "Unqualified source origin"
            )
        if "?" in source_uri or "#" in source_uri or not _safe_path(parts.path):
            return RouteResolution(
                None, "unsafe_path", "Ambiguous or unsafe source path"
            )
        destination = None
        if match := re.fullmatch(rf"/files/({_ID})/(.+)", parts.path):
            book, suffix = match.groups()
            if not suffix.endswith("/"):
                # Single-digit IDs have an explicit upstream 0/ directory.
                shard = "/".join(book[:-1]) if len(book) > 1 else "0"
                destination = f"{self.main_root}{shard}/{book}/{suffix}"
        elif match := re.fullmatch(
            rf"/cache/(?:epub|generated)/({_ID})/(.+)", parts.path
        ):
            book, suffix = match.groups()
            if not suffix.endswith("/"):
                destination = f"{self.generated_root}{book}/{suffix}"
        elif match := re.fullmatch(rf"/ebooks/({_ID})\.([a-z0-9.-]+)", parts.path):
            book, alias = match.groups()
            if alias in _SUFFIXES:
                destination = f"{self.generated_root}{book}/pg{book}{_SUFFIXES[alias]}"
        if destination is None:
            return RouteResolution(
                None, "unsupported_layout", "Unqualified path or format alias"
            )
        try:
            request = _resource_types.SourceRequest(
                source_uri, destination, route_policy=_POLICY
            )
        except _resource_types.ResourceInputError:
            # A bounded source and root can still compose into an overlong URL.
            return RouteResolution(
                None, "invalid_destination", "Mapped URL exceeds request bounds"
            )
        return RouteResolution(
            request, "qualified", "Published Gutenberg URL convention"
        )


@dataclasses.dataclass(frozen=True, slots=True)
class RoutedSelection:
    """Original metadata selection plus one route decision per source resource."""

    selection: _resource_selection.ResourceSelection
    routes: tuple[RouteResolution, ...]

    @property
    def request(self) -> _resource_types.SourceRequest | None:
        """Return the chosen request, or None when no routable format matched."""
        index = self.selection.source_index
        return None if index is None else self.routes[index].request


def select_routable_resource(
    ebook: models.Ebook,
    *,
    routes: GutenbergRoutes,
    preferences: tuple[
        _resource_selection.ResourcePreference, ...
    ] = _resource_selection.DEFAULT_PREFERENCES,
) -> RoutedSelection:
    """Select by declared MIME preference among qualified routes, entirely offline.

    Args:
        ebook: Original metadata; source resource identities/order are preserved.
        routes: Explicit endpoint configuration, not network permission.
        preferences: Same ordered exact preferences as select_resource().

    Returns:
        Selection with MIME/capability diagnostics and all indexed route decisions.
        An unsupported preferred alias cannot conceal a qualified alternative.

    Raises:
        ResourceInputError: Arguments are not the documented typed records.
    """
    if not isinstance(ebook, models.Ebook) or not isinstance(routes, GutenbergRoutes):
        raise _resource_types.ResourceInputError(
            "invalid_selection", "use Ebook and GutenbergRoutes"
        )
    decisions = tuple(routes.resolve(resource.uri) for resource in ebook.resources)
    eligible = frozenset(
        i for i, decision in enumerate(decisions) if decision.request is not None
    )
    selection = _resource_selection.select_resource(
        ebook, preferences=preferences, eligible_indices=eligible
    )
    return RoutedSelection(selection, decisions)
