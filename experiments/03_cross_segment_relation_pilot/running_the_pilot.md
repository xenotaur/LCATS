# Running the cross-segment relation density pilot

This is a manual runbook for a developer/dogfooder actually executing
`run_pilot.py`, not a viewer deciding whether to trust its output — see
`README.md` in this directory for the pilot's purpose, genre strata, metric
definitions, and output-file formats. This runbook is about getting the
script to actually run in your environment, smoke-testing it safely before
spending real API cost, and closing out `WI-EVENT-0030` once you have real
findings.

Every command below is meant to be copy-pasted into a plain terminal — it
does not assume Claude, an agent, or any tool beyond a shell and this repo
checked out locally. If a step doesn't produce the output shown, stop and
check the Troubleshooting section before continuing.

**Directory:** all commands below run from the repo root unless stated
otherwise.

## 1. Environment setup

```bash
cd lcats
scripts/develop
```

This installs `lcats` in editable mode (`pip install -e ".[dev]"`). Note
that the `dev` extra does **not** include `spacy`/`stanza` — those live in
a separate `nlp` extra (`lcats/pyproject.toml`'s
`[project.optional-dependencies]`). You do not need them yet; see Step 2.

## 2. Smoke-test before spending real API cost

`--dry-run` uses a `FakeBackend` for every LLM call (genre detection,
segmentation, and the full Event-Role-World pipeline), so nothing in this
step costs money or requires API credentials. It's split into three
scenarios depending on what you want to verify.

On a fresh checkout, `lcats/data` (the script's default `--data-dir`) does
not exist yet — it's gitignored working-corpus state, not tracked in git
(see `.gitignore`'s `lcats/data` entry). `corpora/` is the tracked,
released snapshot and is always present, so every command below passes
`--data-dir corpora` explicitly. (If you'd rather use `lcats/data`,
generate it first via `lcats gather` — see
`lcats/docs/reference/prepare-corpora-release.md`.)

### 2a. Zero-dependency smoke test (recommended first)

```bash
cd ..   # repo root, if you're still in lcats/
python experiments/03_cross_segment_relation_pilot/run_pilot.py --dry-run \
    --data-dir corpora --sample-size 2 --output /tmp/pilot_dry_run
```

`--dry-run` alone defaults `--nlp-backend` to `"fake"`
(`nlp_backend.FakeNLPBackend`) — this genuinely needs **nothing** beyond
the base `lcats` install from Step 1: no `spacy`, no `stanza`, no model
downloads. It confirms the script's control flow (sample selection, the
stubbed single-segment stage-1 segmentation, and output-file writing) all
work in your environment before you touch any NLP toolkit or spend a
dollar. It does **not** exercise the story-level cross-segment relation
pass specifically — that pass only runs when events exist in at least 2
distinct segments (see `_run_erw_pipeline`'s guard in `run_pilot.py`), and
the dry-run's single stubbed segment with a fake (empty) LLM response
never produces any events at all. Treat this step as a control-flow and
output-format smoke test, not coverage of every pipeline stage.

Expect every row to show `excluded: false` with all-zero counts (a fake
backend can't produce real content) — that's correct, not a bug:

```bash
cat /tmp/pilot_dry_run/pilot_stories.jsonl
cat /tmp/pilot_dry_run/pilot_summary.json
cat /tmp/pilot_dry_run/pilot_usage.jsonl
rm -rf /tmp/pilot_dry_run   # cleanup, this was just a smoke test
```

### 2b. Test your spaCy install

If the real run will use `--nlp-backend spacy` (the default for a real
run), verify the toolkit itself works — still with zero API cost, by
combining `--dry-run` with an explicit `--nlp-backend spacy`:

```bash
cd lcats && pip install -e ".[dev,nlp]" && python -m spacy download en_core_web_sm && cd ..
python experiments/03_cross_segment_relation_pilot/run_pilot.py --dry-run \
    --data-dir corpora --nlp-backend spacy --sample-size 2 \
    --output /tmp/pilot_dry_run_spacy
```

An explicit `--nlp-backend spacy` overrides the `--dry-run` default of
`"fake"`, so this run genuinely calls spaCy's real tokenizer/tagger/parser
on real segment text (LLM calls are still faked). If this fails with
`ModuleNotFoundError: No module named 'spacy'`, see Troubleshooting below.

```bash
cat /tmp/pilot_dry_run_spacy/pilot_stories.jsonl
rm -rf /tmp/pilot_dry_run_spacy
```

`word_count` is computed directly from the story text regardless of NLP
backend, so it won't change from 2a. The NLP backend is loaded once,
before any story runs — look for the script's own
`Loading NLP backend: spacy...` / `NLP backend ready: spacy` console lines
(printed once, near the start) as confirmation, rather than inferring it
from `elapsed_seconds`: since loading now happens outside the per-story
timer, each row's `elapsed_seconds` reflects only real inference time
(typically well under a second per story for spaCy), not a multi-second
load — a small number here is expected and does **not** mean spaCy didn't
run.

### 2c. Test your Stanza install

Same idea, for Stanza:

```bash
cd lcats && pip install -e ".[dev,nlp]" && python -c "import stanza; stanza.download('en')" && cd ..
python experiments/03_cross_segment_relation_pilot/run_pilot.py --dry-run \
    --data-dir corpora --nlp-backend stanza --sample-size 2 \
    --output /tmp/pilot_dry_run_stanza
```

```bash
cat /tmp/pilot_dry_run_stanza/pilot_stories.jsonl
rm -rf /tmp/pilot_dry_run_stanza
```

Stanza's own "Loading these models..." banner prints once, near the start
of the run (before any story is processed), not once per story — if you
see it repeated once per story, something has regressed (the NLP backend
should be built once and reused across the whole sample).

You only need one of 2b/2c working for Step 4 (whichever `--nlp-backend`
you plan to use for real) — running both is just extra confidence.

## 3. API credentials

```bash
mkdir -p .secrets
echo "ANTHROPIC_API_KEY=sk-ant-..." > .secrets/anthropic_api_keys.env
```

(Swap in `openai_api_keys.env` / `OPENAI_API_KEY` if you're running with
`--backend openai` instead — the script defaults to `--backend anthropic`.)
Full explanation of the `.secrets/` pattern: `lcats/docs/secrets-setup.md`.
`.secrets/` is gitignored at the repo root; nothing here risks being
committed. A real shell-exported key (e.g. a CI secrets manager) always
takes precedence over `.secrets/` files.

## 4. The real run

This defaults to `--data-dir lcats/data`, the live working corpus — not
`corpora/`, the frozen release snapshot used for the smoke tests in Step 2.
If `lcats/data` isn't populated yet in your checkout, generate it first
(`lcats/docs/reference/prepare-corpora-release.md`'s "Regenerate" step,
`lcats gather`), or pass `--data-dir corpora` here too if the released
snapshot is sufficient for your purposes.

```bash
python experiments/03_cross_segment_relation_pilot/run_pilot.py \
    --sample-size 5 \
    --output experiments/03_cross_segment_relation_pilot/results
```

Read the README's **Cost note** section before running this — real LLM API
calls happen for genre detection (one call per candidate story scanned,
which can exceed 4 × 5 = 20 depending on the corpus's genre distribution),
segmentation (one call per sampled story), and the Event-Role-World
pipeline itself (4 calls per segment + 1 story-level cross-segment call per
story). `--sample-size 5` (the low end of `WI-EVENT-0030`'s 5–10 range) is
the right place to start.

The script prints progress as it runs (`[genre-detect] ... -> <genre>`
during sampling, then `Running pipeline: [<genre>] <file>` per story, with
`excluded: <reason>` inline for any story that fails). It exits `0` on
success, `1` on a missing/broken backend, `2` if it couldn't fill every
genre stratum before exhausting `--max-candidates` (default 200 — raise
this if a stratum comes up short).

**If the run is interrupted (Ctrl-C, crash, closed terminal), just re-run
the exact same command.** Every stage already checkpointed under
`--output` is served from disk instead of re-issuing its LLM call — see
the README's **Checkpointing and resume** section. Nothing already paid
for is lost or repeated.

## 5. Inspect the results

```bash
cat experiments/03_cross_segment_relation_pilot/results/pilot_summary.json
```

Use `mean_cross_segment_density_per_1000_words` — **not**
`mean_folded_relations_per_1000_words`, which mixes in same-segment
relations too and can't isolate the cross-segment effect. See the README's
"Metric definitions" section if the distinction isn't clear.

```bash
cat experiments/03_cross_segment_relation_pilot/results/pilot_stories.jsonl
```

Check for `excluded: true` rows and their `exclude_reason` before trusting
the aggregate — a genre with a high exclusion rate deserves a second look
(or a re-run with a fresh `--seed`) before treating its mean as reliable.

```bash
cat experiments/03_cross_segment_relation_pilot/results/pilot_usage.jsonl
```

Cost/latency detail per pipeline pass, if you want to report actual token
spend alongside the findings.

## 6. Write up the finding

Copy the README's "Expected Results Format" table structure into a new
`## Results (YYYY-MM-DD)` section in `README.md`, fill it in with the real
`pilot_summary.json` numbers, and write the **Finding** paragraph: does the
real run confirm, weaken, or contradict `WI-EVENT-0028`'s smaller-sample
finding that science fiction/horror shows materially more long-range
cross-segment causal chains than the other strata? Ground the claim in the
actual numbers, not just "yes it matches."

## 7. Close out WI-EVENT-0030

```bash
cd lcats
lrh validate
```

Confirm 0 errors. Then update the work item's frontmatter
(`project/work_items/proposed/WI-EVENT-0030.md`): `status: proposed` →
`resolved`, `resolution: null` → a one-line summary quoting the real
finding and commit, then move the file:

```bash
mkdir -p project/work_items/resolved
git mv project/work_items/proposed/WI-EVENT-0030.md project/work_items/resolved/WI-EVENT-0030.md
lrh validate   # re-confirm after the frontmatter edit
```

If this happens on a feature branch via a PR (the pattern the rest of this
project's Event-Role-World work has followed), push and open the PR as
usual, then run the review-response → confirm-fixes → merge → closeout
cycle (`/lrh-review-response`, `/lrh-confirm-fixes`, `/lrh-closeout`)
rather than committing straight to `main`. See `project/work_items/README.md`
for the work-item lifecycle conventions.

## Troubleshooting

### `ModuleNotFoundError: No module named 'spacy'` (or `'stanza'`)

This happens if you run a real (non-`--dry-run`) pilot, or `--dry-run
--nlp-backend spacy`/`stanza` (Step 2b/2c), without installing the `nlp`
extra first:

```bash
cd lcats   # pyproject.toml lives here, not at the repo root
pip install -e ".[dev,nlp]"
python -m spacy download en_core_web_sm      # if using spaCy
python -c "import stanza; stanza.download('en')"   # if using Stanza
cd ..
```

Root cause: `lcats/pyproject.toml`'s `[project.optional-dependencies]`
puts `spacy`/`stanza` in a separate `nlp` extra, not in `dev` — a standard
`scripts/develop` setup (Step 1) never installs them. This is why Step 2a
(the zero-dependency smoke test) exists and should be your first check —
it isolates whether a failure is this dependency gap versus something
else in the script or your credentials.

Grounding: [spaCy's install docs](https://spacy.io/usage) show the same
two-step shape (`pip install -U spacy`, then a separate
`python -m spacy download en_core_web_sm`) — trained pipelines are their
own installable packages, not bundled into the base `spacy` wheel.
[Stanza's docs](https://stanfordnlp.github.io/stanza/getting_started.html)
work the same way: `pip install stanza`, then
`stanza.download('en')` to fetch the model separately.

### Script exits with code `2`

A genre stratum couldn't be filled before `--max-candidates` (default 200)
candidates were scanned. Either the corpus is thin for that genre, or the
classifier is disagreeing with your expectation — re-run with a higher
`--max-candidates`, or check `lcats assess --genre <genre> <file>
--format human` directly on a story you expected to match
(`lcats/docs/how-to/run-assess.md` has more on manual prompt validation).

### High exclusion rate in `pilot_stories.jsonl`

Check `exclude_reason` per excluded row. A `segmentation failed: ...`
reason with real API credentials configured usually means a transient
backend error (safe to re-run) — this pilot deliberately excludes rather
than silently zero-filling these, so a re-run with a fresh `--seed` is the
right move, not editing the results by hand.
