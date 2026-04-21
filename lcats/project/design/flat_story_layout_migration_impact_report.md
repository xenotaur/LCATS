# Flat Story Layout Migration Impact Report

Date: 2026-04-21  
Scope: LCATS code, tests, and developer-facing docs that currently assume the flat story layout:

- current: `data/<collection>/<story>.json`
- proposed: `data/<collection>/<story>/story.json`

This report is an **audit only**. It does not perform storage migration.

## Executive summary

Flat-layout assumptions are **present and material**, but concentrated in predictable surfaces:

1. direct file creation/writes in gatherers (`filename + ".json"` under a collection dir)
2. story discovery and story identity heuristics in corpus CLI/survey code
3. tests asserting filename/path behavior under flat naming
4. command examples/help text that still refer to `data/` and filename-oriented workflows

Based on the current dependency shape, a migration appears feasible in a **short staged chain** rather than one-shot:

- Stage 1: make loaders/discovery/identifier logic dual-layout-compatible
- Stage 2: migrate writers/gatherers and update output semantics
- Stage 3: migrate fixtures/tests/docs and remove transitional behavior

A single PR is possible technically, but risk is elevated due to test surface area and identifier semantics tied to filename stem and basename.

## Audit method

- Searched LCATS package and tests for JSON suffix checks, glob/rglob usage, path formatting, and filename-stem fallbacks.
- Manually reviewed the primary discovery/loading/CLI/output/gatherer modules.
- Reviewed representative docs and CLI help examples.

## Inventory of impacted areas

### A) Story discovery / enumeration

#### 1) `lcats/lcats/stories.py` (`Corpora.get_corpora`) — **large**

- Enumerates each corpus directory and only consumes immediate `*.json` children.
- Calls `os.listdir(dir_path)` and filters by `file_name.endswith(".json")`.
- This is a hard dependency on the flat layout (`<story>.json` directly in collection).

Migration impact:
- Must change directory traversal logic and story file selection strategy.
- Existing behavior also ingests any JSON peer file in collection root.

#### 2) `lcats/lcats/analysis/corpus/discovery.py` (`find_corpus_stories`, `find_json_files`) — **moderate**

- Recursively gathers all `*.json` files.
- This is compatible with nested `story.json`, but broad matching becomes ambiguous when story dirs include additional JSON artifacts.

Migration impact:
- Introduce explicit story-file predicate (e.g., only `story.json` under story dirs, or schema validation).
- Keep recursive traversal but tighten inclusion criteria.

#### 3) `lcats/lcats/datasets/torchdata.py` (`JsonDataset`) — **moderate**

- Recursively includes every `*.json` under root.
- Under proposed layout this still discovers stories, but also risks over-including non-story JSON sidecars.

Migration impact:
- Add optional filtering policy for canonical story file selection.

### B) Story loading / opening

#### 4) `lcats/lcats/gatherers/downloaders.py` (`DataGatherer.ensure`) — **large**

- Constructs output as `<collection>/<filename>.json` using `filename + suffix`.
- Represents central writer assumption for gatherers.

Migration impact:
- Needs writer path contract change to `<collection>/<story>/story.json`.
- Affects `downloads` mapping values and downstream expectations.

#### 5) `lcats/lcats/analysis/corpus/cli.py` (`run_stats`) — **small/moderate**

- Accepts direct file arguments only when `Path(...).suffix == ".json"`.
- Directory mode relies on discovery; file mode remains filename-oriented.

Migration impact:
- Mostly compatible, but file-vs-dir UX should account for story directories.

### C) Path construction / path printing / story identity

#### 6) `lcats/lcats/analysis/corpus/cli.py` (`infer_story_title`) — **large risk**

- Fallback uses `file_path.stem` as title.
- With `.../<story>/story.json`, stem becomes `story` for nearly all stories.

Migration impact:
- Must replace stem fallback with directory-based identifier or metadata-only policy.

#### 7) `lcats/lcats/analysis/corpus/output.py` (`story_file`, `path`, identifiers) — **moderate/large**

- Uses `file_path.name` for `story_file` and `str(file_path)` for path reporting.
- Identifier mode `filename` becomes low-value under `story.json` canon (collisions).

Migration impact:
- Revisit `story_identifier` semantics and default modes.
- Potentially add `story_dir`/`story_slug` fields or reinterpret filename identifier.

#### 8) `lcats/lcats/analysis/corpus/output.py` (`write_human_rows`) — **small**

- Prints full file path header for findings.
- Works with new layout, but CLI/user documentation must reflect changed path appearance.

### D) Corpus survey / analysis tools

#### 9) `lcats/lcats/analysis/corpus/processing.py` (`process_file`, `process_files`, `process_corpora`) — **small/moderate**

- Mirrors relative input paths into job output directory.
- Generally layout-agnostic, but deeper nesting changes output artifact tree and test expectations.

Migration impact:
- Behavior likely remains valid; update tests and user expectations for mirrored paths.

#### 10) `lcats/lcats/analysis/corpus/cli.py` defaults (`directories` default `data/`) — **small doc/UX**

- Defaults and examples are directory-centric and still workable, but messaging assumes legacy data path habits.

Migration impact:
- Update examples/help to show canonical corpus root and/or story-dir examples.

### E) Tests and fixtures

#### 11) `lcats/tests/analysis_tests/corpus_package_test.py` — **moderate**

- Multiple tests write/read `story.json` directly under one directory and assert exact filenames/paths.
- Some tests already cover nested form (`a/story.json`), but many assertions still encode filename identity assumptions.

Migration impact:
- Update fixtures and assertions around identifier/path columns and fallback title behavior.

#### 12) `lcats/tests/analysis_tests/corpus_survey_test.py` — **moderate/large**

- Heavy assertions on `story_file == "story.json"`, path fields, and rendered output containing file basenames.

Migration impact:
- Substantial assertion updates likely required once identifier policy changes.

#### 13) `lcats/tests/analysis_tests/corpus_surveyor_test.py` — **moderate**

- Mixed fixture patterns (`a/story.json`, flat files, nested files) already exercise recursion.
- Still contains many explicit filename/path expectations that may shift after migration.

Migration impact:
- Mostly assertion/data setup updates; traversal logic tests remain useful.

#### 14) `lcats/tests/stories_test.py` + gatherer tests — **small/moderate**

- Story IO tests use direct `*.json` file paths (fine for unit scope).
- Gatherer tests assert output paths ending with `*.json`; these will need updates when writer contract changes.

### F) Docs / architecture / roadmap / CLI examples

#### 15) `lcats/lcats/cli.py` help examples and `lcats/tests/cli_test.py` — **small/moderate**

- Help epilogs include commands like `lcats survey data/ ...` and `lcats stats data/ ...`.
- Tests pin these example strings.

Migration impact:
- Update CLI examples and corresponding tests in same change set.

#### 16) Repository corpus content (`corpora/<collection>/*.json`) — **context/risk signal**

- Current checked-in corpus content is physically flat per collection with JSON story files at collection root.

Migration impact:
- Any migration plan touching real corpus content should coordinate tooling and fixture updates tightly.

## Recommended migration strategy

Recommendation: **short staged PR chain**.

### Stage 1 — Compatibility primitives (low-risk functional prep)

- Add a single canonical story-file selector utility used by discovery/loaders.
- Make identifier/title fallback robust for nested `story.json` (do not use raw stem fallback when filename is canonical).
- Add dual-layout tests (flat + story-dir) without changing gatherer output yet.

### Stage 2 — Writer and CLI/output contract updates

- Update `DataGatherer` write path policy to story-directory form.
- Update output identifier semantics (de-emphasize `filename` identity under canonical `story.json`).
- Update survey/stats examples/help text and corresponding tests.

### Stage 3 — Fixture/data/doc convergence and cleanup

- Normalize tests/fixtures/docs to story-directory canon.
- Remove temporary dual-layout branches (if added).
- Confirm end-to-end commands over representative corpora trees.

## Risk areas

1. **Filename stem identity collapse**
   - `file_path.stem` fallback becomes `story` across most files.
2. **Identifier column semantics**
   - `story_file`/`filename` identifiers become non-unique under canonical naming.
3. **Over-broad recursive `*.json` discovery**
   - Potential false positives when story directories contain non-story JSON artifacts.
4. **Test fragility around path serialization**
   - Many tests assert exact filename/path rendering.
5. **Gatherer output map expectations**
   - Existing gatherer return values and tests assume direct `<name>.json` leaf files.

## Deferred questions

1. Should canonical story identity come from directory slug, metadata title, or a new explicit story id field?
2. Should discovery include only files named `story.json`, or support both canonical names and schema-qualified JSON files?
3. Do we need a permanent dual-layout read window, or can migration be atomic after fixture/corpus update?
4. Should TSV/human output schema add a first-class `story_dir` column to preserve unique human identifiers?

## Bottom line

Evidence supports migration feasibility, but points to a **staged sequence** as the safer path because identifier behavior and test surface area are tightly coupled to current filename assumptions.
