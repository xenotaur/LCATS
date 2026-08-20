# Segmentation alignment failures beyond whitespace mismatches: categories and recommendations

Date: 2026-08-19
Work item: WI-SEGMENT-0069 (investigation)
Scope: recommendation only — implements no code change itself. Diagnostic
persistence (Required Change 1) landed in the same PR as this document,
since it was needed to gather the evidence below.

## Purpose

`WI-SEGMENT-0068` fixed one specific class of segmentation alignment
failure (a whitespace/newline-only mismatch between an LLM-provided anchor
quote and the real source text) and confirmed via a live smoke test that it
genuinely helped — but the overall exclusion rate remained worse than the
original 65% baseline, with `alignment_error` still the dominant cause.
This document classifies the *remaining* alignment failures into named
categories with real counts, determines which have a safe targeted fix,
and recommends what to do about each.

## Method

Ran `check_segmentation_reliability.py` against 30 stories (real API calls,
`claude-haiku-4-5-20251001`, `--seed 42`), after landing this WI's Required
Change 1 (persisting `parsed_output` — the raw, pre-alignment segments
dict — alongside every result, since `extracted_output` is cleared to
`None` centrally on an alignment failure by `WI-SEGMENT-0059`'s own
design). For every `alignment_error` outcome, the failing segment's raw
`start_par_id`/`end_par_id`/`start_exact`/`end_exact` were recovered from
`parsed_output` and re-run through `text_segmenter`'s own alignment logic
(`_locate_anchor_span`, `paragraph_text_indexer`) to classify *why* each
anchor failed to resolve — not just that it failed. Paragraph indices were
recomputed deterministically from each story's own body text (the indexer
is a pure function of the story text), so no LLM index metadata needed to
be persisted separately.

**Caveat — one category per story, not a full failure census:**
`align_segment` (and the `segments_result_aligner` wrapper around it) fails
fast: it raises on the *first* segment that doesn't align and never checks
the rest of that story's segments. This report classifies only each
story's first-reported failure. Where this matters (the paragraph-marker
pattern below), later, unobserved segments in the same story were directly
inspected via `parsed_output`'s full segment list to confirm the pattern's
real extent within that story.

## Results

30 stories sampled, 30 LLM calls made (no file-level or empty-body skips
this run). Outcome breakdown:

| Outcome | Count |
|---|---|
| included | 6 |
| `no_segments` | 3 |
| `alignment_error` | 21 |

Exclusion rate: 24/30 (80%) — worse than the 65% baseline and worse than
this session's own post-`WI-SEGMENT-0068`-fix measurement (70%, on a
different 20-story sample). This is expected sample-to-sample noise, not a
regression: `--seed 42` reproduces the same *file selection* deterministically,
but each story's LLM call is a fresh, stochastic generation, and different
random samples draw from a corpus with an uneven failure-mode distribution
(see per-category counts below — this run happened to draw an unusually
marker-leakage-heavy cluster). The point of this investigation is the
*within-run category breakdown*, not a new point-estimate of the overall
rate; a larger, dedicated measurement run is a separate follow-up from
this one (see Non-Goals below, restated from the WI itself).

### Category breakdown (one category per story, 21 stories)

| Category | Count | % of alignment_error |
|---|---:|---:|
| `anchor_absent_from_document` | 15 | 71% |
| `paragraph_misnumbering_large_margin` | 4 | 19% |
| `paragraph_misnumbering_narrow_margin` | 2 | 10% |

No story exhibited more than one category, and no story's failure resisted
classification (every one of the 21 resolved to exactly one of the three
categories above via the reproduction method described).

### `anchor_absent_from_document`, subdivided (15 stories)

Manual inspection of each of the 15 anchors (not just automated
re-checking) found three distinct sub-patterns:

**(a) Paragraph-index marker leakage — 3 stories, but not 3 isolated
segments.** `paragraph_text_indexer` prefixes each paragraph shown to the
model with a `[PNNNN]` marker (e.g. `[P0047]`), but `align_segment`
searches `canonical_text`, which never contains these markers. In
`new_apples_in_the_garden__neville`, `perchance_to_dream__stockham`, and
`weak_on_square_roots__burton`, the *first*-failing segment's anchor
literally began with the marker text itself, e.g.:

```
start_exact: '[P0047]\n\nAfter Forester left, Eddie picked up, listlessly fr...'
start_exact: '\n\n[P0044] Twenty-three looked up at the glowing dome of the ...'
start_exact: '[P0027] \n\nCorinne ran along. She spent most of the day shopp...'
```

Because of the fail-fast behavior noted above, each story's full
`parsed_output.segments` list was checked directly (not just the
first-failing one): `new_apples_in_the_garden` has this same marker-prefix
pattern on segments 4, 8, 9, 10, 11, and 12 (6 of its segments);
`perchance_to_dream` on segments 3, 5, 6, 8, and 9 (5 segments);
`weak_on_square_roots` on segments 4, 8, and 9 (3 segments). This is not a
rare one-off — within these 3 stories, it is the model's dominant anchor
style for later segments, once the story runs long enough that the model's
own paragraph markers start bleeding into its "verbatim" quoting.

**(b) Typographic quote/dash mismatch — 2 stories.** The source corpus
uses Unicode curly quotes (`“”‘’`) and em/en dashes; the model's anchor
text uses plain ASCII equivalents. `the_hollow_lens__leverage`'s
`start_exact` and `the_voice_in_the_fog__leverage`'s `end_exact` both
resolve to an exact substring of the source once curly quotes/dashes are
normalized to their ASCII equivalents — e.g. source
`“Beyond the Wall,” “Whispering Wires,”` vs. anchor
`"Beyond the Wall," "Whispering Wires,"`.

**(c) Near-miss quoting with a small edit distance — 10 stories.** The
remaining 10 anchors are not found even after typography normalization,
but are not wholesale fabrications either. Spot-checking with
`difflib.SequenceMatcher` on a sample found single-character or
single-word deviations from the real text, e.g.
`a_great_day_for_the_irish__hopf`'s anchor matches 126 of its 151
characters as one contiguous run against the source, breaking only at one
word (`"made her way"` in the anchor vs. the source's actual `"make her
way"`); `junior__abernathy`'s anchor differs from the source only by one
extra trailing `"` character the source text never had. This looks like
LLM quoting noise at the character/word level — the model is *trying* to
quote verbatim and getting most of it right, not inventing content — but
each miss is different enough (a substituted word here, a stray
punctuation mark there) that no single narrow string transform would
recover all of them without also risking false-positive matches on
genuinely different text.

### `paragraph_misnumbering_*`, subdivided (6 stories)

For all 6, the failing anchor's real text was found intact elsewhere in
the document, outside the paragraph range implied by the model's own
`start_par_id`/`end_par_id`. Required Change 3 asked whether this
correlates with anything observable — checked against paragraph count
(`n_par`) specifically, since that's what the model is asked to count:

| Story | n_par | Claimed range (par IDs → char offsets) | Real anchor position | Margin |
|---|---:|---|---:|---:|
| `love_among_the_robots__mcdowell` (large) | 302 | `[7,51]` → `[1306, 6255]` | 7920 | 1665 chars |
| `the_last_days_of_l_a__smith` (large) | 193 | `[121,144]` → `[23251, 28127]` | 22930 | 321 chars |
| `the_spinster_1905__hichens` (large) | 162 | `[44,75]` → `[4210, 8848]` | 10713 | 1865 chars |
| `way_of_a_rebel__miller` (large) | 110 | `[5,8]` → `[1986, 3693]` | 8787 | 5094 chars |
| `no_charge_for_alterations__gold` (narrow) | 341 | `[52,87]` → `[9053, 12984]` | 8929 | 124 chars |
| `peace_manoeuvres__davis` (narrow) | 208 | `[37,86]` → `[6349, 14764]` | 14766 | 2 chars |
| (for comparison) `included` stories | 373, 244, 195, 174, 124, 48 | — | — | — |

**No correlation observed in this small sample.** Both mis-numbering
categories span roughly the same `n_par` range (110–341) as the stories
that aligned successfully (48–373), and the six included stories' median
`n_par` (184.5) is close to the 21 alignment_error stories' median (175).
This does not *rule out* a relationship between paragraph count and
mis-numbering — overlapping ranges and similar medians across six
failures and six successes are weak evidence at this sample size, and
"paragraph count" alone doesn't capture paragraph *density* (paragraphs
per unit of text length), which wasn't measured separately here. What
this sample does show is that the single most obvious hypothesis (longer
paragraph-count stories systematically mis-number) isn't visibly true in
these 21 cases; a dedicated follow-up with a larger sample and an actual
density measure would be needed to check the hypothesis properly before
treating it as settled either way (review finding, PR #320).

## Recommendations

### Fix now: strip paragraph-index markers and normalize quote/dash typography

Both sub-patterns (a) and (b) above are narrow, well-understood, and
directly analogous to `WI-SEGMENT-0068`'s own fix (a targeted transform
applied before matching, not a widened search range or a fallback that
guesses). Concretely:

1. In `_locate_anchor_span`, before the whitespace-tolerant regex fallback,
   strip a leading `\[P\d+\]\s*` marker (or any embedded occurrence — the
   `\n\n[P0098] \n\n[P0099]` example shows a marker can appear mid-anchor
   too, at a paragraph boundary within the segment) from the anchor before
   matching.
2. Normalize Unicode curly quotes (`“”‘’`) and em/en dashes to their ASCII
   equivalents on *both* sides of the comparison (or match against a
   normalized copy of `text`), matching the existing whitespace-tolerant
   fallback's structure rather than replacing it.

Together, these two sub-patterns account for 5 of 21 (24%) of this
sample's `alignment_error` failures, entirely within `find_anchor_in_range`
/`_locate_anchor_span` — no prompt change, no search-range widening, no
`forbidden_actions` implicated. This is well-scoped enough to be its own
narrow follow-up deliverable WI, structured the same way as
`WI-SEGMENT-0068`.

### Defer: paragraph mis-numbering (6 of 21, 29%)

No safe, evidence-backed fix design emerged from this sample — the one
hypothesis checked (correlation with paragraph count) wasn't visibly
supported, and this WI's own `forbidden_actions` bars widening the search
range without distribution data to justify it. A targeted fix isn't ruled
out in principle, but this sample doesn't supply the evidence to design
one safely. Recommend a follow-up round of diagnostic sampling specifically
targeting this category (e.g., checking whether the model's paragraph
count drifts from a fixed offset consistently within a story, which would
suggest an off-by-N counting habit rather than a random miss) before
committing to a fix design — not blocking, but not ready to implement
either.

### Accept as a likely inherent floor, for now: near-miss quoting (10 of 21,
48%)

No single narrow transform recovers these without risking the exact
silent-wrong-match failure `WI-SEGMENT-0059` already documented and this
WI's `forbidden_actions` explicitly guards against
(`reintroduce_full_document_fallback`). A character-edit-distance-tolerant
fuzzy match is the most obvious next idea, but its false-positive risk
(matching the *wrong* nearby text that happens to be similarly close)
needs its own dedicated design and evaluation, not a quick addition here.
Reported plainly as this investigation's honest outcome for this category,
per the WI's own Risk Notes: not every category has a fix ready to
implement, and this is a legitimate, complete result for an
investigation-type work item.

## Reproducing this analysis

The classification method above (recomputing paragraph indices from a
story's own body text, then re-running `_locate_anchor_span` against the
persisted `parsed_output`) is implemented in
`experiments/03_cross_segment_relation_pilot/classify_alignment_failures.py`,
which reads a `check_segmentation_reliability.py` `--output` directory and
prints the category breakdown and examples shown above. Any future smoke
test run against that script's `--output` can be classified the same way
without a fresh LLM call, as long as Required Change 1's `parsed_output`
persistence is in place.

## Related Workstream and Designs

- Work item: `project/work_items/resolved/WI-SEGMENT-0068.md` (the fix
  whose own post-merge verification surfaced this investigation)
- Work item: `project/work_items/proposed/WI-EVENT-0033.md` (whose own
  verification smoke test originally surfaced this gap)
- Work item: `project/work_items/resolved/WI-SEGMENT-0059.md` (prior art
  on why a naive full-document fallback, or any silent guess, is unsafe —
  the reason the "near-miss quoting" category above is deferred rather
  than papered over with a fuzzy match)
- Design doc: `project/design/event-role-world-cross-segment-relations-evaluation.md`
  (`WI-EVENT-0028`'s investigation-type precedent, whose format this
  document follows)
