# lcats/lcats/utils/paths.py
"""Symlink-aware filesystem helpers for LCATS's regenerable data/cache trees.

Plain ``os.makedirs`` (even with ``exist_ok=True``) does not handle a
dangling symlink gracefully. ``os.path.exists()`` follows symlinks and
returns ``False`` for a broken one, so ``os.makedirs`` proceeds to call
``mkdir()`` regardless, which then fails:

- ``FileExistsError`` if the dangling symlink *is* the target path (a
  directory entry with that name already exists, even though it's broken).
- ``FileNotFoundError`` if the dangling symlink is an *ancestor* of the
  target path (the parent can't be traversed to reach the leaf).

These are genuinely different failures, not two shapes of the same one.
Critically, ``exist_ok=True`` does not help with either: both
``os.makedirs`` and ``pathlib.Path.mkdir`` gate their ``exist_ok``
suppression on ``isdir()``/``is_dir()``, which is also ``False`` for a
dangling symlink.
"""

import os
import pathlib
import shutil


def makedirs(path):
    """Create `path` and any missing parents, healing dangling symlinks.

    Behaves like ``os.makedirs(path, exist_ok=True)``, but additionally
    detects a dangling symlink anywhere in `path` -- the path itself, or
    any ancestor of it -- and heals it by recreating the symlink's
    missing target directory, then lets ``os.makedirs`` fill in the rest.

    This auto-heal is a deliberate choice for LCATS's ``data/``/``cache/``
    trees specifically, which are documented as disposable, regenerable
    caches (see ``lcats/docs/reference/prepare-corpora-release.md``) --
    it would be the wrong default for a general-purpose utility applied
    to arbitrary paths.

    Args:
        path: The directory path to ensure exists.

    Raises:
        NotADirectoryError: `path`, or an ancestor of it, exists as a
            plain file (or a symlink to one), so it can never become a
            directory without deleting that file first.
    """
    target = pathlib.Path(path)

    for ancestor in list(reversed(target.parents)) + [target]:
        if os.fspath(ancestor) in ("", "."):
            continue
        if ancestor.is_dir():
            continue  # already a valid directory (a live symlink counts)
        if ancestor.is_symlink():
            # Dangling: os.path.exists()/is_dir() are False, but a
            # directory entry with this name already exists, so plain
            # os.makedirs can't create it. Heal by recreating whatever
            # the symlink points at.
            link_target = ancestor.parent / ancestor.readlink()
            os.makedirs(link_target, exist_ok=True)
            continue
        if ancestor.exists():
            raise NotADirectoryError(
                f"{ancestor} exists and is not a directory; "
                f"refusing to create {target}"
            )
        # Doesn't exist at all and isn't a symlink -- ordinary case,
        # os.makedirs below will create it.

    os.makedirs(target, exist_ok=True)


def clear_directory_contents(path):
    """Remove everything inside `path`, without touching `path` itself.

    Safe for a symlinked `path`: only the directory's *contents* are
    removed, one entry at a time, so a `data`/`cache`-style symlink to a
    scratch location survives a clear-and-regenerate cycle intact. A
    missing `path` is a silent no-op.

    Args:
        path: The directory whose contents should be removed.
    """
    root = pathlib.Path(path)
    if not root.is_dir():
        return

    for entry in root.iterdir():
        if entry.is_symlink() or entry.is_file():
            entry.unlink()
        else:
            shutil.rmtree(entry)
