"""Offline maintenance qualification with real archives/catalogs and GH boundaries."""

import hashlib
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

import yaml

from lcats.dev import gettenberg_ci
from lcats.gettenberg import _resource_transport
from lcats.gettenberg import lifecycle
from lcats.gettenberg import resources
from lcats.gettenberg import sources_cli
from lcats.utils import capture
from tests.gettenberg_tests import catalog_test
from tests.gettenberg_tests import resources_test

PACKAGE = pathlib.Path(__file__).resolve().parents[2]
REPOSITORY = PACKAGE.parent


def workflow(name):
    """Preserve YAML's `on` key rather than coercing it to a YAML1.1 boolean."""
    return yaml.load(
        (REPOSITORY / ".github/workflows" / name).read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = pathlib.Path(self.directory.name)
        self.cache = self.root / "cache"
        self.archive = self.root / "source.tar.bz2"
        self.archive.write_bytes(
            catalog_test.archive_bytes(
                [
                    (
                        "pg84.rdf",
                        catalog_test.record(84, "Fixture title"),
                        tarfile.REGTYPE,
                    )
                ]
            )
        )
        self.network = mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        )
        self.network.start()
        self.addCleanup(self.network.stop)

    def seed_source(self):
        """Populate the actual receipt/blob store with a substituted HTTP response."""
        client = mock.Mock()
        client.open.return_value = resources_test.MemoryResponse(
            body=self.archive.read_bytes()
        )
        request = sources_cli.catalog_request()
        policy = resources.NetworkPolicy(
            online=True, allowed_origins=("https://www.gutenberg.org",)
        )
        with mock.patch.object(_resource_transport, "opener", return_value=client):
            return resources.ResourceStore(self.cache).fetch(request, policy=policy)

    def test_previews_do_not_create_cache_or_access_network(self):
        result, code = gettenberg_ci.maintain_catalog("setup", self.cache)
        self.assertEqual(code, 0)
        self.assertIn("--dry-run", result["command"])
        self.assertNotIn("--yes", result["command"])
        self.assertFalse(self.cache.exists())
        result, code = gettenberg_ci.maintain_catalog("rebuild", self.cache)
        self.assertEqual(code, 2)
        self.assertIn("--offline", result["command"])
        self.assertFalse(self.cache.exists())

    def test_offline_bootstrap_reuses_resource_receipt_then_rebuilds(self):
        source = self.seed_source()
        result, code = gettenberg_ci.maintain_catalog("rebuild", self.cache, apply=True)
        self.assertEqual(code, 0, result)
        self.assertIn("--offline", result["command"])
        before = lifecycle.CatalogManager(self.cache).status()["active"]
        self.assertEqual(before["manifest"]["archive_sha256"], source.sha256)
        result, code = gettenberg_ci.maintain_catalog("rebuild", self.cache, apply=True)
        self.assertEqual(code, 0, result)
        after = lifecycle.CatalogManager(self.cache).status()["active"]
        self.assertNotEqual(before["generation_id"], after["generation_id"])
        self.assertEqual(
            before["manifest"]["archive_sha256"], after["manifest"]["archive_sha256"]
        )
        self.assertTrue(pathlib.Path(before["catalog_path"]).exists())

    def test_refresh_preserves_count_change_guard_and_requires_explicit_override(self):
        clock = resources_test.Clock()
        with mock.patch.object(_resource_transport, "time", clock):
            self.seed_source()
            _, code = gettenberg_ci.maintain_catalog("rebuild", self.cache, apply=True)
            self.assertEqual(code, 0)
            before = lifecycle.CatalogManager(self.cache).status()["active"][
                "generation_id"
            ]
            updated = catalog_test.archive_bytes(
                [
                    ("first.rdf", catalog_test.record(84, "First"), tarfile.REGTYPE),
                    ("second.rdf", catalog_test.record(85, "Second"), tarfile.REGTYPE),
                ]
            )
            client = mock.Mock()
            client.open.side_effect = (
                lambda *args, **kwargs: resources_test.MemoryResponse(body=updated)
            )
            with mock.patch.object(_resource_transport, "opener", return_value=client):
                result, code = gettenberg_ci.maintain_catalog(
                    "refresh", self.cache, apply=True
                )
                self.assertEqual(code, 2, result)
                self.assertIn("candidate_generation_id", result["result"])
                self.assertEqual(
                    lifecycle.CatalogManager(self.cache).status()["active"][
                        "generation_id"
                    ],
                    before,
                )
                result, code = gettenberg_ci.maintain_catalog(
                    "refresh", self.cache, apply=True, allow_count_change=True
                )
                self.assertEqual(code, 0, result)
            with lifecycle.CatalogManager(self.cache).open() as library:
                self.assertIsNotNone(library.get(85))
            keys = gettenberg_ci.cache_keys(cache_dir=self.cache, run_id="2-1")
            self.assertIn(hashlib.sha256(updated).hexdigest(), keys["catalog_key"])

    def test_setup_reuses_ready_catalog_without_network(self):
        lifecycle.CatalogManager(self.cache).setup(self.archive)
        result, code = gettenberg_ci.maintain_catalog("setup", self.cache, apply=True)
        self.assertEqual(code, 0, result)
        self.assertTrue(result["result"]["reused"])

    def test_invalid_catalog_and_missing_refresh_fail_without_replacement(self):
        result, code = gettenberg_ci.maintain_catalog("refresh", self.cache, apply=True)
        self.assertEqual(code, 2)
        self.assertFalse(self.cache.exists())
        lifecycle.CatalogManager(self.cache).setup(self.archive)
        pointer = self.cache / "gettenberg/active.json"
        pointer.write_text("{bad json", encoding="utf-8")
        result, code = gettenberg_ci.maintain_catalog("setup", self.cache, apply=True)
        self.assertEqual(code, 2)
        self.assertEqual(result["state"], "invalid")
        self.assertEqual(pointer.read_text(), "{bad json")

    def test_cache_keys_separate_source_compatibility_input_and_attempt(self):
        prefixes = gettenberg_ci.cache_keys()
        self.assertFalse(self.cache.exists())
        self.assertNotEqual(prefixes["source_prefix"], prefixes["catalog_prefix"])
        lifecycle.CatalogManager(self.cache).setup(self.archive)
        first = gettenberg_ci.cache_keys(cache_dir=self.cache, run_id="123-1")
        second = gettenberg_ci.cache_keys(cache_dir=self.cache, run_id="123-2")
        digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.assertIn(digest, first["source_key"])
        self.assertIn(digest, first["catalog_key"])
        self.assertNotEqual(first["catalog_key"], second["catalog_key"])
        for key in first.values():
            self.assertNotIn("\n", key)
            self.assertLess(len(key), 512)
        # A compatibility change must not invalidate reusable source blobs.
        with mock.patch.object(
            gettenberg_ci, "compatibility_fingerprint", return_value="f" * 64
        ):
            changed = gettenberg_ci.cache_keys()
        self.assertEqual(changed["source_prefix"], prefixes["source_prefix"])
        self.assertNotEqual(changed["catalog_prefix"], prefixes["catalog_prefix"])
        for run_id in (None, "run\ninjected=yes", "../123", "1-2-extra"):
            with self.subTest(run_id=run_id), self.assertRaises(ValueError):
                gettenberg_ci.cache_keys(cache_dir=self.cache, run_id=run_id)

    def test_restored_catalog_and_resource_paths_are_portable(self):
        self.seed_source()
        result, code = gettenberg_ci.maintain_catalog("rebuild", self.cache, apply=True)
        self.assertEqual(code, 0, result)
        restored = self.root / "other-runner/cache"
        shutil.copytree(self.cache, restored)
        result, code = gettenberg_ci.maintain_catalog("rebuild", restored, apply=True)
        self.assertEqual(code, 0, result)
        with lifecycle.CatalogManager(restored).open() as library:
            self.assertIsNotNone(library.get(84))
        # Simulate a parser/schema key miss: keep only independently restored sources.
        source_only = self.root / "source-only"
        for name in ("resources", "archives"):
            shutil.copytree(
                restored / "gettenberg" / name, source_only / "gettenberg" / name
            )
        result, code = gettenberg_ci.maintain_catalog(
            "rebuild", source_only, apply=True
        )
        self.assertEqual(code, 0, result)

    def test_cli_json_errors_and_safe_github_outputs(self):
        output = self.root / "outputs"
        with capture.suppress_output():
            self.assertEqual(
                gettenberg_ci.main(["keys", "--github-output", str(output)]), 0
            )
            self.assertEqual(
                gettenberg_ci.main(
                    ["keys", "--cache-dir", str(self.cache), "--run-id", "1-1"]
                ),
                2,
            )
        self.assertEqual(len(output.read_text().splitlines()), 2)
        for line in output.read_text().splitlines():
            self.assertEqual(line.count("="), 1)

    def test_workflow_command_really_rebuilds_and_propagates_failure(self):
        config = workflow("cache_maintenance.yml")
        script = next(
            s["run"]
            for s in config["jobs"]["cache_maintenance"]["steps"]
            if s.get("id") == "maintain"
        )
        (self.root / "tools").mkdir()
        (self.root / "tools/gettenberg_ci.py").symlink_to(
            PACKAGE / "tools/gettenberg_ci.py"
        )
        env = {
            **os.environ,
            "PATH": str(pathlib.Path(sys.executable).parent)
            + os.pathsep
            + os.environ["PATH"],
            "PYTHONPATH": str(PACKAGE / "src"),
            "OPERATION": "rebuild",
            "LCATS_CACHE_DIR": str(self.cache),
            "ALLOW_COUNT_CHANGE": "false",
            "GITHUB_OUTPUT": str(self.root / "outputs"),
        }
        # Run the workflow's actual bash, including its errexit behavior.
        failed = subprocess.run(
            ["bash", "-e", "-o", "pipefail", "-c", script],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(failed.returncode, 2, failed.stderr)
        self.assertFalse((self.root / "outputs").exists())
        failure = json.loads((self.root / "maintenance.json").read_text())
        self.assertIn("error", failure["result"])
        lifecycle.CatalogManager(self.cache).setup(self.archive)
        succeeded = subprocess.run(
            ["bash", "-e", "-o", "pipefail", "-c", script],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(succeeded.returncode, 0, succeeded.stderr)
        self.assertEqual((self.root / "outputs").read_text().strip(), "changed=true")


class GithubCacheTests(unittest.TestCase):
    def records(self):
        prefix = gettenberg_ci.CATALOG_NAMESPACE
        return [
            {"id": 9, "key": prefix + "a", "ref": "refs/heads/main"},
            {"id": 10, "key": prefix + "b", "ref": "refs/heads/other"},
            {"id": 11, "key": "Linux-pip-a", "ref": "refs/heads/main"},
            {"id": 12, "key": prefix + "c", "ref": "refs/heads/main"},
            {
                "id": 13,
                "key": gettenberg_ci.SOURCE_NAMESPACE + "a",
                "ref": "refs/heads/main",
            },
        ]

    def boundary(self, *, delete_failure=False):
        calls = []

        def run(args, **kwargs):
            calls.append(args)
            self.assertFalse(kwargs.get("shell", False))
            if args[1] == "api":
                pages = [
                    {"actions_caches": self.records()[:2]},
                    {"actions_caches": self.records()[2:]},
                ]
                return subprocess.CompletedProcess(args, 0, json.dumps(pages), "")
            if delete_failure and args[3] == "12":
                raise subprocess.CalledProcessError(1, args, stderr="fixture failure")
            return subprocess.CompletedProcess(args, 0, "", "")

        return calls, run

    def test_preview_selects_exact_ref_namespace_across_all_pages(self):
        calls, run = self.boundary()
        with mock.patch.object(subprocess, "run", side_effect=run):
            result, code = gettenberg_ci.manage_caches(
                "owner/repo", "refs/heads/main", "catalog"
            )
        self.assertEqual(code, 0)
        self.assertEqual([r["id"] for r in result["selected"]], [9, 12])
        self.assertEqual(result["deleted_ids"], [])
        self.assertEqual(len(calls), 1)
        self.assertIn("--paginate", calls[0])
        self.assertIn("--slurp", calls[0])
        self.assertIn("ref=refs/heads/main", calls[0])

    def test_apply_deletes_numeric_ids_and_reports_partial_failure(self):
        for failure, expected_code, expected_deleted in (
            (False, 0, [9, 12]),
            (True, 2, [9]),
        ):
            with self.subTest(failure=failure):
                calls, run = self.boundary(delete_failure=failure)
                with mock.patch.object(subprocess, "run", side_effect=run):
                    result, code = gettenberg_ci.manage_caches(
                        "owner/repo", "refs/heads/main", "catalog", apply=True
                    )
                self.assertEqual(code, expected_code)
                self.assertEqual(result["deleted_ids"], expected_deleted)
                self.assertEqual(
                    calls[1], ["gh", "cache", "delete", "9", "--repo", "owner/repo"]
                )
                self.assertEqual(calls[2][3], "12")

    def test_missing_or_wrong_ref_save_is_a_failure(self):
        calls, run = self.boundary()
        prefix = gettenberg_ci.CATALOG_NAMESPACE
        with mock.patch.object(subprocess, "run", side_effect=run):
            result, code = gettenberg_ci.verify_saved(
                "owner/repo", "refs/heads/main", [prefix + "a"]
            )
            self.assertEqual(code, 0, result)
            result, code = gettenberg_ci.verify_saved(
                "owner/repo", "refs/heads/main", [prefix + "b", prefix + "missing"]
            )
            self.assertEqual(code, 2)
            self.assertEqual(result["missing_keys"], [prefix + "b", prefix + "missing"])
        self.assertTrue(all(call[1] == "api" for call in calls))

    def test_invalid_inventory_cannot_delete_anything(self):
        for bad in (
            {"bad": []},
            [{"actions_caches": "bad"}],
            [{"actions_caches": [{"id": True, "key": "x", "ref": "refs/heads/main"}]}],
        ):
            with (
                self.subTest(bad=bad),
                mock.patch.object(
                    subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess(
                        [], 0, json.dumps(bad), ""
                    ),
                ) as boundary,
            ):
                with self.assertRaises(ValueError):
                    gettenberg_ci.manage_caches(
                        "owner/repo", "refs/heads/main", "catalog", apply=True
                    )
                self.assertEqual(boundary.call_count, 1)
                with self.assertRaises(ValueError):
                    gettenberg_ci.verify_saved(
                        "owner/repo",
                        "refs/heads/main",
                        [gettenberg_ci.CATALOG_NAMESPACE + "x"],
                    )

    def test_invalid_repo_ref_and_failed_listing_fail_closed(self):
        with mock.patch.object(subprocess, "run") as boundary:
            for repo, ref in (
                ("../repo", "refs/heads/main"),
                ("owner/repo", "main"),
                ("owner/repo", "refs/heads/main\nother"),
            ):
                with self.subTest(repo=repo, ref=ref), self.assertRaises(ValueError):
                    gettenberg_ci.cache_inventory(repo, ref)
            boundary.assert_not_called()
        with (
            mock.patch.object(
                subprocess, "run", side_effect=subprocess.CalledProcessError(1, ["gh"])
            ) as boundary,
            capture.suppress_output(),
        ):
            self.assertEqual(
                gettenberg_ci.main(
                    [
                        "caches",
                        "--repo",
                        "owner/repo",
                        "--ref",
                        "refs/heads/main",
                        "--apply",
                    ]
                ),
                2,
            )
            self.assertEqual(boundary.call_count, 1)


class WorkflowContractTests(unittest.TestCase):
    def test_ordinary_checks_keep_triggers_and_commands_without_gutenberg_caches(self):
        for filename, job_name in (("tests.yml", "test"), ("coverage.yml", "coverage")):
            with self.subTest(filename=filename):
                config = workflow(filename)
                self.assertEqual(
                    set(config["on"]),
                    {"pull_request", "push", "schedule", "workflow_dispatch"},
                )
                job = config["jobs"][job_name]
                self.assertEqual(
                    job["env"]["LCATS_CACHE_DIR"], "${{ runner.temp }}/lcats-unit-cache"
                )
                self.assertFalse(
                    any(
                        s.get("uses", "").startswith("actions/cache")
                        for s in job["steps"]
                    )
                )
                commands = "\n".join(s.get("run", "") for s in job["steps"])
                self.assertNotIn("catalog", commands)
                self.assertNotIn("continue-on-error", json.dumps(config))
                if filename == "tests.yml":
                    self.assertIn("scripts/test", commands)
                else:
                    self.assertEqual(config["on"]["push"]["branches"], ["main"])
                    self.assertIn(
                        "python -m coverage run --source=lcats -m unittest discover",
                        commands,
                    )
                    self.assertIn("python -m coverage report -m", commands)
        lint = workflow("lint.yml")
        self.assertEqual(set(lint["on"]), {"pull_request", "push"})
        self.assertEqual(lint["on"]["push"]["branches"], ["main"])

    def test_manual_workflow_has_explicit_apply_and_no_compatibility_fallback(self):
        config = workflow("cache_maintenance.yml")
        self.assertEqual(set(config["on"]), {"workflow_dispatch"})
        self.assertEqual(
            config["on"]["workflow_dispatch"]["inputs"]["dry_run"]["default"], "true"
        )
        self.assertEqual(config["concurrency"]["cancel-in-progress"], "false")
        steps = config["jobs"]["cache_maintenance"]["steps"]
        for step in steps:
            uses = step.get("uses", "")
            if uses.startswith("actions/cache/restore"):
                self.assertIn("!inputs.dry_run", step["if"])
                self.assertEqual(len(step["with"]["restore-keys"].splitlines()), 1)
                paths = step["with"]["path"]
                if step.get("id") == "source":
                    self.assertIn("/gettenberg/resources", paths)
                    self.assertIn("/gettenberg/archives", paths)
                    self.assertNotIn("generations", paths)
                else:
                    self.assertIn("/gettenberg/generations", paths)
                    self.assertIn("/gettenberg/active.json", paths)
                    self.assertNotIn("archives", paths)
            if uses.startswith("actions/cache/save"):
                self.assertIn("steps.save.outcome == 'success'", step["if"])
        commands = "\n".join(s.get("run", "") for s in steps)
        self.assertNotIn("|| true", commands)
        self.assertNotIn("unittest", commands)
        self.assertNotIn("awk", commands)
        self.assertNotIn("${{ inputs.", commands)
        self.assertIn(
            "--apply",
            next(
                s["run"] for s in steps if s.get("name") == "Delete selected cache IDs"
            ),
        )


if __name__ == "__main__":
    unittest.main()
