"""Receipt-to-generation composition over real files and tiny local HTTP fixtures.

Authored RDF archives exercise production ingestion. Forged metadata fixtures
recompute outer hashes deliberately: rejection must come from semantic validation,
not merely the pointer fingerprint. No external Gutenberg service is contacted.
"""

import dataclasses
import doctest
import hashlib
import json
import pathlib
import socket
import sqlite3
import tarfile
import tempfile
import unittest
from unittest import mock

from lcats.gettenberg import _lifecycle_io
from lcats.gettenberg import _resource_transport
from lcats.gettenberg import _resource_types
from lcats.gettenberg import errors
from lcats.gettenberg import ingestion
from lcats.gettenberg import lifecycle
from lcats.gettenberg import resources
from tests.gettenberg_tests import catalog_test
from tests.gettenberg_tests import resources_test


def artifact_fixture(directory, body, **receipt_changes):
    """Author a receipt-bound local input without pretending a live download."""
    digest = hashlib.sha256(body).hexdigest()
    path = directory / (digest + ".tar.bz2")
    path.write_bytes(body)
    request = resources.SourceRequest.from_url(
        "https://fixture.invalid/archive", kind="archive"
    )
    receipt = resources.RetrievalReceipt(
        schema_version=2,
        request_key=request.key,
        source_uri=request.source_uri,
        request_url=request.request_url,
        kind=request.kind,
        route_policy=request.route_policy,
        final_url=request.request_url,
        redirects=(),
        sha256=digest,
        size=len(body),
        retrieved_at="2026-10-15T00:00:00+00:00",
        headers=(("etag", '"fixture"'),),
    )
    receipt = dataclasses.replace(receipt, **receipt_changes)
    return CatalogReceiptTests.with_receipt(
        resources.SourceArtifact(path, digest, len(body), "", receipt), receipt
    )


class CatalogReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.manager = lifecycle.CatalogManager(self.root / "catalog")
        self.body = self.archive([(1, "Original")])
        self.original = self.artifact(self.body)

    @staticmethod
    def archive(books):
        return catalog_test.archive_bytes(
            [
                (f"pg{i}.rdf", catalog_test.record(i, title), tarfile.REGTYPE)
                for i, title in books
            ]
        )

    def artifact(self, body, **receipt_changes):
        return artifact_fixture(self.root, body, **receipt_changes)

    @staticmethod
    def with_receipt(artifact, receipt):
        value = _resource_types.receipt_value(receipt)
        digest = hashlib.sha256(_resource_types.canonical_json(value)).hexdigest()
        return dataclasses.replace(artifact, receipt=receipt, receipt_sha256=digest)

    def rewrite_manifest(self, generation, change):
        """Reseal an adversarial manifest, bypassing only the outer hash check."""
        path = generation.catalog_path.parent / "manifest.json"
        value = json.loads(path.read_text())
        change(value)
        _lifecycle_io.atomic_json(path, value)
        pointer = self.manager.root / "active.json"
        value = json.loads(pointer.read_text())
        value["manifest_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        _lifecycle_io.atomic_json(pointer, value)

    def test_acquired_setup_is_offline_and_retains_self_contained_receipt(self):
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ):
            generation = self.manager.setup(self.original)
            source = generation.manifest["source"]
            self.assertEqual(source["kind"], "acquired_archive")
            self.assertEqual(source["receipt_sha256"], self.original.receipt_sha256)
            self.assertEqual(
                source["receipt"]["sha256"], generation.manifest["archive_sha256"]
            )
            self.assertEqual(
                source["receipt"]["size"], generation.archive_path.stat().st_size
            )
            self.assertEqual(
                hashlib.sha256(
                    _resource_types.canonical_json(source["receipt"])
                ).hexdigest(),
                self.original.receipt_sha256,
            )
            self.original.path.unlink()
            rebuilt = self.manager.rebuild()
            self.assertEqual(rebuilt.manifest["source"], source)
            self.assertNotEqual(rebuilt.generation_id, generation.generation_id)
            with self.manager.open() as reader:
                self.assertEqual(reader.find_ids(), (1,))

    def test_explicit_rebuild_builds_even_identical_acquired_input(self):
        first = self.manager.setup(self.original)
        second = self.manager.rebuild(self.original)
        self.assertFalse(second.reused)
        self.assertNotEqual(first.generation_id, second.generation_id)
        self.assertEqual(first.manifest["source"], second.manifest["source"])

    def test_setup_reuse_still_ignores_unused_input(self):
        first = self.manager.setup(self.original)
        invalid = dataclasses.replace(self.original, receipt_sha256="bad")
        self.assertEqual(self.manager.setup(invalid).generation_id, first.generation_id)

    def test_update_initial_and_identical_preserves_pointer_and_build_receipt(self):
        first = self.manager.update(self.original)
        pointer = (self.manager.root / "active.json").read_bytes()
        refreshed = self.artifact(self.body, retrieved_at="2026-10-15T01:00:00+00:00")
        second = self.manager.update(refreshed)
        self.assertTrue(second.reused)
        self.assertEqual(first.generation_id, second.generation_id)
        self.assertEqual(
            second.manifest["source"]["receipt_sha256"], self.original.receipt_sha256
        )
        self.assertNotEqual(refreshed.receipt_sha256, self.original.receipt_sha256)
        self.assertEqual((self.manager.root / "active.json").read_bytes(), pointer)
        self.assertEqual(self.manager.status()["candidates"], [])
        self.assertEqual(len(self.manager.status()["generations"]), 1)

    def test_changed_same_count_updates_while_reader_stays_pinned(self):
        first = self.manager.update(self.original)
        changed = self.artifact(self.archive([(1, "Changed")]))
        with self.manager.open() as pinned:
            second = self.manager.update(changed)
            self.assertEqual(pinned.get(1).ebook.titles[0].value.text, "Original")
            with self.manager.open() as reader:
                self.assertEqual(reader.get(1).ebook.titles[0].value.text, "Changed")
        self.assertNotEqual(first.generation_id, second.generation_id)
        self.assertEqual(
            second.manifest["source"]["receipt_sha256"], changed.receipt_sha256
        )
        self.assertTrue(first.archive_path.exists())

    def test_changed_count_requires_approval_and_candidate_is_recoverable(self):
        first = self.manager.update(self.original)
        changed = self.artifact(self.archive([(1, "Changed"), (2, "New")]))
        with self.manager.open() as pinned:
            with self.assertRaises(errors.CatalogCountChangeError) as raised:
                self.manager.update(changed)
            self.assertEqual(
                self.manager.status()["active"]["generation_id"], first.generation_id
            )
            self.assertEqual(pinned.find_ids(), (1,))
            accepted = self.manager.activate(
                raised.exception.generation_id, allow_count_change=True
            )
            self.assertEqual(
                accepted.manifest["source"]["receipt_sha256"], changed.receipt_sha256
            )
            self.assertEqual(pinned.find_ids(), (1,))
        with self.manager.open() as reader:
            self.assertEqual(reader.find_ids(), (1, 2))

    def test_update_explicit_approval_and_input_limits(self):
        self.manager.update(self.original)
        changed = self.artifact(self.archive([(1, "A"), (2, "B")]))
        with self.assertRaises(errors.CatalogError):
            self.manager.update(
                changed, limits=ingestion.BuildLimits(max_compressed_bytes=1)
            )
        accepted = self.manager.update(changed, allow_count_change=True)
        self.assertEqual(accepted.previous_count, 1)
        with self.assertRaises(errors.CatalogError):
            self.manager.update(
                changed, limits=ingestion.BuildLimits(max_compressed_bytes=1)
            )
        for kwargs in ({"allow_count_change": 1}, {"limits": "unbounded"}):
            with (
                self.subTest(kwargs=kwargs),
                self.assertRaises(errors.CatalogInputError),
            ):
                self.manager.update(changed, **kwargs)
        with self.assertRaises(errors.CatalogInputError):
            self.manager.update(changed.path)

    def test_build_failure_preserves_active_and_original(self):
        first = self.manager.update(self.original)
        pointer = (self.manager.root / "active.json").read_bytes()
        with self.manager.open() as pinned:
            with self.assertRaises(errors.CatalogBuildError):
                self.manager.update(self.artifact(b"not an RDF archive"))
            self.assertEqual(pinned.find_ids(), (1,))
        self.assertEqual((self.manager.root / "active.json").read_bytes(), pointer)
        self.assertEqual(first.archive_path.read_bytes(), self.body)

    def test_forged_receipt_and_wrong_kind_rejected_before_archive_retention(self):
        resource_request = resources.SourceRequest.from_url(
            self.original.receipt.request_url
        )
        bad_kind = dataclasses.replace(
            self.original.receipt, kind="resource", request_key=resource_request.key
        )
        cases = [
            dataclasses.replace(self.original, receipt_sha256="0" * 64),
            dataclasses.replace(self.original, size=True),
            self.with_receipt(self.original, bad_kind),
            self.with_receipt(
                self.original,
                dataclasses.replace(
                    self.original.receipt, headers=(("etag", "x" * 70000),)
                ),
            ),
        ]
        for source in cases:
            with self.subTest(source=source.receipt_sha256):
                with self.assertRaises(errors.CatalogError):
                    self.manager.setup(source)
                self.assertEqual(
                    list((self.manager.root / "archives").glob("*.tar.bz2")), []
                )
                self.assertEqual(self.manager.status()["candidates"], [])

    def test_changed_source_rejected_for_initial_changed_and_unchanged_update(self):
        first = self.manager.update(self.original)
        for body in (self.body, self.archive([(2, "Other")])):
            source = self.artifact(body)
            source.path.write_bytes(b"tampered")
            with (
                self.subTest(digest=source.sha256),
                self.assertRaises(errors.CatalogError),
            ):
                self.manager.update(source)
        self.assertEqual(
            self.manager.status()["active"]["generation_id"], first.generation_id
        )
        other = lifecycle.CatalogManager(self.root / "other")
        with self.assertRaises(errors.CatalogError):
            other.setup(self.original)
        self.assertEqual(other.status()["state"], "missing")
        self.assertEqual(list((other.root / "archives").glob("*.tar.bz2")), [])

    def test_unchanged_update_verifies_sealed_database(self):
        first = self.manager.update(self.original)
        # Preserve length and SQLite readability but change the sealed bytes.

        with sqlite3.connect(first.catalog_path) as db:
            db.execute("PRAGMA user_version = 123")
        with self.assertRaises(errors.CatalogError):
            self.manager.update(self.original)

    def test_local_and_version_one_manifest_provenance_remain_unknown(self):
        first = self.manager.setup(self.original.path)
        self.rewrite_manifest(first, lambda value: value.update(version=1))
        self.assertEqual(self.manager.status()["state"], "ready")
        rebuilt = self.manager.rebuild()
        self.assertEqual(rebuilt.manifest["source"]["kind"], "local_archive")
        self.assertIsNone(rebuilt.manifest["source"]["retrieved_at"])
        self.assertIsNone(rebuilt.manifest["source"]["http_etag"])
        # Matching acquired bytes do not invent provenance for an older local build.
        self.assertEqual(
            self.manager.update(self.original).manifest["source"]["kind"],
            "local_archive",
        )

    def test_manifest_reader_checks_receipt_semantics_even_with_resealed_hashes(self):
        cases = (
            lambda v: v["source"].update(receipt_sha256="0" * 64),
            lambda v: v["source"]["receipt"].update(size=123),
            lambda v: v["source"].update(receipt=[]),
            lambda v: v.update(version=1),
            lambda v: v["source"].update(extra="unexpected"),
        )
        for index, change in enumerate(cases):
            with self.subTest(index=index):
                self.manager = lifecycle.CatalogManager(self.root / f"case{index}")
                first = self.manager.update(self.original)
                self.rewrite_manifest(first, change)
                self.assertEqual(self.manager.status()["state"], "invalid")
                with self.assertRaises(errors.CatalogError):
                    self.manager.open()
                with self.assertRaises(errors.CatalogError):
                    self.manager.activate(first.generation_id)

    def test_large_valid_receipt_and_legacy_receipt_schema(self):
        for version in (1, 2):
            with self.subTest(version=version):
                source = self.artifact(self.body, schema_version=version)
                manager = lifecycle.CatalogManager(self.root / f"version{version}")
                self.assertEqual(
                    manager.setup(source).manifest["source"]["receipt"][
                        "schema_version"
                    ],
                    version,
                )
        redirects = tuple(
            f"https://fixture.invalid/{i}/" + "x" * 6970 for i in range(8)
        )
        request = resources.SourceRequest(
            "s" * 1000, self.original.receipt.request_url, kind="archive"
        )
        receipt = dataclasses.replace(
            self.original.receipt,
            redirects=redirects,
            final_url=redirects[-1],
            source_uri=request.source_uri,
            request_key=request.key,
        )
        payload = _resource_types.canonical_json(_resource_types.receipt_value(receipt))
        # Fill a valid source identifier so the receipt is near its own 64KiB cap.
        request = dataclasses.replace(
            request, source_uri="s" * (1000 + 65400 - len(payload))
        )
        receipt = dataclasses.replace(
            receipt, source_uri=request.source_uri, request_key=request.key
        )
        source = self.with_receipt(self.original, receipt)
        generation = self.manager.setup(source)
        manifest_path = generation.catalog_path.parent / "manifest.json"
        self.assertGreater(manifest_path.stat().st_size, 65536)
        self.assertLess(manifest_path.stat().st_size, 131072)
        self.assertEqual(self.manager.status()["state"], "ready")

    def test_how_to_acquisition_example(self):
        document = (
            pathlib.Path(__file__).parents[2] / "docs/how-to/gettenberg-catalog.md"
        )
        runner = doctest.DocTestRunner()
        namespace = {
            "cache_dir": self.root / "docs",
            "archive_path": self.original.path,
            "artifact": self.original,
        }
        runner.run(
            doctest.DocTestParser().get_doctest(
                document.read_text(), namespace, "catalog-how-to", str(document), 0
            )
        )
        self.assertEqual(runner.failures, 0)


class CatalogRefreshCompositionTests(unittest.TestCase):
    def test_http_refresh_failure_304_and_changed_200_preserve_generation_contract(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            server = resources_test.Server()
            self.addCleanup(server.close)
            store = resources.ResourceStore(root)
            manager = lifecycle.CatalogManager(root)
            request = resources.SourceRequest.from_url(
                server.origin + "/catalog", kind="archive"
            )
            policy = resources.NetworkPolicy(
                online=True, allowed_origins=(server.origin,), max_retries=0
            )
            original = CatalogReceiptTests.archive([(1, "Original")])
            changed = CatalogReceiptTests.archive([(1, "Changed"), (2, "New")])
            server.routes["/catalog"] = [
                resources_test.Reply(body=original, headers=(("ETag", '"v1"'),)),
                resources_test.Reply(body=b"", status=503),
                resources_test.Reply(body=b"", status=304, headers=(("ETag", '"v1"'),)),
                resources_test.Reply(body=changed, headers=(("ETag", '"v2"'),)),
            ]
            with mock.patch.object(_resource_transport, "time", resources_test.Clock()):
                first_source = store.fetch(request, policy=policy)
                first = manager.setup(first_source)
                pointer = (manager.root / "active.json").read_bytes()
                with manager.open() as pinned:
                    with self.assertRaises(resources.ResourceError):
                        store.refresh(request, policy=policy)
                    self.assertEqual(
                        (manager.root / "active.json").read_bytes(), pointer
                    )
                    validated = store.refresh(request, policy=policy)
                    self.assertTrue(manager.update(validated).reused)
                    replacement = store.refresh(request, policy=policy)
                    with self.assertRaises(errors.CatalogCountChangeError) as raised:
                        manager.update(replacement)
                    self.assertEqual(pinned.find_ids(), (1,))
                    self.assertEqual(
                        manager.status()["active"]["generation_id"], first.generation_id
                    )
                    accepted = manager.activate(
                        raised.exception.generation_id, allow_count_change=True
                    )
                    self.assertEqual(
                        accepted.manifest["source"]["receipt_sha256"],
                        replacement.receipt_sha256,
                    )
                    self.assertEqual(pinned.find_ids(), (1,))
                self.assertEqual(first_source.path.read_bytes(), original)
                self.assertEqual(
                    manager.rebuild().manifest["source"], accepted.manifest["source"]
                )
                # Receipt snapshots survive resource receipt/reference removal.
                for path in (root / "gettenberg/resources/receipts").glob("*.json"):
                    path.unlink()
                self.assertEqual(manager.status()["state"], "ready")
                self.assertEqual(len(server.requests), 4)
