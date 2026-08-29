# Corpus promotion: data/ to corpora/

`corpora/` is a periodic release snapshot; `data/` is the live working corpus,
cleared and regenerated after major changes (see `project/design/design.md`'s
State and Persistence Boundary). `replace` mode copies whole collections
from `data/` into `corpora/`, gated on a passing special-character survey,
so stale encoding damage cannot silently re-enter the release snapshot the
way the pre-2026-07 `corpora/` snapshot did (148 stories of stale mojibake,
from a promotion that happened without a quality gate). `insert`/`upsert`
promote individual sidecars via a validated manifest instead — they are
not survey-gated the way `replace` is.

## Command

An explicit mode is mandatory (`WI-PROMOTE-0097`): `lcats promote` with no
mode refuses rather than defaulting to any behavior. This closes the
data-loss hazard between additive sidecar promotion and wholesale
collection replacement — a mode name always says which one you're getting.

```bash
lcats promote replace [collection ...] [--source data/] [--dest ../corpora] [--dry-run] [--allow-orphaned-sidecar-deletion]
lcats promote insert --sidecar <kind> (--tranche-manifest <path.jsonl> | --source <dir>) [--dest ../corpora] [--allow-unvalidated] [--dry-run]
lcats promote upsert --sidecar <kind> (--tranche-manifest <path.jsonl> | --source <dir>) [--dest ../corpora] [--allow-unvalidated] [--dry-run]
```

### `replace` — wholesale collection replacement

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
- **Orphaned-sidecar guard** (`WI-PROMOTE-0101`): an otherwise-clean
  collection is also blocked by default if the wholesale replace would
  delete a *registered* sidecar kind (via the same registry `insert`/
  `upsert` use) that exists at the destination for a story but is missing
  from the corresponding source — the scenario where a collection was
  `upsert`-into since its last `replace`, and a later `replace` would
  silently wipe that work. Only registered kinds are checked, never a
  generic "any destination-only file" diff, to avoid false positives on
  legitimate corpora-only content unrelated to sidecar promotion. A
  destination collection that doesn't exist yet is never blocked — there
  is nothing to orphan on a first-time promotion. `--allow-orphaned-
  sidecar-deletion` overrides the guard and restores the unguarded
  wholesale behavior, per invocation. `insert`/`upsert` are entirely
  unaffected — they are structurally incapable of deleting anything
  regardless of flags.
- Exit code is `0` when every considered collection promoted, `1` if any
  collection was blocked (mojibake, malformed sidecar, or orphaned
  sidecar), `2` on a usage/environment error (missing source directory,
  unknown collection name, unsafe source/dest paths).
- `--dry-run` surveys and reports without copying any files.

This tool builds and gates promotion; it does not decide *when* to promote —
running it (for real, not `--dry-run`) is a release-time human action.

### `insert`/`upsert` — additive sidecar promotion

Both modes promote sidecars named in a JSONL manifest into existing story
buckets under `--dest`, without touching any other file in the destination
bucket or collection. `insert` is create-only (refuses, does not overwrite,
if the destination sidecar already exists); `upsert` is create-or-overwrite
(whole-file only — it never merges sidecar content).

- `--sidecar <kind>` selects the registered sidecar kind to promote (e.g.
  `genre`, `scenes`, `linguistics`, `linguistics.tokens.json`). A value with
  no `.` assumes `.json`; a value containing `.` is matched exactly against
  the registry, with no inference.
- Exactly one of two sourcing modes is required — `--tranche-manifest` and
  `--source` are mutually exclusive:
  - `--tranche-manifest <path.jsonl>` reads a JSONL manifest, one
    **envelope** object per line: `{"lcats_id": "<destination story id>",
    "payload": {<sidecar content>}}`. The envelope's `lcats_id` is what
    routes the write — never the payload's own fields, since some sidecar
    kinds (e.g. `scenes.json`) carry no story-identity field of their own.
    A manifest line with no `"payload"` field is also accepted when it
    carries its own non-empty top-level `lcats_id` (a bare legacy record,
    e.g. an existing `genre-sidecar-v1` manifest) — the whole record is
    then treated as the payload.
  - `--source <dir>` scans `<dir>/<collection>/<story>/<sidecar-filename>`
    directly — no manifest file needed. Every story bucket under `<dir>`
    that already has the named `--sidecar` file is promoted; a bucket
    without it is silently skipped, not reported. The bucket's own path
    relative to `<dir>` (e.g. `anderson/bell`) is always the routing
    `lcats_id` — a scanned sidecar's own identity field, if any, is
    validated to agree with that routing `lcats_id` and rejected on
    mismatch, the same as a manifest record would be.
  Both modes feed the exact same validation, escape-check,
  identity-agreement, and existing-destination-file logic — scanning is
  purely an alternative way to source records, not a second promotion
  engine.
- Every `--sidecar` kind is validated against a shared registry by default;
  `--allow-unvalidated` permits promoting a kind with **no registered
  validator** — it never bypasses a registered validator's own rejection of
  malformed content.
- Neither mode creates a destination story bucket — `lcats_id` must name a
  bucket that already has a `story.json`.

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
lcats promote replace  # populates ohenry-four_million, ohenry-whirligigs, wilde_happy_prince, ...
```

This is a one-time historical correction, not a recurring promotion step.
