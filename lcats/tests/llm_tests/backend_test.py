"""Unit tests for lcats.llm.backend."""

import unittest

from lcats.llm import backend
from lcats.llm import fake_backend


class TestLLMBackendProtocol(unittest.TestCase):
    """Verify LLMBackend is a runtime-checkable structural protocol."""

    def test_fake_backend_satisfies_protocol(self):
        """FakeBackend satisfies LLMBackend without inheriting from it."""
        self.assertIsInstance(fake_backend.FakeBackend(), backend.LLMBackend)

    def test_object_without_complete_does_not_satisfy_protocol(self):
        """An object lacking a complete() method does not satisfy LLMBackend."""

        class NotABackend:
            pass

        self.assertNotIsInstance(NotABackend(), backend.LLMBackend)


class TestBackendResponse(unittest.TestCase):
    """Verify BackendResponse field defaults and shape."""

    def test_fields_round_trip(self):
        """All constructor fields are stored as given."""
        response = backend.BackendResponse(
            text="hello",
            tool_result=None,
            model="fake-1.0",
            input_tokens=10,
            output_tokens=20,
            raw={"id": "resp-1"},
        )
        self.assertEqual(response.text, "hello")
        self.assertIsNone(response.tool_result)
        self.assertEqual(response.model, "fake-1.0")
        self.assertEqual(response.input_tokens, 10)
        self.assertEqual(response.output_tokens, 20)
        self.assertEqual(response.raw, {"id": "resp-1"})

    def test_raw_defaults_to_none(self):
        """raw is optional and defaults to None."""
        response = backend.BackendResponse(
            text="",
            tool_result={"verdict": "include"},
            model="fake-1.0",
            input_tokens=0,
            output_tokens=0,
        )
        self.assertIsNone(response.raw)


class TestFakeBackend(unittest.TestCase):
    """Verify FakeBackend records calls and returns fixed responses."""

    def test_complete_returns_configured_text(self):
        """complete() returns the configured response_text when no tool is given."""
        backend_under_test = fake_backend.FakeBackend(response_text="hi there")
        result = backend_under_test.complete(
            system="sys",
            messages=[{"role": "user", "content": "hello"}],
            model="fake-1.0",
        )
        self.assertEqual(result.text, "hi there")
        self.assertIsNone(result.tool_result)

    def test_complete_returns_configured_tool_result(self):
        """complete() returns the configured tool_result when a tool is given."""
        tool_result = {"verdict": "include"}
        backend_under_test = fake_backend.FakeBackend(tool_result=tool_result)
        result = backend_under_test.complete(
            system="sys",
            messages=[{"role": "user", "content": "hello"}],
            model="fake-1.0",
            tool={"name": "record_thing", "input_schema": {}},
        )
        self.assertEqual(result.tool_result, tool_result)

    def test_calls_are_recorded(self):
        """Each complete() call is appended to self.calls with its kwargs."""
        backend_under_test = fake_backend.FakeBackend()
        backend_under_test.complete(
            system="sys1",
            messages=[{"role": "user", "content": "a"}],
            model="model-a",
            temperature=0.5,
            max_tokens=100,
        )
        backend_under_test.complete(
            system="sys2",
            messages=[{"role": "user", "content": "b"}],
            model="model-b",
            tool={"name": "t"},
        )
        self.assertEqual(len(backend_under_test.calls), 2)
        self.assertEqual(backend_under_test.calls[0]["system"], "sys1")
        self.assertEqual(backend_under_test.calls[0]["model"], "model-a")
        self.assertEqual(backend_under_test.calls[0]["temperature"], 0.5)
        self.assertIsNone(backend_under_test.calls[0]["tool"])
        self.assertEqual(backend_under_test.calls[1]["tool"], {"name": "t"})


if __name__ == "__main__":
    unittest.main()
