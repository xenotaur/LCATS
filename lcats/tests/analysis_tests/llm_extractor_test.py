"""Unit tests for lcats.analysis.llm_extractor."""

import json
import unittest
from unittest.mock import MagicMock

from parameterized import parameterized

from lcats.analysis import llm_extractor
from lcats.llm import fake_backend

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_extractor(**kwargs):
    """Return a JSONPromptExtractor backed by a FakeBackend.

    Pass `response_text=` to control what the backend returns.
    Pass `backend=` to supply a fully configured FakeBackend (overrides response_text).
    All other kwargs are forwarded to JSONPromptExtractor.
    Note: force_json is intentionally omitted here to avoid DeprecationWarning in
    tests that don't specifically test the deprecation path.
    """
    if "backend" not in kwargs:
        response_text = kwargs.pop("response_text", "")
        fb_model = kwargs.pop("fb_model", "fake-1.0")
        kwargs["backend"] = fake_backend.FakeBackend(
            response_text=response_text, model=fb_model
        )
    defaults = dict(
        system_prompt="You are a helpful assistant.",
        user_prompt_template="Analyse: {story_text}",
        output_key="segments",
        default_model="gpt-4o",
        temperature=0.2,
    )
    defaults.update(kwargs)
    return llm_extractor.JSONPromptExtractor(**defaults)


class _RaisingBackend:
    """Stub backend that always raises a given exception from complete()."""

    def __init__(self, exc):
        self._exc = exc

    def complete(
        self, *, system, messages, model, temperature=0.2, max_tokens=4096, tool=None
    ):
        raise self._exc


# ---------------------------------------------------------------------------
# Tests: __init__
# ---------------------------------------------------------------------------


class TestJSONPromptExtractorInit(unittest.TestCase):
    """Verify that __init__ stores all parameters correctly."""

    def test_stores_required_params(self):
        """Constructor stores system_prompt, user_prompt_template, and output_key."""
        fb = fake_backend.FakeBackend()
        ext = llm_extractor.JSONPromptExtractor(
            fb,
            system_prompt="sys",
            user_prompt_template="tmpl {story_text}",
            output_key="items",
        )
        self.assertIs(ext.backend, fb)
        self.assertEqual(ext.system_prompt, "sys")
        self.assertEqual(ext.user_prompt_template, "tmpl {story_text}")
        self.assertEqual(ext.output_key, "items")

    def test_default_model_and_temperature(self):
        """Default model and temperature have expected values."""
        ext = _make_extractor()
        self.assertEqual(ext.default_model, "gpt-4o")
        self.assertAlmostEqual(ext.temperature, 0.2)

    def test_force_json_default(self):
        """force_json attribute defaults to True when not explicitly passed."""
        ext = _make_extractor()
        self.assertTrue(ext.force_json)

    def test_force_json_deprecated_warning_on_explicit_true(self):
        """Passing force_json=True emits DeprecationWarning."""
        fb = fake_backend.FakeBackend()
        with self.assertWarns(DeprecationWarning):
            llm_extractor.JSONPromptExtractor(
                fb,
                system_prompt="sys",
                user_prompt_template="tmpl {story_text}",
                force_json=True,
            )

    def test_force_json_deprecated_warning_on_false(self):
        """Passing force_json=False also emits DeprecationWarning."""
        fb = fake_backend.FakeBackend()
        with self.assertWarns(DeprecationWarning):
            llm_extractor.JSONPromptExtractor(
                fb,
                system_prompt="sys",
                user_prompt_template="tmpl {story_text}",
                force_json=False,
            )

    def test_no_warning_when_force_json_not_passed(self):
        """Omitting force_json does not emit any DeprecationWarning."""
        import warnings

        fb = fake_backend.FakeBackend()
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            llm_extractor.JSONPromptExtractor(
                fb,
                system_prompt="sys",
                user_prompt_template="tmpl {story_text}",
            )

    def test_client_kwarg_deprecated_alias(self):
        """Passing client= as keyword arg emits DeprecationWarning and stores as backend."""
        fb = fake_backend.FakeBackend()
        with self.assertWarns(DeprecationWarning):
            ext = llm_extractor.JSONPromptExtractor(
                client=fb,
                system_prompt="sys",
                user_prompt_template="tmpl {story_text}",
            )
        self.assertIs(ext.backend, fb)

    def test_client_and_backend_together_raises(self):
        """Passing both client= and backend= positionally raises TypeError."""
        fb = fake_backend.FakeBackend()
        import warnings

        with self.assertRaises(TypeError):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                llm_extractor.JSONPromptExtractor(
                    fb,
                    client=fb,
                    system_prompt="sys",
                    user_prompt_template="tmpl {story_text}",
                )

    def test_missing_backend_raises(self):
        """Calling without backend= or client= raises TypeError."""
        with self.assertRaises(TypeError):
            llm_extractor.JSONPromptExtractor(
                system_prompt="sys",
                user_prompt_template="tmpl {story_text}",
            )

    def test_optional_hooks_default_to_none(self):
        """text_indexer, result_aligner, result_validator default to None."""
        ext = _make_extractor()
        self.assertIsNone(ext.text_indexer)
        self.assertIsNone(ext.result_aligner)
        self.assertIsNone(ext.result_validator)

    def test_debug_attributes_default_to_none(self):
        """Debug/inspection attributes are None after construction."""
        ext = _make_extractor()
        self.assertIsNone(ext.last_messages)
        self.assertIsNone(ext.last_response)
        self.assertIsNone(ext.last_raw_output)
        self.assertIsNone(ext.last_index_meta)
        self.assertIsNone(ext.last_validation_report)

    def test_optional_hooks_stored(self):
        """Provided hooks are stored on the instance."""

        def indexer(text):
            return (text, {})

        def aligner(parsed, text, meta):
            return parsed

        def validator(parsed, text, meta):
            return {}

        ext = _make_extractor(
            text_indexer=indexer, result_aligner=aligner, result_validator=validator
        )
        self.assertIs(ext.text_indexer, indexer)
        self.assertIs(ext.result_aligner, aligner)
        self.assertIs(ext.result_validator, validator)


# ---------------------------------------------------------------------------
# Tests: _prepare_user_content
# ---------------------------------------------------------------------------


class TestPrepareUserContent(unittest.TestCase):
    """Tests for _prepare_user_content with and without text_indexer."""

    def test_without_indexer_formats_both_keys(self):
        """Without indexer both story_text and indexed_story_text resolve to raw text."""
        ext = _make_extractor(
            user_prompt_template="raw={story_text} idx={indexed_story_text}"
        )
        content, meta = ext._prepare_user_content("hello")
        self.assertEqual(content, "raw=hello idx=hello")
        self.assertIsNone(meta)
        self.assertIsNone(ext.last_index_meta)

    def test_with_indexer_uses_indexed_text(self):
        """With indexer, both keys use the indexed text; meta is stored."""
        indexed = "[P0001] hello"
        index_meta = {"n_paragraphs": 1}
        indexer = MagicMock(return_value=(indexed, index_meta))
        ext = _make_extractor(
            user_prompt_template="raw={story_text} idx={indexed_story_text}",
            text_indexer=indexer,
        )
        content, meta = ext._prepare_user_content("hello")
        self.assertEqual(content, f"raw={indexed} idx={indexed}")
        self.assertIs(meta, index_meta)
        self.assertIs(ext.last_index_meta, index_meta)
        indexer.assert_called_once_with("hello")


# ---------------------------------------------------------------------------
# Tests: build_messages
# ---------------------------------------------------------------------------


class TestBuildMessages(unittest.TestCase):
    """Tests for build_messages."""

    def test_returns_system_and_user_messages(self):
        """build_messages returns exactly two messages in correct order."""
        ext = _make_extractor(
            system_prompt="System prompt",
            user_prompt_template="User: {story_text}",
        )
        msgs = ext.build_messages("my story")
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[0]["content"], "System prompt")
        self.assertEqual(msgs[1]["role"], "user")
        self.assertIn("my story", msgs[1]["content"])

    def test_does_not_call_backend(self):
        """build_messages should not call the backend."""
        fb = fake_backend.FakeBackend()
        ext = _make_extractor(backend=fb)
        ext.build_messages("some text")
        self.assertEqual(fb.calls, [])


# ---------------------------------------------------------------------------
# Tests: _extract_error_json
# ---------------------------------------------------------------------------


class TestExtractErrorJson(unittest.TestCase):
    """Tests for _extract_error_json."""

    def setUp(self):
        self.ext = _make_extractor()

    def test_extracts_json_from_string(self):
        """Finds a JSON object at the end of an error string."""
        # json.loads parses from the first '{' to end of string, so JSON must be at the end.
        text = 'some prefix {"error": {"code": "quota"}}'
        result = self.ext._extract_error_json(text)
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)

    def test_returns_none_when_no_json(self):
        """Returns None when no JSON object is present."""
        result = self.ext._extract_error_json("no json here")
        self.assertIsNone(result)

    def test_returns_none_for_invalid_json(self):
        """Returns None for malformed JSON."""
        result = self.ext._extract_error_json("{not: valid json}")
        self.assertIsNone(result)

    def test_returns_none_for_empty_string(self):
        """Returns None for empty string."""
        result = self.ext._extract_error_json("")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Tests: _classify_api_error
# ---------------------------------------------------------------------------


class TestClassifyApiError(unittest.TestCase):
    """Table-driven tests for _classify_api_error."""

    def setUp(self):
        self.ext = _make_extractor()

    def _classify(self, **kwargs):
        payload = {
            "status": None,
            "code": "",
            "type": "",
            "message": "",
            "raw": "",
        }
        payload.update(kwargs)
        return self.ext._classify_api_error(payload)

    @parameterized.expand(
        [
            (
                "insufficient_quota_code",
                {"code": "insufficient_quota"},
                "quota_exceeded",
            ),
            (
                "quota_in_message",
                {"message": "You have exceeded your quota."},
                "quota_exceeded",
            ),
            ("status_402", {"status": 402}, "quota_exceeded"),
            ("rate_limit_code", {"code": "rate_limit_exceeded"}, "rate_limit"),
            ("rate_limit_message", {"message": "rate limit reached"}, "rate_limit"),
            ("status_429", {"status": 429}, "rate_limit"),
            (
                "tpm_message",
                {"code": "rate_limit_exceeded", "message": "tokens per min"},
                "tpm_limit",
            ),
            (
                "context_length_code",
                {"code": "context_length_exceeded"},
                "context_length",
            ),
            (
                "context_length_message",
                {"message": "maximum context length exceeded"},
                "context_length",
            ),
            ("auth_401", {"status": 401}, "auth"),
            ("auth_api_key", {"message": "invalid api key"}, "auth"),
            ("auth_authentication", {"message": "authentication failed"}, "auth"),
            ("server_500", {"status": 500}, "server"),
            ("server_502", {"status": 502}, "server"),
            ("server_503", {"status": 503}, "server"),
            ("server_504", {"status": 504}, "server"),
            ("server_overloaded", {"message": "the server is overloaded"}, "server"),
            ("unknown", {}, "unknown"),
        ]
    )
    def test_category(self, _name, overrides, expected_category):
        """_classify_api_error returns the expected category."""
        result = self._classify(**overrides)
        self.assertEqual(result["category"], expected_category)

    def test_quota_sets_abort_batch(self):
        """Quota errors should set should_abort_batch=True."""
        result = self._classify(code="insufficient_quota")
        self.assertTrue(result["should_abort_batch"])
        self.assertFalse(result["can_retry"])

    def test_rate_limit_sets_can_retry(self):
        """Rate-limit errors should set can_retry=True."""
        result = self._classify(code="rate_limit_exceeded")
        self.assertTrue(result["can_retry"])
        self.assertFalse(result["should_abort_batch"])

    def test_tpm_sets_needs_smaller_request(self):
        """TPM errors should set needs_smaller_request=True."""
        result = self._classify(
            code="rate_limit_exceeded", message="tokens per min exceeded"
        )
        self.assertTrue(result["needs_smaller_request"])

    def test_context_length_sets_needs_smaller_request(self):
        """Context length errors should set needs_smaller_request=True."""
        result = self._classify(code="context_length_exceeded")
        self.assertTrue(result["needs_smaller_request"])

    def test_server_error_sets_can_retry(self):
        """Server errors should set can_retry=True."""
        result = self._classify(status=500)
        self.assertTrue(result["can_retry"])

    def test_original_payload_fields_preserved(self):
        """The returned dict includes all original payload fields."""
        result = self._classify(code="some_code", message="some msg", status=999)
        self.assertEqual(result["code"], "some_code")
        self.assertEqual(result["message"], "some msg")
        self.assertEqual(result["status"], 999)


# ---------------------------------------------------------------------------
# Tests: _normalize_api_error
# ---------------------------------------------------------------------------


class TestNormalizeApiError(unittest.TestCase):
    """Tests for _normalize_api_error."""

    def setUp(self):
        self.ext = _make_extractor()

    def test_uses_str_exc_as_message_fallback(self):
        """When exception has no .message, str(exc) is used."""
        exc = ValueError("something went wrong")
        result = self.ext._normalize_api_error(exc)
        self.assertIn("something went wrong", result["message"])

    def test_reads_status_code_attribute(self):
        """status_code attribute is read from the exception."""
        exc = Exception("err")
        exc.status_code = 429
        result = self.ext._normalize_api_error(exc)
        self.assertEqual(result["status"], 429)

    def test_reads_http_status_attribute(self):
        """http_status attribute is read when status_code is absent."""
        exc = Exception("err")
        exc.http_status = 500
        result = self.ext._normalize_api_error(exc)
        self.assertEqual(result["status"], 500)

    def test_reads_code_attribute(self):
        """code attribute is read from the exception."""
        exc = Exception("err")
        exc.code = "rate_limit_exceeded"
        result = self.ext._normalize_api_error(exc)
        self.assertEqual(result["code"], "rate_limit_exceeded")

    def test_extracts_embedded_json_error_block(self):
        """When exc string contains JSON with an 'error' block, fields are extracted."""
        embedded = json.dumps(
            {
                "error": {
                    "code": "insufficient_quota",
                    "message": "Quota exceeded",
                    "type": "billing",
                }
            }
        )
        exc = Exception(embedded)
        result = self.ext._normalize_api_error(exc)
        self.assertEqual(result["code"], "insufficient_quota")
        self.assertEqual(result["category"], "quota_exceeded")

    def test_classify_is_called(self):
        """The returned dict has 'category' key from _classify_api_error."""
        exc = Exception("generic error")
        result = self.ext._normalize_api_error(exc)
        self.assertIn("category", result)
        self.assertIn("can_retry", result)
        self.assertIn("should_abort_batch", result)


# ---------------------------------------------------------------------------
# Tests: extract — success path
# ---------------------------------------------------------------------------


class TestExtractSuccess(unittest.TestCase):
    """Tests for extract() on the happy path."""

    def test_returns_extracted_output_on_success(self):
        """extract() returns the parsed segments list on a valid JSON response."""
        payload = json.dumps({"segments": [{"id": 1}]})
        ext = _make_extractor(response_text=payload)
        result = ext.extract("some story")
        self.assertIsNone(result["api_error"])
        self.assertIsNone(result["extraction_error"])
        self.assertEqual(result["extracted_output"], [{"id": 1}])

    def test_populates_all_result_keys(self):
        """Result dict contains all expected keys."""
        payload = json.dumps({"segments": []})
        ext = _make_extractor(response_text=payload)
        result = ext.extract("story")
        expected_keys = {
            "story_text",
            "model_name",
            "messages",
            "response",
            "response_id",
            "usage",
            "raw_output",
            "parsed_output",
            "extracted_output",
            "parsing_error",
            "extraction_error",
            "alignment_error",
            "index_meta",
            "validation_report",
            "validation_error",
            "api_error",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_model_name_from_backend_response(self):
        """model_name in result comes from BackendResponse.model."""
        payload = json.dumps({"segments": []})
        fb = fake_backend.FakeBackend(response_text=payload, model="backend-v1")
        ext = _make_extractor(backend=fb)
        result = ext.extract("story")
        self.assertEqual(result["model_name"], "backend-v1")

    def test_model_name_override_passed_to_backend(self):
        """Passing model_name to extract() forwards it to backend.complete()."""
        payload = json.dumps({"segments": []})
        fb = fake_backend.FakeBackend(response_text=payload)
        ext = _make_extractor(backend=fb)
        ext.extract("story", model_name="gpt-3.5-turbo")
        self.assertEqual(fb.calls[0]["model"], "gpt-3.5-turbo")

    def test_usage_dict_has_token_counts(self):
        """usage in result is a dict with input_tokens and output_tokens."""
        payload = json.dumps({"segments": []})
        fb = fake_backend.FakeBackend(
            response_text=payload, input_tokens=10, output_tokens=20
        )
        ext = _make_extractor(backend=fb)
        result = ext.extract("story")
        self.assertEqual(result["usage"], {"input_tokens": 10, "output_tokens": 20})

    def test_last_messages_set(self):
        """After extract(), last_messages is populated."""
        payload = json.dumps({"segments": []})
        ext = _make_extractor(response_text=payload)
        ext.extract("test text")
        self.assertIsNotNone(ext.last_messages)
        self.assertEqual(ext.last_messages[0]["role"], "system")

    def test_last_raw_output_set(self):
        """After a successful call, last_raw_output holds the model response."""
        payload = json.dumps({"segments": [1, 2]})
        ext = _make_extractor(response_text=payload)
        ext.extract("test text")
        self.assertEqual(ext.last_raw_output, payload)

    def test_call_dunder_delegates_to_extract(self):
        """__call__ returns the same result as extract()."""
        payload = json.dumps({"segments": ["a"]})
        fb1 = fake_backend.FakeBackend(response_text=payload)
        ext1 = _make_extractor(backend=fb1)
        result_call = ext1("story text")
        fb2 = fake_backend.FakeBackend(response_text=payload)
        ext2 = _make_extractor(backend=fb2)
        result_extract = ext2.extract("story text")
        self.assertEqual(
            result_call["extracted_output"], result_extract["extracted_output"]
        )


# ---------------------------------------------------------------------------
# Tests: extract — error paths
# ---------------------------------------------------------------------------


class TestExtractErrorPaths(unittest.TestCase):
    """Tests for extract() error/edge cases."""

    def test_api_exception_sets_api_error(self):
        """When the backend raises, api_error is set and extraction_error='api_error'."""
        ext = _make_extractor(backend=_RaisingBackend(RuntimeError("network failure")))
        result = ext.extract("story")
        self.assertIsNotNone(result["api_error"])
        self.assertEqual(result["extraction_error"], "api_error")
        self.assertIsNone(result["extracted_output"])

    def test_api_exception_result_has_all_keys(self):
        """Even on backend exception, result dict has all expected keys."""
        ext = _make_extractor(backend=_RaisingBackend(Exception("fail")))
        result = ext.extract("story")
        expected_keys = {
            "story_text",
            "model_name",
            "messages",
            "response",
            "response_id",
            "usage",
            "raw_output",
            "parsed_output",
            "extracted_output",
            "parsing_error",
            "extraction_error",
            "alignment_error",
            "index_meta",
            "validation_report",
            "validation_error",
            "api_error",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_missing_output_key_sets_extraction_error(self):
        """When JSON is valid but missing output_key, extraction_error is set."""
        ext = _make_extractor(
            response_text=json.dumps({"other_key": []}), output_key="segments"
        )
        result = ext.extract("story")
        self.assertIsNotNone(result["extraction_error"])
        self.assertIn("segments", result["extraction_error"])
        self.assertIsNone(result["extracted_output"])

    def test_invalid_json_sets_parsing_error(self):
        """When model returns fenced invalid JSON, parsing_error is set."""
        ext = _make_extractor(response_text="```json\nnot valid json here\n```")
        result = ext.extract("story")
        self.assertEqual(result["extraction_error"], "parsing_error")
        self.assertIsNone(result["extracted_output"])

    def test_empty_response_text_sets_api_error(self):
        """When backend returns empty text, api_error is set."""
        ext = _make_extractor(response_text="")
        result = ext.extract("story")
        self.assertIsNotNone(result["api_error"])
        self.assertEqual(result["api_error"]["code"], "empty_response")

    def test_story_text_preserved_in_result(self):
        """story_text in result matches the input."""
        ext = _make_extractor(backend=_RaisingBackend(Exception("fail")))
        result = ext.extract("my unique story")
        self.assertEqual(result["story_text"], "my unique story")


# ---------------------------------------------------------------------------
# Tests: extract — with text_indexer
# ---------------------------------------------------------------------------


class TestExtractWithIndexer(unittest.TestCase):
    """Tests for extract() when text_indexer is provided."""

    def test_indexer_is_called_with_story_text(self):
        """text_indexer receives the raw story_text."""
        index_meta = {"canonical_text": "hello", "para_spans": [], "n_paragraphs": 1}
        indexer = MagicMock(return_value=("[P0001] hello", index_meta))
        fb = fake_backend.FakeBackend(response_text=json.dumps({"segments": []}))
        ext = _make_extractor(
            backend=fb,
            text_indexer=indexer,
            user_prompt_template="{story_text}",
        )
        ext.extract("hello")
        indexer.assert_called_once_with("hello")

    def test_index_meta_stored_on_result(self):
        """index_meta from the indexer is stored in the result."""
        index_meta = {"n_paragraphs": 2}
        indexer = MagicMock(return_value=("[P0001] hello\n\n[P0002] world", index_meta))
        fb = fake_backend.FakeBackend(response_text=json.dumps({"segments": []}))
        ext = _make_extractor(
            backend=fb,
            text_indexer=indexer,
            user_prompt_template="{story_text}",
        )
        result = ext.extract("hello world")
        self.assertIs(result["index_meta"], index_meta)


# ---------------------------------------------------------------------------
# Tests: extract — with result_aligner
# ---------------------------------------------------------------------------


class TestExtractWithAligner(unittest.TestCase):
    """Tests for extract() when result_aligner is provided."""

    def test_aligner_called_when_index_meta_present(self):
        """result_aligner is invoked when index_meta is not None."""
        index_meta = {"n_paragraphs": 1}
        indexer = MagicMock(return_value=("[P0001] hello", index_meta))
        aligner = MagicMock(side_effect=lambda parsed, text, meta: parsed)
        fb = fake_backend.FakeBackend(
            response_text=json.dumps({"segments": [{"id": 1}]})
        )
        ext = _make_extractor(
            backend=fb,
            text_indexer=indexer,
            result_aligner=aligner,
            user_prompt_template="{story_text}",
        )
        ext.extract("hello")
        aligner.assert_called_once()

    def test_aligner_not_called_without_index_meta(self):
        """result_aligner is NOT invoked when there is no text_indexer (index_meta=None)."""
        aligner = MagicMock(side_effect=lambda parsed, text, meta: parsed)
        fb = fake_backend.FakeBackend(
            response_text=json.dumps({"segments": [{"id": 1}]})
        )
        ext = _make_extractor(backend=fb, result_aligner=aligner)
        ext.extract("hello")
        aligner.assert_not_called()

    def test_aligner_exception_sets_alignment_error(self):
        """When aligner raises, alignment_error is set in the result."""
        index_meta = {"n_paragraphs": 1}
        indexer = MagicMock(return_value=("[P0001] hello", index_meta))
        aligner = MagicMock(side_effect=RuntimeError("align failed"))
        fb = fake_backend.FakeBackend(
            response_text=json.dumps({"segments": [{"id": 1}]})
        )
        ext = _make_extractor(
            backend=fb,
            text_indexer=indexer,
            result_aligner=aligner,
            user_prompt_template="{story_text}",
        )
        result = ext.extract("hello")
        self.assertIsNotNone(result["alignment_error"])
        self.assertIn("align failed", result["alignment_error"])


# ---------------------------------------------------------------------------
# Tests: extract — with result_validator
# ---------------------------------------------------------------------------


class TestExtractWithValidator(unittest.TestCase):
    """Tests for extract() when result_validator is provided."""

    def test_validator_called_when_index_meta_present(self):
        """result_validator is invoked when index_meta is not None."""
        index_meta = {"n_paragraphs": 1}
        indexer = MagicMock(return_value=("[P0001] hello", index_meta))
        report = {"score": 1.0}
        validator = MagicMock(return_value=report)
        fb = fake_backend.FakeBackend(
            response_text=json.dumps({"segments": [{"id": 1}]})
        )
        ext = _make_extractor(
            backend=fb,
            text_indexer=indexer,
            result_validator=validator,
            user_prompt_template="{story_text}",
        )
        result = ext.extract("hello")
        validator.assert_called_once()
        self.assertIs(result["validation_report"], report)

    def test_validator_not_called_without_index_meta(self):
        """result_validator is NOT invoked when index_meta is None."""
        validator = MagicMock(return_value={})
        fb = fake_backend.FakeBackend(
            response_text=json.dumps({"segments": [{"id": 1}]})
        )
        ext = _make_extractor(backend=fb, result_validator=validator)
        ext.extract("hello")
        validator.assert_not_called()

    def test_validator_exception_sets_validation_error(self):
        """When validator raises, validation_error is set in the result."""
        index_meta = {"n_paragraphs": 1}
        indexer = MagicMock(return_value=("[P0001] hello", index_meta))
        validator = MagicMock(side_effect=RuntimeError("validate failed"))
        fb = fake_backend.FakeBackend(
            response_text=json.dumps({"segments": [{"id": 1}]})
        )
        ext = _make_extractor(
            backend=fb,
            text_indexer=indexer,
            result_validator=validator,
            user_prompt_template="{story_text}",
        )
        result = ext.extract("hello")
        self.assertIsNotNone(result["validation_error"])
        self.assertIn("validate failed", result["validation_error"])

    def test_last_validation_report_set(self):
        """After validation, last_validation_report is set on the extractor."""
        index_meta = {"n_paragraphs": 1}
        indexer = MagicMock(return_value=("[P0001] hello", index_meta))
        report = {"ok": True}
        validator = MagicMock(return_value=report)
        fb = fake_backend.FakeBackend(
            response_text=json.dumps({"segments": [{"id": 1}]})
        )
        ext = _make_extractor(
            backend=fb,
            text_indexer=indexer,
            result_validator=validator,
            user_prompt_template="{story_text}",
        )
        ext.extract("hello")
        self.assertIs(ext.last_validation_report, report)


# ---------------------------------------------------------------------------
# Tests: result is JSON-serializable
# ---------------------------------------------------------------------------


class TestResultSerializable(unittest.TestCase):
    """Invariant: result (without 'response') can be json.dumps'd."""

    def test_success_result_serializable(self):
        """Success result without 'response' key is JSON-serializable."""
        fb = fake_backend.FakeBackend(
            response_text=json.dumps({"segments": [{"id": 1, "text": "hello"}]}),
            input_tokens=5,
            output_tokens=10,
        )
        ext = _make_extractor(backend=fb)
        result = ext.extract("story")
        result_copy = {k: v for k, v in result.items() if k != "response"}
        serialized = json.dumps(result_copy)
        self.assertIsInstance(serialized, str)

    def test_error_result_serializable(self):
        """Error result (api_error path) without 'response' key is JSON-serializable."""
        ext = _make_extractor(backend=_RaisingBackend(RuntimeError("boom")))
        result = ext.extract("story")
        result_copy = {k: v for k, v in result.items() if k != "response"}
        serialized = json.dumps(result_copy)
        self.assertIsInstance(serialized, str)


if __name__ == "__main__":
    unittest.main()
