"""Unit tests for lcats.analysis.text_indexing."""

import unittest

from lcats.analysis import text_segmenter


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
        """If end < start, it clamps to a single paragraph instead of crashing."""
        parts, spans = text_segmenter.build_paragraph_index(self.story, splitter="\n\n")
        p2_start, p2_end = spans[1]

        start_exact = self.p2[:6]
        end_exact = self.p2[-6:]

        # Intentionally reversed: start_par_id=3, end_par_id=2 -> clamped to 3 (or 2) per implementation
        span = text_segmenter.align_segment(
            self.story,
            spans,
            start_par_id=3,
            end_par_id=2,
            start_exact=start_exact,
            end_exact=end_exact,
        )
        # May fall back to bounds if anchors don't fit paragraph 3; just ensure it returns a valid span.
        self.assertIsNotNone(span)
        s, e = span
        self.assertGreater(e, s)
        self.assertLessEqual(e, len(self.story))

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

    def test_segments_result_aligner_is_resilient_to_missing_fields(self):
        """Segments missing required fields should be left unchanged (no crash)."""
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
        aligned = text_segmenter.segments_result_aligner(
            parsed_output, self.story, meta
        )
        seg = aligned["segments"][0]
        self.assertNotIn("start_char", seg)
        self.assertNotIn("end_char", seg)


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

    def test_ws_normalized_fallback_returns_none_when_not_remappable(self):
        # Exact match fails (text has double space before "brown").
        # WS-normalized match succeeds ("quick brown" found in normalized text).
        # But exact anchor "quick brown" not found verbatim in original text slice
        # → returns None from the heuristic remap branch.
        result = text_segmenter.find_anchor_in_range(
            self.text, "quick brown", 0, len(self.text)
        )
        self.assertIsNone(result)

    def test_ws_normalized_fallback_not_found_returns_none(self):
        # Neither exact nor ws-normalized match is found.
        result = text_segmenter.find_anchor_in_range(
            self.text, "zebra giraffe", 0, len(self.text)
        )
        self.assertIsNone(result)


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
        self.story = "First paragraph text.\n\nSecond paragraph text.\n\nThird paragraph."
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
            "segments": [
                {"segment_id": 1, "start_char": 0, "end_char": n}
            ]
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


if __name__ == "__main__":
    unittest.main()
