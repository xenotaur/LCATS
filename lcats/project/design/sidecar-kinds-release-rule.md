# Release rule for sidecar kinds other than genre.json

Status: investigation result for `WI-PROMOTE-0117` (workstream
`WS-SIDECAR-SAFE-PROMOTION`). It states a rule and records the evidence; it
changes no code and no `corpora/` or `data/` content. It extends
`project/design/genre-sidecars-in-release-workflow.md`, which solved the problem
for `genre.json` only (that note's follow-up 3).

## Question

The release regenerates `data/` and ends with `lcats promote replace`, which
wholesale-replaces each collection. A sidecar that exists only in `corpora/` is
lost unless something puts it back into `data/` first. The orphaned-sidecar guard
(`WI-PROMOTE-0101`) blocks that loss, but only for registered kinds. What is the
rule for every sidecar kind the code can produce, so the 1.0 corpus release cannot
silently lose one?

## What the code registers and what it produces

The guard asks `sidecar_validators.registered_filenames()`
(`src/lcats/analysis/corpus/promote.py:401`), which returns the keys of `_REGISTRY`
(`src/lcats/analysis/corpus/sidecar_validators.py:121-127`): `genre.json`,
`scenes.json`, `linguistics.json`, `linguistics.tokens.json`. (`promote.py`'s
`_SIDECAR_REQUIRED_KEYS`, lines 53-56, is a separate survey-time shape check and
is not the guard's registry.)

Listing every distinct `.json` string literal under `src/lcats` (the check that
settled this; a narrower grep for `*_FILENAME` constants missed a hyphenated name
on a first pass) finds two more per-story sidecars the code writes, neither
registered:

- `linguistics.lexicon.json` (`src/lcats/analysis/linguistics/lexicon.py:16`,
  written at `runner.py:534`).
- `science-fiction.json` (`src/lcats/analysis/science_fiction/sidecar.py:15`,
  written by `publish_sidecar` at `science_fiction/pipeline.py:208-234`). Its
  docstring calls it experiment-local, and the checkpoint layer refuses writes
  under the protected `data/` and `corpora/` roots unless
  `allow_protected_root=True` (`src/lcats/utils/checkpoint.py:115-160`), so it does
  not reach a release by default. I read this from the code and did not reproduce
  it.

The registry comment calls the four "all currently-produced sidecar kinds"; that is
two short. The other `.json` literals are not per-story sidecars (the visualization
`*_manifest.json` outputs, the `corpus_specials.json` allowlist). `audit.json` and
`events.json` appear only in prose and a comment (`discovery.py:144`); no code
writing them was found.

| Kind | Produced by | Lands in | In `corpora/` today | Registered |
|---|---|---|---|---|
| `genre.json` | `lcats annotate` into `data/`; and tranche promotion (`promote insert/upsert --sidecar genre`) into `corpora/` | both | 146 | yes |
| `scenes.json` | `lcats annotate` into `data/`; tranche promotion is possible | `data/`, or both if promoted | 0 | yes |
| `linguistics.json`, `linguistics.tokens.json` | `lcats linguistics <path>`, which writes beside the stories in whatever tree the path names | in place; the documented examples name `corpora/` paths (`docs/how-to/run-linguistics.md:42,48,69`) | 0 | yes |
| `linguistics.lexicon.json` | `lcats linguistics --include-lexicon` (needs token-detail v2) | in place | 0 | **no** |
| `science-fiction.json` | `science_fiction.pipeline.publish_sidecar`, experiment-local; blocked from `data/` and `corpora/` by default | an experiment output root | 0 | **no** |

`docs/reference/linguistics-sidecar.md:250-251` says PR #325 "did not promote
generated linguistic sidecars into `corpora/` or define a release workflow for
them". That is the gap this rule fills.

## The rule

1. **Classify by production path, not by kind.** A kind can have more than one
   path (`genre.json` has two). For each path, ask where the file lands before
   `replace` runs.
2. **A file produced into `data/` needs nothing.** `replace` carries it into
   `corpora/` with the rest of the collection.
3. **A file that exists only in `corpora/` must be seeded into the regenerated
   `data/` before `replace`, with create-only `insert`, from a tracked source.**
   The mechanism is the existing `lcats promote insert --sidecar <kind>`, with
   `--tranche-manifest <jsonl>` or `--source <tree>`. Never use `upsert` for
   seeding, and never pass `--allow-orphaned-sidecar-deletion`: that flag
   disables the guard for every collection and every kind at once.
4. **Prefer a tracked evidence source over `corpora/` itself.** For `genre.json`
   that is the sanitized evidence manifest (runbook step 3b). A kind with no
   separate evidence file has only the git-tracked `corpora/` tree as its record;
   seeding from it is mechanically valid (verified below) but it is the tree being
   replaced, so it protects against a missing sidecar and nothing else.
5. **Do not write a sidecar directly into `corpora/`.** Run `lcats linguistics` and
   `lcats annotate` against `data/`, or promote by tranche. A sidecar written in
   place into `corpora/` has no tracked source, and the next release meets the
   blocked `replace` this rule exists to avoid.
6. **A kind the guard cannot see needs registering before it is released.**
   `linguistics.lexicon.json` is the live case today; `science-fiction.json` is
   the same gap but blocked from the protected roots by default (see the follow-up
   below).

## Go/no-go on a generic seed mechanism: no-go

No new tooling is needed for the registered kinds. `insert --source <tree>` already
scans `<collection>/<story>/<sidecar>` files generically, and the validator
registry already dispatches per kind. What was missing was the rule and its
documentation, which this note and the runbook pointer supply. A "seed every
registered kind" wrapper would be a convenience over a per-kind loop of one
command, and `WI-PROMOTE-0117` forbids implementing it. If a second tranche kind
is ever promoted, the wrapper can be reconsidered then.

Limits worth stating:

- `insert` is create-only and not transactional, and has no collection selector
  (`--source` scans the whole tree). A single-collection release needs a source
  tree containing only that collection; a stray story with no `story.json` in
  `data/` is rejected, which fails the run. This last point is inferred from the
  same code path the manifest runbook documents, not separately reproduced.
- For `genre.json`, a pipeline-written file already in `data/` is refused by
  `insert` (`promote.py:910-930`). A legacy flat `genre.json` is refused in every
  mode, including `upsert`, because that check runs before the `overwrite`
  branch.
- `insert` re-serializes with `indent=2`, so a sidecar that was stored compact
  round-trips semantically equal but not byte-identical. Canonically formatted
  files, such as the real `genre.json` files, round-trip byte-identical.

## Preflight question: no new preflight

`replace --dry-run` (runbook step 6) already reports every registered-kind orphan
and exits `1`; an assertion that every `corpora/` sidecar has a counterpart in
`data/` would duplicate it. The real gap is a file the guard cannot see. Until
`linguistics.lexicon.json` is registered, this read-only check should print nothing
before a release:

```bash
find ../corpora -mindepth 3 -maxdepth 3 -name '*.json' \
  ! -name story.json ! -name genre.json ! -name scenes.json \
  ! -name linguistics.json ! -name linguistics.tokens.json
```

Run from `lcats/` against the current real `corpora/`, it prints nothing today
(0 files).

## Follow-up: register the unregistered per-story sidecars

`linguistics.lexicon.json` and `science-fiction.json` are silent-loss hazards,
prospective because neither exists in `corpora/` yet. For the lexicon, verified in
a scratch copy: `replace` of a collection holding it exits `0` with no warning and
the file is gone afterwards, and `insert --sidecar linguistics.lexicon.json` is
refused without `--allow-unvalidated`. For `science-fiction.json` the protected-root
guard in the checkpoint layer is the only barrier, and the orphaned-sidecar guard
cannot see it either. Registering a kind needs a validator for its shape, which is
a code change and therefore not part of this investigation. Both are recorded in
`project/design/backlog.md`.

## Not reproduced

`linguistics.json` and `linguistics.tokens.json` seeding was not reproduced in a
scratch copy: it needs a real linguistics payload, which needs a spaCy run. The
rule for them rests on the shared registry mechanism and on the `scenes.json`
result below, which exercises the same dispatch.

## Reproduction

All commands ran against a scratch tree outside the repository, never against the
real `corpora/` or `data/`, from `lcats/` with `PYTHONPATH=$(pwd)/src` (the
default editable install resolves to a different checkout). The fixture is three
real Wodehouse story buckets under a collection also named `wodehouse` (a
`genre.json` payload carries its own `lcats_id`, so the scratch collection must
match it), with a real `genre.json` and a synthetic valid `scenes.json`
(`{"segments": []}`) per story in the scratch `corpora/`, and only `story.json` in
the scratch `data/`; plus a second collection with a story and a synthetic
`linguistics.lexicon.json`.

| Step | Command (scratch paths elided) | Result |
|---|---|---|
| 1 | `lcats promote replace wodehouse --source data --dest corpora --dry-run` | blocked: 6 orphaned sidecars across 3 stories (genre and scenes) |
| 2 | `lcats promote insert --sidecar genre --source corpora --dest data --dry-run`, then real; same for `scenes` | 3 would promote then 3 promoted each, exit 0 |
| 3 | the real `insert --sidecar genre` again | exit 1, 3 rejected: `already exists (insert mode is create-only ...)` |
| 4 | `replace wodehouse ... --dry-run`, then real | would promote, exit 0; `genre.json` byte-identical 3 of 3, all 6 sidecars (3 genre, 3 scenes) semantically equal |
| 5 | `replace` of the lexicon collection | exit 0, no warning; the lexicon file is gone |
| 6 | `insert --sidecar linguistics.lexicon.json --source corpora --dest data` | exit 2, `no registered validator ...`; with `--allow-unvalidated`, exit 0 and the file survives a following `replace` |
| 7 | pipeline-written legacy flat `genre.json` already in `data/`, then `insert --sidecar genre` | that story rejected (`already holds a legacy flat genre.json`), the other 2 promoted (non-transactional), pipeline file kept |

A first attempt at step 2 failed because the scratch collection was named `c1`
while the payloads carried `wodehouse/<story>` ids; `insert` correctly refused the
mismatch. That was a fixture error, found, reported and corrected before the
rerun above.
