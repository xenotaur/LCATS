"""Unit tests for lcats.analysis.corpus.assess."""

import pathlib
import unittest
from unittest.mock import patch

from lcats.analysis.corpus import assess
from lcats.llm import fake_backend

_SAMPLE_TOOL_RESULT = {
    "verdict": "include",
    "wellformed": True,
    "genre_match": "confirmed",
    "genre_confidence": 0.95,
    "specials_verdict": "none",
    "summary": "A complete story about frontier life.",
    "issues": [],
    "exclude_reason": "",
    "genre_suggestion": "",
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
        self.assertAlmostEqual(result.genre_confidence, 0.95)
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


class TestRunPreflight(unittest.TestCase):
    """Smoke test that run_preflight is still importable and callable (no backend)."""

    def test_run_preflight_exists(self):
        """run_preflight is a callable that doesn't require a backend."""
        self.assertTrue(callable(assess.run_preflight))


if __name__ == "__main__":
    unittest.main()
