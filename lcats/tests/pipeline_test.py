"""Unit tests for the lcats.pipeline module."""

import unittest
from unittest.mock import Mock, patch

from lcats import pipeline


class TestPipeline(unittest.TestCase):
    """Unit tests for the Pipeline system."""

    def test_single_stage_success(self):
        """Test a pipeline with one successful stage."""

        def add_exclamation(text):
            return text + "!"

        stages = [
            pipeline.Stage(
                name="AddExclamation",
                processor=add_exclamation,
                inputs=["text"],
                outputs=["result"],
            )
        ]
        pipe = pipeline.Pipeline(stages, log=None)
        result = pipe(text="hello")

        self.assertTrue(result.success)
        self.assertEqual(result.values["result"], "hello!")

    def test_missing_input(self):
        """Test that missing input is caught early."""

        def dummy(x):
            return x

        stages = [pipeline.Stage("Dummy", dummy, ["missing"], ["out"])]
        pipe = pipeline.Pipeline(stages, log=None)
        result = pipe()

        self.assertFalse(result.success)
        self.assertIn("Missing inputs", result.failures[0][1])

    def test_multiple_outputs(self):
        """Test that multiple outputs are mapped correctly."""

        def split_text(text):
            return text.split()

        stages = [
            pipeline.Stage(
                name="Splitter",
                processor=split_text,
                inputs=["text"],
                outputs=["first", "second"],
            )
        ]
        pipe = pipeline.Pipeline(stages, log=None)
        result = pipe(text="hello world")

        self.assertTrue(result.success)
        self.assertEqual(result.values["first"], "hello")
        self.assertEqual(result.values["second"], "world")

    def test_unexpected_output_shape(self):
        """Test error raised if output count doesn't match stage outputs."""

        def broken_processor(text):
            return ["too", "many", "values"]

        stages = [
            pipeline.Stage(
                name="TooManyOutputs",
                processor=broken_processor,
                inputs=["text"],
                outputs=["a", "b"],
            )
        ]
        pipe = pipeline.Pipeline(stages, log=None)
        result = pipe(text="boom")

        self.assertFalse(result.success)
        self.assertIn("unexpected output format", result.failures[0][1])

    def test_retry_logic(self):
        """Test retry logic is respected."""
        attempt_counter = {"count": 0}

        def flaky_processor(x):
            attempt_counter["count"] += 1
            if attempt_counter["count"] < 3:
                raise ValueError("Try again")
            return x + 1

        stages = [
            pipeline.Stage(
                name="RetryStage",
                processor=flaky_processor,
                inputs=["x"],
                outputs=["y"],
                retries=2,
            )
        ]
        pipe = pipeline.Pipeline(stages, log=None)
        result = pipe(x=1)

        self.assertTrue(result.success)
        self.assertEqual(result.values["y"], 2)
        self.assertEqual(attempt_counter["count"], 3)

    @patch("builtins.print")
    def test_logging(self, mock_print):
        """Test that logging function is called."""

        def echo(x):
            return x

        stage = pipeline.Stage("Echo", echo, ["x"], ["y"])
        pipe = pipeline.Pipeline([stage], log=print)
        pipe(x="hello")

        mock_print.assert_any_call("Running stage: Echo")


if __name__ == "__main__":
    unittest.main()
