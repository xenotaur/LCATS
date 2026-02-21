"""Unit tests for the utils package."""

import unittest
from unittest.mock import patch

from lcats import utils


class TestPprint(unittest.TestCase):
    """Unit tests for the pprint function."""

    @patch("builtins.print")
    def test_pprint_basic(self, mock_print):
        """Test that a simple paragraph is wrapped correctly."""
        text = "This is a simple paragraph that should wrap correctly."
        utils.pprint(text, width=20)

        # Verify that the printed output was wrapped to the specified width
        expected_calls = [
            ((),),
            (("This is a simple\nparagraph that\nshould wrap\ncorrectly.",),),
            ((),),
        ]
        mock_print.assert_has_calls(expected_calls, any_order=False)

    @patch("builtins.print")
    def test_pprint_multiple_paragraphs(self, mock_print):
        """Test that multiple paragraphs are wrapped separately."""
        text = "First paragraph.\n\nSecond paragraph."
        utils.pprint(text, width=20)

        # Verify each paragraph is wrapped separately
        expected_calls = [
            ((),),  # Extra newline before printing
            (("First paragraph.",),),
            ((),),  # Newline after first paragraph
            (("Second paragraph.",),),
            ((),),  # Newline after second paragraph
        ]
        mock_print.assert_has_calls(expected_calls, any_order=False)


class TestSm(unittest.TestCase):
    """Unit tests for the sm function."""

    def test_sm_within_limit(self):
        """Test that a short text is not shortened."""
        text = "Short text"
        limit = 20
        result = utils.sm(text, limit=limit)
        self.assertEqual(result, text)
        self.assertLess(len(result), limit)

    def test_sm_exceeds_limit(self):
        """Test that a long text is shortened."""
        text = "This is a very long text that exceeds the specified limit for display."
        limit = 20
        result = utils.sm(text, limit=limit)
        expected_result = "This is ... display."
        self.assertEqual(result, expected_result)
        self.assertEqual(len(result), limit)

    def test_sm_exactly_limit(self):
        """Test that a text exactly at the limit is not shortened."""
        text = "Exact limit text here"
        result = utils.sm(text, limit=len(text))
        self.assertEqual(result, text)

    def test_sm_with_short_limit(self):
        """The cutoff for the prefix and suffix should be one plus the spacer length."""
        text = "A somewhat long text"
        spacer = "..."
        too_short = len(spacer) + 1
        with self.assertRaises(ValueError):
            utils.sm(text, limit=too_short, spacer=spacer)
        self.assertEqual(utils.sm(text, limit=too_short + 1, spacer=spacer), "A...t")

    def test_sm_custom_spacer(self):
        """Test that a custom spacer is used for the shortened text."""
        text = "Another long text that should be shortened."
        limit = 25
        result = utils.sm(text, limit=limit, spacer="---")
        expected_result = "Another lon--- shortened."
        self.assertEqual(result, expected_result)
        self.assertEqual(len(result), limit)


class TestSml(unittest.TestCase):
    """Unit tests for the sml function."""

    def test_sml_within_limit(self):
        """When n <= limit, the full list is shown (no spacer)."""
        items = ["item1", "item2", "item3"]
        # default limit is 10, so this should show everything
        result = utils.sml(items)
        expected = "\n".join(
            [
                "[",
                "  item1,",
                "  item2,",
                "  item3",
                "] total items: 3",
            ]
        )
        self.assertEqual(result, expected)

    def test_sml_exceeds_limit_default(self):
        """When n > limit, show head, spacer (without trailing comma), and tail."""
        items = [f"item{i}" for i in range(1, 20)]  # 19 items
        # default limit=10 -> head=5, tail=4, omitted=10
        result = utils.sml(items)  # limit=10 by default
        expected = "\n".join(
            [
                "[",
                "  item1,",
                "  item2,",
                "  item3,",
                "  item4,",
                "  item5,",
                "  ...10 items omitted...",
                "  item16,",
                "  item17,",
                "  item18,",
                "  item19",
                "] total items: 19",
            ]
        )
        self.assertEqual(result, expected)

    def test_sml_exactly_limit(self):
        """Exactly at limit prints all items (no spacer)."""
        items = ["a", "b", "c", "d"]
        result = utils.sml(items, limit=4)
        expected = "\n".join(
            [
                "[",
                "  a,",
                "  b,",
                "  c,",
                "  d",
                "] total items: 4",
            ]
        )
        self.assertEqual(result, expected)

    def test_sml_raises_for_too_small_limit(self):
        """If summarizing is needed and limit < 3, raise ValueError."""
        items = [1, 2, 3, 4]
        with self.assertRaises(ValueError):
            utils.sml(items, limit=2)  # needs spacer but limit too small

    def test_sml_custom_spacer(self):
        """Custom spacer text is used (no trailing comma), and count is correct."""
        items = list(range(1, 9))  # n=8
        # limit=5 -> head=2, tail=2, omitted=4
        spacer = "~ {count} gone ~"
        result = utils.sml(items, limit=5, spacer=spacer)
        expected = "\n".join(
            [
                "[",
                "  1,",
                "  2,",
                "  ~ 4 gone ~",
                "  7,",
                "  8",
                "] total items: 8",
            ]
        )
        self.assertEqual(result, expected)


class TestExtractFencedCodeBlocks(unittest.TestCase):
    """Unit tests for the extract_fenced_code_blocks function."""

    def test_no_code_blocks(self):
        """Test behavior when there's no triple-backtick code fence."""
        text = "Here is some text with no code fences."
        blocks = utils.extract_fenced_code_blocks(text)
        self.assertEqual(
            len(blocks), 0, "Should return an empty list for no code fences."
        )

    def test_single_code_block_no_lang(self):
        """Test extraction of one code block with no specified language."""
        text = """
Here is a fence:

```
some code here print("No language specified")
```

Done.
"""
        blocks = utils.extract_fenced_code_blocks(text)
        self.assertEqual(len(blocks), 1, "Should detect exactly one code block.")
        self.assertEqual(blocks[0][0], "", "Language should be empty if not specified.")
        self.assertIn(
            "some code here",
            blocks[0][1],
            "Extracted code content should match what's inside the fence.",
        )

    def test_single_code_block_with_lang(self):
        """Test extraction of one code block with an explicit language."""
        text = """
Pre-text

```python
def hello_world():
    print("Hello from Python")
```
Post-text """
        blocks = utils.extract_fenced_code_blocks(text)
        self.assertEqual(len(blocks), 1, "Should detect exactly one code block.")
        self.assertEqual(blocks[0][0], "python", "Language should be 'python'.")
        self.assertIn(
            "hello_world",
            blocks[0][1],
            "Function name should be present in extracted code.",
        )

    def test_multiple_code_blocks(self):
        """Test extraction of multiple code blocks (some with language, some without)."""
        text = """
```json
{ "foo": "bar" }
```
Regular text

```plaintext
Here is just plain text in a block
```

And then one more:

```
System.out.println("No language specified here either");
```
"""
        blocks = utils.extract_fenced_code_blocks(text)
        self.assertEqual(len(blocks), 3, "Should extract three code blocks in total.")

        # Check 1st block (json)
        self.assertEqual(blocks[0][0], "json", "First block language should be 'json'.")
        self.assertIn('"bar"', blocks[0][1], "Should contain 'bar' in JSON code.")

        # Check 2nd block (plaintext)
        self.assertEqual(
            blocks[1][0], "plaintext", "Second block language should be 'plaintext'."
        )
        self.assertIn(
            "plain text in a block",
            blocks[1][1],
            "Should contain 'plain text in a block'.",
        )

        # Check 3rd block (no language)
        self.assertEqual(
            blocks[2][0], "", "Third block should have an empty language label."
        )
        self.assertIn(
            "System.out.println",
            blocks[2][1],
            "Should contain Java-style println statement.",
        )

    def test_empty_code_block(self):
        """Test extraction when the code fence has no content."""
        text = """
```python
```
"""
        blocks = utils.extract_fenced_code_blocks(text)
        self.assertEqual(
            len(blocks), 1, "Should still detect one code block even if empty."
        )
        self.assertEqual(blocks[0][0], "python", "Language should be 'python'.")
        self.assertEqual(blocks[0][1].strip(), "", "Code snippet should be empty.")

    def test_inline_backticks_are_ignored(self):
        """Test that single or double backticks inline do not affect extraction."""
        text = "We have inline `code` here, and ``some more`` there, but no fences."
        blocks = utils.extract_fenced_code_blocks(text)
        self.assertEqual(
            len(blocks),
            0,
            "Inline single/double backticks should not be treated as fenced blocks.",
        )

    def test_partial_fence(self):
        """Test that partial fences (missing triple backticks) do not extract anything."""
        text = """
We have something like: ``python code missing the ending backticks

just text """
        blocks = utils.extract_fenced_code_blocks(text)
        self.assertEqual(
            len(blocks),
            0,
            "Incomplete fence should not be treated as valid code blocks.",
        )


class TestMakeSerializable(unittest.TestCase):
    """Unit tests for utils.make_serializable."""

    def test_removes_default_key_without_mutating_original(self):
        """Removes the default 'response' key, leaving the original dict unchanged."""
        original = {"response": object(), "parsed_output": {"a": 1}, "status": "ok"}
        result = utils.make_serializable(original)

        # 'response' removed in the returned copy
        self.assertNotIn("response", result)
        self.assertIn("parsed_output", result)
        self.assertIn("status", result)

        # original untouched
        self.assertIn("response", original)
        self.assertIsNot(result, original)

    def test_noop_when_key_missing(self):
        """If the key is absent, the returned dict equals the input (but is a new object)."""
        original = {"a": 1, "b": 2}
        result = utils.make_serializable(original)

        self.assertEqual(result, original)
        self.assertIsNot(result, original)  # shallow copy returned

    def test_custom_key_removal(self):
        """Removes a custom nonserializable_key when provided."""
        original = {"foo": "bar", "data": 123}
        result = utils.make_serializable(original, nonserializable_key="foo")

        self.assertNotIn("foo", result)
        self.assertIn("data", result)
        # original remains intact
        self.assertIn("foo", original)

    def test_shallow_copy_only(self):
        """Function performs a shallow copy: nested objects are shared."""
        nested = {"k": [1, 2, 3]}
        original = {"response": "X", "nested": nested}
        result = utils.make_serializable(original)

        # response removed, nested preserved
        self.assertNotIn("response", result)
        self.assertIn("nested", result)

        # Same nested object (shallow copy semantics)
        self.assertIs(result["nested"], original["nested"])
        self.assertIs(result["nested"]["k"], original["nested"]["k"])


class TestExtractJson(unittest.TestCase):
    """Unit tests for utils.extract_json."""

    def test_valid_json_string_parsed_directly(self):
        """A valid JSON string is parsed without inspecting code fences."""
        result = utils.extract_json('{"key": "value", "n": 42}')
        self.assertEqual(result, {"key": "value", "n": 42})

    def test_json_in_fenced_code_block(self):
        """JSON wrapped in a ```json fence is extracted and parsed."""
        text = 'Some preamble\n```json\n{"a": 1}\n```\nTrailing text'
        result = utils.extract_json(text)
        self.assertEqual(result, {"a": 1})

    def test_no_json_raises_value_error(self):
        """Plain text with no JSON and no fences raises ValueError."""
        with self.assertRaises(ValueError):
            utils.extract_json("just some plain text, no JSON here")

    def test_multiple_blocks_allow_multiple_false_raises(self):
        """Multiple fenced blocks with allow_multiple=False raises ValueError."""
        text = "```json\n{}\n```\n```json\n{}\n```"
        with self.assertRaises(ValueError):
            utils.extract_json(text, allow_multiple=False)

    def test_multiple_blocks_allow_multiple_true_returns_first(self):
        """Multiple fenced blocks with allow_multiple=True returns the first block."""
        text = '```json\n{"first": 1}\n```\n```json\n{"second": 2}\n```'
        result = utils.extract_json(text, allow_multiple=True)
        self.assertEqual(result, {"first": 1})

    def test_wrong_language_in_fence_raises_value_error(self):
        """A fenced block with a non-json language label raises ValueError."""
        text = "```python\nprint('hello')\n```"
        with self.assertRaises(ValueError):
            utils.extract_json(text)

    def test_single_block_no_language_raises_value_error(self):
        """A fenced block with no language label raises ValueError."""
        text = "```\n{}\n```"
        with self.assertRaises(ValueError):
            utils.extract_json(text)


class TestMakeSerializableExtraction(unittest.TestCase):
    """Unit tests for utils.make_serializable_extraction."""

    def test_drops_response_key_without_mutating_original(self):
        """Drops 'response' and returns a new dict; original is unchanged."""
        original = {"response": object(), "parsed": {"x": 1}, "status": "ok"}
        result = utils.make_serializable_extraction(original)

        self.assertNotIn("response", result)
        self.assertIn("parsed", result)
        self.assertIn("response", original)
        self.assertIsNot(result, original)

    def test_no_response_key_is_a_noop(self):
        """When 'response' is absent the result equals the input (minus nothing)."""
        original = {"a": 1, "b": 2}
        result = utils.make_serializable_extraction(original)

        self.assertEqual(result, original)
        self.assertIsNot(result, original)

    def test_dict_usage_left_unchanged(self):
        """When 'usage' is already a dict it is not coerced."""
        original = {"usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}}
        result = utils.make_serializable_extraction(original)

        self.assertEqual(result["usage"], original["usage"])

    def test_usage_object_with_token_attrs_is_coerced_to_dict(self):
        """A usage object with token attributes is converted to a plain dict."""

        class FakeUsage:
            prompt_tokens = 10
            completion_tokens = 20
            total_tokens = 30

        original = {"usage": FakeUsage()}
        result = utils.make_serializable_extraction(original)

        self.assertIsInstance(result["usage"], dict)
        self.assertEqual(result["usage"]["prompt_tokens"], 10)
        self.assertEqual(result["usage"]["completion_tokens"], 20)
        self.assertEqual(result["usage"]["total_tokens"], 30)

    def test_usage_object_without_token_attrs_falls_back_to_str(self):
        """A usage object with no recognised attrs is coerced to a string."""

        class OpaqueUsage:
            def __str__(self):
                return "opaque-usage-repr"

        original = {"usage": OpaqueUsage()}
        result = utils.make_serializable_extraction(original)

        self.assertIsInstance(result["usage"], str)
        self.assertEqual(result["usage"], "opaque-usage-repr")

    def test_no_usage_key_passes_through(self):
        """When 'usage' is absent the result is unchanged (no KeyError)."""
        original = {"parsed": [1, 2, 3]}
        result = utils.make_serializable_extraction(original)
        self.assertEqual(result["parsed"], [1, 2, 3])
        self.assertNotIn("usage", result)

    def test_result_is_json_serializable(self):
        """The returned dict can be passed to json.dumps without error."""
        import json

        class FakeUsage:
            prompt_tokens = 1
            completion_tokens = 2
            total_tokens = 3

        original = {
            "response": object(),
            "usage": FakeUsage(),
            "data": {"nested": True},
        }
        result = utils.make_serializable_extraction(original)
        # Should not raise
        serialized = json.dumps(result)
        self.assertIsInstance(serialized, str)


if __name__ == "__main__":
    unittest.main()
