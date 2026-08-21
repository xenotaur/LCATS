# Why stories live in per-story bucket directories

Every story in LCATS's `data/` and `corpora/` trees is stored as
`<collection>/<story>/story.json` — a dedicated directory per story,
holding a canonical `story.json` file and, often, sibling analysis
artifacts (`audit.json`, `scenes.json`, `events.json`, and similar
per-story outputs such as `linguistics.json`) alongside it.

This wasn't always the layout. Through mid-2026, a story was a single
flat file: `<collection>/<story>.json`. This page explains why LCATS
migrated away from that, what changed, and what's still true today.

## The problem with a flat file per story

A flat `<collection>/<story>.json` file conflates two different things
under one name: the story's own identity, and the one and only place its
content can live. That was fine as long as a story was *only* its own
JSON content. It stopped being fine once LCATS started producing sibling
analysis artifacts for a story — QA audits, scene segmentations,
extracted events — because there was no natural place to put them next to
the story they describe without inventing an ad hoc naming convention
(`<story>_audit.json`, `<story>.scenes.json`, ...) that would only get
messier as more artifact types appeared.

There was a second, quieter problem: identity. Code that needed to name a
story — for logging, for TSV output, for cross-referencing — used the
flat file's name stem (`<story>.json` → `<story>`). That's a reasonable
identifier only as long as the leaf filename varies per story. Once a
story becomes a directory holding a *canonical*, identically-named leaf
file (as any per-story-bucket scheme requires), the leaf stem is no longer
useful for identity — every story's leaf file has the same name. Something
else has to serve as the identifier instead.

## What changed

LCATS moved to one directory per story, with a single reserved leaf
filename:

```
data/<collection>/<story>/story.json
```

- **The directory's own name (its slug) is the story's identity**, not the
  leaf filename. It's stable, human-legible, and was already unique per
  collection — it's simply the old flat filename's stem, promoted from a
  filename convention to an actual directory name.
- **`story.json` is a reserved, canonical name** — the one and only file
  in a story's bucket that `lcats survey`, `lcats assess`, and `lcats
  promote` treat as *the* story. Every other file in that directory is
  sidecar content: expected, not an ambiguity to resolve case by case.
  (`lcats stats` is a partial exception — it still uses the broader,
  older `find_corpus_stories` selector rather than this canonical one, so
  it can pick up sidecar files too; this is a known, unresolved gap, not
  part of the migration's own design.)
- **`lcats survey`'s output that reports a story's identity** gained a
  dedicated `story_dir` column for this directory-slug identifier,
  alongside the existing columns — rather than repurposing an existing
  column's meaning, which would have silently broken anything already
  parsing it. (`lcats assess`'s separate TSV schema does not have this
  column.)
- **`lcats promote`** (the `data/` → `corpora/` release-promotion gate)
  now standingly rejects a collection where zero canonical stories are
  found — not just a collection with mojibake findings — so a writer
  regression that silently stopped producing real story buckets would be
  caught before reaching the release snapshot, not just once at
  migration time.

## How the migration was staged

This was a deliberately staged migration — Martin Fowler's [Parallel
Change](https://martinfowler.com/bliki/ParallelChange.html) (expand-contract)
pattern — rather than one atomic cutover:

1. **Read-path compatibility** — discovery and identity logic learned to
   recognize *both* the old flat layout and the new bucket layout, so nothing
   broke while the write side hadn't moved yet.
2. **Write-path migration** — the tools that actually produce story files
   (`lcats gather`'s downloaders and story-writing paths) switched to
   writing the bucket layout exclusively.
3. **Convergence** — tests, fixtures, and docs were normalized to the new
   layout, and an explicit end-to-end `lcats gather` → `lcats promote`
   validation pass confirmed the whole pipeline worked correctly against
   the new layout.
4. **Retraction** — once the real, tracked `corpora/` snapshot was
   confirmed fully migrated via an actual production `lcats gather` +
   `lcats promote` run (not just the code being ready), the temporary
   flat-layout read tolerance from step 1 was removed. A flat
   `<collection>/<story>.json` file is no longer recognized as a story by
   any LCATS tooling.

Step 4's timing was deliberate, not an oversight: retracting flat-layout
support in the same change that landed the convergence work would have
made every LCATS command stop finding the (still-flat) production corpus
until someone actually ran the real migration — an outage with no
code-level trigger to prevent it. Gating retraction on a confirmed,
evidence-backed migration closed that gap.

## Current state

As of the migration's completion, the flat layout is fully retracted: it
is not read, written, or tolerated anywhere in LCATS's story-discovery or
story-writing code. Every story under `data/` and `corpora/` is a bucket
directory. If you're looking for a specific story file on disk or in a
command's output, it's always `<collection>/<story>/story.json` — never a
flat `<collection>/<story>.json`.

## See also

- [Quickstart](../tutorials/quickstart.md) — worked examples using the
  current bucket-layout paths.
- [Preparing a corpora release](../reference/prepare-corpora-release.md) —
  the runbook that regenerates and promotes story buckets.
- [Per-story gather-time overrides](../reference/gather-overrides.md) —
  how per-story fixes are keyed by the directory-slug identity this page
  describes.
