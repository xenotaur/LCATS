# LCATS CLI command reference

Flags and arguments for every `lcats` subcommand, verified against
`lcats <command> --help`. For which commands are implemented vs. placeholder,
see [`cli-status.md`](cli-status.md).

## `help`

```
lcats help [topic]
```

Display LCATS help, including command-specific help.

| Argument | Description |
|---|---|
| `topic` | Optional command name, e.g. `lcats help survey`. |

## `info`

```
lcats info
```

Describe LCATS, the literary captain's advisory tool system.

## `gather`

```
lcats gather [--dry-run] [gatherers ...]
```

Gather one or more configured corpora.

| Argument / Flag | Description |
|---|---|
| `gatherers` | Optional gatherer names. Defaults to all gatherers. |
| `--dry-run` | Show which gatherers would run without executing downloads. |

## `inspect`

```
lcats inspect [files ...]
```

Inspect one or more story JSON files and print summaries.

## `display`

```
lcats display [files ...]
```

Display one or more story JSON files in human-readable form.

## `survey`

```
lcats survey [--mode {qa,specials}] [--check-for CHECK_FOR]
              [--print-clean-filenames] [--allowlist-config ALLOWLIST_CONFIG]
              [--allow-smart] [--no-allow-smart] [--context CONTEXT]
              [--nocontext] [--name-width NAME_WIDTH]
              [--identifier {path,filename,title}]
              [--unicode-name-width UNICODE_NAME_WIDTH] [--header]
              [--no-header] [--format {human,tsv}] [--output OUTPUT]
              [--progress] [--no-progress]
              [--exclude-codepoint EXCLUDE_CODEPOINT]
              [--exclude-char EXCLUDE_CHAR]
              [directories ...]
```

Survey LCATS corpus JSON files for quality issues such as special characters
and boundary contamination.

| Argument / Flag | Description |
|---|---|
| `directories` | Directories or files to survey. |
| `--mode {qa,specials}` | Survey mode. `qa` (default) for normal checks, or `specials` to default to special-character extraction. |
| `--check-for CHECK_FOR` | Check(s) to run. Repeatable or comma-separated: `special-characters`, `boundary-contamination`, `the_end-contamination`. |
| `--print-clean-filenames` | Print filenames of clean (finding-free) files. |
| `--allowlist-config ALLOWLIST_CONFIG` | Path to an allowlist config JSON. Defaults to the packaged corpus allowlist; pass an empty string to disable. |
| `--allow-smart` / `--no-allow-smart` | Toggle smart-punctuation allowlisting. |
| `--context CONTEXT` / `--nocontext` | Toggle surrounding-text context in findings. |
| `--name-width NAME_WIDTH` | Column width for filenames in human-format output. |
| `--identifier {path,filename,title}` | Identifier shown in TSV reports. Defaults to `path`. |
| `--unicode-name-width UNICODE_NAME_WIDTH` | Maximum Unicode name width for TSV shown on a TTY. `0` disables truncation. |
| `--header` / `--no-header` | Toggle TSV header row. |
| `--format {human,tsv}` | Output format. |
| `--output OUTPUT` | Write output to a file instead of stdout. |
| `--progress` / `--no-progress` | Toggle progress display. |
| `--exclude-codepoint EXCLUDE_CODEPOINT` | Exclude a specific Unicode codepoint from findings. |
| `--exclude-char EXCLUDE_CHAR` | Exclude a specific character from findings. |

**Note:** `--extract-script` also appears in `--help` output but is a legacy
compatibility flag — extraction now runs in-process via
`lcats.analysis.corpus.specials_cli`.

```
lcats survey --mode specials corpora/sherlock
lcats survey corpora/sherlock --check-for special-characters
lcats survey data/ --format tsv --output findings.tsv
lcats survey corpora/sherlock --no-progress --print-clean-filenames
```

## `assess`

```
lcats assess [--genre GENRE] [--model MODEL]
              [--max-body-chars MAX_BODY_CHARS]
              [--format {jsonl,json,tsv,human}] [--output OUTPUT]
              [--dry-run] [--progress] [--no-progress]
              [directories ...]
```

Assess LCATS corpus JSON files for quality and genre fit. Calls the Claude
API to produce structured include/exclude/review verdicts, genre confidence
scores, issue lists, and story summaries.

| Argument / Flag | Description |
|---|---|
| `directories` | Directories or JSON files to assess (default: `data/`). |
| `--genre GENRE` | Target genre for curation (lens mode): `science fiction`, `horror`, `western`, `romance`. Quote multi-word genres. Omit to detect genre automatically (detect mode). |
| `--model MODEL` | Claude model to use (default: `claude-opus-4-8`). |
| `--max-body-chars MAX_BODY_CHARS` | Max story body characters sent to the API (default: `100000`). |
| `--format {jsonl,json,tsv,human}` | Output format (default: `jsonl`). |
| `--output OUTPUT` | Write output to a file instead of stdout. |
| `--dry-run` | Run pre-flight QA checks and list files without calling the API. |
| `--progress` / `--no-progress` | Toggle progress display. |

See [`docs/how-to/run-assess.md`](../how-to/run-assess.md) for mode selection
guidance, manual prompt validation, and dry-run usage.

```
lcats assess corpora/sherlock --genre 'science fiction'
lcats assess data/ --genre horror --format tsv --output horror.tsv
lcats assess data/ --genre western --dry-run
ANTHROPIC_API_KEY=sk-... lcats assess corpora/ --genre romance --progress
```

## `stats`

```
lcats stats [--dedupe] [--no-dedupe] [--story-output STORY_OUTPUT]
            [--author-output AUTHOR_OUTPUT]
            [directories ...]
```

Compute story-level and author-level statistics for one or more corpus
directories or JSON files.

| Argument / Flag | Description |
|---|---|
| `directories` | Directories or files to compute statistics for. |
| `--dedupe` / `--no-dedupe` | Toggle deduplication by story identity. |
| `--story-output STORY_OUTPUT` | Write per-story stats to this file. |
| `--author-output AUTHOR_OUTPUT` | Write per-author stats to this file. |

```
lcats stats corpora/sherlock
lcats stats data/ --no-dedupe
lcats stats data/ --story-output story_stats.tsv --author-output author_stats.tsv
```

## `repair-specials`

```
lcats repair-specials [--header] [--format {tsv,jsonl}] files [files ...]
```

Generate conservative repair proposals for known mojibake fragments. This
command is non-destructive — it never modifies the input files.

| Argument / Flag | Description |
|---|---|
| `files` | Story JSON files to generate repair proposals for. |
| `--header` | Include a header row (TSV format only). |
| `--format {tsv,jsonl}` | Dry-run report format (human TSV or machine JSONL). |

## `promote`

```
lcats promote [--source SOURCE] [--dest DEST] [--dry-run] [collections ...]
```

Promote `data/` collections into `corpora/`. A collection with any mojibake
finding is skipped and reported rather than promoted; clean collections
wholesale-replace their `corpora/` counterpart.

| Argument / Flag | Description |
|---|---|
| `collections` | Collection names to consider. Defaults to every collection under `--source`. |
| `--source SOURCE` | Root directory of source collections (default: `data/`). |
| `--dest DEST` | Root directory to promote clean collections into (default: `../corpora`). |
| `--dry-run` | Survey and report without copying any files. |

See [`corpus-promotion.md`](corpus-promotion.md) for the full command
explanation, collection-name mapping, and exit-code semantics.

## `clean`

```
lcats clean [--data-only] [--cache-only] [gatherers ...]
```

Clear `data/` and/or `cache/` contents without shell-glob reasoning. Safe for
a symlinked `data/` or `cache/` setup: only contents are removed, never the
directory (or symlink) itself.

| Argument / Flag | Description |
|---|---|
| `gatherers` | Gatherer names to clean under `data/`. **With no names given, this does not scope to "every configured gatherer" one by one — it wholesale-clears everything under `data/`, including any custom or unregistered directories that aren't a known gatherer.** Naming specific gatherers instead removes only those subdirectories. |
| `--data-only` | Clean only `data/`; leave `cache/` untouched. |
| `--cache-only` | Clean only `cache/`; leave `data/` untouched. |

See [Preparing a corpora release](prepare-corpora-release.md) step 2 for a
worked walkthrough of when and why to use `lcats clean`.

## `meta register`

```
lcats meta register [--force] repo_locator
```

Register a repository locator in the local workspace registry.

| Argument / Flag | Description |
|---|---|
| `repo_locator` | The repository locator to register. |
| `--force` | Allow duplicate `repo_locator` entries. |

## Placeholder commands

These commands are declared but not yet implemented — running them prints a
"not yet implemented" message and exits.

| Command | Description |
|---|---|
| `lcats index` | Preprocess a corpus to answer questions. |
| `lcats advise` | Run the LCATS command-line advising tool. |
| `lcats eval` | Evaluate LCATS on a benchmark suite. |
