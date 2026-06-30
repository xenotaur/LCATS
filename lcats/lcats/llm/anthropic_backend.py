"""AnthropicBackend: LLMBackend adapter for the Anthropic Messages API."""

from __future__ import annotations

from typing import Optional

from lcats.llm import backend


class AnthropicBackend:
    """LLMBackend implementation backed by the Anthropic Messages API.

    Uses streaming (`messages.stream`) by default to avoid gateway timeouts
    on large story inputs (typical bodies are 40-100K characters). Set
    `use_streaming=False` for a blocking call instead.
    """

    def __init__(self, api_key: Optional[str] = None, use_streaming: bool = True):
        """Construct an Anthropic-backed LLMBackend.

        Args:
            api_key: Optional API key. When omitted, the Anthropic SDK reads
                the ANTHROPIC_API_KEY environment variable.
            use_streaming: Whether to use the streaming call internally.

        Raises:
            ImportError: If the `anthropic` package is not installed.
        """
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._use_streaming = use_streaming

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
        kwargs = dict(
            model=model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if tool is not None:
            kwargs["tools"] = [tool]
            kwargs["tool_choice"] = {"type": "tool", "name": tool["name"]}

        if self._use_streaming:
            with self._client.messages.stream(**kwargs) as stream:
                message = stream.get_final_message()
        else:
            message = self._client.messages.create(**kwargs)

        if tool is not None:
            tool_block = next(
                (block for block in message.content if block.type == "tool_use"),
                None,
            )
            if tool_block is None:
                content_types = [b.type for b in message.content]
                raise ValueError(
                    f"API returned no tool_use block for tool {tool['name']!r}; "
                    f"content types: {content_types}"
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
            raw=message,
        )
