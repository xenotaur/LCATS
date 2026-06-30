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
):
    """Build a stub object shaped like an OpenAI chat completion response."""
    if tool_call_arguments is not None:
        function = types.SimpleNamespace(arguments=tool_call_arguments)
        tool_call = types.SimpleNamespace(function=function)
        message = types.SimpleNamespace(content=None, tool_calls=[tool_call])
    else:
        message = types.SimpleNamespace(content=content, tool_calls=None)
    choice = types.SimpleNamespace(message=message)
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


if __name__ == "__main__":
    unittest.main()
