"""First-use policy against real tiny catalogs and a stubbed HTTP boundary.

No Gutenberg traffic: authored RDF archives are parsed, acquired, retained and
queried through the real library. Only HTTP responses and terminal input are fake.
"""

import dataclasses
import io
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from lcats import cli
from lcats.gatherers import main
from lcats.gatherers import planning
from lcats.gettenberg import _resource_transport
from lcats.gettenberg import catalog_cli
from lcats.gettenberg import errors
from lcats.gettenberg import preparation
from lcats.gettenberg import resources
from tests.gettenberg_tests import catalog_receipts_test
from tests.gettenberg_tests import resources_test


class Terminal(io.StringIO):
    """Controllable input boundary, without changing actual terminal state."""

    def isatty(self):
        return True


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve()
        self.cache = self.root / "cache"
        self.archive = self.root / "fixture.tar.bz2"
        self.body = catalog_receipts_test.CatalogReceiptTests.archive([(1, "Original")])
        self.archive.write_bytes(self.body)
        self.service = preparation.CatalogPreparation(self.cache, archive=self.archive)
        self.request = resources.SourceRequest.from_url(
            "https://fixture.invalid/rdf", kind="archive"
        )
        self.policy = resources.NetworkPolicy(
            online=True, allowed_origins=("https://fixture.invalid",)
        )
        self.clock = resources_test.Clock()
        patch = mock.patch.object(_resource_transport, "time", self.clock)
        patch.start()
        self.addCleanup(patch.stop)

    def acquire(self):
        """Populate a real original-byte cache using an authored HTTP response."""
        client = mock.Mock()
        client.open.return_value = resources_test.MemoryResponse(
            body=self.body, headers=(("ETag", '"fixture"'),)
        )
        with mock.patch.object(_resource_transport, "opener", return_value=client):
            result = resources.ResourceStore(self.cache).fetch(
                self.request, policy=self.policy
            )
        return result

    def test_plan_dry_run_and_unapproved_setup_create_nothing(self):
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network")):
            plan = self.service.plan()
            self.assertEqual(plan.action, "setup")
            self.assertTrue(plan.approval_required)
            self.assertEqual(self.service.prepare(dry_run=True), plan)
            json.dumps(dataclasses.asdict(plan))
            with self.assertRaisesRegex(preparation.PreparationError, "approval"):
                self.service.prepare()
        self.assertFalse(self.cache.exists())

    def test_not_required_does_not_inspect_broken_catalog(self):
        self.cache.mkdir()
        (self.cache / "gettenberg").write_text("not a directory")
        self.assertEqual(self.service.prepare(required=False).action, "not_required")
        self.assertEqual(self.service.plan().action, "blocked")

    def test_setup_reuse_never_reads_replacement_or_refreshes(self):
        original = self.service.prepare(approved=True)
        self.archive.unlink()
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network")):
            service = preparation.CatalogPreparation(
                self.cache, request=self.request, policy=self.policy
            )
            self.assertEqual(service.plan().action, "reuse")
            reused = service.prepare()
        self.assertEqual(original.generation_id, reused.generation_id)
        self.assertTrue(reused.reused)
        self.assertEqual(len(self.service.manager.status()["generations"]), 1)

    def test_plan_is_rechecked_after_state_changes(self):
        self.assertEqual(self.service.plan().action, "setup")
        self.archive.unlink()
        with self.assertRaisesRegex(preparation.PreparationError, "not a file"):
            self.service.prepare(approved=True)
        self.assertFalse(self.cache.exists())

    def test_missing_source_and_offline_miss_fail_without_writes(self):
        cases = [
            preparation.CatalogPreparation(self.cache),
            preparation.CatalogPreparation(self.cache, request=self.request),
            preparation.CatalogPreparation(
                self.cache, request=self.request, policy=self.policy, offline=True
            ),
        ]
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network")):
            for service in cases:
                self.assertEqual(service.plan().action, "blocked")
                with self.assertRaises(preparation.PreparationError):
                    service.prepare(approved=True)
        self.assertFalse(self.cache.exists())

    def test_offline_verified_archive_reuse_builds_real_catalog(self):
        artifact = self.acquire()
        service = preparation.CatalogPreparation(
            self.cache, request=self.request, policy=self.policy, offline=True
        )
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network")):
            self.assertEqual(service.plan().acquisition, "reuse")
            generation = service.prepare(approved=True)
            with service.manager.open() as reader:
                self.assertEqual(reader.get(1).ebook.titles[0].value.text, "Original")
        self.assertEqual(generation.manifest["archive_sha256"], artifact.sha256)
        self.assertIsNotNone(generation.manifest["source"]["receipt"]["retrieved_at"])

    def test_corrupt_cache_is_not_a_miss(self):
        artifact = self.acquire()
        artifact.path.write_bytes(b"corrupt")
        service = preparation.CatalogPreparation(
            self.cache, request=self.request, policy=self.policy
        )
        with self.assertRaises(resources.ResourceIntegrityError):
            service.prepare(approved=True)
        self.assertEqual(service.manager.status()["state"], "missing")

    def test_online_setup_and_download_plan_use_explicit_authority(self):
        service = preparation.CatalogPreparation(
            self.cache, request=self.request, policy=self.policy
        )
        self.assertEqual(service.plan().acquisition, "download")
        self.assertFalse(self.cache.exists())
        client = mock.Mock()
        client.open.return_value = resources_test.MemoryResponse(body=self.body)
        with mock.patch.object(_resource_transport, "opener", return_value=client):
            generation = service.prepare(approved=True)
        self.assertFalse(generation.reused)
        self.assertEqual(client.open.call_count, 1)

    def test_invalid_arguments_fail_at_boundary(self):
        cases = [
            {"archive": self.archive, "request": self.request},
            {
                "request": resources.SourceRequest.from_url(
                    "https://fixture.invalid/story"
                )
            },
            {"offline": 1},
            {"policy": None},
        ]
        for kwargs in cases:
            with (
                self.subTest(kwargs=kwargs),
                self.assertRaises(errors.CatalogInputError),
            ):
                preparation.CatalogPreparation(self.cache, **kwargs)
        for kwargs in ({"approved": 1}, {"dry_run": 1}, {"required": 1}):
            with (
                self.subTest(kwargs=kwargs),
                self.assertRaises(errors.CatalogInputError),
            ):
                self.service.prepare(**kwargs)
        self.assertFalse(self.cache.exists())

    def command(self, operation, *args):
        message, code = cli.dispatch(
            "catalog", [operation, "--cache-dir", str(self.cache), *args]
        )
        return json.loads(message), code

    def test_nested_help_uses_the_executable_command_prefix(self):
        for operation in ("status", "setup", "refresh", "rebuild"):
            with (
                self.subTest(operation=operation),
                mock.patch.object(sys, "stdout", io.StringIO()) as output,
            ):
                with self.assertRaises(SystemExit) as exited:
                    cli.dispatch("catalog", [operation, "--help"])
                self.assertEqual(exited.exception.code, 0)
                self.assertTrue(
                    output.getvalue().startswith(f"usage: lcats catalog {operation} "),
                    output.getvalue(),
                )
        self.assertFalse(self.cache.exists())

    def test_cli_status_and_dry_run_need_no_approval(self):
        report, code = self.command("status")
        self.assertEqual((report["state"], code), ("missing", 0))
        with mock.patch.object(sys, "stdin", Terminal("yes\n")) as terminal:
            report, code = self.command(
                "setup", "--archive", str(self.archive), "--dry-run"
            )
            self.assertEqual((report["action"], code), ("setup", 0))
            self.assertEqual(terminal.tell(), 0)
        self.assertFalse(self.cache.exists())

    def test_cli_unattended_decline_and_eof_are_nonmutating(self):
        for terminal in (io.StringIO("yes\n"), Terminal("no\n"), Terminal("")):
            with (
                self.subTest(terminal=terminal),
                mock.patch.object(sys, "stdin", terminal),
                mock.patch.object(sys, "stderr", io.StringIO()),
            ):
                report, code = self.command("setup", "--archive", str(self.archive))
                self.assertEqual(code, 2)
                self.assertIn("error", report)
                self.assertFalse(self.cache.exists())

    def test_cli_interactive_setup_and_yes_reuse(self):
        with (
            mock.patch.object(sys, "stdin", Terminal("yes\n")),
            mock.patch.object(sys, "stderr", io.StringIO()) as stderr,
        ):
            report, code = self.command("setup", "--archive", str(self.archive))
        self.assertEqual(code, 0)
        self.assertIn(str(self.archive), stderr.getvalue())
        reused, code = self.command("setup", "--yes")
        self.assertEqual(code, 0)
        self.assertTrue(reused["reused"])
        self.assertEqual(report["generation_id"], reused["generation_id"])

    def test_cli_yes_sets_up_local_archive_offline(self):
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network")):
            report, code = self.command(
                "setup", "--yes", "--offline", "--archive", str(self.archive)
            )
        self.assertEqual(code, 0)
        self.assertFalse(report["reused"])

    def test_cli_rebuild_retained_source_and_count_change_are_explicit(self):
        original = self.service.prepare(approved=True)
        before = sorted(str(p) for p in self.cache.rglob("*"))
        report, code = self.command("rebuild", "--dry-run")
        self.assertEqual((report["action"], code), ("rebuild", 0))
        self.assertEqual(before, sorted(str(p) for p in self.cache.rglob("*")))
        self.archive.unlink()
        report, code = self.command("rebuild")
        self.assertEqual(code, 0)
        self.assertNotEqual(original.generation_id, report["generation_id"])
        self.archive.write_bytes(
            catalog_receipts_test.CatalogReceiptTests.archive([(1, "One"), (2, "Two")])
        )
        previous = report["generation_id"]
        report, code = self.command("rebuild", "--archive", str(self.archive))
        self.assertEqual(code, 2)
        self.assertIn("candidate_generation_id", report)
        self.assertEqual(
            self.service.manager.status()["active"]["generation_id"], previous
        )
        report, code = self.command(
            "rebuild", "--archive", str(self.archive), "--allow-count-change"
        )
        self.assertEqual(code, 0)
        self.assertNotEqual(previous, report["generation_id"])

    def test_cli_refresh_requires_ready_and_online_even_on_hit(self):
        report, code = self.command("refresh", "--url", self.request.request_url)
        self.assertEqual(code, 2)
        self.assertFalse(self.cache.exists())
        self.acquire()
        self.service.prepare(approved=True)
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network")):
            for flags in (("--offline",), ("--offline", "--dry-run")):
                report, code = self.command(
                    "refresh", "--url", self.request.request_url, *flags
                )
                self.assertEqual(code, 2)
            report, code = self.command(
                "refresh", "--url", self.request.request_url, "--dry-run"
            )
            self.assertEqual((report["action"], code), ("refresh", 0))

    def test_cli_refresh_composes_acquisition_and_update(self):
        self.acquire()
        initial = self.service.prepare(approved=True)
        changed = catalog_receipts_test.CatalogReceiptTests.archive([(1, "Changed")])
        client = mock.Mock()
        client.open.return_value = resources_test.MemoryResponse(body=changed)
        with mock.patch.object(_resource_transport, "opener", return_value=client):
            report, code = self.command("refresh", "--url", self.request.request_url)
        self.assertEqual(code, 0)
        self.assertNotEqual(initial.generation_id, report["generation_id"])
        with self.service.manager.open() as reader:
            self.assertEqual(reader.get(1).ebook.titles[0].value.text, "Changed")

    def test_cli_source_argument_errors_do_not_initialize(self):
        for args in (
            (
                "--archive",
                str(self.archive),
                "--allow-origin",
                "https://fixture.invalid",
            ),
            ("--url", "file:///bad"),
            ("--url", self.request.request_url, "--offline", "--yes"),
        ):
            report, code = self.command("setup", *args)
            self.assertEqual(code, 2)
        self.assertFalse(self.cache.exists())
        with (
            mock.patch.object(sys, "stderr", io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            catalog_cli.run(["refresh"])


class CollectionPlanningTests(unittest.TestCase):
    def test_source_identity_does_not_imply_catalog_requirement(self):
        for source in ("local", "fixed_url", "gutenberg"):
            self.assertFalse(
                planning.CollectionRequirement("example", source).needs_catalog
            )
            for use in ("discovery", "enrichment"):
                self.assertTrue(
                    planning.CollectionRequirement("example", source, use).needs_catalog
                )

    def test_selection_order_duplicates_and_default_are_preserved(self):
        names = ["sherlock", "lovecraft", "sherlock"]
        self.assertEqual([item.name for item in planning.select(names)], names)
        self.assertEqual(tuple(item.name for item in planning.select()), planning.NAMES)
        self.assertTrue(planning.select(["mass_quantities"])[0].needs_catalog)

    def test_unknown_name_fails_before_any_collection_import(self):
        with mock.patch.object(
            main.importlib, "import_module", side_effect=AssertionError("executed")
        ):
            message, code = main.run(["sherlock", "unknown"])
        self.assertEqual(code, 2)
        self.assertIn("unknown", message)

    def test_real_cli_pristine_dry_run_has_no_cache_or_network_side_effects(self):
        # A fresh interpreter catches eager imports hidden by unittest's shared
        # module cache. Isolate all user/output/cache roots and suppress bytecode.
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            environment = dict(
                os.environ,
                PYTHONDONTWRITEBYTECODE="1",
                HOME=str(root),
                LCATS_CACHE_DIR=str(root / "cache"),
                LCATS_DATA_DIR=str(root / "data"),
                MPLCONFIGDIR=str(root / "mpl"),
            )
            code = """import socket, ssl, sys
socket.socket = lambda *a, **k: (_ for _ in ()).throw(AssertionError("network"))
from lcats import cli
for command, args in (("gather", ["--dry-run", "sherlock"]), ("gather", ["--dry-run"]), ("catalog", ["status"]), ("catalog", ["setup", "--dry-run"])):
    message, status = cli.dispatch(command, args)
    assert status == 0, message
assert "gutenbergpy" not in sys.modules
assert "matplotlib" not in sys.modules
"""
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(root.iterdir()), [])

    def test_actual_entry_point_reports_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            environment = dict(
                os.environ,
                PYTHONDONTWRITEBYTECODE="1",
                LCATS_CACHE_DIR=str(root / "cache"),
                MPLCONFIGDIR=str(root / "mpl"),
            )
            result = subprocess.run(
                [sys.executable, "-m", "lcats.cli", "gather", "sherlock", "--dry-run"],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("No metadata catalog", result.stdout)
            self.assertEqual(list(root.iterdir()), [])

    def test_selected_fixed_url_gather_preserves_buckets_and_existing_outputs(self):
        # Run the real registry, extractor, cache and normalization in a fresh
        # process. Stub only HTTP text; all generated outputs stay in this temp.
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            environment = dict(
                os.environ,
                PYTHONDONTWRITEBYTECODE="1",
                LCATS_CACHE_DIR=str(root / "cache"),
                LCATS_DATA_DIR=str(root / "data"),
            )
            code = """import json, pathlib, sys
from lcats.gatherers import downloaders, main
from lcats.gatherers.sherlock import gatherer
html = '<html><body>' + ''.join('<h2>'+heading+'</h2><p>A simple story. Two sentences.</p>' for _, heading, _ in gatherer.ADVENTURES_HEADINGS) + '</body></html>'
downloaders.load_page = lambda *a, **k: html
message, status = main.run(['sherlock'])
assert status == 0, message
paths = sorted(pathlib.Path('data/sherlock').glob('*/story.json'))
assert len(paths) == len(gatherer.ADVENTURES_HEADINGS), paths
assert {p.parent.name for p in paths} == {entry[0] for entry in gatherer.ADVENTURES_HEADINGS}
before = {str(p): p.read_bytes() for p in paths}
for path in paths:
    value = json.loads(path.read_text())
    assert 'A simple story.' in str(value), value
downloaders.load_page = lambda *a, **k: (_ for _ in ()).throw(AssertionError('repeat download'))
assert main.run(['sherlock'])[1] == 0
assert all(pathlib.Path(p).read_bytes() == body for p, body in before.items())
assert 'gutenbergpy' not in sys.modules
assert not pathlib.Path('cache/gettenberg').exists()
assert not pathlib.Path('cache/texts').exists()
"""
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
