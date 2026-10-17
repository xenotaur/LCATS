"""Runs the extractors we have."""

import importlib

from lcats.gatherers import planning

# Values are import paths, not imported modules: planning must never initialize
# caches or pull in the metadata parser for an unselected collection.
GATHERERS = {name: f"lcats.gatherers.{name}.gatherer" for name in planning.NAMES}


def run(gatherers=None, dry_run=False):
    """Run the gatherers."""
    try:
        requirements = planning.select(gatherers)
    except ValueError as exc:
        return str(exc), 2
    gatherers = [item.name for item in requirements]
    if dry_run:
        lines = [
            f"Selected {len(requirements)} collections (story counts not evaluated)."
        ]
        for item in requirements:
            lines.append(
                f"{item.name}: {item.source_type}; catalog use: {item.catalog_use}"
            )
        if any(item.needs_catalog for item in requirements):
            lines.append(
                "Metadata-dependent selection/enrichment is unresolved here. "
                "Execution still uses the legacy catalog; new catalog migration is pending."
            )
        else:
            lines.append("No metadata catalog is required.")
        return "\n".join(lines), 0

    print("Gathering data from the corpus.")
    print(f" - Running {len(gatherers)} gatherers: {', '.join(gatherers)}")
    print()
    for gatherer in gatherers:
        print(f"Running gatherer: {gatherer}")
        print("-" * (len(gatherer) + 18))
        importlib.import_module(GATHERERS[gatherer]).gather()
        print()

    return "Gathering complete.", 0


if __name__ == "__main__":
    run()
