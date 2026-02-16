"""Simple pipeline class to manage stages of processing."""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class Stage:
    """A stage in the pipeline."""

    name: str
    processor: Callable[..., Any]
    inputs: list[str]
    outputs: list[str]
    cache: bool = True
    retries: int = 0


@dataclass
class RunResult:
    """Result of running the pipeline."""

    success: bool
    values: dict[str, Any]
    failures: list[tuple[str, str]]  # List of (stage_name, error_message)


@dataclass
class RunContext:
    """Optional context object for more advanced usage."""

    values: dict[str, Any]
    log: list[str] = field(default_factory=list)
    cache: dict[str, Any] = field(default_factory=dict)


class Pipeline:
    """A simple pipeline class to manage stages of processing."""

    def __init__(
        self, stages: list[Stage], log: Optional[Callable[[str], None]] = print
    ):
        self.stages = stages
        self.log = log

    def __call__(self, **kwargs: Any) -> RunResult:
        state = kwargs.copy()
        failures = []

        for stage in self.stages:
            if self.log:
                self.log(f"Running stage: {stage.name}")

            # Check for missing inputs
            missing = [k for k in stage.inputs if k not in state]
            if missing:
                failures.append((stage.name, f"Missing inputs: {missing}"))
                return RunResult(success=False, values=state, failures=failures)

            args = [state[k] for k in stage.inputs]

            try:
                result = self._run_with_retries(stage, args)

                # Map outputs
                if isinstance(stage.outputs, list) and len(stage.outputs) == 1:
                    state[stage.outputs[0]] = result
                elif isinstance(result, (list, tuple)) and len(result) == len(
                    stage.outputs
                ):
                    for name, val in zip(stage.outputs, result):
                        state[name] = val
                else:
                    raise ValueError(
                        f"Stage {stage.name} returned unexpected output format: {result}"
                    )

            except Exception as e:
                failures.append((stage.name, str(e)))
                return RunResult(success=False, values=state, failures=failures)

        return RunResult(success=True, values=state, failures=[])

    def _run_with_retries(self, stage: Stage, args: list[Any]) -> Any:
        last_exception = None
        for attempt in range(stage.retries + 1):
            try:
                return stage.processor(*args)
            except Exception as e:
                last_exception = e
                if self.log:
                    self.log(
                        f"Retry {attempt+1}/{stage.retries} failed for stage {stage.name}: {e}"
                    )
                time.sleep(0.5)
        raise last_exception
