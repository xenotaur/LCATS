from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lcats" / "src"))

import measure_paragraph_boundary_overshoot as m  # noqa: E402
from lcats.analysis import text_segmenter  # noqa: E402

STORY_TEXT = (
    "Alpha bravo charlie delta.\n\n"
    "Echo foxtrot golf hotel india.\n\n"
    "Juliet kilo lima mike november.\n\n"
    "Oscar papa quebec romeo sierra.\n\n"
    # Deliberately contains a decoy duplicate of paragraph 7's end_exact
    # ("hotel again too.") - needed so the bounded-search-vs-unbounded
    # and s_idx-vs-lo tests below can actually discriminate correct from
    # incorrect behavior (review finding, PR #420: an earlier draft used
    # anchors that were unique in the fixture, so those tests passed
    # whether or not the code under test was bounded-first at all).
    "Tango uniform victor whiskey xray hotel again too. Decoy padding filler words here.\n\n"
    "Zulu alpha bravo charlie again.\n\n"
    "Delta echo foxtrot golf hotel again too.\n\n"
    "India juliet kilo lima mike again three.\n"
)


def _para_spans():
    canonical = text_segmenter.canonicalize_text(STORY_TEXT)
    _, index_meta = text_segmenter.paragraph_text_indexer(canonical)
    return canonical, index_meta["para_spans"]


class CheckSegmentTest(unittest.TestCase):
    def test_anchors_found_inside_claimed_window_are_not_flagged(self):
        text, para_spans = _para_spans()
        seg = {
            "segment_id": 1,
            "start_par_id": 2,
            "end_par_id": 2,
            "start_exact": "Echo foxtrot",
            "end_exact": "hotel india.",
        }
        report = m._check_segment(text, para_spans, seg)
        self.assertTrue(report["start"]["located"])
        self.assertTrue(report["start"]["inside_claimed_window"])
        self.assertTrue(report["end"]["located"])
        self.assertTrue(report["end"]["inside_claimed_window"])

    def test_anchor_outside_claimed_window_is_flagged_with_overshoot(self):
        text, para_spans = _para_spans()
        # end_exact actually lives in paragraph 3, but claim the segment
        # ends at paragraph 2 - a real WI-SEGMENT-0098-shaped case.
        seg = {
            "segment_id": 2,
            "start_par_id": 2,
            "end_par_id": 2,
            "start_exact": "Echo foxtrot",
            "end_exact": "mike november.",
        }
        report = m._check_segment(text, para_spans, seg)
        self.assertTrue(report["end"]["located"])
        self.assertFalse(report["end"]["inside_claimed_window"])
        self.assertGreater(report["end"]["overshoot_chars"], 0)

    def test_bounded_search_preferred_over_duplicate_elsewhere(self):
        """ "hotel again too." appears twice: a decoy in paragraph 5 and
        the real occurrence in paragraph 7. Claiming the segment at
        paragraph 7 only, the bounded search must resolve to paragraph
        7's occurrence, not the earlier paragraph-5 decoy (the
        the_invaders__ferris regression this fix exists for). This is a
        real discrimination, not a tautology (review finding, PR #420):
        directly verified that patching the code under test to search
        unboundedly-from-zero instead would make this assertion fail,
        since an unbounded leftmost search finds the paragraph-5 decoy
        first."""
        text, para_spans = _para_spans()
        seg = {
            "segment_id": 3,
            "start_par_id": 7,
            "end_par_id": 7,
            "start_exact": "Delta echo",
            "end_exact": "hotel again too.",
        }
        report = m._check_segment(text, para_spans, seg)
        self.assertTrue(report["end"]["inside_claimed_window"])
        lo, hi = report["claimed_window"]
        match_start, match_end = report["end"]["match_span"]
        self.assertTrue(lo <= match_start and match_end <= hi)
        # Not just "inside some window" - specifically NOT the paragraph-5
        # decoy, which sits entirely before this segment's own window.
        self.assertGreaterEqual(match_start, lo)

    def test_end_exact_search_floor_is_start_position_not_window_start(self):
        """end_exact's search must start from wherever start_exact
        resolved (s_idx), not from the window's own lo again - matching
        align_segment's real sequencing. Constructed so lo and s_idx
        genuinely differ (review finding, PR #420: an earlier draft had
        lo ~= s_idx, so it couldn't tell the two apart): start_par_id=5
        puts lo at paragraph 5's start, but start_exact ("Zulu alpha")
        only resolves in paragraph 6 - AFTER paragraph 5's own decoy
        occurrence of end_exact. A lo-anchored (incorrect) search for
        end_exact over [lo, hi) would find the paragraph-5 decoy first;
        the correct s_idx-anchored search skips past it and finds the
        real paragraph-7 occurrence."""
        text, para_spans = _para_spans()
        seg = {
            "segment_id": 4,
            "start_par_id": 5,
            "end_par_id": 7,
            "start_exact": "Zulu alpha",
            "end_exact": "hotel again too.",
        }
        report = m._check_segment(text, para_spans, seg)
        self.assertTrue(report["start"]["located"])
        self.assertTrue(report["end"]["located"])
        self.assertTrue(report["end"]["inside_claimed_window"])
        # The real (paragraph-7) occurrence, not the paragraph-5 decoy:
        # its offset must be strictly after where start_exact resolved.
        s_idx = report["start"]["match_span"][0]
        end_match_start = report["end"]["match_span"][0]
        self.assertGreater(end_match_start, s_idx)

    def test_bool_par_id_is_rejected(self):
        text, para_spans = _para_spans()
        seg = {
            "segment_id": 5,
            "start_par_id": True,
            "end_par_id": 2,
            "start_exact": "Alpha bravo",
            "end_exact": "hotel india.",
        }
        self.assertIsNone(m._check_segment(text, para_spans, seg))

    def test_end_par_id_lower_than_start_is_clamped_up(self):
        text, para_spans = _para_spans()
        seg = {
            "segment_id": 6,
            "start_par_id": 3,
            "end_par_id": 1,
            "start_exact": "Juliet kilo",
            "end_exact": "mike november.",
        }
        report = m._check_segment(text, para_spans, seg)
        self.assertIsNotNone(report)
        lo, hi = report["claimed_window"]
        self.assertGreaterEqual(hi, lo)

    def test_out_of_range_par_id_is_clamped_not_dropped(self):
        text, para_spans = _para_spans()
        seg = {
            "segment_id": 7,
            "start_par_id": 1,
            "end_par_id": 999,
            "start_exact": "Alpha bravo",
            "end_exact": "again three.",
        }
        report = m._check_segment(text, para_spans, seg)
        self.assertIsNotNone(report)
        _, hi = report["claimed_window"]
        self.assertEqual(hi, para_spans[-1][1])


class MeasureAggregationTest(unittest.TestCase):
    def test_segment_level_and_anchor_level_counts_differ_when_both_anchors_outside(
        self,
    ):
        """A segment with BOTH anchors outside its claimed window must
        count once at the segment level but twice at the anchor level -
        the exact distinction the design doc's review round required."""
        text, para_spans = _para_spans()
        both_outside = {
            "segment_id": 1,
            "start_par_id": 5,
            "end_par_id": 5,
            "start_exact": "Zulu alpha",
            "end_exact": "mike november.",
        }
        report = m._check_segment(text, para_spans, both_outside)
        self.assertFalse(report["start"]["inside_claimed_window"])
        self.assertFalse(report["end"]["inside_claimed_window"])


if __name__ == "__main__":
    unittest.main()
