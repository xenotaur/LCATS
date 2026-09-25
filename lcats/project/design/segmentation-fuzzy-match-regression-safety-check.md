# Segmentation fuzzy-match regression safety check (WI-SEGMENT-0102)

## Purpose

`WI-SEGMENT-0072` proposed a `strict_local_fuzzy` policy
(`experiments/03_cross_segment_relation_pilot/evaluate_near_miss_fuzzy_matching.py`)
as a candidate near-miss recovery mechanism for anchor matching, but froze
its adoption pending further evidence — the policy and its thresholds are
not used in production and this item does not change that.

This item asks a narrower, complementary question: for every real segment
where the *current* production matcher
(`text_segmenter._locate_anchor_span` / `align_segment`) already finds the
correct `(start_char, end_char)`, does `strict_local_fuzzy` ever produce a
**different** answer? Per `WI-SEGMENT-0059`'s standing principle, a
disagreement here is a stop condition, not a tuning invitation — this is a
non-regression / no-op-invariance check, not a recovery-rate measurement.

The implementation, `experiments/03_cross_segment_relation_pilot/
regression_test_fuzzy_matcher_against_real_segments.py`, calls
`evaluate_near_miss_fuzzy_matching.accepted_match` and `candidate_matches`
completely unmodified. No production code or `WI-SEGMENT-0072`'s frozen
thresholds are touched.

**Revision note.** This item's first-round PR ([#425](https://github.com/xenotaur/LCATS/pull/425))
drew a Copilot and a Codex review with several confirmed, material
findings — most significantly, a dedup bug that silently dropped 52 real
segments, and a missing "is this still a currently-correct control"
check. Every number in this document reflects the corrected script,
re-run after all findings below were independently re-verified and fixed.
The original, materially different numbers are not reproduced here except
where needed to describe what was found and fixed.

## Real-data inventory

Acceptance criterion 1 required a repo-wide discovery pass, not reliance on
the two locations named in the WI's original scope. A `grep -rl
'"start_char"' --include="*.json" .` search surfaced more candidates than
expected; each was individually inspected against the real segment schema
(`start_par_id`/`end_par_id`/`start_exact`/`end_exact`/`start_char`/
`end_char`) before being trusted.

**Included** (4 locations, story text resolved from `corpora/<id>/story.json`
or a co-located `story.json`), keyed by **(source, story_id)** — not
story_id alone (see Review round, finding 1):

| Source | Story-outputs | Segments | Provenance |
|---|---|---|---|
| `experiments/03_cross_segment_relation_pilot/results/segmentation_reliability/` | 7 | 56 | `WI-EVENT-0096`'s 17-story cohort (real API output, `outcome: included` only) |
| `.../segmentation_reliability_reworded_prompt/` | 8 | 68 | `WI-SEGMENT-0101`'s reworded-prompt ablation, same cohort |
| `.../segmentation_paragraph_misnumbering_diagnostics/replay_fixture/` | 2 | 31 | `WI-SEGMENT-0071`'s replay fixture |
| `lcats/experimental/annotation_feasibility_trial/source/trial/*/scenes.json` | 24 | 177 | `WI-ANNOTATE-0054`'s real trial output |

Total discovered: **332 segments across 41 (source, story) outputs.**

**Excluded after inspection** (not real narrative-segment data):

- `experiments/03_cross_segment_relation_pilot/results/model_tiering_eval/
  model_tiering_comparison.json` — its `start_char` fields are always
  `null` (stage-2/genre-detection metadata).
- `lcats/experimental/science_fiction_analysis_trial/results/
  worldcon_spike/...` — a different schema
  (`evidence_sets[].records[].anchor.{start_char,end_char,paragraph_ids}`
  for literary-theory evidence spans, not narrative segments), and built
  from `"backend": "fake"` synthetic fixture data per its own `provenance`
  field, not real API output.
- `lcats/experimental/model_comparison/ollama_gpt_oss_20b/` — entity/genre
  data, no segment schema at all.

## Ground-truth validation (why "included" alone is not enough)

Per the WI's own Problem/Context (`the_secret_of_kralitz__kuttner` segments
4 and 5 both ending at char 13102), an `outcome: included` label does not
guarantee non-overlapping or correct boundaries. Four checks are applied
before a segment is trusted as ground truth:

1. **Overlap** — sorted by `(start_char, end_char)`, a running-cluster
   sweep: extending a cluster's max `end_char` across every member (not
   just the immediately-preceding segment) catches a segment overlapping
   any earlier member of its cluster, not only its adjacent neighbor in
   sort order — see Review round, finding 6, for why the earlier
   adjacent-pairs-only version was insufficient.
2. **Reused anchor** — a `start_exact`/`end_exact` string shared by more
   than one segment in the same story excludes every segment touching it.
3. **Paragraph-window containment** (added during this item's own first
   implementation pass, not anticipated in the original acceptance
   criteria) — the window `[start_par_id, end_par_id]` (inclusive,
   clamped) must actually *contain* the segment's own recorded
   `(start_char, end_char)`.
4. **Current-production reproduction** (added during this item's review
   round — see below) — re-running the CURRENT production
   `text_segmenter.align_segment` over the segment's own
   `start_par_id`/`end_par_id`/`start_exact`/`end_exact` must reproduce
   its recorded `(start_char, end_char)` exactly.

Check 3 was necessary, not optional: `love_of_life`, `story_of_keesh`, and
`brown_wolf` in `annotation_feasibility_trial` — the exact three stories
`WI-SEGMENT-0059` named as pre-fix paragraph-collapse casualties — have
every segment's `start_par_id`/`end_par_id` stuck at `(1, 1)` regardless of
the segment's real character span, a residual symptom of the single-newline
paragraph-collapse bug `WI-SEGMENT-0059` fixed in production. Some of these
segments' character spans do not even overlap each other, so overlap
detection alone would not have caught them.

Check 4 was necessary for a different reason (see Review round, finding
2): the first three checks are purely structural and say nothing about
whether the *current* matcher still agrees with a segment's recorded
offsets. 13 structurally-valid segments turned out not to be reproducible
by `align_segment` at all — using them as ground truth would have
compared `strict_local_fuzzy` against a stale, no-longer-correct answer.

**Exclusion breakdown** (41 total segments excluded, out of 332
discovered; reasons are not mutually exclusive per segment):

| Reason | Count |
|---|---|
| Overlaps an adjacent segment | 19 |
| Reused start_exact/end_exact anchor | 3 |
| Paragraph window does not contain recorded char span | 19 |
| Current production matcher does not reproduce recorded offsets | 13 |

**291 segments validated as genuine, currently-correct ground truth.**

## Results

For each of the 291 validated segments, `start_exact` and `end_exact` are
evaluated independently against `strict_local_fuzzy`, and the result is
compared to the segment's own recorded `start_char`/`end_char`.

| Outcome | Count |
|---|---|
| Agree exactly on both anchors | 176 |
| Disagreement (either anchor) | 115 |

Disagreements are reported **at the anchor level**, not just the segment
level (see Review round, finding 3 — a segment-level bucket hides a
wrong-offset anchor whenever the segment's *other* anchor has no match at
all):

| Anchor-level outcome | Count | Safety implication |
|---|---|---|
| No candidate found (`fuzzy_matched: False`) | 137 | Safe — a false negative, not a false accept. |
| Wrong offset (candidate found, differs from recorded) | 9 | **The real safety-relevant finding** — see below. |

### The 9 wrong-offset cases: a genuine, narrow disagreement

All 9 wrong-offset cases are off by exactly **1 character**, spanning 5
distinct stories (`the_lost_charm__norton` — 2 separate segmentation
runs, `the_secret_of_kralitz__kuttner`, `ohenry-whirligigs/girl`,
`red_headed_league` ×3, `scandal_in_bohemia` ×2), 8 on the `end_exact`
side and 1 on `start_exact`. Every case has `required_fuzzy_tolerance:
True` — `strict_local_fuzzy` needed genuine edit-distance tolerance (not
a byte-exact hit, and not something production's own normalized fallback
already reaches — see the tolerance-metric fix below) to find these. This
is exactly the class `WI-SEGMENT-0059` warns about: two
independently-implemented anchor matchers (`_locate_anchor_span`'s
typography/whitespace/case-tolerant exact match vs. `candidate_matches`'
own separately-implemented boundary scoring) computing a slightly
different exact boundary for the same typography-normalized text.

**9 real cases out of 291 (3.1%) — small, but not zero, and this item's
own acceptance criteria require reporting it explicitly rather than
absorbing it into a blanket verdict.**

### The 137 no-match cases: a distinct, previously-undocumented robustness gap

Decomposing the 137 no-match anchors by root cause (checked directly
against `candidate_matches`' real behavior, not inferred):

| Root cause | Count |
|---|---|
| Anchor has fewer than 3 word-tokens | 16 |
| Anchor has ≥3 tokens, but real text has punctuation (not just whitespace) between the last few tokens | 64 |
| Other (not further categorized — likely additional typography-normalization or multi-paragraph-span cases) | 57 |

Two distinct, previously-undiscovered structural limitations in
`WI-SEGMENT-0072`'s frozen `candidate_matches` account for a large share
of these:

1. **Punctuation-blind n-gram reconstruction.** `candidate_matches`
   rebuilds a candidate regex by joining word-tokens with `\s+`
   (whitespace) only. Real prose — especially dialogue — very commonly has
   punctuation between an anchor's last few words (e.g.
   `'"Yes, dear," sighed Mater.'`). Because the reconstructed pattern
   requires only whitespace between tokens, it fails to match text that
   actually has intervening punctuation, and `candidate_matches` returns
   **zero candidates** — confirmed for 64 of the 137 no-match cases by
   rebuilding each anchor's pattern with `\W+` (any non-word run) in place
   of `\s+` and confirming it *does* match the same window.
2. **Minimum 3-token requirement.** `candidate_matches` only builds n-grams
   of width 5, 4, or 3 tokens. An anchor with fewer than 3 word-tokens
   (e.g. `"Everybody was."`, `"DON CHANNING."`) never has a 3-gram to
   build, so zero candidates are ever generated — regardless of whether
   the anchor is an exact substring of the window. This was independently
   discovered while diagnosing this item's own regression-test fixture.

Both are **false negatives, not false accepts** — `strict_local_fuzzy`
never proposes a wrong span in these cases, it simply proposes none. This
makes them safe with respect to `WI-SEGMENT-0059`'s "never silently produce
a plausible-but-wrong span" principle, but they represent a large,
previously-undocumented robustness gap: well over a third of validated
segments have at least one anchor for which this policy would get **no
help at all**, if it were ever used as a recovery mechanism, independent
of its threshold tuning.

### The tolerance metric itself was miscalibrated (fixed during review)

The first implementation flagged 44 anchor matches as
`required_fuzzy_tolerance` by comparing the fuzzy match against a raw
byte-exact substring check. That overstated how much `strict_local_fuzzy`
adds beyond production: 32 of those 44 cases were already reproduced,
at the identical span, by production's own `_locate_anchor_span` — which
is itself case-, typography-, and whitespace-run-tolerant, not a strict
byte comparison. The corrected metric compares against
`_locate_anchor_span`'s real result; only **12** anchor matches now
require something production's own normalized fallback cannot already
reach on its own.

## Verdict

**Not a blanket "safe."** Per this item's own acceptance criteria:

- No production alignment behavior is changed by this item, and
  `WI-SEGMENT-0072`'s frozen thresholds are neither invoked nor altered —
  this check does not clear that gate and was never intended to.
- **A genuine, if narrow, disagreement exists**: 9 of 291 validated real
  segments (3.1%) show `strict_local_fuzzy` disagreeing with the current
  correct result by exactly 1 character, always on a typography-normalized
  boundary requiring real edit-distance tolerance to find. This is the
  same class of two-matchers-disagree risk `WI-SEGMENT-0059` treats as a
  stop condition. It does not block this item (no production behavior
  changed), but it is evidence against ever adopting `strict_local_fuzzy`
  without first resolving this boundary-computation discrepancy between
  the two independently-implemented matchers.
- **Separately, and more significantly**: `candidate_matches` has at least
  two previously-undocumented structural limitations (punctuation-blind
  token-joining, and a hard 3-token minimum) that make it unable to
  propose *any* candidate for a large fraction of real anchors — a
  robustness gap distinct from, and arguably more consequential than,
  `WI-SEGMENT-0072`'s known threshold-tuning questions. This does not
  compromise safety (false negative, not false accept) but materially
  limits the policy's usefulness as a near-miss recovery mechanism in its
  current form, independent of threshold choice.

## Review round (PR #425)

Both an automated Copilot review and a Codex review landed against the
first implementation. Every substantive finding was independently
re-verified against real repo data before being accepted (per this
project's standing review-response discipline) — all were confirmed real:

1. **P1 — inventory dedup silently dropped 52 real segments.** The
   original `discover_sources` deduplicated by `story_id` alone, on the
   documented assumption that a story_id recurring across sources was the
   same evidence committed twice. Verified false: 5 story_ids recur across
   sources with genuinely different, non-identical segment arrays (e.g.
   `peace_manoeuvres__davis` has 11/8/13 segments across its three source
   copies) — confirmed no two copies are byte-identical. **Fixed**: keyed
   by `(source, story_id)` instead. Recovered exactly 52 segments,
   confirmed by direct count before and after.
2. **P1 — structural validity was conflated with "currently correct."**
   The first three validation checks say nothing about whether the
   present-day matcher still agrees with a segment's recorded offsets.
   Verified by re-running `text_segmenter.align_segment` directly over
   all 257 originally-"valid" segments: 13 did not reproduce their
   recorded offsets (one example cited by the reviewer,
   `red_headed_league` segment 7, checked and confirmed:
   `align_segment` returns `(45491, 49418)` against a recorded
   `(45490, 49419)`). **Fixed**: added check 4 above.
3. **P1 — segment-level disagreement bucketing hid 3 wrong-offset
   anchors.** The original aggregation classified a segment as "no match"
   whenever *either* anchor had no candidate, even if the *other* anchor
   had a wrong-offset match — hiding those wrong-offset cases entirely,
   including a 2-character (not 1-character) miss on `red_headed_league`
   segment 7. Verified by recomputing at the anchor level directly against
   the committed JSON: 10 wrong-offset anchors existed pre-fix, not 7.
   **Fixed**: `main()` now counts and reports `total_wrong_offset_anchors`
   / `total_no_match_anchors` at the anchor level. (After fix 2 above also
   excluded the one segment behind that 2-character miss as
   not-currently-correct, the final wrong-offset count settled at 9 — see
   Results above; two *new* wrong-offset cases also surfaced from the
   52 segments recovered by fix 1.)
4. **P2 — the fuzzy-tolerance metric used a byte-exact comparison instead
   of production's real normalized matcher.** Verified directly: 32 of 44
   originally-flagged cases were reproduced by `_locate_anchor_span` at
   the identical span. **Fixed** — see "The tolerance metric itself was
   miscalibrated" above.
5. **Lower-severity Copilot findings, all confirmed and fixed**:
   `_is_real_segment` accepted booleans as offsets (bool is an `int`
   subclass in Python) and didn't require `start_char < end_char`;
   `discover_sources`' trial-data path lacked the `isinstance(dict)`
   guard its reliability-dir path already had, so a malformed
   `scenes.json`/`story.json` would crash the whole run instead of being
   skipped; `validate_controls` and `check_segment` would raise
   `IndexError` on a zero-paragraph story (not currently reachable through
   `canonicalize_text`'s real output, but guarded defensively); an unused
   `para_spans` variable in two test cases was removed.

**Second round: substitute self-review (no automated bot response landed
against the fix commit after an extended wait).** A cold-context
subagent independently reviewed the fix commit and surfaced 2 more
findings, both independently re-verified before being accepted:

6. **Medium — the overlap check only compared adjacent pairs after
   sorting by `start_char`, missing a segment that overlaps a
   non-adjacent neighbor.** Verified by direct reproduction: a
   synthetic `A=(0,170)` enclosing both `B=(5,20)` and `C=(100,120)`
   (with `B`, `C` not overlapping each other) left `C` incorrectly
   accepted as valid ground truth, because sorted order `A, B, C` only
   ever compares `(A,B)` and `(B,C)`, never `(A,C)`. Checked against the
   real committed inventory: this did not change which segments end up
   excluded overall (all 4 newly-caught cases — `love_of_life` segments
   8/9/10/13 — were already excluded via the paragraph-window check), but
   it did change the **overlap** exclusion-reason count from 15 to 19
   (reflected in the table above) and the algorithm's correctness
   guarantee was unsound in general, with no regression coverage for the
   non-adjacent case. **Fixed**: replaced the adjacent-pair comparison
   with a running-cluster sweep (extending a cluster's max `end_char`
   across every member, not resetting it to each new segment's own end),
   and added a dedicated regression test reproducing the exact
   3-segment non-adjacent scenario.
7. **Low — a doc prose error.** This document originally said the 9
   wrong-offset cases span "4 distinct stories" while naming 5. Verified
   directly against the committed JSON (5 distinct `story_id` values).
   **Fixed** — corrected above.

## Regression coverage

`regression_test_fuzzy_matcher_against_real_segments_test.py` (20 tests)
covers `_is_real_segment` (including the bool-offset and
start-not-less-than-end cases from the review), all four
`validate_controls` checks (including the new production-reproduction
check, the non-adjacent-overlap sweep fix, and a zero-paragraph guard),
`check_segment`'s exact-agreement path, its out-of-range-`par_id` clamp,
its zero-paragraph guard, the production-normalized tolerance-metric fix,
the punctuation-causes-no-match case, and a dedicated `discover_sources`
test reproducing the exact (source, story_id) dedup scenario the review's
most severe finding identified. Re-run this suite after any future change
to `strict_local_fuzzy` or its evaluator to re-verify this safety property
still holds.
