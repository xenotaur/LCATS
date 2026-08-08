"""Unit tests for lcats.analysis.corpus.assess."""

import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from lcats.analysis.corpus import assess
from lcats.llm import backend as llm_backend
from lcats.llm import fake_backend

_SAMPLE_TOOL_RESULT = {
    "verdict": "include",
    "wellformed": True,
    "detected_genre": "science fiction",
    "detected_genre_confidence": 0.95,
    "genre_verdict": "confirmed",
    "specials_verdict": "none",
    "summary": "A complete story about frontier life.",
    "issues": [],
    "exclude_reason": "",
    "genre_suggestion": "",
    "secondary_genre": "",
}

_PREFLIGHT_RETURN = (
    "The Test Story",
    "Test Author",
    "http://example.com/story",
    [],
    "Full story body text here.",
)

_FILE = pathlib.Path("/fake/path/story.json")
_GENRE = "science fiction"


class _FailingBackend:
    """Stub backend that always raises from complete()."""

    def complete(
        self, *, system, messages, model, temperature=0.2, max_tokens=4096, tool=None
    ):
        raise RuntimeError("API unavailable")


class _TruncatedBackend:
    """Stub backend raising a usage-carrying backend exception (WI-ASSESS-0051:
    assess_story must forward input_tokens/output_tokens from any caught
    exception that carries them, generically - not just RuntimeError)."""

    def complete(
        self, *, system, messages, model, temperature=0.2, max_tokens=4096, tool=None
    ):
        raise llm_backend.TruncatedResponseError(
            "truncated at max_tokens",
            stop_reason="max_tokens",
            max_tokens=max_tokens,
            input_tokens=321,
            output_tokens=99,
        )


class TestAssessStorySuccess(unittest.TestCase):
    """assess_story happy-path tests using FakeBackend."""

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_returns_assessment_result(self, _mock):
        fb = fake_backend.FakeBackend(tool_result=dict(_SAMPLE_TOOL_RESULT))
        result = assess.assess_story(_FILE, _GENRE, fb)
        self.assertIsInstance(result, assess.AssessmentResult)

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_verdict_and_fields_from_tool_result(self, _mock):
        fb = fake_backend.FakeBackend(tool_result=dict(_SAMPLE_TOOL_RESULT))
        result = assess.assess_story(_FILE, _GENRE, fb)
        self.assertEqual(result.verdict, "include")
        self.assertEqual(result.title, "The Test Story")
        self.assertEqual(result.author, "Test Author")
        self.assertEqual(result.detected_genre, "science fiction")
        self.assertAlmostEqual(result.detected_genre_confidence, 0.95)
        self.assertEqual(result.genre_verdict, "confirmed")
        self.assertTrue(result.wellformed)
        self.assertEqual(result.error, "")

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_file_path_and_genre_stored(self, _mock):
        fb = fake_backend.FakeBackend(tool_result=dict(_SAMPLE_TOOL_RESULT))
        result = assess.assess_story(_FILE, _GENRE, fb)
        self.assertEqual(result.file_path, str(_FILE))
        self.assertEqual(result.target_genre, _GENRE)

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_backend_called_with_assessment_tool(self, _mock):
        """backend.complete() is called with tool=ASSESSMENT_TOOL."""
        fb = fake_backend.FakeBackend(tool_result=dict(_SAMPLE_TOOL_RESULT))
        assess.assess_story(_FILE, _GENRE, fb)
        self.assertEqual(len(fb.calls), 1)
        call = fb.calls[0]
        self.assertIsNotNone(call["tool"])
        self.assertEqual(call["tool"]["name"], "record_story_assessment")

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_model_name_forwarded_to_backend(self, _mock):
        fb = fake_backend.FakeBackend(tool_result=dict(_SAMPLE_TOOL_RESULT))
        assess.assess_story(_FILE, _GENRE, fb, model="test-model-v1")
        self.assertEqual(fb.calls[0]["model"], "test-model-v1")

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_max_tokens_default_raised_above_2048(self, _mock):
        """WI-ANNOTATE-0050: the previous hardcoded 2048 ceiling truncated
        on longer/messier real stories."""
        fb = fake_backend.FakeBackend(tool_result=dict(_SAMPLE_TOOL_RESULT))
        assess.assess_story(_FILE, _GENRE, fb)
        self.assertEqual(fb.calls[0]["max_tokens"], 4096)

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_max_tokens_is_overridable(self, _mock):
        fb = fake_backend.FakeBackend(tool_result=dict(_SAMPLE_TOOL_RESULT))
        assess.assess_story(_FILE, _GENRE, fb, max_tokens=8192)
        self.assertEqual(fb.calls[0]["max_tokens"], 8192)

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_detected_genre_confidence_clamped_above_one(self, _mock):
        """The tool schema no longer enforces min/max, so out-of-range
        values from the model must be clamped locally."""
        tool_result = dict(_SAMPLE_TOOL_RESULT, detected_genre_confidence=1.5)
        fb = fake_backend.FakeBackend(tool_result=tool_result)
        result = assess.assess_story(_FILE, _GENRE, fb)
        self.assertEqual(result.detected_genre_confidence, 1.0)

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_detected_genre_confidence_clamped_below_zero(self, _mock):
        tool_result = dict(_SAMPLE_TOOL_RESULT, detected_genre_confidence=-0.3)
        fb = fake_backend.FakeBackend(tool_result=tool_result)
        result = assess.assess_story(_FILE, _GENRE, fb)
        self.assertEqual(result.detected_genre_confidence, 0.0)

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_system_prompt_contains_genre(self, _mock):
        """The system prompt sent to the backend contains the genre name."""
        fb = fake_backend.FakeBackend(tool_result=dict(_SAMPLE_TOOL_RESULT))
        assess.assess_story(_FILE, _GENRE, fb)
        self.assertIn(_GENRE, fb.calls[0]["system"])

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_max_body_chars_truncation(self, _mock):
        """When max_body_chars is set, the user message is truncated."""
        fb = fake_backend.FakeBackend(tool_result=dict(_SAMPLE_TOOL_RESULT))
        assess.assess_story(_FILE, _GENRE, fb, max_body_chars=5)
        user_content = fb.calls[0]["messages"][0]["content"]
        self.assertIn("[... text truncated ...]", user_content)

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_secondary_genre_passed_through(self, _mock):
        tool_result = dict(_SAMPLE_TOOL_RESULT)
        tool_result["secondary_genre"] = "war"
        fb = fake_backend.FakeBackend(tool_result=tool_result)
        result = assess.assess_story(_FILE, _GENRE, fb)
        self.assertEqual(result.secondary_genre, "war")

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_secondary_genre_defaults_empty(self, _mock):
        """Exercises the a.get("secondary_genre", "") fallback, not just an
        explicit empty string already present in the tool result."""
        tool_result = dict(_SAMPLE_TOOL_RESULT)
        del tool_result["secondary_genre"]
        fb = fake_backend.FakeBackend(tool_result=tool_result)
        result = assess.assess_story(_FILE, _GENRE, fb)
        self.assertEqual(result.secondary_genre, "")

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_new_genre_accepted_in_lens_mode(self, _mock):
        """A genre added in the 4->8 expansion works as a --genre lens value."""
        tool_result = dict(_SAMPLE_TOOL_RESULT)
        tool_result["detected_genre"] = "mystery"
        fb = fake_backend.FakeBackend(tool_result=tool_result)
        result = assess.assess_story(_FILE, "mystery", fb)
        self.assertEqual(result.target_genre, "mystery")
        self.assertEqual(result.detected_genre, "mystery")
        self.assertIn("mystery", fb.calls[0]["system"])

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_issues_list_passed_through(self, _mock):
        tool_result = dict(_SAMPLE_TOOL_RESULT)
        tool_result["issues"] = [
            {
                "type": "transcriber_note",
                "severity": "low",
                "description": "Note at top",
            }
        ]
        fb = fake_backend.FakeBackend(tool_result=tool_result)
        result = assess.assess_story(_FILE, _GENRE, fb)
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0]["severity"], "low")


class TestAssessStoryErrorPaths(unittest.TestCase):
    """assess_story error-path tests."""

    @patch(
        "lcats.analysis.corpus.assess.run_preflight",
        side_effect=RuntimeError("disk read error"),
    )
    def test_preflight_error_captured(self, _mock):
        """When run_preflight raises, error field is set and no backend call made."""
        fb = fake_backend.FakeBackend(tool_result=dict(_SAMPLE_TOOL_RESULT))
        result = assess.assess_story(_FILE, _GENRE, fb)
        self.assertIn("disk read error", result.error)
        self.assertEqual(result.verdict, "review")
        self.assertEqual(len(fb.calls), 0)

    @patch(
        "lcats.analysis.corpus.assess.run_preflight",
        side_effect=RuntimeError("disk read error"),
    )
    def test_preflight_error_title_falls_back_to_directory_slug(self, _mock):
        """Regression test: the fallback title (used only when
        run_preflight raises before it can supply the real title) must be
        derived from file_path.parent.name, not file_path.stem -- under
        the bucket layout every canonical leaf filename is "story.json",
        so file_path.stem would always be the literal string "story"."""
        fb = fake_backend.FakeBackend(tool_result=dict(_SAMPLE_TOOL_RESULT))
        result = assess.assess_story(_FILE, _GENRE, fb)
        self.assertEqual(result.title, "path")

    @patch(
        "lcats.analysis.corpus.assess.run_preflight",
        side_effect=RuntimeError("disk read error"),
    )
    def test_preflight_error_title_resolves_bare_relative_path(self, _mock):
        """Regression test (Copilot review, PR #242): a bare relative
        story.json (e.g. assess run from inside the bucket directory
        itself) has a lexically empty parent name (Path(".").name == "")
        -- the fallback must resolve to recover the real bucket directory
        name instead of returning an empty title, mirroring
        output.story_dir_value's own fallback for the same edge case."""
        fb = fake_backend.FakeBackend(tool_result=dict(_SAMPLE_TOOL_RESULT))
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            bucket_dir = os.path.join(tmpdir, "my_story")
            os.makedirs(bucket_dir)
            os.chdir(bucket_dir)
            try:
                result = assess.assess_story(pathlib.Path("story.json"), _GENRE, fb)
                self.assertEqual(result.title, "my_story")
            finally:
                os.chdir(original_cwd)

    @patch(
        "lcats.analysis.corpus.assess.run_preflight",
        side_effect=RuntimeError("disk read error"),
    )
    @patch("pathlib.Path.resolve", side_effect=OSError("symlink loop"))
    def test_preflight_error_survives_resolve_failure(self, _mock_resolve, _mock):
        """Regression test: the bare-relative-path fallback's resolve()
        call runs before the try/except that exists to catch exactly
        this class of failure (unlike pure string ops, resolve() touches
        the filesystem and can raise -- e.g. a broken symlink loop). A
        resolve() failure must degrade to an empty title, not propagate
        out of assess_story and crash the whole call."""
        fb = fake_backend.FakeBackend(tool_result=dict(_SAMPLE_TOOL_RESULT))
        result = assess.assess_story(pathlib.Path("story.json"), _GENRE, fb)
        self.assertEqual(result.title, "")
        self.assertIn("disk read error", result.error)

    @patch(
        "lcats.analysis.corpus.assess.run_preflight",
        side_effect=RuntimeError("disk read error"),
    )
    @patch("pathlib.Path.resolve", side_effect=RuntimeError("symlink loop"))
    def test_preflight_error_survives_resolve_failure_runtimeerror(
        self, _mock_resolve, _mock
    ):
        """Regression test (WI-PROCESSING-0057): resolve() raises
        RuntimeError, not OSError, for a symlink loop on Python <3.13 --
        the guard must catch both, or this exact failure mode (the one
        the guard exists for) still crashes the call on every
        currently-supported Python version except the newest."""
        fb = fake_backend.FakeBackend(tool_result=dict(_SAMPLE_TOOL_RESULT))
        result = assess.assess_story(pathlib.Path("story.json"), _GENRE, fb)
        self.assertEqual(result.title, "")
        self.assertIn("disk read error", result.error)

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_backend_exception_captured(self, _mock):
        """When backend.complete() raises, error field is set."""
        result = assess.assess_story(_FILE, _GENRE, _FailingBackend())
        self.assertIn("API unavailable", result.error)
        self.assertEqual(result.verdict, "review")

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_none_tool_result_captured(self, _mock):
        """When backend returns tool_result=None, error field is set."""
        fb = fake_backend.FakeBackend(tool_result=None)
        result = assess.assess_story(_FILE, _GENRE, fb)
        self.assertIsNotNone(result.error)
        self.assertIn("no tool result", result.error.lower())
        self.assertEqual(result.verdict, "review")

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_none_tool_result_preserves_usage(self, _mock):
        """WI-ASSESS-0051: a real, billed backend_response's usage must not
        be discarded just because tool_result came back None."""
        fb = fake_backend.FakeBackend(
            tool_result=None, input_tokens=555, output_tokens=77
        )
        result = assess.assess_story(_FILE, _GENRE, fb)
        self.assertEqual(result.input_tokens, 555)
        self.assertEqual(result.output_tokens, 77)

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_backend_exception_preserves_usage(self, _mock):
        """WI-ASSESS-0051: TruncatedResponseError/NoToolCallError carry
        usage for a real, billed-but-failed call; assess_story must
        forward it generically (getattr), not discard it in the except
        branch - required so a cost-estimate sample counts failed-but-
        billed calls' real cost instead of silently recording zero."""
        result = assess.assess_story(_FILE, _GENRE, _TruncatedBackend())
        self.assertEqual(result.input_tokens, 321)
        self.assertEqual(result.output_tokens, 99)
        self.assertIn("truncated", result.error)

    @patch("lcats.analysis.corpus.assess.run_preflight", return_value=_PREFLIGHT_RETURN)
    def test_backend_exception_without_usage_defaults_zero(self, _mock):
        """An exception with no input_tokens/output_tokens attributes
        (e.g. a plain RuntimeError from a network failure before any
        response arrived) must default to zero usage, not raise."""
        result = assess.assess_story(_FILE, _GENRE, _FailingBackend())
        self.assertEqual(result.input_tokens, 0)
        self.assertEqual(result.output_tokens, 0)

    @patch(
        "lcats.analysis.corpus.assess.run_preflight",
        side_effect=FileNotFoundError("no such file"),
    )
    def test_file_not_found_captured(self, _mock):
        """FileNotFoundError from run_preflight is captured into error field."""
        fb = fake_backend.FakeBackend(tool_result=dict(_SAMPLE_TOOL_RESULT))
        result = assess.assess_story(_FILE, _GENRE, fb)
        self.assertIn("no such file", result.error)
        self.assertEqual(result.verdict, "review")


class TestValidGenres(unittest.TestCase):
    """VALID_GENRES and schema coverage for the 4->8 genre expansion."""

    def test_valid_genres_has_eight_entries(self):
        self.assertEqual(len(assess.VALID_GENRES), 8)

    def test_valid_genres_contains_new_genres(self):
        for genre in ("humor", "mystery", "fantasy", "adventure"):
            self.assertIn(genre, assess.VALID_GENRES)

    def test_valid_genres_retains_original_genres(self):
        for genre in ("science fiction", "horror", "western", "romance"):
            self.assertIn(genre, assess.VALID_GENRES)

    def test_detected_genre_enum_matches_valid_genres_plus_other(self):
        detected_genre_schema = assess.ASSESSMENT_TOOL["input_schema"]["properties"][
            "detected_genre"
        ]
        self.assertEqual(
            set(detected_genre_schema["enum"]),
            set(assess.VALID_GENRES) | {"other"},
        )

    def test_secondary_genre_field_in_schema(self):
        properties = assess.ASSESSMENT_TOOL["input_schema"]["properties"]
        self.assertIn("secondary_genre", properties)
        self.assertEqual(properties["secondary_genre"]["type"], "string")

    def test_secondary_genre_is_required(self):
        """secondary_genre must always be evaluated (empty if inapplicable),
        not silently omittable - unlike genre_suggestion, which is
        genuinely conditional on genre_verdict."""
        self.assertIn(
            "secondary_genre", assess.ASSESSMENT_TOOL["input_schema"]["required"]
        )


class TestRunPreflight(unittest.TestCase):
    """Smoke test that run_preflight is still importable and callable (no backend)."""

    def test_run_preflight_exists(self):
        """run_preflight is a callable that doesn't require a backend."""
        self.assertTrue(callable(assess.run_preflight))


if __name__ == "__main__":
    unittest.main()
