---
execution_id: 2026_09_23_17_46_08_DOC_GENRE_SIDECAR_MANIFEST_FIELDS
prompt_id: PROMPT(AD_HOC:DOC_GENRE_SIDECAR_MANIFEST_FIELDS)[2026-09-23T17:45:05+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/443
commit: 13f43730
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/443
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
created_at: 2026-09-23T17:46:08+00:00
---

# Summary

Documents a gotcha found while dogfooding `lcats promote insert`/`upsert`
against real data: a hand-built `--tranche-manifest` `genre.json` payload
is rejected unless it carries its own top-level `lcats_id` and
`story_path` fields, separate from the envelope's routing `lcats_id`.

# Result

- Added a sentence to `docs/reference/corpus-promotion.md`'s
  `insert`/`upsert` section documenting this per-kind payload
  requirement, right after the existing registry-validation bullet.
- No code change. No work item filed -- this is a pure documentation fix
  discovered during dogfooding, per direct user instruction to fold it
  into the doc edit rather than file a separate WI.

# Validation

- `lrh validate`: 0 errors.

# Follow-up

- None.
