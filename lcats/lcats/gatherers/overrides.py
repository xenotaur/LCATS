"""Versioned per-story text overrides applied at gather time.

Some corpus defects are judgment calls that the measured repair rules in
``lcats.analysis.corpus.repairs`` cannot safely cover -- for example
``Ângstrom`` (a stray ``Â`` that a human reads as ``Ångstrom``) is not a clean
encoding-family decode, so it is not a rule. This module lets such fixes live
as versioned repo inputs, keyed by collection and story id, applied by the
normalization hook *after* the rule pass.

Because ``data/`` is cleared and regenerated after major changes, these
overrides -- like the rule table -- are replayable inputs to regeneration, not
edits to stored files. They deliberately live under the package
(``lcats/gatherers/overrides/``), never under ``data/``, so regeneration and
story discovery never touch or wipe them.

Schema (``overrides/<collection>.json``)::

    {
      "<story_id>": [
        {
          "find": "<exact substring, with enough context to be unique>",
          "replace": "<replacement text>",
          "rationale": "<why this is a judgment call, not a rule>",
          "reviewer": "<who decided>"
        }
      ]
    }

``story_id`` is the story's filename stem (e.g. ``f_o_b_venus__bond``). WI-
RESIDUAL-0019 populates these files during human review; this module provides
the mechanism and one canonical seed entry.
"""

import functools
import json
import pathlib
import warnings

# Overrides live beside this module, never under data/, so they survive
# cache-clear + regeneration and are never discovered as story JSON.
OVERRIDES_DIR = pathlib.Path(__file__).parent / "overrides"

# Recorded in provenance so a regenerated corpus can be traced to its overrides.
OVERRIDE_SOURCE = "lcats.gatherers.overrides"


def overrides_path(collection: str) -> pathlib.Path:
    """Return the overrides file path for a collection (may not exist)."""
    return OVERRIDES_DIR / f"{collection}.json"


@functools.lru_cache(maxsize=None)
def load_overrides(collection: str) -> dict:
    """Return the ``{story_id: [entry, ...]}`` overrides map for a collection.

    Returns an empty dict when the collection has no overrides file.

    The result is cached per collection for the lifetime of the process: the
    files are versioned inputs and effectively immutable during a gather run,
    and ``normalize_story_dict`` is called once per story. Callers must treat
    the returned dict as read-only; use ``load_overrides.cache_clear()`` if a
    file changes on disk within a process (e.g. in a test).

    Args:
        collection: The collection (target directory) name, e.g.
            ``mass_quantities``.

    Returns:
        A mapping of story id to a list of override entry dicts.
    """
    path = overrides_path(collection)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def apply_overrides(body, entries):
    """Apply override entries to a story body, returning ``(body, applied)``.

    Each entry is a literal ``find`` -> ``replace`` substitution. An entry is
    skipped with a visible warning rather than silently, since a stale override
    usually signals a story-text change that needs re-review, when its ``find``
    is empty, equals its ``replace`` (a no-op that would otherwise stamp
    provenance without changing the body), or is absent from the body. Only
    entries that actually change the body are recorded in ``applied``; when none
    do, the original ``body`` object is returned unchanged and ``applied`` is
    empty.

    Args:
        body: The story body text (already rule-normalized).
        entries: A list of override entry dicts for this story.

    Returns:
        A tuple of the updated body and a deterministic list of applied-entry
        provenance dicts (``find``/``replace``/``rationale``/``reviewer``/
        ``count``), in entry order.
    """
    if not isinstance(body, str) or not entries:
        return body, []

    updated = body
    applied = []
    for entry in entries:
        find = entry.get("find", "")
        replace = entry.get("replace", "")
        if not find or find == replace:
            warnings.warn(
                f"override is empty or a no-op (find == replace), skipping: {find!r}",
                stacklevel=2,
            )
            continue
        count = updated.count(find)
        if count == 0:
            warnings.warn(
                f"override find text not present, skipping: {find!r}",
                stacklevel=2,
            )
            continue
        updated = updated.replace(find, replace)
        applied.append(
            {
                "find": find,
                "replace": replace,
                "rationale": entry.get("rationale", ""),
                "reviewer": entry.get("reviewer", ""),
                "count": count,
            }
        )
    return updated, applied
