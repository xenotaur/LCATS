"""Unit tests for lcats.analysis.text_indexing."""

import json
import unittest

from lcats.analysis import text_segmenter
from lcats.utils import paths as lcats_paths


class TestTextIndexing(unittest.TestCase):
    """Unit tests for the text_indexing module."""

    def setUp(self):
        # Three simple paragraphs; p2 includes multiple spaces to test exact anchoring.
        self.p1 = "First para line one.\nLine two."
        self.p2 = "Second para with   extra   spaces."
        self.p3 = "Third para end."

        # Simulate Windows newlines between paragraphs to test canonicalization.
        self.story_raw = self.p1 + "\r\n\r\n" + self.p2 + "\r\n\r\n" + self.p3
        self.story = text_segmenter.canonicalize_text(self.story_raw)  # -> \n only

    def test_canonicalize_text_normalizes_newlines(self):
        """CRLF/CR are normalized to LF and content is preserved."""
        self.assertIn("\n\n", self.story)
        self.assertNotIn("\r", self.story)
        self.assertTrue(self.story.startswith("First para"))
        self.assertTrue(self.story.endswith("Third para end."))

    def test_build_paragraph_index_returns_parts_and_spans(self):
        """Paragraphs and their absolute spans should align with the source string."""
        parts, spans = text_segmenter.build_paragraph_index(self.story, splitter="\n\n")
        self.assertEqual(parts, [self.p1, self.p2, self.p3])
        self.assertEqual(len(spans), 3)

        # Check that slicing by spans reproduces each paragraph exactly.
        for (start, end), expected in zip(spans, parts):
            self.assertEqual(self.story[start:end], expected)

        # Spans should be strictly increasing and non-overlapping.
        self.assertLess(spans[0][1], spans[1][0])
        self.assertLess(spans[1][1], spans[2][0])

    def test_add_paragraph_markers_inserts_ids(self):
        """Markers like [P0001] should prefix each paragraph with correct delimiter usage."""
        parts, _ = text_segmenter.build_paragraph_index(self.story, splitter="\n\n")
        indexed = text_segmenter.add_paragraph_markers(parts, delimiter="\n\n")

        self.assertTrue(indexed.startswith("[P0001] "))
        self.assertIn("[P0002] ", indexed)
        self.assertIn("[P0003] ", indexed)

        # There should be exactly (n-1) paragraph delimiters.
        self.assertEqual(indexed.count("\n\n"), len(parts) - 1)

    def test_find_anchor_in_range_exact_match(self):
        """Exact anchor within a paragraph range returns the correct absolute index."""
        _, spans = text_segmenter.build_paragraph_index(self.story, splitter="\n\n")
        lo, hi = spans[1]  # paragraph 2 range
        anchor = "para with   extra   spaces"  # keep spaces exact
        idx = text_segmenter.find_anchor_in_range(self.story, anchor, lo, hi)
        self.assertIsNotNone(idx)
        self.assertEqual(self.story[idx : idx + len(anchor)], anchor)

    def test_find_anchor_in_range_outside_range_returns_none(self):
        """Anchors outside the search window should return None."""
        _, spans = text_segmenter.build_paragraph_index(self.story, splitter="\n\n")
        lo, hi = spans[2]  # paragraph 3 only
        anchor = "Second para"  # exists only in paragraph 2
        self.assertIsNone(
            text_segmenter.find_anchor_in_range(self.story, anchor, lo, hi)
        )

    def test_align_segment_happy_path_within_one_paragraph(self):
        """Align using (start_par_id, end_par_id) and exact anchors inside paragraph 2."""
        parts, spans = text_segmenter.build_paragraph_index(self.story, splitter="\n\n")
        p2_start, p2_end = spans[1]

        start_exact = self.p2[:12]  # "Second para "
        end_exact = self.p2[-7:]  # "spaces."
        span = text_segmenter.align_segment(
            self.story,
            spans,
            start_par_id=2,
            end_par_id=2,
            start_exact=start_exact,
            end_exact=end_exact,
        )
        self.assertIsNotNone(span)
        s, e = span
        # Spans lie within paragraph 2.
        self.assertGreaterEqual(s, p2_start)
        self.assertLessEqual(e, p2_end)
        # The extracted text begins/ends with anchors.
        self.assertTrue(self.story[s:].startswith(start_exact))
        self.assertTrue(self.story[:e].endswith(end_exact))
        self.assertGreater(e, s)

    def test_align_segment_fallback_to_paragraph_bounds_when_anchors_missing(self):
        """Empty anchors fall back to paragraph bounds."""
        parts, spans = text_segmenter.build_paragraph_index(self.story, splitter="\n\n")
        p3_start, p3_end = spans[2]

        span = text_segmenter.align_segment(
            self.story,
            spans,
            start_par_id=3,
            end_par_id=3,
            start_exact="",
            end_exact="",
        )
        self.assertEqual(span, (p3_start, p3_end))

    def test_align_segment_handles_reversed_par_ids_gracefully(self):
        """If end < start, it clamps to a single paragraph (paragraph 3, the
        larger of the two 1-based ids) instead of crashing -- but the
        anchors here are p2's text, which does not occur within paragraph
        3's range, so this is a genuine alignment failure (WI-SEGMENT-0059:
        a real anchor-not-found case, not a silent fallback to bounds)."""
        parts, spans = text_segmenter.build_paragraph_index(self.story, splitter="\n\n")

        start_exact = self.p2[:6]
        end_exact = self.p2[-6:]

        # Intentionally reversed: start_par_id=3, end_par_id=2 -> clamped to paragraph 3.
        span = text_segmenter.align_segment(
            self.story,
            spans,
            start_par_id=3,
            end_par_id=2,
            start_exact=start_exact,
            end_exact=end_exact,
        )
        self.assertIsNone(span)

    def test_align_segment_reversed_par_ids_with_anchors_present_still_aligns(self):
        """Reversed par_ids clamp to a single paragraph; if the anchors
        actually occur within that clamped paragraph's own range, alignment
        still succeeds cleanly (this is the "clamps gracefully" case the
        original test intended -- see the sibling test above for the
        anchor-genuinely-missing case introduced by WI-SEGMENT-0059)."""
        parts, spans = text_segmenter.build_paragraph_index(self.story, splitter="\n\n")
        p3_start, p3_end = spans[2]

        start_exact = self.p3[:5]  # "Third"
        end_exact = self.p3[-5:]  # "end."

        span = text_segmenter.align_segment(
            self.story,
            spans,
            start_par_id=3,
            end_par_id=2,  # reversed; clamps to paragraph 3
            start_exact=start_exact,
            end_exact=end_exact,
        )
        self.assertIsNotNone(span)
        s, e = span
        self.assertGreaterEqual(s, p3_start)
        self.assertLessEqual(e, p3_end)
        self.assertGreater(e, s)

    def test_paragraph_text_indexer_outputs_indexed_text_and_meta(self):
        """Indexer returns indexed text with markers and meta that maps back to canonical text."""
        indexed_text, meta = text_segmenter.paragraph_text_indexer(self.story_raw)

        # Canonical text in meta should equal our precomputed canonical story.
        self.assertEqual(meta["canonical_text"], self.story)

        # para_spans map back into canonical text; counts should match paragraphs.
        self.assertIn("para_spans", meta)
        self.assertEqual(meta["n_paragraphs"], 3)
        self.assertEqual(len(meta["para_spans"]), 3)

        # Indexed text should start with marker and contain three markers.
        self.assertTrue(indexed_text.startswith("[P0001] "))
        self.assertEqual(indexed_text.count("[P"), 3)

    def test_segments_result_aligner_fills_start_end_chars(self):
        """Result aligner fills canonical start/end chars for well-formed segments."""
        _, meta = text_segmenter.paragraph_text_indexer(self.story_raw)

        # Build a parsed_output with one segment targeting paragraph 2 anchors.
        parsed_output = {
            "segments": [
                {
                    "segment_id": 1,
                    "segment_type": "narrative_scene",
                    "start_par_id": 2,
                    "end_par_id": 2,
                    "start_exact": self.p2[:6],  # "Second"
                    "end_exact": self.p2[-7:],  # "spaces."
                    "start_char": None,
                    "end_char": None,
                    "summary": "Para 2 summary",
                    "cohesion": {"time": "", "place": "", "characters": []},
                    "gacd": None,
                    "erac": None,
                    "reason": "Test segment",
                    "confidence": 0.9,
                }
            ]
        }

        aligned = text_segmenter.segments_result_aligner(
            parsed_output, self.story, meta
        )
        self.assertIn("segments", aligned)
        seg = aligned["segments"][0]
        self.assertIsInstance(seg.get("start_char"), int)
        self.assertIsInstance(seg.get("end_char"), int)
        s, e = seg["start_char"], seg["end_char"]
        self.assertGreater(e, s)
        # Anchors should match at the boundaries.
        self.assertTrue(self.story[s:].startswith(self.p2[:6]))
        self.assertTrue(self.story[:e].endswith(self.p2[-7:]))

    def test_segments_result_aligner_raises_on_missing_par_ids(self):
        """A segment missing start_par_id/end_par_id used to be silently
        left unchanged (no start_char/end_char, no error) -- WI-SEGMENT-0059
        treats a missing/wrong-typed par_id the same as any other alignment
        failure: align_segment returns None cleanly (not a raw TypeError),
        and segments_result_aligner raises rather than silently producing a
        story with some segments aligned and others quietly left null."""
        _, meta = text_segmenter.paragraph_text_indexer(self.story_raw)
        parsed_output = {
            "segments": [
                {
                    "segment_id": 99,
                    "segment_type": "other",
                    # Missing start_par_id/end_par_id & anchors
                    "summary": "Unalignable",
                }
            ]
        }
        with self.assertRaises(ValueError) as ctx:
            text_segmenter.segments_result_aligner(parsed_output, self.story, meta)
        self.assertIn("segment_id=99", str(ctx.exception))


class TestCanonicalizeCROnly(unittest.TestCase):
    """CR-only line endings are normalized."""

    def test_cr_only_normalized_to_lf(self):
        raw = "line1\rline2\rline3"
        result = text_segmenter.canonicalize_text(raw)
        self.assertNotIn("\r", result)
        self.assertIn("\n", result)
        self.assertEqual(result, "line1\nline2\nline3")


class TestFindAnchorInRangeEdgeCases(unittest.TestCase):
    """Edge-case coverage for find_anchor_in_range."""

    def setUp(self):
        self.text = "The quick  brown fox jumps over the lazy dog"

    def test_empty_anchor_returns_none(self):
        result = text_segmenter.find_anchor_in_range(self.text, "", 0, len(self.text))
        self.assertIsNone(result)

    def test_whitespace_only_anchor_returns_none(self):
        result = text_segmenter.find_anchor_in_range(
            self.text, "   ", 0, len(self.text)
        )
        self.assertIsNone(result)

    def test_whitespace_tolerant_fallback_now_resolves_a_real_match(self):
        """Regression test (WI-SEGMENT-0068): exact match fails (text has
        a double space before "brown"), but the anchor "quick brown"
        (single space) differs from the source only in whitespace -- the
        whitespace-tolerant fallback must now actually resolve this to
        the real position, not discard its own successful match and
        return None (the bug this WI fixes). Previously this exact case
        incorrectly asserted None; see WI-SEGMENT-0068 for the root
        cause."""
        result = text_segmenter.find_anchor_in_range(
            self.text, "quick brown", 0, len(self.text)
        )
        self.assertEqual(result, self.text.find("quick"))

    def test_whitespace_tolerant_fallback_not_found_returns_none(self):
        # Neither exact nor whitespace-tolerant match is found -- a
        # genuinely wrong anchor (different words, not just different
        # whitespace) must still correctly return None (WI-SEGMENT-0068
        # guard test).
        result = text_segmenter.find_anchor_in_range(
            self.text, "zebra giraffe", 0, len(self.text)
        )
        self.assertIsNone(result)

    def test_ws_tolerant_match_handles_regex_special_characters(self):
        """Regression test (WI-SEGMENT-0068): an anchor containing regex-
        special characters (parens) with a whitespace-only difference
        from the source must still resolve correctly -- proves the fix
        escapes non-whitespace runs rather than passing them through
        re.search() unescaped."""
        text = "The (quick)  brown fox jumps."
        result = text_segmenter.find_anchor_in_range(
            text, "(quick) brown", 0, len(text)
        )
        self.assertEqual(result, text.find("(quick)"))

    def test_newline_vs_space_whitespace_difference_resolves(self):
        """Regression test (WI-SEGMENT-0068): a newline in the anchor
        where the source has a plain space is exactly the class of
        mismatch the fallback exists for -- must resolve, not just
        same-character-count whitespace differences. (The anchor's
        embedded "\\n" makes this genuinely exercise the fallback: an
        exact search for it in the source, which uses a plain space at
        that position, fails first.)"""
        text = "He said the plan clearly. They listened intently."
        anchor = "the plan clearly.\nThey"
        self.assertEqual(
            text.find(anchor), -1, "test setup: anchor must not exact-match"
        )
        result = text_segmenter.find_anchor_in_range(text, anchor, 0, len(text))
        self.assertEqual(result, text.find("the plan"))


class TestAlignSegmentReturnsNone(unittest.TestCase):
    """align_segment returns None when the resulting span is invalid."""

    def test_returns_none_for_empty_story_text(self):
        # Empty story → span (0, 0) → s_idx=0, e_idx=0 → e_idx not > 0 → None
        story = ""
        _, spans = text_segmenter.build_paragraph_index(story, splitter="\n\n")
        result = text_segmenter.align_segment(story, spans, 1, 1, "", "")
        self.assertIsNone(result)


class TestNormalizePreview(unittest.TestCase):
    """Tests for _normalize_preview (internal helper)."""

    def test_empty_string(self):
        self.assertEqual(text_segmenter._normalize_preview(""), "")

    def test_crlf_becomes_single_newline_in_output(self):
        result = text_segmenter._normalize_preview("line1\r\nline2")
        self.assertNotIn("\r", result)
        self.assertIn("line1", result)
        self.assertIn("line2", result)

    def test_multiple_newlines_become_paragraph_separator(self):
        result = text_segmenter._normalize_preview("para1\n\npara2")
        # Double newline → paragraph marker (\u2029) → kept as \n in output
        self.assertIn("\n", result)
        self.assertIn("para1", result)
        self.assertIn("para2", result)

    def test_single_newlines_become_spaces(self):
        result = text_segmenter._normalize_preview("line1\nline2")
        self.assertIn("line1 line2", result)

    def test_extra_spaces_collapsed(self):
        result = text_segmenter._normalize_preview("hello   world")
        self.assertEqual(result, "hello world")

    def test_leading_trailing_whitespace_stripped(self):
        result = text_segmenter._normalize_preview("  hello world  ")
        self.assertEqual(result, "hello world")


class TestValidSpan(unittest.TestCase):
    """Tests for _valid_span (internal helper)."""

    def test_valid_span(self):
        self.assertTrue(text_segmenter._valid_span(0, 5, 10))

    def test_s_equals_e_is_invalid(self):
        self.assertFalse(text_segmenter._valid_span(3, 3, 10))

    def test_s_greater_than_e_is_invalid(self):
        self.assertFalse(text_segmenter._valid_span(5, 3, 10))

    def test_s_negative_is_invalid(self):
        self.assertFalse(text_segmenter._valid_span(-1, 5, 10))

    def test_e_exceeds_n_is_invalid(self):
        self.assertFalse(text_segmenter._valid_span(0, 11, 10))

    def test_non_int_s_is_invalid(self):
        self.assertFalse(text_segmenter._valid_span(None, 5, 10))

    def test_non_int_e_is_invalid(self):
        self.assertFalse(text_segmenter._valid_span(0, None, 10))

    def test_e_equals_n_is_valid(self):
        self.assertTrue(text_segmenter._valid_span(0, 10, 10))


class TestUnionCoverage(unittest.TestCase):
    """Tests for _union_coverage (internal helper)."""

    def test_empty_list_returns_zero(self):
        self.assertEqual(text_segmenter._union_coverage([]), 0)

    def test_single_span(self):
        self.assertEqual(text_segmenter._union_coverage([(0, 10)]), 10)

    def test_non_overlapping_spans(self):
        self.assertEqual(text_segmenter._union_coverage([(0, 5), (10, 15)]), 10)

    def test_overlapping_spans(self):
        self.assertEqual(text_segmenter._union_coverage([(0, 10), (5, 15)]), 15)

    def test_adjacent_spans(self):
        self.assertEqual(text_segmenter._union_coverage([(0, 5), (5, 10)]), 10)

    def test_contained_span(self):
        self.assertEqual(text_segmenter._union_coverage([(0, 20), (5, 10)]), 20)

    def test_unsorted_spans(self):
        self.assertEqual(text_segmenter._union_coverage([(10, 20), (0, 5)]), 15)


class TestValidateCoverageAndOverlaps(unittest.TestCase):
    """Tests for validate_coverage_and_overlaps."""

    def _make_seg(self, seg_id, start, end):
        return {"segment_id": seg_id, "start_char": start, "end_char": end}

    def test_empty_text_no_segments_no_missing(self):
        missing, overlaps = text_segmenter.validate_coverage_and_overlaps("", [])
        self.assertEqual(missing, [])
        self.assertEqual(overlaps, [])

    def test_nonempty_text_no_valid_segments_start_gap(self):
        missing, overlaps = text_segmenter.validate_coverage_and_overlaps(
            "hello world", []
        )
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["type"], "start_gap")
        self.assertEqual(overlaps, [])

    def test_full_coverage_no_gaps_no_overlaps(self):
        text = "hello world"
        segs = [self._make_seg(1, 0, len(text))]
        missing, overlaps = text_segmenter.validate_coverage_and_overlaps(text, segs)
        self.assertEqual(missing, [])
        self.assertEqual(overlaps, [])

    def test_start_gap(self):
        text = "hello world"
        segs = [self._make_seg(1, 6, len(text))]
        missing, overlaps = text_segmenter.validate_coverage_and_overlaps(text, segs)
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["type"], "start_gap")
        self.assertEqual(missing[0]["start"], 0)
        self.assertEqual(missing[0]["end"], 6)

    def test_end_gap(self):
        text = "hello world"
        segs = [self._make_seg(1, 0, 5)]
        missing, overlaps = text_segmenter.validate_coverage_and_overlaps(text, segs)
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["type"], "end_gap")
        self.assertEqual(missing[0]["start"], 5)
        self.assertEqual(missing[0]["end"], len(text))

    def test_middle_gap(self):
        text = "hello world foo"
        segs = [self._make_seg(1, 0, 5), self._make_seg(2, 11, len(text))]
        missing, overlaps = text_segmenter.validate_coverage_and_overlaps(text, segs)
        gap_types = [m["type"] for m in missing]
        self.assertIn("gap", gap_types)

    def test_partial_overlap(self):
        text = "hello world foo"
        segs = [self._make_seg(1, 0, 9), self._make_seg(2, 6, len(text))]
        missing, overlaps = text_segmenter.validate_coverage_and_overlaps(text, segs)
        self.assertEqual(len(overlaps), 1)
        self.assertEqual(overlaps[0]["type"], "partial_overlap")

    def test_duplicate_segments(self):
        text = "hello world"
        segs = [self._make_seg(1, 0, 11), self._make_seg(2, 0, 11)]
        missing, overlaps = text_segmenter.validate_coverage_and_overlaps(text, segs)
        self.assertTrue(any(o["type"] == "duplicate" for o in overlaps))

    def test_contained_segment(self):
        text = "hello world foo bar"
        segs = [self._make_seg(1, 0, len(text)), self._make_seg(2, 3, 10)]
        missing, overlaps = text_segmenter.validate_coverage_and_overlaps(text, segs)
        self.assertTrue(any(o["type"] == "contained" for o in overlaps))

    def test_whitespace_only_gap_ignored_when_small(self):
        # Gap of 3 spaces between segments – should be ignored by default.
        text = "hello   world"
        segs = [self._make_seg(1, 0, 5), self._make_seg(2, 8, len(text))]
        missing, overlaps = text_segmenter.validate_coverage_and_overlaps(
            text, segs, ignore_whitespace_gaps=True, whitespace_gap_max=8
        )
        self.assertEqual(missing, [])

    def test_whitespace_gap_reported_when_ignore_disabled(self):
        text = "hello   world"
        segs = [self._make_seg(1, 0, 5), self._make_seg(2, 8, len(text))]
        missing, overlaps = text_segmenter.validate_coverage_and_overlaps(
            text, segs, ignore_whitespace_gaps=False
        )
        self.assertEqual(len(missing), 1)

    def test_whitespace_gap_exceeding_max_reported(self):
        text = "hello          world"
        segs = [self._make_seg(1, 0, 5), self._make_seg(2, 15, len(text))]
        missing, overlaps = text_segmenter.validate_coverage_and_overlaps(
            text, segs, ignore_whitespace_gaps=True, whitespace_gap_max=4
        )
        self.assertEqual(len(missing), 1)

    def test_segments_with_invalid_spans_ignored(self):
        text = "hello world"
        segs = [
            {"segment_id": 1, "start_char": None, "end_char": None},
            {"segment_id": 2, "start_char": -1, "end_char": 5},
        ]
        missing, overlaps = text_segmenter.validate_coverage_and_overlaps(text, segs)
        # All segments invalid → treated as no segments → start_gap
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["type"], "start_gap")

    def test_contained_across_nonadjacent(self):
        # Segment 3 is contained within segment 1 (not adjacent to segment 2).
        text = "abcdefghijklmnopqrstuvwxyz"
        segs = [
            self._make_seg(1, 0, 20),
            self._make_seg(2, 5, 10),
            self._make_seg(3, 12, 18),
        ]
        missing, overlaps = text_segmenter.validate_coverage_and_overlaps(text, segs)
        contained = [o for o in overlaps if o["type"] == "contained"]
        self.assertGreater(len(contained), 0)

    def test_prev_seg_contained_in_current_same_start(self):
        # seg1 starts at same position as seg2 but ends earlier: seg1 contained in seg2.
        # This exercises the `prev_seg["start"] >= s and prev_seg["end"] <= e` branch.
        text = "hello world foo"
        segs = [self._make_seg(1, 0, 5), self._make_seg(2, 0, 10)]
        missing, overlaps = text_segmenter.validate_coverage_and_overlaps(text, segs)
        contained = [o for o in overlaps if o["type"] == "contained"]
        self.assertEqual(len(contained), 1)


class TestAuditSegmentsAgainstAnchors(unittest.TestCase):
    """Tests for audit_segments_against_anchors."""

    def test_no_warnings_when_anchors_match(self):
        text = "Hello world foo bar"
        segs = [
            {
                "segment_id": 1,
                "start_char": 0,
                "end_char": len(text),
                "start_exact": "Hello",
                "end_exact": "bar",
            }
        ]
        warns = text_segmenter.audit_segments_against_anchors(text, segs)
        self.assertEqual(warns, [])

    def test_start_mismatch_warning(self):
        text = "Hello world"
        segs = [
            {
                "segment_id": 1,
                "start_char": 0,
                "end_char": len(text),
                "start_exact": "Hxxxx",
                "end_exact": "world",
            }
        ]
        warns = text_segmenter.audit_segments_against_anchors(text, segs)
        issues = [w["issue"] for w in warns]
        self.assertIn("start_mismatch", issues)

    def test_end_mismatch_warning(self):
        text = "Hello world"
        segs = [
            {
                "segment_id": 1,
                "start_char": 0,
                "end_char": len(text),
                "start_exact": "Hello",
                "end_exact": "xxxxx",
            }
        ]
        warns = text_segmenter.audit_segments_against_anchors(text, segs)
        issues = [w["issue"] for w in warns]
        self.assertIn("end_mismatch", issues)

    def test_invalid_span_warning(self):
        text = "Hello world"
        segs = [
            {
                "segment_id": 99,
                "start_char": None,
                "end_char": None,
                "start_exact": "Hello",
                "end_exact": "world",
            }
        ]
        warns = text_segmenter.audit_segments_against_anchors(text, segs)
        self.assertEqual(len(warns), 1)
        self.assertEqual(warns[0]["issue"], "invalid_span")

    def test_no_anchors_no_warnings_for_valid_span(self):
        text = "Hello world"
        segs = [{"segment_id": 1, "start_char": 0, "end_char": len(text)}]
        warns = text_segmenter.audit_segments_against_anchors(text, segs)
        self.assertEqual(warns, [])

    def test_sample_parameter_respected(self):
        text = "A" * 200
        segs = [
            {
                "segment_id": 1,
                "start_char": 0,
                "end_char": len(text),
                "start_exact": "B" * 50,
                "end_exact": "C" * 50,
            }
        ]
        warns = text_segmenter.audit_segments_against_anchors(text, segs, sample=20)
        self.assertTrue(len(warns) > 0)


class TestSegmentsAuditor(unittest.TestCase):
    """Tests for segments_auditor."""

    def setUp(self):
        self.story = (
            "First paragraph text.\n\nSecond paragraph text.\n\nThird paragraph."
        )
        _, self.meta = text_segmenter.paragraph_text_indexer(self.story)

    def test_full_coverage_no_warnings(self):
        n = len(self.meta["canonical_text"])
        parsed_output = {
            "segments": [
                {
                    "segment_id": 1,
                    "start_char": 0,
                    "end_char": n,
                    "start_exact": self.meta["canonical_text"][:5],
                    "end_exact": self.meta["canonical_text"][-5:],
                }
            ]
        }
        result = text_segmenter.segments_auditor(parsed_output, self.story, self.meta)
        self.assertIn("coverage", result)
        self.assertIn("counts", result)
        self.assertEqual(result["coverage"]["coverage_pct"], 100.0)
        self.assertEqual(result["counts"]["gaps"], 0)

    def test_uses_canonical_text_from_index_meta(self):
        # index_meta has canonical_text; should be used rather than story_text
        story_with_cr = self.story.replace("\n", "\r\n")
        n = len(self.meta["canonical_text"])
        parsed_output = {
            "segments": [{"segment_id": 1, "start_char": 0, "end_char": n}]
        }
        result = text_segmenter.segments_auditor(
            parsed_output, story_with_cr, self.meta
        )
        self.assertEqual(result["coverage"]["total_chars"], n)

    def test_uses_story_text_when_no_canonical_in_meta(self):
        meta_no_canon = {"para_spans": self.meta["para_spans"]}
        n = len(self.story)
        parsed_output = {
            "segments": [{"segment_id": 1, "start_char": 0, "end_char": n}]
        }
        result = text_segmenter.segments_auditor(
            parsed_output, self.story, meta_no_canon
        )
        self.assertEqual(result["coverage"]["total_chars"], n)

    def test_empty_segments_zero_coverage(self):
        result = text_segmenter.segments_auditor({}, self.story, self.meta)
        self.assertEqual(result["coverage"]["coverage_pct"], 0.0)
        self.assertEqual(result["counts"]["segments_total"], 0)

    def test_result_structure(self):
        result = text_segmenter.segments_auditor({}, self.story, self.meta)
        for key in (
            "warnings",
            "missing_components",
            "overlapping_components",
            "coverage",
            "counts",
        ):
            self.assertIn(key, result)
        for key in ("covered_chars", "total_chars", "coverage_pct"):
            self.assertIn(key, result["coverage"])
        for key in (
            "segments_total",
            "segments_with_valid_spans",
            "warnings",
            "gaps",
            "overlaps",
        ):
            self.assertIn(key, result["counts"])

    def test_partial_coverage_gap_detected(self):
        n = len(self.meta["canonical_text"])
        # Only cover first half
        parsed_output = {
            "segments": [{"segment_id": 1, "start_char": 0, "end_char": n // 2}]
        }
        result = text_segmenter.segments_auditor(parsed_output, self.story, self.meta)
        self.assertGreater(result["counts"]["gaps"], 0)
        self.assertLess(result["coverage"]["coverage_pct"], 100.0)


class TestSingleNewlineParagraphFallback(unittest.TestCase):
    """WI-SEGMENT-0059: build_paragraph_index/paragraph_text_indexer must
    not collapse single-newline-formatted source text (no blank-line
    breaks at all) into one giant paragraph -- that forced every
    segment's anchor search across the entire document and silently
    produced overlapping offsets on real corpora/london stories."""

    def setUp(self):
        self.story = (
            "First line of the first paragraph.\n"
            "Second line, still paragraph one.\n"
            "First line of the second paragraph.\n"
            "First line of the third paragraph."
        )

    def test_build_paragraph_index_falls_back_to_single_newline(self):
        parts, spans = text_segmenter.build_paragraph_index(self.story, splitter="\n\n")
        self.assertEqual(len(parts), 4)
        self.assertGreater(len(spans), 1)
        for (start, end), expected in zip(spans, parts):
            self.assertEqual(self.story[start:end], expected)

    def test_build_paragraph_index_unaffected_when_blank_lines_present(self):
        """A story that genuinely has blank-line paragraph breaks must not
        be affected by the fallback -- splitting stays on "\\n\\n"."""
        story = "Paragraph one.\n\nParagraph two."
        parts, _ = text_segmenter.build_paragraph_index(story, splitter="\n\n")
        self.assertEqual(parts, ["Paragraph one.", "Paragraph two."])

    def test_build_paragraph_index_respects_non_newline_splitter(self):
        """A caller-supplied splitter with no newline at all must never
        trigger the fallback, even if it doesn't occur in the text."""
        story = "a|b|c"
        parts, _ = text_segmenter.build_paragraph_index(story, splitter="::")
        self.assertEqual(parts, ["a|b|c"])

    def test_paragraph_text_indexer_n_paragraphs_reflects_fallback(self):
        _, meta = text_segmenter.paragraph_text_indexer(self.story)
        self.assertEqual(meta["n_paragraphs"], 4)
        self.assertEqual(meta["splitter"], "\n")

    def test_paragraph_text_indexer_markers_use_consistent_delimiter(self):
        """The indexed text's paragraph markers must use the same
        delimiter build_paragraph_index actually split on, not the
        unconditional default -- otherwise the marked-up text shown to
        the model would misrepresent the real paragraph boundaries."""
        indexed_text, meta = text_segmenter.paragraph_text_indexer(self.story)
        self.assertEqual(indexed_text.count("[P"), meta["n_paragraphs"])
        # Markers are joined by the single-newline fallback, not "\n\n".
        self.assertNotIn("\n\n", indexed_text)

    def test_align_segment_search_range_is_narrow_after_fallback(self):
        """The whole point: with the fallback applied, a segment's anchor
        search range is one real paragraph, not the entire document."""
        _, meta = text_segmenter.paragraph_text_indexer(self.story)
        span = text_segmenter.align_segment(
            meta["canonical_text"],
            meta["para_spans"],
            start_par_id=3,
            end_par_id=3,
            start_exact="First line of the second paragraph.",
            end_exact="First line of the second paragraph.",
        )
        self.assertIsNotNone(span)
        s, e = span
        # Must not spill into paragraph 4's text.
        self.assertNotIn("third paragraph", self.story[s:e])


class TestAlignSegmentEndOffsetWithWhitespaceTolerantMatch(unittest.TestCase):
    """Regression test (WI-SEGMENT-0068, review finding PR #317):
    align_segment's end_exact branch used to compute
    `e_idx = e_pos + len(end_exact)`, which assumes the real matched
    text in story_text is exactly len(end_exact) characters long. That
    assumption breaks for a whitespace-tolerant match whose matched
    whitespace run is a different length than end_exact's own -- e.g.
    end_exact "quick brown" (single space) matched against source text
    "quick  brown" (double space) actually spans one character more
    than len(end_exact), so the old formula silently truncated the
    segment's last character."""

    def setUp(self):
        self.story = (
            "Para one text.\n\nThe quick  brown fox jumps over the lazy dog."
            "\n\nPara three."
        )
        _, self.spans = text_segmenter.build_paragraph_index(
            self.story, splitter="\n\n"
        )

    def test_end_offset_reflects_real_matched_span_not_anchor_length(self):
        end_exact = "quick brown"  # single space; source has a double space
        span = text_segmenter.align_segment(
            self.story,
            self.spans,
            start_par_id=2,
            end_par_id=2,
            start_exact="The quick",
            end_exact=end_exact,
        )
        self.assertIsNotNone(span)
        s, e = span
        # The old buggy formula (e_pos + len(end_exact)) would have cut
        # this one character short, truncating "brown" to "brow".
        self.assertEqual(self.story[s:e], "The quick  brown")
        self.assertTrue(self.story[s:e].endswith("brown"))


class TestAlignSegmentFailsOnEitherAnchor(unittest.TestCase):
    """WI-SEGMENT-0059: a genuinely unresolvable anchor must return None
    (alignment failure), never a silent fallback to a paragraph bound --
    for both start_exact and end_exact, not just end_exact (the original
    scope only covered end_exact; review finding, PR #255)."""

    def setUp(self):
        self.story = "Paragraph one text here.\n\nParagraph two text here."
        _, self.spans = text_segmenter.build_paragraph_index(
            self.story, splitter="\n\n"
        )

    def test_unresolvable_start_exact_returns_none(self):
        span = text_segmenter.align_segment(
            self.story,
            self.spans,
            start_par_id=1,
            end_par_id=1,
            start_exact="this text does not appear anywhere",
            end_exact="",
        )
        self.assertIsNone(span)

    def test_unresolvable_end_exact_returns_none(self):
        span = text_segmenter.align_segment(
            self.story,
            self.spans,
            start_par_id=1,
            end_par_id=1,
            start_exact="",
            end_exact="this text does not appear anywhere",
        )
        self.assertIsNone(span)

    def test_both_anchors_resolvable_still_succeeds(self):
        span = text_segmenter.align_segment(
            self.story,
            self.spans,
            start_par_id=1,
            end_par_id=1,
            start_exact="Paragraph one",
            end_exact="text here.",
        )
        self.assertIsNotNone(span)


class TestWiAnnotate0054RealTrialDataReplay(unittest.TestCase):
    """WI-SEGMENT-0059's own deterministic-replay acceptance criterion:
    replay the exact recorded segment metadata from WI-ANNOTATE-0054's 3
    real corpora/london trial failures (love_of_life, story_of_keesh,
    brown_wolf) through the fixed text_segmenter functions against the
    real story text, and confirm the fixed alignment no longer produces
    overlapping/degenerate offsets for that same recorded input.

    This deliberately reads real committed files
    (corpora/london/<story>/story.json and this trial's own committed
    scenes.json output under lcats/experimental/annotation_feasibility_
    trial/), unlike every other test in this module -- an intentional,
    narrow exception to this project's general test-isolation
    convention (never depend on the real data/corpora/ tree, per
    gather_promote_e2e_test.py's own documented rationale). This is not
    a generic corpus-processing test; it is a regression test tied to
    specific, permanently-committed real defect-evidence files that
    exist for exactly this purpose. If those files are ever pruned,
    this test should be updated or removed alongside them, not treated
    as a signal to add more real-corpus dependencies elsewhere.

    Does not test, and does not need to test, whether a fresh model
    call would segment any of these stories differently -- that is a
    separate, nondeterministic question outside this item's scope. It
    tests only whether replaying the exact same (already-recorded,
    now-fixed-in-place) input through the fixed alignment code produces
    a safe outcome: either valid non-overlapping offsets, or a clean
    raised failure -- never the old silent overlap/degenerate result.

    As of this writing, all 3 real cases raise (their recorded
    start_par_id/end_par_id/anchors were generated by the model against
    the OLD, buggy single-paragraph indexing, so replaying them against
    the FIXED, correctly-multi-paragraph indexing means the recorded
    anchors no longer resolve within their narrower, correct search
    range) -- none currently exercise the non-overlapping-success branch
    below. That branch is retained because a clean success is still a
    valid, in-scope outcome this fix permits (e.g. for a hypothetical
    future recorded case whose anchors do still resolve), not because
    it is expected for these specific 3 stories today.
    """

    REPO_ROOT = lcats_paths.find_pyproject_root(__file__).parent
    CORPORA_ROOT = REPO_ROOT / "corpora" / "london"
    TRIAL_ROOT = (
        REPO_ROOT
        / "lcats"
        / "experimental"
        / "annotation_feasibility_trial"
        / "source"
        / "trial"
    )

    # (story, whether the historical run degenerated to a single segment
    # spanning the whole document rather than overlapping segments)
    CASES = (
        ("love_of_life", False),
        ("story_of_keesh", False),
        ("brown_wolf", True),
    )

    def _load(self, story_name: str):
        story_path = self.CORPORA_ROOT / story_name / "story.json"
        scenes_path = self.TRIAL_ROOT / story_name / "scenes.json"
        if not story_path.is_file() or not scenes_path.is_file():
            # These files are this WI's own required regression evidence
            # (acceptance criteria), not an optional/environmental
            # dependency -- a missing file must fail the suite, not
            # silently skip it (AGENTS.md: "Do not suppress or skip
            # failing tests"; review finding, PR #269). A corpora/
            # restructuring or an experimental/ cleanup that removes
            # these files should break this test loudly, forcing a
            # deliberate decision about this coverage, not silently
            # losing it.
            self.fail(
                f"real trial evidence files not present for {story_name} "
                f"({story_path}, {scenes_path}) -- see class docstring. "
                "This is required regression evidence, not optional; if "
                "these files were intentionally moved or removed, update "
                "or remove this test explicitly rather than letting it "
                "silently stop exercising this coverage."
            )
        body = json.loads(story_path.read_text(encoding="utf-8"))["body"]
        segments = json.loads(scenes_path.read_text(encoding="utf-8"))["segments"]
        return body, segments

    def test_paragraph_collapse_no_longer_occurs(self):
        """The root cause: these stories have no blank-line breaks, so the
        old build_paragraph_index collapsed each to n_paragraphs=1. The
        fix must produce more than one real paragraph for all 3."""
        for story_name, _ in self.CASES:
            with self.subTest(story=story_name):
                body, _segments = self._load(story_name)
                _, meta = text_segmenter.paragraph_text_indexer(body)
                self.assertGreater(
                    meta["n_paragraphs"],
                    1,
                    f"{story_name}: still collapsing to a single paragraph",
                )

    def test_replay_never_silently_overlaps_or_degenerates(self):
        for story_name, was_degenerate in self.CASES:
            with self.subTest(story=story_name):
                body, segments = self._load(story_name)
                _, meta = text_segmenter.paragraph_text_indexer(body)
                parsed_output = {"segments": segments}

                try:
                    aligned = text_segmenter.segments_result_aligner(
                        parsed_output, meta["canonical_text"], meta
                    )
                except ValueError:
                    # A clean failure is an acceptable, safe outcome --
                    # the whole point of this fix is that a story is
                    # never silently shipped with wrong offsets.
                    continue

                # If alignment succeeded, the offsets must be genuinely
                # non-overlapping and non-degenerate -- recompute
                # directly from the returned segments, not by trusting
                # any historical characterization.
                aligned_segments = sorted(
                    aligned["segments"], key=lambda s: s["segment_id"]
                )
                prev_end = -1
                overlap_chars = 0
                for seg in aligned_segments:
                    start, end = seg["start_char"], seg["end_char"]
                    if start < prev_end:
                        overlap_chars += prev_end - start
                    prev_end = max(prev_end, end)
                self.assertEqual(
                    overlap_chars,
                    0,
                    f"{story_name}: fixed alignment still overlaps by "
                    f"{overlap_chars} chars",
                )
                if was_degenerate:
                    # brown_wolf's historical failure mode was a single
                    # segment spanning the whole document -- if alignment
                    # now succeeds, it must not still be degenerate.
                    self.assertFalse(
                        len(aligned_segments) == 1
                        and aligned_segments[0]["start_char"] == 0
                        and aligned_segments[0]["end_char"] == len(body),
                        f"{story_name}: still a single whole-document segment",
                    )


class TestWiSegment0068RealCaseReplay(unittest.TestCase):
    """WI-SEGMENT-0068's own acceptance criterion: deterministic replay of
    the exact real-world failure captured 2026-08-14 during a live
    WI-EVENT-0033 verification smoke test, against the real committed
    story text -- following text_segmenter_test.py's own established
    TestWiAnnotate0054RealTrialDataReplay pattern of testing against real
    corpora/ text rather than only synthetic strings, though this case
    needs no separate committed sidecar fixture: the failing anchor text
    itself was captured directly from a live model response and is
    reproduced here as a literal, against corpora/mass_quantities'
    already-permanently-committed story file.

    The model's segment-3 end_exact came back as "glowered suspiciously
    at Mater and the\\nneighbors." -- every word correct, but with a
    hallucinated line-wrap newline where the real source text has a
    plain space. Before this WI's fix, find_anchor_in_range's
    whitespace-tolerant fallback found this normalized match internally
    but then discarded it by re-searching with the original,
    non-normalized anchor string -- returning None and causing the
    whole story's alignment (and therefore the whole story) to be
    excluded, even though the model's segmentation was substantively
    correct.
    """

    REPO_ROOT = lcats_paths.find_pyproject_root(__file__).parent
    STORY_PATH = (
        REPO_ROOT / "corpora" / "mass_quantities" / "junior__abernathy" / "story.json"
    )

    def _load_body(self) -> str:
        if not self.STORY_PATH.is_file():
            # Required regression evidence, not optional -- see class
            # docstring and TestWiAnnotate0054RealTrialDataReplay's own
            # identical rationale for failing loudly rather than
            # skipping when this file is missing.
            self.fail(
                f"real story file not present at {self.STORY_PATH} -- "
                "see class docstring. If this file was intentionally "
                "moved or removed, update or remove this test explicitly."
            )
        from lcats.analysis import story_analysis

        data = json.loads(self.STORY_PATH.read_text(encoding="utf-8"))
        return text_segmenter.canonicalize_text(
            story_analysis.coerce_text(data["body"])
        )

    def test_captured_anchor_with_hallucinated_newline_now_resolves(self):
        body = self._load_body()
        anchor = "glowered suspiciously at Mater and the\nneighbors."
        # Confirm this replay actually exercises the fallback, not the
        # exact-match fast path -- the whole point of this regression
        # test is that exact matching fails here.
        self.assertEqual(
            body.find(anchor), -1, "test setup: anchor must not exact-match"
        )

        result = text_segmenter.find_anchor_in_range(body, anchor, 0, len(body))

        expected = body.find("glowered suspiciously at Mater and the neighbors.")
        self.assertNotEqual(
            expected, -1, "test setup: real text must contain this span"
        )
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
