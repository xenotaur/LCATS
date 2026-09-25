from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lcats" / "src"))

import regression_test_fuzzy_matcher_against_real_segments as m  # noqa: E402
from lcats.analysis import text_segmenter  # noqa: E402

STORY_TEXT = (
    "Alpha bravo charlie delta echo foxtrot golf hotel.\n\n"
    "India juliet kilo lima mike november oscar papa.\n\n"
    "Quebec romeo sierra tango uniform victor whiskey.\n\n"
    'Xray, "yankee," zulu said quietly to the room.\n'
)


def _para_spans(text=STORY_TEXT):
    canonical = text_segmenter.canonicalize_text(text)
    _, index_meta = text_segmenter.paragraph_text_indexer(canonical)
    return canonical, index_meta["para_spans"]


def _segment(seg_id, sp, ep, start_exact, end_exact, start_char, end_char):
    return {
        "segment_id": seg_id,
        "start_par_id": sp,
        "end_par_id": ep,
        "start_exact": start_exact,
        "end_exact": end_exact,
        "start_char": start_char,
        "end_char": end_char,
    }


class IsRealSegmentTest(unittest.TestCase):
    def test_rejects_non_segment_shaped_dicts(self):
        self.assertFalse(m._is_real_segment({"foo": "bar"}))
        self.assertFalse(m._is_real_segment("not a dict"))
        self.assertFalse(m._is_real_segment(None))

    def test_rejects_null_offsets(self):
        seg = _segment(1, 1, 1, "a", "b", None, None)
        self.assertFalse(m._is_real_segment(seg))

    def test_accepts_a_well_formed_segment(self):
        seg = _segment(1, 1, 1, "Alpha bravo", "hotel.", 0, 50)
        self.assertTrue(m._is_real_segment(seg))

    def test_rejects_bool_offsets(self):
        """Review finding, PR #425: bool is an int subclass in Python, so
        an unguarded isinstance(x, int) check would accept True/False as
        if they were real character offsets."""
        seg = _segment(1, 1, 1, "a", "b", True, 50)
        self.assertFalse(m._is_real_segment(seg))
        seg2 = _segment(1, 1, 1, "a", "b", 0, False)
        self.assertFalse(m._is_real_segment(seg2))

    def test_rejects_start_not_less_than_end(self):
        """Review finding, PR #425: a segment whose start_char >= end_char
        is malformed and must not be treated as real, checkable data."""
        seg = _segment(1, 1, 1, "a", "b", 50, 50)
        self.assertFalse(m._is_real_segment(seg))
        seg2 = _segment(1, 1, 1, "a", "b", 60, 50)
        self.assertFalse(m._is_real_segment(seg2))


class ValidateControlsTest(unittest.TestCase):
    def test_non_overlapping_non_reused_segment_is_valid(self):
        text, para_spans = _para_spans()
        segs = [
            _segment(1, 1, 1, "Alpha bravo", "hotel.", 0, 50),
            _segment(2, 2, 2, "India juliet", "papa.", 52, 100),
        ]
        valid, excluded = m.validate_controls(text, segs)
        self.assertEqual(len(valid), 2)
        self.assertEqual(excluded, [])

    def test_overlapping_segments_are_both_excluded(self):
        text, para_spans = _para_spans()
        segs = [
            _segment(1, 1, 1, "Alpha bravo", "foxtrot golf hotel.", 0, 50),
            _segment(2, 1, 1, "delta echo", "hotel.", 20, 50),
        ]
        valid, excluded = m.validate_controls(text, segs)
        self.assertEqual(len(valid), 0)
        self.assertEqual(len(excluded), 2)
        self.assertTrue(
            all(
                "overlaps an adjacent segment" in r
                for ex in excluded
                for r in ex["reasons"]
            )
        )

    def test_non_adjacent_overlap_is_caught_not_just_adjacent_pairs(self):
        """Review finding, PR #425 (2nd round): comparing only adjacent
        pairs after sorting by start_char misses a segment that overlaps
        a NON-adjacent neighbor. A=(0,140) encloses both B=(5,20) and
        C=(70,90); B and C don't overlap each other, so sorted order
        A, B, C only ever directly compares (A,B) and (B,C) - never
        (A,C) - which would silently accept C as valid ground truth even
        though it genuinely overlaps A."""
        text, para_spans = _para_spans()
        a = _segment(1, 1, 4, "Alpha", "whiskey.", 0, 140)
        b = _segment(2, 1, 1, "bravo", "delta", 5, 20)
        c = _segment(3, 3, 3, "sierra", "victor", 70, 90)
        valid, excluded = m.validate_controls(text, [a, b, c])
        self.assertEqual(valid, [])
        excluded_ids = {ex["segment_id"] for ex in excluded}
        self.assertEqual(excluded_ids, {1, 2, 3})

    def test_reused_anchor_across_segments_is_excluded(self):
        text, para_spans = _para_spans()
        segs = [
            _segment(1, 1, 1, "Alpha bravo", "hotel.", 0, 50),
            _segment(2, 2, 2, "hotel.", "papa.", 52, 100),
        ]
        valid, excluded = m.validate_controls(text, segs)
        # segment 1's end_exact ("hotel.") equals segment 2's start_exact -
        # both segments touching that shared string are excluded.
        excluded_ids = {ex["segment_id"] for ex in excluded}
        self.assertIn(1, excluded_ids)
        self.assertIn(2, excluded_ids)

    def test_paragraph_window_not_containing_char_offsets_is_excluded(self):
        """The real love_of_life/story_of_keesh/brown_wolf failure mode:
        start_par_id/end_par_id claim paragraph 1, but the real char span
        is far outside paragraph 1's own bounds - a symptom of the
        pre-WI-SEGMENT-0059 paragraph-collapse bug."""
        text, para_spans = _para_spans()
        seg = _segment(1, 1, 1, "Xray", "zulu said quietly to the room.", 150, 199)
        valid, excluded = m.validate_controls(text, [seg])
        self.assertEqual(valid, [])
        self.assertEqual(len(excluded), 1)
        self.assertTrue(any("does not contain" in r for r in excluded[0]["reasons"]))

    def test_bool_par_id_is_excluded_as_malformed(self):
        text, para_spans = _para_spans()
        seg = _segment(1, True, 1, "Alpha bravo", "hotel.", 0, 51)
        valid, excluded = m.validate_controls(text, [seg])
        self.assertEqual(valid, [])
        self.assertIn("malformed", excluded[0]["reasons"][0])

    def test_segment_not_reproduced_by_production_matcher_is_excluded(self):
        """Review finding, PR #425: the first three checks (overlap,
        reused anchor, window containment) are all structural - none of
        them confirm the CURRENT production align_segment still finds
        this segment's recorded offsets. A segment whose start_exact
        anchor is not actually present in its claimed window is
        structurally fine but not a currently-correct control, and must
        be excluded, not silently accepted."""
        text, para_spans = _para_spans()
        seg = _segment(1, 1, 1, "this text is not in paragraph one", "hotel.", 0, 50)
        valid, excluded = m.validate_controls(text, [seg])
        self.assertEqual(valid, [])
        self.assertEqual(len(excluded), 1)
        self.assertTrue(any("does not reproduce" in r for r in excluded[0]["reasons"]))

    def test_zero_paragraph_story_excludes_all_without_crashing(self):
        """Review finding, PR #425: text_segmenter.paragraph_text_indexer
        always returns at least one paragraph span in practice, but
        validate_controls must not crash with IndexError if it were ever
        called with a story whose index has zero paragraphs (a defensive
        guard against a scenario the real indexer does not currently
        produce, not a reachable-through-canonicalize_text case)."""
        seg = _segment(1, 1, 1, "a", "b", 0, 1)
        with mock.patch.object(
            text_segmenter,
            "paragraph_text_indexer",
            return_value=("", {"para_spans": []}),
        ):
            valid, excluded = m.validate_controls("irrelevant", [seg])
        self.assertEqual(valid, [])
        self.assertEqual(len(excluded), 1)
        self.assertTrue(any("zero paragraphs" in r for r in excluded[0]["reasons"]))


class CheckSegmentTest(unittest.TestCase):
    def test_exact_anchor_agrees_with_recorded_offsets(self):
        text, para_spans = _para_spans()
        policy = m.load_default_policy()
        seg = _segment(1, 1, 1, "Alpha bravo charlie", "foxtrot golf hotel.", 0, 50)
        report = m.check_segment(para_spans, text, policy, seg)
        self.assertTrue(report["start"]["agrees"])
        self.assertTrue(report["end"]["agrees"])
        self.assertFalse(report["start"]["required_fuzzy_tolerance"])

    def test_out_of_range_par_id_is_clamped_not_a_crash(self):
        """Regression test for a real bug caught during this item's own
        execution: check_segment must clamp start_par_id/end_par_id the
        same way validate_controls does, or an out-of-range value raises
        IndexError instead of being handled."""
        text, para_spans = _para_spans()
        policy = m.load_default_policy()
        seg = _segment(1, 1, 999, "Alpha bravo", "hotel.", 0, 50)
        report = m.check_segment(para_spans, text, policy, seg)
        self.assertIn("start", report)
        self.assertIn("end", report)

    def test_tolerance_flag_compares_against_production_normalized_match(self):
        """Review finding, PR #425: required_fuzzy_tolerance must compare
        the fuzzy match against production's own normalized fallback
        (_locate_anchor_span, which is case/typography/whitespace-run
        tolerant), not a raw byte-exact substring check. An anchor with a
        single space where the real text has a whitespace run of two is
        something production's own fallback already resolves - it must
        not be reported as needing fuzzy tolerance beyond that."""
        double_space_text = (
            "Alpha bravo charlie delta echo foxtrot golf hotel.\n\n"
            "India juliet  kilo lima mike november oscar papa.\n\n"
        )
        text, para_spans = _para_spans(double_space_text)
        policy = m.load_default_policy()
        seg = _segment(
            1, 2, 2, "India juliet kilo", "oscar papa.", para_spans[1][0], 100
        )
        report = m.check_segment(para_spans, text, policy, seg)
        self.assertTrue(report["start"]["fuzzy_matched"])
        self.assertTrue(report["start"]["agrees"])
        self.assertFalse(report["start"]["required_fuzzy_tolerance"])

    def test_end_anchor_tolerance_uses_production_narrowed_search_window(self):
        """Review finding, PR #425 (2nd self-review round): production's
        align_segment searches end_exact within [s_idx, hi) - starting
        from where start_exact was actually found - not [lo, hi) again.
        Comparing the fuzzy end match against a production search over
        the WIDER [lo, hi) window could misclassify
        required_fuzzy_tolerance if end_exact's text also occurs earlier,
        in [lo, s_idx). This directly controls _locate_anchor_span's
        return value per call to make that earlier-occurrence scenario
        concrete without depending on candidate_matches' own tie-breaking
        between multiple real occurrences."""
        text, para_spans = _para_spans()
        policy = m.load_default_policy()
        # start_exact locates at char 12 (not 0), so the end anchor's
        # narrowed production search [12, hi) is distinguishable from an
        # (incorrect) wide search [0, hi) by its `lo` argument alone.
        seg = _segment(1, 1, 1, "charlie delta echo", "foxtrot golf hotel.", 0, 50)

        real_locate = text_segmenter._locate_anchor_span

        def fake_locate(text_arg, anchor, lo, hi):
            if anchor == "foxtrot golf hotel.":
                # Wide window [0, hi) would (incorrectly) report an
                # earlier, different span; narrowed window starting from
                # s_idx reports the real match fuzzy also finds.
                if lo == 0:
                    return (5, 10)
                return real_locate(text_arg, anchor, lo, hi)
            return real_locate(text_arg, anchor, lo, hi)

        with mock.patch.object(
            text_segmenter, "_locate_anchor_span", side_effect=fake_locate
        ):
            report = m.check_segment(para_spans, text, policy, seg)

        # The real (narrowed-window) production span agrees with fuzzy's
        # match, so no tolerance beyond production was actually needed -
        # a wide-window comparison would have wrongly reported True here.
        self.assertTrue(report["end"]["agrees"])
        self.assertFalse(report["end"]["required_fuzzy_tolerance"])

    def test_zero_paragraph_story_does_not_crash(self):
        """Review finding, PR #425: check_segment must guard the same
        zero-paragraph edge case validate_controls does, as defense in
        depth against being called directly on such data."""
        text, _ = _para_spans()
        policy = m.load_default_policy()
        seg = _segment(1, 1, 1, "Alpha bravo charlie", "foxtrot golf hotel.", 0, 50)
        report = m.check_segment([], text, policy, seg)
        self.assertFalse(report["start"]["fuzzy_matched"])
        self.assertFalse(report["end"]["fuzzy_matched"])

    def test_anchor_with_internal_punctuation_can_fail_to_match(self):
        """Documents the real WI-SEGMENT-0102 finding: candidate_matches'
        token-ngram regex joins tokens with \\s+ only, so an anchor whose
        real text has punctuation (not just whitespace) between its last
        few tokens can fail to generate any candidate at all - a false
        negative (safe), not a false accept, but a real, common
        robustness gap in real prose (dialogue, exclamations)."""
        punctuated_text = "Alpha bravo charlie.\n\n" '"Yankee," zulu said, quietly.\n'
        text, para_spans = _para_spans(punctuated_text)
        policy = m.load_default_policy()
        seg = _segment(1, 2, 2, '"Yankee,"', "quietly.", 22, len(text))
        report = m.check_segment(para_spans, text, policy, seg)
        # This anchor's tokens ("Yankee", "zulu", "said", "quietly") are
        # separated by a comma in the real text but only \s+ in the
        # reconstructed regex - accepted_match finds nothing.
        self.assertFalse(report["end"]["fuzzy_matched"])


class DiscoverSourcesTest(unittest.TestCase):
    def test_same_story_id_from_distinct_sources_is_not_deduplicated_away(self):
        """Review finding, PR #425 (the most severe of this item's own
        review round): the same story_id recurs across sources with
        genuinely distinct segment arrays (different segmentation runs -
        e.g. a reworded-prompt ablation over the same cohort), never as
        byte-identical duplicates. Deduplicating by story_id alone
        silently dropped 52 real segments from 5 stories in the real
        inventory. The fix keys discovery by (source, story_id)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            base_dir = (
                root
                / "experiments/03_cross_segment_relation_pilot/results"
                / "segmentation_reliability"
            )
            reworded_dir = (
                root
                / "experiments/03_cross_segment_relation_pilot/results"
                / "segmentation_reliability_reworded_prompt"
            )
            replay_dir = (
                root
                / "experiments/03_cross_segment_relation_pilot/results"
                / "segmentation_paragraph_misnumbering_diagnostics/replay_fixture"
            )
            for d in (base_dir, reworded_dir, replay_dir):
                d.mkdir(parents=True, exist_ok=True)
            corpora_dir = root / "corpora" / "storyA"
            corpora_dir.mkdir(parents=True)
            (corpora_dir / "story.json").write_text(
                json.dumps({"body": "Alpha bravo charlie delta echo."}), "utf-8"
            )

            def _write(path, n_segments):
                segs = [
                    _segment(i, 1, 1, "a", "b", i * 10, i * 10 + 5)
                    for i in range(n_segments)
                ]
                path.write_text(
                    json.dumps(
                        {
                            "outcome": "included",
                            "story_id": "storyA",
                            "parsed_output": {"segments": segs},
                        }
                    ),
                    "utf-8",
                )

            _write(base_dir / "storyA.json", 3)
            _write(reworded_dir / "storyA.json", 2)

            with mock.patch.object(m, "REPO_ROOT", root), mock.patch.object(
                m, "CORPORA_ROOT", root / "corpora"
            ):
                sources = m.discover_sources()

        story_a_entries = [s for s in sources if s[1] == "storyA"]
        self.assertEqual(
            len(story_a_entries),
            2,
            "expected one entry per (source, story_id), not one merged entry",
        )
        segment_counts = sorted(len(s[3]) for s in story_a_entries)
        self.assertEqual(segment_counts, [2, 3])


if __name__ == "__main__":
    unittest.main()
