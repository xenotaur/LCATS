"""Unit tests for lcats.llm.anthropic_backend."""

import json
import types
import unittest

from unittest.mock import patch

from lcats.llm import anthropic_backend


def _make_message(
    text=None,
    tool_input=None,
    model="claude-opus-4-8",
    input_tokens=5,
    output_tokens=7,
    stop_reason="end_turn",
    cache_creation_input_tokens=None,
    cache_read_input_tokens=None,
):
    """Build a stub object shaped like an Anthropic Messages API response.

    cache_creation_input_tokens/cache_read_input_tokens default to None,
    matching the real SDK's Usage type (Optional[int], absent/None when
    caching isn't in use) - always set on the stub (not omitted) so
    getattr(usage, "...", None) in production code exercises the real
    attribute-access path, not its fallback, even for the default case.
    """
    content = []
    if text is not None:
        content.append(types.SimpleNamespace(type="text", text=text))
    if tool_input is not None:
        content.append(types.SimpleNamespace(type="tool_use", input=tool_input))
    usage = types.SimpleNamespace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_input_tokens=cache_creation_input_tokens,
        cache_read_input_tokens=cache_read_input_tokens,
    )
    return types.SimpleNamespace(
        content=content, usage=usage, model=model, stop_reason=stop_reason
    )


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

    def test_complete_with_tool_raises_on_max_tokens_truncation(self):
        """complete(tool=...) raises TruncatedResponseError on stop_reason='max_tokens'."""
        from lcats.llm import backend

        tool_schema = {"name": "record_thing", "input_schema": {"type": "object"}}
        stub_client = _StubAnthropicClient(
            _make_message(tool_input={"verdict": "incl"}, stop_reason="max_tokens")
        )
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend()
            with self.assertRaises(backend.TruncatedResponseError) as ctx:
                backend_under_test.complete(
                    system="sys",
                    messages=[{"role": "user", "content": "hi"}],
                    model="claude-opus-4-8",
                    max_tokens=4096,
                    tool=tool_schema,
                )
        self.assertEqual(ctx.exception.stop_reason, "max_tokens")
        self.assertEqual(ctx.exception.max_tokens, 4096)
        self.assertIn('"type": "tool_use"', ctx.exception.raw_content)

    def test_truncation_error_preserves_billed_usage(self):
        """TruncatedResponseError carries the usage the provider already billed."""
        from lcats.llm import backend

        tool_schema = {"name": "record_thing", "input_schema": {"type": "object"}}
        stub_client = _StubAnthropicClient(
            _make_message(
                tool_input={"verdict": "incl"},
                stop_reason="max_tokens",
                input_tokens=123,
                output_tokens=4096,
            )
        )
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend()
            with self.assertRaises(backend.TruncatedResponseError) as ctx:
                backend_under_test.complete(
                    system="sys",
                    messages=[{"role": "user", "content": "hi"}],
                    model="claude-opus-4-8",
                    max_tokens=4096,
                    tool=tool_schema,
                )
        self.assertEqual(ctx.exception.input_tokens, 123)
        self.assertEqual(ctx.exception.output_tokens, 4096)

    def test_complete_with_tool_raises_no_tool_call_error_when_ignored(self):
        """complete(tool=...) raises NoToolCallError when tool_choice is
        ignored (stop_reason='end_turn', no tool_use block) - the same
        `tool_choice` reliability gap WI-LLM-0051 investigates."""
        from lcats.llm import backend

        tool_schema = {"name": "record_thing", "input_schema": {"type": "object"}}
        stub_client = _StubAnthropicClient(
            _make_message(text='{"verdict": "include"}', stop_reason="end_turn")
        )
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend()
            with self.assertRaises(backend.NoToolCallError) as ctx:
                backend_under_test.complete(
                    system="sys",
                    messages=[{"role": "user", "content": "hi"}],
                    model="claude-opus-4-8",
                    tool=tool_schema,
                )
        captured = json.loads(ctx.exception.raw_content)
        self.assertEqual('{"verdict": "include"}', captured[0]["text"])

    def test_no_tool_call_error_preserves_billed_usage(self):
        """NoToolCallError carries the usage the provider already billed
        (review finding, PR #249: a forced tool_choice that a model
        ignores still generates real output tokens, which must not be
        silently reported as zero)."""
        from lcats.llm import backend

        tool_schema = {"name": "record_thing", "input_schema": {"type": "object"}}
        stub_client = _StubAnthropicClient(
            _make_message(
                text='{"verdict": "include"}',
                stop_reason="end_turn",
                input_tokens=45,
                output_tokens=67,
            )
        )
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend()
            with self.assertRaises(backend.NoToolCallError) as ctx:
                backend_under_test.complete(
                    system="sys",
                    messages=[{"role": "user", "content": "hi"}],
                    model="claude-opus-4-8",
                    tool=tool_schema,
                )
        self.assertEqual(ctx.exception.input_tokens, 45)
        self.assertEqual(ctx.exception.output_tokens, 67)

    def test_complete_without_tool_does_not_raise_on_max_tokens(self):
        """Truncation is only checked when a tool_use block was requested."""
        stub_client = _StubAnthropicClient(
            _make_message(text="partial tex", stop_reason="max_tokens")
        )
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend()
            result = backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model="claude-opus-4-8",
            )
        self.assertEqual(result.text, "partial tex")

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

    def test_cache_fields_none_when_present_but_null_on_usage(self):
        """cache_creation_input_tokens/cache_read_input_tokens are None
        when the API response reports them as null (caching not in use
        for this call) - WI-PILOT-0057. This exercises attribute
        access, not the getattr() fallback - see
        test_cache_fields_default_none_when_the_sdk_omits_the_attribute_entirely
        for the case where the SDK's Usage object doesn't even have
        these attributes (e.g. an older installed SDK version)."""
        stub_client = _StubAnthropicClient(_make_message(text="ok"))
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend()
            result = backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model="claude-opus-4-8",
            )
        self.assertIsNone(result.cache_creation_input_tokens)
        self.assertIsNone(result.cache_read_input_tokens)

    def test_cache_fields_default_none_when_the_sdk_omits_the_attribute_entirely(self):
        """AnthropicBackend.complete() reads these fields via
        getattr(usage, "...", None) specifically so an older installed
        SDK whose Usage object doesn't define these attributes at all
        (not merely sets them to None) still returns None rather than
        raising AttributeError - review finding, PR #271: the existing
        test only covered "present but null", never true absence, so it
        could not have caught a regression to a bare
        usage.cache_creation_input_tokens attribute access."""
        usage_without_cache_fields = types.SimpleNamespace(
            input_tokens=5, output_tokens=7
        )
        message_without_cache_fields = types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text="ok")],
            usage=usage_without_cache_fields,
            model="claude-opus-4-8",
            stop_reason="end_turn",
        )
        self.assertFalse(hasattr(usage_without_cache_fields, "cache_read_input_tokens"))
        stub_client = _StubAnthropicClient(message_without_cache_fields)
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend()
            result = backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model="claude-opus-4-8",
            )
        self.assertIsNone(result.cache_creation_input_tokens)
        self.assertIsNone(result.cache_read_input_tokens)

    def test_cache_fields_normalized_from_usage_when_present(self):
        """A present cache_read_input_tokens=0 (genuine cache miss) is
        distinguishable from None (caching not in use) - WI-PILOT-0057."""
        stub_client = _StubAnthropicClient(
            _make_message(
                text="ok", cache_creation_input_tokens=150, cache_read_input_tokens=0
            )
        )
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend()
            result = backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model="claude-opus-4-8",
            )
        self.assertEqual(result.cache_creation_input_tokens, 150)
        self.assertEqual(result.cache_read_input_tokens, 0)
        self.assertIsNotNone(result.cache_read_input_tokens)

    def test_caching_disabled_by_default_sends_plain_system_string_and_no_cache_control(
        self,
    ):
        """Default behavior (enable_prompt_caching not passed) is
        unchanged: system stays a plain string, and a tool dict is sent
        without cache_control - WI-PILOT-0057 is opt-in only."""
        tool_schema = {"name": "record_thing", "input_schema": {"type": "object"}}
        stub_client = _StubAnthropicClient(
            _make_message(tool_input={"verdict": "include"})
        )
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend()
            backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model="claude-opus-4-8",
                tool=tool_schema,
            )
        self.assertEqual(stub_client.last_kwargs["system"], "sys")
        self.assertNotIn("cache_control", stub_client.last_kwargs["tools"][0])

    def test_caching_enabled_wraps_system_in_cache_control_block(self):
        """enable_prompt_caching=True converts system to the block-list
        form with a cache_control breakpoint - a bare string cannot
        carry cache_control (WI-PILOT-0057, Decision 3 scoping)."""
        stub_client = _StubAnthropicClient(_make_message(text="ok"))
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend(
                enable_prompt_caching=True
            )
            backend_under_test.complete(
                system="be helpful",
                messages=[{"role": "user", "content": "hi"}],
                model="claude-opus-4-8",
            )
        self.assertEqual(
            stub_client.last_kwargs["system"],
            [
                {
                    "type": "text",
                    "text": "be helpful",
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        )

    def test_caching_enabled_adds_cache_control_to_the_tool(self):
        """enable_prompt_caching=True attaches cache_control to the tool
        dict sent to the API - WI-PILOT-0057, Decision 3 scoping (tools+
        system only, never messages/segment_text)."""
        tool_schema = {"name": "record_thing", "input_schema": {"type": "object"}}
        stub_client = _StubAnthropicClient(
            _make_message(tool_input={"verdict": "include"})
        )
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend(
                enable_prompt_caching=True
            )
            backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model="claude-opus-4-8",
                tool=tool_schema,
            )
        sent_tool = stub_client.last_kwargs["tools"][0]
        self.assertEqual(sent_tool["cache_control"], {"type": "ephemeral"})
        self.assertEqual(sent_tool["name"], "record_thing")

    def test_caching_enabled_does_not_mutate_the_caller_s_tool_schema_dict(self):
        """The original tool_schema dict a caller passes in (often a
        shared module-level constant, e.g. ENTITY_TOOL_SCHEMA) must not
        be mutated in place - caching would otherwise silently leak into
        every other call site sharing that same dict, including callers
        with enable_prompt_caching=False (WI-PILOT-0057 review finding)."""
        tool_schema = {"name": "record_thing", "input_schema": {"type": "object"}}
        stub_client = _StubAnthropicClient(
            _make_message(tool_input={"verdict": "include"})
        )
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend(
                enable_prompt_caching=True
            )
            backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model="claude-opus-4-8",
                tool=tool_schema,
            )
        self.assertNotIn("cache_control", tool_schema)

    def test_caching_enabled_does_not_add_cache_control_when_no_tool_given(self):
        """enable_prompt_caching=True with no tool= (free-text call) must
        not error trying to attach cache_control to a nonexistent tool -
        only the system prefix is cached in that case."""
        stub_client = _StubAnthropicClient(_make_message(text="ok"))
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend(
                enable_prompt_caching=True
            )
            backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model="claude-opus-4-8",
            )
        self.assertNotIn("tools", stub_client.last_kwargs)


class TestTemperatureDeprecated(unittest.TestCase):
    """Verify _temperature_deprecated() identifies models that reject temperature."""

    def _check(self, model: str, expected: bool) -> None:
        self.assertEqual(
            anthropic_backend._temperature_deprecated(model),
            expected,
            msg=f"_temperature_deprecated({model!r}) should be {expected}",
        )

    def test_opus_4_8_deprecated(self):
        self._check("claude-opus-4-8", True)

    def test_opus_4_7_deprecated(self):
        self._check("claude-opus-4-7", True)

    def test_fable_5_deprecated(self):
        self._check("claude-fable-5", True)

    def test_mythos_5_deprecated(self):
        self._check("claude-mythos-5", True)

    def test_opus_4_6_not_deprecated(self):
        self._check("claude-opus-4-6", False)

    def test_sonnet_4_6_not_deprecated(self):
        self._check("claude-sonnet-4-6", False)

    def test_haiku_4_5_not_deprecated(self):
        self._check("claude-haiku-4-5", False)

    def test_future_major_5_versioned_deprecated(self):
        self._check("claude-opus-5-0", True)


class TestTemperatureOmittedInRequest(unittest.TestCase):
    """Verify temperature is included/omitted in the API call kwargs."""

    def _kwargs_for(self, model: str) -> dict:
        stub_client = _StubAnthropicClient(_make_message(text="ok", model=model))
        with patch("anthropic.Anthropic", return_value=stub_client):
            backend_under_test = anthropic_backend.AnthropicBackend()
            backend_under_test.complete(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                model=model,
                temperature=0.5,
            )
        return stub_client.last_kwargs

    def test_temperature_omitted_for_opus_4_8(self):
        self.assertNotIn("temperature", self._kwargs_for("claude-opus-4-8"))

    def test_temperature_omitted_for_opus_4_7(self):
        self.assertNotIn("temperature", self._kwargs_for("claude-opus-4-7"))

    def test_temperature_omitted_for_fable_5(self):
        self.assertNotIn("temperature", self._kwargs_for("claude-fable-5"))

    def test_temperature_included_for_opus_4_6(self):
        self.assertIn("temperature", self._kwargs_for("claude-opus-4-6"))
        self.assertAlmostEqual(self._kwargs_for("claude-opus-4-6")["temperature"], 0.5)

    def test_temperature_included_for_sonnet_4_6(self):
        self.assertIn("temperature", self._kwargs_for("claude-sonnet-4-6"))


if __name__ == "__main__":
    unittest.main()
