"""Offline route contracts from pinned upstream conventions and saved RDF.

All endpoints are inert examples or local fixtures. These tests establish URL
mapping, not live mirror availability or byte equivalence between formats.
"""

import dataclasses
import pathlib
import re
import tempfile
import unittest

from lcats.gettenberg import models
from lcats.gettenberg import rdf
from lcats.gettenberg import resources
from lcats.utils import capture
from tests.gettenberg_tests import resources_test


class GutenbergRoutingTest(unittest.TestCase):
    def setUp(self):
        self.routes = resources.GutenbergRoutes(
            "https://main.example/books/", "https://generated.example/epub/"
        )

    def test_main_sharding_and_exact_nested_suffix(self):
        cases = (
            ("1", "1.txt", "0/1/1.txt"),
            ("9", "9.zip", "0/9/9.zip"),
            ("10", "10-h/10-h.htm", "1/10/10-h/10-h.htm"),
            ("84", "84-0.txt", "8/84/84-0.txt"),
            (
                "10001",
                "10001-h/images/a%20b.jpg",
                "1/0/0/0/10001/10001-h/images/a%20b.jpg",
            ),
        )
        for book, suffix, expected in cases:
            with self.subTest(book=book):
                uri = f"http://www.gutenberg.org/files/{book}/{suffix}"
                result = self.routes.resolve(uri)
                self.assertEqual(result.code, "qualified")
                self.assertEqual(
                    result.request.request_url, "https://main.example/books/" + expected
                )
                self.assertEqual(result.request.source_uri, uri)
                self.assertEqual(result.request.route_policy, "gutenberg-mirror-v1")

    def test_generated_paths_and_legacy_alias_preserve_filename(self):
        for prefix in ("epub", "generated"):
            for suffix in (
                "pg84-h.zip",
                "pg84.cover.medium.jpg",
                "nested/a.htm",
                "1001.epub",
            ):
                with self.subTest(prefix=prefix, suffix=suffix):
                    result = self.routes.resolve(
                        f"https://www.gutenberg.org/cache/{prefix}/84/{suffix}"
                    )
                    self.assertEqual(
                        result.request.request_url,
                        f"https://generated.example/epub/84/{suffix}",
                    )

    def test_all_published_generated_aliases(self):
        # Expected paths are explicit fixtures, not generated from implementation's
        # alias table. Adding a new alias requires upstream evidence and a case.
        expected = {
            "txt.utf-8": "pg84.txt",
            "html.images": "pg84-images.html",
            "html.noimages": "pg84.html",
            "epub.images": "pg84-images.epub",
            "epub.noimages": "pg84.epub",
            "epub3.images": "pg84-images-3.epub",
            "kindle.images": "pg84-images.mobi",
            "kindle.noimages": "pg84.mobi",
            "kf8.images": "pg84-images-kf8.mobi",
            "pdf.images": "pg84-images.pdf",
            "pdf.noimages": "pg84.pdf",
            "rdf": "pg84.rdf",
            "rst.gen": "pg84.rst",
            "cover.small": "pg84.cover.small.jpg",
            "cover.medium": "pg84.cover.medium.jpg",
            "qrcode": "pg84.qrcode.png",
            "zip": "pg84-h.zip",
        }
        for alias, filename in expected.items():
            with self.subTest(alias=alias):
                uri = f"https://www.gutenberg.org/ebooks/84.{alias}"
                result = self.routes.resolve(uri)
                self.assertEqual(result.request.source_uri, uri)
                self.assertEqual(
                    result.request.request_url,
                    "https://generated.example/epub/84/" + filename,
                )

    def test_catalog_independent_of_mirror_roots(self):
        request = self.routes.catalog_request()
        self.assertEqual(request.kind, "archive")
        self.assertEqual(
            request.request_url,
            "https://www.gutenberg.org/cache/epub/feeds/rdf-files.tar.bz2",
        )
        routes = dataclasses.replace(
            self.routes, catalog_url="https://catalog.example/archive?version=2"
        )
        self.assertEqual(
            routes.catalog_request().request_url,
            "https://catalog.example/archive?version=2",
        )
        self.assertEqual(routes.main_root, self.routes.main_root)

    def test_origin_and_authority_validation(self):
        for uri in (
            "https://evil.example/files/84/a",
            "https://www.gutenberg.org.evil.test/files/84/a",
            "https://www.gutenberg.org:8443/files/84/a",
            "https://gutenberg.org/files/84/a",
            "https://user:secret@www.gutenberg.org/files/84/a",
            "file:///files/84/a",
            "https://www.gutenberg.org:/files/84/a",
            "\nhttps://www.gutenberg.org/files/84/a",
            None,
            42,
            "https://www.gutenberg.org/files/84/%zz",
        ):
            with self.subTest(uri=uri):
                result = self.routes.resolve(uri)
                self.assertIsNone(result.request)
                self.assertNotIn("secret", result.message)
        result = self.routes.resolve("HTTPS://WWW.GUTENBERG.ORG:443/files/84/a")
        self.assertIsNotNone(result.request)
        self.assertEqual(
            result.request.source_uri, "HTTPS://WWW.GUTENBERG.ORG:443/files/84/a"
        )

    def test_unsafe_paths_never_escape_roots(self):
        for suffix in (
            "../x",
            "./x",
            "%2e%2e/x",
            "%2E/x",
            "a%2fb",
            "a%5Cb",
            "%252e%252e/x",
            "a//b",
            "a\\b",
            "%00x",
            "%0ax",
            "%7fx",
            "x?download=1",
            "x#fragment",
            "x?",
            "x#",
        ):
            for prefix in ("files/84", "cache/epub/84"):
                with self.subTest(suffix=suffix, prefix=prefix):
                    result = self.routes.resolve(
                        f"https://www.gutenberg.org/{prefix}/{suffix}"
                    )
                    self.assertIsNone(result.request)

    def test_unknown_or_ambiguous_layouts_are_diagnostic(self):
        for path in (
            "/ebooks/84.future",
            "/ebooks/84.txt.utf-8/extra",
            "/ebooks/84",
            "/etext99/a.txt",
            "/files/084/a",
            "/files/0/a",
            "/files/84/",
            "/cache/epub/84/",
            "/cache/epub/feeds/a",
            "/prefix/files/84/a",
            "/dirs/8/84/a",
            "/ebooks/84.txt.utf-8?download=1",
        ):
            with self.subTest(path=path):
                self.assertIsNone(
                    self.routes.resolve("https://www.gutenberg.org" + path).request
                )
        # Explicit transport remains available; unsupported mapping is not a ban.
        request = resources.SourceRequest.from_url("https://example.org/unknown.epub")
        self.assertEqual(request.route_policy, "explicit-url-v1")

    def test_invalid_roots_and_catalog_configuration_raise(self):
        for root in (
            "https://user:secret@example.org/a",
            "https://example.org/a/../b",
            "https://example.org/a%2fb",
            "https://example.org/%252e",
            "https://example.org/a?",
            "https://example.org/a#",
            "https://example.org//a",
        ):
            with self.subTest(root=root):
                for field in ("main_root", "generated_root"):
                    with self.assertRaises(resources.ResourceInputError):
                        dataclasses.replace(self.routes, **{field: root})
        with self.assertRaises(resources.ResourceInputError):
            dataclasses.replace(self.routes, catalog_url="https://example.org/a#part")
        routes = resources.GutenbergRoutes(
            "https://EXAMPLE.org", "https://example.org/gen"
        )
        self.assertEqual(routes.main_root, "https://example.org/")
        self.assertEqual(routes.generated_root, "https://example.org/gen/")

    def test_composed_url_is_still_bounded(self):
        routes = dataclasses.replace(
            self.routes, main_root="https://example.org/" + "x" * 8000
        )
        result = routes.resolve("https://www.gutenberg.org/files/84/" + "y" * 300)
        self.assertEqual(result.code, "invalid_destination")

    def test_saved_rdf_routes_without_changing_metadata(self):
        count = 0
        for path in sorted((pathlib.Path(__file__).parent / "fixtures").glob("*.rdf")):
            ebook = rdf.parse_record(path.read_bytes(), source_name=path.name).ebook
            before = dataclasses.asdict(ebook)
            for resource in ebook.resources:
                with self.subTest(file=path.name, uri=resource.uri):
                    decision = self.routes.resolve(resource.uri)
                    self.assertIsNotNone(decision.request)
                    self.assertEqual(decision.request.source_uri, resource.uri)
                    count += 1
            self.assertEqual(before, dataclasses.asdict(ebook))
        self.assertEqual(count, 113)

    def test_routing_and_planning_do_not_create_cache_or_grant_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = pathlib.Path(temporary) / "absent"
            store = resources.ResourceStore(cache)
            source = self.routes.resolve(
                "https://www.gutenberg.org/ebooks/84.txt.utf-8"
            ).request
            plan = store.plan(source)
            self.assertEqual(plan.action, "blocked")
            with self.assertRaises(resources.ResourcePolicyError):
                store.fetch(source)
            self.assertFalse(cache.exists())
            policy = resources.NetworkPolicy(
                online=True, allowed_origins=("https://main.example",)
            )
            self.assertEqual(
                store.plan(source, policy=policy).reason, "origin not permitted"
            )
            self.assertFalse(cache.exists())


class RoutableSelectionTest(unittest.TestCase):
    def setUp(self):
        self.routes = resources.GutenbergRoutes(
            "https://example.org/main", "https://example.org/generated"
        )
        self.ebook = models.Ebook(
            84,
            "urn:84",
            resources=(
                models.Resource(
                    "https://www.gutenberg.org/ebooks/84.future",
                    formats=(models.Term(models.Literal("text/plain; charset=utf-8")),),
                ),
                models.Resource(
                    "https://www.gutenberg.org/files/84/84.txt",
                    formats=(models.Term(models.Literal("text/plain")),),
                ),
                models.Resource(
                    "https://www.gutenberg.org/ebooks/84.html.images",
                    formats=(models.Term(models.Literal("text/html")),),
                ),
            ),
        )

    def test_unroutable_preferred_resource_does_not_hide_alternative(self):
        before = dataclasses.asdict(self.ebook)
        result = resources.select_routable_resource(self.ebook, routes=self.routes)
        self.assertIs(result.selection.resource, self.ebook.resources[1])
        self.assertEqual(result.selection.source_index, 1)
        self.assertEqual(result.routes[0].code, "unsupported_layout")
        self.assertEqual(result.request.source_uri, self.ebook.resources[1].uri)
        self.assertIn(
            "ineligible_resource", [d.code for d in result.selection.diagnostics]
        )
        self.assertEqual(before, dataclasses.asdict(self.ebook))
        self.assertEqual(
            result, resources.select_routable_resource(self.ebook, routes=self.routes)
        )

    def test_explicit_preferences_preserve_order(self):
        result = resources.select_routable_resource(
            self.ebook,
            routes=self.routes,
            preferences=(resources.ResourcePreference("text/html"),),
        )
        self.assertEqual(result.selection.source_index, 2)
        self.assertEqual(
            result.request.request_url,
            "https://example.org/generated/84/pg84-images.html",
        )

    def test_empty_all_ineligible_and_unmatched_results(self):
        for ebook in (
            dataclasses.replace(self.ebook, resources=()),
            dataclasses.replace(self.ebook, resources=self.ebook.resources[:1]),
        ):
            with self.subTest(ebook=ebook):
                result = resources.select_routable_resource(ebook, routes=self.routes)
                self.assertIsNone(result.request)
                self.assertEqual(result.selection.diagnostics[-1].code, "no_match")
        result = resources.select_routable_resource(
            self.ebook,
            routes=self.routes,
            preferences=(resources.ResourcePreference("application/pdf"),),
        )
        self.assertIsNone(result.request)
        self.assertEqual(len(result.routes), 3)

    def test_capability_filter_retains_mime_diagnostics_and_source_ties(self):
        bad = models.Resource(
            "urn:bad", formats=(models.Term(models.Literal("invalid")),)
        )
        ebook = dataclasses.replace(
            self.ebook,
            resources=(bad, self.ebook.resources[1], self.ebook.resources[1]),
        )
        result = resources.select_resource(ebook, eligible_indices=frozenset((1, 2)))
        self.assertEqual(result.source_index, 1)
        self.assertEqual(
            [d.code for d in result.diagnostics],
            ["invalid_format", "ineligible_resource", "source_order_tie"],
        )
        self.assertIsNone(
            resources.select_resource(ebook, eligible_indices=frozenset()).resource
        )

    def test_invalid_capabilities_and_arguments(self):
        for indices in (
            {1},
            (1,),
            frozenset((-1,)),
            frozenset((3,)),
            frozenset((True,)),
            frozenset((1.0,)),
        ):
            with self.subTest(indices=indices):
                with self.assertRaises(resources.ResourceInputError):
                    resources.select_resource(self.ebook, eligible_indices=indices)
        for ebook, routes in ((None, self.routes), (self.ebook, None)):
            with self.assertRaises(resources.ResourceInputError):
                resources.select_routable_resource(ebook, routes=routes)


class RoutedAcquisitionTest(unittest.TestCase):
    """Exercise the public route/store boundary with a tiny real loopback server."""

    def setUp(self):
        # Share the existing network-boundary fixture, not a mocked router/store.
        self.server = resources_test.Server()
        self.addCleanup(self.server.close)
        self.reply = resources_test.Reply(body=b"unchanged original bytes")
        self.server.routes["/epub/84/pg84.txt"] = [self.reply]
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.cache = pathlib.Path(self.temporary.name) / "cache"
        self.routes = resources.GutenbergRoutes(
            self.server.origin + "/books/", self.server.origin + "/epub/"
        )

    def test_mapped_alias_reuses_same_url_without_rewriting_receipt(self):
        source = "https://www.gutenberg.org/ebooks/84.txt.utf-8"
        request = self.routes.resolve(source).request
        store = resources.ResourceStore(self.cache)
        policy = resources.NetworkPolicy(
            online=True, allowed_origins=(self.server.origin,)
        )
        first = store.fetch(request, policy=policy)
        self.assertEqual(first.path.read_bytes(), self.reply.body)
        self.assertEqual(first.receipt.source_uri, source)
        self.assertEqual(first.receipt.route_policy, "gutenberg-mirror-v1")
        self.assertEqual(first.receipt.request_url, request.request_url)
        self.assertEqual(first.receipt.final_url, request.request_url)
        direct = self.routes.resolve(
            "https://www.gutenberg.org/cache/epub/84/pg84.txt"
        ).request
        self.assertEqual(request.key, direct.key)
        second = store.fetch(direct)
        self.assertEqual(first, second)
        self.assertEqual(second.receipt.source_uri, source)
        self.assertEqual(len(self.server.requests), 1)

    def test_routing_how_to_examples_execute_with_local_endpoints(self):
        document = (
            pathlib.Path(__file__).resolve().parents[2]
            / "docs/how-to/gettenberg-routing.md"
        )
        blocks = re.findall(
            r"```python\n(.*?)```", document.read_text(encoding="utf-8"), re.S
        )
        self.assertEqual(len(blocks), 4)
        ebook = models.Ebook(
            84,
            "urn:84",
            resources=(
                models.Resource(
                    "https://www.gutenberg.org/ebooks/84.txt.utf-8",
                    formats=(models.Term(models.Literal("text/plain; charset=utf-8")),),
                ),
            ),
        )
        namespace = {"ebook": ebook}
        with capture.capture_output():
            for index, block in enumerate(blocks):
                code = block.replace(
                    "https://main.example", self.server.origin
                ).replace("https://generated.example", self.server.origin)
                code = code.replace('"cache"', repr(str(self.cache)))
                exec(compile(code, str(document), "exec"), namespace)
                if index < 2:
                    self.assertFalse(self.cache.exists())
                    self.assertEqual(self.server.requests, [])
        self.assertEqual(namespace["artifact"].path.read_bytes(), self.reply.body)
        self.assertEqual(len(self.server.requests), 1)
        self.assertEqual(self.server.requests[0][0], "/epub/84/pg84.txt")
