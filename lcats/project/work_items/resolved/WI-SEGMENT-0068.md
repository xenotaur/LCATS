---
resolution: "Implemented and merged via PR #317 (commit d461d188): find_anchor_in_range's second stage now builds a whitespace-tolerant regex directly from the anchor (splitting into whitespace/non-whitespace runs, escaping only the non-whitespace runs, joining with \\s+) and searches it against the full segment via re.search, instead of re-searching a heuristic window with the original, non-normalized anchor string. Removed the now-unused _norm_ws/_WS helpers. A real P1 bug was found and fixed during review (Codex): align_segment's end_exact branch computed e_idx = e_pos + len(end_exact), which silently truncated the segment's final character(s) whenever the matched whitespace run's length differed from the anchor's own -- fixed by extracting _locate_anchor_span() to return the real (start, end) span, with a regression test reproducing the exact off-by-one truncation. Regression tests replay the exact captured real case (mass_quantities/junior__abernathy) against the real committed corpus text. See execution records project/executions/WI-SEGMENT-0068/2026_08_18_22_19_44_WI_SEGMENT_0068.md and project/executions/AD_HOC/2026_08_18_22_18_12_WI_SEGMENT_0068_SELFREVIEW.md."
blocked_reason: null
blocked: false
id: WI-SEGMENT-0068
title: Fix find_anchor_in_range's whitespace-normalized fallback so it actually returns a match
type: deliverable
status: resolved
priority: high
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams: []
related_design:
  - lcats/project/design/backlog.md
depends_on: []
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - rewrite_alignment_algorithm_from_scratch
acceptance:
  - "find_anchor_in_range (text_segmenter.py) returns a correct absolute index when an anchor's only difference from the source text is whitespace/newline placement -- reproduced by this WI's own regression test, not just a synthetic example"
  - "The reproduction case captured 2026-08-14 (mass_quantities/junior__abernathy, segment 3's end_exact 'glowered suspiciously at Mater and the\\nneighbors.' vs. the source's 'the neighbors.' with no embedded newline) passes as a deterministic replay test against real corpora/ text, matching text_segmenter_test.py's existing TestWiAnnotate0054RealTrialDataReplay pattern"
  - "The existing exact-match fast path (find_anchor_in_range's first branch) and existing passing tests (test_find_anchor_in_range_exact_match, align_segment's happy-path tests) are unchanged in behavior"
  - "New tests added to TestFindAnchorInRangeEdgeCases (or a new sibling test class) cover: a whitespace-only difference that should now resolve, and confirm a genuinely absent anchor (wrong words, not just wrong whitespace) still correctly returns None"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/src/lcats/analysis/text_segmenter.py
  - lcats/tests/analysis_tests/text_segmenter_test.py
  - lcats/project/design/backlog.md
---

## Summary

`text_segmenter.py`'s `find_anchor_in_range` has a whitespace-normalized
fallback for when an LLM-provided anchor quote doesn't exact-match the
source text -- but that fallback's second stage silently discards its
own successful match and returns `None` whenever the mismatch is
specifically a whitespace/newline difference, which is exactly the class
of input the fallback exists to handle. This was found live: a
`WI-EVENT-0033` verification smoke test (2026-08-14, real API, 20
stories) measured a 100% alignment-failure rate, and tracing one failure
to its root cause found this bug.

## Problem / Context

**Prior art check:**
- *Duplication search:* No existing fix or WI addresses this -- confirmed
  via `grep -n "find_anchor_in_range\|_norm_ws" text_segmenter.py` and a
  search of `project/work_items/` and `backlog.md` for "whitespace" +
  "anchor" + "align". `WI-SEGMENT-0059` (resolved) fixed a related but
  distinct bug (paragraph-collapse on single-newline source text, causing
  a silent full-document-fallback); this is a new, different failure mode
  in the same function family, only observable now that `WI-SEGMENT-0059`
  made alignment failures raise instead of silently swallowing them.
- *Demand search:* Not yet in `backlog.md` when this WI was first drafted
  -- this WI's own creation PR adds the entry directly (review finding,
  PR #309: the finding wasn't yet documented anywhere else, so it should
  be logged as soon as confirmed, not deferred to implementation).

Root cause, confirmed by direct instrumentation against a real API
response (not assumed): `find_anchor_in_range`
(`text_segmenter.py:89-125`) tries an exact substring search first; on
failure, it whitespace-normalizes both the anchor and the search range
(`_norm_ws`, collapsing whitespace runs to a single space) and finds the
position within the *normalized* text (`pos_n`). Because `_norm_ws`
doesn't preserve string length, that normalized position can't be used
directly -- the function then computes a heuristic `start_guess` and
re-searches a small window of the **original, non-normalized** text
using the **original, non-normalized** `anchor` string
(`window.find(anchor)`, line 122). This second search is exact, not
whitespace-tolerant -- so whenever the original mismatch *was* a
whitespace/newline difference (the only case this fallback is for), the
re-search fails identically to the first exact search, and the function
returns `None` despite having already found the correct location.

Reproduced directly: a live smoke-test story
(`mass_quantities/junior__abernathy`) had a model-returned `end_exact` of
`"glowered suspiciously at Mater and the\nneighbors."` against real
source text `"...the neighbors.\n\n"` (words identical, newline placement
differs -- the model mis-recalled where Project Gutenberg's ~72-char
hard-wrapping fell, not a content error). Confirmed via direct
interpreter session: `pos_n` finds the normalized match at index 4020;
the window's real text at that position is `"...glowered suspiciously at
Mater and the neighbors.\n\n..."` (correct); `window.find(anchor)`
returns `-1` because `anchor` still contains the wrong embedded `\n`.
The function returns `None`, `align_segment` raises `alignment_error`,
and the whole story is excluded -- even though the model's segmentation
was substantively correct.

This plausibly explains the large majority of the 18/20 `alignment_error`
outcomes measured in the live smoke test (all `mass_quantities` stories,
all following the identical failure signature), though this WI doesn't
require re-verifying every one of the 18 individually -- the acceptance
criteria gate on the specific reproduced case plus regression coverage,
not a full re-run (a full live re-run is expensive and better done as a
natural follow-up once this fix lands, not a blocking criterion here).

## Scope

- Fix `find_anchor_in_range`'s second-stage (whitespace-fallback)
  matching so a real normalized match actually resolves to a real
  character span, instead of being discarded by an exact re-search.
- Add regression tests reproducing the captured real-world case plus
  targeted edge cases.
- Mark this WI's own `backlog.md` entry (added by this WI's creation PR)
  resolved once the fix lands.

## Non-Goals

- Does not re-run the full live smoke test against real API credentials
  to get an updated aggregate exclusion-rate number -- a natural
  follow-up, not required here.
- Does not touch the exact-match fast path, `align_segment`'s
  paragraph-ID logic, or any other part of `text_segmenter.py`'s
  alignment pipeline.
- Does not investigate whether other failure signatures exist beyond
  this specific whitespace-mismatch class (e.g. a genuinely wrong quote)
  -- this WI targets the one root cause found and reproduced.

## Required Changes

1. Replace `find_anchor_in_range`'s second-stage heuristic
   (`start_guess`/`window`/exact `window.find(anchor)`) with a
   whitespace-tolerant match that finds the real span directly -- e.g. a
   regex built from `anchor` with each internal whitespace run mapped to
   `\s+` (other characters escaped via `re.escape`), searched against
   `segment` (or a window) via `re.search`, using the match's own span
   for the real offset rather than a guessed-and-rechecked position.
   Implementation detail is at the implementer's discretion as long as
   it satisfies the acceptance criteria; avoid introducing a full
   rewrite of `align_segment` itself (see `forbidden_actions`).
2. Add a regression test replaying the captured real case
   (`mass_quantities/junior__abernathy`'s segment-3 `end_exact` vs. its
   real source text) into `TestFindAnchorInRangeEdgeCases` or a new
   sibling class, following `text_segmenter_test.py`'s existing
   `TestWiAnnotate0054RealTrialDataReplay` pattern of testing against
   real corpora/ text rather than only synthetic strings.
3. Add a test confirming a genuinely-wrong anchor (different words, not
   just different whitespace) still correctly returns `None` -- guard
   against the fix becoming too permissive.
4. Mark `backlog.md`'s "`find_anchor_in_range`'s whitespace-normalized
   fallback discards its own successful match" entry (added by this
   WI's creation PR) resolved as part of this WI's own closeout.

## Acceptance Criteria

(see `acceptance` frontmatter above)

## Validation

- `pytest tests/analysis_tests/text_segmenter_test.py -v`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes

- The regex-escaping step must be careful, and the naive order is
  actually wrong (review finding, PR #309): escaping the *whole* anchor
  first via `re.escape()` and then substituting whitespace runs with
  `\s+` does not work, because `re.escape()` itself escapes a plain
  space as `\ ` (backslash-space) in supported Python versions -- a
  subsequent whitespace-run substitution then has nothing left to match,
  since the literal `" "` was already consumed into `\ `. The correct
  order is the reverse: split `anchor` into whitespace and
  non-whitespace runs *first*, escape only the non-whitespace runs via
  `re.escape()`, then join them back together with `\s+` in place of
  each original whitespace run. Getting this backwards silently
  reproduces the exact bug this WI exists to fix.
- This fix makes alignment slightly more permissive (previously-rejected
  whitespace-only mismatches will now resolve) -- verify this doesn't
  reintroduce anything `WI-SEGMENT-0059` specifically closed off (that
  WI's own concern was a *content* mismatch silently resolving to a
  wrong span, not a whitespace-only difference; this fix only targets
  the latter).
