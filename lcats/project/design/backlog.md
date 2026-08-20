# LCATS Backlog

Untracked or under-tracked follow-up items: things worth doing that don't
currently have a work item, workstream, or proposal of their own. This is a
plain notes file, not an LRH planning-node type — it isn't schema-validated
by `lrh validate` and doesn't carry frontmatter. When an item here is ready
to be scoped, promote it via `/lrh-work-item` (or `/lrh-workstream` /
`/lrh-proposal` if it's bigger than one work item) and remove it from this
list rather than letting it live in both places.

Add an entry here whenever a workstream closes with unresolved Non-Goals,
or when review/investigation surfaces a real gap that isn't worth blocking
the current PR on. Each entry should say what's known now and what the
first concrete next step would be — not a full design.

**Priority tags** (added 2026-08-02, per a resolution-plan review):
`P0` = silent/data-corrupting, fix first; `P1` = silent-but-lower-impact or
loud-but-blocking; `P2` = loud failure and/or low-frequency use, or purely
cosmetic; `P3` = a decision or cost estimate is needed before any code gets
written, not an implementable fix on its own. Ranked by failure-mode
severity first (silent > loud > cosmetic), then effort-to-fix — a silent
failure gives no signal to prompt anyone to notice it, so it's worth fixing
before a loud one even if the loud one blocks more use cases.

---

### `_locate_anchor_span`'s whitespace-tolerant fallback never handles paragraph-marker leakage or curly-quote typography — P2, resolved

Surfaced 2026-08-19 during `WI-SEGMENT-0069`'s investigation into the
segmentation alignment failures remaining after the fix below
(`find_anchor_in_range`'s whitespace-normalized fallback entry). A live
30-story smoke test found the dominant remaining category,
`anchor_absent_from_document` (15 of 21 `alignment_error` failures), was
not one thing: manual inspection of the real captured anchors found two
distinct, narrowly-fixable sub-patterns within it.

1. **Paragraph-index marker leakage.** `paragraph_text_indexer` prefixes
   each paragraph shown to the model with a `[PNNNN]` marker (e.g.
   `[P0047]`), but alignment searches `canonical_text`, which never
   contains these markers. At least 3 stories' anchors included the
   literal marker as a prefix or (at a segment's own paragraph boundary)
   mid-anchor — and this recurred on 3–6 segments within each affected
   story, not as an isolated one-off.
2. **Typographic quote/dash mismatch.** The source corpus uses Unicode
   curly quotes/dashes; the model's anchor text uses plain ASCII
   equivalents. Confirmed in 2 stories where the anchor resolves to an
   exact match once typography is normalized.

Findings, full evidence, and a per-category recommendation are recorded
in `project/design/segmentation-alignment-failure-categories.md`
(`WI-SEGMENT-0069`); the real captured anchors needed to reproduce these
cases deterministically are committed separately as
`experiments/03_cross_segment_relation_pilot/fixtures/wi_segment_0069_alignment_cases.json`.

**Resolved 2026-08-20:** implemented via `WI-SEGMENT-0070`.
`_locate_anchor_span`'s whitespace-tolerant fallback now strips a leaked
`\[P\d{4}\]\s*` marker (the exact 4-digit zero-padded format
`add_paragraph_markers` emits — not a looser `\d+`, which would also
strip real story content that merely resembles a marker, e.g. a
3-digit citation like `[P045]`) from the anchor, and normalizes Unicode
curly quotes (`“”‘’`) and em/en dashes to their ASCII equivalents on
both the anchor and the searched text (via a length-preserving
`str.translate`, so a match found in the normalized copy still maps 1:1
onto the real position in the original text) before building the
regex. Regression tests replay all 16 real fixture segments across all
5 cited stories end-to-end via `align_segment`, plus synthetic edge
cases for a mid-anchor marker and a non-marker 3-digit bracket that must
not be stripped. Two other categories from the same investigation —
paragraph mis-numbering and the residual near-miss-quoting bucket — are
explicitly out of scope for this fix; see `WI-SEGMENT-0069`'s design
doc for why.

---

### `find_anchor_in_range`'s whitespace-normalized fallback discards its own successful match — P1, resolved

Surfaced 2026-08-14 during a `WI-EVENT-0033` verification smoke test
(real API, 20 stories, `claude-haiku-4-5-20251001`): rather than the
expected exclusion-rate improvement, the run measured a 100%
alignment-failure rate (up from the original 65% `parsing_error`
baseline). `WI-EVENT-0033`'s own targeted fix genuinely worked — zero
`parsing_error` outcomes across all 20 stories — but a separate, newly
surfaced failure mode dominated instead: 18 of 20 `alignment_error`
outcomes, all with the identical signature ("anchor text not found in
story text"), plus 2 `no_segments`.

Root cause, confirmed by direct instrumentation against a fresh API
response (not assumed): `text_segmenter.py`'s `find_anchor_in_range`
already has a whitespace-normalized fallback for when an LLM-provided
anchor quote doesn't exact-match the source text — but that fallback's
second stage re-searches a window of the **original, non-normalized**
text using the **original, non-normalized** anchor string, which is
exactly as exact-match-strict as the first search it's meant to be a
fallback for. So whenever the mismatch specifically *is* a
whitespace/newline difference — the only case the fallback exists to
handle — it fails identically to the first search and discards its own
already-found correct match, returning `None`.

Reproduced concretely: `mass_quantities/junior__abernathy`'s
segment-3 `end_exact` came back as `"glowered suspiciously at Mater and
the\nneighbors."` against real source text `"...the neighbors.\n\n"` —
the words are 100% correct; only the line-wrap newline position differs
(the model mis-recalled where Project Gutenberg's ~72-char hard-wrap
falls, not a content error). This is a **newly surfaced**, not newly
introduced, bug: `WI-SEGMENT-0059` (resolved, a distinct paragraph-
collapse bug) made alignment failures raise instead of silently
producing wrong offsets, which is what made this pre-existing gap
visible for the first time — it was never actually exercised by a
passing case before.

**Resolved 2026-08-18:** scoped via [PR #309](https://github.com/xenotaur/LCATS/pull/309)
and implemented via `WI-SEGMENT-0068`'s own implementation PR.
`find_anchor_in_range`'s second stage now builds a whitespace-tolerant
regex directly from `anchor` — splitting it into whitespace and
non-whitespace runs, escaping only the non-whitespace runs, and joining
them with `\s+` — searched against the full `segment` via `re.search`,
rather than re-searching a heuristic window with the original,
non-normalized anchor string. The now-unused `_norm_ws`/`_WS` helpers
were removed as dead code. Regression tests replay the exact captured
real case (`mass_quantities/junior__abernathy`'s segment-3 `end_exact`)
against the real committed corpus text, plus edge cases for
regex-special characters in the anchor and a genuinely-wrong anchor
(different words, not just different whitespace) still correctly
returning `None`.

---

### `lrh work-items validate`'s custom frontmatter parser rejects comments inside YAML lists, and `lrh validate` doesn't catch it — P1, analysis delegated to LogicalRoboticsHarness

Surfaced 2026-08-08 while fixing `WI-LLM-0056.md`'s `malformed-frontmatter`
error. `lrh`'s own frontmatter parser
(`lrh.control.parser.parse_markdown_text`, in the sibling
`LogicalRoboticsHarness` repo at
`logical_robotics_harness/src/lrh/control/parser.py`) is a custom parser,
not PyYAML - and it cannot handle a `#` comment line interleaved between
items of a YAML list (e.g. `artifacts_expected:` with a `# note` line
between two `- path` entries). PyYAML parses this shape fine, so
`lrh validate` (the general, top-level validator) reports 0 errors on a
file with this pattern, but `lrh work-items validate --project-root
<path>` fails it with `malformed-frontmatter`
(`unsupported nested mapping for key '<field>': '<comment line>'`), and
`lrh work-items readiness <id>` fails with "work item not found" even
though the file exists. Nothing in CI or the standard `lrh validate` path
catches this before it lands - confirmed by the fact that this exact
pattern was independently introduced and then independently
rediscovered-and-fixed *twice* in parallel by different concurrent
sessions on 2026-08-08: `WI-LLM-0056.md` (fixed in PR #259) and
`WI-LLM-0051.md` (fixed in PR #254). A repo-wide scan of every `.md` file
under `lcats/project/` on `origin/main` after both fixes landed found no
further instances, but nothing prevents a new one from being introduced
again the same way (e.g. by an agent adding an explanatory YAML comment
inside a list it's editing, which is valid YAML and easy to reach for).
Either fix belongs in `LogicalRoboticsHarness`, not `LCATS` - this repo
can only work around the gap per-file, not close it. **Next step:** an
analysis prompt covering root cause, the `lrh validate` vs. `lrh
work-items validate` inconsistency, fix options (parser tolerance vs.
extending `lrh validate`'s coverage), and blast radius to other
planning-node types was handed off 2026-08-08 to a session in the
`LogicalRoboticsHarness` repo directly - check back there for findings
and fix status before starting independent work on this from the `LCATS`
side.

---

### Concurrent sessions independently minted the same WI number under different prefixes — P2, decision needed

Surfaced 2026-08-07 while creating `WI-PILOT-0051`: at least four work
items now share the numeric suffix `0051` under different prefixes -
`WI-LLM-0051` (created 2026-08-05), `WI-ANNOTATE-0051` (created
2026-08-06, resolved), `WI-ASSESS-0051` (created 2026-08-07, PR #235),
and `WI-PILOT-0051` (created 2026-08-07, PR #237, resolved). Each was
created by a different concurrent session independently computing "next
number = global max + 1" against `main` at a moment when the other
sessions' PRs hadn't yet merged, so multiple sessions landed on the same
number - a true concurrency race.

A second, numerically similar but mechanistically **different** incident
surfaced 2026-08-08: `WI-PROCESSING-0057` (first commit
2026-08-08T00:40:00Z, PR #250) shares its suffix with `WI-PILOT-0057`
(PR #247, merged 2026-08-07T23:46:06Z). Unlike the `*-0051` incidents,
this was **not** a same-moment race - `WI-PILOT-0057` had already merged
to `main` roughly 54 minutes before `WI-PROCESSING-0057`'s first commit
(review finding, PR #256 - an earlier draft of this entry misdated
`WI-PROCESSING-0057`'s creation using its PR's `createdAt` field rather
than its actual first commit / execution-record timestamp, and wrongly
described this as concurrent). The `WI-PROCESSING-0057` session's "next
number" computation must have used a checkout that hadn't picked up
`WI-PILOT-0057`'s merge yet (a stale/non-fresh `git pull` before
computing max+1, not simultaneous computation) - a distinct failure
mechanism worth tracking separately even though the symptom (a
duplicate suffix) looks identical.

A third incident, also 2026-08-08 and also a stale-checkout case:
`WI-PILOT-0058` (first commit 2026-08-08T02:31:52Z, PR #252, merged
2026-08-08T03:02:18Z) shares its suffix with `WI-LLM-0058` (first
commit 2026-08-08T04:31:13Z, PR #257). About 89 minutes separate
`WI-PILOT-0058`'s merge from `WI-LLM-0058`'s first commit - close to
the `*-0057` incident's 54-minute gap, not a same-moment race - so
this is a second confirmed instance of the stale-checkout mechanism
(review finding, PR #265 - an earlier draft of this entry's `*-0059`
addition missed this pre-existing `*-0058` collision entirely, only
counting the incidents it happened to be investigating).

A fourth incident surfaced 2026-08-08: `WI-SEGMENT-0059` (first commit
2026-08-08T04:29:27Z, PR #255, merged 2026-08-08T05:03:40Z) shares its
suffix with `WI-LLM-0059` (first commit 2026-08-08T05:04:40Z, PR #260).
Only about 60 seconds separate `WI-SEGMENT-0059`'s merge from
`WI-LLM-0059`'s first commit - close enough in time that this pattern
matches the `*-0051` same-moment race, not the stale-checkout case's
longer gaps, though (as with the earlier entries) the exact causal
mechanism inside the `WI-LLM-0059` session's own checkout wasn't
independently inspected, only the public commit/merge timestamps. The
two items are topically unrelated - `WI-SEGMENT-0059` fixes a
`text_segmenter.py` alignment bug found during `WI-ANNOTATE-0054`'s
trial; `WI-LLM-0059` investigates a `scene_analysis.py` system-prompt
mitigation for local-model segmentation reliability,
`depends_on: [WI-LLM-0051]` - the collision is purely numeric, not a
sign either item duplicates or should be merged with the other.

In total, ten work items across four incidents now share a
duplicate numeric suffix (four `*-0051` items from a same-moment
concurrency race, two `*-0057` items and two `*-0058` items from two
separate stale-checkout cases, two `*-0059` items from a second
same-moment race). No technical collision resulted in any case
(`lrh validate` passes; each full ID string - prefix plus number - is
unique), but all four defeat the shared cross-prefix numbering pool's
intent of an unambiguous sequence, and the recurrence (four separate
incidents within two days, two confirmed distinct failure mechanisms
each recurring at least twice) suggests this is not a rare edge case
but a predictable consequence of how often concurrent sessions create work
items in this project. **Next step:** this is a design-shaped question,
not a quick fix - decide whether to (a) accept occasional same-number
collisions as a known limitation of the current "compute max+1 from
`main`" convention (numbers are for uniqueness within a prefix's own
namespace, not a global sequence, despite the existing "shared
cross-prefix pool" convention), (b) prefix-scope the numbering instead
(each prefix gets its own independent sequence, removing the
cross-prefix uniqueness expectation entirely), or (c) add a real
coordination mechanism (e.g. a reserved-numbers file, a CI check that
fails on a newly-introduced duplicate suffix across prefixes, or a
numbering authority) - note that (c) would need to guard against both
failure mechanisms found here, not just true concurrency. Does not
retroactively rename any of the ten existing collided items - renaming
a resolved/merged item touches
cross-references and git history and is a separate decision.

---

### Unguarded `pathlib.Path.resolve()` calls could crash callers on filesystem errors — P2, resolved

Surfaced 2026-08-07 during `WI-ASSESS-0050`'s review (Copilot found the
underlying bare-relative-path edge case; self-review then found this
follow-on robustness gap while fixing it): `assess.py`'s `assess_story`
originally added an unguarded `file_path.resolve()` call to recover a
story's real directory name when `file_path.parent.name` is lexically
empty (a bare relative path like `Path("story.json")` run from inside its
own bucket directory). `resolve()` touches the filesystem and can raise
(e.g. on a broken symlink loop or a permission error walking the path) —
in `assess_story`'s case this call sat *before* the function's own
`try/except Exception` block, so a resolve failure would have propagated
out and crashed the whole call instead of returning an `AssessmentResult`
with `error` set. Fixed locally in `assess_story` (guarded with
`except OSError`, falling back to an empty title). The same *unguarded*
`.resolve()` pattern was confirmed to exist at 15 total call sites via
`grep -rn "\.resolve()" lcats/src/lcats/` (excluding tests), across
`promote.py`, `processing.py`, `output.py` (including `story_dir_value`,
the very function `assess_story`'s fix was modeled on but never itself
fixed), `utils/paths.py`, and `utils/checkpoint.py`.

**Full audit completed 2026-08-08** (scoped as `WI-PROCESSING-0057`,
correcting an earlier revision of this same entry that claimed the audit
was done before it actually was — caught by review on that WI's own
creation PR):

- **6 call sites across 3 functions needing a guard (fixed by
  `WI-PROCESSING-0057`):**
  `assess.py:350` (`assess_story`, 1 call, widened from
  `WI-ASSESS-0050`'s original guard), `output.py:113`
  (`story_dir_value`, 1 call, reachable from
  `cli.py`'s `run_survey` per-file loop, which has no per-file exception
  handling at all), and `processing.py`'s `process_file`
  (lines 40-42, three per-file resolves before its own
  `try/except Exception`) plus `process_files`' eager per-file
  `resolve()` in its `normalized_files` list comprehension
  (lines 121-123), which runs *before* `process_file`'s own per-file
  loop even starts and so defeats that function's fault isolation for
  every file in the batch, not just the one with a bad path. **All
  three guards must catch `(OSError, RuntimeError)`, not `OSError`
  alone** — `resolve()` raises `RuntimeError` for a symlink loop on
  Python 3.10-3.12 (confirmed by reproducing a symlink loop and calling
  `.resolve()` directly on Python 3.11.8, the interpreter this repo's
  own test suite runs under), only switching to `OSError` on 3.13+; this
  repo's `pyproject.toml` declares `python_requires = ">=3.10"`, so an
  `OSError`-only guard leaves the motivating failure mode unhandled on
  every currently-supported Python version except the newest — a real
  gap Codex's review caught in `WI-ASSESS-0050`'s already-merged fix.
- **3 call sites across 2 functions left alone, batch-level
  configuration checks (also in `processing.py`):** `process_files`
  (lines 115-116,
  `corpora_root_path`/`output_root_path`, 2 calls) and `process_corpora`
  (line 184, `corpora_root_path`, 1 call) each resolve once per batch
  call, before any per-file loop exists — a failure here means the
  whole call's configuration is bad, not that one file among many is
  bad, so failing fast is correct (same category as the 6 sites below),
  not the per-item fault-isolation problem the 6 fixed sites address.
- **6 call sites across 3 functions left alone, pre-destructive/
  bootstrap safety checks:**
  `promote.py:249-250`'s `_validate_distinct_roots` (2 calls — resolves
  `--source`/`--dest` before comparing them to prevent a same-or-nested
  root from causing `_copy_collection`'s `rmtree` to destroy the source
  before `copytree` runs; confirmed by reading the function — an
  unresolvable root here means promotion cannot safely proceed at all),
  `utils/checkpoint.py:129-130,144`'s `_protected_roots`/
  `_check_working_root_allowed` (3 calls — resolves the canonical
  data/corpora roots and the caller's `working_root` before deciding
  whether a checkpoint write is allowed to a protected location;
  confirmed by reading the function — this is a write-protection guard
  that must fail closed, not open, on an unresolvable path), and
  `utils/paths.py:104`'s `find_pyproject_root` (1 call — resolves the
  starting search path before walking ancestors for `pyproject.toml`;
  confirmed by reading the function — this is bootstrap discovery that
  already documents raising `FileNotFoundError` for its own expected
  failure mode, so an unresolvable starting path is the same category
  of expected, propagate-don't-swallow failure).

Full count, re-verified against the actual code rather than restated
from this entry's own prior (incorrect) draft: 6 calls fixed
(`assess.py` ×1, `output.py` ×1, `processing.py`'s `process_file` ×3
and `process_files`' per-file resolve ×1) + 3 calls left alone as
batch-level configuration (`processing.py`'s `process_files` ×2 and
`process_corpora` ×1) + 6 calls left alone as pre-destructive/bootstrap
safety checks (`promote.py` ×2, `checkpoint.py` ×3, `paths.py` ×1) = 15
total, matching the original grep count exactly.

**Resolved 2026-08-08:** `WI-PROCESSING-0057` implemented and merged via
[PR #262](https://github.com/xenotaur/LCATS/pull/262) (commit
`25218bfc`). No further action.

---

## `quickstart.md` and `prepare-corpora-release.md` show mojibake examples that no longer reproduce — P2, cosmetic

Surfaced during `/lrh-doc-work` on `WS-STORY-BUCKET-LAYOUT` (2026-08-02).
Both docs' "expected output" blocks claim specific mojibake findings
(`corpora/sherlock/boscombe_valley`'s two findings in `quickstart.md`;
`data/mass_quantities/deny_the_slake__wilson`'s finding in
`prepare-corpora-release.md`) that no longer occur — verified by running
`lcats survey --mode specials` against the entire real `corpora/` tree:
zero mojibake findings anywhere. This isn't caused by the bucket-layout
migration (the file *paths* in these examples were fixed as part of that
doc-work run) — it's stale content, caused by the separate, already-closed
`WS-SPECIALS-CLEANUP` workstream cleaning up the real corpus since these
docs were written. Both blocks currently carry a stale-content notice
rather than a fix. **Next step:** find or construct a genuinely
reproducible current example (either a real remaining finding, if any
collection still has one, or a deliberately-seeded fixture) and replace
both illustrative blocks with output that actually reproduces today. Best
scoped as its own `/lrh-doc-work` run against `WS-SPECIALS-CLEANUP` as the
work reference, not the bucket-layout one.

---

## From WS-STORY-BUCKET-LAYOUT's Non-Goals (closed 2026-08-02)

Full audit of the governing proposal's Non-Goals section re-run 2026-08-02
(all 4 WI files' own Non-Goals just defer to the proposal — no additional
items found there). Three items below have no active tracker now that the
workstream is closed and archived
(`project/workstreams/resolved/WS-STORY-BUCKET-LAYOUT.md`). One proposal
Non-Goal is **not** listed here because it already has a home: "`lcats
gather` incremental/restartable checkpointing" is tracked via
`PROP-LCATS-PIPELINE-CHECKPOINTING` (adopted) → `WS-PIPELINE-CHECKPOINTING`
+ `WI-PIPELINE-0040`/`0041` (all still `proposed`).

### Hardcoded flat-layout paths in two notebooks — P2, loud but low-frequency

`lcats/notebooks/12_extract_scenes.ipynb` and `13_clean_corpus.ipynb` still
assume the retracted flat `<collection>/<story>.json` layout — re-verified
2026-08-02, still present. `12_extract_scenes.ipynb` has hardcoded absolute
local-machine paths ending in flat `.json` filenames (e.g.
`corpora/sherlock/noble_bachelor.json`, `corpora/massQuantities/...json` —
note the stale `massQuantities` casing too, a separate naming-drift signal).
`13_clean_corpus.ipynb` has a function parameter defaulting to
`ext: str = ".json"` and literal flat example paths
(`CORPORA_ROOT / 'mass_quantities/george_walker_at_suez.json'`). Per
`AGENTS.md`, notebooks aren't edited as a matter of course, so this was
deliberately left for a dedicated follow-up. **Resolved 2026-08-05:**
implemented and merged via
[WI-EXPERIMENTS-0048](https://github.com/xenotaur/LCATS/pull/225).
`12_extract_scenes.ipynb`'s `SAMPLE_OF_10`/`SAMPLE_OF_100` now draw a
seeded `random.sample()` from a new `canonical_story_files` variable
(`discovery.find_json_files`), not hardcoded literals.
`13_clean_corpus.ipynb`'s `missing_stories` now points at the real
current bucket directories. `rename_and_fix_json_files`'s `ext` default
was left untouched as a deliberate Non-Goal (moot but not broken).
This was the last item from the `WS-STORY-BUCKET-LAYOUT` follow-up
resolution plan; all four scoped batches are now merged.

### `check_segmentation_reliability.py`'s stem-collision bug — P0, silent data corruption

Re-verified 2026-08-02 (severity corrected from the original framing —
this is worse than "an output-naming bug," and worse than the two glob
bugs below, which was not obvious until the actual downstream code path
was traced): `experiments/03_cross_segment_relation_pilot/check_segmentation_reliability.py:193`
writes each story's result to `output_dir / f"{path.stem}.json"`.
`path.stem` is literally `"story"` for every bucket file now, so after
the *first* story writes `output_dir/story.json`, every subsequent story
hits the cache-check (`if result_path.exists(): cached = ...`, line 194)
and **silently reuses story #1's cached result as its own** — including a
`story_id` field also collapsed to `"story"`. The script completes
normally, prints what looks like per-story progress, and produces a
fully-formed report where every number after the first story is silently
wrong. No exception, no non-zero exit code, nothing to catch in a log.
**Correction (found during `WI-EXPERIMENTS-0046`'s own creation-PR review,
2026-08-02):** this script's file discovery (line 149,
`pathlib.Path(args.data_dir).rglob("*.json")`) is **not** fine on its own
— it was incorrectly cleared above. Two gaps, both folded into
`WI-EXPERIMENTS-0046`'s scope: (1) `path.parent.name` alone is only
unique *per collection* (per the governing proposal's own Decision 2),
not globally, and `--data-dir` defaults to the whole multi-collection
`corpora/` root, so two collections sharing a story slug would still
collide — the cache key must be collection-qualified, not just
directory-slug-qualified; (2) `rglob("*.json")` has no sidecar filter, so
a bucket sidecar file (`analysis.json` etc.) could be sampled as if it
were an independent story, and after fix (1) would collide with its own
real story's cache entry too — the canonical `discovery.find_json_files`
selector should be used instead. As of 2026-08-02 the real `corpora/`
tree has zero sidecar JSON files (1,868 tracked files, all `story.json`),
so gap (2) is a defensive/future-proofing fix, not a currently-triggered
one. Confirmed **not** touched by the currently proposed
`WI-PIPELINE-0041`, which explicitly excludes changing this script's
"existing, narrower persistence approach." No committed output from a
real run was found in-repo, so this looks like a live, untriggered bug
rather than damage already done — but it's the single highest-priority
item in this backlog precisely because a silent failure gives no signal
to prompt anyone to notice it, unlike the two loud failures below.
**Resolved 2026-08-05:** implemented and merged via
[WI-EXPERIMENTS-0046](https://github.com/xenotaur/LCATS/pull/220). Both
correction gaps above were folded into the fix, including a
review-round addendum (Copilot finding on PR #220) that routed
`--story-list` entries through `discovery.find_json_files` too, not just
the directory-scan sample path.

### Non-recursive glob bugs in two experiment scripts — P1, loud but blocking

Re-verified 2026-08-02 (severity corrected: these fail **loud**, not
silently, contrary to how this entry originally read):

- `experiments/02_llm_backend_comparison/run_comparison.py:57` —
  `story_files = sorted(f for f in corpus_dir.iterdir() if f.suffix == ".json")`.
  Under bucket layout, `corpus_dir`'s immediate children are story
  *directories*, not `.json` files, so this now finds **zero** files
  against any real bucket-layout collection — but `run()` (line 56-57)
  explicitly checks `if not story_files:` and exits 1 with
  `"error: no .json files found in {corpus_dir}"`. A real, blocking bug
  (the script is currently unusable against real bucket-layout data, and
  the error message is confusing since files clearly do exist, just as
  subdirectories) — but not a silent one.
- `experiments/02_llm_backend_comparison/smoke_test.py:109` —
  `corpus_dir.glob("*.json")`, the same non-recursive pattern. Verified
  the downstream path: `_actual_sample`'s result feeds into `_run_leg`,
  which calls into `run_comparison.py`'s own `run()` and therefore hits
  the same loud `error: no .json files found` exit — `smoke_test.py`
  correctly reports the leg as `FAILED` and the overall run as
  `Smoke test INCOMPLETE`. Loud, same as above.

**Resolved 2026-08-05:** implemented and merged via
[WI-EXPERIMENTS-0047](https://github.com/xenotaur/LCATS/pull/222). Both
scripts switched to `discovery.iter_collection_story_files`; also fixed
`run_comparison.py`'s per-story progress print and repointed
`smoke_test.py`'s `_RUNS` at the tracked `corpora/` snapshot instead of
the gitignored `lcats/data/`. A Copilot review round further clarified
the error message and made `smoke_test.py`'s sample-count check lazy.

### Whether notebooks/ and experiments/ should be librarized — P3, decision not a fix

Open architecture question: should `notebooks/` and `experiments/`
implementation code move into the installable `lcats` package with unit
test coverage, rather than living as standalone scripts? No decision was
made; explicitly out of scope for `WS-STORY-BUCKET-LAYOUT`. **Next step:**
this is a proposal-shaped question (affects testing strategy and packaging
conventions), not a work item — raise via `/lrh-proposal` if/when someone
wants to press on it.

---

## Other known gaps worth following up on

### Malformed-item guards check each item's type but never the container's, exploding into thousands of bogus errors on a non-list field — P1, resolved

Surfaced 2026-08-04, same re-run (against `mass_quantities/calling_the_empress__smith` or its predecessor in the pipeline - the terminal was mid-scrollback when this was noticed): a single story's discourse extraction produced **1300+ separate "speech_acts[N] is not an object (got str): '<single character>'" errors**, one per character of what was clearly a real, long natural-language string (readable prose about "the Sickness on Earth", "wanted to know the truth", etc.) - not a list of speech-act objects at all.

Root cause: `schema.describe_malformed_item()` (`schema.py:22`) is a well-designed per-*item* guard (skip a malformed array element, record why, don't crash - WI-EVENT-0032's own fix for a prior `AttributeError: 'str' object has no attribute 'get'` bug), but every `build_*()` call site that uses it shares the same pattern:

```python
for i, raw in enumerate(tool_result.get("speech_acts") or []):
```

(`discourse_extractor.py:206`, and the identical shape at `relation_extractor.py:142`, `story_relation_extractor.py:216`, `entity_extractor.py:149,156`, `event_extractor.py:196,219,240,251`, and `hypothesis_extractor.py:154` (the optional stage-8 pass - not exercised by this pilot, which runs with `include_hypotheses=False`, but the same vulnerable pattern nonetheless) - this is systemic across every extractor in the package, not a discourse-specific bug). `or []` only substitutes when the value is falsy (`None`, `""`, missing key) - a **non-empty string** is truthy, so `enumerate("some long string")` iterates character-by-character, and each character correctly fails the `isinstance(raw, dict)` check and gets its own `describe_malformed_item()` call. The guard's own design (skip-and-record, don't crash) works exactly as intended per-item; the gap is that nothing checks whether the *container* itself is a list before iterating it as one.

Compounding consequence: `run_pilot.py:1100`'s `row["exclude_reason"] = "; ".join(extraction_errors)` then joins all 1300+ fragments into one giant string, and `run_pilot.py:1328`'s `print(f"  excluded: {row['exclude_reason']}")` prints it with no length cap - this is what flooded the terminal. Related to, but distinct from, the mid-call-progress-feedback gap above: that one is about silence when something legitimate is slow; this is the opposite failure, an unbounded wall of text from one malformed field.

**Open question, not yet answered:** `DISCOURSE_TOOL_SCHEMA` declares `speech_acts` as `"type": "array"` and goes through `strict_tool_schema()` (`discourse_extractor.py:18`) - `strict: true` is supposed to guarantee schema-valid output via grammar-constrained sampling (see that function's own docstring). A real string value coming back for a `strict: true`-constrained array field is surprising and worth understanding before assuming a quick fix covers it - either this is a genuine (rare, extreme-output-length?) violation of Anthropic's own strict-mode guarantee, or something upstream in our own tool-result handling is misassigning a value to this key. Needs investigation, not just the defensive fix below.

**Resolved 2026-08-09:** scoped via [PR #268](https://github.com/xenotaur/LCATS/pull/268)
and implemented via [PR #274](https://github.com/xenotaur/LCATS/pull/274)
(commit `4a5a3c60`). A new `schema.coerce_list_field()` helper
(mirroring `describe_malformed_item()`'s existing per-item pattern)
centralizes the container-type check across all 12 call sites -
`entity_extractor.py` (2), `event_extractor.py` (4),
`relation_extractor.py` (1), `discourse_extractor.py` (3, not the 1
originally named above - the entry's own line-number citations had
drifted since it was written), `story_relation_extractor.py` (1), and
`hypothesis_extractor.py` (1) - so a present-but-non-list value now
produces exactly one `f"{field} is not an array (got {type(value).__name__})"`
error instead of being iterated character-by-character.
`run_pilot.py`'s printed `exclude_reason` is capped via a new
`_capped_exclude_reason()` helper (truncating with a "...N more errors"
suffix, or "(truncated)" when no sibling error was actually omitted);
the stored/persisted row value itself remains uncapped. A first-push
review round (Codex + Copilot) caught two further real gaps in the
first implementation cut, both fixed before merge: `coerce_list_field()`
originally used `if not value`, which silently passed a falsy-but-present
non-list value (`""`, `0`, `False`, `{}`) with no recorded error -
narrowed to `if value is None`; and `_capped_exclude_reason()`'s
`max(total - shown, 1)` floor fabricated a "...1 more error" claim when
the char-count cutoff fell inside the last joined segment rather than
before a real segment boundary. The open question above (whether
`strict: true` should have prevented a non-array value from reaching
this code) was deliberately left unaddressed, per the WI's own
Non-Goals - this fix handles the failure mode defensively, regardless
of its ultimate cause.

### `pilot_usage.jsonl` doesn't track genre-detect or segmentation cost at all — P2, real cost-visibility gap

Surfaced 2026-08-04 while trying to attribute the completed real run's
$42.80 total cost between the 200-candidate genre-detect scan and the
ERW pipeline itself. `pilot_usage.jsonl` only contains `PassUsage`
records from `run_story`'s ERW-pipeline stages (`surface_feature`,
`entity`, `event_anchor`, `relation`, `discourse`, `story_relation`) -
`build_stratified_sample`'s 200 real `assess_story()` calls, and every
`_segment_story` call (successful or truncated), are never captured
into any usage record at all. This run's usage log shows only 6 distinct
`story_id`s (337,503 input + 296,081 output tokens total) despite 18
stories being sampled and 200 candidates being genre-scanned - meaning
roughly a third of the real spend (genre-detect + segmentation) is
completely invisible in the pilot's own cost-reporting output, the exact
data `README.md`'s "Cost note" and `pilot_usage.jsonl` exist to surface.
This made it materially harder to answer a direct "where did the money
go" question with real data instead of a rough estimate. **Next step:**
thread `PassUsage` recording through `assess_story()`'s call in
`build_stratified_sample` and through `_segment_story`'s call, tagged
the same way (`story_id`/`genre`/`pass_name`), so `pilot_usage.jsonl`
reflects the pilot's *entire* real cost, not just the ERW-pipeline
portion of it.

### Pilot's default parameters optimize for full genre coverage, not minimum-cost validation — P3, decision needed

Surfaced 2026-08-04 by the user during the real (non-dry-run) pilot run
against `corpora/`, after the schema and truncation fixes below still
left the run expensive ($22.06+ and climbing) and hitting repeated
exclusions. `run_pilot.py`'s defaults — `--max-candidates 200` and
`--model` defaulting to `claude-opus-4-8` (a top-tier, expensive model)
— are tuned to guarantee full 5-per-genre stratified coverage using the
best available model, not to do the minimum work needed to validate
that the pipeline runs end to end. This is a real architecture/purpose
mismatch: the whole reason `WI-PIPELINE-0040`/`0041` exist is that a
real run is expensive and was previously unsafe to attempt more than
once: the current defaults still point every real invocation at "get a
complete, high-quality stratified sample" rather than "prove the
pipeline works, cheaply, before committing to a full paid run." No
inexpensive smoke-test path exists between `--dry-run` (zero API cost,
fake backend, meaningless output) and a full real run at these
defaults (real cost, real model, real coverage target). **Next step:**
this is a design-shaped question, not a quick fix — revisit via
`/lrh-proposal` or at minimum a scoped decision: should the pilot gain
a cheap/bounded real-API validation mode (e.g. a smaller, faster model
by default; a much lower `--max-candidates`; explicit opt-in flags to
reach full coverage/quality), separate from the full-coverage run this
corpus's real findings ultimately need?

### Discourse extraction truncated even at the already-raised 16384 ceiling — P1, raise attempted and reverted same day; real cause still unknown

Surfaced 2026-08-04, same run: one story was excluded with
`"discourse extraction failed: ... truncated at the max_tokens limit
(16384) before the tool_use block for 'extract_discourse' finished
generating"` - this is already `_ERW_MAX_TOKENS`'s raised ceiling, not
the un-raised default, and it still wasn't enough. This is more
concerning than the segmentation gap above: simply raising the number
again is a plausible fix, but it could also indicate the discourse
extractor is generating unusually verbose or runaway output for some
segment shapes, which a blind ceiling increase would only mask. **Next
step:** before bumping `_ERW_MAX_TOKENS` further, inspect what this
specific segment's discourse-extraction prompt/response actually looks
like (is the raw output pathologically repetitive or just genuinely
dense?) to decide whether a higher ceiling alone is the right fix, or
whether the discourse extractor's prompt/schema needs its own look.

**Update 2026-08-04 (first):** the completed full run surfaced a second
extractor (`event_anchor`, twice, in romance) hitting the exact same
16384 ceiling - cross-extractor recurrence in one run is stronger
evidence for "some real segments genuinely need more headroom" than for
a discourse-specific runaway-generation bug, so the "investigate before
bumping" caution above was downgraded. `_ERW_MAX_TOKENS` raised from
16384 to 32768.

**Update 2026-08-04 (second) - reverted the same day.** The 32768
raise, applied to a resumed real run, produced a new and more concerning
failure mode: repeated `{'type': 'error', 'error': {'details': None,
'type': 'invalid_request_error', 'message': 'Invalid request data'},
'request_id': '...'}` rejections from Anthropic's API - across multiple
*different* extractor types (event/anchor, relation, entity) on
multiple different stories, and the same run's discourse extraction
still separately truncated even at 32768 on `calling_the_empress__smith`.
This is not a max_tokens-ceiling problem in the way it first looked:
`platform.claude.com`'s current model-overview docs confirm
`claude-opus-4-8`'s synchronous-Messages-API max output is **128k
tokens**, with **no beta header required** below that (the
`output-300k-2026-03-24` beta only applies to the Batch API's separate
300k limit, which this pilot doesn't use) - so 32768 should not be
anywhere near a real ceiling for this model. Checked `_normalize_api_error`
(`llm_extractor.py:246`) to confirm our own code isn't discarding extra
detail Anthropic sent - it isn't; `'details': None` is exactly what the
API itself returned, no more informative detail available from our
side. **Reverted:** `_ERW_MAX_TOKENS` back to 16384 (the one value
confirmed to work repeatedly across this whole session) rather than
spend more real API cost guessing further. **Real root cause still
unknown** - candidate leads for a future investigation: (1) capture the
exact outgoing request body via `ANTHROPIC_LOG=debug` on a reproduced
failure (our own error dict has no more detail to give; Anthropic's raw
debug log might); (2) `claude-opus-4-8` defaults `effort` to `high` -
**correction, verified against Anthropic's Opus 5 migration docs
(`platform.claude.com/docs/en/about-claude/models/whats-new-opus-5`):
`claude-opus-4-8` does NOT have thinking/adaptive-thinking on by default -
"On Claude Opus 4.8, requests run without thinking unless you set
`thinking: {"type": "adaptive"}`"; "thinking on by default" is a Claude
Opus 5 change, not a Opus 4.8 behavior. The earlier "Adaptive thinking:
Yes" table entry for Opus 4.8 (`platform.claude.com`'s model overview
page) is a capability-support column (this model *can* be given
`thinking: {"type": "adaptive"}`), not a default-enabled one - conflating
the two was the error here.** Whether the (real) `effort: high` default
interacts with a large `max_tokens` value plus an unusually long/dense
segment in some request-shape-invalidating way is untested, not
confirmed; (3) this corpus's own already-flagged unusually
dense segments (see the malformed-`speech_acts`-string entry above) may
independently be producing some other request-shape problem that just
happens to correlate with when a large `max_tokens` value is also in
play. Do not attempt raising `_ERW_MAX_TOKENS` above 16384 again until
one of these leads is actually run down.

### `lcats survey` and `lcats promote` disagree on which mojibake findings to flag — P3, decision not a fix

`lcats survey --mode specials` applies the legacy `unicode.DEFAULT_EXCLUDED_CHARS`
list (via `cli.py`'s `run_survey`), which silently lets through some
mojibake characters (e.g. bare `Â`/`Ã`/`â`) that `lcats promote`'s
independent `survey_collection()` (in `promote.py`, using an empty
exclusion set) correctly flags. Confirmed by direct testing, not inference
— `lcats promote --dry-run` is the real release gate and isn't affected,
but a human running `lcats survey` for diagnostics can see zero findings on
a file that genuinely has unrepaired mojibake. Has a nominal home —
`WS-SPECIALS-CLEANUP` (still `status: proposed`, `stage: assessed`) was
meant to revisit this architecture, but no specific WI covers it yet.
**Next step:** likely resolution is making `lcats survey`'s CLI stop
applying `unicode.DEFAULT_EXCLUDED_CHARS` by default (or sharing one
exclusion path between both commands) — scope as a WI under
`WS-SPECIALS-CLEANUP` when that workstream is next picked up.

### `lcats stats` uses the wrong (broad) story-file selector — P1, silent

Surfaced during PR #209's review, confirmed 2026-08-02: `cli.py`'s
`run_stats` calls `discovery.find_corpus_stories` — the broad recursive
JSON finder — rather than the canonical-only selector (`find_json_files`)
that `lcats survey` and `lcats assess` both use. This means `lcats stats`
can silently include sidecar files (`audit.json`, `scenes.json`, etc.) as
if they were stories, inflating or corrupting story-level statistics. Not
caused by the bucket-layout migration itself, but it's exactly the
"wrong tool for the canonical-presence question" pattern that migration's
own design guidance warns against (see
`project_story_bucket_proposal_status` memory). **Resolved 2026-08-07:**
implemented and merged via
[WI-STATS-0049](https://github.com/xenotaur/LCATS/pull/238).
`discovery.find_json_files` gained an opt-in `ignore_dir_names`
parameter (defaulting to a no-op) so `run_stats` can switch to it while
still excluding `cache/` directory contents, matching the prior
`find_corpus_stories(ignore_dir_names=("cache",))` behavior. A review
round caught two real bugs in the first version of the fix (an ignored
child directory could mask a real leaf story bucket; `ignore_dir_names`
wasn't safe to pass as a one-shot iterable) — both fixed in the same
PR.

### ~~`assess_story`'s error-path title fallback uses the stem-collision pattern~~ — **fixed, [PR #242](https://github.com/xenotaur/LCATS/pull/242), merged 2026-08-07** — P3, cosmetic

Surfaced 2026-08-02 while scoping a Batch-3 follow-up, then verified
directly against the code before concluding anything (an initial
misreading of `assess.assess_story` looked like a much bigger bug before
reading the whole function): `lcats/src/lcats/analysis/corpus/assess.py`'s
`assess_story` pre-initializes `title = file_path.stem` before calling
`run_preflight(file_path)` (which correctly uses the fixed
`infer_story_title`). In the success path `title` is immediately
reassigned from `run_preflight`'s return, so **the real `lcats assess`
CLI is not broadly broken** — titles are correct in normal operation.
The only surviving gap is the `except Exception` fallback: if
`run_preflight` raises (a genuine file-read/parse error unrelated to
identity), the resulting error `AssessmentResult`'s `title` field falls
back to the stale `file_path.stem` value — literally `"story"` for a
bucket file — instead of the real story slug, making it harder to tell
from the output alone which story actually failed. Cosmetic, not a data
or correctness bug (the record already carries `file_path` and
`error`). **Resolved 2026-08-07:** implemented and merged via
[WI-ASSESS-0050](https://github.com/xenotaur/LCATS/pull/242). The
fallback now initializes from `file_path.parent.name`, matching the
identity convention used everywhere else; a review round found and
fixed a bare-relative-path edge case (empty lexical parent name) and a
follow-on robustness gap (an unguarded `resolve()` call that could have
crashed the fallback itself) — see the new backlog entry above on
unguarded `.resolve()` calls elsewhere in the codebase.

### ~~`VALID_GENRES` still has 4 genres, not the reconciled 8~~ — **fixed, [PR #224](https://github.com/xenotaur/LCATS/pull/224), merged 2026-08-06** — both related gaps now have work items, in progress

Resolved: `VALID_GENRES` now has all 8 reconciled genres (science fiction,
horror, humor, western, romance, mystery, fantasy, adventure), via
`WI-ASSESS-0031` (`status: resolved`). The two related gaps flagged here
now both have work items, tooling landed, real cost estimates measured -
neither is fully executed yet:

- **Current-classifier full-corpus survey** under the 8-genre scheme —
  `WI-ASSESS-0051` (`status: proposed`). Census tooling
  (`experiments/04_genre_census/run_census.py`) landed, PR #251. A real
  `--sample-size 20`
  run measured $4.66 for 20 stories, extrapolating to ~$435/~4.2 hours for
  the full corpus (`experiments/04_genre_census/results/`, PR #292) - the
  `--full` run itself is deliberately deferred pending a cost-free
  local-model (`gpt-oss:20b`) pilot, `WI-LLM-0066` (`status: proposed`,
  in progress in a separate session as of 2026-08-13), rather than run
  immediately. Along the way, a real data-quality defect was found and
  fixed: `WI-LLM-0058` (`status: resolved`) - `ASSESSMENT_TOOL`'s
  `secondary_genre` field was corrupted (leaked tool-call-syntax
  fragments) in 39% of calls across two independent real runs;
  `detected_genre` itself was unaffected in both.
- **Re-scoping `WI-EVENT-0030`'s stratified pilot** for 8 genres instead of
  4 — `WI-EVENT-0030`'s `depends_on` now lists `WI-ASSESS-0051` (PR #246,
  merged 2026-08-12), wiring the dependency at the frontmatter level so an
  executor can't miss it. The actual content re-scope (Scope/Summary/
  Required Changes/Acceptance Criteria) remains deliberately deferred -
  those sections still describe the original 4-genre pilot until
  `WI-ASSESS-0051` produces real per-genre counts to re-scope against.

See `project/design/event-role-world-genre-target-reconciliation.md`'s
Gap 1/2/3 sections for the full picture.

### `lrh request review-response` (and the skills that call it) don't reliably surface every reviewer finding — P1, real and recurring

Surfaced during `WI-ASSESS-0031`'s 5-round review-response loop on
[PR #224](https://github.com/xenotaur/LCATS/pull/224) (2026-08-06).
`chatgpt-codex-connector` posted its actual findings via two different,
inconsistent surfaces across the PR's rounds — sometimes a formal GitHub
`reviews`/`reviewThreads` entry (queryable via the GraphQL API this
tooling already uses), sometimes a plain PR *issue comment*
(`gh api repos/.../issues/<n>/comments`, a surface `lrh request
review_response` does not appear to check at all based on this session's
observed behavior) — even for the same kind of message (a clean-pass
confirmation landed as an issue comment in three separate rounds of this
same PR). Separately, the reviewer's formal review *body* text was
boilerplate-only in every round that had real findings; the actual
findings lived exclusively in separate `reviewThreads` entries not
reflected in the review body summary at all. Relying on `reviews`/review
*body* text alone — the natural place to look first — would have missed
real findings, or missed a clean pass and kept waiting unnecessarily,
several times in a single PR.

**Next step:** audit `lrh request review-response`'s actual data source(s)
against both gaps — (1) does it check PR issue comments in addition to
`reviewThreads`/formal reviews, and (2) does it ever surface review body
*text* as if it were the finding list, rather than always resolving to
the actual `reviewThreads` entries regardless of what the body says. Fix
whichever gap(s) are confirmed, and propagate the fix to any skill that
wraps this command (`/lrh-review-response`, `/lrh-confirm-fixes`,
`/lrh-land`'s inlined Steps 4-5) rather than only patching around it in
one call site.

~~### ERW pipeline audit's Category E (cost/checkpointing/local-model options) never promoted to a proposal~~ — **promoted and delivered, [`PROP-LCATS-PIPELINE-CHECKPOINTING`](proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md) (resolved via `WS-PIPELINE-CHECKPOINTING`) and [`PROP-LCATS-PILOT-COST-SUSTAINABILITY`](proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md) (adopted 2026-08-06, governed by `WS-PILOT-COST-SUSTAINABILITY`)**

`project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`'s
Category E — cost/logging/checkpointing/local-model options, plus a
corpus-wide reconsideration of workflow-orchestration options — was
deliberately left unscoped when the audit's other categories became
`WI-EVENT-0032`/`WI-EVENT-0033`. A follow-on vetting pass (of
`run_pilot.py`, 2026-07-29) found this was a real blocker: a minimal real
Event-Role-World pilot run cost ~98-479 LLM calls with no resume/checkpoint
capability and no test coverage on the cost-dominant functions — not safe
to run again without it. Resolved in two parts: the
crash/interrupt-recovery half became `PROP-LCATS-PIPELINE-CHECKPOINTING`
(implemented, `WS-PIPELINE-CHECKPOINTING` closed); the cost-sustainability
half (targeted test harness, prompt-caching/Batch-API/model-tiering
evaluation gates) became `PROP-LCATS-PILOT-COST-SUSTAINABILITY`, now
governed by `WS-PILOT-COST-SUSTAINABILITY` (proposed, not yet started).

~~### `chunk_story` hangs on `max_tokens <= 0`~~ — **fixed, [PR #296](https://github.com/xenotaur/LCATS/pull/296)**

Resolved: found by a substitute self-review pass on
[PR #216](https://github.com/xenotaur/LCATS/pull/216) (⚡ Bolt: Optimize
`chunk_story` character offset calculation) — `chunk_story(text,
max_tokens=0, overlap_tokens=0, ...)` (or any `max_tokens <= 0`) never
terminated, because `step = max_tokens - overlap_tokens` (or
`max_tokens` when `overlap_tokens == 0`) was non-positive, so
`current_token` never advanced past the `while current_token <
len(tokens)` loop condition. PR #216 added a guard for
`overlap_tokens >= max_tokens` but that only covered the overlap-driven
case. Fixed via a direct `max_tokens <= 0` guard (raises `ValueError`)
plus regression tests in `lcats/src/lcats/chunking.py`'s `chunk_story`.
The same PR also added a guard rejecting negative `overlap_tokens`
(found by Copilot review on PR #296 itself: a negative value made
`step = max_tokens - overlap_tokens` exceed `max_tokens`, silently
skipping a range of tokens between chunks) — together, the three
guards on `max_tokens`/`overlap_tokens` provably close every
non-positive-`step` case.

~~### Pre-existing masking bug in `discovery.py`'s recursive selector~~ — **fixed, [PR #208](https://github.com/xenotaur/LCATS/pull/208), merged 2026-08-02**

Resolved: `_walk_canonical_story_files` no longer mistakes a stray flat
`story.json` at a collection root for a leaf story bucket. Fixed via a new
`_is_leaf_story_bucket` helper that breaks the ambiguity with a domain
rule — a directory is only a real leaf bucket if none of its own
subdirectories are themselves buckets (genuine story buckets never nest
inside each other). No work item was created for this fix; it landed as
an ad hoc PR with its own backfilled execution records. Left here as a
record of resolution rather than deleted outright, since the PR itself
carries no pointer back to this backlog entry.

---

## Concurrent sessions computing "global max+1" independently produced duplicate WI numbers — P2, loud but low-frequency

Surfaced 2026-08-07 while starting `/lrh-execute WI-PILOT-0051`. The
project's WI-numbering convention treats the number as a single pool
shared across all `WI-<PREFIX>-` namespaces (next number = global
max+1 across every prefix, per prior session guidance) — but nothing
enforces this except each session independently `grep`-ing the highest
existing number before minting a new one. With several parallel
sessions creating work items around the same window (2026-08-05
through 2026-08-07), at least four distinct work items landed on `main`
all numbered `0051`: `WI-LLM-0051` ("Investigate Ollama's forced
tool_choice reliability", 2026-08-05, still `proposed`),
`WI-ANNOTATE-0051` ("Build lcats annotate command with checkpoint-safe
sidecar writes", 2026-08-06, `resolved`), `WI-ASSESS-0051` ("Run
current-classifier full-corpus genre survey (Gap 2)", 2026-08-07, PR
#235, still `proposed`), and `WI-PILOT-0051` ("Add --story/--story-list
targeted test harness to run_pilot.py", 2026-08-07, PR #237, still
`proposed`). No technical collision — each full ID string
(`WI-<PREFIX>-0051`) is unique, filenames don't clash, and `lrh
validate` reports 0 errors — but it defeats the numbering scheme's own
intent of an unambiguous shared pool, and makes "WI-0051" alone
(without its prefix) ambiguous across at least 4 different work items.
**Next step:** either (a) a lightweight coordination mechanism (a
committed "next WI number" counter file, updated atomically as part of
each `/lrh-work-item` PR, so two concurrent sessions racing to read it
would at least surface as a merge conflict instead of silently both
succeeding), or (b) drop the global-pool convention in favor of
per-prefix numbering (each `WI-<PREFIX>-*` sequence numbered
independently), which sidesteps the race entirely at the cost of losing
"the WI number alone tells you creation order" as a property. Does not
block any of the four affected work items individually; no renaming
proposed here since at least one (`WI-ANNOTATE-0051`) is already
`resolved` and touching it would rewrite settled history.

---

## Check back on `gutenbergpy` upstream release status for `WI-RELEASE-0037` — P3, decision blocked on external response

Noted 2026-07-29, while formalizing `WS-RELEASE`/`PROP-LCATS-PYPI-RELEASE-READINESS`.
`WI-RELEASE-0037` (resolve the `gutenbergpy` `git+https` direct-VCS-dependency
PyPI-upload blocker) is gated on an external maintainer response: the fixes
LCATS needs (alias tables, title-index correction) are already merged
upstream into `raduangelescu/gutenbergpy:master`
([PR #25](https://github.com/raduangelescu/gutenbergpy/pull/25),
[PR #26](https://github.com/raduangelescu/gutenbergpy/pull/26)), but the
last published PyPI release is still `0.3.5` (2023-03-27), predating that
merge. The user contacted the maintainer directly to ask about their
release schedule; no response yet as of this entry.
`raduangelescu/gutenbergpy:master`'s own `setup.cfg` already shows an
unreleased `version = 0.3.6` bump — a mildly encouraging, non-committal
signal a release may be forthcoming, not confirmation of one.

`WI-RELEASE-0039` (the pre-launch verification gate,
`depends_on: WI-RELEASE-0037`) is the standing mechanism that re-checks
this status immediately before any real PyPI publish attempt — but that
only fires once a publish is imminent, not on any regular cadence in the
meantime. This entry exists so periodic check-ins on the maintainer
response aren't lost between now and whenever a publish attempt actually
happens.

**Next step:** periodically check
[pypi.org/project/gutenbergpy](https://pypi.org/project/gutenbergpy/) for
a release newer than `0.3.5`, and check in on the maintainer conversation
status. If a new release lands containing the needed fixes, "wait on
upstream" becomes viable for `WI-RELEASE-0037` even if a vendor/fork path
was already chosen or in progress — surface that to the user rather than
proceeding on stale assumptions. Remove this entry once `WI-RELEASE-0037`
resolves (its own resolution note should record the outcome either way).

**Suggested kickoff prompt** (paste into a fresh session once the
maintainer responds, or periodically to check in without a response):

```
Check on the gutenbergpy dependency blocker for WI-RELEASE-0037
(lcats/project/work_items/proposed/WI-RELEASE-0037.md), per the backlog
entry "Check back on gutenbergpy upstream release status for
WI-RELEASE-0037" in lcats/project/design/backlog.md.

1. Check https://pypi.org/project/gutenbergpy/ for a release newer than
   0.3.5 (2023-03-27). Also check whether the upstream maintainer
   (raduangelescu/gutenbergpy) has responded to the release-schedule
   question, or cut a release incorporating
   https://github.com/raduangelescu/gutenbergpy/pull/25 and
   https://github.com/raduangelescu/gutenbergpy/pull/26.

2. If a qualifying release now exists: update WI-RELEASE-0037's Problem/
   Context with the finding, choose "wait on upstream" as the resolution
   path if still appropriate, and implement it -- update
   lcats/pyproject.toml:26 and lcats/environment.yml's matching pin from
   the git+https direct-VCS reference to the new PyPI version, following
   the WI's own acceptance criteria.

3. If no qualifying release exists yet and the maintainer hasn't
   responded: report that back plainly (don't assume silence means
   proceed) and ask whether to keep waiting or proceed with the
   vendor-fork path WI-RELEASE-0037 already scopes as Required Change 3
   -- note that file list is explicitly provisional and needs tracing
   gutenbergpy's real import closure at implementation time, not
   trusting the list as-is.

4. Either way, drive WI-RELEASE-0037 through to a PR and, once merged,
   consider whether WI-RELEASE-0039 (the pre-launch verification gate,
   lcats/project/work_items/proposed/WI-RELEASE-0039.md) is ready to run
   -- only if a real PyPI publish is actually imminent, not as a
   formality right after WI-RELEASE-0037 resolves.

Remove this backlog entry once WI-RELEASE-0037 resolves.
```

**Related:** `WS-RELEASE` (`project/workstreams/proposed/WS-RELEASE.md`);
`WI-RELEASE-0037`, `WI-RELEASE-0039`; `PROP-LCATS-PYPI-RELEASE-READINESS`
(`project/design/proposals/proposed/lcats-pypi-release-readiness/00_proposal.md`);
upstream PRs
[raduangelescu/gutenbergpy#25](https://github.com/raduangelescu/gutenbergpy/pull/25),
[#26](https://github.com/raduangelescu/gutenbergpy/pull/26).

---

### `nbstripout` pre-commit hook was added unverified — P1, scoped as WI-INFRA-0012

Surfaced 2026-08-18 closing out PR #315 (secrets-hygiene incident
response). A real, live OpenAI key was found leaked into `main` via saved
notebook cell output (`lcats/notebooks/04_rag_expt.ipynb`), followed by a
second, independent live-key leak found the same way in an Azure OpenAI
notebook (`lcats/notebooks/05_prog_llm_csharp.ipynb`) while empirically
testing the scan tooling's provider coverage. PR #315's root-cause fix
added an `nbstripout` pre-commit hook (`.pre-commit-config.yaml`), scoped
to `lcats/notebooks/*.ipynb`, as the backstop meant to prevent a
repeat — but the session that authored it did not have `pre-commit`
installed, so
the hook was only validated for YAML syntax, never actually run. An
unverified backstop is not a backstop: if it's silently misconfigured
(wrong `files:` pattern, hook rev pin issue, or simply never installed by
a contributor), the next raw-key-in-output leak recurs exactly as before
while everyone believes it's covered.

**Next step:** scoped as `WI-INFRA-0012`
(`project/work_items/proposed/WI-INFRA-0012.md`) - install `pre-commit`,
run it for real against `lcats/notebooks/*.ipynb`, confirm with a live
test (commit a notebook with deliberately-added cell output and check the
hook actually strips it), fix the config if it doesn't work, and replace
`lcats/docs/how-to/secrets-hygiene.md`'s unverified caveat with the real
outcome. Remove this backlog entry once `WI-INFRA-0012` resolves.

**Related:** `lcats/docs/how-to/secrets-hygiene.md`;
`lcats/experimental/secrets_hygiene/` (PR #315); `.gitleaks.toml`.
