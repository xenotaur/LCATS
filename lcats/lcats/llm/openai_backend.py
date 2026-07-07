"""OpenAIBackend: LLMBackend adapter for the OpenAI chat completions API."""

from __future__ import annotations

import json

from typing import Optional

from lcats.llm import backend


class OpenAIBackend:
    """LLMBackend implementation backed by the OpenAI chat completions API."""

    def __init__(self, api_key: Optional[str] = None):
        """Construct an OpenAI-backed LLMBackend.

        Args:
            api_key: Optional API key. When omitted, the OpenAI SDK reads
                the OPENAI_API_KEY environment variable.

        Raises:
            ImportError: If the `openai` package is not installed.
        """
        import openai

        self._client = openai.OpenAI(api_key=api_key)

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
        all_messages = [{"role": "system", "content": system}, *messages]
        kwargs = dict(
            model=model,
            messages=all_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if tool is not None:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool["input_schema"],
                    },
                }
            ]
            kwargs["tool_choice"] = {
                "type": "function",
                "function": {"name": tool["name"]},
            }
        else:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        if tool is not None:
            tool_calls = choice.message.tool_calls
            if not tool_calls:
                raise ValueError(
                    f"API returned no tool calls for tool {tool['name']!r}; "
                    f"finish_reason: {choice.finish_reason!r}"
                )
            raw_arguments = tool_calls[0].function.arguments
            tool_result = json.loads(raw_arguments)
            text = ""
        else:
            text = choice.message.content or ""
            tool_result = None

        usage = response.usage
        return backend.BackendResponse(
            text=text,
            tool_result=tool_result,
            model=response.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            raw=response,
        )
