---
id: WI-PILOT-0057
title: Evaluate Anthropic prompt caching against the WI-PILOT-0051 fixture set
type: evaluation
status: resolved
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams:
  - WS-PILOT-COST-SUSTAINABILITY
related_design:
  - lcats/project/design/proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md
depends_on:
  - WI-PILOT-0051
blocked_by: []
blocked: false
blocked_reason: null
resolution: "Implemented and merged in PR #282 (commit f9795838e77b7232b59ffe43ce3dc92ced00da66): real Anthropic prompt-caching measurement completed and Decision 3 updated with measured go recommendation."
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - run_real_llm_calls_without_explicit_approval
  - default_enable_prompt_caching
  - implement_mid_conversation_tool_changes
acceptance:
  - AnthropicBackend gains an opt-in cache_control mechanism scoped to the tools+system prefix (per Decision 3's "narrower opportunity" framing - not the per-segment segment_text, which can never be a stable cache prefix under the current per-call-different-tool-schema shape) - off by default
  - BackendResponse surfaces cache_creation_input_tokens/cache_read_input_tokens from message.usage (currently absent from the return path) so cache hits/misses are actually measurable, not assumed
  - A bounded, explicitly-approved real measurement run against WI-PILOT-0051's fixture set, preserving the harness's real production call ordering and timing (not an artificially same-extractor-grouped sequence), reports the observed cache_creation_input_tokens/cache_read_input_tokens for each call - including a genuine zero, if the tools+system prefix falls below Anthropic's minimum cacheable-prefix length - alongside a real measured cost delta versus caching disabled
  - A written go/no-go conclusion updates Decision 3 of the adopted proposal with the real measured numbers - "no real benefit" is a valid, complete outcome for this item, not a failure
  - Caching remains off by default in AnthropicBackend regardless of the evaluation's conclusion - adoption as the default is a separate follow-on decision, not silently flipped on as part of this evaluation
  - lrh validate and scripts/test both report 0 errors/failures
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/src/lcats/llm/anthropic_backend.py
  - lcats/src/lcats/llm/backend.py
  - lcats/project/design/proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md
---

## Summary

Measure the real, narrower prompt-caching opportunity Decision 3 of
`PROP-LCATS-PILOT-COST-SUSTAINABILITY` identifies - caching the stable
`tools`+`system` prefix within one extractor type, reused across
segments/stories - against `WI-PILOT-0051`'s fixture set, and record a
go/no-go conclusion with real numbers. This is WI 2 of
`WS-PILOT-COST-SUSTAINABILITY`'s Implementation Plan, gated on WI 1's
harness (now resolved, PR #244).

## Problem / Context

The proposal's Decision 3 originally assumed adopting prompt caching
would let 3 of the pipeline's 4 per-segment extractor calls
(entity/event/relation/discourse) hit cache reads on the shared
`segment_text`. That assumption does not hold: Anthropic's prompt-caching
docs define cache prefixes in strict hierarchical order (`tools` →
`system` → `messages`), and changing tool definitions invalidates the
entire cache. `AnthropicBackend.complete`
(`lcats/src/lcats/llm/anthropic_backend.py:53-124`) sends a single,
different `tool` per call (`entity_extractor.py:16`,
`event_extractor.py:17`, confirmed distinct per extractor), so the 4
per-segment calls can never share a cache hit with each other regardless
of how identical their `segment_text` is.

The real, narrower opportunity Decision 3 identifies instead: caching the
comparatively small, stable `tools`+`system` prefix *within one extractor
type*, reused across every call of that same extractor across different
segments and different stories in a run - not the large `segment_text`,
which varies every call and is never a stable prefix under this
pipeline's current call shape. This is a real but unmeasured saving.
Decision 3 explicitly defers measuring it to "a follow-on work item" -
this is that item.

### Duplication search
- In-repo: No existing prompt-caching implementation or measurement
  anywhere in `lcats/src/lcats/llm/`. Confirmed via
  `grep -rn "cache_control" lcats/src/lcats/` - zero matches.
- Sibling repos: None identified.
- External libraries: None - this evaluates Anthropic's own SDK-native
  `cache_control` feature (confirmed present in the installed
  `anthropic==0.113.0`: `anthropic.types.CacheControlEphemeralParam`,
  and `message.usage.cache_creation_input_tokens`/
  `.cache_read_input_tokens` are real fields on
  `anthropic.types.usage.Usage`), not a new dependency.
- Recommendation: Proceed.

### Demand search
- Work items: `WI-PILOT-0051` (resolved) is this item's direct
  prerequisite per `depends_on`; no other matching work item found.
- Proposals: `PROP-LCATS-PILOT-COST-SUSTAINABILITY` (adopted) requests
  this exact item as WI 2 of its Implementation Plan, explicitly gated
  on WI 1.
- Workstreams: `WS-PILOT-COST-SUSTAINABILITY` lists this as WI 2 in its
  `## Work Items` section.
- Backlog: No matching entries in `project/design/backlog.md`.
- Recommendation: Proceed.

## Scope

- Add an opt-in `cache_control: {"type": "ephemeral"}` mechanism to
  `AnthropicBackend`, applied to the `tools`+`system` prefix only (not
  `messages`/`segment_text`), disabled by default.
- Extend `BackendResponse` (`lcats/src/lcats/llm/backend.py`) to carry
  `cache_creation_input_tokens`/`cache_read_input_tokens`, populated from
  `message.usage` when the Anthropic SDK returns them (they are
  `Optional[int]` on the SDK's `Usage` type - absent/`None` when caching
  isn't in use, so downstream consumers must handle that case).
- Preflight the actual token count of the `tools`+`system` prefix for
  each extractor before spending anything, since a prefix below
  Anthropic's minimum cacheable-prefix length makes zero cache reads the
  *correct*, expected result, not a signal to retry.
- Run a bounded, explicitly-approved real measurement, with caching
  enabled and disabled, that preserves the targeted harness's real
  production call ordering and timing - `processor.py:124-220`
  interleaves entity/event/relation/discourse calls per segment, and the
  5-minute cache TTL can expire between same-extractor calls under that
  real interleaving, so grouping same-extractor calls back-to-back would
  measure a hit rate the real pipeline never sees and overstate the
  cost conclusion. Report the real measured `$` delta and observed
  cache-token values (including zero) versus caching disabled on the
  same fixture set, in the same call order.
- Update Decision 3 of `PROP-LCATS-PILOT-COST-SUSTAINABILITY`'s
  `00_proposal.md` with the real measured numbers and a go/no-go
  recommendation.

## Required Changes

1. Add an opt-in caching flag to `AnthropicBackend.__init__` (e.g.
   `enable_prompt_caching: bool = False`), and when enabled, attach
   `cache_control: {"type": "ephemeral"}` to the `tools` list entry
   and/or `system` field in `complete()`'s request construction
   (`anthropic_backend.py:53-74`) - per Decision 3's scoping, not to
   `messages`.
2. Extend `backend.BackendResponse` with
   `cache_creation_input_tokens: Optional[int] = None` and
   `cache_read_input_tokens: Optional[int] = None` fields, populated
   from `usage.cache_creation_input_tokens`/`usage.cache_read_input_tokens`
   in `complete()`'s return construction (`anthropic_backend.py:118-124`).
3. Preflight the `tools`+`system` prefix token count for each extractor
   (e.g. via the Anthropic SDK's token-counting endpoint, or an
   equivalent local estimate) before any real call, and record it
   alongside the measurement results - this determines whether a zero
   `cache_read_input_tokens` result is expected (prefix below the
   cacheable minimum) or a genuine cache miss worth investigating.
4. Add a small, explicitly-gated measurement script or test under
   `experiments/03_cross_segment_relation_pilot/` (or a new location if
   more appropriate) that makes a bounded number of real paid calls
   against `WI-PILOT-0051`'s fixture set, with caching both enabled and
   disabled, **preserving the fixture set's real per-segment call
   ordering and timing as the harness itself produces it** - not an
   artificial same-extractor-grouped sequence - and reports the observed
   cache-token values (including zero) and real cost delta for each
   trial. **This step requires a separate, explicit human confirmation
   before any real API call is made** - it is not covered by this work
   item's own chain-authorization gate, matching this project's
   dry-run/real-spend discipline for anything not already
   fake-backend-verifiable.
5. Update Decision 3 in
   `lcats/project/design/proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md`
   with the real measured numbers from step 4 and a clear go/no-go
   recommendation for defaulting `enable_prompt_caching` on.

## Non-Goals

- Does not default `enable_prompt_caching` to `True` in
  `AnthropicBackend` - opt-in only for this item, regardless of the
  evaluation's conclusion. Adopting it as the default (if the evaluation
  recommends it) is a separate follow-on decision/work item.
- Does not implement Anthropic's mid-conversation tool-changes beta -
  Decision 3 notes it as a genuinely relevant but bigger alternative
  (would require restructuring the 4 independent per-segment calls into
  one multi-turn conversation); out of scope here.
- Does not merge or redesign the entity/event/relation/discourse
  extraction sequence (Decision 6, rejected in the proposal).
- Does not evaluate the Batch API or per-stage model tiering (WI 3/4 of
  this workstream) - separate, sequenced items.
- Does not change `run_pilot.py`'s own targeted-run harness
  (`WI-PILOT-0051`) beyond using its fixture set as the measurement
  target.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- `scripts/version tools`
- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- A bounded, explicitly-approved real measurement run against the
  WI-PILOT-0051 fixture set (not a fake-backend run - see Risk Notes)

## Risk Notes

- Unlike most items in this workstream, this evaluation's core
  measurement genuinely cannot be done with a fake backend - cache
  read/write behavior is a real property of Anthropic's live API, not
  something a fake backend can simulate meaningfully. The real-call step
  must be small, bounded to the fixture set (not a full corpus run), and
  gated behind its own explicit human approval separate from this item's
  chain-authorization gate.
- `cache_creation_input_tokens`/`cache_read_input_tokens` are
  `Optional[int]` on the Anthropic SDK's `Usage` type - code consuming
  `BackendResponse`'s new fields must handle `None` (caching not in use
  or not supported for this call), not assume they're always populated.
- A measured "no real benefit" result is a valid, complete outcome for
  this item, per the workstream's own exit criteria ("adopt or reject,
  with real numbers... none is a foregone commitment") - do not treat a
  negative result as a reason to keep iterating past a clear measurement.
- The 5-minute default cache TTL (`ttl: "5m"` on
  `CacheControlEphemeralParam`, extendable to `"1h"`) means measurement
  timing matters - calls spaced too far apart will show false negatives
  (cache expired, not "caching doesn't work"). This is exactly why the
  measurement must preserve the real pipeline's interleaved call order
  (`processor.py:124-220`) rather than grouping same-extractor calls
  together - grouping would keep same-extractor calls closer in time
  than production ever does, artificially inflating the observed hit
  rate (review finding, PR #247).
- A short `tools`+`system` prefix can fall below Anthropic's minimum
  cacheable-prefix length, in which case zero `cache_creation_input_tokens`/
  `cache_read_input_tokens` is the *correct* result for every call, not
  a failed measurement - do not retry calls to try to manufacture a
  nonzero reading (review finding, PR #247). Preflighting the actual
  prefix token count before spending (Required Change 3) is what
  distinguishes this expected case from a genuine cache miss.

## Dependencies / Order

Depends on `WI-PILOT-0051` (resolved, PR #244) - this item cannot start
its real measurement step until the targeted test harness and fixture
set exist. WI 3 (Batch API evaluation) and WI 4 (model-tiering
evaluation) may proceed independently of this item's outcome, per the
workstream's Open Questions (no strict inter-evaluation ordering beyond
both depending on WI 1).

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-PILOT-COST-SUSTAINABILITY.md`
- Design: `project/design/proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md`
