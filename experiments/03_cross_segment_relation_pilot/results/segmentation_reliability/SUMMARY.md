# WI-EVENT-0096 measurement: segmentation schema-hardening effect

**Real API run, 2026-08-26.** `claude-haiku-4-5-20251001`, 17 real LLM
calls, actual cost **$0.59** (225,626 input tokens, 73,483 output tokens -
measured directly from each story's recorded `usage`, not estimated).

## Cohort

The exact original 17-story baseline cohort from
`experiments/03_cross_segment_relation_pilot/results/pilot_stories.jsonl`
(5 science fiction, 5 horror, 2 western, 5 romance), resolved to current
`corpora/` paths via `resolve_baseline_story_list.py`. Not a fresh or
substitute sample.

## Headline result

| | Baseline (pre-fix) | This run (post-fix, PR #188) |
|---|---|---|
| Exclusion rate (any cause) | 11/17 (65%) | **10/17 (59%)** |
| Exclusion cause | 11/11 `parsing_error` (100%) | 0/10 `parsing_error` (0%); 10/10 `alignment_error` (100%) |

**The `parsing_error` failure mode is structurally eliminated**: dropped
from 11/17 to **zero**, by switching to the `tool_schema=` path, which
removes the free-text JSON-parse step that mode used to fail at. This
0/17 is not itself measured evidence of improved reliability, though -
`JSONPromptExtractor.extract()` sets `parsing_error = None`
unconditionally on the `tool_schema` path, so a 0/17 count is guaranteed
by the code path regardless of whether segmentation actually got more
reliable (review finding, PR #398, confirmed real - the paragraph
originally here overclaimed 0/17 as confirmation of success). The only
real, measured evidence is the any-cause exclusion-rate comparison below.

**Overall segmentation reliability barely moved (65% -> 59%,
a 6-point improvement), because a different, pre-existing failure mode
was already present underneath and is now fully exposed.** All 10
new-run exclusions are `alignment_error: "anchor text not found in story
text"` - the exact near-miss-anchor category `WI-SEGMENT-0069`
investigated and `WI-SEGMENT-0072` evaluated (fuzzy-matching) and
deliberately declined to fix, due to false-positive risk. The model
successfully parses and returns a full segment list (e.g.
`lovecraft/the_haunter_of_the_dark` returned 13 well-formed segments),
but one segment's anchor text fails to align against the real story text,
and the whole story is excluded as a result - not a parsing failure at
all, a distinct alignment failure that `parsing_error`-based reporting
would have hidden entirely (per this item's own review-round correction:
`parsing_error` is `None` unconditionally on the `tool_schema` path, so a
naive comparison would have shown a false 0%-improvement-impossible or
100%-improvement result depending on which side of the tautology was
read).

## One observed inclusion flip, not yet established as a regression

`wintry_peacock_from_the_new_decameron_volume_iii__lawrence` (romance)
was **included** in the original baseline and is **excluded** in this
run (`alignment_error`, segment_id=9). `make_segment_extractor` samples
at `temperature=0.2`, and this compares one pre-fix call against one
post-fix call with no repeated trials or same-version control - the flip
could reflect ordinary model-output variance rather than a real effect of
the code change (review finding, PR #398). Reported as an observed flip,
not asserted as a regression, pending further evidence. Per-genre detail:

| Genre | Baseline included | This run included | Note |
|---|---|---|---|
| science fiction | 1/5 | 1/5 | unchanged |
| horror | 1/5 | 2/5 | improved |
| western | 0/2 | 1/2 | improved - no longer zero |
| romance | 4/5 | 3/5 | `wintry_peacock...` flipped from included to excluded (see above) |

## Conclusion

`WI-EVENT-0033`'s schema-hardening fix structurally eliminates its named
failure mode (`parsing_error`) by removing the free-text JSON-parse step
that mode failed at - confirmed by code path, not by the 0/17 count
alone, which is guaranteed regardless of real reliability. The measured,
real evidence is the any-cause exclusion rate, which did not improve
meaningfully (65% -> 59%), because a different, already-known,
already-deferred failure mode (near-miss anchor alignment) was the
larger and previously partially-masked contributor. Per this project's
practice of not forcing a pass on a smaller-than-expected improvement,
`WI-EVENT-0033` is not being resolved by this measurement alone - see its
own Risk Notes for the updated real evidence and the resulting
recommendation.

## Raw data

One JSON file per story under this directory (mirroring `corpora/`'s
`<collection>/<slug>.json` layout), each containing `outcome`,
`llm_call_made`, `word_count`, `segment_count`, `raw_output`,
`parsed_output`, `extracted_output`, `api_error`, `extraction_error`, and
`usage` (real `input_tokens`/`output_tokens`).
