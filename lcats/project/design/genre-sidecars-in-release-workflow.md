# Genre sidecars in the standard corpus release workflow

Status: investigation result for `WI-PROMOTE-0108` (2026-10-07). Recommendation
and follow-up list only; nothing here is implemented beyond one small doc note
in `docs/reference/prepare-corpora-release.md`.

## Question

The documented release (`docs/reference/prepare-corpora-release.md`, steps 2-7)
clears `data/`, regenerates it, surveys it, and ends with a plain
`lcats promote replace`, which wholesale-replaces each collection in
`corpora/` with its `data/` counterpart. The 146 `genre.json` sidecars from
PR #362 (`WI-GENRE-0077`) exist **only** in `corpora/`. How should they become
part of the repeatable release, so the release does not depend on the
orphaned-sidecar guard (`WI-PROMOTE-0101`) alone?

## Why the guard is a safeguard, not a release source

Verified against `promote.py` and by dry-run (commands below):

- `replace` does `shutil.rmtree(dest)` then `shutil.copytree(source, dest)` per
  collection (`_copy_collection`). Anything at the destination that is not in
  the source is deleted.
- The guard (`_find_orphaned_sidecars`) only blocks that deletion, and only for
  registered sidecar kinds, only for stories present in both trees, and only
  until `--allow-orphaned-sidecar-deletion` is passed.
- The release procedure never puts the sidecars into `data/`: `lcats clean`
  empties `data/`, `lcats gather` regenerates stories only, and nothing in the
  documented steps produces `genre.json` there.

Observed result of a bare release run today (`replace --dry-run`, source = a
populated `data/` of 12 collections, destination = this repo's `corpora/`):

| Run | Exit | Outcome |
|---|---|---|
| `lcats promote replace --dry-run` | 1 | 7 collections blocked (anderson 18, chesterton 12, grimm 2, london 8, lovecraft 10, mass_quantities 84, wodehouse 12 = 146 orphaned sidecars); 5 would promote |
| same, plus `--allow-orphaned-sidecar-deletion` | 0 | all 12 would promote, i.e. all 146 sidecars deleted |

So the documented step 7b ("if this exits 0, every collection promoted") is
reached against the current `corpora/` only by passing the override. The
runbook never mentions that flag, but each blocked line in the CLI output ends
"pass --allow-orphaned-sidecar-deletion to delete it anyway", so an operator
who hits the block is pointed at the one flag that destroys the evidence. The
override is a single global switch: it also disables the guard for every other
registered sidecar kind (`scenes.json`, `linguistics.json`,
`linguistics.tokens.json`) in every collection.

## What the evidence actually is (a finding that constrains every option)

- The 146 sidecars are derived from the tracked file
  `experiments/05_metadata_genre_prefilter/results/full_scan/validation_results.jsonl`
  (146 bare `genre-sidecar-v1` records). It is committed, it is the adjudicated
  Opus validation evidence from `WI-GENRE-0004`, and `WI-GENRE-0077` forbade
  modifying it.
- After the `WI-GENRE-0109` rewrite (PR #477), the current `corpora/` genre
  sidecars equal that evidence in every field except `cache_db_path`
  (checked: 0 of 146 differ once `cache_db_path` is reduced to a basename).
- **The tracked evidence still contains 146 absolute `cache_db_path` values.**
  Replaying it unchanged into a release would re-introduce the leak that
  `WI-GENRE-0109` removed. Verified: seeding a scratch `data/` from the raw file
  and grepping the result found 146 absolute paths.
- A genre sidecar carries no story-text hash or fingerprint (no hash/sha/digest
  field anywhere in a sample sidecar). Once story text changes, a replayed
  sidecar silently describes old text.

## Options

### A. Replay a tracked manifest *after* `replace`, using the override flag

`replace --allow-orphaned-sidecar-deletion`, then
`upsert --sidecar genre --tranche-manifest <manifest> --dest ../corpora`.

- Pro: no change to `replace`; small.
- Con: deliberately defeats the guard for all collections and all sidecar kinds
  during the window; a failed or skipped replay leaves a published corpus with
  no sidecars; an unrelated orphan (a `linguistics.json` not in the manifest)
  is deleted silently; needs a sanitized manifest.

### B. Regenerate sidecars in `data/` with the pipeline (`lcats annotate`)

- Pro: no tracked manifest; the natural path for pipeline-produced sidecars
  (they already flow through `replace`).
- Con: re-runs paid model calls and produces different, non-adjudicated labels.
  It cannot recreate the validated Opus evidence or any human adjudication. Not
  viable for tranche-promoted, adjudicated sidecars.

### C. Seed `data/` from a tracked manifest *before* `replace` (recommended)

`upsert --sidecar genre --tranche-manifest <sanitized manifest> --dest data/`,
then the unchanged `replace`.

- Pro: `data/` becomes the complete release source; `replace` semantics and the
  guard stay exactly as they are, and the guard remains an active safety net;
  no override flag; the seed step is validated by the same registry validator;
  an ID that no longer matches a regenerated bucket is rejected loudly (exit 1).
- Con: one more release step; needs a tracked, sanitized manifest; each future
  adjudicated sidecar kind needs its own manifest; stale evidence is still
  possible (no text hash).
- Verified end to end on scratch copies (see Reproduction): seeding a copy of
  `data/` with the sanitized manifest, then running a bare `replace` into a copy
  of `corpora/`, exited 0 with 12 promoted and 0 blocked, and all 146 resulting
  `genre.json` files were byte-identical to the ones in `corpora/`.

### D. Restore from git after `replace`

`replace` with the override, then `git restore` the sidecar paths.

- Same weaknesses as A, plus no validator on the restored files. Rejected.

### E. A tracked sidecar tree mirrored into `data/`

Equivalent to C with a directory of 146 files in place of one JSONL, but it
duplicates `corpora/` and severs the link to the adjudicated evidence file.
Viable, heavier, no advantage over C.

### F. Change `replace` to preserve registered sidecars

Contradicts the shape of `PROP-LCATS-PROMOTE-MODE-REDESIGN` Decision 6 (`replace`
stays a wholesale replacement and is protected by a refuse-by-default guard, not
by preserving destination content) and this work item's Non-Goals. Rejected.

## Recommendation: Option C

Make `data/` the complete release source. Two kinds of sidecar, one rule:

- **Pipeline-produced sidecars** (`lcats annotate` writes into `data/`) already
  flow through `replace`. No change.
- **Adjudicated or tranche-promoted sidecars** (the 146 genre sidecars; a future
  linguistics tranche) are seeded into the freshly regenerated `data/` from a
  tracked, sanitized manifest before `replace`.

Do not edit `validation_results.jsonl`. Sanitize at seed time (or derive a
separate tracked seed manifest) so the evidence stays immutable and the
absolute paths are removed on the way in.

### Failure modes to design for

| Failure | Behaviour with Option C |
|---|---|
| Seed record names a bucket that regeneration no longer produces | `upsert` rejects it, exit 1; release stops before `replace` |
| Operator skips the seed step | `replace` is blocked by the guard (exit 1), as today; nothing is deleted |
| Operator passes the override flag anyway | sidecars deleted; documented as the one thing not to do (see doc note below) |
| Story text changed since the evidence was produced | **not detected** (no text hash); needs the schema follow-up |
| Raw evidence replayed unsanitized | re-introduces 146 absolute paths; the seed step must sanitize |

## Drafted revised release procedure (text only; not applied)

Between today's step 6 (preview) and step 7 (promote), add:

> **6b. Seed adjudicated sidecars into `data/`** — directory `lcats/`.
> `lcats` regenerated `data/` contains stories but not tranche-promoted
> sidecars. Seed them from the tracked seed manifest, preview first:
> ```bash
> lcats promote upsert --sidecar genre --tranche-manifest <seed-manifest> --dest data/ --dry-run
> lcats promote upsert --sidecar genre --tranche-manifest <seed-manifest> --dest data/
> ```
> The dry-run must report one `would promote sidecar:` line per manifest record
> and exit 0; stop if any record is rejected.

and replace the 7b sentence "If this exits `0`, every collection promoted..." with:
"If this exits `0`, every collection promoted. Exit `1` with orphaned-sidecar
blocks means a sidecar exists in `corpora/` that is not in `data/`: re-check
step 6b. Do not pass `--allow-orphaned-sidecar-deletion` to get past it."

The 6b text depends on the follow-up manifest below, so only the 7b caution is
applied now (see the doc change in this PR).

## Follow-up work items implied

1. **Tracked, sanitized seed manifest and seed command** (deliverable). Decide
   the manifest's location; sanitize `cache_db_path` at seed time or derive a
   separate manifest; add a test that the seeded output equals the current
   `corpora/` sidecars. Reuse the logic in `tools/rewrite_genre_cache_db_path.py`.
2. **Add step 6b and the guard explanation to the release runbook**
   (`prepare-corpora-release.md`, `corpus-promotion.md`) once item 1 exists.
3. **Release preflight and rule for other sidecar kinds** (investigation).
   State the pipeline-vs-adjudicated rule for `linguistics.json` and
   `scenes.json`, and whether the preflight should assert that every
   `corpora/` sidecar has a counterpart in `data/` after seeding (the guard
   dry-run already reports this).
4. **Story-text binding for genre sidecars** (design). Add a story-text
   fingerprint to the sidecar provenance so a seeded sidecar can be detected as
   stale. Schema change; needs its own design pass. Optional, P3.

## Reproduction

All commands ran from `lcats/` with `PYTHONPATH=$(pwd)/src` (the default
editable install resolves to a different checkout) and the pinned toolchain.
Real trees were never written: scratch copies of `data/` (58 MB, 12
collections) and `corpora/` were used for every write.

```bash
# Bare release run, dry-run, real corpora as destination
lcats promote replace --source <data> --dest ../corpora --dry-run                  # exit 1, 7 blocked
lcats promote replace --source <data> --dest ../corpora --dry-run \
      --allow-orphaned-sidecar-deletion                                            # exit 0, 12 would promote

# Option C on scratch copies
lcats promote upsert --sidecar genre --tranche-manifest raw.jsonl   --dest scratch/data --dry-run   # 146 would promote
lcats promote upsert --sidecar genre --tranche-manifest clean.jsonl --dest scratch/data              # 146 promoted
lcats promote replace --source scratch/data --dest scratch/corpora                                   # exit 0, 12 promoted, 0 blocked
# 146 genre.json compared with corpora/: 0 byte-differing
```

`raw.jsonl` is `validation_results.jsonl` as tracked; `clean.jsonl` is the same
records with `cache_db_path` reduced to a basename. Seeding `raw.jsonl` into a
scratch `data/` produced 146 sidecars with absolute paths.
