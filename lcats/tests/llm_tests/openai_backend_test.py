"""Unit tests for lcats.llm.openai_backend."""

import json
import types
import unittest

from unittest.mock import patch

from lcats.llm import openai_backend


def _make_response(
    content=None,
    tool_call_arguments=None,
    model="gpt-4o-2024-08-06",
    prompt_tokens=5,
    completion_tokens=7,
    finish_reason="stop",
):
    """Build a stub object shaped like an OpenAI chat completion response."""
    if tool_call_arguments is not None:
        function = types.SimpleNamespace(arguments=tool_call_arguments)
        tool_call = types.SimpleNamespace(function=function)
        message = types.SimpleNamespace(content=None, tool_calls=[tool_call])
    else:
        message = types.SimpleNamespace(content=content, tool_calls=None)
    choice = types.SimpleNamespace(message=message, finish_reason=finish_reason)
    usage = types.SimpleNamespace(
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
    )
    return types.SimpleNamespace(choices=[choice], usage=usage, model=model)


class _StubOpenAIClient:
    """Minimal stand-in for openai.OpenAI exposing only what the backend uses."""

    def __init__(self, response):
        self.last_kwargs = None
        self._response = response
        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs):
        self.last_kwargs = kwargs
        return self._response


class TestOpenAIBackend(unittest.TestCase):
    """Verify OpenAIBackend translates to/from the OpenAI chat completions API."""

    def test_satisfies_llm_backend_protocol(self):
        """OpenAIBackend satisfies the LLMBackend protocol."""
        from lcats.llm import backend

        with patch("openai.OpenAI") as mock_ctor:
            mock_ctor.return_value = _StubOpenAIClient(_make_response(content="{}"))
            self.assertIsInstance(openai_backend.OpenAIBackend(), backend.LLMBackend)

    def test_constructor_forwards_base_url(self):
        """base_url is forwarded to the OpenAI SDK client, so OpenAIBackend
        can point at an OpenAI-compatible local runtime (Ollama, vLLM, LM
        Studio, ...) instead of api.openai.com."""
        with patch("openai.OpenAI") as mock_ctor:
            mock_ctor.return_value = _StubOpenAIClient(_make_response(content="{}"))
            openai_backend.OpenAIBackend(
                api_key="ollama", base_url="http://localhost:11434/v1"
            )
        mock_ctor.assert_called_once_with(
            api_key="ollama", base_url="http://localhost:11434/v1"
        )

    def test_complete_without_tool_uses_json_object_mode(self):
        """complete(tool=None) requests response_format=json_object."""
        stub_client = _StubOpenAIClient(_make_response(content='{"a": 1}'))
        with patch("openai.OpenAI", return_value=stub_client):
            backend_under_test = openai_backend.OpenAIBackend()
            result = backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-4o-2024-08-06",
            )
        self.assertEqual(
            stub_client.last_kwargs["response_format"], {"type": "json_object"}
        )
        self.assertNotIn("tools", stub_client.last_kwargs)
        self.assertEqual(result.text, '{"a": 1}')
        self.assertIsNone(result.tool_result)

    def test_complete_prepends_system_message(self):
        """complete() prepends the system prompt to the messages list."""
        stub_client = _StubOpenAIClient(_make_response(content="ok"))
        with patch("openai.OpenAI", return_value=stub_client):
            backend_under_test = openai_backend.OpenAIBackend()
            backend_under_test.complete(
                system="be helpful",
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-4o-2024-08-06",
            )
        sent_messages = stub_client.last_kwargs["messages"]
        self.assertEqual(sent_messages[0], {"role": "system", "content": "be helpful"})
        self.assertEqual(sent_messages[1], {"role": "user", "content": "hi"})

    def test_complete_with_tool_uses_function_calling(self):
        """complete(tool=...) sets tools/tool_choice and parses tool arguments."""
        tool_schema = {
            "name": "record_thing",
            "description": "Record a thing.",
            "input_schema": {"type": "object", "properties": {}},
        }
        stub_client = _StubOpenAIClient(
            _make_response(tool_call_arguments=json.dumps({"verdict": "include"}))
        )
        with patch("openai.OpenAI", return_value=stub_client):
            backend_under_test = openai_backend.OpenAIBackend()
            result = backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-4o-2024-08-06",
                tool=tool_schema,
            )
        self.assertEqual(
            stub_client.last_kwargs["tools"],
            [
                {
                    "type": "function",
                    "function": {
                        "name": "record_thing",
                        "description": "Record a thing.",
                        "parameters": {"type": "object", "properties": {}},
                        "strict": False,
                    },
                }
            ],
        )
        self.assertEqual(
            stub_client.last_kwargs["tool_choice"],
            {"type": "function", "function": {"name": "record_thing"}},
        )
        self.assertNotIn("response_format", stub_client.last_kwargs)
        self.assertEqual(result.tool_result, {"verdict": "include"})
        self.assertEqual(result.text, "")

    def test_complete_with_tool_forwards_strict_flag(self):
        """A tool schema's top-level strict:true is forwarded to OpenAI's
        function-level strict flag (WI-EVENT-0033 review finding) - without
        this, schemas hardened via lcats.llm.tool_schema.strict_tool_schema()
        were not actually enforced for OpenAI-backed extractors, silently
        defeating the hardening for any extractor defaulting to gpt-4o."""
        tool_schema = {
            "name": "record_thing",
            "description": "Record a thing.",
            "input_schema": {"type": "object", "properties": {}},
            "strict": True,
        }
        stub_client = _StubOpenAIClient(
            _make_response(tool_call_arguments=json.dumps({"verdict": "include"}))
        )
        with patch("openai.OpenAI", return_value=stub_client):
            backend_under_test = openai_backend.OpenAIBackend()
            backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-4o-2024-08-06",
                tool=tool_schema,
            )
        self.assertTrue(stub_client.last_kwargs["tools"][0]["function"]["strict"])

    def test_complete_with_tool_raises_on_length_truncation(self):
        """complete(tool=...) raises TruncatedResponseError on finish_reason='length'."""
        from lcats.llm import backend

        tool_schema = {
            "name": "record_thing",
            "description": "Record a thing.",
            "input_schema": {"type": "object", "properties": {}},
        }
        stub_client = _StubOpenAIClient(
            _make_response(
                tool_call_arguments='{"verdict": "incl',
                finish_reason="length",
            )
        )
        with patch("openai.OpenAI", return_value=stub_client):
            backend_under_test = openai_backend.OpenAIBackend()
            with self.assertRaises(backend.TruncatedResponseError) as ctx:
                backend_under_test.complete(
                    system="sys",
                    messages=[{"role": "user", "content": "hi"}],
                    model="gpt-4o-2024-08-06",
                    max_tokens=4096,
                    tool=tool_schema,
                )
        self.assertEqual(ctx.exception.stop_reason, "length")
        self.assertEqual(ctx.exception.max_tokens, 4096)
        self.assertIn(
            '"arguments": "{\\"verdict\\": \\"incl"', ctx.exception.raw_content
        )

    def test_truncation_error_preserves_billed_usage(self):
        """TruncatedResponseError carries the usage the provider already billed."""
        from lcats.llm import backend

        tool_schema = {
            "name": "record_thing",
            "description": "Record a thing.",
            "input_schema": {"type": "object", "properties": {}},
        }
        stub_client = _StubOpenAIClient(
            _make_response(
                tool_call_arguments='{"verdict": "incl',
                finish_reason="length",
                prompt_tokens=88,
                completion_tokens=4096,
            )
        )
        with patch("openai.OpenAI", return_value=stub_client):
            backend_under_test = openai_backend.OpenAIBackend()
            with self.assertRaises(backend.TruncatedResponseError) as ctx:
                backend_under_test.complete(
                    system="sys",
                    messages=[{"role": "user", "content": "hi"}],
                    model="gpt-4o-2024-08-06",
                    max_tokens=4096,
                    tool=tool_schema,
                )
        self.assertEqual(ctx.exception.input_tokens, 88)
        self.assertEqual(ctx.exception.output_tokens, 4096)

    def test_complete_with_tool_raises_no_tool_call_error_when_ignored(self):
        """complete(tool=...) raises NoToolCallError when tool_choice is
        ignored (finish_reason='stop', no tool_calls) - the same
        `tool_choice` reliability gap WI-LLM-0051 investigates."""
        from lcats.llm import backend

        tool_schema = {
            "name": "record_thing",
            "description": "Record a thing.",
            "input_schema": {"type": "object", "properties": {}},
        }
        stub_client = _StubOpenAIClient(
            _make_response(content='{"verdict": "include"}', finish_reason="stop")
        )
        with patch("openai.OpenAI", return_value=stub_client):
            backend_under_test = openai_backend.OpenAIBackend()
            with self.assertRaises(backend.NoToolCallError) as ctx:
                backend_under_test.complete(
                    system="sys",
                    messages=[{"role": "user", "content": "hi"}],
                    model="gpt-4o-2024-08-06",
                    tool=tool_schema,
                )
        self.assertEqual(ctx.exception.raw_content, '{"verdict": "include"}')

    def test_no_tool_call_error_preserves_billed_usage(self):
        """NoToolCallError carries the usage the provider already billed
        (review finding, PR #249: a forced tool_choice that a model
        ignores still generates real output tokens, which must not be
        silently reported as zero)."""
        from lcats.llm import backend

        tool_schema = {
            "name": "record_thing",
            "description": "Record a thing.",
            "input_schema": {"type": "object", "properties": {}},
        }
        stub_client = _StubOpenAIClient(
            _make_response(
                content='{"verdict": "include"}',
                finish_reason="stop",
                prompt_tokens=99,
                completion_tokens=123,
            )
        )
        with patch("openai.OpenAI", return_value=stub_client):
            backend_under_test = openai_backend.OpenAIBackend()
            with self.assertRaises(backend.NoToolCallError) as ctx:
                backend_under_test.complete(
                    system="sys",
                    messages=[{"role": "user", "content": "hi"}],
                    model="gpt-4o-2024-08-06",
                    tool=tool_schema,
                )
        self.assertEqual(ctx.exception.input_tokens, 99)
        self.assertEqual(ctx.exception.output_tokens, 123)

    def test_malformed_tool_arguments_preserve_raw_content_and_usage(self):
        tool_schema = {
            "name": "record_thing",
            "input_schema": {"type": "object", "properties": {}},
        }
        stub_client = _StubOpenAIClient(
            _make_response(
                tool_call_arguments='{"verdict": "incl',
                prompt_tokens=88,
                completion_tokens=19,
            )
        )
        with patch("openai.OpenAI", return_value=stub_client):
            backend_under_test = openai_backend.OpenAIBackend()
            with self.assertRaises(json.JSONDecodeError) as ctx:
                backend_under_test.complete(
                    system="sys",
                    messages=[{"role": "user", "content": "hi"}],
                    model="gpt-4o-2024-08-06",
                    tool=tool_schema,
                )
        self.assertEqual('{"verdict": "incl', ctx.exception.raw_content)
        self.assertEqual(88, ctx.exception.input_tokens)
        self.assertEqual(19, ctx.exception.output_tokens)

    def test_complete_without_tool_does_not_raise_on_length(self):
        """Truncation is only checked when a tool call was requested."""
        stub_client = _StubOpenAIClient(
            _make_response(content="partial tex", finish_reason="length")
        )
        with patch("openai.OpenAI", return_value=stub_client):
            backend_under_test = openai_backend.OpenAIBackend()
            result = backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-4o-2024-08-06",
            )
        self.assertEqual(result.text, "partial tex")

    def test_complete_normalizes_token_usage_and_model(self):
        """input_tokens/output_tokens/model are normalized from the API response."""
        stub_client = _StubOpenAIClient(
            _make_response(
                content="ok",
                model="gpt-4o-2024-08-06",
                prompt_tokens=11,
                completion_tokens=22,
            )
        )
        with patch("openai.OpenAI", return_value=stub_client):
            backend_under_test = openai_backend.OpenAIBackend()
            result = backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-4o-2024-08-06",
            )
        self.assertEqual(result.model, "gpt-4o-2024-08-06")
        self.assertEqual(result.input_tokens, 11)
        self.assertEqual(result.output_tokens, 22)


_TOOL_SCHEMA = {
    "name": "record_thing",
    "description": "Record a thing.",
    "input_schema": {"type": "object", "properties": {}},
    "strict": True,
}


class TestOpenAIBackendRequestRecorder(unittest.TestCase):
    """Verify the optional request recorder reports the request as built."""

    def _backend(self, response, recorder=None):
        stub_client = _StubOpenAIClient(response)
        with patch("openai.OpenAI", return_value=stub_client):
            backend_under_test = openai_backend.OpenAIBackend()
        backend_under_test.request_recorder = recorder
        return backend_under_test, stub_client

    def _complete(self, backend_under_test, **updates):
        arguments = dict(
            system="secret system prompt",
            messages=[{"role": "user", "content": "secret story text"}],
            model="gpt-4o-2024-08-06",
            max_tokens=4096,
            tool=_TOOL_SCHEMA,
        )
        arguments.update(updates)
        return backend_under_test.complete(**arguments)

    def test_the_recorder_is_off_by_default_and_satisfies_the_optional_protocol(self):
        """A new backend has no recorder, yet advertises the capability."""
        from lcats.llm import backend

        stub_client = _StubOpenAIClient(_make_response(content="{}"))
        with patch("openai.OpenAI", return_value=stub_client):
            backend_under_test = openai_backend.OpenAIBackend()
        self.assertIsNone(backend_under_test.request_recorder)
        self.assertIsInstance(backend_under_test, backend.RequestRecordingBackend)
        self.assertIsInstance(backend_under_test, backend.LLMBackend)

    def test_no_recorder_leaves_the_request_unchanged(self):
        """With no recorder the request sent to the client is the same."""
        response = _make_response(tool_call_arguments=json.dumps({"verdict": "x"}))
        plain, plain_client = self._backend(response)
        self._complete(plain)
        recorded, recorded_client = self._backend(response, recorder=lambda _r: None)
        self._complete(recorded)
        self.assertEqual(plain_client.last_kwargs, recorded_client.last_kwargs)

    def test_the_recorded_request_matches_what_the_client_received(self):
        """The record equals the sent request except the messages, which are omitted."""
        captured = []
        backend_under_test, stub_client = self._backend(
            _make_response(tool_call_arguments=json.dumps({"verdict": "x"})),
            recorder=captured.append,
        )
        self._complete(backend_under_test)
        self.assertEqual(1, len(captured))
        sent = dict(stub_client.last_kwargs)
        sent.pop("messages")
        self.assertEqual(sent, captured[0])
        function = captured[0]["tools"][0]["function"]
        self.assertTrue(function["strict"])
        self.assertEqual(_TOOL_SCHEMA["input_schema"], function["parameters"])
        self.assertEqual(
            {"type": "function", "function": {"name": "record_thing"}},
            captured[0]["tool_choice"],
        )
        self.assertNotIn("messages", captured[0])
        self.assertNotIn("secret", json.dumps(captured[0]))

    def test_the_record_is_a_copy_and_is_captured_before_the_call(self):
        """The recorder runs before the client call, on a deep copy."""
        order = []

        def recorder(request):
            order.append("recorded")
            request["tools"][0]["function"]["name"] = "mutated"

        stub_client = _StubOpenAIClient(
            _make_response(tool_call_arguments=json.dumps({"verdict": "x"}))
        )
        original_create = stub_client._create

        def create(**kwargs):
            order.append("sent")
            return original_create(**kwargs)

        stub_client.chat.completions.create = create
        with patch("openai.OpenAI", return_value=stub_client):
            backend_under_test = openai_backend.OpenAIBackend()
        backend_under_test.request_recorder = recorder
        self._complete(backend_under_test)
        self.assertEqual(["recorded", "sent"], order)
        self.assertEqual(
            "record_thing", stub_client.last_kwargs["tools"][0]["function"]["name"]
        )

    def test_a_request_is_recorded_even_when_the_call_raises(self):
        """Truncation and no-tool-call failures still leave a request record."""
        from lcats.llm import backend

        for response, error in (
            (
                _make_response(tool_call_arguments='{"v": "in', finish_reason="length"),
                backend.TruncatedResponseError,
            ),
            (_make_response(content="no tool"), backend.NoToolCallError),
        ):
            captured = []
            backend_under_test, _client = self._backend(
                response, recorder=captured.append
            )
            with self.assertRaises(error):
                self._complete(backend_under_test)
            self.assertEqual(1, len(captured))
            self.assertEqual(4096, captured[0]["max_tokens"])

    def test_a_request_without_a_tool_records_the_json_mode(self):
        """Without a tool the record shows the json_object response format."""
        captured = []
        backend_under_test, _client = self._backend(
            _make_response(content="{}"), recorder=captured.append
        )
        self._complete(backend_under_test, tool=None)
        self.assertEqual({"type": "json_object"}, captured[0]["response_format"])
        self.assertNotIn("tools", captured[0])


if __name__ == "__main__":
    unittest.main()
