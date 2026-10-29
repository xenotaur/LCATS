# Genre-evidence checkpoint archive (2026-08-21 runs)

Tracked, byte-identical copies of the per-story validation checkpoints for the 146
stories of `../validation_results.jsonl`, plus the baseline story-hash manifest derived
from them (`../story_hash_baseline.jsonl`). Created by `WI-PROMOTE-0124`.

## Why this exists

Each checkpoint records `fingerprint.story_content_hash`, the sha256 of the story's
`story.json` bytes when it was assessed. The committed results contain no hash, and
`.gitignore` deliberately keeps checkpoint scratch files out of git
(`experiments/05_metadata_genre_prefilter/results/**/*__*/validation*.json`), so these
files existed only in one worktree. The model assessment in each genre sidecar depends
on the story text, so these hashes are the only proof that "the text is unchanged since
it was assessed". See `lcats/project/design/genre-sidecar-story-binding.md`.

## What is here

| Path | Contents |
|---|---|
| `<collection>/<story>/opus-checkpoint.json` | The Claude Opus checkpoint (`claude-opus-4-8`, run id `2026-08-21T18:55:51.831553Z`); source name `validation.json`. |
| `<collection>/<story>/gpt-oss-20b-checkpoint.json` | The local-model checkpoint (`gpt-oss:20b` over Ollama, `WI-LLM-0074`); source name `validation_openai_http_localhost_11434_v1.json`. Kept because it is not yet known whether this evidence will be needed. Not used to build the manifest. The committed run log records two complete runs of the same 146 stories (run ids `2026-08-22T18:12:52.694890Z`, 104 agreements, and `2026-08-22T22:43:34.555291Z`, 107 agreements); the checkpoints carry no run id, so which run a given file reflects is not recorded. |
| `archive_index.jsonl` | One row per archived file: `lcats_id`, `kind`, `archive_path`, `sha256`, `bytes`. |
| `../story_hash_baseline.jsonl` | 146 rows `{lcats_id, story_content_hash, archive_path, archive_sha256}`, derived from the archived **Opus** files only. |

292 files, 327,005 bytes. The archive path is the `lcats_id` (`<collection>/<story>`), the
same key as `corpora/<lcats_id>/story.json`.

## Provenance

- Source: the checkpoint files under `experiments/05_metadata_genre_prefilter/results/full_scan/<collection>__<story>/`
  in the worktree `lcats-special-char-strategy-c18aa7`, copied byte for byte. The
  originals were left in place and untouched.
- The contents are identical to the originals; only the file names differ (renamed so
  the ignore rule does not match them, which avoids any `.gitignore` change).
- Hash basis: sha256 over the `story.json` file bytes, exactly as
  `run_prefilter._validation_fingerprint` computed it.
- The Opus run cost about $36.32 and would not reproduce the same outputs; that is why
  the files are kept.

## Verified relationships

`archive_checkpoints.py verify` and `archive_checkpoints_test.py` check, for all 146
stories:

- each archived file equals the index sha256 and size, the index has no duplicate or
  wrong-path rows, and no unexpected file is present;
- the manifest has exactly the 146 evidence ids, each hash equal to the archived Opus
  `fingerprint.story_content_hash`, with the right `archive_path` and `archive_sha256`;
- every hash equals the sha256 of today's `corpora/<lcats_id>/story.json` bytes;
- the archived Opus `data.model_assessment` equals the committed model assessment in
  `validation_results.jsonl` in full (the whole object);
- each gpt-oss hash equals the Opus hash for the same story;
- `git check-ignore` reports none of the archived paths as ignored.

The index attests the files it lists, so `verify` is a drift detector, not a proof of
authenticity: it semantically checks the hash fields and the whole Opus
`model_assessment`, and anything else in a checkpoint is covered only by the index
sha256. If a malformed file or input is found, `verify` reports it as a problem (exit
1) or, for bad input such as an unreadable evidence file, exits 2.

Re-check any time, from `lcats/`:

```bash
python ../experiments/05_metadata_genre_prefilter/archive_checkpoints.py verify
```

## Caveats

- **Names are built forward, never parsed backwards.** 84 of the 146 story names (all in
  `mass_quantities`) themselves contain `__`, so a source directory name such as
  `mass_quantities__the_courting_of_lady_jane__bacon` cannot be split reliably. The tool
  maps each known `lcats_id` to its source name (`/` replaced by `__`).
- The files have no trailing newline. `experiments/` is excluded from the repository's
  pre-commit hooks (`.pre-commit-config.yaml`), so no fixer rewrites them; do not
  reformat them.
- **The check fails when a story legitimately changes.** `verify` (and the real-archive
  tests, which run in CI) compare the baseline with the current
  `corpora/<lcats_id>/story.json`. If one of the 146 stories is deliberately edited, the
  baseline must be reconciled on purpose (the edit invalidates the model assessment that
  was computed on the old text), not silently updated.
- This is evidence of the text hash, not a release check. Building the release-time
  comparison, and choosing between file bytes and an effective-input hash, are separate
  follow-ups (see `lcats/project/design/genre-sidecar-story-binding.md`).
