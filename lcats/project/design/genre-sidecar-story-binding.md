# How a seeded genre sidecar is bound to its story

Status: investigation result for `WI-PROMOTE-0118` (workstream
`WS-SIDECAR-SAFE-PROMOTION`). It records evidence and a recommendation. It changes
no code, no sidecar schema, no `corpora/` content and no evidence file. It answers
follow-up 4 of `project/design/genre-sidecars-in-release-workflow.md`.

## Question

The release seeds `data/` with the 146 tranche-promoted `genre.json` sidecars and
then runs `lcats promote replace`, which replaces `corpora/` with the freshly
regenerated `data/`. Nothing checks that a regenerated story is still the story a
seeded sidecar was computed from. Should the sidecar be bound to its story, how, and
where would the check run?

## What a genre sidecar depends on

Every one of the 146 records in
`experiments/05_metadata_genre_prefilter/results/full_scan/validation_results.jsonl`
holds two assessments (checked: 146 of 146, no exceptions):

| Assessment | Provenance keys | Depends on |
|---|---|---|
| `gutenberg_subject_rules` | `cache_db_path`, `cache_status`, `gutenberg_id`, `gutenberg_url`, `story_id`, `story_path` | the story's Gutenberg identity and the metadata cache; not the story text |
| `lcats.analysis.corpus.assess.assess_story` (model) | `backend_model`, `input_tokens`, `output_tokens`, `run_id`, `story_id`, `story_path` | the story text (`run_prefilter.py:1206-1211` calls `assess_story()` on the story file), the `author` and source `url` from `metadata` that `run_preflight` reads and the prompt shows the model (`assess.py:364-366`, `432-437`), the backend model and the run |

`provenance.gutenberg_url` equals `story.json` `metadata.url` for all 146 stories
(checked, 0 mismatches), so the metadata assessment's identity is already
consistent with the story. Nothing in the sidecar says whether the model
assessment's story text has changed.

## The original text hashes survive, and they match today

The experiment hashed every story's file bytes into its resume fingerprint
(`_validation_fingerprint`, `run_prefilter.py:1018-1053`, the `story_content_hash`
field, sha256 over `story.json` bytes). None of the committed results files contain
a hash (0 hits for `fingerprint` or `sha256` in `validation_results.jsonl`,
`validation_run_log.jsonl` and `validation_summary.json`), which is what made the
original text look unrecoverable.

It is not. The per-story checkpoint files from the Opus run
(`claude-opus-4-8`, run id `2026-08-21T18:55:51.831553Z`) still exist, gitignored,
in a sibling worktree of this clone (`lcats-special-char-strategy-c18aa7`, under
`experiments/05_metadata_genre_prefilter/results/full_scan/<collection>__<story>/validation.json`).
For all 146 stories:

- the checkpoint's `story_content_hash` equals the sha256 of today's
  `corpora/<story>/story.json` bytes (146 of 146 match);
- the checkpoint is the one that produced the committed assessment: its
  `data.model_assessment` carries the same `generated_at`, and its `input_tokens`
  match the committed model assessment's, for 146 of 146;
- the experiment read its stories from `corpora/` (the selection dry-run's
  `summary.json` records `corpus_root: corpora`; the validation run's own summary
  records no root), and every one of the 146 `story.json` files is byte-identical
  between the commit at run time (`e0c2a2f9`) and `HEAD` (146 of 146), so the
  hash match above is what actually ties the bytes together;
- no commit has touched any of the 146 `story.json` files since the run.

So "the text is unchanged since it was assessed" is proven for all 146 today, not
assumed. Two cautions. The checkpoints are matched by `.gitignore:137`
(`experiments/05_metadata_genre_prefilter/results/**/*__*/validation*.json`), so
`git status` does not show them and `git clean -fd` does not remove them, but
`git clean -fdx`, deleting that worktree or a fresh clone loses them. A search of
this machine's LCATS tree found them in that one worktree only. And a second
checkpoint set from a local-model run sits beside them
(`validation_openai_http_localhost_11434_v1.json`, model `gpt-oss:20b`); its
`story_content_hash` values also equal today's bytes for 146 of 146, a harmless
duplicate that does not bear on the shipped Opus assessments.

## Precedent in this repository

| Where | What it hashes | Where the hash lives |
|---|---|---|
| `run_prefilter.py` `_validation_fingerprint` | `story.json` bytes (`story_content_hash`) | the checkpoint, not the sidecar |
| `annotate.py` `_genre_fingerprint`, `_scenes_fingerprint` (lines 118-151) | the story body text (`body_hash`, sha256), alongside `author` and `url` in the same fingerprint (`annotate.py:126-138`) | the checkpoint fingerprint, not `genre.json` or `scenes.json` |
| `linguistics/sidecar.py` | the story body (`input.body_sha256`) | the sidecar itself; the validator compares it to the source body when one is supplied (lines 744-757, `source_hash_mismatch`) |
| `science_fiction/models.py` and `preparation.py` | the normalized story text (`story_hash`, sha256 over `normalize_story_text` output) | the sidecar models; each evidence set and analysis repeats it and the validator checks it against the sidecar's own top-level `story_hash` (`models.py:705,722`), which is internal consistency, not a comparison with the source |

So both patterns exist here: change detection in a checkpoint outside the sidecar
(the genre producers), and a hash inside the sidecar (linguistics, science fiction),
of which only the linguistics validator can compare it with the source body. The tranche-promoted
genre sidecars are the one group with neither. The hashes also differ in basis:
file bytes (the experiment), body text plus `author` and `url` (annotate), body text
(linguistics) and normalized text (science fiction).

`genre_sidecar.validate_sidecar` (`genre_sidecar.py:63`) tolerates an extra field:
adding a `story_content_hash` at the sidecar top level, on an assessment, or in an
assessment's provenance each left a real record valid (checked in memory, nothing
written). So an in-sidecar hash is mechanically compatible with the existing
validator.

## Options

| | Option | For | Against |
|---|---|---|---|
| A | Add a hash to each sidecar (a schema change) | self-describing; follows the linguistics pattern | touches the 146 promoted files, which would need an `upsert` rewrite like `WI-GENRE-0109`; cannot be added to the immutable evidence file; the validator sees only the payload, so the comparison still needs a second component |
| B | Compare `provenance.gutenberg_url` with `story.json` `metadata.url` | no new artifact | binds the metadata assessment only; says nothing about the model assessment; already true for all 146 |
| C | No new check | nothing to build | a regenerated story that differs from the assessed one is seeded silently; the CI drift test compares the seed with `corpora/` and never sees a regenerated story |
| D | A side manifest of baseline hashes, compared at release time | no schema change; evidence and sidecars untouched; reuses the recovered originals; covers both assessments, because hashing the file bytes includes `metadata.url` | a second artifact to keep in sync with the 146 |

## Recommendation

- **No-go on a sidecar schema change now.** Option A buys self-description at the
  cost of rewriting 146 promoted files, and the check would still need an external
  component.
- **Go on Option D.** Record `{lcats_id, story_content_hash}` for the 146, with the
  hash being sha256 over `story.json` bytes exactly as the experiment computed it,
  and compare it with the regenerated `data/` after `lcats gather` and before
  `replace` (before or after the seed step; the comparison reads only `story.json`). Using the recovered originals makes the baseline a
  provenance claim, not a "today's text, trust me" claim. Option D subsumes
  Option B, since the file bytes include `metadata.url`.
- **Where the check runs:** a release-time read-only comparison in the runbook,
  alongside the two read-only checks already in step 3b. Not in `validate_sidecar`
  (it sees only the payload) and not in `promote insert` (it needs no story
  content to be create-only). Nor in the seed tool, `tools/build_genre_seed_manifest.py`,
  which builds the manifest from the evidence file and never reads `corpora/` or
  `data/`: a runbook check needs no code and covers the whole release, not only the
  seeded sidecars, and a follow-up may later fold it into the tool. Keep the CI
  drift test as it is.
- **What it flags, and which changes should count.** The assessment's real inputs
  are the body, `author` and `url` (`assess.py:347-369`, `432-439`); the title is
  just the bucket directory name (`infer_story_title` returns
  `file_path.parent.name` and discards the data, `cli.py:47-60`), already encoded in
  the item id, which is why `annotate`'s fingerprint leaves it out
  (`annotate.py:121-127`), and `year`, `name` and a top-level `author` key (84 of 146 stories carry one;
  only `metadata.author` is read) are not read at all. So:
  - A change to the body, `author` or `url` makes a sidecar stale. An unchanged body
    with a changed author or URL still does, and `url` also anchors the metadata
    assessment. A body-only hash would miss it.
  - A change to an unused field such as `year` or `name` does not make a sidecar
    stale.
  - **File bytes** (what the recovered baseline already is) are a conservative
    superset: they catch every real change and also flag unused-field edits, which
    cost an unnecessary re-assess-or-accept decision but never miss a stale sidecar.
  - An **effective-input hash** over `author`, `url` and the body (the shape
    `annotate`'s fingerprint uses) is exact for what the model sees, with no false positives. It should hash the
    coerced body (`coerce_story_text`), as `annotate.py:609` does, and the body as
    truncated if the cap matters: `assess_story` cuts the body at
    `max_body_chars=100_000` (`assess.py:377`, `422-423`), so text past the cap never
    reaches the model. None of the 146 stories is that long (the longest is 77,811
    characters), so there is no effect today. The recovered baseline can be
    re-expressed in that form today, because all 146 files are unchanged and the
    inputs can be read from them.
  - A **body hash** is acceptable only paired with separate `author` and `url`
    checks (for example `provenance.gutenberg_url` against `metadata.url`, the
    note's Option B, plus an author comparison) and an identity check that the bucket
    is the intended story. On its own it is not.
  The follow-up chooses between the first two; this note recommends starting with
  file bytes because the baseline already exists in that form, and moving to the
  effective-input hash if false positives prove noisy.
- **When it fires:** the operator re-assesses that story, or accepts the stale
  sidecar knowingly. The note does not decide which; re-assessment costs model
  calls.
- **Time-sensitive, and preserve the evidence, not only the hashes:** the baseline's
  source files are gitignored files in one sibling worktree. A manifest of 146
  hashes derived from them merely asserts that they came from the Opus run; the
  checkpoints are the primary evidence that links each hash to the model run
  (their `generated_at` and token counts match the committed assessments). So the
  first step is to archive the 146 Opus `validation.json` checkpoints themselves
  (159,630 bytes in total) under `experiments/05_metadata_genre_prefilter/results/full_scan/`,
  which needs a forced add or an ignore exception because `.gitignore:137` matches
  them, in line with `AGENTS.md`'s "preserve historical outputs". The manifest is
  then derived from the archived files, so the connection can be re-checked. The
  local-model set is optional. This is a data-preservation change and outside this
  investigation, which forbids implementing a fingerprint.

A prototype of the comparison, run in a scratch tree only (a 146-entry manifest
rebuilt from the surviving checkpoints, a stand-in `data/` holding the 12 Wodehouse
stories, the comparison restricted to the `wodehouse/` entries), printed nothing and
exited 0 for the unmodified set, and for one edited and one
dropped story printed exactly:

```
CHANGED since assessed: wodehouse/at_geisenheimer_s
MISSING in data/: wodehouse/bill_the_bloodhound
```

and exited 1. The script is a few lines: read the manifest, hash
`data/<lcats_id>/story.json` bytes, report mismatches. It is described here and
not committed, to respect the no-implementation boundary.

## What was not measured

- **Whether a fresh `gather` reproduces the stored text.** That is the real
  determinant of how often the check fires at release. There is no populated `data/`
  in this worktree, and running `gather` is a networked, cached, long step outside
  this investigation. The measure should be the first job of the follow-up.
- Any change in `lcats gather` or the specials cleanup that could alter regenerated
  text in the future.

## Corrections to earlier statements

An earlier reply on `xenotaur/LCATS#362` said the committed results contain no story
hash, so a "text unchanged since assessed" claim could not be recovered after the
fact. The first half is right; the second is superseded by this note. Earlier drafts
of this work item and an earlier explanation also described the sidecar as
metadata-derived and a text hash as the wrong binding; that was corrected during
`PR #496` review, which established the two-assessment structure above.

## Follow-ups

- Archive the 146 Opus checkpoint files as tracked evidence, then derive the
  baseline manifest from them (data preservation; time sensitive).
- Build the release-time comparison, choosing between file bytes (conservative,
  baseline already in that form) and an effective-input hash over `author`, `url`
  and the body (exact), never a body hash alone, and decide the re-assess-or-accept
  rule.
- Measure whether a fresh `gather` reproduces the stored text.

These are recorded in `project/design/backlog.md`.

## Reproduction

All commands were read-only against the repository or ran in a scratch tree outside
it, from `lcats/` with `PYTHONPATH=$(pwd)/src` where `lcats` was imported (the
default editable install resolves to a different checkout).

| Step | What | Result |
|---|---|---|
| 1 | list the assessments per record in `validation_results.jsonl` | 146 of 146 hold exactly the two above, with the stated provenance keys |
| 2 | compare each record's `provenance.gutenberg_url` with `corpora/<story>/story.json` `metadata.url` | 146 of 146 equal |
| 3 | grep the committed results for `fingerprint` or `sha256` | 0 hits in all three files |
| 4 | read each of the 146 `validation.json` checkpoints in the sibling worktree and compare `story_content_hash` with the sha256 of `git show HEAD:corpora/<story>/story.json` | 146 of 146 match |
| 5 | compare `git show e0c2a2f9:corpora/...` with `git show HEAD:corpora/...` for each story | 146 of 146 byte-identical |
| 6 | `git log` since the run touching the 146 `story.json` paths | none |
| 7 | add a `story_content_hash` field in memory to a real record at three levels, then `validate_sidecar` | valid each time |
| 8 | the scratch comparison above, unmodified and with one edit and one drop | exit 0; then exit 1 naming both |
| 9 | compare each Opus checkpoint's `data.model_assessment.generated_at` and `input_tokens` with the committed model assessment | 146 of 146 equal |
| 10 | read the 146 local-model checkpoints beside them; `git check-ignore -v` on one checkpoint | model `gpt-oss:20b`, hashes equal today's bytes 146 of 146; ignored by `.gitignore:137` |
| 11 | find every `validation.json` under the LCATS tree on this machine | 146 files, all in the one sibling worktree |
