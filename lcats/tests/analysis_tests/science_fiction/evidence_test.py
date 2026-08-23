"""Tests for shared science-fiction evidence records."""

import dataclasses
import unittest

from lcats.analysis.science_fiction import evidence
from lcats.analysis.science_fiction import preparation


def _prepared_story():
    body = "\n\n".join(
        [
            "The city lifted on engines at dawn.",
            "Mara measured the blue exhaust and revised the failed equation.",
            "The old farms below froze as the city shadow crossed them.",
            "Mara feared the engines, but the council called them ordinary.",
            "The city lifted on engines at dawn.",
        ]
    )
    return preparation.prepare_story_data(
        {"name": "Lifted City", "body": body},
        story_path="/tmp/collection/lifted-city/story.json",
        config=preparation.PreparationConfig(
            whole_story_max_chars=10,
            chunk_target_chars=90,
            chunk_max_chars=180,
            chunk_overlap_paragraphs=1,
        ),
    )


class StaticExtractor:
    def __init__(self, candidates):
        self.candidates = candidates
        self.requests = []

    def extract(self, request):
        self.requests.append(request)
        return self.candidates


class ChunkAwareExtractor:
    def __init__(self, quote):
        self.quote = quote
        self.emitting_chunk_id = None

    def extract(self, request):
        if "p00005" not in request.paragraph_ids:
            return []
        self.emitting_chunk_id = request.chunk_id
        return [
            {
                "evidence_type": "storyworld_change",
                "quote": self.quote,
                "paraphrase": "The mobile city recurs as a storyworld change.",
                "confidence": 0.8,
            }
        ]


class EvidenceTest(unittest.TestCase):
    def test_request_from_chunk_is_backend_independent(self):
        prepared = _prepared_story()

        request = evidence.EvidenceExtractionRequest.from_chunk(
            prepared, prepared.chunks[0]
        )

        self.assertEqual(prepared.story_hash, request.story_hash)
        self.assertEqual(prepared.chunks[0].chunk_id, request.chunk_id)
        self.assertEqual("science-fiction-evidence-output-v1", request.schema_version)
        self.assertEqual(
            list(request.paragraph_ids), request.to_dict()["paragraph_ids"]
        )

    def test_locates_exact_quote_against_stable_paragraph_anchor(self):
        prepared = _prepared_story()
        candidate = evidence.EvidenceCandidate(
            evidence_type="scientific_or_technical_explanation",
            quote="blue exhaust",
            paraphrase="A measurable engine exhaust is used in technical reasoning.",
            confidence=0.82,
            source_chunk_id=prepared.chunks[0].chunk_id,
            raw_id="raw-1",
        )

        evidence_set = evidence.build_evidence_set(prepared, [candidate])

        self.assertEqual(1, len(evidence_set.records))
        self.assertFalse(evidence_set.quarantined)
        record = evidence_set.records[0]
        self.assertEqual(("p00002",), record.anchor.paragraph_ids)
        self.assertEqual(
            "blue exhaust",
            prepared.normalized_text[record.anchor.start_char : record.anchor.end_char],
        )
        self.assertEqual("raw-1", record.provenance[0].raw_id)

    def test_uses_candidate_offsets_when_repeated_quote_is_ambiguous(self):
        prepared = _prepared_story()
        repeated = "The city lifted on engines at dawn."
        second_start = prepared.normalized_text.rfind(repeated)
        candidate = evidence.EvidenceCandidate(
            evidence_type="storyworld_change",
            quote=repeated,
            paraphrase="A mobile city changes the storyworld.",
            confidence=0.9,
            start_char=second_start,
            end_char=second_start + len(repeated),
        )

        evidence_set = evidence.build_evidence_set(prepared, [candidate])

        self.assertEqual(1, len(evidence_set.records))
        self.assertEqual(("p00005",), evidence_set.records[0].anchor.paragraph_ids)

    def test_invalid_candidate_offsets_are_quarantined(self):
        prepared = _prepared_story()
        candidate = evidence.EvidenceCandidate(
            evidence_type="storyworld_change",
            quote="dawn",
            paraphrase="A malformed offset must not become an accepted anchor.",
            confidence=0.8,
            start_char=-4,
            end_char=len(prepared.normalized_text),
        )

        evidence_set = evidence.build_evidence_set(prepared, [candidate])

        self.assertFalse(evidence_set.records)
        self.assertEqual(1, len(evidence_set.quarantined))
        self.assertIn("could not be located", evidence_set.quarantined[0].reason)

    def test_declared_paragraph_constraints_are_not_silently_ignored(self):
        prepared = _prepared_story()
        candidate = evidence.EvidenceCandidate(
            evidence_type="storyworld_change",
            quote="blue exhaust",
            paraphrase="The quote exists, but not in the claimed paragraph.",
            confidence=0.8,
            paragraph_ids=("p00001",),
        )

        evidence_set = evidence.build_evidence_set(prepared, [candidate])

        self.assertFalse(evidence_set.records)
        self.assertEqual(1, len(evidence_set.quarantined))
        self.assertIn("could not be located", evidence_set.quarantined[0].reason)

    def test_fallback_search_rejects_wrong_paragraph_in_broad_bounds(self):
        prepared = _prepared_story()
        candidate = evidence.EvidenceCandidate(
            evidence_type="scientific_or_technical_explanation",
            quote="blue exhaust",
            paraphrase="The quote sits between the claimed paragraphs.",
            confidence=0.8,
            paragraph_ids=("p00001", "p00003"),
        )

        evidence_set = evidence.build_evidence_set(prepared, [candidate])

        self.assertFalse(evidence_set.records)
        self.assertEqual(1, len(evidence_set.quarantined))
        self.assertIn("could not be located", evidence_set.quarantined[0].reason)

    def test_null_collection_fields_are_quarantined_not_raised(self):
        prepared = _prepared_story()
        candidate = {
            "evidence_type": "character_reaction",
            "quote": "Mara feared the engines",
            "paraphrase": "A character reacts with fear.",
            "confidence": 0.8,
            "paragraph_ids": None,
            "entity_ids": None,
            "event_ids": None,
        }

        evidence_set = evidence.build_evidence_set(prepared, [candidate])

        self.assertFalse(evidence_set.records)
        self.assertEqual(1, len(evidence_set.quarantined))
        self.assertIn(
            "paragraph_ids must be an array", evidence_set.quarantined[0].reason
        )

    def test_non_string_collection_items_are_quarantined(self):
        prepared = _prepared_story()
        candidate = {
            "evidence_type": "character_reaction",
            "quote": "Mara feared the engines",
            "paraphrase": "A character reacts with fear.",
            "confidence": 0.8,
            "paragraph_ids": ["p00001"],
            "entity_ids": [123],
            "event_ids": [None],
        }

        evidence_set = evidence.build_evidence_set(prepared, [candidate])

        self.assertFalse(evidence_set.records)
        self.assertEqual(1, len(evidence_set.quarantined))
        self.assertIn("entity_ids must be an array", evidence_set.quarantined[0].reason)

    def test_null_required_scalar_fields_are_quarantined(self):
        prepared = preparation.prepare_story_data(
            {"name": "None Story", "body": "None"},
            story_path="/tmp/collection/none-story/story.json",
        )
        candidate = {
            "evidence_type": "storyworld_change",
            "quote": None,
            "paraphrase": None,
            "confidence": 0.8,
        }

        evidence_set = evidence.build_evidence_set(prepared, [candidate])

        self.assertFalse(evidence_set.records)
        self.assertEqual(1, len(evidence_set.quarantined))
        self.assertIn("quote must be a string", evidence_set.quarantined[0].reason)

    def test_unlocatable_or_malformed_evidence_is_quarantined(self):
        prepared = _prepared_story()
        valid = {
            "evidence_type": "catastrophe",
            "quote": "old farms below froze",
            "paraphrase": "The engine-driven city causes agricultural damage.",
            "confidence": 0.7,
        }
        invalid_type = {
            "evidence_type": "knight_score",
            "quote": "city shadow",
            "paraphrase": "This would be theory-specific and must not enter here.",
            "confidence": 0.5,
        }
        unlocatable = {
            "evidence_type": "character_reaction",
            "quote": "a sentence that is not present",
            "paraphrase": "The character reacts.",
            "confidence": 0.4,
        }

        evidence_set = evidence.build_evidence_set(
            prepared, [valid, invalid_type, unlocatable, "not-a-dict"]
        )

        self.assertEqual(1, len(evidence_set.records))
        self.assertEqual(3, len(evidence_set.quarantined))
        self.assertIn(
            "unsupported neutral evidence type", evidence_set.quarantined[0].reason
        )
        self.assertIn("could not be located", evidence_set.quarantined[1].reason)
        self.assertIn("candidate must be an object", evidence_set.quarantined[2].reason)

    def test_overlap_duplicates_merge_provenance(self):
        prepared = _prepared_story()
        candidates = [
            evidence.EvidenceCandidate(
                evidence_type="storyworld_change",
                quote="old farms below froze",
                paraphrase="The moving city harms farms below.",
                confidence=0.4,
                source_chunk_id="c0001",
                raw_id="a",
            ),
            evidence.EvidenceCandidate(
                evidence_type="storyworld_change",
                quote="old farms below froze",
                paraphrase="The moving city harms farms below.",
                confidence=0.9,
                source_chunk_id="c0002",
                raw_id="b",
            ),
        ]

        evidence_set = evidence.build_evidence_set(prepared, candidates)

        self.assertEqual(1, len(evidence_set.records))
        self.assertEqual(0.9, evidence_set.records[0].confidence)
        self.assertEqual(
            ["a", "b"],
            sorted(item.raw_id for item in evidence_set.records[0].provenance),
        )

    def test_overlap_conflicts_are_preserved(self):
        prepared = _prepared_story()
        candidates = [
            evidence.EvidenceCandidate(
                evidence_type="reader_facing_contrast",
                quote="council called them ordinary",
                paraphrase="The text contrasts reader strangeness with local normality.",
                confidence=0.8,
                raw_id="ordinary-reader",
            ),
            evidence.EvidenceCandidate(
                evidence_type="reader_facing_contrast",
                quote="council called them ordinary",
                paraphrase="The phrase only shows a civic judgment.",
                confidence=0.6,
                raw_id="ordinary-civic",
            ),
        ]

        evidence_set = evidence.build_evidence_set(prepared, candidates)

        self.assertEqual(2, len(evidence_set.records))
        self.assertEqual(1, len(evidence_set.conflicts))
        self.assertEqual(
            sorted(record.evidence_id for record in evidence_set.records),
            sorted(evidence_set.conflicts[0].evidence_ids),
        )

    def test_output_ids_are_stable_when_candidates_are_reordered(self):
        prepared = _prepared_story()
        candidates = [
            evidence.EvidenceCandidate(
                evidence_type="catastrophe",
                quote="old farms below froze",
                paraphrase="The city causes environmental harm.",
                confidence=0.7,
                raw_id="catastrophe",
            ),
            evidence.EvidenceCandidate(
                evidence_type="character_reaction",
                quote="Mara feared the engines",
                paraphrase="A character reacts with fear.",
                confidence=0.8,
                raw_id="reaction",
            ),
        ]

        first = evidence.build_evidence_set(prepared, candidates)
        second = evidence.build_evidence_set(prepared, list(reversed(candidates)))

        self.assertEqual(first.evidence_set_id, second.evidence_set_id)
        self.assertEqual(
            [record.evidence_id for record in first.records],
            [record.evidence_id for record in second.records],
        )

    def test_output_ids_are_stable_when_quarantined_candidates_are_reordered(self):
        prepared = _prepared_story()
        candidates = [
            {
                "evidence_type": "storyworld_change",
                "quote": "not present",
                "paraphrase": "This quote cannot be located.",
                "confidence": 0.7,
                "raw_id": "missing",
            },
            {
                "evidence_type": "character_reaction",
                "quote": "Mara feared the engines",
                "paraphrase": "A character reacts with fear.",
                "confidence": 0.8,
                "paragraph_ids": None,
                "raw_id": "malformed",
            },
        ]

        first = evidence.build_evidence_set(prepared, candidates)
        second = evidence.build_evidence_set(prepared, list(reversed(candidates)))

        self.assertEqual(first.evidence_set_id, second.evidence_set_id)
        self.assertEqual(
            ["missing", "malformed"],
            [item.candidate.raw_id for item in first.quarantined],
        )

    def test_extractor_absence_of_erw_does_not_block(self):
        prepared = _prepared_story()
        extractor = StaticExtractor(
            [
                evidence.EvidenceCandidate(
                    evidence_type="inquiry_or_scientific_method",
                    quote="measured the blue exhaust",
                    paraphrase="Measurement supports an inquiry process.",
                    confidence=0.75,
                    source_chunk_id=prepared.chunks[0].chunk_id,
                )
            ]
        )

        evidence_set = evidence.extract_evidence_set(extractor, prepared)

        self.assertGreaterEqual(len(extractor.requests), 1)
        self.assertEqual(1, len(evidence_set.records))
        self.assertFalse(evidence_set.quarantined)

    def test_extractor_candidates_inherit_emitting_chunk_id(self):
        prepared = _prepared_story()
        quote = "The city lifted on engines at dawn."
        extractor = ChunkAwareExtractor(quote)

        evidence_set = evidence.extract_evidence_set(extractor, prepared)

        self.assertEqual(1, len(evidence_set.records))
        record = evidence_set.records[0]
        self.assertEqual(("p00005",), record.anchor.paragraph_ids)
        self.assertEqual(
            extractor.emitting_chunk_id, record.provenance[0].source_chunk_id
        )

    def test_optional_erw_adapter_uses_duck_typed_sf_tags(self):
        prepared = _prepared_story()

        @dataclasses.dataclass
        class FakeSpan:
            start_char: int
            end_char: int
            quote: str
            paragraph_ids: list[str]

        @dataclasses.dataclass
        class FakeTag:
            tag_id: str
            tag: str
            evidence: FakeSpan
            linked_entity_ids: list[str]
            linked_event_ids: list[str]
            confidence: float

        @dataclasses.dataclass
        class FakeAnnotation:
            sf_tags: list[FakeTag]
            explanations: list

        quote = "old farms below froze"
        start = prepared.normalized_text.index(quote)
        annotation = FakeAnnotation(
            sf_tags=[
                FakeTag(
                    tag_id="tag-1",
                    tag="anomaly_or_novum",
                    evidence=FakeSpan(
                        start_char=start,
                        end_char=start + len(quote),
                        quote=quote,
                        paragraph_ids=["p00003"],
                    ),
                    linked_entity_ids=["city"],
                    linked_event_ids=["freeze"],
                    confidence=0.66,
                )
            ],
            explanations=[],
        )

        candidates = evidence.adapt_erw_annotation(
            annotation, source_chunk_id=prepared.chunks[0].chunk_id
        )
        evidence_set = evidence.build_evidence_set(prepared, candidates)

        self.assertEqual(1, len(candidates))
        self.assertEqual("erw", candidates[0].source)
        self.assertEqual("storyworld_change", candidates[0].evidence_type)
        self.assertEqual(1, len(evidence_set.records))
        self.assertEqual(("city",), evidence_set.records[0].entity_ids)

    def test_erw_adapter_translates_segment_local_offsets(self):
        prepared = _prepared_story()

        @dataclasses.dataclass
        class FakeSpan:
            start_char: int
            end_char: int
            quote: str
            paragraph_ids: list[str]

        @dataclasses.dataclass
        class FakeExplanation:
            explanation_id: str
            topic: str
            evidence: FakeSpan
            linked_entity_ids: list[str]
            linked_event_ids: list[str]
            confidence: float

        @dataclasses.dataclass
        class FakeAnnotation:
            sf_tags: list
            explanations: list[FakeExplanation]

        quote = "Mara measured the blue exhaust"
        segment_start = prepared.normalized_text.index("Mara measured")
        annotation = FakeAnnotation(
            sf_tags=[],
            explanations=[
                FakeExplanation(
                    explanation_id="exp-1",
                    topic="engine measurement",
                    evidence=FakeSpan(
                        start_char=0,
                        end_char=len(quote),
                        quote=quote,
                        paragraph_ids=["p00002"],
                    ),
                    linked_entity_ids=[],
                    linked_event_ids=[],
                    confidence=0.7,
                )
            ],
        )

        candidates = evidence.adapt_erw_annotation(
            annotation, segment_start_char=segment_start
        )
        evidence_set = evidence.build_evidence_set(prepared, candidates)

        self.assertEqual(1, len(evidence_set.records))
        self.assertEqual(segment_start, evidence_set.records[0].anchor.start_char)

    def test_erw_adapter_quarantines_null_quote(self):
        prepared = preparation.prepare_story_data(
            {"name": "None Story", "body": "None"},
            story_path="/tmp/collection/none-story/story.json",
        )

        @dataclasses.dataclass
        class FakeSpan:
            quote: object
            paragraph_ids: list[str]

        @dataclasses.dataclass
        class FakeTag:
            tag_id: str
            tag: str
            evidence: FakeSpan
            linked_entity_ids: list[str]
            linked_event_ids: list[str]
            confidence: float

        @dataclasses.dataclass
        class FakeAnnotation:
            sf_tags: list[FakeTag]
            explanations: list

        annotation = FakeAnnotation(
            sf_tags=[
                FakeTag(
                    tag_id="tag-null",
                    tag="anomaly_or_novum",
                    evidence=FakeSpan(quote=None, paragraph_ids=[]),
                    linked_entity_ids=[],
                    linked_event_ids=[],
                    confidence=0.8,
                )
            ],
            explanations=[],
        )

        candidates = evidence.adapt_erw_annotation(annotation)
        evidence_set = evidence.build_evidence_set(prepared, candidates)

        self.assertFalse(evidence_set.records)
        self.assertEqual(1, len(evidence_set.quarantined))
        self.assertIn("quote must be a string", evidence_set.quarantined[0].reason)

    def test_erw_adapter_quarantines_null_linked_ids(self):
        prepared = _prepared_story()

        @dataclasses.dataclass
        class FakeSpan:
            quote: str
            paragraph_ids: list[str]

        @dataclasses.dataclass
        class FakeTag:
            tag_id: str
            tag: str
            evidence: FakeSpan
            linked_entity_ids: object
            linked_event_ids: object
            confidence: float

        @dataclasses.dataclass
        class FakeAnnotation:
            sf_tags: list[FakeTag]
            explanations: list

        annotation = FakeAnnotation(
            sf_tags=[
                FakeTag(
                    tag_id="tag-null-ids",
                    tag="anomaly_or_novum",
                    evidence=FakeSpan(
                        quote="old farms below froze", paragraph_ids=["p00003"]
                    ),
                    linked_entity_ids=None,
                    linked_event_ids=None,
                    confidence=0.8,
                )
            ],
            explanations=[],
        )

        candidates = evidence.adapt_erw_annotation(annotation)
        evidence_set = evidence.build_evidence_set(prepared, candidates)

        self.assertFalse(evidence_set.records)
        self.assertEqual(1, len(evidence_set.quarantined))
        self.assertIn("entity_ids must be an array", evidence_set.quarantined[0].reason)

    def test_erw_adapter_quarantines_non_string_linked_id_items(self):
        prepared = _prepared_story()

        @dataclasses.dataclass
        class FakeSpan:
            quote: str
            paragraph_ids: list[str]

        @dataclasses.dataclass
        class FakeTag:
            tag_id: str
            tag: str
            evidence: FakeSpan
            linked_entity_ids: list[object]
            linked_event_ids: list[object]
            confidence: float

        @dataclasses.dataclass
        class FakeAnnotation:
            sf_tags: list[FakeTag]
            explanations: list

        annotation = FakeAnnotation(
            sf_tags=[
                FakeTag(
                    tag_id="tag-bad-ids",
                    tag="anomaly_or_novum",
                    evidence=FakeSpan(
                        quote="old farms below froze", paragraph_ids=["p00003"]
                    ),
                    linked_entity_ids=[123],
                    linked_event_ids=[None],
                    confidence=0.8,
                )
            ],
            explanations=[],
        )

        candidates = evidence.adapt_erw_annotation(annotation)
        evidence_set = evidence.build_evidence_set(prepared, candidates)

        self.assertFalse(evidence_set.records)
        self.assertEqual(1, len(evidence_set.quarantined))
        self.assertIn("entity_ids must be an array", evidence_set.quarantined[0].reason)


if __name__ == "__main__":
    unittest.main()
