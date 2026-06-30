"""LLMBackend Protocol and BackendResponse for unified LLM API access."""

from __future__ import annotations

import dataclasses

from typing import Any, Optional, Protocol, runtime_checkable


@dataclasses.dataclass
class BackendResponse:
    """Normalized result of an LLMBackend.complete() call.

    Attributes:
        text: Free-text model output. Empty string when `tool` was provided.
        tool_result: Structured tool-use output. None when no tool was used.
        model: Exact model string echoed back by the provider's API response.
        input_tokens: Number of input/prompt tokens reported by the API.
        output_tokens: Number of output/completion tokens reported by the API.
        raw: The raw, provider-specific SDK response object, for debugging.
    """

    text: str
    tool_result: Optional[dict]
    model: str
    input_tokens: int
    output_tokens: int
    raw: Any = dataclasses.field(repr=False, default=None)


@runtime_checkable
class LLMBackend(Protocol):
    """Structural protocol for a single-call LLM backend.

    Implementations adapt a specific provider SDK (OpenAI, Anthropic, ...)
    to this normalized call shape so callers can switch providers by
    swapping the backend instance, without touching prompt or call-site code.
    """

    def complete(
        self,
        *,
        system: str,
        messages: list,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        tool: Optional[dict] = None,
    ) -> BackendResponse:
        """Run one completion call and return a normalized response.

        Args:
            system: System prompt text.
            messages: Chat messages excluding the system prompt, e.g.
                [{"role": "user", "content": "..."}].
            model: Provider-specific model identifier.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            tool: Optional single tool schema. When provided, the backend
                forces the model to call this tool and returns its
                arguments in `BackendResponse.tool_result`. When None, the
                backend requests free-form JSON-friendly text output in
                `BackendResponse.text`.

        Returns:
            A BackendResponse with normalized fields.
        """
        ...
