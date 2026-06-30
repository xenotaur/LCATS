"""FakeBackend: deterministic LLMBackend test double."""

from __future__ import annotations

from typing import Optional

from lcats.llm import backend


class FakeBackend:
    """Deterministic LLMBackend test double.

    Records every call's keyword arguments in `self.calls` for assertion,
    and always returns a fixed BackendResponse built from the constructor
    arguments.
    """

    def __init__(
        self,
        response_text: str = "",
        tool_result: Optional[dict] = None,
        model: str = "fake-1.0",
        input_tokens: int = 0,
        output_tokens: int = 0,
    ):
        self.response_text = response_text
        self.tool_result = tool_result
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.calls = []

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
        """Record the call and return the fixed response."""
        self.calls.append(
            dict(
                system=system,
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tool=tool,
            )
        )
        return backend.BackendResponse(
            text=self.response_text,
            tool_result=self.tool_result,
            model=self.model,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            raw=None,
        )
