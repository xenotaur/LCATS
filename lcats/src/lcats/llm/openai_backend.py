"""OpenAIBackend: LLMBackend adapter for the OpenAI chat completions API."""

from __future__ import annotations

import json

from typing import Optional

from lcats.llm import backend


class OpenAIBackend:
    """LLMBackend implementation backed by the OpenAI chat completions API."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Construct an OpenAI-backed LLMBackend.

        Args:
            api_key: Optional API key. When omitted, the OpenAI SDK reads
                the OPENAI_API_KEY environment variable.
            base_url: Optional API base URL override. Local runtimes that
                expose an OpenAI-compatible chat completions endpoint
                (Ollama's `http://localhost:11434/v1`, vLLM, LM Studio, ...)
                can be driven through this same backend by pointing it here
                instead of api.openai.com - no separate backend class needed.

        Raises:
            ImportError: If the `openai` package is not installed.
        """
        import openai

        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)

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
                        "strict": tool.get("strict", False),
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
            if choice.finish_reason == "length":
                usage = response.usage
                raise backend.TruncatedResponseError(
                    f"OpenAI response for model {model!r} was truncated at "
                    f"the max_tokens limit ({max_tokens}) before the tool "
                    f"call for {tool['name']!r} finished generating; its "
                    "arguments may be incomplete or invalid JSON.",
                    stop_reason=choice.finish_reason,
                    max_tokens=max_tokens,
                    input_tokens=usage.prompt_tokens if usage else 0,
                    output_tokens=usage.completion_tokens if usage else 0,
                )
            tool_calls = choice.message.tool_calls
            if not tool_calls:
                # Include the model's own free-text response (if any) in the
                # error rather than discarding it - a forced tool_choice
                # that a backend/model silently ignores (e.g. some local
                # OpenAI-compatible runtimes) still often produces real text
                # explaining what it did instead, which is otherwise lost:
                # BackendResponse is never constructed on this path, so
                # nothing else captures choice.message.content. This
                # preview is truncated (2000 chars) for the error message
                # only - it is not a substitute for a full raw-output
                # capture, and callers should not treat it as proof the
                # full response was schema-conformant or complete (review
                # finding, PR #249).
                content_preview = (choice.message.content or "")[:2000]
                usage = response.usage
                raise backend.NoToolCallError(
                    f"API returned no tool calls for tool {tool['name']!r}; "
                    f"finish_reason: {choice.finish_reason!r}; "
                    f"content: {content_preview!r}",
                    input_tokens=usage.prompt_tokens if usage else 0,
                    output_tokens=usage.completion_tokens if usage else 0,
                    raw_content=choice.message.content or "",
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
