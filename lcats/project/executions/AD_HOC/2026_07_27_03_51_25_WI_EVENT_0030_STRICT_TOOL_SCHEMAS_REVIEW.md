---
execution_id: 2026_07_27_03_51_25_WI_EVENT_0030_STRICT_TOOL_SCHEMAS_REVIEW
prompt_id: PROMPT(AD_HOC:WI_EVENT_0030_STRICT_TOOL_SCHEMAS_REVIEW)[2026-07-27T03:50:59-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_07_27_03_18_44_WI_EVENT_0030_STRICT_TOOL_SCHEMAS
pr: https://github.com/xenotaur/LCATS/pull/168
commit: 98dcd6cf
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/168
session_transcript: pending
created_at: 2026-07-27T03:51:25-04:00
---

# Summary

Address PR #168 review feedback: two copilot-pull-request-reviewer
comments, both real correctness gaps in the strict-schema override logic
itself.

# Result

- **`_close_schema_objects()` used `setdefault` for `additionalProperties`,
  and only matched a bare `type: "object"` string.** A pre-existing looser
  value (e.g. `additionalProperties: true`) would have silently survived,
  defeating the exact requirement strict mode depends on; a union type
  like `type: ["object", "null"]` would also have been missed. Fixed to
  set `additionalProperties` unconditionally, and to detect "object"
  inside a type list as well as a bare string. None of the 5 real ERW
  schemas currently trigger either case, but the fix closes a latent gap
  rather than relying on that being permanently true.
- **The PR's own write-up claimed the strict-schema override was a no-op
  for `--backend openai`, which was wrong.** `AnthropicBackend.complete()`
  does forward the tool dict verbatim (so an added top-level `strict` key
  is inert unless read), but `OpenAIBackend.complete()` forwards
  `tool["input_schema"]` directly as its function `parameters` - the
  `additionalProperties: false` this same code injects into `input_schema`
  would have reached OpenAI's schema too, an untested and unintended
  behavior change. Rather than just correcting the prose, gated the whole
  override to `backend_name == "anthropic"` in `_build_erw_extractors()`
  (now takes a `backend_name` parameter, threaded from `main()`'s
  `args.backend`), removing the risk entirely instead of merely
  documenting it.

# Validation

- `scripts/format --check --diff` / `scripts/lint` - clean (black
  reformatted one function signature; re-verified clean after).
- `scripts/test` - 1439 tests pass, no regressions.
- `lrh validate` - 0 errors, 43 pre-existing unrelated warnings.
- Manual checks: union-type schema (`type: ["object", "null"]`) now
  closes correctly; a schema with pre-existing `additionalProperties: true`
  is now forced to `False`; `--backend openai` extractors are confirmed to
  have neither `strict` nor `additionalProperties` injected, while
  `--backend anthropic` extractors still get both; the module-level
  `RELATION_TOOL_SCHEMA` constant remains unmutated after building
  extractors for both backends.
- Re-ran `--dry-run --sample-size 1 --data-dir corpora` end to end after
  the fix - still completes cleanly, 0 exclusions.

# Follow-up

- `session_transcript: pending` should be updated to `claude-app:<session-id>`
  after this session ends.
- Proceed to `/lrh-confirm-fixes https://github.com/xenotaur/LCATS/pull/168`
  to verify fixes against the current diff and resolve review threads, then
  the merge gate, then closeout.
