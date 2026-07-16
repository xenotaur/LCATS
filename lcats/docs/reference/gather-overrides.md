# Per-story gather-time overrides

Some corpus defects are judgment calls that the measured repair rules in
`lcats/analysis/corpus/repairs.py` cannot safely cover. For example
`Ângstrom` — a stray `Â` (U+00C2) a human reads as `Ångstrom` — is not a clean
encoding-family decode, so it is deliberately *not* a repair rule. Per-story
overrides let such fixes live as versioned repo inputs that the gather-time
normalization hook applies **after** the rule pass.

Like the rule table, overrides are replayable inputs to regeneration, not edits
to stored files: because `data/` is cleared and regenerated after major changes,
a one-off edit to a story JSON would be wiped on the next run. Overrides live
under the package (`lcats/gatherers/overrides/`), never under `data/`, so
regeneration and story discovery never touch or wipe them.

## File layout

One JSON file per collection:

```
lcats/gatherers/overrides/<collection>.json
```

where `<collection>` is the collection / target-directory name, e.g.
`mass_quantities`. A collection with no overrides simply has no file.

## Schema

```json
{
  "<story_id>": [
    {
      "find": "<exact substring, with enough context to be unique>",
      "replace": "<replacement text>",
      "rationale": "<why this is a judgment call, not a rule>",
      "reviewer": "<who decided>"
    }
  ]
}
```

- `story_id` is the story's filename stem (e.g. `f_o_b_venus__bond`).
- `find` is a literal substring match, not a regex. Include enough surrounding
  context that it is unique within the story — a bare single character will
  misfire.
- Each applied entry is recorded in the story's
  `metadata.normalization.overrides_applied`, alongside `rules_applied`, for
  provenance.

## Behavior

- Overrides are applied by `lcats.gatherers.normalization.normalize_story_dict`
  when it is called with both `collection` and `story_id` (the two gather write
  paths pass these). They run after rule-based repairs, so an override sees
  already-rule-normalized text.
- An entry is **skipped with a warning** — never silently — when its `find` is
  empty, equals its `replace` (a no-op that would otherwise stamp provenance
  onto an unchanged body), or is absent from the body. A stale override usually
  means the story text changed and the entry needs re-review.
- Per-collection override files are parsed once and cached for the process
  lifetime (they are versioned, effectively immutable during a run).
- Application is deterministic and idempotent in the sense that regenerating
  from the same cached source produces identical output.

## Populating overrides

This mechanism (WI-OVERRIDES-0018) ships with one canonical seed entry
(`Ângstrom` in `f_o_b_venus__bond`). Systematic population from human review of
residual defects is handled by WI-RESIDUAL-0019.
