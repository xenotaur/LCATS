# Cross-segment causal relation extraction: need and design evaluation

Date: 2026-07-25
Work item: WI-EVENT-0028 (investigation)
Scope: recommendation only — implements no architecture, adds no code.

## Purpose

`WI-EVENT-0026` implemented the Event-Role-World extractor's stage 6
(relation pass) as a per-segment `tool=` call: `relation_extractor.py` only
ever receives its own segment's event IDs, so a relation's source/target
event can never actually reference a different segment's event.
`schema.reconcile_story_annotations` (also WI-EVENT-0026) qualifies every
relation for safe story-scoped representation but does not, and cannot,
discover a genuinely cross-segment causal link — this is documented as a
"Known limitation" on `schema.StoryWorldAnnotation`'s docstring.

This document determines whether the Worldcon "Shape of Science Fiction"
paper's analysis actually needs cross-segment causal relations, and if so,
evaluates candidate architectures for giving stage 6 broader context.

## Does the paper need this?

### The candidate metric itself does not require it

The governing proposal's "Candidate paper-facing metrics" section
(`00_proposal.md`) lists "causal and explanatory link density" as a simple
per-1,000-words count. A count metric is agnostic to whether a relation's
two endpoints live in the same segment or different ones — as long as the
same chunking-and-scope methodology is applied uniformly across every
genre being compared, a per-segment-only count remains a internally
consistent relative measure. This alone does not establish need.

### The proposal's resulting scientific claim is the actual concern

The proposal's "Resulting scientific claim" section hypothesizes that
science fiction shows "denser **mechanistic** causal links" than mystery,
romance, and adventure. This is not a generic causality claim — it is
specifically about *mechanistic* (technological/scientific) causal chains,
which plausibly play out over a longer narrative arc than other genres'
more immediate, scene-local cause-effect (e.g., a technology or discovery
introduced early in a story causing consequences many scenes later, versus
a romance's cause and effect typically resolving within the same scene or
its immediate sequel). If that asymmetry is real, per-segment-only
counting would systematically *undercount* SF's causal density
specifically — not uniformly across genres — which directly threatens the
validity of the comparison the paper exists to make.

The proposal's own schema sketch also lists "cross-segment relations" as
expected `StoryWorldAnnotation` content (`00_proposal.md`, Core schema
sketch section), suggesting the original design anticipated this need,
even though the specific candidate-metrics list does not spell it out.

### Determination: qualified yes, pending a cheap empirical check

This is a real, non-speculative validity concern — but it is also
exactly the kind of assumption the proposal itself warns against: "The
extractor must be designed to test this claim, not assume it." Committing
to a bigger architecture change on the strength of a plausible-sounding
asymmetry, without checking whether it actually holds in this corpus,
would repeat the same mistake in miniature.

**Recommendation: run a cheap empirical pilot before building anything.**
Take a small stratified sample (e.g., 5-10 stories each from the SF corpus
and from the mystery/romance/adventure comparison genres already used
elsewhere in this proposal), and for each, manually or semi-automatically
check how often an event's plausible cause or effect appears more than one
segment away versus within the same or an adjacent segment. If SF shows
materially more long-range causal chains than the comparison genres, the
undercounting risk is real and an architecture from below should be built.
If the rates are comparable across genres, per-segment relations remain
sufficient — the current implementation needs no change, and this is a
complete, valid outcome, not a failure to find a need.

This document does not run that pilot — it is a follow-up step for
whoever picks this up next, sized to be quick relative to building any of
the architectures below.

## Candidate architectures (if the pilot confirms need)

### A. Post-reconciliation story-level relation pass (recommended)

Run one additional LLM call (or a small, bounded number for very long
stories — see caveat below) per story, *after* `reconcile_story_annotations`
has produced global entity IDs and the full list of segment-qualified
events, asking the model to identify causal/enabling/preventing/temporal/
motivational/explanatory links between events that live in *different*
segments (same-segment links are already covered by the existing stage-6a
pass and would be excluded from this pass's scope to avoid double-counting).

- **Cost/latency:** cheapest of the three options — a small, fixed number
  of additional calls per *story*, not per segment, regardless of segment
  count.
- **Implementation complexity:** moderate. Requires building a compact
  representation of every story-level event (predicate, event type, its
  segment ID, and its already-resolved `EvidenceSpan`) to pass as context,
  and a new tool schema for cross-segment relations. Crucially, this
  approach can **reuse each event's already-resolved evidence span as one
  endpoint's evidence** rather than requiring a fresh quote search across a
  multi-segment text blob — the hardest grounding problem in any
  cross-segment design is sidestepped almost entirely.
- **Accuracy risk:** the model reasons over event summaries rather than
  full original text for events outside the immediate story-level prompt,
  which is a real limitation, but the same `EventRelation.certainty` field
  already implemented (`explicit`/`strongly_implied`/`weakly_inferred`)
  applies unchanged here — no new schema field is needed to keep speculative
  cross-segment links separately partitioned, exactly as WI-EVENT-0026
  already does for same-segment ones.
- **Caveat:** for very long stories (novels), the full global event list
  may exceed one LLM call's context window even in compact form. A simple
  mitigation is to cap the pass to salient/high-confidence events only, or
  to window the pass hierarchically (e.g., chapter-level first, then a
  final story-level pass over chapter-level relation summaries) — this
  adds complexity proportional to corpus length and should be scoped in
  the follow-up implementation work item once story-length distributions
  in the actual corpus are checked.

### B. Growing per-story event index fed into the existing per-segment pass

Keep the current per-segment call shape, but accumulate a compact index of
prior segments' events (predicate, event type, short quote) as
`process_segments` iterates through a story in order, and pass that index
into each subsequent segment's stage-6 call alongside its own event IDs.

- **Cost/latency:** call count is unchanged (still per segment), but each
  call's prompt grows as the story progresses — early segments stay cheap,
  later segments' prompts grow with story length. For long stories this
  can approach or exceed option A's total added cost, spread across many
  smaller increments rather than one lump sum.
- **Implementation complexity:** moderate-to-high. `processor.py`'s
  per-segment loop currently has no story-level accumulator; this would
  need one, plus changes to `relation_extractor.py`'s prompt template and
  `_extract_with_placeholders` to carry a growing index rather than a
  fixed value.
- **Accuracy risk:** better than option A for evidence grounding on the
  *current* segment (full original text is still available for it), but
  claimed links to earlier events rely on the same compact-index summaries
  as option A, so the improvement is partial.
- **Assessment:** roughly comparable total cost to option A for long
  stories, with more implementation disruption to the existing per-segment
  loop, for a marginal grounding improvement. Not recommended over A unless
  a future need for incremental/streaming processing (not currently a
  requirement) makes this shape preferable.

### C. Widen the per-segment extraction window to include neighboring segments

Reuse the existing per-segment call shape unchanged, but pass the current
segment's text plus a fixed number of neighboring segments (e.g., ±1) as
context, letting the model find relations across that local window.

- **Cost/latency:** proportional increase in per-call token cost (a
  window of 3 segments roughly triples per-call input tokens), but no
  increase in call count.
- **Implementation complexity:** lowest of the three — no new schema, no
  new tool, just a change to which text slice is passed into the existing
  call.
- **Accuracy risk:** lowest of the three, since full original text is
  available for the entire window (no compact-summary grounding gap).
- **Assessment:** cheapest and simplest, but only catches *local* cross-
  segment links within the fixed window. This does not address the
  specific phenomenon this investigation is concerned with — a
  technology's consequences unfolding many scenes later, potentially well
  beyond any practical fixed window size. **Not recommended as the primary
  fix**, though it could serve as an interim, low-cost partial mitigation
  if the pilot in the previous section shows most cross-segment causal
  links are short-range (within a few segments) rather than long-range.

## Recommendation

If the empirical pilot confirms SF shows materially more long-range causal
chains than the comparison genres: build **option A** (post-reconciliation
story-level relation pass). It targets the actual phenomenon of concern,
is the cheapest of the three at scale, and reuses already-resolved evidence
spans rather than requiring new text-search machinery across segment
boundaries.

If the pilot instead shows most cross-segment links are short-range: option
C (widened window) is a reasonable, much cheaper partial fix, and building
the full option A may not be justified by the marginal accuracy gain.

If the pilot shows no material genre difference in cross-segment causal
chain prevalence: no architecture change is needed. Per-segment relations
(as already implemented in WI-EVENT-0026) remain sufficient, and this is a
complete, valid conclusion — not a gap.

**Rationale in one line:** the proposal's own resulting-claim language
(SF's causal links being specifically *mechanistic* and plausibly
long-range) is a real, non-speculative validity concern for a simple
per-segment count, but the proposal's own methodological standard ("test
the claim, don't assume it") means that concern should be checked cheaply
before any architecture is built, not assumed and built against.

## Sketch if a follow-up implementation work item is created

Not applicable until the empirical pilot above determines need and, if
needed, which architecture. If option A is eventually approved, the
concrete additions would be: a new `relation_extractor.py` function (or a
second tool schema in the same module) for the story-level pass, a new
`PassUsage` entry (e.g. `"story_relation"`) so its cost is visible per the
existing cost/baseline reporting pattern, and extending
`reconcile_story_annotations`'s output to include these newly-discovered
relations alongside the qualified same-segment ones already there. No
changes to `schema.EventRelation` itself would be required — the existing
fields (including `certainty`) already fit this use case.
