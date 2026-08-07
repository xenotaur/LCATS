"""Corpus file discovery helpers."""

import os
import pathlib
import sys
import typing

from typing import Iterable, Iterator, Union

CANONICAL_STORY_FILENAME = "story.json"


def find_corpus_stories(
    root: Union[str, pathlib.Path],
    *,
    ignore_dir_names: Iterable[str] = ("cache",),
    follow_symlinks: bool = False,
    ignore_hidden: bool = False,
    sort: bool = True,
) -> list[pathlib.Path]:
    """Recursively list all JSON files under root."""
    root_path = pathlib.Path(root).expanduser()
    if not root_path.exists():
        raise FileNotFoundError(f"Root path not found: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Root is not a directory: {root_path}")

    ignore_set = {name.casefold() for name in ignore_dir_names}
    results: typing.List[pathlib.Path] = []

    for dirpath, dirnames, filenames in os.walk(
        root_path, topdown=True, followlinks=follow_symlinks
    ):
        pruned = []
        for directory_name in dirnames:
            if directory_name.casefold() in ignore_set:
                continue
            if ignore_hidden and directory_name.startswith("."):
                continue
            pruned.append(directory_name)
        dirnames[:] = pruned

        for filename in filenames:
            if ignore_hidden and filename.startswith("."):
                continue
            if filename.lower().endswith(".json"):
                results.append(pathlib.Path(dirpath) / filename)

    if sort:
        results.sort()
    return results


def iter_collection_story_files(
    collection_dir: Union[str, pathlib.Path],
) -> Iterator[pathlib.Path]:
    """Yield canonical story files that are immediate entries of collection_dir.

    The canonical story-file selector, per Decision 3 of
    PROP-LCATS-STORY-BUCKET-LAYOUT, as retracted to bucket-only by
    Decision 4: a story is only ``<story>/story.json`` -- a subdirectory
    of ``collection_dir`` containing a file literally named
    ``story.json``. A flat ``<story>.json`` file directly in
    ``collection_dir`` is no longer a valid story source; the production
    ``corpora/`` snapshot has been confirmed fully migrated to the bucket
    layout (see ``WI-STORY-0045``'s execution record).

    Applies only one level of nesting relative to ``collection_dir``. A
    subdirectory without a canonical ``story.json`` is skipped, not searched
    further -- ``collection_dir`` is assumed to already be a single
    collection's own directory. Sibling JSON artifacts inside a story's own
    bucket directory (analysis output, override sidecars) are intentionally
    excluded, since only the canonical leaf name is accepted.

    Directory entries reached via a symlink are skipped, matching
    :func:`find_corpus_stories`'s default ``follow_symlinks=False``.
    """
    path = pathlib.Path(collection_dir)
    if not path.is_dir():
        return
    for entry in sorted(path.iterdir()):
        if entry.is_symlink() and entry.is_dir():
            continue
        if entry.is_dir():
            nested = entry / CANONICAL_STORY_FILENAME
            if nested.is_file():
                yield nested


def _is_leaf_story_bucket(
    directory: pathlib.Path,
    *,
    ignore_dir_names: frozenset[str] = frozenset(),
) -> bool:
    """True if ``directory`` is unambiguously one story's own bucket.

    A directory containing an immediate ``story.json`` is ambiguous on its
    own: it might be a story's own bucket, or it might be a collection
    whose layout happens to include a stray flat file literally named
    ``story.json`` -- the two look identical from that single check alone
    (see Decision 3 of PROP-LCATS-STORY-BUCKET-LAYOUT). A subdirectory
    that is itself a real story bucket (has its own immediate
    ``story.json``) settles it: genuine story buckets never contain other
    story buckets, so that sibling evidence means ``directory`` is
    actually a collection, not a leaf bucket -- its ``story.json`` is the
    stray file, not the marker.

    ``ignore_dir_names`` must already be a case-folded frozenset (the
    normalized form :func:`find_json_files` builds once) -- a subdirectory
    matching it is excluded from this nested-bucket check entirely, so an
    ignored child (e.g. ``cache/story.json``) can never cause a real leaf
    bucket to be misclassified as a collection.
    """
    if not (directory / CANONICAL_STORY_FILENAME).is_file():
        return False
    for entry in directory.iterdir():
        if entry.is_symlink():
            continue
        if entry.is_dir() and entry.name.casefold() not in ignore_dir_names:
            if (entry / CANONICAL_STORY_FILENAME).is_file():
                return False
    return True


def _walk_canonical_story_files(
    directory: pathlib.Path,
    *,
    ignore_dir_names: frozenset[str] = frozenset(),
) -> Iterator[pathlib.Path]:
    """Recursively yield canonical story files under directory.

    First checks whether ``directory`` is unambiguously a leaf story
    bucket (see :func:`_is_leaf_story_bucket`) -- if so, yields only its
    ``story.json`` and stops, regardless of what other JSON sidecars
    (``audit.json``, ``scenes.json``, ``events.json``, and similar
    per-story analysis artifacts) sit alongside it.

    Otherwise treats ``directory`` as a collection and recurses into every
    subdirectory, letting the recursive call's own
    :func:`_is_leaf_story_bucket` check decide whether that subdirectory is
    a leaf bucket or another collection level to descend through. This
    behaves correctly whether ``directory`` is a corpus root (immediate
    children are collection directories), a single collection directory,
    or a single story's own bucket directory -- without relying on
    presence-of-story.json alone to decide which, since a collection
    directory can itself hold a stray flat file literally named
    ``story.json`` alongside real nested buckets. Flat files are never
    yielded here, per Decision 4's bucket-only retraction -- the only
    file ever eligible is a directory's own canonical ``story.json``,
    reached via the leaf-bucket check above.

    ``ignore_dir_names`` must already be a case-folded frozenset (built
    once by :func:`find_json_files`, never a one-shot iterable like a
    generator -- reusing the same frozenset across every recursive call
    is what keeps pruning correct below the first traversal level).
    Matching subdirectories are pruned before recursing into them, and
    are also excluded from :func:`_is_leaf_story_bucket`'s own
    nested-bucket check -- the top-level ``directory`` argument itself is
    never pruned, only its descendants, matching :func:`os.walk`'s own
    root-vs-children pruning semantics.

    Directory entries reached via a symlink are skipped, matching
    :func:`find_corpus_stories`'s default ``follow_symlinks=False``.
    """
    if _is_leaf_story_bucket(directory, ignore_dir_names=ignore_dir_names):
        yield directory / CANONICAL_STORY_FILENAME
        return
    for entry in sorted(directory.iterdir()):
        if entry.is_symlink():
            continue
        if entry.is_dir():
            if entry.name.casefold() in ignore_dir_names:
                continue
            yield from _walk_canonical_story_files(
                entry, ignore_dir_names=ignore_dir_names
            )


def find_json_files(
    directories: Iterable[Union[str, pathlib.Path]],
    *,
    ignore_dir_names: Iterable[str] = (),
) -> Iterator[pathlib.Path]:
    """Yield canonical story files from provided paths in deterministic order.

    Bucket-only, per Decision 4 of PROP-LCATS-STORY-BUCKET-LAYOUT (dual-layout
    retraction): every story is ``<story>/story.json`` via
    :func:`_walk_canonical_story_files`. A JSON file is eligible only if it
    is literally named ``story.json`` -- whether reached by scanning a
    directory, or passed directly as a literal file path in ``directories``.
    A non-canonical file path passed directly is silently skipped, matching
    the same rule a directory scan applies; there is no longer a
    caller-knows-best exception, since the retraction's whole point is that
    ``story.json`` is the one and only valid marker everywhere.

    A directory scan additionally resolves an ambiguity presence-of-
    ``story.json`` alone cannot: see :func:`_is_leaf_story_bucket` for how a
    directory is told apart from a collection whose layout happens to
    include a stray flat file literally named ``story.json``.

    ``ignore_dir_names`` defaults to an empty tuple (a no-op) so every
    existing caller is unaffected unless it opts in; pass e.g.
    ``("cache",)`` to prune subdirectories with that name (case-insensitive)
    from the scan, matching :func:`find_corpus_stories`'s own parameter.
    Materialized into a case-folded frozenset exactly once here, then
    reused unchanged across every recursive call below -- ``directories``
    and ``ignore_dir_names`` may each be one-shot iterables (e.g.
    generators); only ``directories`` is safe to consume lazily in the
    outer loop, since ``ignore_dir_names`` must survive many reuses.
    """
    ignore_names = frozenset(name.casefold() for name in ignore_dir_names)
    for directory in directories:
        path = pathlib.Path(directory)
        if not path.exists():
            print(f"warning: directory does not exist: {directory}", file=sys.stderr)
            continue
        if path.is_file():
            if path.name == CANONICAL_STORY_FILENAME:
                yield path
            continue
        yield from _walk_canonical_story_files(path, ignore_dir_names=ignore_names)
