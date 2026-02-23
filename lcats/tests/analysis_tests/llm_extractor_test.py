"""Unit tests for lcats.analysis.llm_extractor."""

import json
import unittest
from unittest.mock import MagicMock

from parameterized import parameterized

from lcats.analysis import llm_extractor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_extractor(**kwargs):
    """Return a JSONPromptExtractor with sensible defaults."""
    defaults = dict(
        client=MagicMock(),
        system_prompt="You are a helpful assistant.",
        user_prompt_template="Analyse: {story_text}",
        output_key="segments",
        default_model="gpt-4o",
        temperature=0.2,
        force_json=True,
    )
    defaults.update(kwargs)
    return llm_extractor.JSONPromptExtractor(**defaults)


def _make_mock_response(content):
    """Return a mock OpenAI-like response object."""
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    response.id = "resp-001"
    response.usage = None
    return response


# ---------------------------------------------------------------------------
# Tests: __init__
# ---------------------------------------------------------------------------


class TestJSONPromptExtractorInit(unittest.TestCase):
    """Verify that __init__ stores all parameters correctly."""

    def test_stores_required_params(self):
        """Constructor stores system_prompt, user_prompt_template, and output_key."""
        client = MagicMock()
        ext = llm_extractor.JSONPromptExtractor(
            client,
            system_prompt="sys",
            user_prompt_template="tmpl {story_text}",
            output_key="items",
        )
        self.assertIs(ext.client, client)
        self.assertEqual(ext.system_prompt, "sys")
        self.assertEqual(ext.user_prompt_template, "tmpl {story_text}")
        self.assertEqual(ext.output_key, "items")

    def test_default_model_and_temperature(self):
        """Default model and temperature have expected values."""
        ext = _make_extractor()
        self.assertEqual(ext.default_model, "gpt-4o")
        self.assertAlmostEqual(ext.temperature, 0.2)

    def test_force_json_default(self):
        """force_json defaults to True."""
        ext = _make_extractor()
        self.assertTrue(ext.force_json)

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

    def test_does_not_call_client(self):
        """build_messages should not call the client."""
        ext = _make_extractor()
        ext.build_messages("some text")
        ext.client.chat.completions.create.assert_not_called()


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

    def _make_ext_with_response(self, content, output_key="segments"):
        """Return (extractor, mock_client) configured to return content."""
        client = MagicMock()
        response = _make_mock_response(content)
        client.chat.completions.create.return_value = response
        ext = _make_extractor(client=client, output_key=output_key)
        return ext, client, response

    def test_returns_extracted_output_on_success(self):
        """extract() returns the parsed segments list on a valid JSON response."""
        payload = json.dumps({"segments": [{"id": 1}]})
        ext, _, _ = self._make_ext_with_response(payload)
        result = ext.extract("some story")
        self.assertIsNone(result["api_error"])
        self.assertIsNone(result["extraction_error"])
        self.assertEqual(result["extracted_output"], [{"id": 1}])

    def test_populates_all_result_keys(self):
        """Result dict contains all expected keys."""
        payload = json.dumps({"segments": []})
        ext, _, _ = self._make_ext_with_response(payload)
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

    def test_model_name_override(self):
        """Passing model_name overrides the default model."""
        payload = json.dumps({"segments": []})
        ext, _, _ = self._make_ext_with_response(payload)
        result = ext.extract("story", model_name="gpt-3.5-turbo")
        self.assertEqual(result["model_name"], "gpt-3.5-turbo")

    def test_force_json_adds_response_format(self):
        """When force_json=True, response_format is passed to create()."""
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            json.dumps({"segments": []})
        )
        ext = _make_extractor(client=client, force_json=True)
        ext.extract("story")
        call_kwargs = client.chat.completions.create.call_args[1]
        self.assertIn("response_format", call_kwargs)
        self.assertEqual(call_kwargs["response_format"], {"type": "json_object"})

    def test_force_json_false_omits_response_format(self):
        """When force_json=False, response_format is NOT passed to create()."""
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            json.dumps({"segments": []})
        )
        ext = _make_extractor(client=client, force_json=False)
        ext.extract("story")
        call_kwargs = client.chat.completions.create.call_args[1]
        self.assertNotIn("response_format", call_kwargs)

    def test_last_messages_set(self):
        """After extract(), last_messages is populated."""
        payload = json.dumps({"segments": []})
        ext, _, _ = self._make_ext_with_response(payload)
        ext.extract("test text")
        self.assertIsNotNone(ext.last_messages)
        self.assertEqual(ext.last_messages[0]["role"], "system")

    def test_last_raw_output_set(self):
        """After a successful call, last_raw_output holds the model response."""
        payload = json.dumps({"segments": [1, 2]})
        ext, _, _ = self._make_ext_with_response(payload)
        ext.extract("test text")
        self.assertEqual(ext.last_raw_output, payload)

    def test_call_dunder_delegates_to_extract(self):
        """__call__ returns the same result as extract()."""
        payload = json.dumps({"segments": ["a"]})
        ext, _, _ = self._make_ext_with_response(payload)
        result_call = ext("story text")
        ext2, _, _ = self._make_ext_with_response(payload)
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
        """When the client raises, api_error is set and extraction_error='api_error'."""
        client = MagicMock()
        client.chat.completions.create.side_effect = RuntimeError("network failure")
        ext = _make_extractor(client=client)
        result = ext.extract("story")
        self.assertIsNotNone(result["api_error"])
        self.assertEqual(result["extraction_error"], "api_error")
        self.assertIsNone(result["extracted_output"])

    def test_api_exception_result_has_all_keys(self):
        """Even on API exception, result dict has all expected keys."""
        client = MagicMock()
        client.chat.completions.create.side_effect = Exception("fail")
        ext = _make_extractor(client=client)
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
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            json.dumps({"other_key": []})
        )
        ext = _make_extractor(client=client, output_key="segments")
        result = ext.extract("story")
        self.assertIsNotNone(result["extraction_error"])
        self.assertIn("segments", result["extraction_error"])
        self.assertIsNone(result["extracted_output"])

    def test_invalid_json_sets_parsing_error(self):
        """When model returns fenced invalid JSON, parsing_error is set."""
        # Wrap in a fenced block so extract_json attempts json.loads on the content
        # and raises JSONDecodeError (which extract() catches as parsing_error).
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            "```json\nnot valid json here\n```"
        )
        ext = _make_extractor(client=client)
        result = ext.extract("story")
        self.assertEqual(result["extraction_error"], "parsing_error")
        self.assertIsNone(result["extracted_output"])

    def test_empty_response_choices_sets_api_error(self):
        """When response has no choices, api_error is set."""
        client = MagicMock()
        response = MagicMock()
        response.choices = []
        response.id = None
        response.usage = None
        client.chat.completions.create.return_value = response
        ext = _make_extractor(client=client)
        result = ext.extract("story")
        self.assertIsNotNone(result["api_error"])
        self.assertEqual(result["api_error"]["code"], "empty_response")

    def test_story_text_preserved_in_result(self):
        """story_text in result matches the input."""
        client = MagicMock()
        client.chat.completions.create.side_effect = Exception("fail")
        ext = _make_extractor(client=client)
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
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            json.dumps({"segments": []})
        )
        ext = _make_extractor(
            client=client,
            text_indexer=indexer,
            user_prompt_template="{story_text}",
        )
        ext.extract("hello")
        indexer.assert_called_once_with("hello")

    def test_index_meta_stored_on_result(self):
        """index_meta from the indexer is stored in the result."""
        index_meta = {"n_paragraphs": 2}
        indexer = MagicMock(return_value=("[P0001] hello\n\n[P0002] world", index_meta))
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            json.dumps({"segments": []})
        )
        ext = _make_extractor(
            client=client,
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
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            json.dumps({"segments": [{"id": 1}]})
        )
        ext = _make_extractor(
            client=client,
            text_indexer=indexer,
            result_aligner=aligner,
            user_prompt_template="{story_text}",
        )
        ext.extract("hello")
        aligner.assert_called_once()

    def test_aligner_not_called_without_index_meta(self):
        """result_aligner is NOT invoked when there is no text_indexer (index_meta=None)."""
        aligner = MagicMock(side_effect=lambda parsed, text, meta: parsed)
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            json.dumps({"segments": [{"id": 1}]})
        )
        ext = _make_extractor(client=client, result_aligner=aligner)
        ext.extract("hello")
        aligner.assert_not_called()

    def test_aligner_exception_sets_alignment_error(self):
        """When aligner raises, alignment_error is set in the result."""
        index_meta = {"n_paragraphs": 1}
        indexer = MagicMock(return_value=("[P0001] hello", index_meta))
        aligner = MagicMock(side_effect=RuntimeError("align failed"))
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            json.dumps({"segments": [{"id": 1}]})
        )
        ext = _make_extractor(
            client=client,
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
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            json.dumps({"segments": [{"id": 1}]})
        )
        ext = _make_extractor(
            client=client,
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
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            json.dumps({"segments": [{"id": 1}]})
        )
        ext = _make_extractor(client=client, result_validator=validator)
        ext.extract("hello")
        validator.assert_not_called()

    def test_validator_exception_sets_validation_error(self):
        """When validator raises, validation_error is set in the result."""
        index_meta = {"n_paragraphs": 1}
        indexer = MagicMock(return_value=("[P0001] hello", index_meta))
        validator = MagicMock(side_effect=RuntimeError("validate failed"))
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            json.dumps({"segments": [{"id": 1}]})
        )
        ext = _make_extractor(
            client=client,
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
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            json.dumps({"segments": [{"id": 1}]})
        )
        ext = _make_extractor(
            client=client,
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
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            json.dumps({"segments": [{"id": 1, "text": "hello"}]})
        )
        ext = _make_extractor(client=client)
        result = ext.extract("story")
        result_copy = {k: v for k, v in result.items() if k != "response"}
        # Should not raise
        serialized = json.dumps(result_copy)
        self.assertIsInstance(serialized, str)

    def test_error_result_serializable(self):
        """Error result (api_error path) without 'response' key is JSON-serializable."""
        client = MagicMock()
        client.chat.completions.create.side_effect = RuntimeError("boom")
        ext = _make_extractor(client=client)
        result = ext.extract("story")
        result_copy = {k: v for k, v in result.items() if k != "response"}
        serialized = json.dumps(result_copy)
        self.assertIsInstance(serialized, str)


if __name__ == "__main__":
    unittest.main()
