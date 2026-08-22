# lcats/src/lcats/utils/run_log.py
"""Shared crash-safe run-event log for LCATS's LLM-driven batch scripts.

Generalizes ``experiments/05_metadata_genre_prefilter/run_prefilter.py``'s
``_log_run_event()`` (PR #334) into a reusable pattern, per
``PROP-LCATS-RUN-LOG``: a durable, incremental, human-readable record of
*what happened, in order, including why a run stopped* -- distinct from
``lcats.utils.checkpoint``, which answers "is this item done and
resume-safe?", not "what happened and when?"

Two entry points:

- :func:`log_event` -- the free function, append-open-write-close per
  call, for callers with no run-scoped lifecycle to wrap (or with no
  ``CheckpointRoots`` of their own).
- :class:`RunLog` -- a context manager wrapping a whole run. Emits
  ``run_start`` on ``__enter__`` and, on ``__exit__``, either ``run_end``
  (clean exit) or a ``run_aborted_*`` event (an exception propagated).
  This closes a real gap the free function alone leaves open: a caller
  that only logs the specific exception types it anticipates produces no
  terminal event for a genuinely unanticipated exception anywhere else in
  the run (including in output-writing code that runs after the main
  loop) -- ``RunLog.__exit__`` always emits a terminal event, regardless
  of which code path raised.

Design decisions (see ``PROP-LCATS-RUN-LOG``,
``project/design/proposals/proposed/lcats-run-log/00_proposal.md``):

- **Crash-safety scope.** Both entry points write via
  open-append-write-close per call -- never a buffered or held-open file
  handle -- so a hard interruption (``kill -9``, an uncaught exception,
  an OOM kill) never loses an already-written line. This guarantees
  *process*-level crash safety only: ``close()`` flushes Python's own
  buffer into the OS, but does not ``fsync()``, so an unclean *machine*
  shutdown or power loss can still lose bytes the OS has not yet written
  to disk. Narrowing this claim (rather than the reference
  implementation's own docstring, which overstates it) is deliberate --
  see the proposal's Decision 1.
- **Protected-root re-validation, always.** ``RunLog`` derives its log
  path under a working root and always re-runs
  ``checkpoint.resolve_roots()``'s own protected-root guard against that
  root, even when the caller already supplies a
  ``checkpoint.CheckpointRoots`` -- it never trusts a caller-supplied
  ``CheckpointRoots`` as already validated. ``CheckpointRoots`` is a bare
  frozen dataclass with no marker distinguishing a genuine
  ``resolve_roots()`` result from one a caller constructed by hand
  pointed at ``data/`` or ``corpora/`` (review finding, PR #352) -- an
  "or accepts an already-validated ``CheckpointRoots``" escape hatch
  would be silently unsafe.
- **Event-name family.** ``run_start``, per-item events (caller-defined
  names), ``run_end``, and two abort variants: ``run_aborted_fatal`` (a
  caller-classified fatal/account-level exception -- reusing the
  reference implementation's own name, not a new one) and
  ``run_aborted_unexpected`` (any other exception). The caller supplies
  the classification via the ``fatal_exceptions`` constructor argument;
  an exception matching none of those types is always
  ``run_aborted_unexpected``.
"""

from __future__ import annotations

import datetime
import json
import pathlib
from typing import Any, Optional, Union

from lcats.utils import checkpoint

PathLike = Union[str, pathlib.Path]


def log_event(log_path: PathLike, event: str, **fields: Any) -> None:
    """Append one timestamped JSON line to the run log, then close.

    Opens, writes, and closes per call rather than holding a long-lived
    handle across the whole run, so a hard interruption never loses a
    buffered-but-unflushed line -- the exact failure mode this log exists
    to survive. The per-call open/close cost is negligible next to a real
    API call's own latency.
    """
    record = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "event": event,
        **fields,
    }
    with pathlib.Path(log_path).open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


class RunLog:
    """Context manager wrapping one run's worth of :func:`log_event` calls.

    ``roots`` is either a ``checkpoint.CheckpointRoots`` or a bare
    ``working_root`` path -- either way it is always re-validated via
    ``checkpoint.resolve_roots()`` (never trusted as already validated),
    and the log file is written at ``<validated working_root>/<filename>``.

    ``fatal_exceptions`` is a tuple of exception types that, if raised
    inside the ``with`` block, are logged as ``run_aborted_fatal``; any
    other propagating exception is logged as ``run_aborted_unexpected``.
    Defaults to ``()``, meaning every exception is treated as unexpected
    -- callers with a real fatal-exception class (e.g.
    ``FatalValidationError``) should pass it explicitly.

    ``**run_fields`` are attached to the ``run_start`` event (e.g.
    ``model=...``, ``story_count=...``).
    """

    def __init__(
        self,
        roots: Union["checkpoint.CheckpointRoots", PathLike],
        filename: str,
        *,
        fatal_exceptions: tuple = (),
        **run_fields: Any,
    ) -> None:
        if isinstance(roots, checkpoint.CheckpointRoots):
            working_root: PathLike = roots.working_root
            source_root: Optional[PathLike] = roots.source_root
        else:
            working_root = roots
            source_root = None
        validated = checkpoint.resolve_roots(working_root, source_root)
        self.roots = validated
        self.log_path = validated.working_root / filename
        # Callers name an output directory that may not exist yet (e.g. a
        # fresh --output path); log_event() only opens in append mode and
        # never creates directories, so this must happen before the first
        # write or that first append fails with FileNotFoundError.
        validated.working_root.mkdir(parents=True, exist_ok=True)
        self.fatal_exceptions = tuple(fatal_exceptions)
        self._run_fields = dict(run_fields)

    def event(self, event: str, **fields: Any) -> None:
        """Log one mid-run event (e.g. a per-item outcome)."""
        log_event(self.log_path, event, **fields)

    def __enter__(self) -> "RunLog":
        self.event("run_start", **self._run_fields)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            self.event("run_end")
        elif self.fatal_exceptions and issubclass(exc_type, self.fatal_exceptions):
            self.event("run_aborted_fatal", error=repr(exc))
        else:
            self.event("run_aborted_unexpected", error=repr(exc))
        return False  # never suppress the exception
