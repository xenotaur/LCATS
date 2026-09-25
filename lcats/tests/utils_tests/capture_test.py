"""Unit tests for the output capture utilities in lcats.utils.capture."""

import contextlib
import io
import os
import subprocess
import sys
import unittest

from lcats.utils import capture


class CaptureUtilsTests(unittest.TestCase):
    """Unit tests for the capture utilities in lcats.utils.capture."""

    def test_capture_output_captures_stdout_and_stderr(self):
        """Test that capture_output captures both stdout and stderr by default."""
        outer_out = io.StringIO()
        outer_err = io.StringIO()

        with (
            contextlib.redirect_stdout(outer_out),
            contextlib.redirect_stderr(outer_err),
        ):
            with capture.capture_output() as inner:
                print("hello stdout")
                print("hello stderr", file=sys.stderr)

            # Inner should capture both.
            self.assertIn("hello stdout", inner.stdout.getvalue())
            self.assertIn("hello stderr", inner.stderr.getvalue())

        # Outer should see nothing (no leakage).
        self.assertEqual(outer_out.getvalue(), "")
        self.assertEqual(outer_err.getvalue(), "")

    def test_capture_output_can_leave_stderr_uncaptured(self):
        """Test that capture_output can capture only stdout while allowing stderr through."""
        outer_out = io.StringIO()
        outer_err = io.StringIO()

        with (
            contextlib.redirect_stdout(outer_out),
            contextlib.redirect_stderr(outer_err),
        ):
            with capture.capture_output(capture_stderr=False) as inner:
                print("hello stdout")
                print("hello stderr", file=sys.stderr)

            # Stdout captured, stderr not captured.
            self.assertIn("hello stdout", inner.stdout.getvalue())
            self.assertEqual(inner.stderr.getvalue(), "")

        # Outer should see stderr (since we didn't capture it), but not stdout.
        self.assertEqual(outer_out.getvalue(), "")
        self.assertIn("hello stderr", outer_err.getvalue())

    def test_suppress_output_suppresses_stdout_and_stderr(self):
        """Test that suppress_output suppresses both stdout and stderr by default."""
        outer_out = io.StringIO()
        outer_err = io.StringIO()

        with (
            contextlib.redirect_stdout(outer_out),
            contextlib.redirect_stderr(outer_err),
        ):
            with capture.suppress_output():
                print("noisy stdout")
                print("noisy stderr", file=sys.stderr)

        # Nothing should leak.
        self.assertEqual(outer_out.getvalue(), "")
        self.assertEqual(outer_err.getvalue(), "")

    def test_suppress_output_can_leave_stderr_unsuppressed(self):
        """Test that suppress_output can suppress only stdout while allowing stderr through."""
        outer_out = io.StringIO()
        outer_err = io.StringIO()

        with (
            contextlib.redirect_stdout(outer_out),
            contextlib.redirect_stderr(outer_err),
        ):
            with capture.suppress_output(suppress_stderr=False):
                print("noisy stdout")
                print("noisy stderr", file=sys.stderr)

        # Stdout suppressed, stderr allowed through.
        self.assertEqual(outer_out.getvalue(), "")
        self.assertIn("noisy stderr", outer_err.getvalue())

    def test_suppress_output_can_silence_child_processes(self):
        with capture.capture_output() as outer:
            with capture.suppress_output(suppress_file_descriptors=True):
                subprocess.run(
                    [sys.executable, "-c", "print('child output')"], check=True
                )

        self.assertEqual(outer.stdout.getvalue(), "")
        self.assertEqual(outer.stderr.getvalue(), "")

    def test_suppress_output_restores_file_descriptors(self):
        read_fd, write_fd = os.pipe()
        saved_stdout = os.dup(1)
        try:
            os.dup2(write_fd, 1)
            with capture.suppress_output(suppress_file_descriptors=True):
                os.write(1, b"suppressed")
            os.write(1, b"restored")
        finally:
            os.dup2(saved_stdout, 1)
            os.close(saved_stdout)
            os.close(write_fd)

        try:
            self.assertEqual(os.read(read_fd, 1024), b"restored")
        finally:
            os.close(read_fd)
