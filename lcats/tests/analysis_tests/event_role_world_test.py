"""Unit tests for lcats.analysis.event_role_world."""

import unittest
import unittest.mock

from lcats.llm import backend as llm_backend
from lcats.analysis.event_role_world import baseline
from lcats.analysis.event_role_world import discourse_extractor
from lcats.analysis.event_role_world import entity_extractor
from lcats.analysis.event_role_world import event_extractor
from lcats.analysis.event_role_world import export
from lcats.analysis.event_role_world import hypothesis_extractor
from lcats.analysis.event_role_world import nlp_backend
from lcats.analysis.event_role_world import processor
from lcats.analysis.event_role_world import relation_extractor
from lcats.analysis.event_role_world import schema
from lcats.analysis.event_role_world import story_relation_extractor
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

    def test_dangling_hypothesis_subject_reference_is_an_error(self):
        text = "Maria believed the machine was alive."
        evidence = schema.EvidenceSpan(
            start_char=6, end_char=38, quote="believed the machine was alive"
        )
        hypothesis = schema.Hypothesis(
            hypothesis_id="h1",
            hypothesis_type="belief",
            proposition_or_target="the machine is alive",
            evidence=evidence,
            subject_entity_id="unknown_entity",
        )
        annotation = schema.SegmentWorldAnnotation(
            segment_id=1, hypotheses=[hypothesis]
        )
        errors = schema.validate_segment_annotation(annotation, text)
        self.assertTrue(any("unknown subject entity" in e for e in errors))


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

        # The entity's only mention failed to resolve, leaving it with no
        # grounded evidence at all - it must be dropped entirely rather than
        # surfaced as an ungrounded "ghost" entity with an empty mention list.
        self.assertEqual(mentions, [])
        self.assertEqual(entities, [])

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
# Tests: relation_extractor (stage 6)
# ---------------------------------------------------------------------------


class TestBuildRelations(unittest.TestCase):
    def test_builds_explicit_relation_in_main_list(self):
        text = "The machine hummed, which caused the lights to flicker."
        tool_result = {
            "relations": [
                {
                    "relation_id": "r1",
                    "source_event_id": "ev1",
                    "target_event_id": "ev2",
                    "relation_type": "causes",
                    "quote": "hummed",
                    "certainty": "explicit",
                    "confidence": 0.9,
                }
            ]
        }
        relations, weakly_inferred = relation_extractor.build_relations(
            tool_result, text
        )
        self.assertEqual(len(relations), 1)
        self.assertEqual(relations[0].relation_id, "r1")
        self.assertEqual(relations[0].certainty, "explicit")
        self.assertEqual(weakly_inferred, [])

    def test_partitions_weakly_inferred_relation_into_separate_list(self):
        text = "The machine hummed."
        tool_result = {
            "relations": [
                {
                    "relation_id": "r1",
                    "source_event_id": "ev1",
                    "target_event_id": "ev2",
                    "relation_type": "motivates",
                    "quote": "hummed",
                    "certainty": "weakly_inferred",
                }
            ]
        }
        relations, weakly_inferred = relation_extractor.build_relations(
            tool_result, text
        )
        self.assertEqual(relations, [])
        self.assertEqual(len(weakly_inferred), 1)
        self.assertEqual(weakly_inferred[0].certainty, "weakly_inferred")

    def test_drops_relation_with_unresolvable_quote(self):
        text = "The machine hummed."
        tool_result = {
            "relations": [
                {
                    "relation_id": "r1",
                    "source_event_id": "ev1",
                    "target_event_id": "ev2",
                    "relation_type": "causes",
                    "quote": "not present in text",
                }
            ]
        }
        relations, weakly_inferred = relation_extractor.build_relations(
            tool_result, text
        )
        self.assertEqual(relations, [])
        self.assertEqual(weakly_inferred, [])

    def test_empty_tool_result_produces_no_relations(self):
        relations, weakly_inferred = relation_extractor.build_relations({}, "some text")
        self.assertEqual(relations, [])
        self.assertEqual(weakly_inferred, [])


# ---------------------------------------------------------------------------
# Tests: discourse_extractor (stage 7)
# ---------------------------------------------------------------------------


class TestBuildDiscourse(unittest.TestCase):
    def test_builds_speech_act_explanation_and_sf_tag(self):
        text = (
            '"Reroute the plasma conduits," she said, since the core was overheating.'
        )
        tool_result = {
            "speech_acts": [
                {
                    "speech_act_id": "sp1",
                    "act_type": "command",
                    "quote": "Reroute the plasma conduits",
                    "speaker_entity_id": "e1",
                    "addressee_entity_ids": ["e2"],
                }
            ],
            "explanations": [
                {
                    "explanation_id": "ex1",
                    "topic": "overheating core",
                    "mechanism_or_rationale_type": "technical_operation",
                    "quote": "the core was overheating",
                    "linked_entity_ids": ["e2"],
                }
            ],
            "sf_tags": [
                {
                    "tag_id": "sf1",
                    "tag": "technology_as_agent",
                    "quote": "plasma conduits",
                    "linked_entity_ids": ["e2"],
                    "status": "extractive",
                }
            ],
        }
        speech_acts, explanations, sf_tags = discourse_extractor.build_discourse(
            tool_result, text
        )
        self.assertEqual(len(speech_acts), 1)
        self.assertEqual(speech_acts[0].speaker_entity_id, "e1")
        self.assertEqual(len(explanations), 1)
        self.assertEqual(
            explanations[0].mechanism_or_rationale_type, "technical_operation"
        )
        self.assertEqual(len(sf_tags), 1)
        self.assertEqual(sf_tags[0].status, "extractive")

    def test_defaults_sf_tag_status_to_hypothesis(self):
        text = "The old machine hummed."
        tool_result = {
            "sf_tags": [
                {"tag_id": "sf1", "tag": "anomaly_or_novum", "quote": "machine"}
            ]
        }
        _, _, sf_tags = discourse_extractor.build_discourse(tool_result, text)
        self.assertEqual(sf_tags[0].status, "hypothesis")

    def test_drops_items_with_unresolvable_quotes(self):
        text = "The machine hummed."
        tool_result = {
            "speech_acts": [
                {"speech_act_id": "sp1", "act_type": "assertion", "quote": "nowhere"}
            ],
            "explanations": [
                {
                    "explanation_id": "ex1",
                    "topic": "x",
                    "mechanism_or_rationale_type": "x",
                    "quote": "nowhere",
                }
            ],
            "sf_tags": [{"tag_id": "sf1", "tag": "x", "quote": "nowhere"}],
        }
        speech_acts, explanations, sf_tags = discourse_extractor.build_discourse(
            tool_result, text
        )
        self.assertEqual(speech_acts, [])
        self.assertEqual(explanations, [])
        self.assertEqual(sf_tags, [])

    def test_empty_tool_result_produces_nothing(self):
        speech_acts, explanations, sf_tags = discourse_extractor.build_discourse(
            {}, "some text"
        )
        self.assertEqual(speech_acts, [])
        self.assertEqual(explanations, [])
        self.assertEqual(sf_tags, [])

    def test_same_quote_can_be_claimed_by_multiple_layers(self):
        """A single passage can legitimately be both a speech act AND an
        explanation AND an SF tag at once. A shared cursor across layers
        would let the first layer's claim consume the only occurrence of
        the quote, silently dropping the later layers' otherwise-valid
        claims on that same span."""
        text = '"Reroute the plasma conduits," she said.'
        tool_result = {
            "speech_acts": [
                {
                    "speech_act_id": "sp1",
                    "act_type": "command",
                    "quote": "Reroute the plasma conduits",
                }
            ],
            "explanations": [
                {
                    "explanation_id": "ex1",
                    "topic": "plasma routing",
                    "mechanism_or_rationale_type": "technical_operation",
                    "quote": "Reroute the plasma conduits",
                }
            ],
            "sf_tags": [
                {
                    "tag_id": "sf1",
                    "tag": "technology_as_agent",
                    "quote": "Reroute the plasma conduits",
                }
            ],
        }
        speech_acts, explanations, sf_tags = discourse_extractor.build_discourse(
            tool_result, text
        )
        self.assertEqual(len(speech_acts), 1)
        self.assertEqual(len(explanations), 1)
        self.assertEqual(len(sf_tags), 1)


# ---------------------------------------------------------------------------
# Tests: hypothesis_extractor (stage 8, optional)
# ---------------------------------------------------------------------------


class TestBuildHypotheses(unittest.TestCase):
    def test_builds_hypothesis_with_subject_and_linked_entity(self):
        text = "Maria believed the machine was alive."
        tool_result = {
            "hypotheses": [
                {
                    "hypothesis_id": "h1",
                    "hypothesis_type": "belief",
                    "proposition_or_target": "the machine is alive",
                    "quote": "believed the machine was alive",
                    "subject_entity_id": "e2",
                    "linked_entity_ids": ["e1"],
                    "confidence": 0.7,
                }
            ]
        }
        hypotheses = hypothesis_extractor.build_hypotheses(tool_result, text)
        self.assertEqual(len(hypotheses), 1)
        self.assertEqual(hypotheses[0].hypothesis_type, "belief")
        self.assertEqual(hypotheses[0].subject_entity_id, "e2")
        self.assertEqual(hypotheses[0].linked_entity_ids, ["e1"])

    def test_drops_hypothesis_with_unresolvable_quote(self):
        text = "Maria believed the machine was alive."
        tool_result = {
            "hypotheses": [
                {
                    "hypothesis_id": "h1",
                    "hypothesis_type": "belief",
                    "proposition_or_target": "x",
                    "quote": "not present in text",
                }
            ]
        }
        hypotheses = hypothesis_extractor.build_hypotheses(tool_result, text)
        self.assertEqual(hypotheses, [])

    def test_empty_tool_result_produces_no_hypotheses(self):
        self.assertEqual(hypothesis_extractor.build_hypotheses({}, "some text"), [])

    def test_repeated_quote_resolves_to_successive_occurrences(self):
        text = "First she feared it. Later, she feared it again."
        tool_result = {
            "hypotheses": [
                {
                    "hypothesis_id": "h1",
                    "hypothesis_type": "emotion_appraisal",
                    "proposition_or_target": "fear, first instance",
                    "quote": "she feared it",
                },
                {
                    "hypothesis_id": "h2",
                    "hypothesis_type": "emotion_appraisal",
                    "proposition_or_target": "fear, second instance",
                    "quote": "she feared it",
                },
            ]
        }
        hypotheses = hypothesis_extractor.build_hypotheses(tool_result, text)
        self.assertEqual(len(hypotheses), 2)
        self.assertLess(
            hypotheses[0].evidence.start_char, hypotheses[1].evidence.start_char
        )


# ---------------------------------------------------------------------------
# Tests: story_relation_extractor (WI-EVENT-0029, story-level cross-segment)
# ---------------------------------------------------------------------------


class TestBuildEventIndex(unittest.TestCase):
    def test_builds_one_line_per_event_across_segments(self):
        evidence1 = schema.EvidenceSpan(0, 6, "hummed")
        evidence2 = schema.EvidenceSpan(0, 8, "shut off")
        seg1 = schema.SegmentWorldAnnotation(
            segment_id=1,
            events=[
                schema.Event(
                    event_id="ev1",
                    predicate="hummed",
                    event_type="sound_emission",
                    evidence=evidence1,
                )
            ],
        )
        seg2 = schema.SegmentWorldAnnotation(
            segment_id=2,
            events=[
                schema.Event(
                    event_id="ev1",
                    predicate="shut off",
                    event_type="mechanical_failure",
                    evidence=evidence2,
                )
            ],
        )
        story = schema.reconcile_story_annotations("s1", [seg1, seg2])

        index_text = story_relation_extractor.build_event_index(story)

        self.assertIn("1:ev1", index_text)
        self.assertIn("2:ev1", index_text)
        self.assertIn("hummed", index_text)
        self.assertIn("shut off", index_text)

    def test_empty_story_produces_empty_index(self):
        story = schema.StoryWorldAnnotation(story_id="s1")
        self.assertEqual(story_relation_extractor.build_event_index(story), "")


class TestBuildStoryRelations(unittest.TestCase):
    def _story_with_two_segment_events(self):
        evidence1 = schema.EvidenceSpan(0, 6, "hummed")
        evidence2 = schema.EvidenceSpan(0, 8, "shut off")
        seg1 = schema.SegmentWorldAnnotation(
            segment_id=1,
            events=[
                schema.Event(
                    event_id="ev1",
                    predicate="hummed",
                    event_type="sound_emission",
                    evidence=evidence1,
                )
            ],
        )
        seg2 = schema.SegmentWorldAnnotation(
            segment_id=2,
            events=[
                schema.Event(
                    event_id="ev1",
                    predicate="shut off",
                    event_type="mechanical_failure",
                    evidence=evidence2,
                )
            ],
        )
        return schema.reconcile_story_annotations("s1", [seg1, seg2])

    def test_builds_cross_segment_relation_reusing_source_evidence(self):
        story = self._story_with_two_segment_events()
        tool_result = {
            "relations": [
                {
                    "relation_id": "r1",
                    "source_event_id": "1:ev1",
                    "target_event_id": "2:ev1",
                    "relation_type": "causes",
                    "certainty": "explicit",
                    "confidence": 0.9,
                }
            ]
        }

        relations, weakly_inferred = story_relation_extractor.build_story_relations(
            tool_result, story
        )

        self.assertEqual(len(relations), 1)
        self.assertEqual(relations[0].relation_id, "story:r1")
        self.assertEqual(relations[0].source_event_id, "1:ev1")
        self.assertEqual(relations[0].target_event_id, "2:ev1")
        # Evidence is reused directly from the source event's own span.
        self.assertEqual(relations[0].evidence.quote, "hummed")
        self.assertEqual(weakly_inferred, [])

    def test_partitions_weakly_inferred_relation_into_separate_list(self):
        story = self._story_with_two_segment_events()
        tool_result = {
            "relations": [
                {
                    "relation_id": "r1",
                    "source_event_id": "1:ev1",
                    "target_event_id": "2:ev1",
                    "relation_type": "motivates",
                    "certainty": "weakly_inferred",
                }
            ]
        }

        relations, weakly_inferred = story_relation_extractor.build_story_relations(
            tool_result, story
        )

        self.assertEqual(relations, [])
        self.assertEqual(len(weakly_inferred), 1)
        self.assertEqual(weakly_inferred[0].certainty, "weakly_inferred")

    def test_drops_relation_referencing_unknown_event_id(self):
        story = self._story_with_two_segment_events()
        tool_result = {
            "relations": [
                {
                    "relation_id": "r1",
                    "source_event_id": "1:ev1",
                    "target_event_id": "9:does_not_exist",
                    "relation_type": "causes",
                }
            ]
        }

        relations, weakly_inferred = story_relation_extractor.build_story_relations(
            tool_result, story
        )

        self.assertEqual(relations, [])
        self.assertEqual(weakly_inferred, [])

    def test_drops_relation_whose_endpoints_are_in_the_same_segment(self):
        """This pass's contract is cross-segment only; a same-segment claim
        (the model violating its own instructions) must be discarded rather
        than silently accepted, since same-segment links are already
        covered by the existing per-segment pass."""
        story = self._story_with_two_segment_events()
        tool_result = {
            "relations": [
                {
                    "relation_id": "r1",
                    "source_event_id": "1:ev1",
                    "target_event_id": "1:ev1",
                    "relation_type": "precedes",
                }
            ]
        }

        relations, weakly_inferred = story_relation_extractor.build_story_relations(
            tool_result, story
        )

        self.assertEqual(relations, [])
        self.assertEqual(weakly_inferred, [])

    def test_empty_tool_result_produces_no_relations(self):
        story = self._story_with_two_segment_events()
        relations, weakly_inferred = story_relation_extractor.build_story_relations(
            {}, story
        )
        self.assertEqual(relations, [])
        self.assertEqual(weakly_inferred, [])

    def test_relation_id_is_qualified_with_story_prefix(self):
        """Qualifying the ID this way means cross_segment_relations can
        never collide with a per-segment relation's raw ID once both
        appear in the same exported table — no runtime deduplication is
        needed (see StoryWorldAnnotation.cross_segment_relations)."""
        story = self._story_with_two_segment_events()
        tool_result = {
            "relations": [
                {
                    "relation_id": "r1",
                    "source_event_id": "1:ev1",
                    "target_event_id": "2:ev1",
                    "relation_type": "causes",
                }
            ]
        }
        relations, _ = story_relation_extractor.build_story_relations(
            tool_result, story
        )
        self.assertTrue(relations[0].relation_id.startswith("story:"))

    def test_deduplicates_repeated_raw_relation_id_within_one_call(self):
        """The tool schema does not forbid the model from returning the same
        relation_id twice in one call; a naive qualify-and-store would
        produce two "story:r1" entries, inflating the density count. This
        must be deduplicated before storing/counting, not merely flagged
        later by validate_story_annotation."""
        story = self._story_with_two_segment_events()
        tool_result = {
            "relations": [
                {
                    "relation_id": "r1",
                    "source_event_id": "1:ev1",
                    "target_event_id": "2:ev1",
                    "relation_type": "causes",
                },
                {
                    "relation_id": "r1",
                    "source_event_id": "1:ev1",
                    "target_event_id": "2:ev1",
                    "relation_type": "causes",
                },
            ]
        }
        relations, weakly_inferred = story_relation_extractor.build_story_relations(
            tool_result, story
        )
        self.assertEqual(len(relations), 1)
        self.assertEqual(weakly_inferred, [])


# ---------------------------------------------------------------------------
# Tests: schema.reconcile_story_annotations / validate_story_annotation (stage 9)
# ---------------------------------------------------------------------------


class TestReconcileStoryAnnotations(unittest.TestCase):
    def _entity(self, entity_id, canonical_name, aliases=None, mention_ids=None):
        return schema.Entity(
            entity_id=entity_id,
            canonical_name=canonical_name,
            entity_type="x",
            aliases=list(aliases or []),
            mention_ids=list(mention_ids or []),
        )

    def test_merges_entities_with_same_canonical_name_case_insensitively(self):
        seg1 = schema.SegmentWorldAnnotation(
            segment_id=1, entities=[self._entity("e1", "the machine")]
        )
        seg2 = schema.SegmentWorldAnnotation(
            segment_id=2, entities=[self._entity("e1", "The Machine")]
        )

        story = schema.reconcile_story_annotations("s1", [seg1, seg2])

        self.assertEqual(len(story.entities), 1)
        self.assertEqual(
            story.entity_alias_map,
            {"1:e1": story.entities[0].entity_id, "2:e1": story.entities[0].entity_id},
        )
        self.assertEqual(story.validation_errors, [])

    def test_merges_entities_via_alias_overlap_not_just_canonical_name(self):
        """Two segments give the same participant different canonical
        names ("Elizabeth" vs "Liz"), but the second segment's alias list
        overlaps the first segment's canonical name — matching on
        canonical_name alone would never notice this and would fragment
        the participant into two global entities."""
        seg1 = schema.SegmentWorldAnnotation(
            segment_id=1, entities=[self._entity("e1", "Elizabeth")]
        )
        seg2 = schema.SegmentWorldAnnotation(
            segment_id=2,
            entities=[self._entity("e1", "Liz", aliases=["Elizabeth"])],
        )

        story = schema.reconcile_story_annotations("s1", [seg1, seg2])

        self.assertEqual(len(story.entities), 1)
        merged = story.entities[0]
        self.assertEqual(merged.canonical_name, "Elizabeth")
        self.assertIn("Liz", merged.aliases)
        self.assertEqual(
            story.entity_alias_map, {"1:e1": merged.entity_id, "2:e1": merged.entity_id}
        )

    def test_preserves_segment_qualified_mention_ids_on_merge(self):
        """Story-level merged entities must not drop Entity.mention_ids —
        they should be segment-qualified so they stay traceable back to
        segment_annotations[*].mentions without colliding across segments
        that both use e.g. mention_id "m1"."""
        seg1 = schema.SegmentWorldAnnotation(
            segment_id=1,
            entities=[self._entity("e1", "the machine", mention_ids=["m1"])],
        )
        seg2 = schema.SegmentWorldAnnotation(
            segment_id=2,
            entities=[self._entity("e1", "The Machine", mention_ids=["m1"])],
        )

        story = schema.reconcile_story_annotations("s1", [seg1, seg2])

        self.assertEqual(len(story.entities), 1)
        self.assertEqual(sorted(story.entities[0].mention_ids), ["1:m1", "2:m1"])

    def test_keeps_distinct_entities_separate(self):
        seg1 = schema.SegmentWorldAnnotation(
            segment_id=1, entities=[self._entity("e1", "the machine")]
        )
        seg2 = schema.SegmentWorldAnnotation(
            segment_id=2, entities=[self._entity("e1", "the captain")]
        )

        story = schema.reconcile_story_annotations("s1", [seg1, seg2])

        self.assertEqual(len(story.entities), 2)

    def test_qualifies_relation_event_ids_with_segment_id(self):
        evidence = schema.EvidenceSpan(start_char=0, end_char=1, quote="x")
        relation = schema.EventRelation(
            relation_id="r1",
            source_event_id="ev1",
            target_event_id="ev2",
            relation_type="causes",
            evidence=evidence,
            certainty="explicit",
        )
        seg = schema.SegmentWorldAnnotation(segment_id=7, relations=[relation])

        story = schema.reconcile_story_annotations("s1", [seg])

        self.assertEqual(len(story.relations), 1)
        self.assertEqual(story.relations[0].source_event_id, "7:ev1")
        self.assertEqual(story.relations[0].target_event_id, "7:ev2")

    def test_entity_alias_merge_across_segments_does_not_disturb_relation_qualification(
        self,
    ):
        """Entity reconciliation (which does span segments) and relation
        qualification (which does not — see the "Known limitation" note on
        StoryWorldAnnotation) are independent: merging the same entity seen
        under different segments must not affect how a same-segment
        relation's event IDs get qualified. This is NOT a test of a
        genuinely cross-segment relation (source event in one segment,
        target event in another) — the current per-segment stage-6
        relation_extractor cannot produce one, since it only ever sees its
        own segment's event IDs."""
        evidence = schema.EvidenceSpan(start_char=0, end_char=1, quote="x")
        event = schema.Event(
            event_id="ev1", predicate="p", event_type="x", evidence=evidence
        )
        relation = schema.EventRelation(
            relation_id="r1",
            source_event_id="ev1",
            target_event_id="ev1",
            relation_type="precedes",
            evidence=evidence,
            certainty="weakly_inferred",
        )
        seg1 = schema.SegmentWorldAnnotation(
            segment_id=1, entities=[self._entity("e1", "the machine")], events=[event]
        )
        seg2 = schema.SegmentWorldAnnotation(
            segment_id=2,
            entities=[self._entity("e1", "The Machine")],
            events=[event],
            weakly_inferred_relations=[relation],
        )

        story = schema.reconcile_story_annotations("s1", [seg1, seg2])

        # Entities from both segments merged into one global entity.
        self.assertEqual(len(story.entities), 1)
        global_id = story.entities[0].entity_id
        self.assertEqual(story.entity_alias_map["1:e1"], global_id)
        self.assertEqual(story.entity_alias_map["2:e1"], global_id)
        # The weakly_inferred relation (from segment 2) is qualified with
        # segment 2's ID, not segment 1's — entirely local to segment 2,
        # unaffected by the cross-segment entity merge above.
        self.assertEqual(len(story.relations), 1)
        self.assertEqual(story.relations[0].source_event_id, "2:ev1")
        self.assertEqual(story.validation_errors, [])

    def test_validate_story_annotation_flags_dangling_relation(self):
        evidence = schema.EvidenceSpan(start_char=0, end_char=1, quote="x")
        relation = schema.EventRelation(
            relation_id="r1",
            source_event_id="does_not_exist",
            target_event_id="also_missing",
            relation_type="causes",
            evidence=evidence,
        )
        story = schema.StoryWorldAnnotation(story_id="s1", relations=[relation])
        errors = schema.validate_story_annotation(story)
        self.assertTrue(any("does_not_exist" in e for e in errors))
        self.assertTrue(any("also_missing" in e for e in errors))

    def _story_with_two_segment_events(self):
        evidence = schema.EvidenceSpan(start_char=0, end_char=1, quote="x")
        seg1 = schema.SegmentWorldAnnotation(
            segment_id=1,
            events=[
                schema.Event(
                    event_id="ev1", predicate="p", event_type="x", evidence=evidence
                )
            ],
        )
        seg2 = schema.SegmentWorldAnnotation(
            segment_id=2,
            events=[
                schema.Event(
                    event_id="ev1", predicate="p", event_type="x", evidence=evidence
                )
            ],
        )
        return schema.reconcile_story_annotations("s1", [seg1, seg2])

    def test_validate_story_annotation_accepts_valid_cross_segment_relation(self):
        story = self._story_with_two_segment_events()
        evidence = schema.EvidenceSpan(start_char=0, end_char=1, quote="x")
        story.cross_segment_relations = [
            schema.EventRelation(
                relation_id="story:r1",
                source_event_id="1:ev1",
                target_event_id="2:ev1",
                relation_type="causes",
                evidence=evidence,
            )
        ]
        errors = schema.validate_story_annotation(story)
        self.assertEqual(errors, [])

    def test_validate_story_annotation_flags_cross_segment_relation_dangling_endpoint(
        self,
    ):
        story = self._story_with_two_segment_events()
        evidence = schema.EvidenceSpan(start_char=0, end_char=1, quote="x")
        story.cross_segment_relations = [
            schema.EventRelation(
                relation_id="story:r1",
                source_event_id="1:ev1",
                target_event_id="9:does_not_exist",
                relation_type="causes",
                evidence=evidence,
            )
        ]
        errors = schema.validate_story_annotation(story)
        self.assertTrue(any("does_not_exist" in e for e in errors))

    def test_validate_story_annotation_flags_same_segment_cross_segment_relation(self):
        """A same-segment link in cross_segment_relations would indicate the
        story-level pass violated its own scope — this must be flagged as
        an error, not silently accepted."""
        story = self._story_with_two_segment_events()
        evidence = schema.EvidenceSpan(start_char=0, end_char=1, quote="x")
        story.cross_segment_relations = [
            schema.EventRelation(
                relation_id="story:r1",
                source_event_id="1:ev1",
                target_event_id="1:ev1",
                relation_type="causes",
                evidence=evidence,
            )
        ]
        errors = schema.validate_story_annotation(story)
        self.assertTrue(any("not a genuine cross-segment link" in e for e in errors))

    def test_validate_story_annotation_flags_relation_id_collision(self):
        """Defense in depth: cross_segment_relations and relations should
        never share a relation_id (they come from disjoint sources by
        construction), but validation still checks for it explicitly."""
        story = self._story_with_two_segment_events()
        evidence = schema.EvidenceSpan(start_char=0, end_char=1, quote="x")
        story.relations = [
            schema.EventRelation(
                relation_id="dup",
                source_event_id="1:ev1",
                target_event_id="1:ev1",
                relation_type="causes",
                evidence=evidence,
            )
        ]
        story.cross_segment_relations = [
            schema.EventRelation(
                relation_id="dup",
                source_event_id="1:ev1",
                target_event_id="2:ev1",
                relation_type="causes",
                evidence=evidence,
            )
        ]
        errors = schema.validate_story_annotation(story)
        self.assertTrue(any("collides" in e for e in errors))

    def test_validate_story_annotation_flags_certainty_bucket_mismatch(self):
        story = self._story_with_two_segment_events()
        evidence = schema.EvidenceSpan(start_char=0, end_char=1, quote="x")
        story.cross_segment_relations = [
            schema.EventRelation(
                relation_id="story:r1",
                source_event_id="1:ev1",
                target_event_id="2:ev1",
                relation_type="causes",
                evidence=evidence,
                certainty="weakly_inferred",
            )
        ]
        errors = schema.validate_story_annotation(story)
        self.assertTrue(any("has certainty" in e for e in errors))

    def test_reconciliation_is_deterministic(self):
        seg1 = schema.SegmentWorldAnnotation(
            segment_id=1, entities=[self._entity("e1", "the machine")]
        )
        seg2 = schema.SegmentWorldAnnotation(
            segment_id=2, entities=[self._entity("e1", "The Machine")]
        )

        story_a = schema.reconcile_story_annotations("s1", [seg1, seg2])
        story_b = schema.reconcile_story_annotations("s1", [seg1, seg2])

        self.assertEqual(story_a.to_dict(), story_b.to_dict())


# ---------------------------------------------------------------------------
# Tests: export (stage 9)
# ---------------------------------------------------------------------------


class TestExport(unittest.TestCase):
    def _story_with_one_of_everything(self):
        evidence = schema.EvidenceSpan(start_char=0, end_char=7, quote="machine")
        entity = schema.Entity(
            entity_id="e1",
            canonical_name="the machine",
            entity_type="x",
            mention_ids=["m1"],
        )
        mention = schema.EntityMention(
            mention_id="m1", entity_id="e1", text="machine", evidence=evidence
        )
        event = schema.Event(
            event_id="ev1", predicate="hummed", event_type="x", evidence=evidence
        )
        relation = schema.EventRelation(
            relation_id="r1",
            source_event_id="ev1",
            target_event_id="ev1",
            relation_type="causes",
            evidence=evidence,
            certainty="explicit",
        )
        speech_act = schema.SpeechAct(
            speech_act_id="sp1", act_type="assertion", evidence=evidence
        )
        explanation = schema.ExplanationDiscourse(
            explanation_id="ex1",
            topic="t",
            mechanism_or_rationale_type="x",
            evidence=evidence,
        )
        sf_tag = schema.SFWorldModelTag(
            tag_id="sf1", tag="novum", evidence=evidence, status="extractive"
        )
        hypothesis = schema.Hypothesis(
            hypothesis_id="h1",
            hypothesis_type="belief",
            proposition_or_target="p",
            evidence=evidence,
        )
        seg = schema.SegmentWorldAnnotation(
            segment_id=1,
            entities=[entity],
            mentions=[mention],
            events=[event],
            relations=[relation],
            speech_acts=[speech_act],
            explanations=[explanation],
            sf_tags=[sf_tag],
            hypotheses=[hypothesis],
        )
        return schema.reconcile_story_annotations("s1", [seg])

    def test_validate_artifacts_passes_for_clean_story(self):
        story = self._story_with_one_of_everything()
        self.assertEqual(export.validate_artifacts(story), [])

    def test_validate_artifacts_flags_invalid_sf_tag_status(self):
        story = self._story_with_one_of_everything()
        story.segment_annotations[0].sf_tags[0].status = "not_a_valid_status"
        errors = export.validate_artifacts(story)
        self.assertTrue(any("invalid status" in e for e in errors))

    def test_validate_artifacts_flags_invalid_relation_certainty(self):
        story = self._story_with_one_of_everything()
        story.segment_annotations[0].relations[0].certainty = "not_a_valid_certainty"
        errors = export.validate_artifacts(story)
        self.assertTrue(any("invalid certainty" in e for e in errors))

    def test_validate_artifacts_flags_invalid_hypothesis_type(self):
        story = self._story_with_one_of_everything()
        story.segment_annotations[0].hypotheses[0].hypothesis_type = "not_a_valid_type"
        errors = export.validate_artifacts(story)
        self.assertTrue(any("invalid" in e and "hypothesis_type" in e for e in errors))

    def test_validate_artifacts_flags_invalid_cross_segment_relation_certainty(self):
        story = self._story_with_one_of_everything()
        evidence = schema.EvidenceSpan(start_char=0, end_char=7, quote="machine")
        story.cross_segment_relations = [
            schema.EventRelation(
                relation_id="story:r1",
                source_event_id="1:ev1",
                target_event_id="1:ev1",
                relation_type="causes",
                evidence=evidence,
                certainty="not_a_valid_certainty",
            )
        ]
        errors = export.validate_artifacts(story)
        self.assertTrue(any("invalid certainty" in e for e in errors))

    def test_to_canonical_json_is_deterministic(self):
        story = self._story_with_one_of_everything()
        self.assertEqual(
            export.to_canonical_json(story), export.to_canonical_json(story)
        )

    def test_build_analysis_tables_covers_every_layer(self):
        story = self._story_with_one_of_everything()
        tables = export.build_analysis_tables(story)
        for table_name in (
            "entities",
            "events",
            "relations",
            "speech_acts",
            "explanations",
            "sf_tags",
            "hypotheses",
        ):
            self.assertEqual(len(tables[table_name]), 1, table_name)

    def test_build_analysis_tables_includes_cross_segment_relations(self):
        story = self._story_with_one_of_everything()
        evidence = schema.EvidenceSpan(start_char=0, end_char=7, quote="machine")
        story.cross_segment_relations = [
            schema.EventRelation(
                relation_id="story:r2",
                source_event_id="1:ev1",
                target_event_id="1:ev1",
                relation_type="causes",
                evidence=evidence,
            )
        ]
        story.weakly_inferred_cross_segment_relations = [
            schema.EventRelation(
                relation_id="story:r3",
                source_event_id="1:ev1",
                target_event_id="1:ev1",
                relation_type="motivates",
                evidence=evidence,
                certainty="weakly_inferred",
            )
        ]
        tables = export.build_analysis_tables(story)
        # 1 per-segment relation (from _story_with_one_of_everything) + 2
        # story-level cross-segment relations, with no deduplication needed
        # since the two sources are disjoint by construction.
        self.assertEqual(len(tables["relations"]), 3)
        story_rows = [r for r in tables["relations"] if r["segment_id"] == "story"]
        self.assertEqual(len(story_rows), 2)
        self.assertIn("story:r2", [r["relation_id"] for r in story_rows])
        self.assertIn("story:r3", [r["relation_id"] for r in story_rows])

    def test_rows_to_jsonl_produces_one_line_per_row(self):
        rows = [{"a": 1}, {"a": 2}]
        lines = export.rows_to_jsonl(rows).splitlines()
        self.assertEqual(len(lines), 2)

    def test_rows_to_csv_handles_empty_rows(self):
        self.assertEqual(export.rows_to_csv([]), "")

    def test_rows_to_csv_json_encodes_nested_values(self):
        rows = [{"evidence": {"quote": "x"}, "linked_entity_ids": ["e1"]}]
        csv_text = export.rows_to_csv(rows)
        self.assertIn('"quote"', csv_text)


# ---------------------------------------------------------------------------
# Tests: baseline
# ---------------------------------------------------------------------------


class _CharEncoder:
    """Deterministic, network-free fake tiktoken.Encoding test double.

    Operates at the Python-codepoint level (one "token" per character):
    exactly reversible, so make_fixed_token_chunks' contiguous-coverage
    invariants can be tested without depending on tiktoken's real vocab
    data, per tests/AGENTS.md's determinism guidance.
    """

    def encode(self, text, **kwargs):
        return [ord(c) for c in text]

    def decode(self, tokens):
        return "".join(chr(t) for t in tokens)


class _ByteEncoder:
    """Fake encoder operating at the UTF-8 byte level (one token per byte).

    Mirrors real BPE tokenizers closely enough to test that chunk
    boundaries falling mid-character (a multi-byte UTF-8 character split
    across two chunks) still produce correct, non-overlapping,
    non-duplicated char offsets - the exact failure mode a naive
    per-chunk-decode approach is vulnerable to.
    """

    def encode(self, text, **kwargs):
        return list(text.encode("utf-8"))

    def decode(self, tokens):
        return bytes(tokens).decode("utf-8", errors="ignore")


class TestMakeFixedTokenChunks(unittest.TestCase):
    def setUp(self):
        self._encoder_patcher = unittest.mock.patch(
            "lcats.analysis.story_analysis.get_encoder", return_value=_CharEncoder()
        )
        self._encoder_patcher.start()
        self.addCleanup(self._encoder_patcher.stop)

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

    def test_offsets_stay_contiguous_when_boundary_splits_a_multibyte_char(self):
        with unittest.mock.patch(
            "lcats.analysis.story_analysis.get_encoder", return_value=_ByteEncoder()
        ):
            # Each of these characters is multi-byte in UTF-8 (é: 2 bytes,
            # 世/界: 3 bytes each, 🎉: 4 bytes), so a small chunk_size_tokens
            # (byte count) is very likely to split at least one character's
            # bytes across two chunks.
            text = "café 世界 🎉 more plain text after the emoji to pad it out"
            chunks = baseline.make_fixed_token_chunks(text, chunk_size_tokens=3)

            self.assertGreater(len(chunks), 1)
            self.assertEqual(chunks[0]["start_char"], 0)
            self.assertEqual(chunks[-1]["end_char"], len(text))
            for prev, nxt in zip(chunks, chunks[1:]):
                self.assertEqual(prev["end_char"], nxt["start_char"])
                self.assertLessEqual(prev["end_char"], nxt["end_char"])


class TestSummarizeAndCompare(unittest.TestCase):
    def _annotation(
        self,
        word_count,
        n_entities,
        n_events,
        n_relations=0,
        n_weakly_inferred_relations=0,
        n_speech_acts=0,
        n_explanations=0,
        n_sf_tags=0,
        n_hypotheses=0,
    ):
        evidence = schema.EvidenceSpan(0, 1, "x")
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
            relations=[
                schema.EventRelation(f"r{i}", "ev0", "ev0", "causes", evidence)
                for i in range(n_relations)
            ],
            weakly_inferred_relations=[
                schema.EventRelation(
                    f"wr{i}",
                    "ev0",
                    "ev0",
                    "causes",
                    evidence,
                    certainty="weakly_inferred",
                )
                for i in range(n_weakly_inferred_relations)
            ],
            speech_acts=[
                schema.SpeechAct(f"sp{i}", "assertion", evidence)
                for i in range(n_speech_acts)
            ],
            explanations=[
                schema.ExplanationDiscourse(f"ex{i}", "t", "x", evidence)
                for i in range(n_explanations)
            ],
            sf_tags=[
                schema.SFWorldModelTag(f"sf{i}", "x", evidence)
                for i in range(n_sf_tags)
            ],
            hypotheses=[
                schema.Hypothesis(f"h{i}", "belief", "p", evidence)
                for i in range(n_hypotheses)
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

    def test_summarize_covers_relation_discourse_and_sf_tag_layers(self):
        annotations = [
            self._annotation(
                word_count=500,
                n_entities=0,
                n_events=0,
                n_relations=1,
                n_weakly_inferred_relations=2,
                n_speech_acts=3,
                n_explanations=4,
                n_sf_tags=5,
            )
        ]
        summary = baseline.summarize_annotations(annotations)
        self.assertEqual(summary["relations_per_1000_words"], 2.0)
        self.assertEqual(summary["weakly_inferred_relations_per_1000_words"], 4.0)
        self.assertEqual(summary["speech_acts_per_1000_words"], 6.0)
        self.assertEqual(summary["explanations_per_1000_words"], 8.0)
        self.assertEqual(summary["sf_tags_per_1000_words"], 10.0)

    def test_summarize_covers_hypotheses_layer(self):
        annotations = [
            self._annotation(word_count=500, n_entities=0, n_events=0, n_hypotheses=3)
        ]
        summary = baseline.summarize_annotations(annotations)
        self.assertEqual(summary["hypotheses_per_1000_words"], 6.0)

    def test_summarize_without_story_omits_cross_segment_relations(self):
        """Backward compatibility: omitting `story` must produce identical
        rates to before WI-EVENT-0029 - existing callers with only
        per-segment annotations must not be affected."""
        annotations = [
            self._annotation(word_count=500, n_entities=0, n_events=0, n_relations=1)
        ]
        summary = baseline.summarize_annotations(annotations)
        self.assertEqual(summary["relations_per_1000_words"], 2.0)

    def test_summarize_folds_cross_segment_relations_into_relations_rate(self):
        evidence = schema.EvidenceSpan(0, 1, "x")
        annotations = [
            self._annotation(word_count=500, n_entities=0, n_events=0, n_relations=1)
        ]
        story = schema.StoryWorldAnnotation(
            story_id="s1",
            cross_segment_relations=[
                schema.EventRelation("story:r1", "1:ev0", "2:ev0", "causes", evidence)
            ],
        )
        summary = baseline.summarize_annotations(annotations, story)
        # 1 per-segment relation + 1 cross-segment relation, per 500 words.
        self.assertEqual(summary["relations_per_1000_words"], 4.0)

    def test_summarize_folds_weakly_inferred_cross_segment_relations_separately(self):
        evidence = schema.EvidenceSpan(0, 1, "x")
        annotations = [self._annotation(word_count=500, n_entities=0, n_events=0)]
        story = schema.StoryWorldAnnotation(
            story_id="s1",
            weakly_inferred_cross_segment_relations=[
                schema.EventRelation(
                    "story:r1",
                    "1:ev0",
                    "2:ev0",
                    "motivates",
                    evidence,
                    certainty="weakly_inferred",
                )
            ],
        )
        summary = baseline.summarize_annotations(annotations, story)
        self.assertEqual(summary["relations_per_1000_words"], 0.0)
        self.assertEqual(summary["weakly_inferred_relations_per_1000_words"], 2.0)

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


class TestProcessSegments(unittest.TestCase):
    """End-to-end processor tests using entirely faked LLM and NLP backends.

    Runs deterministically in any environment, including a clean checkout
    with no NLP models downloaded: make_nlp_backend is patched to return
    FakeNLPBackend regardless of the requested backend name, so these tests
    exercise process_segments' own logic (error propagation, entity-ID
    threading, usage capture) without depending on a real model. Real
    NLPBackend integration coverage lives in TestRealNLPBackends instead.
    """

    def setUp(self):
        self._nlp_backend_patcher = unittest.mock.patch(
            "lcats.analysis.event_role_world.surface_feature_extractor.make_nlp_backend",
            return_value=nlp_backend.FakeNLPBackend(),
        )
        self._nlp_backend_patcher.start()
        self.addCleanup(self._nlp_backend_patcher.stop)

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
        relation_tool_result = {
            "relations": [
                {
                    "relation_id": "r1",
                    "source_event_id": "ev1",
                    "target_event_id": "ev1",
                    "relation_type": "enables",
                    "quote": "hummed",
                    "certainty": "explicit",
                }
            ]
        }
        discourse_tool_result = {
            "sf_tags": [
                {
                    "tag_id": "sf1",
                    "tag": "nonhuman_actant",
                    "quote": "machine",
                    "linked_entity_ids": ["e1"],
                    "status": "extractive",
                }
            ]
        }
        hypothesis_tool_result = {
            "hypotheses": [
                {
                    "hypothesis_id": "h1",
                    "hypothesis_type": "perspective",
                    "proposition_or_target": "the machine seemed alive",
                    "quote": "old machine",
                    "subject_entity_id": "e1",
                }
            ]
        }
        fake = _SequencedFakeBackend(
            [
                entity_tool_result,
                event_tool_result,
                relation_tool_result,
                discourse_tool_result,
                hypothesis_tool_result,
            ]
        )
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
        self.assertEqual(len(seg["relations"]), 1)
        self.assertEqual(seg["weakly_inferred_relations"], [])
        self.assertEqual(len(seg["sf_tags"]), 1)
        self.assertEqual(len(seg["hypotheses"]), 1)
        self.assertEqual(seg["validation_errors"], [])

        # Exactly one LLM call each for entities, events, relations,
        # discourse, hypotheses.
        self.assertEqual(len(fake.calls), 5)

        # Cost/usage reporting: token counts, model, and elapsed time per
        # pass - not just call counts (WI-EVENT-0024 acceptance criterion).
        usage_by_pass = {u["pass_name"]: u for u in result["usage"]}
        self.assertIn("surface_feature", usage_by_pass)
        self.assertIn("entity", usage_by_pass)
        self.assertIn("event_anchor", usage_by_pass)
        self.assertIn("relation", usage_by_pass)
        self.assertIn("discourse", usage_by_pass)
        self.assertIn("hypothesis", usage_by_pass)
        self.assertFalse(usage_by_pass["surface_feature"]["is_llm_backed"])
        self.assertTrue(usage_by_pass["entity"]["is_llm_backed"])
        self.assertEqual(usage_by_pass["entity"]["input_tokens"], 10)
        self.assertEqual(usage_by_pass["entity"]["model"], "fake-1.0")

        # Stage 9: story-level reconciliation is included in the result.
        self.assertIn("story", result)
        self.assertEqual(len(result["story"]["entities"]), 1)
        self.assertEqual(result["story"]["entity_alias_map"], {"1:e1": "global_e0"})

    def test_include_hypotheses_false_skips_stage_8_entirely(self):
        """Stage 8 is optional per the proposal: a caller that opts out via
        include_hypotheses=False must not pay for the extra LLM request, and
        must not see a hypothesis-provider failure in extraction_errors for
        a layer it never asked for."""
        segment_text = "The old machine hummed."
        entity_tool_result = {
            "entities": [
                {
                    "entity_id": "e1",
                    "canonical_name": "the machine",
                    "entity_type": "machine_or_artifact",
                    "mentions": [
                        {"mention_id": "m1", "text": "the machine", "quote": "machine"}
                    ],
                }
            ]
        }
        fake = _SequencedFakeBackend(
            [entity_tool_result, {"events": []}, {"relations": []}, {}]
        )
        segments = [{"segment_id": 1, "start_char": 0, "end_char": len(segment_text)}]

        result = processor.process_segments(
            segment_text,
            segments,
            nlp_backend_name="spacy",
            llm_backend=fake,
            include_hypotheses=False,
        )

        # Exactly 4 calls (entity, event, relation, discourse) - no
        # hypothesis call was ever made.
        self.assertEqual(len(fake.calls), 4)
        seg = result["segments"][0]
        self.assertEqual(seg["hypotheses"], [])
        self.assertEqual(seg["extraction_errors"], [])
        usage_by_pass = {u["pass_name"]: u for u in result["usage"]}
        self.assertNotIn("hypothesis", usage_by_pass)

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
        fake = _SequencedFakeBackend(
            [entity_tool_result, event_tool_result, {"relations": []}, {}, {}]
        )
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

    def test_entity_extraction_failure_is_recorded_not_silently_empty(self):
        """A failed entity pass must not read as 'zero entities found'."""
        segment_text = "The machine hummed."

        class _NoToolResultBackend:
            def __init__(self):
                self.calls = 0

            def complete(self, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    # Simulate a tool-call failure on the entity pass: no
                    # tool_result, which JSONPromptExtractor.extract()
                    # turns into an "empty_tool_result" api_error.
                    return llm_backend.BackendResponse(
                        text="",
                        tool_result=None,
                        model="fake-1.0",
                        input_tokens=5,
                        output_tokens=0,
                        raw=None,
                    )
                return llm_backend.BackendResponse(
                    text="",
                    tool_result={"events": []},
                    model="fake-1.0",
                    input_tokens=5,
                    output_tokens=2,
                    raw=None,
                )

        backend = _NoToolResultBackend()
        segments = [{"segment_id": 1, "start_char": 0, "end_char": len(segment_text)}]

        result = processor.process_segments(
            segment_text, segments, nlp_backend_name="spacy", llm_backend=backend
        )

        seg = result["segments"][0]
        self.assertEqual(seg["entities"], [])
        self.assertTrue(
            any("entity extraction failed" in e for e in seg["extraction_errors"]),
            seg["extraction_errors"],
        )

    def test_event_pass_failure_does_not_abort_remaining_segments(self):
        """A transient failure on one segment's event pass must not lose
        every other segment's already-processed results (the bug: bypassing
        JSONPromptExtractor.extract()'s exception handling let a raised
        exception propagate out of process_segments entirely)."""
        segment_text_1 = "The machine hummed."
        segment_text_2 = "It stopped."

        entity_result_empty = {"entities": []}

        class _RaisesOnSecondCallBackend:
            def __init__(self):
                self.calls = 0

            def complete(self, **kwargs):
                self.calls += 1
                # Call order per segment: entity, event. Raise only on
                # segment 1's event call (call #2).
                if self.calls == 2:
                    raise RuntimeError("simulated transient provider failure")
                return llm_backend.BackendResponse(
                    text="",
                    tool_result=(
                        entity_result_empty if self.calls % 2 == 1 else {"events": []}
                    ),
                    model="fake-1.0",
                    input_tokens=5,
                    output_tokens=2,
                    raw=None,
                )

        backend = _RaisesOnSecondCallBackend()
        segments = [
            {"segment_id": 1, "start_char": 0, "end_char": len(segment_text_1)},
            {
                "segment_id": 2,
                "start_char": len(segment_text_1) + 1,
                "end_char": len(segment_text_1) + 1 + len(segment_text_2),
            },
        ]
        story_text = segment_text_1 + " " + segment_text_2

        # Must not raise - the transient failure on segment 1's event call
        # is caught and recorded, not propagated out of process_segments.
        result = processor.process_segments(
            story_text, segments, nlp_backend_name="spacy", llm_backend=backend
        )

        self.assertEqual(len(result["segments"]), 2)
        seg1 = result["segments"][0]
        self.assertTrue(
            any(
                "event/anchor extraction failed" in e for e in seg1["extraction_errors"]
            ),
            seg1["extraction_errors"],
        )
        # Segment 2 still got processed despite segment 1's failure.
        seg2 = result["segments"][1]
        self.assertEqual(seg2["extraction_errors"], [])

    def test_relation_extraction_failure_is_recorded_not_silently_empty(self):
        """A failed relation pass must not read as 'zero relations found'."""
        segment_text = "The machine hummed."

        class _NoToolResultOnThirdCallBackend:
            def __init__(self):
                self.calls = 0

            def complete(self, **kwargs):
                self.calls += 1
                if self.calls == 3:
                    # Call order per segment: entity, event, relation,
                    # discourse. Simulate a tool-call failure on the
                    # relation pass (call #3).
                    return llm_backend.BackendResponse(
                        text="",
                        tool_result=None,
                        model="fake-1.0",
                        input_tokens=5,
                        output_tokens=0,
                        raw=None,
                    )
                return llm_backend.BackendResponse(
                    text="",
                    tool_result={},
                    model="fake-1.0",
                    input_tokens=5,
                    output_tokens=2,
                    raw=None,
                )

        backend = _NoToolResultOnThirdCallBackend()
        segments = [{"segment_id": 1, "start_char": 0, "end_char": len(segment_text)}]

        result = processor.process_segments(
            segment_text, segments, nlp_backend_name="spacy", llm_backend=backend
        )

        seg = result["segments"][0]
        self.assertEqual(seg["relations"], [])
        self.assertTrue(
            any("relation extraction failed" in e for e in seg["extraction_errors"]),
            seg["extraction_errors"],
        )

    def test_discourse_extraction_failure_is_recorded_not_silently_empty(self):
        """A failed discourse pass must not read as 'nothing found'."""
        segment_text = "The machine hummed."

        class _NoToolResultOnFourthCallBackend:
            def __init__(self):
                self.calls = 0

            def complete(self, **kwargs):
                self.calls += 1
                if self.calls == 4:
                    # Call order per segment: entity, event, relation,
                    # discourse. Simulate a tool-call failure on the
                    # discourse pass (call #4).
                    return llm_backend.BackendResponse(
                        text="",
                        tool_result=None,
                        model="fake-1.0",
                        input_tokens=5,
                        output_tokens=0,
                        raw=None,
                    )
                return llm_backend.BackendResponse(
                    text="",
                    tool_result={},
                    model="fake-1.0",
                    input_tokens=5,
                    output_tokens=2,
                    raw=None,
                )

        backend = _NoToolResultOnFourthCallBackend()
        segments = [{"segment_id": 1, "start_char": 0, "end_char": len(segment_text)}]

        result = processor.process_segments(
            segment_text, segments, nlp_backend_name="spacy", llm_backend=backend
        )

        seg = result["segments"][0]
        self.assertEqual(seg["sf_tags"], [])
        self.assertTrue(
            any("discourse extraction failed" in e for e in seg["extraction_errors"]),
            seg["extraction_errors"],
        )

    def test_hypothesis_extraction_failure_is_recorded_not_silently_empty(self):
        """A failed hypothesis pass must not read as 'no hypotheses found'."""
        segment_text = "The machine hummed."

        class _NoToolResultOnFifthCallBackend:
            def __init__(self):
                self.calls = 0

            def complete(self, **kwargs):
                self.calls += 1
                if self.calls == 5:
                    # Call order per segment: entity, event, relation,
                    # discourse, hypothesis. Simulate a tool-call failure
                    # on the hypothesis pass (call #5).
                    return llm_backend.BackendResponse(
                        text="",
                        tool_result=None,
                        model="fake-1.0",
                        input_tokens=5,
                        output_tokens=0,
                        raw=None,
                    )
                return llm_backend.BackendResponse(
                    text="",
                    tool_result={},
                    model="fake-1.0",
                    input_tokens=5,
                    output_tokens=2,
                    raw=None,
                )

        backend = _NoToolResultOnFifthCallBackend()
        segments = [{"segment_id": 1, "start_char": 0, "end_char": len(segment_text)}]

        result = processor.process_segments(
            segment_text, segments, nlp_backend_name="spacy", llm_backend=backend
        )

        seg = result["segments"][0]
        self.assertEqual(seg["hypotheses"], [])
        self.assertTrue(
            any("hypothesis extraction failed" in e for e in seg["extraction_errors"]),
            seg["extraction_errors"],
        )

    def _two_segment_setup(self):
        """Two segments, each with exactly one event, so the story-level
        cross-segment relation pass (WI-EVENT-0029) has something to work
        with (its guard requires at least 2 events total)."""
        segment_text_1 = "The old machine hummed."
        segment_text_2 = "It shut off forever."
        story_text = segment_text_1 + " " + segment_text_2
        segments = [
            {"segment_id": 1, "start_char": 0, "end_char": len(segment_text_1)},
            {
                "segment_id": 2,
                "start_char": len(segment_text_1) + 1,
                "end_char": len(segment_text_1) + 1 + len(segment_text_2),
            },
        ]
        seg1_results = [
            {"entities": []},
            {
                "events": [
                    {
                        "event_id": "ev1",
                        "predicate": "hummed",
                        "event_type": "sound_emission",
                        "quote": "hummed",
                    }
                ]
            },
            {"relations": []},
            {},
            {},
        ]
        seg2_results = [
            {"entities": []},
            {
                "events": [
                    {
                        "event_id": "ev1",
                        "predicate": "shut off",
                        "event_type": "mechanical_failure",
                        "quote": "shut off",
                    }
                ]
            },
            {"relations": []},
            {},
            {},
        ]
        return story_text, segments, seg1_results + seg2_results

    def test_story_relation_pass_discovers_cross_segment_relation(self):
        story_text, segments, per_segment_results = self._two_segment_setup()
        story_relation_result = {
            "relations": [
                {
                    "relation_id": "r1",
                    "source_event_id": "1:ev1",
                    "target_event_id": "2:ev1",
                    "relation_type": "causes",
                    "certainty": "explicit",
                }
            ]
        }
        fake = _SequencedFakeBackend(per_segment_results + [story_relation_result])

        result = processor.process_segments(
            story_text, segments, nlp_backend_name="spacy", llm_backend=fake
        )

        # 5 calls per segment x 2 segments + 1 story-level call.
        self.assertEqual(len(fake.calls), 11)
        usage_by_pass = {u["pass_name"]: u for u in result["usage"]}
        self.assertIn("story_relation", usage_by_pass)
        self.assertTrue(usage_by_pass["story_relation"]["is_llm_backed"])

        story = result["story"]
        self.assertEqual(len(story["cross_segment_relations"]), 1)
        relation = story["cross_segment_relations"][0]
        self.assertEqual(relation["relation_id"], "story:r1")
        self.assertEqual(relation["source_event_id"], "1:ev1")
        self.assertEqual(relation["target_event_id"], "2:ev1")
        self.assertEqual(story["weakly_inferred_cross_segment_relations"], [])
        self.assertEqual(story["validation_errors"], [])

    def test_include_cross_segment_relations_false_skips_story_pass(self):
        story_text, segments, per_segment_results = self._two_segment_setup()
        fake = _SequencedFakeBackend(per_segment_results)

        result = processor.process_segments(
            story_text,
            segments,
            nlp_backend_name="spacy",
            llm_backend=fake,
            include_cross_segment_relations=False,
        )

        # Exactly 10 calls (5 per segment) - no story-level call was made.
        self.assertEqual(len(fake.calls), 10)
        usage_by_pass = {u["pass_name"]: u for u in result["usage"]}
        self.assertNotIn("story_relation", usage_by_pass)
        self.assertEqual(result["story"]["cross_segment_relations"], [])

    def test_cross_segment_relation_pass_skipped_when_fewer_than_two_events(self):
        """A cross-segment relation needs at least two events by
        definition - the pass must not spend an LLM call on a story that
        cannot possibly produce one."""
        segment_text = "The machine hummed."
        fake = _SequencedFakeBackend(
            [
                {"entities": []},
                {
                    "events": [
                        {
                            "event_id": "ev1",
                            "predicate": "hummed",
                            "event_type": "x",
                            "quote": "hummed",
                        }
                    ]
                },
                {"relations": []},
                {},
                {},
            ]
        )
        segments = [{"segment_id": 1, "start_char": 0, "end_char": len(segment_text)}]

        result = processor.process_segments(
            segment_text, segments, nlp_backend_name="spacy", llm_backend=fake
        )

        # Exactly 5 calls - the story-level pass was never invoked despite
        # include_cross_segment_relations defaulting to True.
        self.assertEqual(len(fake.calls), 5)
        usage_by_pass = {u["pass_name"]: u for u in result["usage"]}
        self.assertNotIn("story_relation", usage_by_pass)

    def test_cross_segment_relation_pass_skipped_for_single_segment_story(self):
        """Two events in the SAME segment cannot produce a genuinely
        cross-segment relation - build_story_relations would discard every
        candidate as same-segment, so the pass must be skipped even though
        total event count is >= 2 (a naive "at least 2 events" guard would
        incorrectly let this one through)."""
        segment_text = "The machine hummed. It shut off."
        fake = _SequencedFakeBackend(
            [
                {"entities": []},
                {
                    "events": [
                        {
                            "event_id": "ev1",
                            "predicate": "hummed",
                            "event_type": "x",
                            "quote": "hummed",
                        },
                        {
                            "event_id": "ev2",
                            "predicate": "shut off",
                            "event_type": "x",
                            "quote": "shut off",
                        },
                    ]
                },
                {"relations": []},
                {},
                {},
            ]
        )
        segments = [{"segment_id": 1, "start_char": 0, "end_char": len(segment_text)}]

        result = processor.process_segments(
            segment_text, segments, nlp_backend_name="spacy", llm_backend=fake
        )

        # Exactly 5 calls - both events are in segment 1, so no distinct
        # second segment exists for a cross-segment relation to span.
        self.assertEqual(len(fake.calls), 5)
        usage_by_pass = {u["pass_name"]: u for u in result["usage"]}
        self.assertNotIn("story_relation", usage_by_pass)

    def test_story_relation_extraction_failure_is_recorded_not_silently_empty(self):
        """A failed story-relation pass must not read as 'no cross-segment
        relations found'."""
        story_text, segments, per_segment_results = self._two_segment_setup()

        class _FailsOnEleventhCallBackend:
            def __init__(self):
                self.calls = 0

            def complete(self, **kwargs):
                self.calls += 1
                if self.calls == 11:
                    return llm_backend.BackendResponse(
                        text="",
                        tool_result=None,
                        model="fake-1.0",
                        input_tokens=5,
                        output_tokens=0,
                        raw=None,
                    )
                result = per_segment_results[self.calls - 1]
                return llm_backend.BackendResponse(
                    text="",
                    tool_result=result,
                    model="fake-1.0",
                    input_tokens=5,
                    output_tokens=2,
                    raw=None,
                )

        backend = _FailsOnEleventhCallBackend()

        result = processor.process_segments(
            story_text, segments, nlp_backend_name="spacy", llm_backend=backend
        )

        story = result["story"]
        self.assertEqual(story["cross_segment_relations"], [])
        self.assertTrue(
            any(
                "story relation extraction failed" in e
                for e in story["extraction_errors"]
            ),
            story["extraction_errors"],
        )


if __name__ == "__main__":
    unittest.main()
