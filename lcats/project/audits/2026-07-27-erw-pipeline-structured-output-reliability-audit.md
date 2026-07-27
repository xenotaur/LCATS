# Event-Role-World pipeline structured-output reliability audit — LCATS

- Prompt ID used: `PROMPT(AD_HOC:ERW_PIPELINE_STRUCTURED_OUTPUT_RELIABILITY_AUDIT)[2026-07-27T12:41:56-04:00]`
- Audit date: 2026-07-27
- Scope: every LLM-structured-output call site reachable from WI-EVENT-0030's
  pilot run (`experiments/03_cross_segment_relation_pilot/run_pilot.py`),
  looked at broadly rather than narrowly — triggered by two real crashes hit
  during live dogfooding (PR #167, PR #168), but this pass goes past just
  those two sites to the whole surface. Extended (Category E) to cover a
  distinct, non-bug concern raised in the same conversation: the pilot has
  spent roughly $15 of its ~$50 budget and this burn rate is not sustainable
  for routine dogfooding, let alone a full-corpus run - covers model-call
  logging/budgeting, restartable/checkpointed runs, and cheaper/local model
  options.
- Status: **finding only, no fix yet**. Written to capture and ground the
  issues while WI-EVENT-0030's real run (currently in progress with the
  default Opus model, after switching off Haiku) finishes, per user
  direction: revisit this file once that run completes, discuss, and only
  then spin up the actual work item(s)/workstream/design proposal - not
  going through PR review/confirm/merge for this capture step since the
  work is still in flight.
- **Update 2026-07-27**: that Opus run has since completed with a fatal,
  uncaught crash (see "Update 2026-07-27" under Category B below) after
  spending roughly the pilot's full ~$50 budget with no usable results.
  User's determination: close this pilot run out as a failed dogfood
  attempt and conduct a postmortem before any re-run - this file now also
  serves as that postmortem's grounding material.
- Not yet acted on: WI-EVENT-0030 has `forbidden_actions:
  modify_event_role_world_extractor`, which blocks Categories A/B/D below
  (anything inside `lcats/lcats/analysis/event_role_world/`) from being
  fixed inside that work item. Category C's `scene_analysis.py`/
  `story_analysis.py` sites are outside that constraint, but were also left
  unfixed pending this broader look, per user request to scope a properly
  unconstrained work item/workstream instead of another caller-side
  workaround.

## 1. Summary

Two real crashes during WI-EVENT-0030 dogfooding (`ValueError` on non-JSON
model output in segmentation, PR #167; `AttributeError` on a malformed
tool-result array item in `relation_extractor.build_relations`, PR #168)
turned out to be instances of two broader, systemic gaps rather than
one-off bugs:

1. None of the LLM structured-output tool schemas in this codebase set
   Anthropic's `strict: true` (which requires `additionalProperties: false`
   on every object) - so none of them get the schema-conformance guarantee
   Anthropic's own docs describe as the actual fix for exactly this class
   of failure.
2. Three extractors use no tool schema at all (fully unconstrained
   `json_object`-mode JSON-in-text), the least reliable output mode - one
   of which (`scene_analysis.make_segment_extractor`) is the confirmed,
   live cause of the pilot's 65% segmentation exclusion rate with a cheaper
   model.
3. Every one of the six Event-Role-World tool-schema extractors shares the
   identical unguarded-array-item pattern that produced PR #168's crash -
   only one has actually crashed so far, but the same latent risk exists in
   eleven call sites across six files.
4. `processor.py` (blocked from editing by this work item) has two related
   gaps of its own: a hardcoded model with no override, and structured API
   error information (`should_abort_batch`/`category`/`can_retry`)
   discarded into a plain string before it reaches any caller.

PR #166 and #168 fixed their respective issues via runtime overrides local
to `run_pilot.py` (the only file WI-EVENT-0030 permits editing for
ERW-adjacent behavior) - Category A/D-style gaps that remain unfixed at
the source. PR #167 is different in kind: it fixed the segmentation
JSON-parsing crash at the actual source, in the shared
`lcats/analysis/llm_extractor.py` parser (commit `abf8282`, widening a
bare `except json.JSONDecodeError` to `except ValueError`, with a
regression test) - not a caller-local workaround. That crash class is
genuinely fixed for every caller, not just `run_pilot.py`; this audit's
Category C findings are about a *different* gap (no `tool_schema` at all
for those three extractors), not a reopening of what PR #167 already
closed. This audit is the enumeration of what PR #166's and #168's
overrides did *not* fix at the source, for scoping as real work once the
current run finishes.

## 2. Scope and source material

Reviewed directly, this session, via `git show origin/main:<path>`:

- `lcats/lcats/analysis/event_role_world/entity_extractor.py`
- `lcats/lcats/analysis/event_role_world/event_extractor.py`
- `lcats/lcats/analysis/event_role_world/relation_extractor.py`
- `lcats/lcats/analysis/event_role_world/discourse_extractor.py`
- `lcats/lcats/analysis/event_role_world/story_relation_extractor.py`
- `lcats/lcats/analysis/event_role_world/hypothesis_extractor.py`
- `lcats/lcats/analysis/event_role_world/processor.py`
- `lcats/lcats/analysis/llm_extractor.py`
- `lcats/lcats/analysis/scene_analysis.py`
- `lcats/lcats/analysis/story_analysis.py`
- `lcats/lcats/analysis/story_processors.py`
- `lcats/lcats/analysis/text_segmenter.py`
- `lcats/lcats/analysis/corpus/assess.py`
- `experiments/03_cross_segment_relation_pilot/run_pilot.py`

Also grounded in Anthropic's own documentation (fetched live this session):
`platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use` and
`platform.claude.com/docs/en/build-with-claude/structured-outputs`.

Governing proposal: `lcats/project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md`
- explicitly separates "scene/sequel extraction" (a Non-Goal to reimplement)
  from "the Event-Role-World extractor," and its own "Implementation
  prerequisites" section already flags that "the current scene/sequel
  prompts'" `json_object` mode is the weaker pattern the ERW stages were
  specifically designed to replace via `tool=` - i.e. this gap in
  `scene_analysis.py` was a known, accepted limitation at proposal time,
  not an oversight introduced later.

## 3. Findings

### Category A - tool schemas missing `strict: true` / `additionalProperties: false`

| File:line | Schema | Inside `event_role_world/`? |
|---|---|---|
| `entity_extractor.py:15` | `ENTITY_TOOL_SCHEMA` | yes |
| `event_extractor.py:16` | `EVENT_TOOL_SCHEMA` | yes |
| `relation_extractor.py:15` | `RELATION_TOOL_SCHEMA` | yes |
| `discourse_extractor.py:17` | `DISCOURSE_TOOL_SCHEMA` | yes |
| `story_relation_extractor.py:31` | `STORY_RELATION_TOOL_SCHEMA` | yes |
| `hypothesis_extractor.py:15` | `HYPOTHESIS_TOOL_SCHEMA` | yes (unused by this pilot - `include_hypotheses=False` - but shared production code) |
| `lcats/lcats/analysis/corpus/assess.py:31` | `ASSESSMENT_TOOL` | **no** - this is the genre-detection tool used by this pilot's own Step 3/4 scan, entirely outside the forbidden path |

Per Anthropic's Strict tool use docs: *"Without strict mode, Claude might
return incompatible types ... or omit required fields, breaking your
functions and causing runtime errors."* None of the seven schemas above set
`strict: true`, and none set the `additionalProperties: false` it
additionally requires on every object (top-level and nested inside array
items) per the JSON Schema limitations docs.

`run_pilot.py`'s `_strict_tool_schema()`/`_close_schema_objects()`
(added in PR #168, hardened further in its review round) already deep-copy
and patch the five ERW schemas that this pilot's `_build_erw_extractors()`
constructs, at runtime, gated to `--backend anthropic` only. This does
**not** reach `hypothesis_extractor.py` (never built by this pilot) or
`corpus/assess.py`'s `ASSESSMENT_TOOL` (built via a separate code path,
`assess_story()`, not through `_build_erw_extractors()` at all).

### Category B - unguarded array-item type assumptions (the exact crash class hit live in PR #168)

Every one of the six Event-Role-World extractors shares the identical
pattern - iterating a tool-result array and calling `.get(...)` on each
item with no `isinstance(item, dict)` guard:

- `entity_extractor.py:142` (`entities`), `:144` (`mentions`) - **this site
  also crashed live**, see "Update 2026-07-27" below
- `event_extractor.py:185` (`temporal_anchors`), `:203` (`spatial_anchors`), `:219` (`events`), `:225` (`semantic_roles`)
- `relation_extractor.py:131` (`relations`) - **this is the site that first crashed** (`AttributeError: 'str' object has no attribute 'get'`, fixed for now only via PR #168's runtime strict-schema override, not at the source)
- `discourse_extractor.py:196` (`speech_acts`), `:213` (`explanations`), `:232` (`sf_tags`)
- `story_relation_extractor.py:205` (`relations`)
- `hypothesis_extractor.py:146` (`hypotheses`)

Eleven sites total. Strict mode (Category A) reduces the odds any of these
fire, but does not make the code defensive.

**Correction (review, PR #169):** an `isinstance` check alone is not a
complete fix if it merely skips the malformed item and continues -
`processor.process_segment()` (`lcats/analysis/event_role_world/processor.py`)
only records an extraction error when the extractor result reports one, so
silently dropping a malformed entity/event/relation would make that
segment look like a *successful* partial extraction rather than a failed
one, biasing the pilot's density figures exactly the way WI-EVENT-0030's
own acceptance criteria warn against ("stories whose run produced any
extraction_errors are excluded ... not silently counted as zero/partial").
The correct remedy at each of the eleven sites is to detect the malformed
item, preserve the raw payload for diagnosis, and explicitly surface an
extraction error for that segment/story (so it is excluded and reported,
not silently treated as clean) - not just guard-and-skip.

#### Update 2026-07-27: a second, later real run crashed at `entity_extractor.py:144`, with strict mode confirmed genuinely active

A subsequent real run (Opus, after the Haiku-vs-Opus model switch) crashed
at a *different* Category B site than PR #168 fixed:
`entity_extractor.py:144` (`raw_entity.get("mentions")`), same
`AttributeError: 'str' object has no attribute 'get'`. This closed out the
pilot's ~$50 budget with no usable results and prompted a postmortem.

Initial hypothesis was that this run's checkout predated PR #168's merge
(`837761e7`) - i.e. the strict-mode fix simply wasn't active. **This was
checked directly against the run's own `ANTHROPIC_LOG=debug` output
(`/tmp/pilot_debug.log`) and disproven:**

- `grep -o "'strict': True" /tmp/pilot_debug.log | wc -l` -> 53
- `grep -c "'additionalProperties': False" /tmp/pilot_debug.log` -> 53
- The specific request that crashed (content matching the "Mryna"/Rythar/
  Guardian Wheel story, i.e. `the_guardians__cox.json`) carries
  `'strict': True` and `'additionalProperties': False` at both the outer
  `entities` level and the nested `mentions` level - confirmed by locating
  that exact request in the log and inspecting its `tools` payload
  directly. The corresponding response was `200 OK`, not a schema-rejection
  error.

Per Anthropic's Strict tool use docs, this should not be possible: *"Tool
`input` strictly follows the `input_schema`"* is stated as a guarantee, not
a probabilistic improvement. Two further avenues were checked before
concluding anything:

- The debug log only captures request/response metadata (headers, status),
  not the raw streamed tool-call content (`partial_json` deltas or the
  final reconstructed `tool_use.input`) - so the actual malformed payload
  Claude returned could not be inspected directly from this log.
- Checked whether LCATS's own code could be corrupting a valid streamed
  response during reconstruction: `lcats/lcats/llm/anthropic_backend.py:76-77`
  uses `stream.get_final_message()`, the Anthropic SDK's own official
  helper for accumulating a streamed tool call into a parsed message - not
  a hand-rolled SSE parser. A client-side reconstruction bug is unlikely to
  be the cause.

**Conclusion:** either grammar-constrained sampling has a real, rare
failure mode for deeply nested arrays-of-objects (`entities[].mentions[]`)
that the documentation doesn't fully capture, or something not yet
identified is at play - this could not be fully resolved without capturing
the actual raw tool-call payload from a failing case, which the debug log
does not retain. **Regardless of which is true, this materially raises the
priority of two fixes already identified:**

1. Category B's defensive checks are not optional belt-and-suspenders
   anymore - detecting a malformed item is the *only* thing that would
   have prevented this specific crash, since strict mode alone
   demonstrably did not. Per the correction above, detection alone is not
   sufficient either: the fix must also surface an explicit extraction
   error for the affected segment/story (not just skip-and-continue) and
   log the raw offending item to a file when tripped, so a future
   recurrence is both correctly excluded from density figures and fully
   diagnosable without another expensive full run or debug-log
   archaeology.
2. `experiments/03_cross_segment_relation_pilot/run_pilot.py`'s `main()`
   per-story loop only catches `FatalPilotError` around `run_story()` - any
   other exception (like this one) propagates uncaught, and the code that
   writes `pilot_stories.jsonl`/`pilot_usage.jsonl`/`pilot_summary.json`
   never runs. This crash discarded the *entire* run's results, including
   `junior__abernathy`'s already-completed, already-paid-for full pipeline
   pass and all 18 genre-detection classifications - not just the one
   story that failed. This is independent of the strict-mode question and
   is a certain, high-value fix on its own.

### Category C - extractors with no tool schema at all (fully unconstrained JSON-in-text)

- `scene_analysis.py:186` `make_segment_extractor` - Stage 1 segmentation.
  **Confirmed live**: with `--model claude-haiku-4-5-20251001`, 11 of 17
  sampled stories (65%) were excluded with `extraction_error="parsing_error"`
  in the user's own real run, and the `western` stratum had zero included
  stories. This is the actual, currently-blocking reliability problem -
  worse than either crash already fixed.
- `scene_analysis.py:465` `make_semantics_extractor` - per-segment semantics
  evaluation (`output_key="judgment"`). Same risk class as segmentation;
  not exercised by this pilot, so failure rate is unmeasured, not absent.
- `story_analysis.py:398` `make_doc_classification_extractor` - whole-text
  document classification (`output_key="classification"`). Same risk
  class, different module, also unmeasured.

`llm_extractor.py`'s `extract()` method ([`:373-401` region]) behaves
differently on the tool_schema path than the non-tool_schema path: when
`tool_schema` is set, `extracted_output` becomes the **whole** parsed dict
(e.g. `{"relations": [...]}`), with no `output_key` unwrapping - this is
load-bearing for the six ERW extractors (each of which reads a
differently-named top-level key: `relations`, `entities`, etc., not
`output_key`'s default of `"segments"`). Retrofitting `scene_analysis.py`'s
`make_segment_extractor` with a `tool_schema` would change its
`extracted_output` shape from a bare list to `{"segments": [...]}`, which
would break its **other** real caller,
`lcats/lcats/analysis/story_processors.py:76,142` (`segments =
seg_extraction.get("extracted_output") or []` expects a bare list today).
Any fix here needs to update both call sites (or design around it, e.g. a
second, schema-hardened extractor specific to one caller) - not just add
`tool_schema=` to the shared factory function in isolation.

### Category D - `processor.py` (blocked by `forbidden_actions: modify_event_role_world_extractor`)

- `processor.py:315-329` `process_segments()` (plural, the normal public
  entry point) has no `model` parameter - it builds every extractor via its
  factory (`make_entity_extractor(llm_backend)`, etc.) with each one's
  hardcoded `gpt-4o` default baked in. Any caller with a non-OpenAI backend
  silently gets an invalid model ID unless, like `run_pilot.py`, it avoids
  `process_segments()` entirely and drives `process_segment()` (singular)
  directly with self-built, model-overridden extractors.
- `processor.py:130-137` (entity), `:158-160` (event), `:178-182`
  (relation), `:197-201` (discourse), `:223-227` (hypothesis) - each pass's
  `process_segment()` stringifies the structured `api_error` dict (which
  already carries `category`/`can_retry`/`should_abort_batch` from
  `llm_extractor.py`'s `_classify_api_error`) into a plain f-string before
  appending it to `extraction_errors`, discarding that structure. This
  forced `run_pilot.py`'s `FatalPilotError`/`_check_fatal()` (PR #166) to
  re-derive fatality via substring-matching on the stringified message
  instead of reading the flag that already exists one layer up.

### Category E - cost visibility and control (logging, budgets, checkpointed runs, local models)

Distinct in kind from Categories A-D: not a correctness bug, but a missing
capability. Raised because the real pilot run has spent roughly $15 of its
~$50 budget so far - not sustainable for routine dogfooding, let alone a
deliberate full-corpus run, if every iteration costs this much to find and
fix reliability bugs like Categories A-D above.

**What already exists, confirmed by grep:** every `LLMBackend.complete()`
call already returns token counts (`BackendResponse.input_tokens`/
`output_tokens`, `lcats/lcats/llm/backend.py:11-28`), and the ERW pipeline
already has a per-pass usage record (`PassUsage`,
`lcats/lcats/analysis/event_role_world/processor.py:40-59`) - but it is
opt-in per script (only `run_pilot.py` writes it, to `pilot_usage.jsonl`),
there is no dollar-cost conversion anywhere in the codebase (grepped for
any pricing table - none exists), and nothing tracks Spacy/Stanza
construction cost at all, which is exactly what caused PR #165's per-story
NLP-backend-reload bug - a systemic logger would have caught that in
seconds instead of a live dogfooding session. No prior checkpoint/resume
design doc exists in `project/` either, despite being recalled as
previously discussed - if so, it was not captured here.

**E1. Model-invocation logging and budget enforcement.** Options considered:

| Option | Pros | Cons |
|---|---|---|
| Extend `PassUsage` into a shared, opt-in logger (`lcats.utils.usage_log`) reused across scripts | Minimal new surface, reuses a pattern already proven and reviewed this session | Still requires each call site to invoke it unless hooked centrally |
| Hook logging at the backend layer itself (`AnthropicBackend.complete()`/`OpenAIBackend.complete()`) | Every caller gets logging "for free," retroactively covers every existing and future script; single choke point to also enforce a budget-abort check, reusing the `FatalPilotError` abort pattern from PR #166 | Touches shared `lcats/llm/` code - smaller blast radius than `event_role_world/` but still a real, testable change |
| OpenTelemetry | Industry-standard, exportable to real dashboards later | Real dependency + conceptual overhead for what is currently single-researcher local scripts - likely overkill now |
| A pricing table (`lcats/llm/pricing.py`: model -> $/1M input/output tokens) | Needed regardless of the above to turn token counts into dollar budgets | Needs upkeep as providers change pricing/models |

Recommendation floated in discussion: hook logging at the backend layer
plus a pricing table - highest leverage, makes every future script
cost-visible and budget-enforceable by default rather than opt-in.

**E2. Restartable/checkpointed runs.** Options considered:

| Option | Fit | Tradeoff |
|---|---|---|
| Custom checkpoint file, keyed on a success/failure predicate (not mere presence) | Cheapest possible fix; ~80% already built - `FatalPilotError`'s partial-write-on-abort (PR #166) already gives a durable record of what completed | Not a general "workflow" tool, just this script, unless generalized into a small shared helper |
| `joblib.Memory` | Trivial dependency, near-zero learning curve | Call-level memoization only, not real pause/resume/monitor semantics for a running multi-stage job |
| Prefect (open-source core, no server required for local use) | Purpose-built for this: `@flow`/`@task` decorators, built-in retries, result caching/resume, runs entirely locally | Real new dependency and a framework to learn |
| Luigi | Similar niche to Prefect, target-based resumability (skip a task if its output file exists) | Older, less actively developed than Prefect |
| Dagster / Airflow / Ray Workflows | Full orchestration platforms with durable execution | Significant infrastructure (scheduler, DB, or cluster) - poor fit for a single researcher's local `python run_pilot.py` scripts |

Recommendation floated in discussion: start with the custom checkpoint
approach given how much is already built; only reach for Prefect if
checkpointing needs to generalize across several experiments with genuinely
independent stages needing real pause/resume/monitor semantics.

**Correction (review, PR #169):** mere presence of a `story_id` in
`pilot_stories.jsonl` is not a valid completion marker on its own -
`run_story()` (`experiments/03_cross_segment_relation_pilot/run_pilot.py`)
writes a row with `excluded: true` for exactly the transient
parsing/extraction failures this audit is about (including the ones this
audit proposes fixing). Treating any recorded `story_id` as "done" would
mean a resumed run - after switching models or repairing an extractor -
preserves or skips those recoverable failures instead of recomputing them,
silently under-filling or biasing the sample. Any checkpoint design needs
a success/failure predicate (e.g. only skip rows where `excluded` is
false, or where the failure reason is known non-transient), not bare
presence.

**E2 (design proposal): break the pipeline into staged, inspectable steps.**
Proposed after the second real crash (see the Category B update above):
decompose the single monolithic script into discrete stages that each
persist their output to disk before the next stage runs, so a downstream
failure or fix does not require redoing expensive upstream work - a full
end-to-end script remains fine for the final, validated run.

*Current state, confirmed by direct inspection of
`experiments/03_cross_segment_relation_pilot/run_pilot.py`*: natural stage
boundaries already exist as functions - `build_stratified_sample`
(`:197`), `_segment_story` (`:259`), `_run_erw_pipeline` (`:443`),
`run_story` (`:561`) - but every one of them passes Python objects to the
next stage purely in memory. Nothing is written to disk until `main()`'s
single write block at the very end (`:847-859`), after the *entire*
per-story loop finishes. This is the concrete mechanism behind both real
crashes this pilot has had: a failure anywhere before that block discards
every already-completed, already-paid-for story, not just the one that
failed.

Grounded against two reputable, fetched (not recalled) sources:

- Apache Airflow's own best-practices docs: *"You should treat tasks in
  Airflow equivalent to transactions in a database. This implies that you
  should never produce incomplete results from your tasks"* and, on
  passing data between stages, *"a good way of passing larger data between
  tasks is to use a remote storage such as S3/HDFS"* rather than in-memory
  objects.
- Databricks' medallion architecture (bronze/silver/gold staged layers),
  on the specific cost benefit of persisting intermediate output: *"the
  ability to provide ... reprocessing if needed without rereading the data
  from the source system"* - you can "recreate your tables from raw data
  at any time," avoiding "repeatedly pulling data from source systems."

**Pros:**
- Directly fixes the sunk-cost problem: genre-detection (200 API calls)
  and segmentation are exactly the "source system pulls" the medallion
  pattern says shouldn't be repeated on every downstream failure - right
  now they are repeated on every crash, paid or not.
- Would have resolved this session's actual debugging dead end: had
  entity-extraction's raw `tool_result` been persisted per segment, the
  literal malformed payload from the crashing call would have been
  directly inspectable, rather than unrecoverable from the debug log (see
  the Category B update above).
- Each stage becomes a pure function (read one artifact, write another),
  directly serving the "much more robust unit testing" goal - far easier
  to fixture-test in isolation than mocking the whole pipeline end-to-end.
- Enables exactly the proposed workflow: inspect intermediate output,
  tweak it, re-run just the affected stage.
- This is a concrete design for the checkpointing option already listed
  above (E2's own table) - staged artifacts are the checkpoint boundaries.
- Precedent for the value of partial persistence already exists in this
  codebase: PR #166's `FatalPilotError` already carries partial
  `usage_rows` so an aborted run doesn't lose *that* data; this
  generalizes the same instinct to the whole pipeline.

**Cons:**
- More moving parts: needs a naming/manifest scheme tying a run's stage
  artifacts together, and a way to pin exactly which sample a downstream
  stage is operating on (so a later run with a different `--seed` cannot
  silently mismatch upstream and downstream artifacts).
- Two orchestration paths (staged/inspectable for dev, single end-to-end
  for the final run) risk drifting out of sync unless built as the same
  underlying stage functions with two thin wrappers - a real risk in this
  codebase specifically, given this session already found one instance of
  two code paths silently disagreeing (Category C's `extracted_output`
  shape differing between tool_schema and non-tool_schema modes).
- Modest I/O overhead - real but trivial at this pilot's scale (dozens of
  stories, not millions of rows).
- Scope question worth deciding explicitly: this is a real architectural
  change to `run_pilot.py` itself. It sits within WI-EVENT-0030's
  `expected_actions: create_file, edit_file` and does not touch
  `event_role_world/` (so `forbidden_actions:
  modify_event_role_world_extractor` does not block it), but given the
  postmortem framing this pilot is now under, it may be cleaner to scope
  as its own follow-up rather than another patch under the same work item.

**E2 (revisited): corpus-wide context changes which "real tool" to reach
for later, not whether to start with checkpointing.** Prompted by a
broader framing: LCATS is now used by two researchers, is open source
with a planned pip release, has multiple pipeline-like processes beyond
this pilot (other story-analysis experiments, notebooks, `lcats/KMo/`,
the `lcats gather` pipeline), and has real medium-term scale ambitions
(10x-100x corpus growth over the next year, a million-book corpus under
consideration) plus an explicit goal of processing stories "possibly in
parallel."

Two artifacts already in the repo turned out to be directly relevant:

- `lcats/lcats/pipeline.py` (last touched only by a
  formatter-only commit - confirms "aborted, unfinished"): a minimal
  `Stage`/`Pipeline`/`RunResult` dataclass trio that threads named values
  through a sequence of callables in memory, with simple retry-with-sleep
  support (`_run_with_retries`). `RunContext` is declared but never
  referenced anywhere in `Pipeline`'s logic - dead code.
  `Stage.cache: bool = True` is declared but never read or acted on -
  the caching it implies was never implemented. No disk persistence at
  all (`state` lives only in the Python process; a crash loses
  everything, the same failure mode `run_pilot.py` has today), and no
  parallelism (purely sequential `for stage in self.stages`). A reasonable
  ordering/retry skeleton, but it does not solve checkpointing or
  parallelism.
- `lcats/project/design/flat_story_layout_migration_impact_report.md`: a
  16-site impact audit (deferred, unimplemented) for moving each story
  from a flat `data/<collection>/<story>.json` file to its own directory
  `data/<collection>/<story>/story.json`. Once each story has its own
  directory, that directory becomes the natural place to persist
  per-stage artifacts (`story.json`, `segments.json`, `entities.json`,
  ...) - this is the "staged, inspectable pipeline" idea from the E2
  design proposal above, generalized from one experiment script to the
  whole corpus at once.

**The precedent that actually settles the "is custom-checkpointing just a
hack" question**: `lcats gather`'s own writer already does file-existence
checkpointing in production, at real scale -
`lcats/lcats/gatherers/downloaders.py:223-253` (`DataGatherer.download`):

```python
def download(self, filename, resource, handler, force=False):
    """If a file doesn't already exist, get its resource and process it with the handler."""
    file_exists, file_path = self.ensure(filename)
    if not file_exists or force:
        ...
    else:
        print(f"File {file_path} exists, skipping download.")
```

This is already the house pattern for one of LCATS's two major pipelines,
not a one-off shortcut being proposed for `run_pilot.py` alone. Also
confirmed: none of Prefect/Dagster/Airflow/Ray/Luigi/joblib appear
anywhere in `lcats/pyproject.toml` or the codebase, and `lcats/KMo/`'s own
per-story loops (`analyze.py:109,225,305,412`, `scenes.py:222,390`) are
all plain sequential `for story in corpora.stories:` - no parallelism
exists anywhere in LCATS today either.

**Revised table, reflecting this context:**

| Option | Fit given the new context | Verdict |
|---|---|---|
| Bucket-directory + file-existence checkpoint (generalizing `DataGatherer.download`'s pattern) | Proven precedent, zero new dependency, matches a design the team already independently arrived at | **Do this first, regardless of what comes later** |
| Revived `lcats/lcats/pipeline.py` | Fine ordering/retry skeleton, but needs real work added (disk-backed state, per-item parallel execution) before it does anything the current pattern doesn't | Worth reviving as the shared orchestration layer once bucket-checkpointing exists, not as-is |
| Prefect | Still a reasonable, low-friction "graduate to a real tool" option | Still viable, no longer uniquely best |
| Ray | Purpose-built for exactly "checkpointed, parallel processing of many independent items" - a closer conceptual match to "per-story bucket, parallelizable" than a DAG-orchestration tool | Rises significantly given the stated parallelism goal and eventual scale |
| Dagster | Its "Software-Defined Assets" model maps almost one-to-one onto "each story-bucket directory holds versioned per-stage artifacts" - the mental model the migration report already arrived at independently | Rises significantly - adopting it would implement an already-agreed model in an established tool, not require reconceiving the design |
| Luigi | Less community/docs than Prefect/Dagster | Weaker now, given an OSS audience that will want strong docs |
| Airflow | Needs a persistent scheduler + metadata DB + webserver - built for continuously-scheduled jobs | Still disqualified - LCATS's usage is researcher-triggered ad hoc runs, not a standing service; unchanged by the new information |

**Decisive advantage / disqualifying limitation, revisited**: the
bucket-based checkpoint approach still has a decisive advantage (proven
in-production precedent + zero new dependency + already-agreed design).
Airflow's disqualifying limitation is unchanged (operational model
mismatch, not a scale question). Ray and Dagster are re-ranked upward, not
newly decided - they deserve real evaluation once the custom pattern is
outgrown, specifically because of the parallelism and asset-lineage
goals, not "more scale = fancier tool" reasoning alone.

**Recommendation on sequencing**: do the bucket-directory migration plus
the generalized checkpoint pattern first - the natural next increment,
matching proven precedent - and let that experience determine empirically
whether Ray or Dagster (or neither) is actually needed once real
parallel/distributed execution is warranted, rather than choosing an
orchestrator speculatively before the corpus scale demands it.

**E3. Local/less-expensive models.** Colleague (Kenny) reports using Ollama
(supports multiple local backend models) for Llama 3 and Gemma, "in
conversation, not coding support" - speed and quality both lower than
desired. Flagged concern: Ollama-hosted local models have historically had
much weaker/inconsistent tool-calling and structured-output support than
Anthropic's or OpenAI's mature APIs - precisely the reliability axis
Categories A-C above are about. Conversational use (Kenny's tested case) is
the easy case; the ERW pipeline's entire viability depends on the harder
case (schema-conformant structured extraction). Recommendation floated:
a cheap, targeted spike - run one story through the actual tool-schema path
against a local Ollama model - before investing further, rather than
assuming it's a viable cost-reduction lever untested.

## 4. Next steps (not yet started)

1. Let the in-progress real run (Opus, post-Haiku-switch) finish and
   inspect its results/exclusion rate - does switching models alone resolve
   Category C's segmentation failures enough to trust this run's density
   numbers, or is a source-level fix still needed before WI-EVENT-0030 can
   close?
2. Revisit this file, discuss scope, then create the actual work item(s) -
   likely a workstream given the breadth (Categories A/B/D require their
   own work item(s) since they touch `event_role_world/` directly and need
   a `forbidden_actions`-free work item to do so; Category C is a separate,
   more novel design problem per extractor - segmentation's fix in
   particular needs to address the `story_processors.py` blast radius
   noted above, not just bolt on a schema).
3. Category E is independent of the pipeline-reliability work above and
   could proceed on its own schedule - decide whether it becomes its own
   work item/workstream or folds into the same one, once scope discussion
   happens.
4. No code changes have been made as part of this audit - it is a finding
   only.
