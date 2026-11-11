"""Unit tests for LCATS using its actual package imports.

Run from the LCATS repository root:
    python -m unittest discover -s tests -p '*_test.py' -v
"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json
import sqlite3

from lcats.gatherers import registry


class CaptureOutput:
    """Capture console output without relying on another test framework."""

    def __init__(self):
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()

    def readouterr(self):
        result = SimpleNamespace(
            out=self.stdout.getvalue(),
            err=self.stderr.getvalue(),
        )

        self.stdout.seek(0)
        self.stdout.truncate(0)
        self.stderr.seek(0)
        self.stderr.truncate(0)

        return result


class LCATSTestCase(unittest.TestCase):
    """Provide the same temporary-file and mock cleanup as existing LCATS tests."""

    def setUp(self):
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)

        self.tmp_path = Path(self._temporary_directory.name)
        self.capsys = CaptureOutput()

        self._stdout_capture = contextlib.redirect_stdout(self.capsys.stdout)
        self._stderr_capture = contextlib.redirect_stderr(self.capsys.stderr)

        self._stdout_capture.__enter__()
        self.addCleanup(self._stdout_capture.__exit__, None, None, None)

        self._stderr_capture.__enter__()
        self.addCleanup(self._stderr_capture.__exit__, None, None, None)

    def patch_attribute(self, target, name, replacement):
        """Patch a real module or object, restoring it after this test."""
        patcher = patch.object(target, name, replacement)
        patcher.start()
        self.addCleanup(patcher.stop)

        return replacement


def database_fixture(tmp_path):
    return tmp_path / "stories.sqlite3"


def seeded_registry_fixture(registry_module, database):
    registry_module.add_story(
        "foundation.json",
        "Asimov",
        source="Gutenberg",
        registry=database,
    )

    registry_module.add_story(
        "nightfall.json",
        ["Asimov", "Silverberg"],
        source="Standard EBooks",
        registry=database,
    )

    return database


class TestRegistry(LCATSTestCase):
    def test_normalize_filename(self):
        for _case_index, (raw, expected) in enumerate(
            [
                ("Story.JSON", "story.json"),
                ("  STORY.json  ", "story.json"),
                ("/books/stories/Story.JSON", "story.json"),
                ("/books/stories/  Story.JSON  ", "story.json"),
                ("cafÉ.json", "café.json"),
                ("", ""),
            ]
        ):
            with self.subTest(raw=raw, expected=expected):
                registry_module = registry
                self.assertEqual(registry_module._normalize_filename(raw), expected)

    def test_normalize_filename_accepts_path_objects(self):
        registry_module = registry
        value = Path("somewhere") / "Example.JSON"
        result = registry_module._normalize_filename(value)

        self.assertEqual(result, "example.json")

    def test_normalize_authors(self):
        for _case_index, (authors, expected) in enumerate(
            [
                ("Asimov", ["asimov"]),
                (["Asimov"], ["asimov"]),
                (["Silverberg", "Asimov"], ["asimov", "silverberg"]),
                ([" Asimov ", "ASIMOV"], ["asimov"]),
                (["  ", "Asimov", ""], ["asimov"]),
                ([], []),
                (["Écrivain"], ["écrivain"]),
            ]
        ):
            with self.subTest(authors=authors, expected=expected):
                registry_module = registry
                result = registry_module._normalize_authors(authors)
                self.assertEqual(json.loads(result), expected)

    def test_normalize_authors_emits_deterministic_json(self):
        registry_module = registry
        first = registry_module._normalize_authors(["Smith", "Jones", "SMITH"])
        second = registry_module._normalize_authors(["jones", "smith"])

        self.assertEqual(first, second)

    def test_connection_creates_database_and_table(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)

        self.assertFalse(database.exists())
        with registry_module._connect(database) as connection:
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()

        self.assertTrue(database.exists())

        self.assertIn(("stories",), tables)

    def test_reopening_database_preserves_existing_stories(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        registry_module.add_story("sample.json", "Wells", registry=database)
        with registry_module._connect(database) as connection:
            rows = connection.execute(
                "SELECT filename, authors FROM stories"
            ).fetchall()

        self.assertEqual(rows, [("sample.json", '["wells"]')])

    def test_reopening_connection_does_not_erase_existing_rows(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        registry_module.add_story("sample.json", "Wells", registry=database)
        with registry_module._connect(database) as connection:
            connection.execute("SELECT COUNT(*) FROM stories").fetchone()

        self.assertEqual(registry_module.registry_count(database), 1)

    def test_database_enforces_composite_primary_key(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        registry_module.add_story("sample.json", "Wells", registry=database)
        with registry_module._connect(database) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO stories (filename, authors) VALUES (?, ?)",
                    ("sample.json", '["wells"]'),
                )

    def test_check_story_returns_false_for_new_story(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        result = registry_module.check_story("unknown.json", "Wells", registry=database)

        self.assertIs(result, False)

        self.assertEqual(registry_module.registry_count(database), 0)

    def test_check_story_does_not_insert_missing_story(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        for _ in range(3):
            self.assertIs(
                registry_module.check_story("unknown.json", "Wells", registry=database),
                False,
            )

        self.assertEqual(registry_module.registry_count(database), 0)

    def test_check_story_finds_existing_entry(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        seeded_registry = seeded_registry_fixture(registry_module, database)

        self.assertIs(
            registry_module.check_story(
                "foundation.json", "Asimov", registry=seeded_registry
            ),
            True,
        )

    def test_check_story_normalizes_filename_and_author(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        seeded_registry = seeded_registry_fixture(registry_module, database)
        result = registry_module.check_story(
            "/old/files/FOUNDATION.JSON", [" ASIMOV "], registry=seeded_registry
        )

        self.assertIs(result, True)

    def test_check_story_ignores_author_order(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        seeded_registry = seeded_registry_fixture(registry_module, database)
        result = registry_module.check_story(
            "nightfall.json", ["SILVERBERG", "asimov"], registry=seeded_registry
        )

        self.assertIs(result, True)

    def test_check_story_requires_matching_authors(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        seeded_registry = seeded_registry_fixture(registry_module, database)

        self.assertIs(
            registry_module.check_story(
                "foundation.json", "Wells", registry=seeded_registry
            ),
            False,
        )

    def test_check_story_requires_matching_filename(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        seeded_registry = seeded_registry_fixture(registry_module, database)

        self.assertIs(
            registry_module.check_story(
                "different.json", "Asimov", registry=seeded_registry
            ),
            False,
        )

    def test_check_story_does_not_change_existing_record(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        seeded_registry = seeded_registry_fixture(registry_module, database)
        with sqlite3.connect(seeded_registry) as connection:
            before = connection.execute(
                "SELECT filename, authors, source, date_added FROM stories ORDER BY filename"
            ).fetchall()
        registry_module.check_story(
            "foundation.json", "Asimov", registry=seeded_registry
        )
        with sqlite3.connect(seeded_registry) as connection:
            after = connection.execute(
                "SELECT filename, authors, source, date_added FROM stories ORDER BY filename"
            ).fetchall()

        self.assertEqual(after, before)

    def test_add_story_returns_true_for_new_entry(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        result = registry_module.add_story("sample.json", "Wells", registry=database)

        self.assertIs(result, True)

        self.assertEqual(registry_module.registry_count(database), 1)

    def test_add_story_returns_false_for_existing_entry(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        registry_module.add_story("sample.json", "Wells", registry=database)
        result = registry_module.add_story("SAMPLE.JSON", ["wells"], registry=database)

        self.assertIs(result, False)

        self.assertEqual(registry_module.registry_count(database), 1)

    def test_add_story_allows_same_filename_with_different_authors(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        registry_module.add_story("same.json", "Wells", registry=database)
        registry_module.add_story("same.json", "Asimov", registry=database)

        self.assertEqual(registry_module.registry_count(database), 2)

    def test_add_story_allows_same_author_with_different_filenames(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        registry_module.add_story("first.json", "Wells", registry=database)
        registry_module.add_story("second.json", "Wells", registry=database)

        self.assertEqual(registry_module.registry_count(database), 2)

    def test_add_story_ignores_repeated_authors(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        registry_module.add_story(
            "sample.json", ["Asimov", "Asimov"], registry=database
        )
        result = registry_module.add_story("sample.json", "asimov", registry=database)

        self.assertIs(result, False)

    def test_add_story_stores_source_and_timestamp(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        registry_module.add_story(
            "sample.json", "Wells", source="Project Gutenberg", registry=database
        )
        with sqlite3.connect(database) as connection:
            source, date_added = connection.execute(
                "SELECT source, date_added FROM stories"
            ).fetchone()

        self.assertEqual(source, "Project Gutenberg")

        self.assertIsNot(date_added, None)

        self.assertTrue(date_added.startswith("20"))

    def test_add_story_keeps_original_source_on_duplicate(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        registry_module.add_story(
            "sample.json", "Wells", source="First Source", registry=database
        )
        registry_module.add_story(
            "sample.json", "Wells", source="Second Source", registry=database
        )
        with sqlite3.connect(database) as connection:
            source = connection.execute("SELECT source FROM stories").fetchone()[0]

        self.assertEqual(source, "First Source")

    def test_check_and_add_accepts_new_stories(self):
        for _case_index, mode in enumerate(["ignore", "discard", "warn"]):
            with self.subTest(mode=mode):
                tmp_path = self.tmp_path / str(_case_index)
                tmp_path.mkdir(parents=True, exist_ok=True)
                registry_module = registry
                database = database_fixture(tmp_path)
                capsys = self.capsys
                result = registry_module.check_and_add(
                    "sample.json", "Wells", mode=mode, registry=database
                )
                self.assertIs(result, True)
                self.assertEqual(registry_module.registry_count(database), 1)
                self.assertEqual(capsys.readouterr().out, "")

    def test_check_and_add_uses_duplicate_policy(self):
        for _case_index, (mode, expected) in enumerate(
            [("ignore", True), ("discard", False), ("warn", True)]
        ):
            with self.subTest(mode=mode, expected=expected):
                tmp_path = self.tmp_path / str(_case_index)
                tmp_path.mkdir(parents=True, exist_ok=True)
                registry_module = registry
                database = database_fixture(tmp_path)
                registry_module.add_story("sample.json", "Wells", registry=database)
                result = registry_module.check_and_add(
                    "SAMPLE.JSON", ["wells"], mode=mode, registry=database
                )
                self.assertIs(result, expected)
                self.assertEqual(registry_module.registry_count(database), 1)

    def test_check_and_add_warn_reports_original_and_current_sources(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        capsys = self.capsys
        registry_module.add_story(
            "sample.json", "Wells", source="Gutenberg", registry=database
        )
        result = registry_module.check_and_add(
            "sample.json",
            "Wells",
            mode="warn",
            source="Standard EBooks",
            registry=database,
        )
        message = capsys.readouterr().out

        self.assertIs(result, True)

        self.assertIn("WARNING: Duplicate story detected", message)

        self.assertIn("sample.json", message)

        self.assertIn("Previously gathered from: Gutenberg", message)

        self.assertIn("Current source: Standard EBooks", message)

    def test_check_and_add_warn_without_sources_prints_only_warning(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        capsys = self.capsys
        registry_module.add_story("sample.json", "Wells", registry=database)
        registry_module.check_and_add(
            "sample.json", "Wells", mode="warn", registry=database
        )
        message = capsys.readouterr().out

        self.assertIn("WARNING: Duplicate story detected", message)

        self.assertNotIn("Previously gathered from:", message)

        self.assertNotIn("Current source:", message)

    def test_check_and_add_silent_modes_produce_no_output(self):
        for _case_index, mode in enumerate(["ignore", "discard"]):
            with self.subTest(mode=mode):
                tmp_path = self.tmp_path / str(_case_index)
                tmp_path.mkdir(parents=True, exist_ok=True)
                registry_module = registry
                database = database_fixture(tmp_path)
                capsys = self.capsys
                registry_module.add_story("sample.json", "Wells", registry=database)
                registry_module.check_and_add(
                    "sample.json", "Wells", mode=mode, registry=database
                )
                self.assertEqual(capsys.readouterr().out, "")

    def test_check_and_add_rejects_invalid_modes(self):
        for _case_index, mode in enumerate(["reject", "", "WARN", None]):
            with self.subTest(mode=mode):
                tmp_path = self.tmp_path / str(_case_index)
                tmp_path.mkdir(parents=True, exist_ok=True)
                registry_module = registry
                database = database_fixture(tmp_path)
                with self.assertRaisesRegex(ValueError, "mode must be"):
                    registry_module.check_and_add(
                        "sample.json", "Wells", mode=mode, registry=database
                    )
                self.assertFalse(database.exists())

    def test_check_and_add_does_not_replace_initial_source(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        registry_module.check_and_add(
            "sample.json",
            "Wells",
            mode="discard",
            source="First Source",
            registry=database,
        )
        registry_module.check_and_add(
            "sample.json",
            "Wells",
            mode="ignore",
            source="Later Source",
            registry=database,
        )
        with sqlite3.connect(database) as connection:
            source = connection.execute("SELECT source FROM stories").fetchone()[0]

        self.assertEqual(source, "First Source")

    def test_export_empty_tsv_has_header(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        target = tmp_path / "empty.tsv"
        count = registry_module.export_registry(target, registry=database)

        self.assertEqual(count, 0)

        self.assertEqual(target.read_text(encoding="utf-8"), "Filename\tAuthors\n")

    def test_export_default_tsv_omits_source(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        seeded_registry = seeded_registry_fixture(registry_module, database)
        target = tmp_path / "registry.tsv"
        count = registry_module.export_registry(target, registry=seeded_registry)
        lines = target.read_text(encoding="utf-8").splitlines()

        self.assertEqual(count, 2)

        self.assertEqual(
            lines,
            [
                "Filename\tAuthors",
                "foundation.json\tasimov",
                "nightfall.json\tasimov, silverberg",
            ],
        )

    def test_export_tsv_can_include_source(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        seeded_registry = seeded_registry_fixture(registry_module, database)
        target = tmp_path / "registry.tsv"
        count = registry_module.export_registry(
            target, registry=seeded_registry, include_source=True
        )
        lines = target.read_text(encoding="utf-8").splitlines()

        self.assertEqual(count, 2)

        self.assertEqual(
            lines,
            [
                "Filename\tAuthors\tSource",
                "foundation.json\tasimov\tGutenberg",
                "nightfall.json\tasimov, silverberg\tStandard EBooks",
            ],
        )

    def test_export_tsv_uses_blank_source_when_missing(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        registry_module.add_story("sample.json", "Wells", registry=database)
        target = tmp_path / "registry.tsv"
        registry_module.export_registry(target, registry=database, include_source=True)

        self.assertEqual(
            target.read_text(encoding="utf-8").splitlines()[1], "sample.json\twells\t"
        )

    def test_export_text_has_labels(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        seeded_registry = seeded_registry_fixture(registry_module, database)
        target = tmp_path / "registry.txt"
        count = registry_module.export_registry(
            target, registry=seeded_registry, format="text"
        )
        content = target.read_text(encoding="utf-8")

        self.assertEqual(count, 2)

        self.assertIn("Filename: foundation.json\n", content)

        self.assertIn("Authors:  asimov\n", content)

        self.assertIn("Filename: nightfall.json\n", content)

        self.assertIn("Authors:  asimov, silverberg\n", content)

        self.assertNotIn("Source:", content)

    def test_export_text_includes_source(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        seeded_registry = seeded_registry_fixture(registry_module, database)
        target = tmp_path / "registry.txt"
        registry_module.export_registry(
            target, registry=seeded_registry, format="text", include_source=True
        )
        content = target.read_text(encoding="utf-8")

        self.assertIn("Source:   Gutenberg", content)

        self.assertIn("Source:   Standard EBooks", content)

    def test_export_empty_text_is_empty(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        target = tmp_path / "empty.txt"
        count = registry_module.export_registry(
            target, registry=database, format="text"
        )

        self.assertEqual(count, 0)

        self.assertEqual(target.read_text(encoding="utf-8"), "")

    def test_export_rejects_unknown_formats(self):
        for _case_index, format_name in enumerate(["csv", "json", "", "TEXT"]):
            with self.subTest(format_name=format_name):
                tmp_path = self.tmp_path / str(_case_index)
                tmp_path.mkdir(parents=True, exist_ok=True)
                registry_module = registry
                database = database_fixture(tmp_path)
                target = tmp_path / "invalid_output.txt"
                with self.assertRaisesRegex(ValueError, "format must be"):
                    registry_module.export_registry(
                        target, registry=database, format=format_name
                    )
                self.assertFalse(target.exists())
                self.assertFalse(database.exists())

    def test_export_does_not_modify_registry(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        seeded_registry = seeded_registry_fixture(registry_module, database)
        target = tmp_path / "registry.tsv"
        registry_module.export_registry(target, registry=seeded_registry)

        self.assertEqual(registry_module.registry_count(seeded_registry), 2)

    def test_registry_count_returns_zero_for_empty_database(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)

        self.assertEqual(registry_module.registry_count(database), 0)

    def test_registry_count_reports_unique_records(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        registry_module.add_story("first.json", "Wells", registry=database)
        registry_module.add_story("second.json", "Wells", registry=database)
        registry_module.add_story("FIRST.JSON", ["wells"], registry=database)

        self.assertEqual(registry_module.registry_count(database), 2)

    def test_clear_registry_removes_all_stories(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        seeded_registry = seeded_registry_fixture(registry_module, database)
        registry_module.clear_registry(seeded_registry)

        self.assertEqual(registry_module.registry_count(seeded_registry), 0)

        self.assertIs(
            registry_module.check_story(
                "foundation.json", "Asimov", registry=seeded_registry
            ),
            False,
        )

    def test_clear_registry_retains_sqlite_table(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        seeded_registry = seeded_registry_fixture(registry_module, database)
        registry_module.clear_registry(seeded_registry)
        with sqlite3.connect(seeded_registry) as connection:
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'stories'"
            ).fetchall()

        self.assertEqual(tables, [("stories",)])

    def test_clear_registry_allows_new_entries(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        seeded_registry = seeded_registry_fixture(registry_module, database)
        registry_module.clear_registry(seeded_registry)
        result = registry_module.add_story(
            "new.json", "Butler", registry=seeded_registry
        )

        self.assertIs(result, True)

        self.assertEqual(registry_module.registry_count(seeded_registry), 1)

    def test_clear_registry_is_idempotent(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        seeded_registry = seeded_registry_fixture(registry_module, database)
        registry_module.clear_registry(seeded_registry)
        registry_module.clear_registry(seeded_registry)

        self.assertEqual(registry_module.registry_count(seeded_registry), 0)

    def test_separate_database_paths_are_independent(self):
        registry_module = registry
        tmp_path = self.tmp_path
        first = tmp_path / "first.sqlite3"
        second = tmp_path / "second.sqlite3"
        registry_module.add_story("first.json", "Wells", registry=first)
        registry_module.add_story("second.json", "Asimov", registry=second)

        self.assertEqual(registry_module.registry_count(first), 1)

        self.assertEqual(registry_module.registry_count(second), 1)

        self.assertIs(
            registry_module.check_story("first.json", "Wells", registry=second), False
        )

        self.assertIs(
            registry_module.check_story("second.json", "Asimov", registry=first), False
        )

    def test_check_then_add_workflow_does_not_register_until_added(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        exists_before_download = registry_module.check_story(
            "sample.json", "Wells", registry=database
        )
        count_before_save = registry_module.registry_count(database)
        saved_successfully = True
        if saved_successfully:
            added = registry_module.add_story(
                "sample.json", "Wells", source="Standard EBooks", registry=database
            )

        self.assertIs(exists_before_download, False)

        self.assertEqual(count_before_save, 0)

        self.assertIs(added, True)

        self.assertTrue(
            registry_module.check_story("sample.json", "Wells", registry=database)
        )

    def test_failed_download_workflow_leaves_registry_unchanged(self):
        registry_module = registry
        tmp_path = self.tmp_path
        database = database_fixture(tmp_path)
        exists_before_download = registry_module.check_story(
            "sample.json", "Wells", registry=database
        )

        self.assertIs(exists_before_download, False)

        self.assertEqual(registry_module.registry_count(database), 0)


if __name__ == "__main__":
    unittest.main()
