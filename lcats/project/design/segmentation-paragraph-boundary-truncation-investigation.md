# Segmentation Paragraph-Range Boundary Truncation Investigation

Date: 2026-08-28

Related work:

- `WI-EVENT-0096` measured `WI-EVENT-0033`'s schema-hardening fix against
  the real 17-story baseline cohort and found 10 real `alignment_error`
  failures.
- `WI-SEGMENT-0097` fixed 2 of those 10 (pure case-only near-misses).
- `WI-SEGMENT-0099` (separately scoped) covers 2 more (genuine
  word-level near-misses: a content substitution and a spelling typo).
- This item covers the remaining 6: cases where the model's claimed
  `end_exact` anchor is recoverable (exactly, or via the existing
  typography/whitespace-tolerant fallback) at a location that falls
  outside `align_segment`'s computed `[lo, hi)` search window.

## Summary

All 6 cases show the **same direction of error**: the real anchor text
is always found in a paragraph **after** the model's claimed
`end_par_id`, never before. 5 of 6 are off by exactly one paragraph; one
is off by two, and that one outlier has a distinct, identifiable cause
(an empty paragraph in the source). `text_segmenter`'s own paragraph
splitting was directly verified correct in every inspected case - the
root cause is the model itself misjudging which paragraph number its
own quoted `end_exact` text belongs to, not a code-side indexing
disagreement.

**Recommendation: a narrowly-scoped, end-boundary-only search-window
widening is the most promising mitigation**, but this item does not
implement it - the exact margin needs sizing from a broader sample than
this investigation's 6 real cases, all from one story cohort. See
Recommendation section.

## Method

For each case, real story text was loaded and re-indexed with
`text_segmenter.paragraph_text_indexer` (the same function used to build
the `[P0001]`-marked text sent to the model). `_locate_anchor_span` was
called against the **entire canonicalized document** (not the claimed
window) to find the anchor's true location, then that location was
checked against `para_spans` to determine which real paragraph number
contains it. This directly reuses the already-in-production alignment
function - no new matching logic was introduced for this investigation.

## Per-Case Findings

| Case | Claimed end_par_id | Real paragraph | Match-end overshoot (chars) |
|---|---:|---:|---:|
| `easy_money__sinclair` seg 3 | 117 | 118 | 286 |
| `the_voice_in_the_fog__leverage` seg 3 | 34 | 35 | 80 |
| `the_guardians__cox` seg 9 | 142 | 143 | 455 |
| `the_medici_boots__swet` seg 10 | 125 | 127 | 360 |
| `wintry_peacock_..._lawrence` seg 9 | 162 | 163 | 108 |
| `romance_of_an_ugly_policeman` seg 3 | 53 | 54 | 58 |

("Overshoot" = the real match's own end offset minus the claimed
window's end (`hi`) - review finding, PR #403: an earlier draft of this
table reported match-*start*-minus-`hi` instead for 5 of 6 rows, which
materially understates the character margin a production widening would
need to cover the full anchor, not just reach its start. Corrected by
re-running `_locate_anchor_span` and computing `match_end - hi`
directly. These larger values (tens to hundreds of characters, not a
handful) matter for sizing any future window-widening fix - see
Recommendation.)

### Direct inspection of the marked-up boundary text

**`easy_money__sinclair`, paragraphs 116-119** (claimed end: 117, real: 118):

```
[P0116] "Sure. This is a headquarters commissary. Big layout. Feeding two or
three camps from here."

[P0117] Charlie passed on. On a bit of good grass along the creek bottom he
staked his horses and cooked his supper. Grading camps offered none of
the hospitality the range afforded. No casual wayfarer got an...

[P0118] Charlie ate his supper by the fire, watched the men and teams string in
at six o'clock. It was a big camp. He estimated four hundred men...

[P0119] In the morning, with his own matutinal coffee bestowed where it would do
the most good...
```

Paragraphs 117 and 118 are two short, consecutive paragraphs continuing
the **same narrative beat** ("Charlie" cooking/eating supper at the same
camp, same evening) with no scene, time, or place change between them -
exactly the kind of boundary this pipeline's own segmentation prompt
(`SCENE_SEQUEL_SYSTEM_PROMPT`) instructs the model to treat as one
continuous unit for *scene* purposes, while `end_par_id` still needs
paragraph-level precision. The model's claimed `end_exact` text is drawn
from paragraph 118's content, but it labeled the segment's `end_par_id`
as 117 - plausibly because it perceived the two paragraphs as one
continuous beat and picked the earlier paragraph number.

**`the_guardians__cox`, paragraphs 141-143** (claimed end: 142, real: 143):

```
[P0141] "You didn't believe me?" Mryna gasped.

[P0142] "Of course not. If a plague carrier escaped from Rythar, we would have
heard about it long before this. The trouble with you scientists is you
don't grant the rest of us any common sense. And Jameson's the worst of
the lot. He's always contended that the sociologists should determine
our Rytharian policy, not the elected representatives of the people."

[P0143] Mryna broke down and began to cry hysterically. The senator put his hand
under her arm--none too gently. "Let's have no more dramatics, please...
```

Correction (review finding, PR #403): an earlier draft of this excerpt
was truncated by this investigation's own debug print (cut at 250
characters) and wrongly described paragraph 142 as ending mid-sentence.
The full paragraph 142 above is in fact complete and self-contained -
a single character's uninterrupted dialogue turn that closes its own
quotation cleanly. There is no mid-sentence break here; paragraph 143
begins a genuinely separate narration beat (a different
character/action). Unlike `easy_money__sinclair`'s case, this pair does
not share an obvious narrative-continuity or truncation cue - the model
still misattributed its `end_exact` text to paragraph 143 instead of the
correct 142, but this case does not by itself explain *why*, beyond the
same directional pattern (always forward, never backward) seen across
all 6 cases.

**`the_medici_boots__swet`, paragraphs 124-127** (claimed end: 125, real: 127 - the one +2 outlier):

```
[P0124] Before Eric could reply, dinner was announced...

[P0125] John offered his arm to his wife...Suzanne shrugged and said in a
caressing voice, "Eric?"

[P0126] (empty)

[P0127] Eric could only bow stiffly and offer his arm, while John walked
slowly beside them...
```

Paragraph 126 is **empty** (zero-length, likely from a doubled blank
line or a stripped scene-break marker in the source). This is a
distinct, identifiable cause for this one outlier: an empty paragraph
between the claimed and real paragraphs plausibly confused the model's
own paragraph count (it may not perceive an empty `[P0126]` marker as a
"real" paragraph worth counting, while `build_paragraph_index` still
assigns it a number), producing a 2-paragraph gap instead of the 1-
paragraph gap seen everywhere else.

## Categorization

Per the acceptance criteria's own question - model-side miscount vs.
code-side indexing disagreement - the evidence points to **model-side
miscount**, not a `text_segmenter` bug:

- `text_segmenter.paragraph_text_indexer`'s paragraph numbering was
  directly verified correct and internally consistent in every case
  (the same function that built the model's input was used to
  re-locate the real anchor).
- The error is one-directional (always undercounts `end_par_id`, never
  overcounts) and always small (1-2 paragraphs), consistent with a
  model attribution error at natural narrative-beat boundaries rather
  than a systematic numbering offset (which would show a constant
  gap regardless of content, and could go either direction).
- One outlier (`the_medici_boots__swet`) has a distinct, plausible
  secondary cause: an empty paragraph in the source, which is a
  legitimate input-representation question (should an empty paragraph
  get its own `[P####]` marker at all?) separate from the general
  narrative-continuity pattern seen in the other 5 cases.

## Recommendation

**A narrowly-scoped, end-boundary-only search-window widening is the
most promising direction**, not fixing the indexer (already correct) or
adjusting the prompt (the underlying ambiguity - two paragraphs
continuing one narrative beat - is a real property of the source text,
not something a prompt instruction can reliably eliminate).

This is **not implemented by this item** (investigation-only, per its
own `forbidden_actions`). Before any production change:

- The exact margin (how many paragraphs or characters past `end_par_id`
  to search) should be sized from a broader real sample than this
  item's 6 cases from one story cohort - 5 needed only 1 paragraph of
  margin, but the true tail is unknown from this sample alone.
- Per `WI-SEGMENT-0059`'s documented danger, any widening must carry
  its own explicit safety argument: it should apply **only to the end
  boundary** (never the start, where no evidence of this pattern
  exists), and the widened window should still require the same
  exact/typography/case-tolerant match `_locate_anchor_span` already
  uses - not a similarity threshold - so a genuine match at the
  widened boundary is still a very close textual match, not a guess.
- The empty-paragraph outlier suggests a secondary, separate question
  worth evaluating independently: whether `build_paragraph_index`
  should skip assigning a marker to zero-length paragraphs (merging
  them into an adjacent paragraph) rather than giving them their own
  number the model may not perceive as a real paragraph.
- Any widening fix should be tested against currently-*correctly*
  aligned stories too, to confirm it does not change or worsen any
  presently-passing alignment (per this item's own Risk Notes on thin
  sample size).

If a follow-on WI is filed to implement this, it should be scoped as a
`deliverable` depending on this investigation, sized against a
predeclared broader sample, and validated against both the failing
cases here and a control set of currently-passing alignments - not
implemented directly from this evidence alone.
