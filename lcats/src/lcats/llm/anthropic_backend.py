"""AnthropicBackend: LLMBackend adapter for the Anthropic Messages API."""

from __future__ import annotations

import re
from typing import Optional

from lcats.llm import backend


def _temperature_deprecated(model: str) -> bool:
    """Return True if this Anthropic model rejects the temperature parameter.

    claude-opus-4-7, claude-opus-4-8, claude-fable-5, and all subsequent
    Anthropic models return HTTP 400 when temperature is passed. Older models
    (claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5) still accept it.

    The rule: versioned models matching claude-<name>-<major>-<minor> suppress
    temperature when major > 4 or (major == 4 and minor >= 7). Non-versioned
    model IDs (claude-fable-5, claude-mythos-5) always suppress.
    """
    m = re.search(r"claude-[a-z]+-(\d+)-(\d+)$", model)
    if not m:
        return True
    major, minor = int(m.group(1)), int(m.group(2))
    return major > 4 or (major == 4 and minor >= 7)


class AnthropicBackend:
    """LLMBackend implementation backed by the Anthropic Messages API.

    Uses streaming (`messages.stream`) by default to avoid gateway timeouts
    on large story inputs (typical bodies are 40-100K characters). Set
    `use_streaming=False` for a blocking call instead.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        use_streaming: bool = True,
        enable_prompt_caching: bool = False,
    ):
        """Construct an Anthropic-backed LLMBackend.

        Args:
            api_key: Optional API key. When omitted, the Anthropic SDK reads
                the ANTHROPIC_API_KEY environment variable.
            use_streaming: Whether to use the streaming call internally.
            enable_prompt_caching: Opt-in only, off by default
                (WI-PILOT-0057 - evaluation, not adoption; see Decision 3 of
                PROP-LCATS-PILOT-COST-SUSTAINABILITY). When True, marks the
                tools+system prefix with `cache_control: {"type":
                "ephemeral"}` so repeated calls sharing that exact prefix
                (same tool, same system prompt - e.g. the same extractor
                type across segments/stories) can hit Anthropic's prompt
                cache. Does NOT cache `messages`/segment_text, which varies
                every call and is never a stable prefix under this
                pipeline's per-call-different-tool-schema call shape.

        Raises:
            ImportError: If the `anthropic` package is not installed.
        """
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._use_streaming = use_streaming
        self._enable_prompt_caching = enable_prompt_caching

    def complete(
        self,
        *,
        system: str,
        messages: list,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        tool: Optional[dict] = None,
    ) -> backend.BackendResponse:
        """See lcats.llm.backend.LLMBackend.complete."""
        kwargs: dict = dict(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
        if self._enable_prompt_caching:
            # Cache breakpoint on the tools+system prefix only - per
            # Decision 3's scoping, never on messages/segment_text, which
            # varies every call and can never be a stable cache prefix
            # under this pipeline's per-call-different-tool-schema shape
            # (WI-PILOT-0057). Anthropic's system param must become the
            # block-list form to carry cache_control; a bare string cannot.
            kwargs["system"] = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        else:
            kwargs["system"] = system
        if not _temperature_deprecated(model):
            kwargs["temperature"] = temperature
        if tool is not None:
            if self._enable_prompt_caching:
                tool = {**tool, "cache_control": {"type": "ephemeral"}}
            kwargs["tools"] = [tool]
            kwargs["tool_choice"] = {"type": "tool", "name": tool["name"]}

        if self._use_streaming:
            with self._client.messages.stream(**kwargs) as stream:
                message = stream.get_final_message()
        else:
            message = self._client.messages.create(**kwargs)

        if tool is not None:
            if message.stop_reason == "max_tokens":
                raise backend.TruncatedResponseError(
                    f"Anthropic response for model {model!r} was truncated "
                    f"at the max_tokens limit ({max_tokens}) before the "
                    f"tool_use block for {tool['name']!r} finished "
                    "generating; its input may be incomplete or invalid.",
                    stop_reason=message.stop_reason,
                    max_tokens=max_tokens,
                    input_tokens=message.usage.input_tokens,
                    output_tokens=message.usage.output_tokens,
                )
            tool_block = next(
                (block for block in message.content if block.type == "tool_use"),
                None,
            )
            if tool_block is None:
                content_types = [b.type for b in message.content]
                # Include the model's own free-text response (if any) in the
                # error rather than discarding it - see OpenAIBackend's
                # identical fix for the rationale (BackendResponse is never
                # constructed on this path, so nothing else captures it).
                # This preview is truncated (2000 chars) for the error
                # message only - not a substitute for a full raw-output
                # capture; callers should not treat it as proof the full
                # response was schema-conformant or complete (review
                # finding, PR #249).
                text_preview = "".join(
                    block.text for block in message.content if block.type == "text"
                )[:2000]
                raise backend.NoToolCallError(
                    f"API returned no tool_use block for tool {tool['name']!r}; "
                    f"content types: {content_types}; text: {text_preview!r}",
                    input_tokens=message.usage.input_tokens,
                    output_tokens=message.usage.output_tokens,
                )
            tool_result = tool_block.input
            text = ""
        else:
            text = next(
                (block.text for block in message.content if block.type == "text"),
                "",
            )
            tool_result = None

        usage = message.usage
        return backend.BackendResponse(
            text=text,
            tool_result=tool_result,
            model=message.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            # Optional[int] on the SDK's Usage type - None when caching
            # isn't in use or the provider omits the field; a present 0 is
            # a genuine cache miss, not "not attempted" (WI-PILOT-0057).
            cache_creation_input_tokens=getattr(
                usage, "cache_creation_input_tokens", None
            ),
            cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", None),
            raw=message,
        )
