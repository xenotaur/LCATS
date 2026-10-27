"""Execute public documentation examples with network access forbidden."""

import contextlib
import doctest
import io
import json
import os
import pathlib
import re
import shlex
import socket
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

from lcats import cli
from lcats.dev import gettenberg_ci
from lcats.gatherers import downloaders
from lcats.gatherers import gutenberg_source
from lcats.gatherers.mass_quantities import storymap
from lcats.gatherers.sherlock import gatherer as sherlock
from lcats.gettenberg import _resource_transport
from lcats.gettenberg import lifecycle
from lcats.gettenberg import resources
from lcats.utils import capture
from tests.gatherers_tests import live_gather_test
from tests.gettenberg_tests import catalog_test
from tests.gettenberg_tests import resources_test


DOCS = pathlib.Path(__file__).resolve().parents[2] / "docs"


class DocumentationTests(unittest.TestCase):
    def migration_example(self, name):
        """Select a named example without coupling tests to document block order."""
        path = DOCS / "how-to/gettenberg-migration.md"
        blocks = re.findall(
            r"```python\n(.*?)```", path.read_text(encoding="utf-8"), re.S
        )
        matching = [
            block for block in blocks if block.startswith(f"# Example: {name}\n")
        ]
        self.assertEqual(len(matching), 1, f"missing or duplicate example: {name}")
        return path, matching[0]

    def run_doctest(self, relative_path):
        path = DOCS / relative_path
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ):
            result = doctest.testfile(
                str(path), module_relative=False, encoding="utf-8", verbose=False
            )
        self.assertEqual(result.failed, 0)
        self.assertGreater(result.attempted, 0)

    def test_first_catalog_tutorial(self):
        self.run_doctest("tutorials/gettenberg-first-catalog.md")

    def test_architecture_example(self):
        self.run_doctest("explanation/gettenberg-architecture.md")

    def test_preparation_reference_example(self):
        path = DOCS / "reference/gettenberg-preparation.md"
        blocks = re.findall(
            r"```python\n(.*?)```", path.read_text(encoding="utf-8"), re.S
        )
        self.assertEqual(len(blocks), 1)
        with tempfile.TemporaryDirectory() as temporary:
            cache = pathlib.Path(temporary) / "cache"
            namespace = {}
            with mock.patch.object(
                socket, "socket", side_effect=AssertionError("network forbidden")
            ):
                for block in blocks:
                    code = block.replace(
                        'cache_dir="cache"', f"cache_dir={str(cache)!r}"
                    )
                    exec(compile(code, str(path), "exec"), namespace)
            self.assertEqual(namespace["plan"].action, "not_required")
            self.assertFalse(cache.exists())

    def test_migration_catalog_query_example(self):
        path, example = self.migration_example("catalog-query")
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            archive = root / "fixture.tar.bz2"
            fixture = catalog_test.FIXTURES / "pg84.rdf"
            archive.write_bytes(
                catalog_test.archive_bytes(
                    [(fixture.name, fixture.read_bytes(), tarfile.REGTYPE)]
                )
            )
            cache = root / "cache"
            namespace = {}
            with mock.patch.object(
                socket, "socket", side_effect=AssertionError("network forbidden")
            ):
                lifecycle.CatalogManager(cache).setup(archive)
                code = example.replace(
                    'CatalogManager("cache")', f"CatalogManager({str(cache)!r})"
                )
                exec(compile(code, str(path), "exec"), namespace)
            self.assertEqual(namespace["record"].ebook.gutenberg_id, 84)
            self.assertEqual(namespace["ids"], (84,))

            # Exercise the complete new session example against the same real catalog.
            path, example = self.migration_example("source-session")
            code = example.replace('cache_dir = "cache"', f"cache_dir = {str(cache)!r}")
            with (
                mock.patch.object(
                    socket, "socket", side_effect=AssertionError("network forbidden")
                ),
                capture.capture_output(),
            ):
                exec(compile(code, str(path), "exec"), namespace)
            self.assertEqual(namespace["metadata"].ebook.gutenberg_id, 84)
            self.assertTrue(namespace["metadata"].titles)
            self.assertFalse(namespace["policy"].online)

    def test_migration_extraction_example_reuses_original_bytes_offline(self):
        path, inspect_example = self.migration_example("inspect-story")
        _, publish_example = self.migration_example("publish-story")
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            cache = root / "cache"
            archive = root / "fixture.tar.bz2"
            # Use the existing authored story fixture at the example's ebook ID.
            record = live_gather_test.fixture_record().replace(
                str(live_gather_test.BOOK_ID).encode(), b"84"
            )
            archive.write_bytes(
                catalog_test.archive_bytes([("pg84.rdf", record, tarfile.REGTYPE)])
            )
            manager = lifecycle.CatalogManager(cache)
            store = resources.ResourceStore(cache)
            routes = resources.GutenbergRoutes(
                live_gather_test.MAIN_ROOT, live_gather_test.GENERATED_ROOT
            )
            policy = resources.NetworkPolicy(
                online=True, allowed_origins=(live_gather_test.ORIGIN,)
            )
            with (
                mock.patch.object(
                    socket, "socket", side_effect=AssertionError("network forbidden")
                ),
                capture.capture_output(),
            ):
                manager.setup(archive)
                with manager.open() as library:
                    choice = resources.select_routable_resource(
                        library.get(84).ebook, routes=routes
                    )
                    client = mock.Mock()
                    client.open.return_value = resources_test.MemoryResponse(
                        body=live_gather_test.ENVELOPE.encode("utf-8"),
                        headers=(("Content-Type", "text/plain; charset=utf-8"),),
                    )
                    with mock.patch.object(
                        _resource_transport, "opener", return_value=client
                    ):
                        original = store.fetch(choice.request, policy=policy)
                    source = gutenberg_source.GutenbergStorySource(
                        library, store, routes=routes
                    )
                    namespace = {"source": source}
                    # Redirect only the documented output root; execute both real examples.
                    example = (
                        inspect_example
                        + "\n"
                        + publish_example.replace(
                            'root="migration-output"', f"root={str(root / 'data')!r}"
                        )
                    )
                    exec(compile(example, str(path), "exec"), namespace)
                    report = namespace["report"]
                    self.assertIsNone(report["rejection"])
                    self.assertEqual(report["body"], live_gather_test.BODY)
                    self.assertEqual(
                        report["provenance"]["original_sha256"], original.sha256
                    )
                    self.assertEqual(namespace["story_id"], 84)
                    self.assertIsNone(namespace["rejection"])
                    output = pathlib.Path(namespace["path"])
                    saved = output.read_bytes()
                    self.assertEqual(json.loads(saved)["body"], report["body"])
                    # Repeating the documented workflow preserves published output.
                    exec(compile(example, str(path), "exec"), namespace)
                    self.assertEqual(output.read_bytes(), saved)

    def test_catalog_reference_python_blocks(self):
        path = DOCS / "reference/gettenberg-catalog.md"
        blocks = re.findall(
            r"```python\n(.*?)```", path.read_text(encoding="utf-8"), re.S
        )
        self.assertEqual(len(blocks), 2)
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            archive = root / "fixture.tar.bz2"
            candidate = root / "candidate.sqlite"
            fixture = catalog_test.FIXTURES / "pg84.rdf"
            archive.write_bytes(
                catalog_test.archive_bytes(
                    [(fixture.name, fixture.read_bytes(), tarfile.REGTYPE)]
                )
            )
            namespace = {}
            with mock.patch.object(
                socket, "socket", side_effect=AssertionError("network forbidden")
            ):
                for block in blocks:
                    code = block.replace(
                        '"/path/to/rdf-files.tar.bz2"', repr(str(archive))
                    ).replace('"/path/to/new-candidate.sqlite"', repr(str(candidate)))
                    exec(compile(code, str(path), "exec"), namespace)
            self.assertEqual(namespace["report"].status, "complete")
            self.assertEqual(namespace["book"].ebook.gutenberg_id, 84)
            self.assertEqual(namespace["matches"], (84,))

    def test_record_reference_entry_point(self):
        path = DOCS / "reference/gettenberg-records.md"
        blocks = re.findall(
            r"```python\n(.*?)```", path.read_text(encoding="utf-8"), re.S
        )
        self.assertEqual(len(blocks), 1)
        namespace = {"raw_bytes": (catalog_test.FIXTURES / "pg84.rdf").read_bytes()}
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ):
            exec(compile(blocks[0], str(path), "exec"), namespace)
        self.assertEqual(namespace["book"].gutenberg_id, 84)

    def test_preparation_how_to_commands_with_local_sources(self):
        path = DOCS / "how-to/gettenberg-preparation.md"
        blocks = re.findall(
            r"```bash\n(.*?)```", path.read_text(encoding="utf-8"), re.S
        )
        commands = [line for block in blocks for line in block.splitlines() if line]
        self.assertEqual(len(commands), 14)
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            cache = root / "cache"
            archive = root / "fixture.tar.bz2"
            body = catalog_test.archive_bytes(
                [("pg84.rdf", catalog_test.record(84, "Example"), tarfile.REGTYPE)]
            )
            archive.write_bytes(body)
            client = mock.Mock()
            client.open.side_effect = (
                lambda *args, **kwargs: resources_test.MemoryResponse(body=body)
            )
            first_generation = None
            with (
                mock.patch.dict(os.environ, LCATS_CACHE_DIR=str(cache)),
                mock.patch.object(sys, "stdin", io.StringIO()),
                mock.patch.object(
                    socket, "socket", side_effect=AssertionError("network forbidden")
                ),
                mock.patch.object(_resource_transport, "opener", return_value=client),
                mock.patch.object(_resource_transport, "time", resources_test.Clock()),
                capture.capture_output(),
            ):
                for command in commands:
                    tokens = shlex.split(command)
                    arguments = [
                        (
                            str(archive)
                            if token == "/path/to/rdf-files.tar.bz2"
                            else (
                                "https://fixture.invalid/archive"
                                if token == "$ARCHIVE_URL"
                                else token
                            )
                        )
                        for token in tokens[2:]
                    ]
                    message, code = cli.dispatch(tokens[1], arguments)
                    expected = 2 if command.endswith("--offline") else 0
                    self.assertEqual(code, expected, (command, message))
                    if code == 2:
                        self.assertFalse(cache.exists())
                    if command.endswith("--offline --yes"):
                        first_generation = json.loads(message)["generation_id"]
                    if command == 'lcats catalog refresh --url "$ARCHIVE_URL"':
                        self.assertEqual(
                            json.loads(message)["generation_id"], first_generation
                        )
                    if command == "lcats catalog rebuild":
                        self.assertNotEqual(
                            json.loads(message)["generation_id"], first_generation
                        )
                self.assertEqual(
                    lifecycle.CatalogManager(cache).status()["state"], "ready"
                )

    def test_catalog_how_to_python_recovery_and_acquisition(self):
        path = DOCS / "how-to/gettenberg-catalog.md"
        blocks = re.findall(
            r"```python\n(.*?)```", path.read_text(encoding="utf-8"), re.S
        )
        self.assertEqual(len(blocks), 2)
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            cache = root / "cache"
            archive = root / "one.tar.bz2"
            newer = root / "two.tar.bz2"
            one = ("pg1.rdf", catalog_test.record(1, "One"), tarfile.REGTYPE)
            two = ("pg2.rdf", catalog_test.record(2, "Two"), tarfile.REGTYPE)
            archive.write_bytes(catalog_test.archive_bytes([one]))
            body = catalog_test.archive_bytes([one, two])
            newer.write_bytes(body)
            manager = lifecycle.CatalogManager(cache)
            namespace = {
                "manager": manager,
                "cache_dir": cache,
                "new_archive_path": newer,
                "archive_url": "https://fixture.invalid/archive",
                "policy": resources.NetworkPolicy(
                    online=True, allowed_origins=("https://fixture.invalid",)
                ),
            }
            client = mock.Mock()
            client.open.side_effect = (
                lambda *args, **kwargs: resources_test.MemoryResponse(body=body)
            )
            with (
                mock.patch.object(
                    socket, "socket", side_effect=AssertionError("network forbidden")
                ),
                mock.patch.object(_resource_transport, "opener", return_value=client),
                mock.patch.object(_resource_transport, "time", resources_test.Clock()),
            ):
                manager.setup(archive)
                for block in blocks:
                    exec(compile(block, str(path), "exec"), namespace)
                self.assertEqual(
                    (namespace["old_count"], namespace["new_count"]), (1, 2)
                )
                self.assertTrue(namespace["updated"].reused)
                with manager.open() as library:
                    self.assertEqual(library.find_ids(), (1, 2))

    def test_gather_how_to_commands_with_fixture_sources(self):
        path = DOCS / "how-to/gettenberg-gather.md"
        blocks = re.findall(
            r"```bash\n(.*?)```", path.read_text(encoding="utf-8"), re.S
        )
        commands = [
            line
            for block in blocks
            for line in block.replace("\\\n", " ").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        variables = {}
        body = catalog_test.archive_bytes(
            [("fixture.rdf", live_gather_test.fixture_record(), tarfile.REGTYPE)]
        )
        client = mock.Mock()
        client.open.side_effect = (
            lambda request, **kwargs: resources_test.MemoryResponse(
                body=(
                    body
                    if request.full_url.endswith(".tar.bz2")
                    else live_gather_test.ENVELOPE.encode("utf-8")
                )
            )
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            cache = root / "cache"
            with (
                contextlib.chdir(root),
                mock.patch.dict(
                    os.environ,
                    LCATS_CACHE_DIR=str(cache),
                    LCATS_DATA_DIR=str(root / "data"),
                ),
                mock.patch.object(sys, "stdin", io.StringIO()),
                mock.patch.object(
                    socket, "socket", side_effect=AssertionError("network forbidden")
                ),
                mock.patch.object(_resource_transport, "opener", return_value=client),
                mock.patch.object(_resource_transport, "time", resources_test.Clock()),
                mock.patch.object(
                    storymap, "SINGLE_STORIES", [live_gather_test.BOOK_ID]
                ),
                mock.patch.object(
                    sherlock, "ADVENTURES_HEADINGS", [("fixture", "FIXTURE", "Fixture")]
                ),
                mock.patch.object(
                    downloaders,
                    "load_page",
                    return_value="<h2>FIXTURE</h2><p>A simple story.</p>",
                ),
                capture.capture_output(),
            ):
                # The general walkthrough uses already-clean fixture outputs.
                # The separate review CLI guide is exercised below.
                executed = 0
                for command in commands:
                    tokens = shlex.split(command)
                    if tokens[0] == "export":
                        name, value = tokens[1].split("=", 1)
                        variables["$" + name] = value
                        continue
                    self.assertEqual(tokens[:2], ["lcats", "gather"])
                    arguments = [
                        (
                            str(cache)
                            if token == "/path/to/cache"
                            else variables.get(token, token)
                        )
                        for token in tokens[2:]
                    ]
                    message, code = cli.dispatch("gather", arguments)
                    expected = 2 if command == "lcats gather mass_quantities" else 0
                    self.assertEqual(code, expected, (command, message))
                    executed += 1
                self.assertEqual(executed, 9)
                outputs = sorted((root / "data").glob("*/*/story.json"))
                self.assertEqual(len(outputs), 2)
                mass_output = next(
                    path
                    for path in outputs
                    if path.parent.parent.name == "mass_quantities"
                )
                self.assertEqual(
                    json.loads(mass_output.read_text())["body"], live_gather_test.BODY
                )

    def test_ci_maintenance_preview_command_examples(self):
        path = DOCS / "how-to/gettenberg-ci-maintenance.md"
        blocks = re.findall(
            r"```bash\n(.*?)```", path.read_text(encoding="utf-8"), re.S
        )
        self.assertEqual(len(blocks), 2)
        commands = blocks[0].splitlines()
        self.assertEqual(len(commands), 4)
        with tempfile.TemporaryDirectory() as temporary:
            cache = pathlib.Path(temporary) / "cache"

            def github_inventory(arguments, **kwargs):
                self.assertEqual(arguments[:2], ["gh", "api"])
                return subprocess.CompletedProcess(
                    arguments, 0, json.dumps([{"actions_caches": []}]), ""
                )

            with (
                mock.patch.dict(os.environ, LCATS_CACHE_DIR=str(cache)),
                mock.patch.object(
                    socket, "socket", side_effect=AssertionError("network forbidden")
                ),
                mock.patch.object(subprocess, "run", side_effect=github_inventory),
                capture.capture_output(),
            ):
                for command in commands:
                    tokens = shlex.split(command)
                    self.assertEqual(tokens[:2], ["python", "tools/gettenberg_ci.py"])
                    arguments = [
                        str(cache) if token == "/tmp/lcats-catalog-preview" else token
                        for token in tokens[2:]
                    ]
                    if arguments == ["--help"]:
                        with self.assertRaises(SystemExit) as exited:
                            gettenberg_ci.main(arguments)
                        self.assertEqual(exited.exception.code, 0)
                    else:
                        self.assertEqual(gettenberg_ci.main(arguments), 0)
            self.assertFalse(cache.exists())
