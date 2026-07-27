---
execution_id: 2026_07_27_03_18_44_WI_EVENT_0030_STRICT_TOOL_SCHEMAS
prompt_id: PROMPT(AD_HOC:WI_EVENT_0030_STRICT_TOOL_SCHEMAS)[2026-07-27T03:18:35-04:00]
work_item: AD_HOC
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/168
commit: 2771fcd5
agent: claude_app
instruction_source: chat session (real Step-4 run, second crash after PR #167 landed)
session_transcript: pending
created_at: 2026-07-27T03:18:44-04:00
---

# Summary

A real pilot run crashed again, this time during the ERW pipeline stage:
`AttributeError: 'str' object has no attribute 'get'` in
`relation_extractor.build_relations()` at
`evidence = cursor.resolve(raw.get("quote", ""), segment_text)`. The
model returned a plain string as one item of the `relations` array
instead of the required object, and `build_relations()` has no defensive
type check.

# Result

Root-caused via Anthropic's own documentation: by default, tool use does
not guarantee the model's `tool_use` input strictly matches the declared
`input_schema` - "Claude might return incompatible types ... or omit
required fields, breaking your functions and causing runtime errors"
(Strict tool use docs). Schema conformance is only *guaranteed* when
`strict: true` is set on the tool definition, which none of the 5
Event-Role-World tool schemas (entity/event/relation/discourse/
story_relation) do. `strict: true` additionally requires
`additionalProperties: false` on every object in the schema, including
nested ones inside array items (JSON Schema limitations docs) - none of
these schemas set that either.

Cannot edit the schemas' own modules
(`lcats/analysis/event_role_world/*.py`) directly - forbidden by this
work item's `forbidden_actions: modify_event_role_world_extractor`, the
same constraint that shaped `_build_erw_extractors()`'s existing
`default_model` override. Applied the identical pattern for schemas:
added `_close_schema_objects()` (recursively adds
`additionalProperties: false` to every object, top-level and nested) and
`_strict_tool_schema()` (applies that closure, then sets `strict: true`)
to `run_pilot.py`, and call it on each extractor's `.tool_schema` in
`_build_erw_extractors()` right after the existing `default_model`
override - a deep copy assigned to the extractor instance, leaving each
module's own `*_TOOL_SCHEMA` constant untouched.

Confirmed the fix actually reaches the API: `AnthropicBackend.complete()`
forwards the whole tool dict verbatim as `tools=[tool]`, so the injected
`strict`/`additionalProperties` keys pass through unmodified.
`OpenAIBackend.complete()` explicitly picks only `name`/`description`/
`input_schema` when building its own function-call dict, so this change
has no effect (and no risk of breaking anything) for `--backend openai`.

Did not touch `scene_analysis.make_segment_extractor` (the Stage-1
segmentation extractor that crashed in the *previous* PR #167 fix) -
that extractor does not use `tool_schema=` at all (plain JSON-in-text
parsing instead), so strict tool use doesn't apply to it.

# Validation

- `scripts/format --check --diff` / `scripts/lint` - clean.
- `scripts/test` - 1439 tests pass (no regressions; no new test file added
  since `experiments/03_cross_segment_relation_pilot/` has no existing
  test suite of its own, consistent with the rest of this pilot script).
- `lrh validate` - 0 errors, 43 pre-existing unrelated warnings.
- Manual check: `_strict_tool_schema()` applied to the real
  `RELATION_TOOL_SCHEMA` produces `additionalProperties: false` at both
  the top-level `input_schema` and the nested `relations` array's item
  object, plus `strict: true` alongside `name`/`description` - matching
  Anthropic's own documented example shape exactly.
- Manual check: confirmed the original module-level `RELATION_TOOL_SCHEMA`
  dict is unmodified after calling `_strict_tool_schema()` on it (deep
  copy, not in-place mutation).
- Ran `--dry-run --sample-size 1 --data-dir corpora` end to end - all 4
  genres complete with 0 exclusions, no regression to existing control
  flow (FakeBackend ignores `tool=` entirely, so this only verifies
  `_build_erw_extractors()` and the rest of the pipeline still run
  cleanly with the new schema-copy step in place).

# Follow-up

- `session_transcript: pending` should be updated to `claude-app:<session-id>`
  after this session ends.
- This does not eliminate every possible crash from a malformed tool
  result (strict mode is Anthropic-specific and this pilot also supports
  `--backend openai`), but it addresses the actual, reproduced failure
  mode using the mechanism Anthropic's own docs recommend for exactly
  this class of bug.
- Worth raising outside this work item's scope: the ERW extractor
  modules' own tool schemas (`entity_extractor.py`,
  `event_extractor.py`, etc.) could set `strict: true` +
  `additionalProperties: false` permanently at the source, benefiting
  every caller, not just this pilot script's runtime override - out of
  scope here due to `forbidden_actions: modify_event_role_world_extractor`.
- The user's real run is still not complete - Steps 5-7 (results
  write-up, WI-EVENT-0030 closeout) still need a clean re-run after this
  lands.
