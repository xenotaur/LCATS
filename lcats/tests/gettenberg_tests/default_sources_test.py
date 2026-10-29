"""CLI defaults through real catalogs and gathering; only I/O boundaries are fake.

Reuse the authored single-story fixture to test actual publication, cache reuse,
approval and transport policy without contacting Gutenberg or writing user data.
"""

import io
import json
import socket
import sys
import unittest
from unittest import mock

from lcats import cli
from lcats.gatherers import main
from lcats.gatherers.sherlock import gatherer as sherlock
from lcats.gettenberg import _resource_transport
from lcats.gettenberg import catalog_cli
from lcats.gettenberg import sources_cli
from lcats.utils import capture
from lcats.utils import names
from tests.gatherers_tests import live_gather_test
from tests.gettenberg_tests import preparation_test
from tests.gettenberg_tests import resources_test


class DefaultSourceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = live_gather_test.LiveGatherTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.cache = self.fixture.cache
        # Every test also blocks accidental real traffic outside the fake opener.
        patch = mock.patch.object(
            socket, "socket", side_effect=AssertionError("network")
        )
        patch.start()
        self.addCleanup(patch.stop)

    def gather(self, *arguments):
        """Exercise argparse and dispatch, not just the source resolver."""
        with capture.capture_output():
            return cli.dispatch("gather", ["--cache-dir", str(self.cache), *arguments])

    def catalog(self, command, *arguments):
        text, code = cli.dispatch(
            "catalog", [command, "--cache-dir", str(self.cache), *arguments]
        )
        return json.loads(text), code

    def client(self, *, story=True):
        client = mock.Mock()
        replies = [
            resources_test.MemoryResponse(body=self.fixture.archive.read_bytes())
        ]
        if story:
            replies.append(
                resources_test.MemoryResponse(
                    body=live_gather_test.ENVELOPE.encode(),
                    headers=(("Content-Type", "text/plain; charset=utf-8"),),
                )
            )
        client.open.side_effect = replies
        return client

    def test_default_first_use_downloads_then_reuses_without_refresh(self):
        client = self.client()
        with mock.patch.object(_resource_transport, "opener", return_value=client):
            message, code = self.gather("mass_quantities", "--yes")
        self.assertEqual(code, 0, message)
        self.assertEqual(
            [call.args[0].full_url for call in client.open.call_args_list],
            [
                sources_cli.CATALOG_URL,
                sources_cli.GENERATED_ROOT + "990001/pg990001.txt",
            ],
        )
        output = next(self.fixture.data.rglob("story.json"))
        before = output.read_bytes()
        self.assertEqual(json.loads(before)["body"], live_gather_test.BODY)
        with mock.patch.object(
            _resource_transport, "opener", side_effect=AssertionError("refetch")
        ):
            message, code = self.gather("mass_quantities", "--offline", "--yes")
        self.assertEqual(code, 0, message)
        self.assertEqual(before, output.read_bytes())
        self.assertEqual(len(self.fixture.manager.status()["generations"]), 1)

    def test_default_setup_and_gather_report_same_source_without_writes(self):
        with mock.patch.object(
            sys, "stdin", preparation_test.Terminal("yes\n")
        ) as terminal:
            report, code = self.catalog("setup", "--dry-run")
            message, gather_code = self.gather("--dry-run")
            self.assertEqual(terminal.tell(), 0)
        self.assertEqual((code, gather_code), (0, 0))
        self.assertEqual(report["source"], sources_cli.CATALOG_URL)
        self.assertTrue(report["approval_required"])
        self.assertEqual(report["allowed_origins"], ["https://www.gutenberg.org"])
        for url in (
            sources_cli.CATALOG_URL,
            sources_cli.MAIN_ROOT,
            sources_cli.GENERATED_ROOT,
        ):
            self.assertIn(url, message)
        self.assertIn("Permitted origins:", message)
        self.assertFalse(self.cache.exists())
        self.assertFalse(self.fixture.data.exists())

    def test_default_first_setup_requires_unattended_or_interactive_approval(self):
        for terminal in (io.StringIO("yes\n"), preparation_test.Terminal("no\n")):
            with mock.patch.object(sys, "stdin", terminal):
                message, code = self.gather("mass_quantities")
            self.assertEqual(code, 2, message)
            self.assertFalse(self.cache.exists())
        client = self.client(story=False)
        with (
            mock.patch.object(sys, "stdin", preparation_test.Terminal("yes\n")),
            mock.patch.object(sys, "stderr", io.StringIO()) as prompt,
            mock.patch.object(_resource_transport, "opener", return_value=client),
        ):
            report, code = self.catalog("setup")
        self.assertEqual(code, 0, report)
        self.assertIn(sources_cli.CATALOG_URL, prompt.getvalue())
        self.assertFalse(report["reused"])

    def test_offline_default_miss_is_blocked_even_with_yes(self):
        message, code = self.gather("mass_quantities", "--offline", "--yes")
        self.assertEqual(code, 2)
        self.assertIn("offline", message.lower())
        report, code = self.catalog("setup", "--offline", "--yes")
        self.assertEqual(code, 2)
        self.assertIn("offline", report["error"].lower())
        self.assertFalse(self.cache.exists())

    def test_explicit_local_source_does_not_permit_default_archive_origin(self):
        service, routes, policy = main._services(
            self.cache, self.fixture.archive, None, None, None, (), False
        )
        self.assertIsNone(service.request)
        self.assertEqual(service.archive, self.fixture.archive)
        self.assertEqual(policy.allowed_origins, ("https://gutenberg.pglaf.org",))
        self.assertEqual(routes.main_root, sources_cli.MAIN_ROOT)
        report, code = self.catalog(
            "setup", "--archive", str(self.fixture.archive), "--dry-run"
        )
        self.assertEqual(code, 0)
        self.assertFalse(report["online"])
        self.assertEqual(report["allowed_origins"], [])
        self.assertFalse(self.cache.exists())

    def test_explicit_url_and_root_pair_replace_defaults_independently(self):
        service, routes, policy = main._services(
            self.cache,
            None,
            "https://archive.invalid/rdf",
            "https://books.invalid/main/",
            "https://generated.invalid/",
            ("https://redirect.invalid",),
            False,
        )
        self.assertEqual(service.request.request_url, "https://archive.invalid/rdf")
        self.assertEqual(routes.generated_root, "https://generated.invalid/")
        self.assertEqual(
            set(policy.allowed_origins),
            {
                "https://archive.invalid",
                "https://books.invalid",
                "https://generated.invalid",
                "https://redirect.invalid",
            },
        )
        report, code = self.catalog(
            "setup", "--url", "https://archive.invalid/rdf", "--dry-run"
        )
        self.assertEqual(code, 0)
        self.assertEqual(report["source"], "https://archive.invalid/rdf")
        self.assertNotIn("gutenberg", str(report))

    def test_half_root_override_rejected_before_setup(self):
        for flag in ("--gutenberg-main-root", "--gutenberg-generated-root"):
            message, code = self.gather(
                "mass_quantities", flag, "https://mirror.invalid/", "--yes"
            )
            self.assertEqual(code, 2)
            self.assertIn("both", message)
        self.assertFalse(self.cache.exists())

    def test_denied_default_archive_never_tries_another_endpoint(self):
        client = mock.Mock()
        client.open.return_value = resources_test.MemoryResponse(status=403)
        with mock.patch.object(_resource_transport, "opener", return_value=client):
            message, code = self.gather("mass_quantities", "--yes")
        self.assertEqual(code, 2, message)
        self.assertEqual(client.open.call_count, 1)
        self.assertEqual(
            client.open.call_args.args[0].full_url, sources_cli.CATALOG_URL
        )
        self.assertEqual(self.fixture.manager.status()["state"], "missing")
        self.assertFalse(self.fixture.data.exists())

    def test_unpermitted_default_redirect_does_not_fetch_target(self):
        client = mock.Mock()
        client.open.return_value = resources_test.MemoryResponse(
            status=302, headers=(("Location", "https://unlisted.invalid/rdf"),)
        )
        with mock.patch.object(_resource_transport, "opener", return_value=client):
            report, code = self.catalog("setup", "--yes")
        self.assertEqual(code, 2, report)
        self.assertEqual(client.open.call_count, 1)
        self.assertEqual(self.fixture.manager.status()["state"], "missing")

    def test_curated_only_does_not_resolve_sources_even_with_partial_root(self):
        with mock.patch.object(
            sources_cli, "catalog_request", side_effect=AssertionError("catalog")
        ):
            message, code = self.gather(
                "sherlock",
                "--dry-run",
                "--gutenberg-main-root",
                "https://ignored.invalid/",
            )
        self.assertEqual(code, 0, message)
        self.assertIn("No metadata catalog", message)
        self.assertFalse(self.cache.exists())

    def test_mixed_default_collections_reuse_both_caches_offline(self):
        client = self.client()
        with mock.patch.object(_resource_transport, "opener", return_value=client):
            message, code = self.gather("mass_quantities", "--yes")
        self.assertEqual(code, 0, message)
        html_cache = self.cache / "resources"
        html_cache.mkdir()
        (html_cache / names.url_to_filename(sherlock.ADVENTURES_GUTENBERG)).write_text(
            "<h2>FIXTURE</h2><p>Curated story.</p><h2>NEXT</h2>", encoding="utf-8"
        )
        with mock.patch.object(
            sherlock, "ADVENTURES_HEADINGS", [("fixture", "FIXTURE", "Fixture")]
        ):
            message, code = self.gather("sherlock", "mass_quantities", "--offline")
        self.assertEqual(code, 0, message)
        self.assertEqual(len(list(self.fixture.data.rglob("story.json"))), 2)
        self.assertEqual(
            json.loads((self.fixture.data / "sherlock/fixture/story.json").read_text())[
                "body"
            ],
            "Curated story.",
        )

    def test_status_rebuild_and_refresh_do_not_acquire_default_source(self):
        for command in ("status", "rebuild"):
            args = catalog_cli.build_parser().parse_args(
                [command, "--cache-dir", str(self.cache)]
            )
            service = catalog_cli._preparation(args)
            self.assertIsNone(service.request)
            self.assertFalse(service.policy.online)
        with (
            mock.patch.object(sys, "stderr", io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            catalog_cli.build_parser().parse_args(["refresh"])
