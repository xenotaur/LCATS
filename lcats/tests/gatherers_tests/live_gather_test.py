"""Authored end-to-end migration fixtures; no live Gutenberg access.

Only HTTP responses, terminal input and collection definitions are substituted.
The catalog, resource store, decoder, cleanup, parser, normalization and output
publication run for real in temporary directories. Fresh-process tests forbid
legacy imports to catch import-order dependencies hidden by the full suite.
"""

import contextlib
import hashlib
import io
import json
import os
import pathlib
import socket
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

from lcats.gatherers import downloaders
from lcats.gatherers import gutenberg_source
from lcats.gatherers import main
from lcats.gatherers import parser
from lcats.gatherers import overrides
from lcats.gatherers.sherlock import gatherer as sherlock
from lcats.gatherers import story_output
from lcats.gatherers.mass_quantities import storymap
from lcats.gettenberg import _resource_transport
from lcats.gettenberg import lifecycle
from lcats.gettenberg import resources
from lcats.utils import capture
from lcats.utils import names
from tests.gettenberg_tests import catalog_test
from tests.gettenberg_tests import preparation_test
from tests.gettenberg_tests import resources_test

BOOK_ID = 990001
SOURCE_URI = f"https://www.gutenberg.org/ebooks/{BOOK_ID}.txt.utf-8"
ORIGIN = "https://fixture.invalid"
MAIN_ROOT = ORIGIN + "/main/"
GENERATED_ROOT = ORIGIN + "/generated/"
PARAGRAPHS = [
    f"Paragraph {i}: the travelers waited beside the quiet river and watched the boats."
    for i in range(15)
]
BODY = "\n\n".join(PARAGRAPHS)
CONTENT = "The Bell\n\nJohn Smith\n\n" + BODY
ENVELOPE = (
    "The Project Gutenberg eBook of The Bell\n\n"
    "*** START OF THE PROJECT GUTENBERG EBOOK THE BELL ***\n\n"
    + CONTENT
    + "\n\n*** END OF THE PROJECT GUTENBERG EBOOK THE BELL ***\n\n"
    "THE FULL PROJECT GUTENBERG LICENSE\n"
)


def fixture_record(*, language="en", media_type="text/plain; charset=utf-8"):
    """Small RDF with author/translator distinction and an explicit resource."""
    return catalog_test.record(
        BOOK_ID,
        "The Bell",
        f"""
        <dc:alternative>Another title</dc:alternative>
        <dc:creator><pg:agent rdf:about="2009/agents/1">
          <pg:name>Smith, John</pg:name><pg:alias>J. Smith</pg:alias>
        </pg:agent></dc:creator>
        <rel:trl><pg:agent rdf:about="2009/agents/2">
          <pg:name>Translator, Jane</pg:name><pg:alias>Jane T.</pg:alias>
        </pg:agent></rel:trl>
        <dc:language><rdf:Description><rdf:value>{language}</rdf:value></rdf:Description></dc:language>
        <dc:subject><rdf:Description><rdf:value>PS</rdf:value></rdf:Description></dc:subject>
        <dc:subject><rdf:Description><rdf:value>Short stories</rdf:value></rdf:Description></dc:subject>
        <dc:hasFormat><pg:file rdf:about="{SOURCE_URI}">
          <dc:format><rdf:Description><rdf:value>{media_type}</rdf:value></rdf:Description></dc:format>
        </pg:file></dc:hasFormat>
        """,
    )


class LiveGatherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve()
        self.cache = self.root / "cache"
        self.data = self.root / "data"
        self.archive = self.root / "fixture.tar.bz2"
        self.write_archive()
        self.manager = lifecycle.CatalogManager(self.cache)
        self.store = resources.ResourceStore(self.cache)
        self.routes = resources.GutenbergRoutes(MAIN_ROOT, GENERATED_ROOT)
        self.policy = resources.NetworkPolicy(online=True, allowed_origins=(ORIGIN,))
        self.clock = resources_test.Clock()
        for patch in (
            mock.patch.object(_resource_transport, "time", self.clock),
            mock.patch.dict(os.environ, LCATS_DATA_DIR=str(self.data)),
            mock.patch.object(storymap, "SINGLE_STORIES", [BOOK_ID]),
        ):
            patch.start()
            self.addCleanup(patch.stop)
        # Keep legacy run logs away from both the checkout and the data tree.
        self.cwd = contextlib.chdir(self.root)
        self.cwd.__enter__()
        self.addCleanup(self.cwd.__exit__, None, None, None)

    def write_archive(self, **kwargs):
        self.archive.write_bytes(
            catalog_test.archive_bytes(
                [("fixture.rdf", fixture_record(**kwargs), tarfile.REGTYPE)]
            )
        )

    def source(self, *, online=False):
        self.manager.setup(self.archive)
        library = self.manager.open()
        self.addCleanup(library.close)
        return gutenberg_source.GutenbergStorySource(
            library,
            self.store,
            routes=self.routes,
            policy=self.policy if online else resources.NetworkPolicy(),
        )

    def acquire(self, body=ENVELOPE.encode()):
        """Seed a real request/receipt/blob chain through the HTTP boundary."""
        source = self.source(online=True)
        metadata = source.metadata(BOOK_ID)
        selected = resources.select_routable_resource(
            metadata.ebook, routes=self.routes
        )
        client = mock.Mock()
        client.open.return_value = resources_test.MemoryResponse(
            body=body, headers=(("Content-Type", "text/plain; charset=utf-8"),)
        )
        with mock.patch.object(_resource_transport, "opener", return_value=client):
            artifact = self.store.fetch(selected.request, policy=self.policy)
        return source, artifact

    def run_gather(self, **kwargs):
        """Run the real CLI-facing coordinator, supplying explicit test routes."""
        options = dict(
            cache_dir=self.cache,
            catalog_archive=self.archive,
            main_root=MAIN_ROOT,
            generated_root=GENERATED_ROOT,
            offline=True,
        )
        options.update(kwargs)
        with capture.capture_output():
            return main.run(["mass_quantities"], **options)

    def test_inspection_matches_gathered_body_without_writing_output(self):
        source, artifact = self.acquire()
        source.policy = resources.NetworkPolicy()
        report = parser.inspect_story(BOOK_ID, source=source)
        self.assertIsNone(report["rejection"])
        self.assertEqual(report["body"], BODY)
        self.assertEqual(report["provenance"]["original_sha256"], artifact.sha256)
        self.assertEqual(report["metadata"]["aliases"], ["J. Smith"])
        json.dumps(report)
        self.assertFalse(self.data.exists())
        self.run_gather()
        output = next(self.data.rglob("story.json"))
        self.assertEqual(json.loads(output.read_text())["body"], report["body"])

    def test_inspection_missing_and_ineligible_records_do_not_acquire(self):
        self.write_archive(language="fr")
        source = self.source()
        missing = parser.inspect_story(999999, source=source)
        rejected = parser.inspect_story(BOOK_ID, source=source)
        self.assertIn("No data", missing["rejection"])
        self.assertIn("not suitable", rejected["rejection"])
        self.assertIsNone(missing["body"])
        self.assertIsNone(rejected["provenance"])
        self.assertFalse(self.data.exists())

    def test_short_body_is_reported_and_never_published(self):
        source, _ = self.acquire(b"The Bell\n\nJohn Smith\n\nA short story.")
        source.policy = resources.NetworkPolicy()
        report = parser.inspect_story(BOOK_ID, source=source)
        self.assertIn("too short", report["rejection"])
        self.assertIn("short story", report["body"])
        self.run_gather()
        self.assertEqual(list(self.data.rglob("story.json")), [])

    def test_chaptered_body_is_reported_and_never_published(self):
        content = (
            "The Bell\n\nJohn Smith\n\nChapter I\n\n"
            + BODY
            + "\n\nChapter II\n\n"
            + BODY
        )
        source, _ = self.acquire(content.encode())
        source.policy = resources.NetworkPolicy()
        report = parser.inspect_story(BOOK_ID, source=source)
        self.assertIn("chapters", report["rejection"])
        self.run_gather()
        self.assertEqual(list(self.data.rglob("story.json")), [])

    def test_projection_preserves_author_roles_order_and_missing_record(self):
        source = self.source()
        record = source.metadata(BOOK_ID)
        self.assertEqual(record.titles, ("The Bell",))
        self.assertEqual(record.authors, ("Smith, John",))
        self.assertEqual(record.aliases, ("J. Smith",))
        self.assertEqual(record.subjects, ("PS", "Short stories"))
        self.assertEqual(record.languages, ("en",))
        self.assertEqual(len(record.ebook.contributors), 2)
        self.assertIsNone(source.metadata(BOOK_ID + 1))

    def test_offline_derivation_and_output_preserve_body_bucket_and_provenance(self):
        _, artifact = self.acquire()
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network")):
            message, code = self.run_gather()
        self.assertEqual(code, 0, message)
        outputs = list(self.data.rglob("story.json"))
        self.assertEqual(len(outputs), 1)
        output = outputs[0]
        slug = pathlib.Path(
            names.title_and_author_to_filename(
                "The Bell", ["Smith, John"], ext=".json", max_len=50
            )
        ).stem
        self.assertEqual(output.parent.name, slug)
        self.assertEqual(output.parent.parent.name, storymap.TARGET_DIRECTORY)
        result = json.loads(output.read_text())
        self.assertEqual(result["body"], BODY)
        self.assertEqual(result["name"], "The Bell")
        self.assertEqual(result["author"], ["Smith, John"])
        provenance = result["metadata"]["gettenberg"]
        self.assertEqual(result["metadata"]["url"], SOURCE_URI)
        self.assertEqual(provenance["original_sha256"], artifact.sha256)
        self.assertEqual(provenance["receipt_sha256"], artifact.receipt_sha256)
        self.assertEqual(provenance["encoding"], "utf-8")
        self.assertEqual(artifact.path.read_bytes(), ENVELOPE.encode())
        self.assertNotIn("Project Gutenberg", result["body"])
        self.assertEqual(len(self.manager.status()["generations"]), 1)

    def test_physical_line_endings_preserve_extracted_body_and_original_bytes(self):
        for newline in ("\r\n", "\r"):
            with self.subTest(newline=newline):
                case = LiveGatherTests()
                case.setUp()
                try:
                    raw = ENVELOPE.replace("\n", newline).encode()
                    _, artifact = case.acquire(raw)
                    message, code = case.run_gather()
                    self.assertEqual(code, 0, message)
                    outputs = list(case.data.rglob("story.json"))
                    self.assertEqual(len(outputs), 1)
                    self.assertEqual(json.loads(outputs[0].read_text())["body"], BODY)
                    self.assertEqual(artifact.path.read_bytes(), raw)
                finally:
                    case.doCleanups()

    def test_online_first_use_acquires_archive_and_story_once(self):
        client = mock.Mock()
        client.open.side_effect = [
            resources_test.MemoryResponse(body=self.archive.read_bytes()),
            resources_test.MemoryResponse(
                body=ENVELOPE.encode(),
                headers=(("Content-Type", "text/plain; charset=utf-8"),),
            ),
        ]
        with mock.patch.object(_resource_transport, "opener", return_value=client):
            message, code = self.run_gather(
                catalog_archive=None,
                catalog_url=ORIGIN + "/rdf.tar.bz2",
                offline=False,
                yes=True,
            )
        self.assertEqual(code, 0, message)
        self.assertEqual(client.open.call_count, 2)
        self.assertEqual(len(list(self.data.rglob("story.json"))), 1)
        self.assertEqual(self.manager.status()["state"], "ready")
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network")):
            self.assertEqual(self.run_gather(yes=True)[1], 0)

    def test_existing_output_reuses_without_source_even_when_yes(self):
        self.acquire()
        self.assertEqual(self.run_gather()[1], 0)
        output = next(self.data.rglob("story.json"))
        original = output.read_bytes()
        # Forbid acquisition entirely: an existing output needs no source reads.
        with (
            mock.patch.object(
                _resource_transport, "opener", side_effect=AssertionError("network")
            ),
            mock.patch.object(
                resources.ResourceStore,
                "fetch",
                side_effect=AssertionError("source reuse unnecessary"),
            ),
        ):
            self.assertEqual(self.run_gather(yes=True)[1], 0)
        self.assertEqual(output.read_bytes(), original)
        self.assertEqual(len(self.manager.status()["generations"]), 1)

    def test_missing_offline_source_aborts_with_no_story_and_log(self):
        self.manager.setup(self.archive)
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network")):
            message, code = self.run_gather()
        self.assertEqual(code, 2)
        self.assertIn("offline", message.lower())
        self.assertFalse(list(self.data.rglob("story.json")))
        log = next((self.root / "logs").rglob("*.jsonl")).read_text()
        self.assertIn("run_aborted_unexpected", log)
        self.assertNotIn("story_ready", log)

    def test_strict_decode_and_ambiguous_cleanup_keep_original_and_fail(self):
        for body in (
            b"invalid utf8 \xff",
            ENVELOPE.replace("*** END OF", "*** START OF").encode(),
        ):
            with self.subTest(body=body[:30]):
                # Each case needs an isolated cache because fetch deliberately never refreshes.
                self.cache = self.root / hashlib.sha256(body).hexdigest()
                self.manager = lifecycle.CatalogManager(self.cache)
                self.store = resources.ResourceStore(self.cache)
                _, artifact = self.acquire(body)
                message, code = self.run_gather()
                self.assertEqual(code, 2, message)
                self.assertEqual(artifact.path.read_bytes(), body)
                self.assertFalse(list(self.data.rglob("story.json")))

    def seed_batch(self, middle_body):
        """Create three independent sources through the real catalog/cache boundary."""
        books = [BOOK_ID, BOOK_ID + 1, BOOK_ID + 2]
        entries = []
        for index, book in enumerate(books):
            raw = fixture_record().replace(str(BOOK_ID).encode(), str(book).encode())
            raw = raw.replace(b"The Bell", f"The Bell {index}".encode())
            entries.append((f"{book}.rdf", raw, tarfile.REGTYPE))
        self.archive.write_bytes(catalog_test.archive_bytes(entries))
        source = self.source(online=True)
        for index, book in enumerate(books):
            body = ENVELOPE.replace("The Bell", f"The Bell {index}").encode()
            if index == 1:
                body = middle_body
            selected = resources.select_routable_resource(
                source.metadata(book).ebook, routes=self.routes
            )
            client = mock.Mock()
            client.open.return_value = resources_test.MemoryResponse(
                body=body, headers=(("Content-Type", "text/plain; charset=utf-8"),)
            )
            with mock.patch.object(_resource_transport, "opener", return_value=client):
                self.store.fetch(selected.request, policy=self.policy)
        return books

    def test_refusal_continues_cli_batch_and_repeat_preserves_both_outputs(self):
        books = self.seed_batch(ENVELOPE.replace("*** END OF", "*** START OF").encode())
        with (
            mock.patch.object(storymap, "SINGLE_STORIES", books),
            mock.patch.object(socket, "socket", side_effect=AssertionError("network")),
        ):
            message, code = self.run_gather()
            self.assertEqual(code, 2)
            self.assertIn("Gathering incomplete", message)
            self.assertIn(
                "2 ready (written or reused), 0 skipped, 1 cleanup refused", message
            )
            outputs = {p: p.read_bytes() for p in self.data.rglob("story.json")}
            self.assertEqual(len(outputs), 2)
            self.assertEqual(
                {
                    json.loads(raw)["metadata"]["gettenberg"]["gutenberg_id"]
                    for raw in outputs.values()
                },
                {books[0], books[2]},
            )
            self.assertEqual(self.run_gather(), (message, code))
            self.assertEqual({p: p.read_bytes() for p in outputs}, outputs)
        log = self.root / "logs/gather/mass_quantities_gather_run_log.jsonl"
        rows = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(
            [row["event"] for row in rows[:6]],
            [
                "run_start",
                "story_ready",
                "story_cleanup_refused",
                "story_ready",
                "batch_summary",
                "run_end",
            ],
        )
        self.assertEqual(rows[2]["story"], books[1])
        self.assertTrue(rows[4]["incomplete"])

    def test_non_refusal_decode_error_still_aborts_after_written_prefix(self):
        books = self.seed_batch(b"invalid utf8 \xff")
        with mock.patch.object(storymap, "SINGLE_STORIES", books):
            message, code = self.run_gather()
        self.assertEqual(code, 2)
        self.assertIn("Gathering failed", message)
        outputs = list(self.data.rglob("story.json"))
        self.assertEqual(len(outputs), 1)
        self.assertEqual(
            json.loads(outputs[0].read_text())["metadata"]["gettenberg"][
                "gutenberg_id"
            ],
            books[0],
        )
        rows = [
            json.loads(line)
            for line in (self.root / "logs/gather/mass_quantities_gather_run_log.jsonl")
            .read_text()
            .splitlines()
        ]
        self.assertEqual(
            [row["event"] for row in rows],
            ["run_start", "story_ready", "run_aborted_unexpected"],
        )

    def test_empty_and_ineligible_selections_are_complete_not_refused(self):
        self.write_archive(language="fr")
        self.source()
        for books, skipped in (([], 0), ([BOOK_ID], 1)):
            with (
                self.subTest(books=books),
                mock.patch.object(storymap, "SINGLE_STORIES", books),
            ):
                message, code = self.run_gather()
                self.assertEqual(code, 0, message)
                self.assertIn(
                    f"0 ready (written or reused), {skipped} skipped, 0 cleanup refused",
                    message,
                )

    def test_metadata_skip_does_not_acquire(self):
        self.write_archive(language="fr")
        source = self.source()
        gatherer = downloaders.DataGatherer("fixture", root=self.data)
        with (
            capture.capture_output(),
            mock.patch.object(socket, "socket", side_effect=AssertionError("network")),
        ):
            _, path, reason = parser.gather_story(gatherer, BOOK_ID, source=source)
        self.assertIsNone(path)
        self.assertIn("Metadata not suitable", reason)
        self.assertFalse(self.data.exists())

    def test_html_only_metadata_never_falls_back(self):
        self.write_archive(media_type="text/html")
        source = self.source()
        with self.assertRaisesRegex(resources.ResourceInputError, "plain-text"):
            source.read(source.metadata(BOOK_ID))

    def test_unattended_declined_and_dry_run_setup_do_not_write(self):
        for terminal, dry_run in (
            (io.StringIO("yes\n"), False),
            (preparation_test.Terminal("no\n"), False),
            (preparation_test.Terminal("yes\n"), True),
        ):
            with (
                self.subTest(dry_run=dry_run, terminal=type(terminal)),
                mock.patch.object(sys, "stdin", terminal),
            ):
                _, code = self.run_gather(dry_run=dry_run)
                self.assertEqual(code, 0 if dry_run else 2)
                self.assertFalse(self.cache.exists())
                self.assertFalse(self.data.exists())
                if dry_run:
                    self.assertEqual(terminal.tell(), 0)

    def test_approved_local_setup_happens_once_then_offline_source_miss_fails(self):
        message, code = self.run_gather(yes=True)
        self.assertEqual(code, 2, message)
        self.assertEqual(self.manager.status()["state"], "ready")
        self.assertEqual(len(self.manager.status()["generations"]), 1)
        self.assertFalse(list(self.data.rglob("story.json")))

    def test_interactive_approval_builds_catalog_before_source_miss(self):
        with mock.patch.object(sys, "stdin", preparation_test.Terminal("yes\n")):
            message, code = self.run_gather()
        self.assertEqual(code, 2, message)
        self.assertEqual(self.manager.status()["state"], "ready")

    def test_normalization_and_versioned_override_use_bucket_slug(self):
        raw = ENVELOPE.replace("Paragraph 0:", "Paragraph 0: blas√© eyes;")
        self.acquire(raw.encode())
        slug = pathlib.Path(
            names.title_and_author_to_filename(
                "The Bell", ["Smith, John"], ext=".json", max_len=50
            )
        ).stem
        directory = self.root / "overrides"
        directory.mkdir()
        (directory / f"{storymap.TARGET_DIRECTORY}.json").write_text(
            json.dumps(
                {
                    slug: [
                        {
                            "find": "blasé eyes",
                            "replace": "observant eyes",
                            "rationale": "Authored fixture correction",
                            "reviewer": "test",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        overrides.load_overrides.cache_clear()
        try:
            with mock.patch.object(overrides, "OVERRIDES_DIR", directory):
                message, code = self.run_gather()
            self.assertEqual(code, 0, message)
            output = json.loads(next(self.data.rglob("story.json")).read_text())
            self.assertIn("observant eyes", output["body"])
            proof = output["metadata"]["normalization"]
            self.assertEqual(len(proof["rules_applied"]), 1)
            self.assertEqual(len(proof["overrides_applied"]), 1)
            self.assertIn("gettenberg", output["metadata"])
        finally:
            overrides.load_overrides.cache_clear()

    def test_mixed_collections_share_explicit_cache_and_offline_policy(self):
        self.acquire()
        html_cache = self.cache / "resources"
        html_cache.mkdir()
        path = html_cache / names.url_to_filename(sherlock.ADVENTURES_GUTENBERG)
        path.write_text(
            "<h2>FIXTURE</h2><p>Curated story.</p><h2>NEXT</h2>", encoding="utf-8"
        )
        with (
            capture.capture_output(),
            mock.patch.object(
                sherlock, "ADVENTURES_HEADINGS", [("fixture", "FIXTURE", "Fixture")]
            ),
            mock.patch.object(socket, "socket", side_effect=AssertionError("network")),
        ):
            message, code = main.run(
                ["sherlock", "mass_quantities"],
                cache_dir=self.cache,
                main_root=MAIN_ROOT,
                generated_root=GENERATED_ROOT,
                offline=True,
            )
        self.assertEqual(code, 0, message)
        self.assertEqual(len(list(self.data.rglob("story.json"))), 2)
        self.assertEqual(
            json.loads((self.data / "sherlock/fixture/story.json").read_text())["body"],
            "Curated story.",
        )

    def test_curated_only_missing_offline_source_needs_no_catalog(self):
        with (
            capture.capture_output(),
            mock.patch.object(socket, "socket", side_effect=AssertionError("network")),
        ):
            message, code = main.run(["sherlock"], cache_dir=self.cache, offline=True)
        self.assertEqual(code, 2)
        self.assertIn("offline", message)
        self.assertFalse((self.cache / "gettenberg").exists())
        self.assertFalse(list(self.data.rglob("story.json")))

    def test_partial_routes_and_unknown_selection_fail_before_setup(self):
        self.assertEqual(
            self.run_gather(yes=True, main_root=None, generated_root=GENERATED_ROOT)[1],
            2,
        )
        with capture.capture_output():
            message, code = main.run(
                ["sherlock", "not-a-collection"], cache_dir=self.cache
            )
        self.assertEqual(code, 2, message)
        self.assertFalse(self.cache.exists())
        self.assertFalse(self.data.exists())

    def test_fresh_process_offline_cli_never_imports_legacy(self):
        self.acquire()
        package_root = pathlib.Path(__file__).resolve().parents[2]
        program = r"""
import importlib.abc, socket, ssl, sys
class DenyLegacy(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "gutenbergpy" or fullname.startswith("gutenbergpy.") or fullname in ("lcats.gettenberg.api", "lcats.gettenberg.headers", "lcats.gettenberg.cache"):
            raise AssertionError("legacy import: " + fullname)
sys.meta_path.insert(0, DenyLegacy())
def denied(*args, **kwargs):
    raise AssertionError("network")
socket.socket = denied
from lcats.gatherers.mass_quantities import storymap
storymap.SINGLE_STORIES = [990001]
from lcats import cli
cli.main(sys.argv[1:])
"""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                program,
                "gather",
                "mass_quantities",
                "--offline",
                "--cache-dir",
                str(self.cache),
                "--gutenberg-main-root",
                MAIN_ROOT,
                "--gutenberg-generated-root",
                GENERATED_ROOT,
            ],
            cwd=self.root,
            env={**os.environ, "PYTHONPATH": str(package_root / "src")},
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(list(self.data.rglob("story.json"))), 1)


class StoryPublicationTests(unittest.TestCase):
    def test_complete_json_and_existing_bytes_are_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            path = pathlib.Path(root) / "story.json"
            story_output.publish(path, {"body": "a full story"})
            self.assertEqual(json.loads(path.read_text()), {"body": "a full story"})
            original = path.read_bytes()
            story_output.publish(path, {"body": "replacement"})
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.glob(".story-*")), [])

    def test_serialization_failure_leaves_no_output_or_temporary(self):
        with tempfile.TemporaryDirectory() as root:
            path = pathlib.Path(root) / "story.json"
            with self.assertRaises(TypeError):
                story_output.publish(path, {"body": object()})
            self.assertEqual(list(path.parent.iterdir()), [])

    def test_concurrent_winner_is_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            path = pathlib.Path(root) / "story.json"
            link = os.link

            def concurrent_link(source, destination):
                pathlib.Path(destination).write_bytes(b"concurrent winner")
                return link(source, destination)

            with mock.patch.object(os, "link", side_effect=concurrent_link):
                story_output.publish(path, {"body": "loser"})
            self.assertEqual(path.read_bytes(), b"concurrent winner")
            self.assertEqual(list(path.parent.glob(".story-*")), [])

    def test_symlink_and_directory_outputs_are_refused(self):
        with tempfile.TemporaryDirectory() as root:
            root = pathlib.Path(root)
            (root / "directory").mkdir()
            (root / "symlink").symlink_to(root / "missing")
            for path in (root / "directory", root / "symlink"):
                with self.subTest(path=path), self.assertRaises(OSError):
                    story_output.publish(path, {})


class HtmlOfflineTests(unittest.TestCase):
    def test_offline_hit_and_miss_enforced_at_http_boundary(self):
        with tempfile.TemporaryDirectory() as root:
            cache = downloaders.UrlResourceCache(root=root, offline=True)
            url = "https://fixture.invalid/story.html"
            with self.assertRaises(resources.ResourcePolicyError):
                cache.get(url)
            path = pathlib.Path(cache.full_path(cache.canonicalize(url)))
            path.write_text("<p>cached source</p>", encoding="utf-8")
            with (
                capture.capture_output(),
                mock.patch.object(
                    socket, "socket", side_effect=AssertionError("network")
                ),
            ):
                self.assertEqual(cache.get(url), "<p>cached source</p>")
                with self.assertRaises(resources.ResourcePolicyError):
                    cache.get(url, force=True)
            self.assertEqual(path.read_text(), "<p>cached source</p>")

    def test_runtime_roots_follow_environment(self):
        with (
            tempfile.TemporaryDirectory() as root,
            mock.patch.dict(os.environ, LCATS_CACHE_DIR=root, LCATS_DATA_DIR=root),
        ):
            gatherer = downloaders.DataGatherer("example")
            self.assertEqual(pathlib.Path(gatherer.root), pathlib.Path(root))
            self.assertEqual(
                pathlib.Path(gatherer.cache), pathlib.Path(root) / "resources"
            )
