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
def suppress_output(
    *, suppress_stderr: bool = True, suppress_file_descriptors: bool = False
) -> Iterator[None]:
    """
    Suppress stdout (and optionally stderr) for the duration of the context.

    Use this in tests when:
      - You do NOT care about output
      - You want zero buffering overhead
      - You want test output completely clean
      - You need to silence child-process output with
        ``suppress_file_descriptors=True``
    """
    with open(os.devnull, "w", encoding="utf-8") as devnull:
        saved_fds = []
        if suppress_file_descriptors:
            for fd in (1, 2) if suppress_stderr else (1,):
                saved_fds.append((fd, os.dup(fd)))
                os.dup2(devnull.fileno(), fd)
        try:
            with contextlib.redirect_stdout(devnull):
                if suppress_stderr:
                    with contextlib.redirect_stderr(devnull):
                        yield
                else:
                    yield
        finally:
            for fd, saved_fd in reversed(saved_fds):
                os.dup2(saved_fd, fd)
                os.close(saved_fd)
