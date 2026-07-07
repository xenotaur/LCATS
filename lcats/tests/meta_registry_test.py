"""Tests for lcats.meta_registry."""

import datetime
import pathlib
import tempfile
import unittest

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    import tomli as tomllib

from lcats import meta_registry


class TestMetaRegistry(unittest.TestCase):

    def test_register_project_successful_writes_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = pathlib.Path(tmp)
            repo_dir = workspace / "sample-repo"
            (repo_dir / "project").mkdir(parents=True)

            record = meta_registry.register_project(
                workspace_root=workspace,
                repo_locator=str(repo_dir),
            )

            self.assertEqual(record["setup_state"], "lrh_project_present")
            self.assertEqual(record["short_name"], "sample-repo")

            record_path = workspace / "projects" / f"{record['directory_name']}.toml"
            self.assertTrue(record_path.exists())
            text = record_path.read_text(encoding="utf-8")
            self.assertIn("[project]", text)
            self.assertIn('setup_state = "lrh_project_present"', text)

    def test_register_project_duplicate_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = pathlib.Path(tmp)
            repo_dir = workspace / "repo-one"
            repo_dir.mkdir(parents=True)

            meta_registry.register_project(
                workspace_root=workspace,
                repo_locator=str(repo_dir),
            )

            with self.assertRaises(ValueError):
                meta_registry.register_project(
                    workspace_root=workspace,
                    repo_locator=str(repo_dir),
                )

            forced = meta_registry.register_project(
                workspace_root=workspace,
                repo_locator=str(repo_dir),
                force=True,
            )
            self.assertTrue(
                (workspace / "projects" / f"{forced['directory_name']}.toml").exists()
            )

    def test_register_project_setup_state_not_set_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = pathlib.Path(tmp)
            repo_dir = workspace / "repo-two"
            repo_dir.mkdir(parents=True)

            record = meta_registry.register_project(
                workspace_root=workspace,
                repo_locator=str(repo_dir),
            )
            self.assertEqual(record["setup_state"], "not_set_up")

    def test_register_project_escapes_toml_string_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = pathlib.Path(tmp)
            locator = 'C:\\repos\\my"proj'

            record = meta_registry.register_project(
                workspace_root=workspace,
                repo_locator=locator,
            )
            record_path = workspace / "projects" / f"{record['directory_name']}.toml"

            parsed = tomllib.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(parsed["identity"]["repo_locator"], locator)

    def test_project_ids_increment_for_same_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = pathlib.Path(tmp)
            first = meta_registry.register_project(
                workspace_root=workspace,
                repo_locator="https://example.com/a.git",
            )
            second = meta_registry.register_project(
                workspace_root=workspace,
                repo_locator="https://example.com/b.git",
            )

            date_part = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
            self.assertEqual(first["id"], f"proj-{date_part}-001")
            self.assertEqual(second["id"], f"proj-{date_part}-002")


if __name__ == "__main__":
    unittest.main()
