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


if __name__ == "__main__":
    unittest.main()
