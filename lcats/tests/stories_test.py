"""Unit tests for lcats.stories module."""

import json
import os
import tempfile
import unittest

from lcats import stories


class TestStoryInit(unittest.TestCase):
    """Tests for Story.__init__."""

    def test_fields_stored(self):
        """Constructor stores name, body, and metadata."""
        story = stories.Story("Title", "Body text", {"author": "Alice"})
        self.assertEqual(story.name, "Title")
        self.assertEqual(story.body, "Body text")
        self.assertEqual(story.metadata, {"author": "Alice"})

    def test_empty_fields(self):
        """Constructor accepts empty strings and empty dict."""
        story = stories.Story("", "", {})
        self.assertEqual(story.name, "")
        self.assertEqual(story.body, "")
        self.assertEqual(story.metadata, {})


class TestStoryFromDict(unittest.TestCase):
    """Tests for Story.from_dict."""

    def test_full_dict(self):
        """from_dict populates all fields."""
        data = {
            "name": "MyStory",
            "body": "Once upon a time.",
            "metadata": {"year": 1900},
        }
        story = stories.Story.from_dict(data)
        self.assertEqual(story.name, "MyStory")
        self.assertEqual(story.body, "Once upon a time.")
        self.assertEqual(story.metadata, {"year": 1900})

    def test_missing_keys_use_defaults(self):
        """from_dict uses empty defaults for missing keys."""
        story = stories.Story.from_dict({})
        self.assertEqual(story.name, "")
        self.assertEqual(story.body, "")
        self.assertEqual(story.metadata, {})

    def test_partial_dict(self):
        """from_dict handles partial data."""
        story = stories.Story.from_dict({"name": "Partial"})
        self.assertEqual(story.name, "Partial")
        self.assertEqual(story.body, "")
        self.assertEqual(story.metadata, {})


class TestStoryFromJsonFile(unittest.TestCase):
    """Tests for Story.from_json_file."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp)

    def test_load_from_json(self):
        """from_json_file loads a Story from a JSON file."""
        data = {
            "name": "JSON Story",
            "body": "A JSON body.",
            "metadata": {"author": "Bob"},
        }
        path = os.path.join(self.tmp, "story.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        story = stories.Story.from_json_file(path)
        self.assertEqual(story.name, "JSON Story")
        self.assertEqual(story.body, "A JSON body.")
        self.assertEqual(story.metadata, {"author": "Bob"})

    def test_load_json_with_unicode(self):
        """from_json_file handles unicode content."""
        data = {"name": "Ünïcödé", "body": "日本語テスト", "metadata": {}}
        path = os.path.join(self.tmp, "unicode.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        story = stories.Story.from_json_file(path)
        self.assertEqual(story.name, "Ünïcödé")
        self.assertEqual(story.body, "日本語テスト")


class TestStoryFromYamlFile(unittest.TestCase):
    """Tests for Story.from_yaml_file."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp)

    def test_load_from_yaml(self):
        """from_yaml_file loads a Story from a YAML file."""
        path = os.path.join(self.tmp, "story.yaml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                "name: YAML Story\nbody: A YAML body.\nmetadata:\n  author: Carol\n"
            )
        story = stories.Story.from_yaml_file(path)
        self.assertEqual(story.name, "YAML Story")
        self.assertEqual(story.body, "A YAML body.")
        self.assertEqual(story.metadata, {"author": "Carol"})


class TestStoryToDict(unittest.TestCase):
    """Tests for Story.to_dict."""

    def test_roundtrip_dict(self):
        """to_dict produces the same data used to create the Story."""
        data = {"name": "Round", "body": "Trip.", "metadata": {"x": 1}}
        story = stories.Story.from_dict(data)
        self.assertEqual(story.to_dict(), data)

    def test_to_dict_is_json_serializable(self):
        """to_dict result can be serialized with json.dumps."""
        story = stories.Story("Serializable", "Body.", {"key": "val"})
        result = story.to_dict()
        dumped = json.dumps(result)
        self.assertIsInstance(dumped, str)


class TestStoryToJsonFile(unittest.TestCase):
    """Tests for Story.to_json_file."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp)

    def test_write_and_reload(self):
        """to_json_file writes valid JSON that can be reloaded."""
        story = stories.Story("SavedJSON", "JSON body text.", {"year": 2024})
        path = os.path.join(self.tmp, "out.json")
        story.to_json_file(path)
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["name"], "SavedJSON")
        self.assertEqual(data["body"], "JSON body text.")
        self.assertEqual(data["metadata"], {"year": 2024})

    def test_json_roundtrip_via_classmethod(self):
        """Writing then loading a Story returns equivalent data."""
        original = stories.Story("RT", "Roundtrip body.", {"a": "b"})
        path = os.path.join(self.tmp, "rt.json")
        original.to_json_file(path)
        reloaded = stories.Story.from_json_file(path)
        self.assertEqual(reloaded.name, original.name)
        self.assertEqual(reloaded.body, original.body)
        self.assertEqual(reloaded.metadata, original.metadata)


class TestStoryToYamlFile(unittest.TestCase):
    """Tests for Story.to_yaml_file."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp)

    def test_write_and_reload(self):
        """to_yaml_file writes YAML that can be reloaded."""
        story = stories.Story("SavedYAML", "YAML body text.", {"author": "Dave"})
        path = os.path.join(self.tmp, "out.yaml")
        story.to_yaml_file(path)
        self.assertTrue(os.path.isfile(path))
        reloaded = stories.Story.from_yaml_file(path)
        self.assertEqual(reloaded.name, "SavedYAML")
        self.assertEqual(reloaded.body, "YAML body text.")
        self.assertEqual(reloaded.metadata, {"author": "Dave"})


class TestStoryStr(unittest.TestCase):
    """Tests for Story.__str__."""

    def test_short_body_in_output(self):
        """Short bodies appear verbatim in __str__ output."""
        story = stories.Story("Short", "Brief body.", {"author": "Eve", "year": 1999})
        output = str(story)
        self.assertIn("Short", output)
        self.assertIn("Brief body.", output)
        self.assertIn("Eve", output)
        self.assertIn("1999", output)

    def test_long_body_truncated(self):
        """Bodies longer than 100 chars are truncated in __str__."""
        long_body = "x" * 200
        story = stories.Story("LongStory", long_body, {})
        output = str(story)
        self.assertIn("[truncated]", output)
        self.assertNotIn(long_body, output)

    def test_missing_author_and_year(self):
        """__str__ falls back to 'Unknown' and 'N/A' when metadata is absent."""
        story = stories.Story("NoMeta", "Body.", {})
        output = str(story)
        self.assertIn("Unknown", output)
        self.assertIn("N/A", output)

    def test_body_exactly_at_max_len(self):
        """Body of exactly 100 chars is not truncated."""
        exact_body = "a" * 100
        story = stories.Story("Exact", exact_body, {})
        output = str(story)
        self.assertNotIn("[truncated]", output)
        self.assertIn(exact_body, output)


class TestCorpora(unittest.TestCase):
    """Tests for the Corpora class."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp)

    def _make_corpus_dir(self, corpus_name, story_dicts):
        """Helper: create a corpus subdirectory with JSON story files."""
        corpus_dir = os.path.join(self.tmp, corpus_name)
        os.makedirs(corpus_dir)
        for i, data in enumerate(story_dicts):
            path = os.path.join(corpus_dir, f"story_{i}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        return corpus_dir

    def test_corpora_root_property(self):
        """corpora_root returns the path passed to __init__."""
        corpora = stories.Corpora(self.tmp)
        self.assertEqual(corpora.corpora_root, self.tmp)

    def test_empty_corpora_root(self):
        """get_corpora on an empty root returns an empty dict."""
        corpora = stories.Corpora(self.tmp)
        result = corpora.get_corpora()
        self.assertEqual(result, {})

    def test_get_corpora_loads_stories(self):
        """get_corpora finds JSON files within subdirectories."""
        story_data = {"name": "S1", "body": "Body1", "metadata": {}}
        self._make_corpus_dir("fantasy", [story_data])
        corpora = stories.Corpora(self.tmp)
        result = corpora.get_corpora()
        self.assertIn("fantasy", result)
        self.assertEqual(len(result["fantasy"]), 1)
        self.assertIsInstance(result["fantasy"][0], stories.Story)
        self.assertEqual(result["fantasy"][0].name, "S1")

    def test_get_corpora_multiple_corpora(self):
        """get_corpora handles multiple subdirectories."""
        self._make_corpus_dir("scifi", [{"name": "S2", "body": "B2", "metadata": {}}])
        self._make_corpus_dir(
            "horror",
            [
                {"name": "S3", "body": "B3", "metadata": {}},
                {"name": "S4", "body": "B4", "metadata": {}},
            ],
        )
        corpora = stories.Corpora(self.tmp)
        result = corpora.get_corpora()
        self.assertIn("scifi", result)
        self.assertIn("horror", result)
        self.assertEqual(len(result["scifi"]), 1)
        self.assertEqual(len(result["horror"]), 2)

    def test_get_corpora_ignores_non_json(self):
        """get_corpora ignores files that are not .json."""
        corpus_dir = os.path.join(self.tmp, "misc")
        os.makedirs(corpus_dir)
        with open(os.path.join(corpus_dir, "readme.txt"), "w") as f:
            f.write("not a story")
        with open(os.path.join(corpus_dir, "story.yaml"), "w") as f:
            f.write("name: yaml_story\n")
        corpora = stories.Corpora(self.tmp)
        result = corpora.get_corpora()
        self.assertIn("misc", result)
        self.assertEqual(result["misc"], [])

    def test_corpora_property_lazy_loads(self):
        """corpora property is loaded once and cached."""
        self._make_corpus_dir("mystery", [{"name": "M1", "body": "B", "metadata": {}}])
        corpora = stories.Corpora(self.tmp)
        self.assertIsNone(corpora._corpora)
        first = corpora.corpora
        self.assertIsNotNone(corpora._corpora)
        second = corpora.corpora
        self.assertIs(first, second)

    def test_stories_property_lazy_loads(self):
        """stories property is loaded once and cached."""
        self._make_corpus_dir("drama", [{"name": "D1", "body": "B", "metadata": {}}])
        corpora = stories.Corpora(self.tmp)
        self.assertIsNone(corpora._stories)
        first = corpora.stories
        self.assertIsNotNone(corpora._stories)
        second = corpora.stories
        self.assertIs(first, second)

    def test_get_stories_returns_flat_list(self):
        """get_stories returns a flat list of all Story objects."""
        self._make_corpus_dir(
            "corpA",
            [
                {"name": "A1", "body": "BA1", "metadata": {}},
                {"name": "A2", "body": "BA2", "metadata": {}},
            ],
        )
        self._make_corpus_dir(
            "corpB",
            [
                {"name": "B1", "body": "BB1", "metadata": {}},
            ],
        )
        corpora = stories.Corpora(self.tmp)
        result = corpora.get_stories()
        self.assertEqual(len(result), 3)
        names = {s.name for s in result}
        self.assertEqual(names, {"A1", "A2", "B1"})


if __name__ == "__main__":
    unittest.main()
