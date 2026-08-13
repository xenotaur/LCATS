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
deliberately left for a dedicated follow-up. **Next step:** scope a small WI
to update both notebooks' path construction to the bucket layout
(`<collection>/<story>/story.json`).

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
**Next step:** in progress — see
[WI-EXPERIMENTS-0046](https://github.com/xenotaur/LCATS/pull/212)
(work-item creation PR, not yet implemented).

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

**Next step:** one small WI covering both (same root-cause bug shape,
`smoke_test.py` exists specifically to exercise `run_comparison.py`, so
they're naturally coupled) — switch both to a recursive selector, ideally
reusing `discovery.find_json_files` rather than re-implementing traversal.

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
`project_story_bucket_proposal_status` memory). **Next step:** switch
`run_stats`'s file discovery to `discovery.find_json_files`, matching
`survey`/`assess`, and add a regression test asserting sidecar files are
excluded from stats output.

### `assess_story`'s error-path title fallback uses the stem-collision pattern — P3, cosmetic

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
`error`). **Next step:** initialize the fallback `title` from
`file_path.parent.name` instead of `file_path.stem`, matching the
identity convention used everywhere else.

### `VALID_GENRES` still has 4 genres, not the reconciled 8 — P3, needs cost estimate first

`lcats/src/lcats/analysis/corpus/assess.py`'s `VALID_GENRES` is
`("science fiction", "horror", "western", "romance")` (confirmed current as
of 2026-08-02) — the Worldcon 2026 paper's actual target is 8: science
fiction, horror, humor, western, romance, mystery, fantasy, adventure. This
gap already has a work item, `WI-ASSESS-0031` (`status: proposed`, not yet
implemented) — not a backlog item on its own, listed here only as a
pointer. Two related gaps from the same reconciliation genuinely have no
work item yet:

- **Current-classifier full-corpus survey** under the 8-genre scheme —
  needed before sizing any stratified annotation pilot; do not reuse the
  2025-10 `experiments/01_classify_corpora` counts, they're a different,
  older classifier's output.
- **Re-scoping `WI-EVENT-0030`'s stratified pilot** for 8 genres instead of
  4 — depends on both `WI-ASSESS-0031` and the corpus survey above.

Both carry real API cost and should get cost estimates before being scoped
as work items, per `project/design/event-role-world-genre-target-reconciliation.md`'s
own recommendation.

### ERW pipeline audit's Category E (cost/checkpointing/local-model options) never promoted to a proposal — P3, decision not a fix

`project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`'s
Category E — cost/logging/checkpointing/local-model options, plus a
corpus-wide reconsideration of workflow-orchestration options — was
deliberately left unscoped when the audit's other categories became
`WI-EVENT-0032`/`WI-EVENT-0033`. It still lives only as prose inside the
audit doc. A follow-on vetting pass (of `run_pilot.py`, 2026-07-29) found
this is now a real blocker: a minimal real Event-Role-World pilot run costs
~98-479 LLM calls with no resume/checkpoint capability and no test coverage
on the cost-dominant functions — not safe to run again without it. **Next
step:** promote Category E to a real `/lrh-proposal`, incorporating the
vetting pass's 3 additional gaps (a bounded small-scale trial, call-count
estimation, rate-limit/retry classification) alongside the audit's original
scope.

### `chunk_story` hangs on `max_tokens <= 0` — P2, pre-existing, out of scope of PR #216

Found by a substitute self-review pass on [PR #216](https://github.com/xenotaur/LCATS/pull/216)
(⚡ Bolt: Optimize `chunk_story` character offset calculation) and
independently reproduced: `chunk_story(text, max_tokens=0, overlap_tokens=0, ...)`
(or any `max_tokens <= 0`) never terminates, because
`step = max_tokens - overlap_tokens` (or `max_tokens` when
`overlap_tokens == 0`) is non-positive, so `current_token` never advances
past the `while current_token < len(tokens)` loop condition. PR #216 added
a guard for `overlap_tokens >= max_tokens` (per a Copilot review comment)
but that only covers the overlap-driven case, not `max_tokens <= 0` with
no overlap. This bug predates PR #216 and is unrelated to the O(N²) issue
that PR set out to fix — neither review bot flagged it. **Next step:** add
a `max_tokens <= 0` guard (raise `ValueError`, mirroring the existing
`overlap_tokens` guard) plus a regression test, either as a small ad hoc
fix or a thin work item — `lcats/src/lcats/chunking.py`'s `chunk_story`.

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
