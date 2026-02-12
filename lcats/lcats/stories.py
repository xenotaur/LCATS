"""Classes for working with stories and corpora of stories."""

import json
import os
import yaml


class Corpora:
    """API for accessing corpora of stories."""

    def __init__(self, corpora_root):
        self._corpora_root = corpora_root
        self._corpora = None
        self._stories = None

    @property
    def corpora_root(self):
        """The root directory containing the corpora of stories."""
        return self._corpora_root

    @property
    def corpora(self):
        """The list of story corpora."""
        if self._corpora is None:
            self._corpora = self.get_corpora()
        return self._corpora

    @property
    def stories(self):
        """The list of stories from all corpora."""
        if self._stories is None:
            self._stories = self.get_stories()
        return self._stories

    def get_stories(self):
        """Utility function to extract stories from the corpora."""
        stories = []
        for corpus in self.corpora.values():
            for story in corpus:
                stories.append(story)
        return stories

    def get_corpora(self):
        """Utility function to load all corpora from the corpora root."""
        corpora = {}
        for root, dirs, files in os.walk(self.corpora_root):
            del files  # Unused
            for dir_name in dirs:
                corpora[dir_name] = []
                dir_path = os.path.join(root, dir_name)
                for file_name in os.listdir(dir_path):
                    if file_name.endswith(".json"):
                        file_path = os.path.join(dir_path, file_name)
                        story = Story.from_json_file(file_path)
                        corpora[dir_name].append(story)
        return corpora


class Story:
    """
    A simple Python class to hold a story with fields:
    - name (str): The title or name of the story
    - body (str): The full text of the story
    - metadata (dict): A dictionary containing metadata about the story
    """

    def __init__(self, name: str, body: str, metadata: dict):
        """Creates a new Story instance with the given name, body, and metadata."""
        self.name = name
        self.body = body
        self.metadata = metadata

    #
    #  Class methods for creation from dict, JSON file, YAML file
    #

    @classmethod
    def from_dict(cls, data: dict) -> "Story":
        """
        Create a Story instance directly from a Python dictionary.
        The dict is expected to have keys: 'name', 'body', 'metadata'.
        """
        return cls(
            name=data.get("name", ""),
            body=data.get("body", ""),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json_file(cls, filepath: str) -> "Story":
        """
        Load a Story from a JSON file on disk.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_yaml_file(cls, filepath: str) -> "Story":
        """
        Load a Story from a YAML file on disk.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    #
    #  Instance methods for converting to dict, writing JSON, writing YAML
    #

    def to_dict(self) -> dict:
        """
        Convert this Story instance into a dict with 'name', 'body', 'metadata'.
        """
        return {"name": self.name, "body": self.body, "metadata": self.metadata}

    def to_json_file(self, filepath: str) -> None:
        """
        Write this Story instance out to a JSON file on disk.
        """
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def to_yaml_file(self, filepath: str) -> None:
        """
        Write this Story instance out to a YAML file on disk.
        """
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.to_dict(), f, sort_keys=False, allow_unicode=True)

    #
    # __str__ method for displaying the Story
    #
    def __str__(self) -> str:
        """
        Return a readable summary of the Story, using a hypothetical utils.sm
        function to summarize longer bodies of text.
        """
        # For demonstration, we just do a naive short excerpt if body is long.
        max_len = 100
        if len(self.body) <= max_len:
            body_text = self.body
        else:
            # In real code: body_text = utils.sm(self.body)
            body_text = self.body[:max_len] + " ... [truncated]"
            body_text.strip()

        return (
            f"Story: {self.name}\n"
            f"Author: {self.metadata.get('author', 'Unknown')}\n"
            f"Year: {self.metadata.get('year', 'N/A')}\n"
            f"Body Excerpt:\n---{body_text}\n"
            f"---"
        )
