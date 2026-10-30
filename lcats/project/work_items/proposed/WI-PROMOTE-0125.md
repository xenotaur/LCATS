---
id: WI-PROMOTE-0125
title: Reproduce linguistics sidecar release seeding with a real spaCy run
type: investigation
status: proposed
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams:
  - WS-SIDECAR-SAFE-PROMOTION
related_design:
  - project/design/sidecar-kinds-release-rule.md
  - src/lcats/analysis/corpus/linguistics_cli.py
  - src/lcats/analysis/corpus/sidecar_validators.py
  - src/lcats/analysis/linguistics/runner.py
  - docs/how-to/run-linguistics.md
  - project/work_items/resolved/WI-PROMOTE-0117.md
depends_on:
  - WI-PROMOTE-0117
blocked_by: []
blocked: false
blocked_reason: null
resolution: null
expected_actions:
  - read_files
  - run_tests
  - edit_file
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - edit_corpora
  - change_promote_replace_semantics
  - implement_seeding_wrapper
  - register_unregistered_sidecar_kinds
  - use_network
acceptance:
  - "Real spaCy outputs (linguistics.json, linguistics.tokens.json at token-detail v1 and v2, and linguistics.lexicon.json) are generated for at least three real stories in a scratch tree outside the repository, and the two registered kinds validate through the registry validators"
  - "In scratch, an unseeded replace blocks both registered linguistics kinds; insert --sidecar linguistics and insert --sidecar linguistics.tokens.json with --source live scan seed them (dry-run first); a second insert is rejected as create-only; a seeded replace exits 0; and whether the round trip is byte-identical or only semantically equal is stated"
  - "A real linguistics.lexicon.json reproduces the silent deletion by replace and the validator-less refusal by insert; the single-collection live-scan case and the stray-story rejection are reproduced"
  - "project/design/sidecar-kinds-release-rule.md is updated: linguistics seeding moves from 'Not reproduced' to reproduced rows with commands, results and the spaCy and model versions, the inferred limits are revised, and the resolution states whether WS-SIDECAR-SAFE-PROMOTION exit criterion 1 is now met"
  - "No network is used, no real corpora/ or data/ is written, no code is changed, and lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - project/design/sidecar-kinds-release-rule.md (reproduction rows and revised limits)
---

# Work Item: WI-PROMOTE-0125

## Summary

Close the one open gap in `WS-SIDECAR-SAFE-PROMOTION` exit criterion 1: reproduce, with
real spaCy output, the release seeding of the two registered linguistics sidecar kinds
(`linguistics.json` and `linguistics.tokens.json`). The release rule written in
`WI-PROMOTE-0117` rests on the shared registry mechanism for these kinds, not on a
reproduction.

## Problem / Context

`WI-PROMOTE-0117` produced `project/design/sidecar-kinds-release-rule.md`. Its
"Not reproduced" section says linguistics seeding was never reproduced in a scratch
copy, because the registry's linguistics validators need a schema-valid payload (an
empty object fails) and generating one needs a spaCy run. The investigation could only
synthesize `{"segments": []}` for `scenes.json`. Three related items are also still
inferred, not reproduced: the single-collection behavior of `insert --source` (a source
tree containing only that collection), the rejection of a stray story with no
`story.json` in `data/` for the live-scan route, and the lexicon behavior with a real
file (only a synthetic `linguistics.lexicon.json` was used). `linguistics.lexicon.json`
is written by `lcats linguistics --include-lexicon` but is not a registered kind
(`WI-PROMOTE-0117`: `replace` deletes it silently; `insert` needs `--allow-unvalidated`).

The work is now cheap and local. Verified on 2026-10-25: spaCy 3.8.14 with the
`en_core_web_sm` model is installed in both the default environment and the `LCATS`
conda environment (no `md` or `lg` models). `lcats linguistics`
(`src/lcats/analysis/corpus/linguistics_cli.py`) supports `--backend spacy|stanza|fake`,
`--include-token-detail`, `--token-detail-version v1|v2`, `--include-lexicon` (requires
v2), `--existing skip|validate|overwrite`, `--output-root` and `--dry-run`, and writes
`linguistics.json` beside each `story.json` by default (`runner.py:517-518`). No network
is needed.

Prior art check:

- **Duplication search:** no existing reproduction of linguistics seeding; the rule note
  and `docs/reference/linguistics-sidecar.md` both state it is undefined or unreproduced.
- **Demand search:** the "Not reproduced" section of the rule note and the workstream's
  exit criterion 1 request exactly this.

Priority is framed around the 1.0 corpus release procedure being complete and safe, not
WorldCon timing.

## Scope

In a scratch tree outside the repository (never the real `corpora/` or `data/`), with
`PYTHONPATH` set to the checkout and the `LCATS` environment's Python (the default
editable install can point at another checkout):

1. Run `lcats linguistics --backend spacy` on at least three real stories copied from
   `corpora/` (include a `mass_quantities` story whose name contains `__` if it is cheap
   enough), first with token detail v1, then with v2 and `--include-lexicon`. Confirm the
   real outputs validate through the registry validators.
2. Reproduce the release scenario for both registered kinds: sidecars only in the scratch
   `corpora/`, regenerated stories only in the scratch `data/`. Unseeded `replace` blocks
   both kinds; `insert --sidecar linguistics` and `--sidecar linguistics.tokens.json` with
   `--source` live scan seed them (dry-run first); a second insert is rejected as
   create-only; a seeded `replace` then exits 0. State whether the round trip is
   byte-identical or only semantically equal (`insert` re-serializes with `indent=2`).
3. Repeat once with a real `linguistics.lexicon.json` to confirm the silent deletion and
   the validator-less refusal.
4. Reproduce the single-collection live-scan case and the stray-story rejection.
5. Record determinism: run spaCy twice on one story and compare the outputs, and record
   the spaCy and model versions.

## Required Changes

- Update `project/design/sidecar-kinds-release-rule.md`: move linguistics seeding from
  "Not reproduced" to reproduced reproduction rows with the commands and results, add
  the tool versions, and revise the limits that were inferred.
- State in the resolution whether workstream exit criterion 1 is now met.
- If a real payload exposes a validator or round-trip gap that contradicts the rule note,
  record it as a finding and stop for direction; do not change code.

## Non-Goals

- No code change, and no seeding wrapper.
- No registering of `linguistics.lexicon.json` or `science-fiction.json` (backlog).
- No network use, no edit to real `corpora/` or `data/`, no change to `replace` semantics.
- No archive of the scratch outputs beyond what the note's reproduction table records.

## Acceptance Criteria

- Real spaCy outputs are generated for at least three real stories and the two registered
  kinds validate through the registry validators, for token detail v1 and v2.
- Both registered kinds are seeded in scratch and a seeded `replace` exits 0, with the
  byte-identical or semantically-equal result stated; a second insert is rejected.
- The real-lexicon silent deletion, the single-collection case and the stray-story
  rejection are reproduced.
- The rule note is updated with commands, results and tool versions, and the resolution
  states whether exit criterion 1 is met.
- No network, no real corpora/data writes, no code change; `lrh validate` reports 0 errors.

## Validation

- lrh validate
- git diff --stat main
- grep -n "Not reproduced" project/design/sidecar-kinds-release-rule.md
- python -c "import spacy; print(spacy.__version__)"

## Risk Notes

A real linguistics payload could expose a validator or round-trip gap; that is a finding,
not a failure, and stops the run for direction if it contradicts the rule note. spaCy
output may not be byte-reproducible across versions, so record the versions. The run is
small and free. Keep every scratch tree outside the repository, and confirm that no real
`corpora/` or `data/` file changed (`git status`) before committing.
