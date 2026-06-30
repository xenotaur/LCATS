"""Unit tests for lcats.llm.anthropic_backend."""

import types
import unittest

from unittest.mock import patch

from lcats.llm import anthropic_backend


def _make_message(
    text=None, tool_input=None, model="claude-opus-4-8", input_tokens=5, output_tokens=7
):
    """Build a stub object shaped like an Anthropic Messages API response."""
    content = []
    if text is not None:
        content.append(types.SimpleNamespace(type="text", text=text))
    if tool_input is not None:
        content.append(types.SimpleNamespace(type="tool_use", input=tool_input))
    usage = types.SimpleNamespace(
        input_tokens=input_tokens, output_tokens=output_tokens
    )
    return types.SimpleNamespace(content=content, usage=usage, model=model)


class _StubStream:
    """Minimal stand-in for the context manager returned by messages.stream."""

    def __init__(self, message):
        self._message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def get_final_message(self):
        return self._message


class _StubAnthropicClient:
    """Minimal stand-in for anthropic.Anthropic exposing only what is used."""

    def __init__(self, message):
        self.last_kwargs = None
        self.last_method = None
        self._message = message
        self.messages = types.SimpleNamespace(stream=self._stream, create=self._create)

    def _stream(self, **kwargs):
        self.last_kwargs = kwargs
        self.last_method = "stream"
        return _StubStream(self._message)

    def _create(self, **kwargs):
        self.last_kwargs = kwargs
        self.last_method = "create"
        return self._message


class TestAnthropicBackend(unittest.TestCase):
    """Verify AnthropicBackend translates to/from the Anthropic Messages API."""

    def test_satisfies_llm_backend_protocol(self):
        """AnthropicBackend satisfies the LLMBackend protocol."""
        from lcats.llm import backend

        with patch("anthropic.Anthropic") as mock_ctor:
            mock_ctor.return_value = _StubAnthropicClient(_make_message(text="ok"))
            self.assertIsInstance(
                anthropic_backend.AnthropicBackend(), backend.LLMBackend
            )

    def test_complete_passes_system_as_top_level_kwarg(self):
        """system is passed as a top-level kwarg, not embedded in messages."""
        stub_client = _StubAnthropicClient(_make_message(text="ok"))
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend()
            backend_under_test.complete(
                system="be helpful",
                messages=[{"role": "user", "content": "hi"}],
                model="claude-opus-4-8",
            )
        self.assertEqual(stub_client.last_kwargs["system"], "be helpful")
        self.assertEqual(
            stub_client.last_kwargs["messages"], [{"role": "user", "content": "hi"}]
        )

    def test_complete_without_tool_returns_text_block(self):
        """complete(tool=None) extracts the text block."""
        stub_client = _StubAnthropicClient(_make_message(text="hello world"))
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend()
            result = backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model="claude-opus-4-8",
            )
        self.assertEqual(result.text, "hello world")
        self.assertIsNone(result.tool_result)
        self.assertNotIn("tools", stub_client.last_kwargs)

    def test_complete_with_tool_sets_tool_choice_and_returns_input(self):
        """complete(tool=...) sets tools/tool_choice and extracts tool_use input."""
        tool_schema = {"name": "record_thing", "input_schema": {"type": "object"}}
        stub_client = _StubAnthropicClient(
            _make_message(tool_input={"verdict": "include"})
        )
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend()
            result = backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model="claude-opus-4-8",
                tool=tool_schema,
            )
        self.assertEqual(stub_client.last_kwargs["tools"], [tool_schema])
        self.assertEqual(
            stub_client.last_kwargs["tool_choice"],
            {"type": "tool", "name": "record_thing"},
        )
        self.assertEqual(result.tool_result, {"verdict": "include"})
        self.assertEqual(result.text, "")

    def test_complete_uses_streaming_by_default(self):
        """complete() uses messages.stream() by default."""
        stub_client = _StubAnthropicClient(_make_message(text="ok"))
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend()
            backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model="claude-opus-4-8",
            )
        self.assertEqual(stub_client.last_method, "stream")

    def test_complete_uses_blocking_call_when_streaming_disabled(self):
        """complete() uses messages.create() when use_streaming=False."""
        stub_client = _StubAnthropicClient(_make_message(text="ok"))
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend(use_streaming=False)
            backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model="claude-opus-4-8",
            )
        self.assertEqual(stub_client.last_method, "create")

    def test_complete_normalizes_token_usage_and_model(self):
        """input_tokens/output_tokens/model are normalized from the API response."""
        stub_client = _StubAnthropicClient(
            _make_message(
                text="ok",
                model="claude-opus-4-8",
                input_tokens=13,
                output_tokens=29,
            )
        )
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend()
            result = backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model="claude-opus-4-8",
            )
        self.assertEqual(result.model, "claude-opus-4-8")
        self.assertEqual(result.input_tokens, 13)
        self.assertEqual(result.output_tokens, 29)


if __name__ == "__main__":
    unittest.main()
