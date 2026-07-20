# Quickstart

This tutorial takes you from a fresh clone to your first working `lcats` command. Every
command below was run in order, in a real environment, before this page was written — the
output shown is what you should actually see, not an approximation.

No API key is required for anything in this tutorial.

## 1. Clone and set up

```bash
gh repo clone xenotaur/LCATS
cd LCATS/lcats
```

LCATS's execution root is the nested `lcats/` directory, not the repository root — every command
in this tutorial (and everywhere else in LCATS's docs) assumes you're standing in `LCATS/lcats/`.

### Prerequisites

Before building, make sure you're on **Python 3.10 or later**. Several LCATS modules use `X |
None` union-type syntax evaluated at import time, which raises an error on import before 3.10 —
including `lcats/lcats/meta_registry.py`, which `lcats/cli.py` imports directly, so this isn't a
theoretical edge case: an unsupported interpreter breaks `lcats info` in the very next step, not
just some rarely-used command. (`pyproject.toml` and `setup.py` still declare `>=3.6`; that's
stale — see [`lcats/README.md`](../../README.md#requirements) for the full explanation.)

Install the packages `scripts/build` and `scripts/develop` need (from
[`lcats/README.md`](../../README.md#requirements)):

```bash
pip install build    # can be conda installed: conda install conda-forge::python-build
pip install twine     # can be conda installed: conda install conda-forge::twine
pip install beautifulsoup4
pip install lxml
conda install conda-forge::parameterized
```

If you're using conda, make sure your environment is activated first.

### Build and install

```bash
scripts/clean && scripts/build && scripts/develop
```

`scripts/clean` removes previous build artifacts (`build/`, `dist/`, `*.egg-info`) — it does not
touch any corpus data, and is unrelated to the [`lcats clean` CLI command](../reference/cli-commands.md#clean).
`scripts/build` builds the package; `scripts/develop` installs it in editable mode, so further
edits to the source are picked up without reinstalling.

If `scripts/develop` fails with a missing-package error even after the prerequisites step above,
you're likely running a system or Homebrew Python rather than the conda environment LCATS expects.

## 2. Verify the install

```bash
lcats info
```

Expected output:

```
LCATS is a literary case based reasoning system.
```

If you see this, the `lcats` command is on your `PATH` and the install worked.

## 3. Run your first command: `lcats survey`

`lcats survey` checks corpus JSON files for quality issues — encoding damage, boundary
contamination, and similar defects — without changing anything. Point it at a single story file
from the bundled `corpora/` collection:

```bash
lcats survey ../corpora/sherlock/boscombe_valley.json --no-progress
```

Expected output:

```
../corpora/sherlock/boscombe_valley.json
  [spchar] error: Special character finding. (U+00A9, '©')
    context: lies my mÃ©tier,\nand
  [spchar] error: Special character finding. (U+00A9, '©')
    context: g so outrÃ© as a dyin
```

Exit code `1`. That's expected, not a failure — `boscombe_valley.json` genuinely has two
mojibake findings (mangled accented characters from a bad encoding round-trip somewhere upstream),
and `survey`'s exit code reflects that. Each finding shows the Unicode codepoint involved and a
snippet of surrounding text so you can see exactly where it occurs.

**What just happened:** `survey`'s `[spchar]` check flagged two spots where accented characters
(`é` in "métier" and "outré") were mangled into `Ã©` sequences — a classic UTF-8-decoded-as-Latin-1
mojibake pattern. This is real, pre-existing content in the bundled corpus, not a fabricated
example. For the full flag reference, see
[`docs/reference/cli-commands.md`](../reference/cli-commands.md#survey).

## 4. An alternative first command: `lcats assess --dry-run`

`lcats assess` is LCATS's LLM-powered curation tool — it calls the Claude API to score a story for
quality and genre fit. `--dry-run` runs only the pre-flight checks (file discovery, QA findings)
without calling the API, so it costs nothing and needs no key:

```bash
lcats assess ../corpora/sherlock/boscombe_valley.json --dry-run
```

Expected output:

```
[dry-run] ../corpora/sherlock/boscombe_valley.json
  Title:    Sherlock Holmes - The Boscombe Valley Mystery
  Author:   Arthur Conan Doyle
  Genre:    (detect mode)
  QA findings (2):
    [ERROR] mojibake-sequence: Likely mojibake sequence.
    [ERROR] mojibake-sequence: Likely mojibake sequence.
```

Exit code `0` — a dry run always succeeds; it's reporting the same two findings `survey` found,
just as a curation pre-check rather than a standalone report.

## 5. Next steps

- To run a **live** `lcats assess` call (spends API credits), see
  [Setting up API keys](../secrets-setup.md) first, then
  [How to run `lcats assess`](../how-to/run-assess.md) for mode selection and manual
  prompt-validation guidance.
- For the full flag reference of every `lcats` subcommand, see
  [`docs/reference/cli-commands.md`](../reference/cli-commands.md).
- For the `LLMBackend` abstraction `lcats assess` is built on, see
  [`docs/reference/llm-backend.md`](../reference/llm-backend.md).
- To understand the corpus analysis subsystem `survey` belongs to, see
  [`lcats/analysis/corpus/README.md`](../../lcats/analysis/corpus/README.md).
