---
id: WI-PROMOTE-0112
title: Build the sanitized genre-sidecar seed manifest and seed command
type: deliverable
status: resolved
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams: []
related_design:
  - project/design/genre-sidecars-in-release-workflow.md
  - experiments/05_metadata_genre_prefilter/results/full_scan/validation_results.jsonl
  - tools/rewrite_genre_cache_db_path.py
  - docs/reference/corpus-promotion.md
  - docs/reference/prepare-corpora-release.md
  - src/lcats/analysis/corpus/promote.py
  - project/work_items/resolved/WI-PROMOTE-0108.md
  - project/work_items/resolved/WI-GENRE-0109.md
  - project/work_items/resolved/WI-GENRE-0077.md
  - project/work_items/resolved/WI-PROMOTE-0101.md
  - project/work_items/resolved/WI-PROMOTE-0100.md
depends_on:
  - WI-PROMOTE-0108
  - WI-GENRE-0109
blocked_by: []
blocked: false
blocked_reason: null
resolution: 'Implemented and merged in PR #486: tools/build_genre_seed_manifest.py builds a sanitized genre-sidecar seed manifest from the tracked evidence file validation_results.jsonl at release time (146 records, no absolute cache_db_path values, every payload validated, written atomically), with 39 tests including a drift check against corpora/. Refuses to write over the evidence file or inside corpora/ or data (by file identity, so miscased paths and hard links are caught). On scratch copies, create-only insert then a bare replace exits 0 with 0 blocked and 146 byte-identical genre.json files; an unseeded data stays blocked. Runbook step 6b and the other design-note follow-ups are not implemented here.'
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - change_promote_replace_semantics
  - modify_validation_evidence
  - edit_corpora
  - write_to_real_corpora_or_data
  - use_promote_upsert_for_seeding
acceptance:
  - "A tool builds a seed manifest from the tracked evidence file experiments/05_metadata_genre_prefilter/results/full_scan/validation_results.jsonl without modifying that file: exactly 146 {lcats_id, payload} records, zero absolute cache_db_path values, and a payload for every record that validates via genre_sidecar.validate_sidecar()"
  - "Unit tests cover sanitizing, the record count, an unmodified evidence file, the envelope shape, idempotence on already-clean input, and loud failure (non-zero exit) on malformed input, plus a drift test asserting the built payloads equal the current corpora/ genre sidecars"
  - "A scratch-copy run, recorded in the execution record, shows the create-only seed and a bare replace working: insert --dry-run reports 146 records, a real insert into a scratch data/ exits 0, a second insert is rejected for all 146, and a bare replace into a scratch corpora/ exits 0 with 0 blocked and 146 genre.json files byte-identical to corpora/; no real data/ or corpora/ is written"
  - "lrh validate reports 0 errors"
required_evidence:
  - test_output
  - manual_review
  - lrh_validate
artifacts_expected:
  - tools/ seed-manifest build tool (new, or a new mode of tools/rewrite_genre_cache_db_path.py)
  - tests/dev_tests/ unit test for the tool
---

# Work Item: WI-PROMOTE-0112

## Summary

Build a small, tested tool that derives a sanitized seed manifest from the
tracked genre evidence file, so a corpus release can seed the regenerated
`data/` with the 146 tranche-promoted `genre.json` sidecars before
`lcats promote replace`. This is follow-up 1 of the design note
`project/design/genre-sidecars-in-release-workflow.md` (`WI-PROMOTE-0108`).

## Problem / Context

The documented release regenerates `data/` and ends with a plain
`lcats promote replace`. The 146 `genre.json` sidecars from PR #362 exist only
in `corpora/`, so a bare release run against the current `corpora/` exits `1`
and blocks 7 collections (146 orphaned sidecars); the only way to exit `0` is
`--allow-orphaned-sidecar-deletion`, which would delete all of them
(`WI-PROMOTE-0108`, verified by dry-run).

The recommended fix (Option C in that note) seeds the regenerated `data/` from a
tracked manifest before `replace`, using create-only
`lcats promote insert --sidecar genre --tranche-manifest <manifest> --dest data/`.
It must be `insert`, not `upsert`: `upsert` overwrites a whole file and would
silently discard a pipeline-produced `genre.json`; `insert` refuses and stops
the release. On scratch copies this gave a bare `replace` exit `0`, 12
collections promoted, 0 blocked, and 146 byte-identical `genre.json` files.

The source for the seed is the tracked evidence file
`experiments/05_metadata_genre_prefilter/results/full_scan/validation_results.jsonl`
(146 bare `genre-sidecar-v1` records). It is immutable (`WI-GENRE-0077` forbade
modifying validation evidence) and **still contains 146 absolute
`cache_db_path` values**, so replaying it unchanged would re-introduce the leak
that `WI-GENRE-0109` removed. The manifest must therefore be sanitized when it is
built. `tools/rewrite_genre_cache_db_path.py` (`WI-GENRE-0109`) already has a
tested `rewrite_cache_db_path()` to reuse.

### Duplication search
- In-repo: no existing tool builds a seed manifest. `tools/rewrite_genre_cache_db_path.py`
  builds a manifest from `corpora/` for a different purpose (rewriting the
  already-promoted files); it is the code to reuse, not a duplicate. The design
  note lists this item as follow-up 1.
- Sibling repos: none identified.
- External libraries: none; project-specific tooling.
- Recommendation: Proceed.

### Demand search
- Work items: none open; this is follow-up 1 named in `WI-PROMOTE-0108`'s note.
- Proposals: `PROP-LCATS-PROMOTE-MODE-REDESIGN` covers the guard, not the seed.
- Backlog: no entry; raised by the `WI-PROMOTE-0108` investigation.
- Recommendation: Proceed.

Both parent workstreams (`WS-GENRE-EVIDENCE-SIDECARS`, `WS-PROMOTE-MODE-REDESIGN`)
are resolved, so `related_workstreams` is left empty.

## Scope

- Decide where the seed manifest lives. **Default: derive it from the evidence
  file at release time with a command, so no second tracked copy of 146
  payloads is created and the evidence file stays untouched.** Committing a
  derived manifest is allowed only if the executor records, in the execution
  record, why building at release time was not enough.
- Add a small tested tool or command that builds the sanitized manifest. Reuse
  `rewrite_cache_db_path()`, either as a new input mode of
  `tools/rewrite_genre_cache_db_path.py` or as a small sibling tool that imports
  it.
- Verify, on scratch copies only, that seeding a regenerated `data/` and then a
  bare `replace` works end to end.

## Required Changes

- Add the build tool. It reads the evidence file, sanitizes every
  `assessments[*].provenance.cache_db_path` to its basename, and writes a JSONL
  manifest of `{"lcats_id": "<collection>/<story>", "payload": <sanitized record>}`
  envelopes. It never writes to the evidence file, `corpora/`, or `data/`.
- Add unit tests under `tests/dev_tests/` for sanitizing, the 146-record count,
  an unmodified evidence file, the envelope shape, idempotence on already-clean
  input, and a non-zero exit on malformed input. Add a drift test asserting the
  built payloads equal the current `corpora/*/*/genre.json` files.
- Verify on scratch copies of a populated `data/` and of `corpora/` (see Risk
  Notes). Record the exact commands and results in the execution record:
  `lcats promote insert ... --dry-run` reports 146; a real `insert` into the
  scratch `data/` exits 0; a second `insert` is rejected for all 146; a bare
  `lcats promote replace --source <scratch data> --dest <scratch corpora>` exits 0
  with 0 blocked; the 146 `genre.json` files are byte-identical to `corpora/`.
- Seeding uses `insert`, never `upsert`; the real `data/` and `corpora/` are not
  written by this work item.

## Non-Goals

- Does not change `lcats promote replace` semantics or the orphaned-sidecar guard.
- Does not edit `corpora/` or `validation_results.jsonl`.
- Does not define merge or precedence rules for a seeded sidecar colliding with a
  pipeline-produced one; the create-only `insert` stops the release instead.
- Does not add release-runbook step 6b (`prepare-corpora-release.md`); that is
  follow-up item 2 of the design note, unless it is a trivial one-line pointer.
- Does not cover other sidecar kinds, a release preflight, or a story-text
  fingerprint for genre sidecars (follow-up items 3 and 4).

## Acceptance Criteria

- A tool builds a seed manifest from the tracked evidence file without modifying
  it: exactly 146 `{lcats_id, payload}` records, zero absolute `cache_db_path`
  values, every payload valid under `genre_sidecar.validate_sidecar()`.
- Unit tests cover sanitizing, the record count, an unmodified evidence file, the
  envelope shape, idempotence on clean input, and malformed-input failure, plus a
  drift test that the built payloads equal the current `corpora/` genre sidecars.
- The scratch-copy run is recorded and shows insert dry-run 146, real insert exit
  0, second insert rejected for all 146, and a bare `replace` exit 0 with 0
  blocked and 146 byte-identical `genre.json` files; no real tree is written.
- `lrh validate` reports 0 errors.

## Validation

- `scripts/test`
- `lrh validate`
- `git diff --name-only origin/main`

## Risk Notes

- A worktree has no `data/`; the scratch run needs a populated `data/` copy (a
  shared one exists at `/Users/centaur/Tempspace/Projects/LCATS/data`). Copy it
  and `corpora/` to a scratch directory and write only there.
- The editable `lcats` install can resolve to a different checkout; verify
  `lcats.__file__` and run with `PYTHONPATH` set to this checkout's `src`. Use the
  `LCATS` conda environment's pinned black and ruff before committing.
- The seed relies on regenerated bucket IDs matching the evidence's `lcats_id`
  values. A mismatch is rejected loudly (exit 1), but a story whose text changed
  since the evidence was produced is **not** detected: sidecars carry no
  story-text fingerprint (follow-up item 4).
- Building at release time keeps one source of truth but makes the release depend
  on the evidence file staying in the repository; do not move or rename it
  without updating the tool.
