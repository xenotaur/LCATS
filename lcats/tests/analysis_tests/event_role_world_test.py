"""Unit tests for lcats.analysis.event_role_world."""

import unittest

from lcats.llm import backend as llm_backend
from lcats.analysis.event_role_world import baseline
from lcats.analysis.event_role_world import entity_extractor
from lcats.analysis.event_role_world import event_extractor
from lcats.analysis.event_role_world import nlp_backend
from lcats.analysis.event_role_world import processor
from lcats.analysis.event_role_world import schema
from lcats.analysis.event_role_world import surface_feature_extractor


def _spacy_model_available() -> bool:
    """Return True iff the "en_core_web_sm" spaCy model is installed.

    Per the LCATS-specific offline/no-network-CI constraint recorded in
    project/design/event-role-world-surface-feature-nlp-evaluation.md, tests
    that require a downloaded NLP model must skip (not fail) in a clean
    checkout where the model hasn't been fetched.
    """
    try:
        import spacy

        spacy.load("en_core_web_sm")
        return True
    except Exception:  # noqa: BLE001 - any load failure means "unavailable"
        return False


_SPACY_AVAILABLE = _spacy_model_available()


class _SequencedFakeBackend:
    """LLMBackend test double returning a fixed sequence of tool results.

    Unlike lcats.llm.fake_backend.FakeBackend (one fixed response for every
    call), this returns a different tool_result per call in order — needed
    to test a pipeline that makes multiple distinct LLM-backed passes.
    """

    def __init__(self, tool_results):
        self._results = list(tool_results)
        self.calls = []

    def complete(self, **kwargs):
        self.calls.append(kwargs)
        result = self._results.pop(0)
        return llm_backend.BackendResponse(
            text="",
            tool_result=result,
            model="fake-1.0",
            input_tokens=10,
            output_tokens=5,
            raw=None,
        )


# ---------------------------------------------------------------------------
# Tests: schema
# ---------------------------------------------------------------------------


class TestEvidenceSpan(unittest.TestCase):
    def test_validate_accepts_matching_span(self):
        text = "The machine hummed."
        span = schema.EvidenceSpan(start_char=4, end_char=11, quote="machine")
        self.assertIsNone(span.validate(text))

    def test_validate_rejects_out_of_bounds(self):
        text = "short"
        span = schema.EvidenceSpan(start_char=0, end_char=100, quote="short")
        self.assertIsNotNone(span.validate(text))

    def test_validate_rejects_text_mismatch(self):
        text = "The machine hummed."
        span = schema.EvidenceSpan(start_char=4, end_char=11, quote="wrong text here")
        error = span.validate(text)
        self.assertIsNotNone(error)
        self.assertIn("mismatch", error)

    def test_validate_rejects_empty_span(self):
        span = schema.EvidenceSpan(start_char=5, end_char=5, quote="")
        self.assertIsNotNone(span.validate("some text"))


class TestResolveEvidence(unittest.TestCase):
    def test_finds_quote(self):
        text = "The old machine hummed."
        evidence = schema.resolve_evidence("machine", text)
        self.assertIsNotNone(evidence)
        self.assertEqual(evidence.quote, "machine")
        self.assertEqual(text[evidence.start_char : evidence.end_char], "machine")

    def test_returns_none_for_missing_quote(self):
        self.assertIsNone(schema.resolve_evidence("not present", "The machine hummed."))

    def test_returns_none_for_empty_quote(self):
        self.assertIsNone(schema.resolve_evidence("", "The machine hummed."))


class TestValidateSegmentAnnotation(unittest.TestCase):
    def test_clean_annotation_has_no_errors(self):
        text = "The machine hummed."
        evidence = schema.EvidenceSpan(start_char=4, end_char=11, quote="machine")
        entity = schema.Entity(
            entity_id="e1",
            canonical_name="the machine",
            entity_type="machine_or_artifact",
            mention_ids=["m1"],
        )
        mention = schema.EntityMention(
            mention_id="m1", entity_id="e1", text="machine", evidence=evidence
        )
        annotation = schema.SegmentWorldAnnotation(
            segment_id=1, entities=[entity], mentions=[mention]
        )
        errors = schema.validate_segment_annotation(annotation, text)
        self.assertEqual(errors, [])

    def test_dangling_mention_entity_reference_is_an_error(self):
        text = "The machine hummed."
        evidence = schema.EvidenceSpan(start_char=4, end_char=11, quote="machine")
        mention = schema.EntityMention(
            mention_id="m1",
            entity_id="unknown_entity",
            text="machine",
            evidence=evidence,
        )
        annotation = schema.SegmentWorldAnnotation(segment_id=1, mentions=[mention])
        errors = schema.validate_segment_annotation(annotation, text)
        self.assertTrue(any("unknown entity" in e for e in errors))

    def test_dangling_event_anchor_reference_is_an_error(self):
        text = "The machine hummed."
        evidence = schema.EvidenceSpan(start_char=4, end_char=11, quote="machine")
        event = schema.Event(
            event_id="ev1",
            predicate="hummed",
            event_type="sound",
            evidence=evidence,
            temporal_anchor_ids=["missing_anchor"],
        )
        annotation = schema.SegmentWorldAnnotation(segment_id=1, events=[event])
        errors = schema.validate_segment_annotation(annotation, text)
        self.assertTrue(any("unknown anchor" in e for e in errors))

    def test_misaligned_evidence_is_an_error(self):
        text = "The machine hummed."
        bad_evidence = schema.EvidenceSpan(start_char=0, end_char=7, quote="machine")
        event = schema.Event(
            event_id="ev1",
            predicate="hummed",
            event_type="sound",
            evidence=bad_evidence,
        )
        annotation = schema.SegmentWorldAnnotation(segment_id=1, events=[event])
        errors = schema.validate_segment_annotation(annotation, text)
        self.assertTrue(any("mismatch" in e for e in errors))


# ---------------------------------------------------------------------------
# Tests: nlp_backend
# ---------------------------------------------------------------------------


class TestFakeNLPBackend(unittest.TestCase):
    def test_returns_fixed_sentences_and_records_calls(self):
        token = nlp_backend.TokenRecord(
            text="hi",
            lemma="hi",
            upos="INTJ",
            xpos="UH",
            feats="",
            head_index=0,
            deprel="root",
        )
        fixed = [nlp_backend.SentenceRecord(tokens=[token])]
        backend = nlp_backend.FakeNLPBackend(sentences=fixed)

        result = backend.analyze("hi")

        self.assertEqual(result, fixed)
        self.assertEqual(backend.calls, ["hi"])

    def test_default_sentences_is_empty_list(self):
        backend = nlp_backend.FakeNLPBackend()
        self.assertEqual(backend.analyze("anything"), [])


class TestTokenRecord(unittest.TestCase):
    def test_to_dict_round_trips_fields(self):
        token = nlp_backend.TokenRecord(
            text="ran",
            lemma="run",
            upos="VERB",
            xpos="VBD",
            feats="Tense=Past",
            head_index=0,
            deprel="root",
        )
        d = token.to_dict()
        self.assertEqual(d["text"], "ran")
        self.assertEqual(d["upos"], "VERB")
        self.assertEqual(d["head_index"], 0)


# ---------------------------------------------------------------------------
# Tests: surface_feature_extractor
# ---------------------------------------------------------------------------


class TestExtractSurfaceFeatures(unittest.TestCase):
    def test_counts_words_and_sentences_from_backend_tokens(self):
        tok = lambda t: nlp_backend.TokenRecord(  # noqa: E731
            text=t, lemma=t, upos="X", xpos="X", feats="", head_index=0, deprel="root"
        )
        sentences = [
            nlp_backend.SentenceRecord(tokens=[tok("The"), tok("cat"), tok("ran")]),
            nlp_backend.SentenceRecord(tokens=[tok("It"), tok("stopped")]),
        ]
        backend = nlp_backend.FakeNLPBackend(sentences=sentences)

        features = surface_feature_extractor.extract_surface_features(
            "The cat ran. It stopped.", backend, backend_name="fake"
        )

        self.assertEqual(features.word_count, 5)
        self.assertEqual(features.sentence_count, 2)
        self.assertEqual(features.avg_sentence_length, 2.5)
        self.assertEqual(features.backend_name, "fake")
        self.assertEqual(len(features.tokens), 5)

    def test_empty_text_produces_zeroed_features(self):
        backend = nlp_backend.FakeNLPBackend()
        features = surface_feature_extractor.extract_surface_features("", backend)
        self.assertEqual(features.word_count, 0)
        self.assertEqual(features.sentence_count, 0)
        self.assertEqual(features.avg_sentence_length, 0.0)
        self.assertEqual(features.avg_word_length, 0.0)

    def test_whitespace_only_text_does_not_call_backend(self):
        backend = nlp_backend.FakeNLPBackend()
        surface_feature_extractor.extract_surface_features("   \n  ", backend)
        self.assertEqual(backend.calls, [])


class TestMakeNlpBackend(unittest.TestCase):
    def test_rejects_unknown_backend_name(self):
        with self.assertRaises(ValueError):
            surface_feature_extractor.make_nlp_backend("not_a_real_backend")


def _stanza_model_available() -> bool:
    """Return True iff the Stanza English model has been downloaded."""
    try:
        import stanza

        stanza.Pipeline(
            lang="en", processors="tokenize,pos,lemma,depparse", download_method=None
        )
        return True
    except Exception:  # noqa: BLE001 - any load failure means "unavailable"
        return False


class TestRealNLPBackends(unittest.TestCase):
    """Direct integration coverage for both supported real backends.

    Each backend's test skips independently if its model isn't downloaded,
    so a checkout with only one model present still gets partial coverage
    rather than an all-or-nothing skip.
    """

    @unittest.skipUnless(
        _SPACY_AVAILABLE,
        "en_core_web_sm not installed; run `python -m spacy download en_core_web_sm`",
    )
    def test_spacy_backend_produces_normalized_tokens(self):
        backend = nlp_backend.SpacyBackend()
        sentences = backend.analyze("The old machine hummed.")
        self.assertEqual(len(sentences), 1)
        tokens = sentences[0].tokens
        self.assertTrue(any(t.upos == "VERB" for t in tokens))
        # Exactly one token should be the sentence root (head_index == 0).
        self.assertEqual(sum(1 for t in tokens if t.head_index == 0), 1)

    @unittest.skipUnless(
        _stanza_model_available(),
        "Stanza 'en' model not downloaded; run stanza.download('en')",
    )
    def test_stanza_backend_produces_normalized_tokens(self):
        backend = nlp_backend.StanzaBackend()
        sentences = backend.analyze("The old machine hummed.")
        self.assertEqual(len(sentences), 1)
        tokens = sentences[0].tokens
        self.assertTrue(any(t.upos == "VERB" for t in tokens))
        self.assertEqual(sum(1 for t in tokens if t.head_index == 0), 1)


# ---------------------------------------------------------------------------
# Tests: entity_extractor
# ---------------------------------------------------------------------------


class TestBuildEntities(unittest.TestCase):
    def test_builds_entity_and_mention_with_resolved_evidence(self):
        text = "The old machine hummed."
        tool_result = {
            "entities": [
                {
                    "entity_id": "e1",
                    "canonical_name": "the machine",
                    "entity_type": "machine_or_artifact",
                    "aliases": ["it"],
                    "actant_roles": ["instrument"],
                    "confidence": 0.9,
                    "mentions": [
                        {
                            "mention_id": "m1",
                            "text": "the machine",
                            "quote": "old machine",
                        }
                    ],
                }
            ]
        }

        entities, mentions = entity_extractor.build_entities(tool_result, text)

        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0].entity_id, "e1")
        self.assertEqual(entities[0].mention_ids, ["m1"])
        self.assertEqual(len(mentions), 1)
        self.assertEqual(mentions[0].evidence.quote, "old machine")

    def test_drops_mention_with_unresolvable_quote(self):
        text = "The old machine hummed."
        tool_result = {
            "entities": [
                {
                    "entity_id": "e1",
                    "canonical_name": "the machine",
                    "entity_type": "machine_or_artifact",
                    "mentions": [
                        {"mention_id": "m1", "text": "x", "quote": "not in the text"}
                    ],
                }
            ]
        }

        entities, mentions = entity_extractor.build_entities(tool_result, text)

        self.assertEqual(mentions, [])
        self.assertEqual(entities[0].mention_ids, [])

    def test_empty_tool_result_produces_no_entities(self):
        entities, mentions = entity_extractor.build_entities({}, "some text")
        self.assertEqual(entities, [])
        self.assertEqual(mentions, [])


# ---------------------------------------------------------------------------
# Tests: event_extractor
# ---------------------------------------------------------------------------


class TestBuildEventsAndAnchors(unittest.TestCase):
    def test_builds_event_with_semantic_role_and_anchors(self):
        text = "The machine hummed in the pit for decades."
        tool_result = {
            "temporal_anchors": [
                {"anchor_id": "t1", "text": "decades", "quote": "for decades"}
            ],
            "spatial_anchors": [
                {"anchor_id": "s1", "text": "the pit", "quote": "in the pit"}
            ],
            "events": [
                {
                    "event_id": "ev1",
                    "predicate": "hummed",
                    "event_type": "sound_emission",
                    "quote": "hummed",
                    "modality": "actual",
                    "confidence": 0.8,
                    "temporal_anchor_ids": ["t1"],
                    "spatial_anchor_ids": ["s1"],
                    "semantic_roles": [
                        {
                            "role": "agent",
                            "filler_entity_id": "e1",
                            "quote": "The machine",
                        }
                    ],
                }
            ],
        }

        events, temporal_anchors, spatial_anchors = (
            event_extractor.build_events_and_anchors(tool_result, text)
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_id, "ev1")
        self.assertEqual(len(events[0].semantic_roles), 1)
        self.assertEqual(events[0].semantic_roles[0].filler_entity_id, "e1")
        self.assertEqual(len(temporal_anchors), 1)
        self.assertEqual(len(spatial_anchors), 1)

    def test_drops_event_with_unresolvable_quote(self):
        text = "The machine hummed."
        tool_result = {
            "events": [
                {
                    "event_id": "ev1",
                    "predicate": "hummed",
                    "event_type": "sound",
                    "quote": "not present in text",
                }
            ]
        }
        events, _, _ = event_extractor.build_events_and_anchors(tool_result, text)
        self.assertEqual(events, [])

    def test_drops_semantic_role_with_unresolvable_quote_but_keeps_event(self):
        text = "The machine hummed."
        tool_result = {
            "events": [
                {
                    "event_id": "ev1",
                    "predicate": "hummed",
                    "event_type": "sound",
                    "quote": "hummed",
                    "semantic_roles": [
                        {"role": "agent", "filler_entity_id": "e1", "quote": "nowhere"}
                    ],
                }
            ]
        }
        events, _, _ = event_extractor.build_events_and_anchors(tool_result, text)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].semantic_roles, [])


# ---------------------------------------------------------------------------
# Tests: baseline
# ---------------------------------------------------------------------------


class TestMakeFixedTokenChunks(unittest.TestCase):
    def test_empty_text_produces_no_chunks(self):
        self.assertEqual(baseline.make_fixed_token_chunks(""), [])

    def test_chunks_cover_full_text_contiguously(self):
        text = "The old machine hummed in the pit. " * 20
        chunks = baseline.make_fixed_token_chunks(text, chunk_size_tokens=30)

        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0]["start_char"], 0)
        self.assertEqual(chunks[-1]["end_char"], len(text))
        for prev, nxt in zip(chunks, chunks[1:]):
            self.assertEqual(prev["end_char"], nxt["start_char"])

    def test_chunks_are_labeled_fixed_chunk(self):
        chunks = baseline.make_fixed_token_chunks(
            "some short text here", chunk_size_tokens=2
        )
        self.assertTrue(all(c["segment_type"] == "fixed_chunk" for c in chunks))


class TestSummarizeAndCompare(unittest.TestCase):
    def _annotation(self, word_count, n_entities, n_events):
        return schema.SegmentWorldAnnotation(
            segment_id=1,
            surface_features=schema.SurfaceFeatures(
                word_count=word_count,
                sentence_count=1,
                avg_sentence_length=word_count,
                avg_word_length=4.0,
            ),
            entities=[
                schema.Entity(
                    entity_id=f"e{i}", canonical_name=f"e{i}", entity_type="x"
                )
                for i in range(n_entities)
            ],
            events=[
                schema.Event(
                    event_id=f"ev{i}",
                    predicate="p",
                    event_type="x",
                    evidence=schema.EvidenceSpan(0, 1, "x"),
                )
                for i in range(n_events)
            ],
        )

    def test_summarize_computes_per_1000_word_rates(self):
        annotations = [self._annotation(word_count=500, n_entities=1, n_events=2)]
        summary = baseline.summarize_annotations(annotations)
        self.assertEqual(summary["total_word_count"], 500)
        self.assertEqual(summary["entities_per_1000_words"], 2.0)
        self.assertEqual(summary["events_per_1000_words"], 4.0)

    def test_summarize_handles_zero_words_without_dividing_by_zero(self):
        annotations = [self._annotation(word_count=0, n_entities=0, n_events=0)]
        summary = baseline.summarize_annotations(annotations)
        self.assertEqual(summary["entities_per_1000_words"], 0.0)

    def test_compare_returns_both_strategies(self):
        seg = [self._annotation(word_count=500, n_entities=1, n_events=1)]
        chunk = [self._annotation(word_count=500, n_entities=2, n_events=2)]
        comparison = baseline.compare_chunking_strategies(seg, chunk)
        self.assertIn("segment", comparison)
        self.assertIn("fixed_chunk", comparison)
        self.assertEqual(comparison["fixed_chunk"]["entities_per_1000_words"], 4.0)


# ---------------------------------------------------------------------------
# Tests: processor (end-to-end with fakes)
# ---------------------------------------------------------------------------


@unittest.skipUnless(
    _SPACY_AVAILABLE,
    "en_core_web_sm not installed; run `python -m spacy download en_core_web_sm`",
)
class TestProcessSegments(unittest.TestCase):
    def test_end_to_end_pipeline_with_fakes(self):
        segment_text = "The old machine hummed in the pit. It had run for decades."

        entity_tool_result = {
            "entities": [
                {
                    "entity_id": "e1",
                    "canonical_name": "the machine",
                    "entity_type": "machine_or_artifact",
                    "aliases": ["it"],
                    "actant_roles": ["instrument"],
                    "confidence": 0.9,
                    "mentions": [
                        {
                            "mention_id": "m1",
                            "text": "the machine",
                            "quote": "old machine",
                        }
                    ],
                }
            ]
        }
        event_tool_result = {
            "temporal_anchors": [
                {"anchor_id": "t1", "text": "decades", "quote": "for decades"}
            ],
            "spatial_anchors": [
                {"anchor_id": "s1", "text": "the pit", "quote": "in the pit"}
            ],
            "events": [
                {
                    "event_id": "ev1",
                    "predicate": "hummed",
                    "event_type": "sound_emission",
                    "quote": "hummed",
                    "modality": "actual",
                    "confidence": 0.8,
                    "temporal_anchor_ids": [],
                    "spatial_anchor_ids": ["s1"],
                    "semantic_roles": [
                        {
                            "role": "agent",
                            "filler_entity_id": "e1",
                            "quote": "old machine",
                        }
                    ],
                }
            ],
        }
        fake = _SequencedFakeBackend([entity_tool_result, event_tool_result])
        segments = [{"segment_id": 1, "start_char": 0, "end_char": len(segment_text)}]

        result = processor.process_segments(
            segment_text, segments, nlp_backend_name="spacy", llm_backend=fake
        )

        self.assertEqual(len(result["segments"]), 1)
        seg = result["segments"][0]
        self.assertEqual(len(seg["entities"]), 1)
        self.assertEqual(len(seg["events"]), 1)
        self.assertEqual(len(seg["temporal_anchors"]), 1)
        self.assertEqual(len(seg["spatial_anchors"]), 1)
        self.assertEqual(seg["validation_errors"], [])

        # Exactly one LLM call for entities, one for events - not more.
        self.assertEqual(len(fake.calls), 2)

        # Cost/usage reporting: token counts, model, and elapsed time per
        # pass - not just call counts (WI-EVENT-0024 acceptance criterion).
        usage_by_pass = {u["pass_name"]: u for u in result["usage"]}
        self.assertIn("surface_feature", usage_by_pass)
        self.assertIn("entity", usage_by_pass)
        self.assertIn("event_anchor", usage_by_pass)
        self.assertFalse(usage_by_pass["surface_feature"]["is_llm_backed"])
        self.assertTrue(usage_by_pass["entity"]["is_llm_backed"])
        self.assertEqual(usage_by_pass["entity"]["input_tokens"], 10)
        self.assertEqual(usage_by_pass["entity"]["model"], "fake-1.0")

    def test_entity_ids_from_stage_3_are_passed_to_stage_4_5_prompt(self):
        segment_text = "The machine hummed."
        entity_tool_result = {
            "entities": [
                {
                    "entity_id": "e1",
                    "canonical_name": "the machine",
                    "entity_type": "machine_or_artifact",
                    "mentions": [
                        {"mention_id": "m1", "text": "machine", "quote": "machine"}
                    ],
                }
            ]
        }
        event_tool_result = {"events": []}
        fake = _SequencedFakeBackend([entity_tool_result, event_tool_result])
        segments = [{"segment_id": 1, "start_char": 0, "end_char": len(segment_text)}]

        processor.process_segments(
            segment_text, segments, nlp_backend_name="spacy", llm_backend=fake
        )

        second_call_content = fake.calls[1]["messages"][0]["content"]
        self.assertIn("e1", second_call_content)

    def test_skips_segment_without_char_offsets(self):
        fake = _SequencedFakeBackend([])
        segments = [{"segment_id": 1, "start_char": None, "end_char": None}]

        result = processor.process_segments(
            "some text", segments, nlp_backend_name="spacy", llm_backend=fake
        )

        self.assertEqual(result["segments"], [])
        self.assertEqual(fake.calls, [])


if __name__ == "__main__":
    unittest.main()
