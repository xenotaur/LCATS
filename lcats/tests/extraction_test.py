import json
import unittest

from lcats import extraction
from lcats.llm import fake_backend


class TestExtraction(unittest.TestCase):

    def setUp(self):
        self.story = "Alice opened the door and stepped into a world of wonder."

        self.template = extraction.ExtractionTemplate(
            name="test-template",
            system_template="System prompt here.",
            user_template='Story to process:\n"""{story_text}"""',
        )

        self.valid_events_json = json.dumps(
            {
                "events": [
                    {"type": "scene", "text": "Alice opened the door."},
                    {"type": "none", "text": "She stepped into a world of wonder."},
                ]
            }
        )

        self.fake_backend = fake_backend.FakeBackend(
            response_text=self.valid_events_json
        )

    def test_prompt_template_renders_correctly(self):
        messages = self.template.build_prompt(self.story)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("Story to process", messages[1]["content"])
        self.assertIn(self.story, messages[1]["content"])

    def test_extract_successful(self):
        result = extraction.extract_from_story(
            story_text=self.story,
            template=self.template,
            backend=self.fake_backend,
        )
        self.assertEqual(len(result.extracted_output), 2)
        self.assertIsNone(result.parsing_error)
        self.assertIsNone(result.extraction_error)
        self.assertEqual(result.extracted_output[0]["type"], "scene")

    def test_extract_model_name_from_backend_response(self):
        """model_name in ExtractionResult comes from BackendResponse.model."""
        fb = fake_backend.FakeBackend(
            response_text=self.valid_events_json, model="test-model-v1"
        )
        result = extraction.extract_from_story(
            story_text=self.story,
            template=self.template,
            backend=fb,
        )
        self.assertEqual(result.model_name, "test-model-v1")

    def test_extract_fails_on_invalid_json(self):
        fb = fake_backend.FakeBackend(response_text="this is not JSON")
        result = extraction.extract_from_story(
            story_text=self.story,
            template=self.template,
            backend=fb,
        )
        self.assertIsNone(result.parsed_output)
        self.assertIsNotNone(result.parsing_error)
        self.assertIn("No parsed JSON", result.extraction_error)

    def test_extract_fails_on_missing_events_key(self):
        fb = fake_backend.FakeBackend(response_text='{"not_events": []}')
        result = extraction.extract_from_story(
            story_text=self.story,
            template=self.template,
            backend=fb,
        )
        self.assertIsNotNone(result.parsed_output)
        self.assertIsNone(result.extracted_output)
        self.assertIn("missing 'events' key", result.extraction_error)

    def test_summary(self):
        result = extraction.extract_from_story(
            story_text=self.story,
            template=self.template,
            backend=self.fake_backend,
        )
        summary = result.summary()
        self.assertIn("Events extracted: 2", summary)

    def test_backend_called_with_correct_system_prompt(self):
        """extract_from_story passes system template as system= arg."""
        fb = fake_backend.FakeBackend(response_text=self.valid_events_json)
        extraction.extract_from_story(
            story_text=self.story,
            template=self.template,
            backend=fb,
        )
        self.assertEqual(len(fb.calls), 1)
        self.assertEqual(fb.calls[0]["system"], "System prompt here.")

    def test_backend_called_with_story_in_messages(self):
        """extract_from_story passes story text inside messages."""
        fb = fake_backend.FakeBackend(response_text=self.valid_events_json)
        extraction.extract_from_story(
            story_text=self.story,
            template=self.template,
            backend=fb,
        )
        user_content = fb.calls[0]["messages"][0]["content"]
        self.assertIn(self.story, user_content)


if __name__ == "__main__":
    unittest.main()
