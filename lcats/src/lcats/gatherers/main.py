"""Plan selected collections before setup, then run with explicit I/O policy."""

import contextlib
import importlib
from urllib import parse

from lcats.gatherers import planning
from lcats.gettenberg import approval_cli
from lcats.gettenberg import errors
from lcats.gettenberg import preparation
from lcats.gettenberg import resources

GATHERERS = {name: f"lcats.gatherers.{name}.gatherer" for name in planning.NAMES}


def _services(
    cache_dir, archive, catalog_url, main_root, generated_root, allow_origins, offline
):
    """Resolve explicit endpoints without selecting a default operational mirror."""
    if bool(main_root) != bool(generated_root):
        raise ValueError(
            "provide both --gutenberg-main-root and --gutenberg-generated-root"
        )
    routes = resources.GutenbergRoutes(main_root, generated_root) if main_root else None
    request = (
        resources.SourceRequest.from_url(catalog_url, kind="archive")
        if catalog_url
        else None
    )
    urls = [url for url in (main_root, generated_root, catalog_url) if url]
    origins = [
        f"{parse.urlsplit(url).scheme}://{parse.urlsplit(url).netloc}" for url in urls
    ]
    policy = resources.NetworkPolicy(
        online=not offline,
        allowed_origins=tuple(dict.fromkeys([*origins, *allow_origins])),
    )
    service = preparation.CatalogPreparation(
        cache_dir, archive=archive, request=request, policy=policy, offline=offline
    )
    return service, routes, policy


def run(
    gatherers=None,
    dry_run=False,
    *,
    yes=False,
    offline=False,
    catalog_archive=None,
    catalog_url=None,
    main_root=None,
    generated_root=None,
    allow_origins=(),
    cache_dir=None,
):
    """Gather selected collections, with setup approval and true offline access.

    No selection means all collections. All names and required configuration are
    checked before setup or extraction. Dry-run performs local inspection only;
    it does not resolve metadata-dependent story counts or import consumers.
    Explicit URLs/roots permit their origins; --yes approves first setup only.
    Existing outputs are reused. Operational failures return exit2, with partial
    prior outputs/cache retained and the collection run log recording abortion.
    """
    try:
        for value in (dry_run, yes, offline):
            if type(value) is not bool:
                raise ValueError("dry_run, yes and offline must be bool")
        requirements = planning.select(gatherers)
        needs_catalog = any(item.needs_catalog for item in requirements)
        service = routes = policy = None
        if needs_catalog:
            service, routes, policy = _services(
                cache_dir,
                catalog_archive,
                catalog_url,
                main_root,
                generated_root,
                allow_origins,
                offline,
            )
        if dry_run:
            lines = [
                f"Selected {len(requirements)} collections (story counts not evaluated)."
            ]
            lines.extend(
                f"{item.name}: {item.source_type}; catalog use: {item.catalog_use}"
                for item in requirements
            )
            if service is None:
                lines.append("No metadata catalog is required.")
            else:
                plan = service.plan()
                lines.append(
                    f"Catalog: {plan.catalog_state}; preparation: {plan.action} ({plan.reason})."
                )
                lines.append(
                    "Metadata-dependent selection/enrichment counts are unresolved in this plan."
                )
                lines.append(
                    "Resource routes: explicit."
                    if routes
                    else "Resource routes: not configured; supply both Gutenberg roots before execution."
                )
            lines.append(
                "Network: forbidden (offline)."
                if offline
                else "Network: permitted for missing sources during execution; catalog setup requires approval."
            )
            return "\n".join(lines), 0
        if service is not None and routes is None:
            raise ValueError(
                "metadata-dependent gathering requires explicit --gutenberg-main-root and --gutenberg-generated-root; no default mirror is configured"
            )
        with contextlib.ExitStack() as stack:
            source = None
            if service is not None:
                approved = approval_cli.confirm_setup(service, service.plan(), yes=yes)
                service.prepare(approved=approved)
                from lcats.gatherers import gutenberg_source

                catalog = stack.enter_context(service.manager.open())
                source = gutenberg_source.GutenbergStorySource(
                    catalog, service.store, routes=routes, policy=policy
                )
            for item in requirements:
                print(f"Running gatherer: {item.name}")
                module = importlib.import_module(GATHERERS[item.name])
                if item.needs_catalog:
                    module.gather(source=source)
                else:
                    module.gather(offline=offline, cache_dir=cache_dir)
        return "Gathering complete.", 0
    except (
        errors.GettenbergError,
        resources.ResourceError,
        OSError,
        ValueError,
    ) as exc:
        return f"Gathering failed: {exc}", 2


if __name__ == "__main__":
    from lcats import cli
    import sys

    cli.main(["gather", *sys.argv[1:]])
