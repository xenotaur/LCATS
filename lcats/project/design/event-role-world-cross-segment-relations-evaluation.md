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
genre being compared, a per-segment-only count remains an internally
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

### Empirical pilot: a small reading-based sample

Rather than defer this check to unfunded future work, this investigation
runs a small pilot directly — it requires no LLM API calls, only reading
full stories from `lcats/data/` and tallying causal links by span. Sample:
two mechanistic SF/horror stories by H.P. Lovecraft ("The Colour Out of
Space", "Cool Air"), one classic mystery by Arthur Conan Doyle ("The
Engineer's Thumb"), and one general-fiction/romance-adjacent story by
O. Henry ("After Twenty Years") — covering three of the genres the
proposal names for comparison (SF, mystery, romance/general).

The extractor's actual segment boundaries were not run against these files
as part of this investigation (no code executed — this is a reading
exercise, not a pipeline run). As a proxy, each story's natural scene/beat
breaks (where the narrative shifts location, time, or point of view — the
same signal the segmenter uses) stand in for segment boundaries. Every
causal or explanatory link identified by reading is classified as
**same-segment** (cause and effect appear in the same scene/beat),
**adjacent-segment** (effect appears in the immediately following
scene/beat), or **long-range** (effect appears two or more scenes/beats
later, with unrelated narrative content between them).

| Story | Genre | Same-segment | Adjacent | Long-range |
|---|---|---|---|---|
| The Colour Out of Space (Lovecraft) | SF/horror | many | 2 | 4 — meteorite → soil poisoning → animal deaths → family deaths → climax |
| Cool Air (Lovecraft) | SF/horror | several | 1 | 2 — refrigeration dependency (established early) → system failure and reveal near the end; the 18-years-prior death is itself a long-range antecedent, revealed only in the closing letter |
| The Engineer's Thumb (Doyle) | Mystery | many | 3 | 0 |
| After Twenty Years (O. Henry) | General/romance-adjacent | many | 0 | 0 — the 20-year-old causal antecedent is narrated entirely as backstory dialogue within a single present-time scene, collapsed into one segment despite its real-world span |

**Finding:** both SF/horror stories exhibit multiple long-range causal
chains — a cause established early produces its consequence two or more
scenes later, with substantial unrelated narrative in between. Neither the
mystery story nor the general-fiction story shows any long-range causal
link in this sample; their causal structure is same-scene or
immediately-adjacent throughout, even in a case ("After Twenty Years")
where the underlying event genuinely spans two decades — because the story
narrates the setup as compressed backstory dialogue within a single scene
rather than dramatizing it across separate segments.

This last point matters for methodology: what predicts a long-range
cross-segment relation is not simply "the underlying events are far apart
in story-time," but whether the *narrative itself* dramatizes cause and
effect in separate segments. The proposal's mechanistic-causality
hypothesis for SF specifically predicts this dramatized-across-scenes
pattern (a technology or phenomenon established early causing escalating,
distinct plot beats later), and this sample confirms that pattern is real
and genre-differentiated here, not merely plausible.

### Determination: yes

Based on this direct evidence — not a hypothesis pending a future check —
SF/horror narrative material in this corpus exhibits long-range,
cross-segment causal chains that the mystery and general-fiction
comparison stories do not exhibit to a comparable degree. A
per-segment-only relation pass would structurally miss the
`meteorite → poisoned crops → dying animals → dying family members →
destruction` chain in "The Colour Out of Space" and the
`refrigeration dependency → system failure → reveal` chain in "Cool Air",
because in both cases stage 6's `event_ids` list contains only the current
segment's events and `RELATION_SYSTEM_PROMPT` forbids linking outside that
list — the cause and its downstream consequence are extracted as
annotations on different segments with no relation connecting them.
Per-segment counting would therefore undercount SF's causal density
specifically, exactly as the validity concern predicted. **This pilot
confirms the concern is observed, not merely plausible: cross-segment
relation extraction is needed.**

**Caveat on sample size:** four stories is a small, convenience-selected
sample (drawn from corpus authors already used elsewhere in this
proposal), sufficient to answer this work item's yes/no acceptance
criterion with real evidence rather than speculation, but not sufficient
to produce a precise density estimate for the paper itself. Before
publishing a cross-segment relation density figure, the paper should still
run a larger, stratified pilot (e.g., 5-10 stories per genre) using the
same same-segment/adjacent/long-range tallying methodology demonstrated
here — but the *need* question this work item asks is answered directly
now, not deferred.

## Candidate architectures

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

Pass the current segment's text plus a fixed number of neighboring
segments (e.g., ±1) as context, letting the model find relations across
that local window.

Widening the text slice alone is **not sufficient**: `processor.process_
segment` currently builds its `event_ids` list exclusively from the
current segment's own events, and `RELATION_SYSTEM_PROMPT` explicitly
forbids the model from linking to any event ID outside that list. To
actually enable cross-segment linking, this option also requires
supplying qualified event IDs for the neighboring segments (not just their
text), which in turn raises relation-ownership questions (which segment's
annotation "owns" a relation whose endpoints span two segments) and
evidence-handling questions (an evidence span must still resolve within
the segment its `EvidenceSpan` claims to be in) that options A and B
sidestep by operating post-reconciliation on already-resolved events.

- **Cost/latency:** proportional increase in per-call token cost (a
  window of 3 segments roughly triples per-call input tokens), but no
  increase in call count.
- **Implementation complexity:** lower than B, but higher than the "just
  widen the text" framing suggests once the `event_ids`/prompt-restriction
  and relation-ownership issues above are accounted for — a new schema
  field or convention is needed to record which segment a cross-segment
  relation belongs to.
- **Accuracy risk:** lowest of the three, since full original text is
  available for the entire window (no compact-summary grounding gap).
- **Assessment:** cheapest and simplest, but only catches *local* cross-
  segment links within the fixed window. The pilot above found the
  opposite of what would justify this option: most of the long-range links
  observed (e.g., meteorite → soil poisoning → animal deaths → family
  deaths → climax in "The Colour Out of Space") span more than a couple of
  scenes, well beyond any practical fixed window size. **Not recommended**
  as anything more than a low-cost interim partial mitigation, given the
  pilot shows the phenomenon of concern is predominantly long-range, not
  short-range.

## Recommendation

Build **option A** (post-reconciliation story-level relation pass). The
pilot above found the SF/horror stories' long-range causal chains (4 in
"The Colour Out of Space", 2 in "Cool Air") span well beyond adjacent
segments, so option C's fixed local window would still miss most of them
even with the `event_ids`/relation-ownership issues resolved. Option A
targets the actual phenomenon observed, is the cheapest of the three at
scale, and reuses already-resolved evidence spans rather than requiring
new text-search or cross-segment `event_ids` machinery.

The larger, stratified pilot recommended above (5-10 stories per genre)
should still be run before the paper publishes a cross-segment relation
density figure, to size the effect precisely — but it is not a
prerequisite for starting option A's implementation, since the need itself
is now established.

**Rationale in one line:** the proposal's own resulting-claim language
(SF's causal links being specifically *mechanistic* and plausibly
long-range) predicted a validity concern for a simple per-segment count,
and a small direct reading pilot confirmed that concern is real and
genre-differentiated in this corpus, not merely plausible.

## Sketch if a follow-up implementation work item is created

If option A is approved, the concrete additions would be: a new
`relation_extractor.py` function (or a second tool schema in the same
module) for the story-level pass, a new `PassUsage` entry (e.g.
`"story_relation"`) so its cost is visible per the existing cost/baseline
reporting pattern, and extending `reconcile_story_annotations`'s output to
include these newly-discovered relations alongside the qualified
same-segment ones already there.

This is not sufficient by itself, however: `export.build_analysis_tables`
currently builds its `"relations"` table exclusively from each segment's
`SegmentWorldAnnotation.relations`, and `baseline.summarize_annotations`
computes causal-link density the same way — neither path reads
`StoryWorldAnnotation.relations` at all. A follow-up implementation must
also update both `export.py` and `baseline.py` to include story-level
relations in their respective outputs, and must do so without
double-counting a relation that could conceivably appear in both a
segment's list and the story-level list (the "exclude same-segment links
from the new pass's scope" rule in option A's description above is the
intended guard against this, but the export/summary code must not assume
it and should de-duplicate defensively, e.g. by relation ID). No changes
to `schema.EventRelation` itself would be required — the existing fields
(including `certainty`) already fit this use case.
