"""Qualified source defaults for CLI workflows, without I/O or network authority.

The catalog/preparation/acquisition APIs remain explicit and offline by default.
Only workflows that actually need Gutenberg metadata call these resolvers. A
selected URL is still subject to approval, cache integrity and network policy.
"""

from lcats.gettenberg import errors
from lcats.gettenberg import resources

CATALOG_URL = "https://www.gutenberg.org/cache/epub/feeds/rdf-files.tar.bz2"
MAIN_ROOT = "https://gutenberg.pglaf.org/"
GENERATED_ROOT = "https://gutenberg.pglaf.org/cache/epub/"


def catalog_request(*, archive=None, url=None):
    """Select an explicit archive/URL or the published default catalog request.

    Local archives suppress the default URL. Supplying both explicit forms is
    invalid, including for Python callers bypassing argparse's exclusion group.
    """
    if archive is not None and url is not None:
        raise errors.CatalogInputError("choose archive or URL, not both")
    if archive is not None:
        return None
    return resources.SourceRequest.from_url(
        CATALOG_URL if url is None else url, kind="archive"
    )


def gutenberg_routes(main_root=None, generated_root=None):
    """Select the qualified pair or require a complete explicit replacement.

    Never fill half an override with a default: the two layouts belong to the
    caller's chosen mirror. No mirror discovery or automatic failover is done.
    """
    if (main_root is None) != (generated_root is None):
        raise errors.CatalogInputError(
            "provide both --gutenberg-main-root and --gutenberg-generated-root"
        )
    if main_root is None:
        main_root, generated_root = MAIN_ROOT, GENERATED_ROOT
    return resources.GutenbergRoutes(main_root, generated_root)
