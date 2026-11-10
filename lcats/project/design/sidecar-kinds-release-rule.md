# Release rule for sidecar kinds other than genre.json

Status: investigation result for `WI-PROMOTE-0117` (workstream
`WS-SIDECAR-SAFE-PROMOTION`), extended by `WI-PROMOTE-0125`, which reproduced the
linguistics kinds with real spaCy output (see "Linguistics reproduction"). It states
a rule and records the evidence; it changes no code and no `corpora/` or `data/`
content. It extends
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
  path set at `runner.py:534`, written at `runner.py:368`).
- `science-fiction.json` (`src/lcats/analysis/science_fiction/sidecar.py:15`,
  written by `publish_sidecar` at `science_fiction/pipeline.py:208-234`). Its
  docstring calls it experiment-local, and the checkpoint layer refuses writes
  under the protected `data/` and `corpora/` roots unless
  `allow_protected_root=True` (`src/lcats/utils/checkpoint.py:115-160`), so it does
  not reach a release by default. I read this from the code and did not reproduce
  it.

The registry comment calls the four "all currently-produced sidecar kinds"; that is
two short. The other `.json` literals are not per-story sidecars (the visualization
`*_manifest.json` outputs, the `corpus_specials.json` allowlist, and the per-item
`<stage>.json` checkpoint files written by `utils/checkpoint.py:224`, which the
same protected-root guard keeps out of `data/` and `corpora/`). `audit.json` and
`events.json` appear only in prose and a comment (`discovery.py:144`); no code
writing them was found.

| Kind | Produced by | Lands in | In `corpora/` today | Registered |
|---|---|---|---|---|
| `genre.json` | `lcats annotate` into `data/`; and tranche promotion (`promote insert/upsert --sidecar genre`) into `corpora/` | both | 146 | yes |
| `scenes.json` | `lcats annotate` into `data/`; tranche promotion is possible | `data/`, or both if promoted | 0 | yes |
| `linguistics.json`, `linguistics.tokens.json` | `lcats linguistics <path>`, which writes beside the stories in whatever tree the path names (`runner.py:517-518`; `--output-root` redirects) | in place; the how-to's examples named `corpora/` paths until this change moved them to `data/` | 0 | yes |
| `linguistics.lexicon.json` | `lcats linguistics --include-lexicon` (needs token-detail v2) | in place | 0 | **no** |
| `science-fiction.json` | `science_fiction.pipeline.publish_sidecar`, experiment-local; blocked from `data/` and `corpora/` by default | an experiment output root | 0 | **no** |

`docs/reference/linguistics-sidecar.md:250-251` says PR #325 "did not promote
generated linguistic sidecars into `corpora/` or define a release workflow for
them". That is the gap this rule fills.

## The rule

1. **Classify by production path, not by kind.** A kind can have more than one
   path (`genre.json` has two). For each path, ask where the file lands before
   `replace` runs.
2. **A file produced into `data/` after `lcats gather` and before `replace` needs
   nothing.** `replace` carries it into `corpora/` with the rest of the collection.
   But `lcats clean` (runbook step 2) deletes every `data/` collection, `lcats gather`
   regenerates stories only, and the runbook has no pipeline step after it. A sidecar
   from an earlier run therefore reaches `replace` only if its pipeline step is
   re-run after `gather`; otherwise it exists only in `corpora/` and rule 3 applies.
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
  `data/` is rejected, which fails the run (reproduced, Reproduction row 9; linguistics: L12).
- For `genre.json`, a pipeline-written file already in `data/` is refused by
  `insert` (`promote.py:910-930`). A legacy flat `genre.json` is refused in every
  mode, including `upsert`, because that check runs before the `overwrite`
  branch.
- `insert` re-serializes with `json.dumps(payload, indent=2)` (`promote.py:944`):
  default `ensure_ascii=True`, no `sort_keys`, no trailing newline. A sidecar
  therefore round-trips byte-identical only if it was written by that same call
  (the real `genre.json` files, Reproduction row 4). A sidecar from another writer
  round-trips semantically equal but not byte-identical. The linguistics writer
  (`sidecar.py:1109`) uses `ensure_ascii=False`, `sort_keys=True` and a trailing
  newline, so in the reproduction below all 10 registered-kind files (v1) and all
  5 lexicon files changed bytes on the first cycle: a dropped final newline, plus
  `\uXXXX` escapes for non-ASCII text in the Wodehouse token files (tokens grew by up to 203
  bytes). A second seed-and-replace cycle on the v1 files changed
  nothing, so the reformatting happens once, at the first seeding.
- The linguistics validators check schema shape, not location: `insert` accepted
  a payload whose `story_path` (`gen/wodehouse/...`) named a different directory
  from where it landed (`data/wodehouse/...`). `story_path` and
  `input.source_path` record the path exactly as given, so an absolute-path
  invocation writes a machine-local absolute path into the sidecar (seen in an
  earlier scratch run; the L-rows all used relative paths). Run `lcats linguistics` with relative paths from
  `lcats/` (for example `data/<collection>`) so the committed payload stays
  portable.
- Token-detail sidecars are large: the five stories measured 81 KiB to 1.1 MiB at
  v1 and 160 KiB to 2.2 MiB at v2. Whether to commit them to `corpora/` is a
  size and policy decision this note does not make; the rule only says how to
  carry them if they are committed.

## Preflight question: two read-only checks, no new command

`replace --dry-run` (runbook step 6) reports every registered-kind orphan for a
story present in both trees, and exits `1`. It does not cover two cases:

- **A story missing from the regenerated `data/`.** The guard skips it by design
  (`promote.py:406-409`: a wholesale `replace` legitimately retires a story), so
  `replace` deletes the story and its sidecars, exits `0`, and prints no warning
  (reproduced, Reproduction row 8 below). For a registered kind the seed step catches it:
  `insert` rejects `no story.json at data/...`, exits `1`, and the runbook's stop
  rule applies (Reproduction row 9).
- **A file whose name is not registered.** The guard cannot see it at all.

Two read-only checks cover both, from `lcats/`, and print nothing when clean. The
first looks for sidecar names the guard does not know; it prints nothing today
against the real `corpora/` (0 files):

```bash
find ../corpora -mindepth 3 -maxdepth 3 -name '*.json' \
  ! -name story.json ! -name genre.json ! -name scenes.json \
  ! -name linguistics.json ! -name linguistics.tokens.json
```

The second lists every `corpora/` sidecar whose story is absent from the
regenerated `data/`. It is only meaningful right after `lcats gather`; against a
stale or empty `data/` it lists everything:

```bash
find ../corpora -mindepth 3 -maxdepth 3 -name '*.json' ! -name story.json |
  while read -r f; do
    b=$(dirname "${f#../corpora/}")
    [ -f "data/$b/story.json" ] || echo "no story.json in data/ for: $b ($(basename "$f"))"
  done
```

Both checks were run verbatim in a scratch layout that mirrors the repository
(a `corpora/` beside an `lcats/` holding `data/`): the first flagged a synthetic
`linguistics.lexicon.json`, and the second listed exactly the dropped story's two
sidecars.

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

`linguistics.json` and `linguistics.tokens.json` seeding is now reproduced with real
spaCy output (see "Linguistics reproduction" at the end). Still not reproduced:

- `science-fiction.json`: read from the code only.
- `scenes.json` with a real `lcats annotate` payload: the rows below used a
  synthetic `{"segments": []}`, which is all the registered validator checks.
- The linguistics kinds with any backend or model other than spaCy 3.8.14 with
  `en_core_web_sm` 3.8.0 (the `stanza` backend and the `md`/`lg` models are not
  installed), on any machine other than the one that ran it, and over the full
  1,868-story corpus (five stories were run).
- A release that regenerates `data/` with `lcats gather`: the scratch `data/` trees
  were built by copying `story.json` files.

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
| 8 | one story absent from the regenerated `data/`, the other two seeded, then `replace wodehouse --dry-run` and real | exit 0 both times (`would promote`); the dropped story and its sidecars are gone afterwards, with no warning |
| 9 | the same absent story, seeding with `insert --sidecar genre\|scenes --source corpora --dest data` | exit 1 each, 1 rejected (`no story.json at data/wodehouse/<story>`), the other 2 promoted |

A first attempt at step 2 failed because the scratch collection was named `c1`
while the payloads carried `wodehouse/<story>` ids; `insert` correctly refused the
mismatch. That was a fixture error, found, reported and corrected before the
rerun above.

## Linguistics reproduction

`WI-PROMOTE-0125`, run from `lcats/` with `PYTHONPATH=$(pwd)/src` against checkout
`62d929e7`, in scratch trees outside the repository (no network; the real
`corpora/` and `data/` were not written).

**Tool versions.** spaCy 3.8.14 with `en_core_web_sm` 3.8.0 (the payload records
`core_web_sm@3.8.0`), thinc 8.3.13, numpy 2.3.0, Python 3.11.9 in the `LCATS` conda
environment, macOS arm64. Extractor `lcats.analysis.linguistics` v1. Schemas
`linguistics-sidecar-v1`, `linguistics-token-detail-v1` and `-v2`, and
`linguistics-lexicon-v1`.

**Fixture.** Five real stories copied from `corpora/`: `wodehouse/one_touch_of_nature`,
`wodehouse/sea_of_troubles`, `wodehouse/wilton_s_holiday`,
`mass_quantities/king_of_the_hill__blish` and
`mass_quantities/five_o_clock_tea_farce__howells` (two names contain `__`). A scratch
`corpora/` holds the stories and their real sidecars; a scratch `lcats/data/` beside
it holds only `story.json`. The sidecars came from relative-path runs of
`lcats linguistics --backend spacy --include-token-detail --token-detail-version v1`
(and `v2 --include-lexicon` for the lexicon rows) over `gen/wodehouse` and
`gen/mass_quantities` from `lcats/`; each run took about 10 seconds for the five
stories. Every `linguistics.json`, v1 and v2 `linguistics.tokens.json` passed the
registry validator (5 of 5 each); `linguistics.lexicon.json` has none.

| Step | Command (scratch paths elided) | Result |
|---|---|---|
| L1 | `lcats promote replace wodehouse --source data --dest ../corpora --dry-run`, then real; same for `mass_quantities` | blocked, exit 1 both times: 6 orphaned sidecars across 3 stories (`linguistics.json` and `linguistics.tokens.json` each), then 4 across 2; nothing deleted |
| L2 | `insert --sidecar linguistics --source ../corpora --dest data --dry-run`, then real; same for `--sidecar linguistics.tokens.json` | exit 0; 5 would promote, then 5 promoted per kind (10 in `data/`) |
| L3 | the real `insert` of each kind again | exit 1, all 5 rejected per kind: `already exists (insert mode is create-only ...)` |
| L4 | `replace` of each collection, `--dry-run` then real | exit 0 all four runs. Round trip: 5 of 5 `story.json` byte-identical; all 10 sidecars semantically equal, none byte-identical (dropped final newline; `\uXXXX` escapes in the Wodehouse token files) |
| L5 | the same cycle again on the result of L4 | `diff -rq` against the L4 result: identical, so the reformat is one-time |
| L6 | v2 + lexicon tree: unseeded `replace wodehouse --dry-run` | blocked, exit 1, 6 orphans; the lexicon files are not counted |
| L7 | `insert --sidecar linguistics.lexicon.json --source ../corpora --dest data` | exit 2, `no registered validator ...` |
| L8 | v2 tree: seed the two registered kinds, then `replace` both collections | exit 0 (dry-run and real); the 5 `linguistics.lexicon.json` files are gone, with no warning |
| L9 | same, but first `insert --sidecar linguistics.lexicon.json ... --allow-unvalidated` | exit 0; the 5 lexicon files survive `replace`, semantically equal and not byte-identical |
| L10 | `data/` holds only `wodehouse`; `insert --sidecar <kind> --source ../corpora` | exit 1 per kind: 3 promoted, 2 rejected (`no story.json at data/mass_quantities/...`) |
| L11 | same state, `--source` a tree holding only a copy of `corpora/wodehouse` | exit 0 per kind, 3 promoted; `replace wodehouse` exit 0; the `mass_quantities` sidecars in `corpora/` (4) untouched |
| L12 | one story absent from the regenerated `data/`; `insert --sidecar <kind> --source ../corpora` | exit 1 per kind: 4 promoted, 1 rejected (`no story.json at data/wodehouse/sea_of_troubles`) |
| L13 | spaCy run twice on two stories (v2 + lexicon), identical relative paths and versions | 6 of 6 files byte-identical |

**What this changes.** The rule is unchanged: the registered linguistics kinds seed
with create-only `insert`, the lexicon is a silent-loss hazard until registered, and a
single-collection release needs a source tree with only that collection. What was
inferred is now reproduced for linguistics (L1 to L5, L10 to L12), and the
byte-identical claim is corrected above: it holds only for payloads written by
`insert` itself. Determinism (L13) holds on one machine and one set of versions; a
different spaCy or model version is not covered.

**Workstream exit criterion 1.** `WS-SIDECAR-SAFE-PROMOTION` exit criterion 1 (every
registered kind has a documented release rule and a verified seed or regeneration
path) is now met: `genre.json` (Reproduction rows 1 to 9), the two linguistics kinds
(L1 to L5, L10 to L12) and `scenes.json`. One caveat: the `scenes.json` rows used a
synthetic payload, which is sufficient only because its registered validator checks
nothing beyond `segments` being a list. `linguistics.lexicon.json` and
`science-fiction.json` are not registered, so they fall outside the criterion; they
remain backlog hazards. The workstream's other criteria are not assessed here.
