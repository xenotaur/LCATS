# lcats/tests/utils/capture.py

from __future__ import annotations

import contextlib
import io
import os
from dataclasses import dataclass
from typing import Iterator


@dataclass
class CapturedOutput:
    """Container for captured stdout/stderr streams."""

    stdout: io.StringIO
    stderr: io.StringIO


@contextlib.contextmanager
def capture_output(*, capture_stderr: bool = True) -> Iterator[CapturedOutput]:
    """
    Capture stdout (and optionally stderr) for the duration of the context.

    Use this in tests when:
      - You want to silence noisy print output, OR
      - You want to assert on printed output.
    """
    out = io.StringIO()
    err = io.StringIO()

    with contextlib.redirect_stdout(out):
        if capture_stderr:
            with contextlib.redirect_stderr(err):
                yield CapturedOutput(stdout=out, stderr=err)
        else:
            yield CapturedOutput(stdout=out, stderr=err)


@contextlib.contextmanager
def suppress_output(*, suppress_stderr: bool = True) -> Iterator[None]:
    """
    Suppress stdout (and optionally stderr) for the duration of the context.

    Use this in tests when:
      - You do NOT care about output
      - You want zero buffering overhead
      - You want test output completely clean
    """
    with open(os.devnull, "w", encoding="utf-8") as devnull:
        with contextlib.redirect_stdout(devnull):
            if suppress_stderr:
                with contextlib.redirect_stderr(devnull):
                    yield
            else:
                yield
