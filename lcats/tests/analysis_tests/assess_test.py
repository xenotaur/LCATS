"""Unit tests for lcats.analysis.corpus.assess."""

import pathlib
import unittest
from unittest.mock import patch

from lcats.analysis.corpus import assess
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
