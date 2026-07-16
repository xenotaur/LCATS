# Corpus promotion: data/ to corpora/

`corpora/` is a periodic release snapshot; `data/` is the live working corpus,
cleared and regenerated after major changes (see `project/design/design.md`'s
State and Persistence Boundary). Promotion copies collections from `data/`
into `corpora/`, gated on a passing special-character survey, so stale
encoding damage cannot silently re-enter the release snapshot the way the
pre-2026-07 `corpora/` snapshot did (148 stories of stale mojibake, from a
promotion that happened without a quality gate).

## Command

```bash
lcats promote [collection ...] [--source data/] [--dest ../corpora] [--dry-run]
```

- With no `collection` arguments, every subdirectory under `--source` is
  considered.
- Every requested collection is surveyed first, as one complete phase; only
  once all surveys finish does copying begin. Each collection is still gated
  **independently** (a deliberate, documented mode — not an all-or-nothing
  whole-corpus gate): a collection with any mojibake (`likely_repairable`)
  finding is skipped and its findings are printed to stderr, while every
  other clean collection is still promoted, so an unrelated collection that
  still needs regeneration doesn't hold the rest hostage.
- A clean collection **wholesale-replaces** its `corpora/` counterpart (the
  destination directory is removed, then the source directory is copied), so
  files removed from `data/` since the last promotion don't linger in
  `corpora/`.
- Refuses to run (exit `2`) if `--source` and `--dest` resolve to the same
  directory or are nested inside one another — this would otherwise delete
  the source before the copy could run.
- Exit code is `0` when every considered collection promoted, `1` if any
  collection was blocked, `2` on a usage/environment error (missing source
  directory, unknown collection name, unsafe source/dest paths).
- `--dry-run` surveys and reports without copying any files.

This tool builds and gates promotion; it does not decide *when* to promote —
running it (for real, not `--dry-run`) is a release-time human action.

## Collection-name mapping

The mapping is **identity**: a `data/` collection promotes to `corpora/` under
the same name. There is no rename or merge table.

This was resolved 2026-07-16, before any external LCATS release, by adopting
`data/`'s current names as canonical everywhere. Two `corpora/` collections
previously used older, divergent names:

| `data/` collection (canonical) | Legacy `corpora/` name | Relationship |
|---|---|---|
| `ohenry-four_million` (25 stories) | `ohenry` (25 stories) | Same 25 stories, identical filenames — a straight rename. |
| `ohenry-whirligigs` (24 stories) | *(none)* | A second O. Henry collection ("Whirligigs"), never previously promoted — not a merge target. |
| `wilde_happy_prince` (5 stories) | `wilde` (5 stories) | Same 5 stories, identical filenames — a straight rename. |

All other collections (`anderson`, `chesterton`, `grimm`, `hemingway`,
`london`, `lovecraft`, `mass_quantities`, `sherlock`, `wodehouse`) already use
identical names in both trees.

### One-time manual cleanup

`lcats promote` only ever touches the destination directory matching a source
collection's own name — it does not know that `corpora/ohenry` and
`corpora/wilde` are the old identities of `ohenry-four_million` and
`wilde_happy_prince`, and it will not delete them automatically. The first
real promotion under this scheme should include, as part of that same change:

```bash
git rm -r corpora/ohenry corpora/wilde
lcats promote  # populates ohenry-four_million, ohenry-whirligigs, wilde_happy_prince, ...
```

This is a one-time historical correction, not a recurring promotion step.
