"""Tests for standalone linguistic sidecar extraction."""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest
from io import StringIO
from unittest import mock

from lcats.analysis.corpus import linguistics_cli
from lcats.analysis.event_role_world import nlp_backend
from lcats.analysis.linguistics import lexicon, runner, sidecar
from lcats import stories


def _token(text: str, upos: str = "X") -> nlp_backend.TokenRecord:
    return nlp_backend.TokenRecord(
        text=text,
        lemma=text.casefold(),
        upos=upos,
        xpos=upos,
        feats="",
        head_index=0,
        deprel="root",
    )


def _backend() -> nlp_backend.FakeNLPBackend:
    return nlp_backend.FakeNLPBackend(
        sentences=[
            nlp_backend.SentenceRecord(
                tokens=[_token("The"), _token("cat"), _token(".", "PUNCT")]
            ),
            nlp_backend.SentenceRecord(tokens=[_token("slept")]),
        ]
    )


def _v2_backend(body: str) -> nlp_backend.FakeNLPBackend:
    def token(
        text: str, upos: str, head: int, start_at: int
    ) -> nlp_backend.TokenRecord:
        start = body.index(text, start_at)
        return nlp_backend.TokenRecord(
            text=text,
            lemma=text.casefold(),
            upos=upos,
            xpos=upos,
            feats="",
            head_index=head,
            deprel="root" if head == 0 else "dep",
            start_char=start,
            end_char=start + len(text),
        )

    old = token("old", "ADJ", 2, 0)
    machine = token("machine", "NOUN", 0, old.end_char or 0)
    hummed = token("hummed", "VERB", 2, machine.end_char or 0)
    period = token(".", "PUNCT", 2, hummed.end_char or 0)
    return nlp_backend.FakeNLPBackend(
        sentences=[
            nlp_backend.SentenceRecord(
                tokens=[old, machine, hummed, period],
                start_char=old.start_char,
                end_char=period.end_char,
            )
        ]
    )


def _offset_token(
    body: str, text: str, upos: str, head: int, start_at: int
) -> nlp_backend.TokenRecord:
    start = body.index(text, start_at)
    return nlp_backend.TokenRecord(
        text=text,
        lemma=text.casefold(),
        upos=upos,
        xpos=upos,
        feats="",
        head_index=head,
        deprel="root" if head == 0 else "dep",
        start_char=start,
        end_char=start + len(text),
    )


def _story_data(body: str = "The cat. slept") -> dict:
    return {
        "name": "Example",
        "body": body,
        "metadata": {"author": "A. Writer"},
    }


def _write_story(bucket: pathlib.Path, body: str = "The cat. slept") -> pathlib.Path:
    bucket.mkdir(parents=True, exist_ok=True)
    story_path = bucket / "story.json"
    story_path.write_text(json.dumps(_story_data(body)), encoding="utf-8")
    return story_path


class LinguisticsAnalysisTest(unittest.TestCase):
    def test_analyze_story_uses_surface_feature_aggregates(self):
        backend = _backend()
        story = stories.Story.from_dict(_story_data())
        options = sidecar.LinguisticsOptions(backend_name="fake")

        result = sidecar.analyze_story(story, backend, options)

        self.assertEqual(result["metrics"]["word_count"], 3)
        self.assertEqual(result["metrics"]["sentence_count"], 2)
        self.assertEqual(result["metrics"]["avg_sentence_length"], 1.5)
        self.assertEqual(result["metrics"]["token_count"], 4)
        self.assertNotIn("tokens", result)

    def test_optional_token_detail_is_not_in_default_sidecar(self):
        story_path = pathlib.Path("corpus/story/story.json")
        options = sidecar.LinguisticsOptions(backend_name="fake")

        data, detail = sidecar.build_sidecar(
            story_data=_story_data(),
            story_path=story_path,
            backend=_backend(),
            options=options,
        )

        self.assertNotIn("tokens", data)
        self.assertIsNone(detail)

    def test_include_token_detail_writes_separate_payload(self):
        options = sidecar.LinguisticsOptions(
            backend_name="fake", include_token_detail=True
        )

        data, detail = sidecar.build_sidecar(
            story_data=_story_data(),
            story_path=pathlib.Path("corpus/story/story.json"),
            backend=_backend(),
            options=options,
        )

        self.assertNotIn("tokens", data)
        self.assertIsNotNone(detail)
        self.assertEqual(4, len(detail["tokens"]))

    def test_include_v2_token_detail_writes_nested_sentence_payload(self):
        body = "The old machine hummed."
        options = sidecar.LinguisticsOptions(
            backend_name="fake",
            include_token_detail=True,
            token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
        )

        data, detail = sidecar.build_sidecar(
            story_data=_story_data(body),
            story_path=pathlib.Path("corpus/story/story.json"),
            backend=_v2_backend(body),
            options=options,
        )

        self.assertNotIn("tokens", data)
        self.assertIsNotNone(detail)
        self.assertEqual(sidecar.DETAIL_V2_SCHEMA_VERSION, detail["schema_version"])
        self.assertEqual("v2", detail["options"]["token_detail_version"])
        self.assertEqual(1, detail["sentences"][0]["sentence_index"])
        self.assertEqual(2, detail["sentences"][0]["tokens"][1]["token_index"])
        self.assertEqual(2, detail["sentences"][0]["tokens"][1]["global_token_index"])
        self.assertEqual(
            "machine",
            body[
                detail["sentences"][0]["tokens"][1]["start_char"] : detail["sentences"][
                    0
                ]["tokens"][1]["end_char"]
            ],
        )

    def test_v2_token_detail_reports_unaligned_offsets_as_unavailable(self):
        body = "du"
        backend = nlp_backend.FakeNLPBackend(
            sentences=[
                nlp_backend.SentenceRecord(
                    tokens=[
                        nlp_backend.TokenRecord(
                            text="de",
                            lemma="de",
                            upos="ADP",
                            xpos="ADP",
                            feats="",
                            head_index=0,
                            deprel="root",
                        ),
                        nlp_backend.TokenRecord(
                            text="le",
                            lemma="le",
                            upos="DET",
                            xpos="DET",
                            feats="",
                            head_index=1,
                            deprel="det",
                        ),
                    ]
                )
            ]
        )
        options = sidecar.LinguisticsOptions(
            backend_name="fake",
            include_token_detail=True,
            token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
        )

        compact, detail = sidecar.build_sidecar(
            story_data=_story_data(body),
            story_path=pathlib.Path("corpus/story/story.json"),
            backend=backend,
            options=options,
        )
        result = sidecar.validate_token_detail(
            detail, source_body=body, compact_sidecar=compact
        )

        self.assertTrue(result.valid)
        self.assertIsNone(detail["sentences"][0]["tokens"][0]["start_char"])
        self.assertIsNone(detail["sentences"][0]["tokens"][0]["end_char"])
        self.assertEqual(
            "unavailable",
            detail["provenance"]["capabilities"]["token_offsets"],
        )

    def test_v1_token_detail_shape_remains_default(self):
        options = sidecar.LinguisticsOptions(
            backend_name="fake", include_token_detail=True
        )

        _, detail = sidecar.build_sidecar(
            story_data=_story_data(),
            story_path=pathlib.Path("corpus/story/story.json"),
            backend=_backend(),
            options=options,
        )

        self.assertEqual(sidecar.DETAIL_SCHEMA_VERSION, detail["schema_version"])
        self.assertIn("tokens", detail)
        self.assertNotIn("sentences", detail)
        self.assertNotIn("token_detail_version", detail["options"])

    def test_empty_story_produces_zero_metrics_without_backend_call(self):
        backend = nlp_backend.FakeNLPBackend()

        result = sidecar.analyze_story(
            stories.Story.from_dict(_story_data("")),
            backend,
            sidecar.LinguisticsOptions(backend_name="fake"),
        )

        self.assertEqual(0, result["metrics"]["word_count"])
        self.assertEqual(0, result["metrics"]["sentence_count"])
        self.assertEqual([], backend.calls)

    def test_unicode_and_typographic_punctuation_are_hash_stable(self):
        text = "Curly quotes: “hello” — voilà."

        digest = sidecar.body_sha256(text)

        self.assertEqual(digest, sidecar.body_sha256(text))
        self.assertNotEqual(digest, sidecar.body_sha256(text + " "))


class LinguisticsSidecarValidationTest(unittest.TestCase):
    def test_valid_sidecar_passes_schema_validation(self):
        data, _ = sidecar.build_sidecar(
            story_data=_story_data(),
            story_path=pathlib.Path("sample_collection/sample_story/story.json"),
            backend=_backend(),
            options=sidecar.LinguisticsOptions(backend_name="fake"),
        )

        result = sidecar.validate_sidecar(data)

        self.assertTrue(result.valid)
        self.assertEqual((), result.findings)

    def test_invalid_sidecar_reports_structured_findings(self):
        result = sidecar.validate_sidecar({"schema_version": "bad"})

        self.assertFalse(result.valid)
        self.assertIn(
            "invalid_schema_version", {finding.kind for finding in result.findings}
        )
        self.assertIn("$.metrics", {finding.path for finding in result.findings})

    def test_provenance_and_body_hash_are_recorded(self):
        data, _ = sidecar.build_sidecar(
            story_data=_story_data("Body"),
            story_path=pathlib.Path("c/s/story.json"),
            backend=_backend(),
            options=sidecar.LinguisticsOptions(backend_name="fake"),
        )

        self.assertEqual(sidecar.SCHEMA_VERSION, data["schema_version"])
        self.assertEqual(sidecar.EXTRACTOR_VERSION, data["extractor"]["version"])
        self.assertEqual("fake", data["backend"]["name"])
        self.assertEqual(sidecar.body_sha256("Body"), data["input"]["body_sha256"])

    def test_story_identity_for_bucket_relative_story_file_uses_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            bucket = pathlib.Path(tmp) / "collection" / "story"
            bucket.mkdir(parents=True)
            with mock.patch.object(pathlib.Path, "cwd", return_value=bucket):
                self.assertEqual(
                    "story", sidecar.story_identity(pathlib.Path("story.json"))
                )

    def test_default_stanza_model_provenance_records_language(self):
        data, _ = sidecar.build_sidecar(
            story_data=_story_data("Body"),
            story_path=pathlib.Path("c/s/story.json"),
            backend=_backend(),
            options=sidecar.LinguisticsOptions(backend_name="stanza"),
        )

        self.assertEqual("en", data["backend"]["model"])

    def test_deterministic_serialization_for_identical_input(self):
        data, _ = sidecar.build_sidecar(
            story_data=_story_data(),
            story_path=pathlib.Path("c/s/story.json"),
            backend=_backend(),
            options=sidecar.LinguisticsOptions(backend_name="fake"),
        )

        self.assertEqual(sidecar.dumps_json(data), sidecar.dumps_json(data))
        self.assertIn('\n  "backend": {', sidecar.dumps_json(data))

    def test_valid_v2_token_detail_passes_strict_validation(self):
        body = "“Come,” said Alice. The old machine hummed."
        backend = nlp_backend.FakeNLPBackend(
            sentences=[
                nlp_backend.SentenceRecord(
                    tokens=[
                        _offset_token(body, "“", "PUNCT", 2, 0),
                        _offset_token(body, "Come", "VERB", 0, 0),
                        _offset_token(body, ",", "PUNCT", 2, 0),
                        _offset_token(body, "”", "PUNCT", 2, 0),
                        _offset_token(body, "said", "VERB", 2, 0),
                        _offset_token(body, "Alice", "PROPN", 5, 0),
                        _offset_token(body, ".", "PUNCT", 5, 0),
                    ],
                    start_char=0,
                    end_char=20,
                ),
                nlp_backend.SentenceRecord(
                    tokens=[
                        _offset_token(body, "The", "DET", 3, 20),
                        _offset_token(body, "old", "ADJ", 3, 20),
                        _offset_token(body, "machine", "NOUN", 0, 20),
                        _offset_token(body, "hummed", "VERB", 3, 20),
                        _offset_token(body, ".", "PUNCT", 3, 20),
                    ],
                    start_char=20,
                    end_char=len(body),
                ),
            ]
        )
        options = sidecar.LinguisticsOptions(
            backend_name="fake",
            include_token_detail=True,
            token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
        )

        compact, detail = sidecar.build_sidecar(
            story_data=_story_data(body),
            story_path=pathlib.Path("collection/story/story.json"),
            backend=backend,
            options=options,
        )
        result = sidecar.validate_token_detail(
            detail, source_body=body, compact_sidecar=compact
        )

        self.assertTrue(result.valid)
        self.assertEqual((), result.findings)

    def test_v2_validation_rejects_bad_span_head_upos_and_count(self):
        body = "The old machine hummed."
        options = sidecar.LinguisticsOptions(
            backend_name="fake",
            include_token_detail=True,
            token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
        )
        compact, detail = sidecar.build_sidecar(
            story_data=_story_data(body),
            story_path=pathlib.Path("collection/story/story.json"),
            backend=_v2_backend(body),
            options=options,
        )
        detail["sentences"][0]["tokens"][1]["text"] = "wrong"
        detail["sentences"][0]["tokens"][1]["global_token_index"] = 99
        detail["sentences"][0]["tokens"][1]["head_index"] = 99
        detail["sentences"][0]["tokens"][1]["upos"] = "NOT_A_TAG"
        compact["metrics"]["token_count"] = 99

        result = sidecar.validate_token_detail(
            detail, source_body=body, compact_sidecar=compact
        )
        kinds = {finding.kind for finding in result.findings}

        self.assertFalse(result.valid)
        self.assertIn("source_span_mismatch", kinds)
        self.assertIn("non_monotonic_global_token_index", kinds)
        self.assertIn("invalid_head_index", kinds)
        self.assertIn("invalid_upos", kinds)
        self.assertIn("compact_token_count_mismatch", kinds)

    def test_v2_validation_rejects_sentence_span_that_excludes_tokens(self):
        body = "The old machine hummed."
        options = sidecar.LinguisticsOptions(
            backend_name="fake",
            include_token_detail=True,
            token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
        )
        compact, detail = sidecar.build_sidecar(
            story_data=_story_data(body),
            story_path=pathlib.Path("collection/story/story.json"),
            backend=_v2_backend(body),
            options=options,
        )
        detail["sentences"][0]["start_char"] = 3
        detail["sentences"][0]["end_char"] = 4

        result = sidecar.validate_token_detail(
            detail, source_body=body, compact_sidecar=compact
        )
        kinds = {finding.kind for finding in result.findings}

        self.assertFalse(result.valid)
        self.assertIn("token_span_outside_sentence_span", kinds)

    def test_v2_validation_rejects_out_of_order_sentence_spans(self):
        body = "One. Two."
        one = _offset_token(body, "One", "NUM", 0, 0)
        first_period = _offset_token(body, ".", "PUNCT", 1, one.end_char or 0)
        two = _offset_token(body, "Two", "NUM", 0, first_period.end_char or 0)
        second_period = _offset_token(body, ".", "PUNCT", 1, two.end_char or 0)
        backend = nlp_backend.FakeNLPBackend(
            sentences=[
                nlp_backend.SentenceRecord(
                    tokens=[one, first_period], start_char=0, end_char=4
                ),
                nlp_backend.SentenceRecord(
                    tokens=[two, second_period], start_char=5, end_char=9
                ),
            ]
        )
        options = sidecar.LinguisticsOptions(
            backend_name="fake",
            include_token_detail=True,
            token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
        )
        compact, detail = sidecar.build_sidecar(
            story_data=_story_data(body),
            story_path=pathlib.Path("collection/story/story.json"),
            backend=backend,
            options=options,
        )
        detail["sentences"][1]["start_char"] = 3

        result = sidecar.validate_token_detail(
            detail, source_body=body, compact_sidecar=compact
        )
        kinds = {finding.kind for finding in result.findings}

        self.assertFalse(result.valid)
        self.assertIn("non_monotonic_sentence_span", kinds)

    def test_v2_validation_reports_empty_required_strings_precisely(self):
        body = "The old machine hummed."
        options = sidecar.LinguisticsOptions(
            backend_name="fake",
            include_token_detail=True,
            token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
        )
        compact, detail = sidecar.build_sidecar(
            story_data=_story_data(body),
            story_path=pathlib.Path("collection/story/story.json"),
            backend=_v2_backend(body),
            options=options,
        )
        detail["sentences"][0]["tokens"][0]["text"] = ""

        result = sidecar.validate_token_detail(
            detail, source_body=body, compact_sidecar=compact
        )
        messages_by_kind = {
            finding.kind: finding.message for finding in result.findings
        }

        self.assertFalse(result.valid)
        self.assertEqual(
            "expected non-empty string",
            messages_by_kind["empty_string"],
        )

    def test_invalid_token_detail_version_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "token_detail_version"):
            sidecar.LinguisticsOptions(token_detail_version="v3")


class LinguisticsWriterTest(unittest.TestCase):
    def test_atomic_write_preserves_existing_file_on_replace_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "linguistics.json"
            path.write_text("old\n", encoding="utf-8")
            with mock.patch.object(sidecar.os, "replace", side_effect=OSError("boom")):
                with self.assertRaises(OSError):
                    sidecar.write_json_atomic(path, {"new": True})

            self.assertEqual("old\n", path.read_text(encoding="utf-8"))
            self.assertEqual([], list(path.parent.glob(".*.tmp")))


class LinguisticsLexiconTest(unittest.TestCase):
    def test_build_lexicon_records_deterministic_surface_lemma_upos_counts(self):
        body = "Alice saw Alice."
        alice_1 = _offset_token(body, "Alice", "PROPN", 2, 0)
        saw = _offset_token(body, "saw", "VERB", 0, alice_1.end_char or 0)
        alice_2 = _offset_token(body, "Alice", "PROPN", 2, saw.end_char or 0)
        period = _offset_token(body, ".", "PUNCT", 2, alice_2.end_char or 0)
        backend = nlp_backend.FakeNLPBackend(
            sentences=[
                nlp_backend.SentenceRecord(
                    tokens=[alice_1, saw, alice_2, period],
                    start_char=0,
                    end_char=len(body),
                )
            ]
        )
        options = sidecar.LinguisticsOptions(
            backend_name="fake",
            include_token_detail=True,
            token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
        )
        _, detail = sidecar.build_sidecar(
            story_data=_story_data(body),
            story_path=pathlib.Path("collection/story/story.json"),
            backend=backend,
            options=options,
        )

        data = lexicon.build_lexicon(detail)
        index = lexicon.LexiconIndex.from_artifact(data)

        self.assertEqual(lexicon.SCHEMA_VERSION, data["schema_version"])
        self.assertEqual(4, data["denominators"]["token_count"])
        self.assertEqual(
            [
                {"count": 1, "lemma": ".", "surface": ".", "upos": "PUNCT"},
                {"count": 2, "lemma": "alice", "surface": "Alice", "upos": "PROPN"},
                {"count": 1, "lemma": "saw", "surface": "saw", "upos": "VERB"},
            ],
            data["counts"],
        )
        self.assertEqual(2, index.surface_count("Alice"))
        self.assertEqual(2, index.lemma_count("alice"))
        self.assertEqual(2, index.upos_count("PROPN"))

    def test_validate_lexicon_rejects_mutation_against_source_detail(self):
        body = "The old machine hummed."
        options = sidecar.LinguisticsOptions(
            backend_name="fake",
            include_token_detail=True,
            token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
        )
        _, detail = sidecar.build_sidecar(
            story_data=_story_data(body),
            story_path=pathlib.Path("collection/story/story.json"),
            backend=_v2_backend(body),
            options=options,
        )
        data = lexicon.build_lexicon(detail)
        data["counts"][0]["count"] += 1

        result = lexicon.validate_lexicon(data, source_token_detail=detail)
        kinds = {finding.kind for finding in result.findings}

        self.assertFalse(result.valid)
        self.assertIn("token_count_mismatch", kinds)
        self.assertIn("regeneration_mismatch", kinds)

    def test_validate_lexicon_rejects_stale_source_fingerprint(self):
        body = "The old machine hummed."
        options = sidecar.LinguisticsOptions(
            backend_name="fake",
            include_token_detail=True,
            token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
        )
        _, detail = sidecar.build_sidecar(
            story_data=_story_data(body),
            story_path=pathlib.Path("collection/story/story.json"),
            backend=_v2_backend(body),
            options=options,
        )
        data = lexicon.build_lexicon(detail)
        changed_detail = json.loads(sidecar.dumps_json(detail))
        changed_detail["sentences"][0]["tokens"][1]["lemma"] = "machines"

        result = lexicon.validate_lexicon(data, source_token_detail=changed_detail)
        kinds = {finding.kind for finding in result.findings}

        self.assertFalse(result.valid)
        self.assertIn("source_token_detail_mismatch", kinds)
        self.assertIn("regeneration_mismatch", kinds)

    def test_validate_lexicon_rejects_boolean_integer_fields(self):
        body = "The old machine hummed."
        options = sidecar.LinguisticsOptions(
            backend_name="fake",
            include_token_detail=True,
            token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
        )
        _, detail = sidecar.build_sidecar(
            story_data=_story_data(body),
            story_path=pathlib.Path("collection/story/story.json"),
            backend=_v2_backend(body),
            options=options,
        )
        data = lexicon.build_lexicon(detail)
        data["counts"][0]["count"] = True
        data["denominators"]["token_count"] = True
        data["denominators"]["sentence_count"] = False
        data["denominators"]["lexical_row_count"] = True

        result = lexicon.validate_lexicon(data, source_token_detail=detail)
        paths = {finding.path for finding in result.findings}
        kinds = {finding.kind for finding in result.findings}

        self.assertFalse(result.valid)
        self.assertIn("$.counts[0].count", paths)
        self.assertIn("$.denominators.token_count", paths)
        self.assertIn("$.denominators.sentence_count", paths)
        self.assertIn("$.denominators.lexical_row_count", paths)
        self.assertIn("regeneration_mismatch", kinds)

    def test_query_benchmark_uses_indexed_lexicon_rows(self):
        body = "Alice saw Alice."
        options = sidecar.LinguisticsOptions(
            backend_name="fake",
            include_token_detail=True,
            token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
        )
        _, detail = sidecar.build_sidecar(
            story_data=_story_data(body),
            story_path=pathlib.Path("collection/story/story.json"),
            backend=nlp_backend.FakeNLPBackend(
                sentences=[
                    nlp_backend.SentenceRecord(
                        tokens=[
                            _offset_token(body, "Alice", "PROPN", 2, 0),
                            _offset_token(body, "saw", "VERB", 0, 0),
                            _offset_token(body, "Alice", "PROPN", 2, 10),
                            _offset_token(body, ".", "PUNCT", 2, 10),
                        ],
                        start_char=0,
                        end_char=len(body),
                    )
                ]
            ),
            options=options,
        )
        data = lexicon.build_lexicon(detail)

        report = lexicon.benchmark_queries(
            data,
            [
                {"field": "surface", "value": "Alice"},
                {"field": "lemma", "value": "alice"},
                {"field": "upos", "value": "PROPN"},
                {"field": "upos", "value": "NOUN"},
            ],
        )

        self.assertEqual([2, 2, 2, 0], report["results"])
        self.assertEqual(16, report["token_scan_row_visits"])
        self.assertEqual(7, report["indexed_row_visits"])
        self.assertGreater(report["estimated_row_visits_saved"], 0)
        self.assertGreaterEqual(report["elapsed_ns"], 0)

    def test_query_benchmark_guards_unvalidated_denominators(self):
        data = {
            "denominators": {"token_count": "not-an-int"},
            "counts": [
                {"surface": "Alice", "lemma": "alice", "upos": "PROPN", "count": 2}
            ],
        }

        report = lexicon.benchmark_queries(
            data, [{"field": "surface", "value": "Alice"}]
        )

        self.assertEqual([2], report["results"])
        self.assertEqual(0, report["token_row_count"])
        self.assertEqual(1, report["lexicon_row_count"])
        self.assertEqual(0, report["token_scan_row_visits"])

        malformed_report = lexicon.benchmark_queries(
            {"denominators": None, "counts": "not-rows"},
            [{"field": "surface", "value": "Alice"}],
        )
        self.assertEqual([0], malformed_report["results"])
        self.assertEqual(0, malformed_report["token_row_count"])
        self.assertEqual(0, malformed_report["lexicon_row_count"])


class LinguisticsRunnerTest(unittest.TestCase):
    def test_run_story_writes_sidecar_and_detail(self):
        with tempfile.TemporaryDirectory() as tmp:
            story_path = _write_story(pathlib.Path(tmp) / "collection" / "story")
            options = sidecar.LinguisticsOptions(
                backend_name="fake", include_token_detail=True
            )

            result = runner.run_story(story_path, backend=_backend(), options=options)

            self.assertEqual(runner.STATUS_WRITTEN, result.status)
            self.assertTrue((story_path.parent / sidecar.SIDECAR_FILENAME).is_file())
            self.assertTrue(
                (story_path.parent / sidecar.TOKEN_DETAIL_FILENAME).is_file()
            )

    def test_run_story_redirects_sidecar_under_output_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            story_path = _write_story(root / "collection" / "story")
            output_root = root / "linguistics-output"

            result = runner.run_story(
                story_path,
                backend=_backend(),
                options=sidecar.LinguisticsOptions(backend_name="fake"),
                output_root=output_root,
            )

            redirected = output_root / "collection" / "story" / sidecar.SIDECAR_FILENAME
            self.assertEqual(runner.STATUS_WRITTEN, result.status)
            self.assertEqual(redirected, result.sidecar_path)
            self.assertTrue(redirected.is_file())
            self.assertFalse((story_path.parent / sidecar.SIDECAR_FILENAME).exists())
            data = sidecar.load_json(redirected)
            self.assertEqual(story_path.as_posix(), data["input"]["source_path"])

    def test_run_story_redirects_token_detail_under_output_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            story_path = _write_story(root / "collection" / "story")
            output_root = root / "linguistics-output"
            options = sidecar.LinguisticsOptions(
                backend_name="fake", include_token_detail=True
            )

            result = runner.run_story(
                story_path,
                backend=_backend(),
                options=options,
                output_root=output_root,
            )

            redirected_detail = (
                output_root / "collection" / "story" / sidecar.TOKEN_DETAIL_FILENAME
            )
            self.assertEqual(redirected_detail, result.detail_path)
            self.assertTrue(redirected_detail.is_file())
            self.assertFalse(
                (story_path.parent / sidecar.TOKEN_DETAIL_FILENAME).exists()
            )

    def test_run_story_redirects_v2_token_detail_under_output_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            body = "The old machine hummed."
            story_path = _write_story(root / "collection" / "story", body=body)
            output_root = root / "linguistics-output"
            options = sidecar.LinguisticsOptions(
                backend_name="fake",
                include_token_detail=True,
                token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
            )

            result = runner.run_story(
                story_path,
                backend=_v2_backend(body),
                options=options,
                output_root=output_root,
            )

            redirected_detail = (
                output_root / "collection" / "story" / sidecar.TOKEN_DETAIL_FILENAME
            )
            detail = sidecar.load_json(redirected_detail)
            self.assertEqual(runner.STATUS_WRITTEN, result.status)
            self.assertEqual(sidecar.DETAIL_V2_SCHEMA_VERSION, detail["schema_version"])
            self.assertEqual("v2", detail["options"]["token_detail_version"])
            self.assertEqual(redirected_detail, result.detail_path)

    def test_run_story_writes_lexicon_from_v2_token_detail(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = "The old machine hummed."
            story_path = _write_story(
                pathlib.Path(tmp) / "collection" / "story", body=body
            )
            options = sidecar.LinguisticsOptions(
                backend_name="fake",
                include_token_detail=True,
                token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
            )

            result = runner.run_story(
                story_path,
                backend=_v2_backend(body),
                options=options,
                include_lexicon=True,
            )

            lexicon_path = story_path.parent / lexicon.LEXICON_FILENAME
            detail = sidecar.load_json(
                story_path.parent / sidecar.TOKEN_DETAIL_FILENAME
            )
            data = sidecar.load_json(lexicon_path)
            self.assertEqual(runner.STATUS_WRITTEN, result.status)
            self.assertEqual(lexicon_path, result.lexicon_path)
            self.assertTrue(
                lexicon.validate_lexicon(data, source_token_detail=detail).valid
            )

    def test_lexicon_requires_v2_token_detail_option(self):
        with tempfile.TemporaryDirectory() as tmp:
            story_path = _write_story(pathlib.Path(tmp) / "collection" / "story")

            result = runner.run_story(
                story_path,
                backend=_backend(),
                options=sidecar.LinguisticsOptions(backend_name="fake"),
                include_lexicon=True,
            )

            self.assertEqual(runner.STATUS_FAILED, result.status)
            self.assertIn("token-detail-version v2", result.message)
            self.assertFalse((story_path.parent / lexicon.LEXICON_FILENAME).exists())

    def test_matching_existing_output_skips_without_backend_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            story_path = _write_story(pathlib.Path(tmp) / "collection" / "story")
            backend = _backend()
            options = sidecar.LinguisticsOptions(backend_name="fake")
            first = runner.run_story(story_path, backend=backend, options=options)
            self.assertEqual(runner.STATUS_WRITTEN, first.status)
            second_backend = _backend()

            second = runner.run_story(
                story_path, backend=second_backend, options=options
            )

            self.assertEqual(runner.STATUS_SKIPPED, second.status)
            self.assertEqual([], second_backend.calls)

    def test_default_duplicate_story_input_uses_existing_output_semantics(self):
        with tempfile.TemporaryDirectory() as tmp:
            story_path = _write_story(pathlib.Path(tmp) / "collection" / "story")

            summary = runner.run(
                [story_path, story_path],
                backend=_backend(),
                options=sidecar.LinguisticsOptions(backend_name="fake"),
            )

            self.assertTrue(summary.clean)
            self.assertEqual(
                [runner.STATUS_WRITTEN, runner.STATUS_SKIPPED],
                [result.status for result in summary.results],
            )

    def test_matching_redirected_output_skips_without_backend_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            story_path = _write_story(root / "collection" / "story")
            output_root = root / "linguistics-output"
            options = sidecar.LinguisticsOptions(backend_name="fake")
            first = runner.run_story(
                story_path,
                backend=_backend(),
                options=options,
                output_root=output_root,
            )
            self.assertEqual(runner.STATUS_WRITTEN, first.status)
            second_backend = _backend()

            second = runner.run_story(
                story_path,
                backend=second_backend,
                options=options,
                output_root=output_root,
            )

            self.assertEqual(runner.STATUS_SKIPPED, second.status)
            self.assertEqual([], second_backend.calls)

    def test_redirected_validate_reports_stale_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            story_path = _write_story(root / "collection" / "story")
            output_root = root / "linguistics-output"
            options = sidecar.LinguisticsOptions(backend_name="fake")
            runner.run_story(
                story_path,
                backend=_backend(),
                options=options,
                output_root=output_root,
            )
            _write_story(story_path.parent, body="Changed body")

            result = runner.run_story(
                story_path,
                backend=_backend(),
                options=options,
                existing=runner.EXISTING_VALIDATE,
                output_root=output_root,
            )

            self.assertEqual(runner.STATUS_FAILED, result.status)
            self.assertIn("valid but stale", result.message)

    def test_token_detail_resume_requires_existing_detail_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            story_path = _write_story(pathlib.Path(tmp) / "collection" / "story")
            options = sidecar.LinguisticsOptions(
                backend_name="fake", include_token_detail=True
            )
            first = runner.run_story(story_path, backend=_backend(), options=options)
            self.assertEqual(runner.STATUS_WRITTEN, first.status)
            (story_path.parent / sidecar.TOKEN_DETAIL_FILENAME).unlink()
            second_backend = _backend()

            second = runner.run_story(
                story_path, backend=second_backend, options=options
            )

            self.assertEqual(runner.STATUS_FAILED, second.status)
            self.assertIn("token detail is missing", second.message)
            self.assertEqual([], second_backend.calls)

    def test_token_detail_resume_requires_matching_detail_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            story_path = _write_story(pathlib.Path(tmp) / "collection" / "story")
            options = sidecar.LinguisticsOptions(
                backend_name="fake", include_token_detail=True
            )
            runner.run_story(story_path, backend=_backend(), options=options)
            detail_path = story_path.parent / sidecar.TOKEN_DETAIL_FILENAME
            detail = sidecar.load_json(detail_path)
            detail["input"]["body_sha256"] = "stale"
            sidecar.write_json_atomic(detail_path, detail)
            second_backend = _backend()

            second = runner.run_story(
                story_path, backend=second_backend, options=options
            )

            self.assertEqual(runner.STATUS_FAILED, second.status)
            self.assertIn("token detail differs", second.message)
            self.assertEqual([], second_backend.calls)

    def test_token_detail_resume_skips_when_detail_fingerprint_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            story_path = _write_story(pathlib.Path(tmp) / "collection" / "story")
            options = sidecar.LinguisticsOptions(
                backend_name="fake", include_token_detail=True
            )
            first = runner.run_story(story_path, backend=_backend(), options=options)
            self.assertEqual(runner.STATUS_WRITTEN, first.status)
            second_backend = _backend()

            second = runner.run_story(
                story_path, backend=second_backend, options=options
            )

            self.assertEqual(runner.STATUS_SKIPPED, second.status)
            self.assertEqual([], second_backend.calls)

    def test_v2_token_detail_resume_validates_source_spans_before_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = "The old machine hummed."
            story_path = _write_story(pathlib.Path(tmp) / "collection" / "story", body)
            options = sidecar.LinguisticsOptions(
                backend_name="fake",
                include_token_detail=True,
                token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
            )
            first = runner.run_story(
                story_path, backend=_v2_backend(body), options=options
            )
            self.assertEqual(runner.STATUS_WRITTEN, first.status)
            detail_path = story_path.parent / sidecar.TOKEN_DETAIL_FILENAME
            detail = sidecar.load_json(detail_path)
            detail["sentences"][0]["tokens"][1]["text"] = "wrong"
            sidecar.write_json_atomic(detail_path, detail)
            second_backend = _v2_backend(body)

            second = runner.run_story(
                story_path, backend=second_backend, options=options
            )

            self.assertEqual(runner.STATUS_FAILED, second.status)
            self.assertIn("source_span_mismatch", second.message)
            self.assertEqual([], second_backend.calls)

    def test_lexicon_resume_requires_existing_lexicon_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = "The old machine hummed."
            story_path = _write_story(
                pathlib.Path(tmp) / "collection" / "story", body=body
            )
            options = sidecar.LinguisticsOptions(
                backend_name="fake",
                include_token_detail=True,
                token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
            )
            first = runner.run_story(
                story_path,
                backend=_v2_backend(body),
                options=options,
                include_lexicon=True,
            )
            self.assertEqual(runner.STATUS_WRITTEN, first.status)
            (story_path.parent / lexicon.LEXICON_FILENAME).unlink()
            second_backend = _v2_backend(body)

            second = runner.run_story(
                story_path,
                backend=second_backend,
                options=options,
                include_lexicon=True,
            )

            self.assertEqual(runner.STATUS_FAILED, second.status)
            self.assertIn("existing lexicon is missing", second.message)
            self.assertEqual([], second_backend.calls)

    def test_lexicon_resume_validates_against_existing_v2_detail(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = "The old machine hummed."
            story_path = _write_story(
                pathlib.Path(tmp) / "collection" / "story", body=body
            )
            options = sidecar.LinguisticsOptions(
                backend_name="fake",
                include_token_detail=True,
                token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
            )
            first = runner.run_story(
                story_path,
                backend=_v2_backend(body),
                options=options,
                include_lexicon=True,
            )
            self.assertEqual(runner.STATUS_WRITTEN, first.status)
            lexicon_path = story_path.parent / lexicon.LEXICON_FILENAME
            data = sidecar.load_json(lexicon_path)
            data["counts"][0]["count"] += 1
            sidecar.write_json_atomic(lexicon_path, data)
            second_backend = _v2_backend(body)

            second = runner.run_story(
                story_path,
                backend=second_backend,
                options=options,
                include_lexicon=True,
            )

            self.assertEqual(runner.STATUS_FAILED, second.status)
            self.assertIn("existing lexicon is invalid", second.message)
            self.assertEqual([], second_backend.calls)

    def test_lexicon_resume_rejects_boolean_count_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = "The old machine hummed."
            story_path = _write_story(
                pathlib.Path(tmp) / "collection" / "story", body=body
            )
            options = sidecar.LinguisticsOptions(
                backend_name="fake",
                include_token_detail=True,
                token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
            )
            first = runner.run_story(
                story_path,
                backend=_v2_backend(body),
                options=options,
                include_lexicon=True,
            )
            self.assertEqual(runner.STATUS_WRITTEN, first.status)
            lexicon_path = story_path.parent / lexicon.LEXICON_FILENAME
            data = sidecar.load_json(lexicon_path)
            data["counts"][0]["count"] = True
            data["denominators"]["token_count"] = True
            data["denominators"]["sentence_count"] = False
            data["denominators"]["lexical_row_count"] = True
            sidecar.write_json_atomic(lexicon_path, data)
            second_backend = _v2_backend(body)

            second = runner.run_story(
                story_path,
                backend=second_backend,
                options=options,
                include_lexicon=True,
            )

            self.assertEqual(runner.STATUS_FAILED, second.status)
            self.assertIn("existing lexicon is invalid", second.message)
            self.assertIn("wrong_type", second.message)
            self.assertEqual([], second_backend.calls)

    def test_explicit_overwrite_replaces_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            story_path = _write_story(pathlib.Path(tmp) / "collection" / "story")
            options = sidecar.LinguisticsOptions(backend_name="fake")
            runner.run_story(story_path, backend=_backend(), options=options)
            _write_story(story_path.parent, body="Changed body")

            result = runner.run_story(
                story_path,
                backend=_backend(),
                options=options,
                existing=runner.EXISTING_OVERWRITE,
            )

            data = sidecar.load_json(story_path.parent / sidecar.SIDECAR_FILENAME)
            self.assertEqual(runner.STATUS_WRITTEN, result.status)
            self.assertEqual(
                sidecar.body_sha256("Changed body"), data["input"]["body_sha256"]
            )

    def test_redirected_overwrite_replaces_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            story_path = _write_story(root / "collection" / "story")
            output_root = root / "linguistics-output"
            options = sidecar.LinguisticsOptions(backend_name="fake")
            runner.run_story(
                story_path,
                backend=_backend(),
                options=options,
                output_root=output_root,
            )
            _write_story(story_path.parent, body="Changed body")

            result = runner.run_story(
                story_path,
                backend=_backend(),
                options=options,
                existing=runner.EXISTING_OVERWRITE,
                output_root=output_root,
            )

            redirected = output_root / "collection" / "story" / sidecar.SIDECAR_FILENAME
            data = sidecar.load_json(redirected)
            self.assertEqual(runner.STATUS_WRITTEN, result.status)
            self.assertEqual(
                sidecar.body_sha256("Changed body"), data["input"]["body_sha256"]
            )

    def test_stale_existing_output_fails_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            story_path = _write_story(pathlib.Path(tmp) / "collection" / "story")
            options = sidecar.LinguisticsOptions(backend_name="fake")
            runner.run_story(story_path, backend=_backend(), options=options)
            _write_story(story_path.parent, body="Changed body")

            result = runner.run_story(story_path, backend=_backend(), options=options)

            self.assertEqual(runner.STATUS_FAILED, result.status)
            self.assertIn("--existing overwrite", result.message)

    def test_batch_failure_isolated_per_story(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            good = _write_story(root / "collection" / "good")
            bad = root / "collection" / "missing" / "story.json"

            summary = runner.run(
                [good, bad],
                backend=_backend(),
                options=sidecar.LinguisticsOptions(backend_name="fake"),
            )

            self.assertFalse(summary.clean)
            statuses = [result.status for result in summary.results]
            self.assertEqual([runner.STATUS_WRITTEN, runner.STATUS_FAILED], statuses)

    def test_redirected_batch_detects_duplicate_output_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            first = _write_story(root / "first-root" / "collection" / "story")
            second = _write_story(root / "second-root" / "collection" / "story")
            output_root = root / "linguistics-output"

            summary = runner.run(
                [first, second],
                backend=_backend(),
                options=sidecar.LinguisticsOptions(backend_name="fake"),
                output_root=output_root,
            )

            self.assertFalse(summary.clean)
            self.assertEqual(
                [runner.STATUS_WRITTEN, runner.STATUS_FAILED],
                [result.status for result in summary.results],
            )
            self.assertIn("same output sidecar path", summary.results[1].message)

    def test_redirected_batch_detects_symlinked_duplicate_output_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            first = _write_story(root / "alpha-source" / "alpha" / "story")
            second = _write_story(root / "beta-source" / "beta" / "story")
            output_root = root / "linguistics-output"
            (output_root / "beta").mkdir(parents=True)
            (output_root / "alpha").symlink_to(output_root / "beta")

            summary = runner.run(
                [first, second],
                backend=_backend(),
                options=sidecar.LinguisticsOptions(backend_name="fake"),
                output_root=output_root,
            )

            self.assertFalse(summary.clean)
            self.assertEqual(
                [runner.STATUS_WRITTEN, runner.STATUS_FAILED],
                [result.status for result in summary.results],
            )
            self.assertIn("same output sidecar path", summary.results[1].message)

    def test_redirected_output_path_failure_is_isolated_per_story(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            story_path = _write_story(root / "collection" / "story")
            output_root = root / "linguistics-output"

            with mock.patch.object(sidecar, "story_identity", return_value="../story"):
                summary = runner.run(
                    [story_path],
                    backend=_backend(),
                    options=sidecar.LinguisticsOptions(backend_name="fake"),
                    output_root=output_root,
                )

            self.assertFalse(summary.clean)
            self.assertEqual(runner.STATUS_FAILED, summary.results[0].status)
            self.assertIn("could not resolve output path", summary.results[0].message)

    def test_run_summary_records_output_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            story_path = _write_story(root / "collection" / "story")
            output_root = root / "linguistics-output"

            summary = runner.run(
                [story_path],
                backend=_backend(),
                options=sidecar.LinguisticsOptions(backend_name="fake"),
                output_root=output_root,
            )

            self.assertEqual(output_root.as_posix(), summary.to_dict()["output_root"])

    def test_run_summary_omits_output_root_when_default_output_is_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            story_path = _write_story(pathlib.Path(tmp) / "collection" / "story")

            summary = runner.run(
                [story_path],
                backend=_backend(),
                options=sidecar.LinguisticsOptions(backend_name="fake"),
            )

            self.assertNotIn("output_root", summary.to_dict())

    def test_resolve_story_paths_accepts_bucket_directory_and_story_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            story_path = _write_story(root / "collection" / "story")
            story_list = root / "stories.txt"
            story_list.write_text("collection/story\n", encoding="utf-8")

            resolved = runner.resolve_story_paths(
                [story_path.parent], story_list_files=[story_list]
            )

            self.assertEqual([story_path], resolved)

    def test_missing_explicit_input_is_reported_as_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = pathlib.Path(tmp) / "missing" / "story.json"

            resolved = runner.resolve_story_inputs([missing])
            summary = runner.run(
                resolved.story_paths,
                backend=_backend(),
                options=sidecar.LinguisticsOptions(backend_name="fake"),
            )
            summary = runner.with_prepended_results(
                summary, runner.missing_input_results(resolved.missing_paths)
            )

            self.assertFalse(summary.clean)
            self.assertEqual({"failed": 1}, summary.to_dict()["counts"])
            self.assertEqual("input path does not exist", summary.results[0].message)

    def test_missing_backend_package_or_model_diagnostics_are_clear(self):
        with mock.patch(
            "lcats.analysis.event_role_world.nlp_backend.SpacyBackend",
            side_effect=OSError("missing"),
        ):
            with self.assertRaisesRegex(RuntimeError, "spaCy model"):
                runner.make_backend("spacy", "missing_model")

        with self.assertRaisesRegex(ValueError, "Unknown NLP backend"):
            runner.make_backend("not_real")


class LinguisticsCliTest(unittest.TestCase):
    def test_cli_passes_output_root_to_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            story_path = _write_story(root / "collection" / "story")
            output_root = root / "linguistics-output"

            status = linguistics_cli.run(
                [
                    str(story_path),
                    "--backend",
                    "fake",
                    "--output-root",
                    str(output_root),
                    "--summary-output",
                    str(root / "summary.json"),
                ]
            )

            self.assertEqual(0, status)
            self.assertTrue(
                (
                    output_root / "collection" / "story" / sidecar.SIDECAR_FILENAME
                ).is_file()
            )

    def test_cli_can_request_v2_token_detail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            body = "The old machine hummed."
            story_path = _write_story(root / "collection" / "story", body=body)

            with mock.patch.object(
                runner, "make_backend", return_value=_v2_backend(body)
            ):
                status = linguistics_cli.run(
                    [
                        str(story_path),
                        "--backend",
                        "fake",
                        "--include-token-detail",
                        "--token-detail-version",
                        "v2",
                        "--summary-output",
                        str(root / "summary.json"),
                    ]
                )

            detail = sidecar.load_json(
                story_path.parent / sidecar.TOKEN_DETAIL_FILENAME
            )
            summary = sidecar.load_json(root / "summary.json")
            self.assertEqual(0, status)
            self.assertEqual(sidecar.DETAIL_V2_SCHEMA_VERSION, detail["schema_version"])
            self.assertEqual("v2", summary["token_detail_version"])

    def test_cli_rejects_lexicon_flags_before_backend_loading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            story_path = _write_story(root / "collection" / "story")

            with (
                mock.patch.object(runner, "make_backend") as make_backend,
                mock.patch.object(sys, "stderr", new=StringIO()) as stderr,
            ):
                status = linguistics_cli.run(
                    [str(story_path), "--include-lexicon", "--backend", "spacy"]
                )

            self.assertEqual(2, status)
            make_backend.assert_not_called()
            self.assertIn("--include-token-detail", stderr.getvalue())

    def test_cli_can_request_lexicon_from_v2_token_detail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            body = "The old machine hummed."
            story_path = _write_story(root / "collection" / "story", body=body)

            with mock.patch.object(
                runner, "make_backend", return_value=_v2_backend(body)
            ):
                status = linguistics_cli.run(
                    [
                        str(story_path),
                        "--backend",
                        "fake",
                        "--include-token-detail",
                        "--token-detail-version",
                        "v2",
                        "--include-lexicon",
                        "--summary-output",
                        str(root / "summary.json"),
                    ]
                )

            data = sidecar.load_json(story_path.parent / lexicon.LEXICON_FILENAME)
            summary = sidecar.load_json(root / "summary.json")
            self.assertEqual(0, status)
            self.assertTrue(lexicon.validate_lexicon(data).valid)
            self.assertTrue(summary["include_lexicon"])
            self.assertEqual(
                (story_path.parent / lexicon.LEXICON_FILENAME).as_posix(),
                summary["results"][0]["lexicon_path"],
            )


class LinguisticsFixtureTest(unittest.TestCase):
    def test_representative_fixture_bucket_runs_end_to_end(self):
        fixture = (
            pathlib.Path(__file__).parent
            / "fixtures"
            / "linguistics"
            / "sample_collection"
            / "sample_story"
        )
        with tempfile.TemporaryDirectory() as tmp:
            target = pathlib.Path(tmp) / "sample_collection" / "sample_story"
            target.mkdir(parents=True)
            (target / "story.json").write_text(
                (fixture / "story.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            summary = runner.run(
                [target / "story.json"],
                backend=_backend(),
                options=sidecar.LinguisticsOptions(backend_name="fake"),
            )

            self.assertTrue(summary.clean)
            output = sidecar.load_json(target / sidecar.SIDECAR_FILENAME)
            self.assertTrue(sidecar.validate_sidecar(output).valid)


def _spacy_model_available() -> bool:
    try:
        from lcats.analysis.event_role_world import nlp_backend as nlp_module

        nlp_module.SpacyBackend()
        return True
    except Exception:  # noqa: BLE001
        return False


class LinguisticsOptionalNLPTest(unittest.TestCase):
    @unittest.skipUnless(
        _spacy_model_available(),
        "spaCy en_core_web_sm unavailable; optional smoke test skipped",
    )
    def test_spacy_smoke_backend_can_build_sidecar(self):
        backend = runner.make_backend("spacy")

        data, _ = sidecar.build_sidecar(
            story_data=_story_data("The old machine hummed."),
            story_path=pathlib.Path("c/s/story.json"),
            backend=backend,
            options=sidecar.LinguisticsOptions(backend_name="spacy"),
        )

        self.assertTrue(sidecar.validate_sidecar(data).valid)
