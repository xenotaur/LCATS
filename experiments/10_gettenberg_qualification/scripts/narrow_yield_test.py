"""Exercise the yield observer against real fixture-backed gathering.

From lcats/, with PYTHONPATH="$PWD/src":
python -m unittest discover -s ../experiments/10_gettenberg_qualification/scripts -p narrow_yield_test.py
No external network, persistent caches or canonical outputs. Fixtures and observed
publications use temporary roots. Tests cover interruption accounting, fresh writes,
reuse with no source cache, metadata skips and filename collision attribution.
"""

import contextlib
import dataclasses
import io
import os
import pathlib
import socket
import tempfile
import unittest
from unittest import mock

from lcats.gatherers import gutenberg_source
from lcats.gettenberg import lifecycle, resources
import qualify_narrow_installed
import qualify_narrow_yield


class GatherYieldTests(unittest.TestCase):
    """Validate observer claims using the real gather pipeline and output files."""

    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="yield-observer-test-")
        cls.root = pathlib.Path(cls.temporary.name).resolve()
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("no network")
        ):
            cls.smoke = qualify_narrow_installed.exercise(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(
            mock.patch.object(
                socket, "socket", side_effect=AssertionError("no network")
            )
        )
        self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        self.stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
        self.case = pathlib.Path(
            self.stack.enter_context(tempfile.TemporaryDirectory(prefix="yield-case-"))
        ).resolve()
        self.stack.enter_context(
            mock.patch.dict(
                os.environ, {"LCATS_CORPORA_DIR": str(self.case / "corpora")}
            )
        )
        self.catalog = self.stack.enter_context(
            lifecycle.CatalogManager(self.root / "cache").open()
        )
        origin = qualify_narrow_installed.ORIGIN
        self.source = gutenberg_source.GutenbergStorySource(
            self.catalog,
            resources.ResourceStore(self.root / "cache"),
            routes=resources.GutenbergRoutes(origin + "/main/", origin + "/generated/"),
        )
        self.books = qualify_narrow_installed.BOOKS
        self.metas = {book: self.source.metadata(book) for book in self.books}
        self.priors = {book: {} for book in self.books}
        for story in self.smoke["stories"]:
            self.priors[story["id"]] = {
                "body": {
                    "normalized_sha256": qualify_narrow_yield.sha(story["json"]["body"])
                }
            }

    def observe(self, identifiers, name, source=None, metas=None):
        """Give each invocation its own log but a shared output directory."""
        return qualify_narrow_yield.observe_gather(
            identifiers,
            source or self.source,
            metas or self.metas,
            self.case / "data",
            self.case / name,
            self.priors,
        )

    def test_abort_retains_written_prefix_and_repeat_reuses(self):
        first, second, refused = self.books
        order = [first, refused, second]
        cold = self.observe(order, "cold")
        self.assertEqual(
            [row["outcome"] for row in cold["rows"]], ["published", "refused"]
        )
        self.assertEqual(cold["unattempted_ids"], [second])
        self.assertEqual(cold["summary"]["attempted"], 2)
        self.assertEqual(cold["exception"]["code"], "cleanup_refused")
        self.assertTrue(cold["rows"][0]["matches_prior_body"])
        repeat = self.observe(order, "repeat")
        self.assertEqual(
            [row["outcome"] for row in repeat["rows"]], ["reused", "refused"]
        )
        self.assertEqual(repeat["rows"][0]["output"], cold["rows"][0]["output"])
        self.assertTrue(repeat["events"][-1]["event"].startswith("run_aborted"))
        self.source.store = resources.ResourceStore(self.case / "empty-cache")
        reused = self.observe([first], "empty-cache-reuse")
        self.assertEqual(reused["summary"]["reused"], 1)
        self.assertIsNone(reused["exception"])

    def test_metadata_skip_does_not_publish(self):
        book = self.books[0]
        metas = dict(self.metas)
        metas[book] = dataclasses.replace(metas[book], subjects=())

        class MetadataSource:
            def metadata(self, identifier):
                return metas[identifier]

            def read(self, metadata):
                raise AssertionError("ineligible metadata must not read a source")

        report = self.observe([book], "skip", MetadataSource(), metas)
        self.assertEqual(report["summary"]["skipped"], 1)
        self.assertIn("No data", report["rows"][0]["skip_reason"])
        self.assertIsNone(report["rows"][0]["output"])

    def test_collision_is_reuse_not_second_publication(self):
        first, second, _ = self.books
        metas = dict(self.metas)
        metas[second] = dataclasses.replace(metas[second], titles=metas[first].titles)
        original = self.source

        class CollisionSource:
            def metadata(self, identifier):
                return metas[identifier]

            def read(self, metadata):
                return original.read(metadata)

        report = self.observe([first, second], "collision", CollisionSource(), metas)
        self.assertEqual(
            [row["outcome"] for row in report["rows"]], ["published", "reused"]
        )
        self.assertEqual(report["summary"]["ownership_mismatches"], 1)
        self.assertFalse(report["rows"][1]["owner_matches"])

    def test_offline_cache_miss_is_error_not_refusal_or_skip(self):
        self.source.store = resources.ResourceStore(self.case / "empty-cache")
        report = self.observe([self.books[0], self.books[1]], "cache-miss")
        self.assertEqual(report["summary"]["error"], 1)
        self.assertEqual(report["summary"]["unattempted"], 1)
        self.assertEqual(report["exception"]["code"], "network_denied")
        self.assertIsNone(report["rows"][0]["output"])


if __name__ == "__main__":
    unittest.main()
