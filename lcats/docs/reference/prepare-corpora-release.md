# Preparing a corpora release

This is a manual runbook. Every command below is meant to be copy-pasted into
a plain terminal — it does not assume Claude, an agent, or any tool beyond a
shell and this repository checked out locally. If a step doesn't produce the
output shown, stop and report it rather than continuing to the next step.

`corpora/` is LCATS's periodic release snapshot; `data/` is the live working
corpus, rebuilt from upstream sources as needed. This runbook clears the
local working corpus, regenerates it from scratch, verifies it's free of
encoding damage, and promotes it into `corpora/` — the actual release step.

Each step below states which directory to run it from. LCATS is laid out as:

```
<repo root>/
├── corpora/        # the release snapshot (this runbook's destination)
└── lcats/           # the Python package and all tooling (this runbook's
                      # working directory for most steps)
```

## 1. Pre-flight

**Directory:** `lcats/` (the package directory, not the repo root).

Set up the environment once per machine, per `lcats/README.md`'s own
"Building" section:

```bash
cd LCATS/lcats
scripts/clean && scripts/build && scripts/develop
lcats info
```

`lcats info` should print a one-line description of LCATS. If it errors
with a missing-package message, you are likely using a system/Homebrew
Python rather than the conda environment `scripts/develop` installed into —
re-activate the conda environment and re-run `scripts/develop`.

## 2. Clear stale local state

**Directory:** `lcats/`.

Most gatherers skip any story file that already exists on disk (no
`--force` flag exists to override this), so without this step "regenerate"
below can silently leave old files in place. `mass_quantities` is the one
exception — it always overwrites its story files — but the real risk this
step guards against applies to every collection either way: `lcats gather`
never *deletes* outputs it no longer produces, so a story dropped from the
source list (or renamed) leaves a stale file behind that `lcats survey` and
`lcats promote` will still scan. `data/` is a regenerable cache (unlike
`corpora/`, nothing here is precious):

```bash
lcats clean
```

`lcats clean` clears every `data/<gatherer>` directory and every cache
mechanism: `cache/resources`, plus `mass_quantities`'s separate
`cache/texts`/`cache/tmp` and its Gutenberg metadata cache
(`cache/gutenbergindex.db`, `cache/rdf-files.tar.bz2`). It's safe on a
symlinked `data/`/`cache/` setup (some machines point these at a
scratch/tempspace location, to keep large regenerated data out of a
backup system) — only contents are ever removed, never the directory or
symlink itself — and it self-heals a dangling symlink it encounters along
the way (one whose target directory no longer exists), rather than
crashing on the next `lcats gather` the way a bare `os.makedirs` does.

Clearing the Gutenberg metadata cache means the *first* metadata lookup
in the next `lcats gather mass_quantities` rebuilds it from scratch —
downloading and parsing the whole Gutenberg RDF catalog, not just the
per-story text this section already warns about. Expect that one rebuild
to take a while, regardless of how small a subset of `mass_quantities`
you're regenerating.

To re-check a single collection instead of the whole corpus, scope the
clear to just that gatherer, e.g. `lcats clean mass_quantities`. This
intentionally does **not** touch `cache/`, and scope every following
command in this runbook to that same collection name too (`lcats survey
--mode specials data/mass_quantities --no-progress`, `lcats promote
replace mass_quantities --dry-run`, `lcats promote replace
mass_quantities`) rather than running the unscoped forms — those consider every collection under
`data/`, including ones you did not just regenerate. Clear the cache too
with `lcats clean --cache-only`, if you specifically need a from-network
recheck of that one collection (see the note on `lcats gather` below).

(If `lcats` isn't on `PATH` yet — e.g. you're troubleshooting the
Pre-flight step above and haven't finished `scripts/develop` — the
equivalent raw shell command is
`sh -c 'rm -rf data/* data/.[!.]* data/..?*'`. The three glob patterns
together (`data/*`, `data/.[!.]*`, `data/..?*`) are the standard portable
idiom for "every entry, dotfiles included, excluding `.`/`..` themselves"
— a bare `data/*` misses dotfiles. Running the globs under `sh -c '...'`
rather than directly is deliberate, not stylistic: zsh's default options
abort with `no matches found` if *any one* of the three globs doesn't
match anything, while `/bin/sh` doesn't have that behavior. Unlike
`lcats clean`, this fallback does not self-heal a dangling symlink.)

## 3. Regenerate

**Directory:** `lcats/`.

```bash
lcats gather
```

`lcats gather` takes optional gatherer names and defaults to running every
gatherer when none are given, so the bare command above regenerates the
whole corpus. The full list of gatherer names, if you want to target one:
`sherlock`, `lovecraft`, `ohenry_four_million`, `ohenry_whirligigs`,
`hemingway`, `wilde_happy_prince`, `wodehouse`, `grimm`, `anderson`,
`chesterton`, `london`, `mass_quantities` — for example:

```bash
lcats gather mass_quantities
```

This reads from the `cache/resources` cache when a source page is already
cached there, and only hits Project Gutenberg over the network for pages
that aren't. Expect it to take a while for the full corpus either way,
`mass_quantities` in particular (it's by far the largest collection). To
force a genuinely fresh, fully-networked run, clear the cache too:
`lcats clean --cache-only` (or bare `lcats clean`, which clears both
`data/` and `cache/` together — see step 2 above).

## 3b. Seed the tranche-promoted sidecars

**Directory:** `lcats/`.

`lcats clean` empties `data/`, and `lcats gather` regenerates stories only. The
146 `genre.json` sidecars promoted by PR #362 exist only in `corpora/`, so
nothing above puts them back into `data/` — and `lcats promote replace` then
refuses (exit `1`, `orphaned sidecar` blocks, 7 collections) rather than delete
them. This step restores them into `data/`, from the tracked evidence file, so
`data/` is the complete release source. It adds sidecars only: no story file is
touched.

**Full release** (you ran a bare `lcats clean` and `lcats gather`). Build the
seed manifest outside the repository, then preview and apply it:

```bash
SEED="$(mktemp -d)/genre_seed.jsonl"
python tools/build_genre_seed_manifest.py --manifest-out "$SEED" --expect-count 146
lcats promote insert --sidecar genre --tranche-manifest "$SEED" --dest data/ --dry-run
```

The build prints `146 seed records (146 cache_db_path values reduced to a
basename); manifest written to ...`. The `--dry-run` prints 146 lines of
`would promote sidecar: <collection>/<story>` and exits `0`; it writes nothing.
**Only if it did exactly that**, apply it:

```bash
lcats promote insert --sidecar genre --tranche-manifest "$SEED" --dest data/
```

Expected: 146 `promoted sidecar: <collection>/<story>` lines, exit `0`.

**Single-collection release** (you ran `lcats clean <collection>` and
`lcats gather <collection>`). `data/` still holds the sidecars you seeded for
every other collection, and `promote insert` has no collection selector, so the
full manifest would be rejected for all of them. Seed only the collection you
regenerated, from a manifest filtered to it. Build `$SEED` as above, then:

```bash
COLLECTION=wodehouse
grep -F "\"lcats_id\": \"$COLLECTION/" "$SEED" > "${SEED%.jsonl}_$COLLECTION.jsonl"
wc -l < "${SEED%.jsonl}_$COLLECTION.jsonl"
lcats promote insert --sidecar genre --tranche-manifest "${SEED%.jsonl}_$COLLECTION.jsonl" --dest data/ --dry-run
```

Then apply it exactly as above (same `--tranche-manifest`, no `--dry-run`) once
the dry-run is clean. The trailing `/` in the pattern keeps one collection name
from matching another that begins with it. Only seven collections have seeded
sidecars today; the filtered line count must be:

| Collection | Lines | Collection | Lines |
|---|---|---|---|
| `anderson` | 18 | `lovecraft` | 10 |
| `chesterton` | 12 | `mass_quantities` | 84 |
| `grimm` | 2 | `wodehouse` | 12 |
| `london` | 8 | every other collection | 0 |

The counts sum to 146. A collection with `0` has nothing to seed: skip this step
for it, and a scoped `lcats promote replace <collection>` is not blocked. If a
collection in the table with a non-zero count gives `0`, the filter did not match
(the pattern depends on the manifest's `"lcats_id": "` spacing); stop rather than
skip, because the scoped `replace` would then be blocked.

**If the dry-run fails** (exit `1`, `rejected:` lines — typically `no story.json
at data/<collection>/<story>`, meaning regeneration no longer produces a story
that has a seeded sidecar, or `gather` did not finish): nothing was written. Fix
the cause and re-run the dry-run. Do not run the real `insert` until it reports
exactly the expected count with exit `0`.

**If the real `insert` reports any rejection:** `insert` writes record by
record and is not transactional, so the other records were written. Do not
continue to step 4 or on to `replace`, and do not just retry — a retry on the
same `data/` rejects every sidecar already written (exit `1`). The step 6
preview does not catch this either: after a partial `insert` it can still exit
`0` and look clean, so the stop rule here is the only guard. Restore a clean
`data/` (re-run step 2 and step 3, scoped to the collection for a
single-collection release), fix the cause, and re-run the dry-run and the
`insert` from scratch.

**If a pipeline-produced `genre.json` is already in `data/`** (for example from
`lcats annotate`): `insert` refuses and exits `1`. Do not switch to `upsert` — it
overwrites the whole file and would silently discard that file's assessments.
Stop and decide the precedence deliberately.

Never pass `--allow-orphaned-sidecar-deletion` to avoid this step: it disables
the orphaned-sidecar guard for every collection and every sidecar kind at once.
The seeded sidecars carry no story-text fingerprint, so they are not checked
against the regenerated story text.

## 4. Verify

**Directory:** `lcats/`.

```bash
lcats survey --mode specials data/ --no-progress
```

**Clean result:** no output, exit code `0`.

**Problem result:** one block per flagged file, e.g.:

```
data/mass_quantities/deny_the_slake__wilson/story.json
  [spchar] error: Special character finding. (U+00C3, 'Ã')
    context: em a resumÃ©.\n\n"As I s
```

> **Note:** the path reflects the current per-story-bucket layout
> (`<collection>/<story>/story.json`). This specific illustrative finding
> no longer reproduces — the real corpus has since been cleaned by a
> separate workstream (`WS-SPECIALS-CLEANUP`) — but the output *shape* is
> otherwise still accurate. See `project/design/backlog.md`.

and a non-zero exit code. If you see findings after a genuine fresh
regeneration (step 2 done first), that's real information, not a false
positive — see "If verification finds problems" below.

## 5. Inspect (optional diagnostic)

**Directory:** `lcats/`.

For any flagged file, this shows exactly what the repair pipeline would
propose, without changing anything:

```bash
lcats repair-specials data/mass_quantities/deny_the_slake__wilson/story.json --format jsonl
```

Each line is one proposed fix (`rule_id`, `original_text`, `replacement_text`,
`rationale`). This is read-only — it never modifies the file.

## 6. Preview promotion

**Directory:** `lcats/`.

```bash
lcats promote replace --dry-run
```

Reports, per collection, either `would promote: <name> -> <name>` or
`blocked: <name> (N finding(s) across M stories)` with the specific findings
listed. If it instead shows `blocked: ... orphaned sidecar(s)`, step 3b was
skipped or did not finish: go back and seed before continuing. This makes no
changes regardless of what it finds — see
[`corpus-promotion.md`](corpus-promotion.md) for the full command reference,
including `--source`/`--dest` and why they default correctly only when run
from `lcats/`.

## 7. Promote (the actual release step)

This step changes tracked files in `corpora/`. Everything above this line is
read-only.

The `cd` commands below use `git rev-parse --show-toplevel` rather than a
relative `cd ..`/`cd lcats`, so they work regardless of whether you run 7a,
skip it, or run these steps out of order.

**7a. One-time historical cleanup — directory: repo root** (`corpora/` does
not exist under `lcats/`, so this fails if run from there):

```bash
cd "$(git rev-parse --show-toplevel)"
git rm -r corpora/ohenry corpora/wilde
```

This is a one-time correction for two legacy collection names, documented in
full in [`corpus-promotion.md`](corpus-promotion.md#collection-name-mapping).
Skip this step if it's already been done (i.e. `corpora/ohenry` and
`corpora/wilde` no longer exist).

**7b. Promote — directory:** `lcats/`:

```bash
cd "$(git rev-parse --show-toplevel)/lcats"
lcats promote replace
```

If this exits `0`, every collection promoted and `corpora/` now reflects the
regenerated `data/`. Commit the result as its own PR.

If it exits `1` with `orphaned sidecar` blocks, a registered sidecar (for
example `genre.json`) exists in `corpora/` for a story but not in the
regenerated `data/`, and `replace` refused to delete it for that collection.
Exit `1` does not mean nothing changed: collections that were not blocked are
still promoted (each collection is gated independently). The usual cause is a
skipped or unfinished [step 3b](#3b-seed-the-tranche-promoted-sidecars): seed
`data/`, re-run the step 6 preview, and promote again. Do **not** pass
`--allow-orphaned-sidecar-deletion` to get past this: it disables the guard for
every collection and every sidecar kind at once, and it would delete the 146
tranche-promoted `genre.json` sidecars. See
[`genre-sidecars-in-release-workflow.md`](../../project/design/genre-sidecars-in-release-workflow.md)
for why this happens.

## If verification finds problems

A finding after a genuine fresh regeneration (step 2 → 3 → 3b → 4, in order) means
a defect exists that the current rule table, override files, or allowlist
don't yet cover. Do not edit the story JSON directly — every fix is a
versioned pipeline input:

- A clean, general encoding-family fix → a new rule in
  `lcats/analysis/corpus/repairs.py`'s `DEFAULT_REPAIR_RULES`.
- A one-off, story-specific judgment call → a new entry in
  `lcats/gatherers/overrides/<collection>.json`.
- A legitimate character that shouldn't be flagged at all → a new entry in
  `lcats/analysis/corpus/allowlists/corpus_specials.json`.

This is the same disposition method used to reach the current clean state;
see the `WI-RESIDUAL-0019` execution record for worked examples of each.

Whenever you re-run step 2 or step 3 to re-check a fix, `data/` is emptied or
partly regenerated again, so re-run [step 3b](#3b-seed-the-tranche-promoted-sidecars)
before step 4 and the preview.

## Optional next step: quality/genre assessment

**Directory:** `lcats/`.

Once `corpora/` is promoted, `lcats assess` can score the release for
quality and genre fit using the Claude API. This is a separate, optional
step from the promotion above — not part of the release itself — and,
unlike everything above, it is **not free**: it calls a real model on every
story you point it at. Always preview first. `corpora/` is a sibling of
`lcats/`, not under it, so from this section's `lcats/` working directory
the path is `../corpora/`:

```bash
lcats assess ../corpora/ --genre "science fiction" --dry-run
```

`--dry-run` runs the same pre-flight checks (file discovery, body-length
limits) without calling the API, so it's safe to run anytime. `--genre` is
one of `science fiction`, `horror`, `humor`, `western`, `romance`,
`mystery`, `fantasy`, `adventure`; omit it to run detect mode instead of
genre-lens mode. A real run needs an API key and your explicit go-ahead:

```bash
ANTHROPIC_API_KEY=sk-... lcats assess ../corpora/ --genre "science fiction" --format tsv --output sf_assessment.tsv
```

See [`lcats assess`'s how-to guide](../../src/lcats/analysis/corpus/README.md#9-story-assessment-lcats-assess)
for the full option reference, output formats, and manual prompt-validation
guidance.
