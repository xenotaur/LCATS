"""LLMBackend Protocol and BackendResponse for unified LLM API access."""

from __future__ import annotations

import dataclasses

from typing import Any, Optional, Protocol, runtime_checkable


class TruncatedResponseError(RuntimeError):
    """Raised when a backend's response was cut off before completion.

    Typically caused by hitting the max_tokens ceiling mid-generation while a
    tool_use block was still being produced, leaving `tool_result` incomplete
    or holding malformed JSON (e.g. a string field cut off mid-value with no
    closing quote/bracket). Callers should retry the same request with a
    higher `max_tokens`, not attempt to parse or repair the existing result.

    input_tokens/output_tokens carry the usage the provider already reported
    for this (truncated) call, so callers with cost/usage tracking don't
    silently undercount a call that was billed despite failing - the
    response that hit max_tokens still consumed and was charged for those
    output tokens.
    """

    def __init__(
        self,
        message: str,
        *,
        stop_reason: str,
        max_tokens: int,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ):
        super().__init__(message)
        self.stop_reason = stop_reason
        self.max_tokens = max_tokens
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


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
