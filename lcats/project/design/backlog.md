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

### Malformed-item guards check each item's type but never the container's, exploding into thousands of bogus errors on a non-list field — P1, real and now confirmed

Surfaced 2026-08-04, same re-run (against `mass_quantities/calling_the_empress__smith` or its predecessor in the pipeline - the terminal was mid-scrollback when this was noticed): a single story's discourse extraction produced **1300+ separate "speech_acts[N] is not an object (got str): '<single character>'" errors**, one per character of what was clearly a real, long natural-language string (readable prose about "the Sickness on Earth", "wanted to know the truth", etc.) - not a list of speech-act objects at all.

Root cause: `schema.describe_malformed_item()` (`schema.py:22`) is a well-designed per-*item* guard (skip a malformed array element, record why, don't crash - WI-EVENT-0032's own fix for a prior `AttributeError: 'str' object has no attribute 'get'` bug), but every `build_*()` call site that uses it shares the same pattern:

```python
for i, raw in enumerate(tool_result.get("speech_acts") or []):
```

(`discourse_extractor.py:206`, and the identical shape at `relation_extractor.py:142`, `story_relation_extractor.py:216`, `entity_extractor.py:149,156`, `event_extractor.py:196,219,240,251`, and `hypothesis_extractor.py:154` (the optional stage-8 pass - not exercised by this pilot, which runs with `include_hypotheses=False`, but the same vulnerable pattern nonetheless) - this is systemic across every extractor in the package, not a discourse-specific bug). `or []` only substitutes when the value is falsy (`None`, `""`, missing key) - a **non-empty string** is truthy, so `enumerate("some long string")` iterates character-by-character, and each character correctly fails the `isinstance(raw, dict)` check and gets its own `describe_malformed_item()` call. The guard's own design (skip-and-record, don't crash) works exactly as intended per-item; the gap is that nothing checks whether the *container* itself is a list before iterating it as one.

Compounding consequence: `run_pilot.py:1100`'s `row["exclude_reason"] = "; ".join(extraction_errors)` then joins all 1300+ fragments into one giant string, and `run_pilot.py:1328`'s `print(f"  excluded: {row['exclude_reason']}")` prints it with no length cap - this is what flooded the terminal. Related to, but distinct from, the mid-call-progress-feedback gap above: that one is about silence when something legitimate is slow; this is the opposite failure, an unbounded wall of text from one malformed field.

**Open question, not yet answered:** `DISCOURSE_TOOL_SCHEMA` declares `speech_acts` as `"type": "array"` and goes through `strict_tool_schema()` (`discourse_extractor.py:18`) - `strict: true` is supposed to guarantee schema-valid output via grammar-constrained sampling (see that function's own docstring). A real string value coming back for a `strict: true`-constrained array field is surprising and worth understanding before assuming a quick fix covers it - either this is a genuine (rare, extreme-output-length?) violation of Anthropic's own strict-mode guarantee, or something upstream in our own tool-result handling is misassigning a value to this key. Needs investigation, not just the defensive fix below.

**Next step (defensive fix, addressable regardless of the above):** add a container-type check before each of these iteration sites - if `tool_result.get(field)` is present but not a list, emit **one** clear error (e.g. `f"{field} is not an array (got {type(value).__name__})"`) instead of iterating it character-by-character. Apply uniformly across all `build_*()` call sites listed above, not just discourse. Separately, cap `run_pilot.py:1328`'s printed `exclude_reason` length (e.g. truncate with a "...N more errors" suffix) so one malformed field can't flood the console regardless of how it happened.

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

### ~~`VALID_GENRES` still has 4 genres, not the reconciled 8~~ — **fixed, [PR #224](https://github.com/xenotaur/LCATS/pull/224), merged 2026-08-06** — two related gaps remain, P3, needs cost estimate first

Resolved: `VALID_GENRES` now has all 8 reconciled genres (science fiction,
horror, humor, western, romance, mystery, fantasy, adventure), via
`WI-ASSESS-0031` (`status: resolved`). Two related gaps from the same
reconciliation genuinely still have no work item:

- **Current-classifier full-corpus survey** under the 8-genre scheme —
  needed before sizing any stratified annotation pilot; do not reuse the
  2025-10 `experiments/01_classify_corpora` counts, they're a different,
  older classifier's output.
- **Re-scoping `WI-EVENT-0030`'s stratified pilot** for 8 genres instead of
  4 — depends on both `WI-ASSESS-0031` and the corpus survey above.

Both carry real API cost and should get cost estimates before being scoped
as work items, per `project/design/event-role-world-genre-target-reconciliation.md`'s
own recommendation.

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
