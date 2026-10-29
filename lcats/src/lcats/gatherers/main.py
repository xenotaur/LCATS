"""Plan selected collections before setup, then run with explicit I/O policy."""

import contextlib
import importlib
from urllib import parse

from lcats.gatherers import planning
from lcats.gettenberg import approval_cli
from lcats.gettenberg import errors
from lcats.gettenberg import preparation
from lcats.gettenberg import resources
from lcats.gettenberg import sources_cli

GATHERERS = {name: f"lcats.gatherers.{name}.gatherer" for name in planning.NAMES}


def _services(
    cache_dir, archive, catalog_url, main_root, generated_root, allow_origins, offline
):
    """Select workflow defaults or overrides, then bound their network authority."""
    routes = sources_cli.gutenberg_routes(main_root, generated_root)
    request = sources_cli.catalog_request(archive=archive, url=catalog_url)
    urls = [routes.main_root, routes.generated_root]
    if request is not None:
        urls.append(request.request_url)
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
    Selected default or explicit sources permit their origins; --yes approves
    first setup only.
    Existing outputs are reused. Cleanup refusals and HTTP 404s do not stop mass gathering or
    later collections; the final summary reports incomplete gathering with exit 2.
    Other operational failures abort with exit 2, retaining prior outputs/cache.
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
                report = approval_cli.plan_report(service, plan)
                lines.extend(
                    [
                        f"Catalog source: {report['source']}",
                        f"Resource main root: {routes.main_root}",
                        f"Resource generated root: {routes.generated_root}",
                        f"Permitted origins: {', '.join(policy.allowed_origins)}",
                        f"Catalog setup approval required: {plan.approval_required}",
                    ]
                )
            lines.append(
                "Network: forbidden (offline)."
                if offline
                else "Network: permitted for missing sources during execution; catalog setup requires approval."
            )
            return "\n".join(lines), 0
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
            summaries = []
            incomplete = False
            for item in requirements:
                print(f"Running gatherer: {item.name}")
                module = importlib.import_module(GATHERERS[item.name])
                if item.needs_catalog:
                    result = module.gather(source=source)
                    if item.name == "mass_quantities":
                        summaries.append(f"{item.name}: {result.summary}")
                        incomplete = incomplete or result.incomplete
                else:
                    module.gather(offline=offline, cache_dir=cache_dir)
        if incomplete:
            return (
                "Gathering incomplete: cleanup refusals or unavailable sources remain.\n"
                + "\n".join(summaries),
                2,
            )
        message = "Gathering complete."
        if summaries:
            message += "\n" + "\n".join(summaries)
        return message, 0
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
