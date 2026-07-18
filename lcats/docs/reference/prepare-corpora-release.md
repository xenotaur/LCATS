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
mass_quantities --dry-run`, `lcats promote mass_quantities`) rather than
running the unscoped forms — those consider every collection under
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

## 4. Verify

**Directory:** `lcats/`.

```bash
lcats survey --mode specials data/ --no-progress
```

**Clean result:** no output, exit code `0`.

**Problem result:** one block per flagged file, e.g.:

```
data/mass_quantities/deny_the_slake__wilson.json
  [spchar] error: Special character finding. (U+00C3, 'Ã')
    context: em a resumÃ©.\n\n"As I s
```

and a non-zero exit code. If you see findings after a genuine fresh
regeneration (step 2 done first), that's real information, not a false
positive — see "If verification finds problems" below.

## 5. Inspect (optional diagnostic)

**Directory:** `lcats/`.

For any flagged file, this shows exactly what the repair pipeline would
propose, without changing anything:

```bash
lcats repair-specials data/mass_quantities/deny_the_slake__wilson.json --format jsonl
```

Each line is one proposed fix (`rule_id`, `original_text`, `replacement_text`,
`rationale`). This is read-only — it never modifies the file.

## 6. Preview promotion

**Directory:** `lcats/`.

```bash
lcats promote --dry-run
```

Reports, per collection, either `would promote: <name> -> <name>` or
`blocked: <name> (N finding(s) across M stories)` with the specific findings
listed. This makes no changes regardless of what it finds — see
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
lcats promote
```

If this exits `0`, every collection promoted and `corpora/` now reflects the
regenerated `data/`. Commit the result as its own PR.

## If verification finds problems

A finding after a genuine fresh regeneration (step 2 → 3 → 4, in order) means
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
one of `science fiction`, `horror`, `western`, `romance`; omit it to run
detect mode instead of genre-lens mode. A real run needs an API key and
your explicit go-ahead:

```bash
ANTHROPIC_API_KEY=sk-... lcats assess ../corpora/ --genre "science fiction" --format tsv --output sf_assessment.tsv
```

See [`lcats assess`'s how-to guide](../../lcats/analysis/corpus/README.md#9-story-assessment-lcats-assess)
for the full option reference, output formats, and manual prompt-validation
guidance.
