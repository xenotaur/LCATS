"""CLI wrapper for clearing data/ and cache/ contents, symlink-safe."""

import argparse
import shutil
import sys

from lcats.gatherers import main as gatherers_main
from lcats.gettenberg import cache as gettenberg_cache
from lcats.utils import env
from lcats.utils import paths


def build_parser(add_help: bool = True) -> argparse.ArgumentParser:
    """Build parser for the clean command."""
    parser = argparse.ArgumentParser(
        description=(
            "Clear data/ and/or cache/ contents without shell-glob reasoning. "
            "Safe for a symlinked data/ or cache/ setup: only contents are "
            "removed, never the directory (or symlink) itself."
        ),
        add_help=add_help,
        epilog=(
            "Examples:\n"
            "  lcats clean                  # clear all of data/ and all of cache/\n"
            "  lcats clean mass_quantities  # clear just data/mass_quantities/,\n"
            "                               # leaving cache/ untouched -- a targeted\n"
            "                               # recheck must not invalidate the shared\n"
            "                               # cache every other gatherer relies on\n"
            "  lcats clean --cache-only     # clear cache/ only, leave data/ alone\n"
            "  lcats clean --data-only      # clear data/ only, leave cache/ alone"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "gatherers",
        nargs="*",
        help="Gatherer names to clean under data/. Defaults to every gatherer.",
    )
    parser.add_argument(
        "--data-only",
        action="store_true",
        help="Clean only data/; leave cache/ untouched.",
    )
    parser.add_argument(
        "--cache-only",
        action="store_true",
        help="Clean only cache/; leave data/ untouched.",
    )
    return parser


def _clean_data(gatherer_names):
    """Clear data/, either entirely or scoped to specific gatherer names.

    Heals a dangling data/ symlink first (paths.makedirs is a no-op when
    data/ is already fine) -- clear_directory_contents alone can't do this,
    since it no-ops on a path that isn't currently a valid directory.
    """
    paths.makedirs(env.data_root())

    if not gatherer_names:
        paths.clear_directory_contents(env.data_root())
        print(f"cleared: {env.data_root()}")
        return

    for name in gatherer_names:
        if name not in gatherers_main.GATHERERS:
            print(f"Unknown gatherer: {name}", file=sys.stderr)
            continue
        target = env.data_root() / name
        shutil.rmtree(target, ignore_errors=True)
        print(f"cleared: {target}")


def _clean_cache():
    """Clear every cache mechanism: resources, and the Gutenberg cache."""
    paths.makedirs(env.cache_resources_dir())
    paths.clear_directory_contents(env.cache_resources_dir())
    print(f"cleared: {env.cache_resources_dir()}")
    gettenberg_cache.clear_all()
    print(f"cleared: {gettenberg_cache.GUTENBERG_TEXTS}")
    print(f"cleared: {gettenberg_cache.GUTENBERG_TMP}")
    print(f"cleared: {gettenberg_cache.GUTENBERG_ROOT} (index DB, RDF archive)")


def run(argv=None, parsed_args=None) -> int:
    """Run the clean command. Returns 0 on success."""
    parser = build_parser()
    args = parsed_args if parsed_args is not None else parser.parse_args(argv)

    if args.data_only and args.cache_only:
        print(
            "error: --data-only and --cache-only are mutually exclusive",
            file=sys.stderr,
        )
        return 2

    if args.gatherers and args.cache_only:
        print("error: gatherer names are not valid with --cache-only", file=sys.stderr)
        return 2

    try:
        if not args.cache_only:
            _clean_data(args.gatherers)
        # Scoping to specific gatherer names is a targeted recheck, not a
        # full release-prep clear -- it must not also invalidate the shared
        # cache/ that every other gatherer relies on.
        if not args.data_only and not args.gatherers:
            _clean_cache()
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(run())
