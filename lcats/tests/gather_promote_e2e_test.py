"""End-to-end gather-then-promote validation for the per-story bucket layout.

WI-STORY-0044's own validation requirement: an explicit end-to-end pass
confirming the write path (Stage 2), discovery (Stage 1), and standing
promote validation (Stage 2, Decision 6) all work together correctly
against a representative -- not production -- corpora tree.

The only mocked boundary is the network resource fetch itself
(``DataGatherer.resource_cache``, replaced with a local fake acquirer, the
same pattern ``downloaders_test.py`` already uses) -- everything else
(``DataGatherer.ensure``/``download``, ``discovery`` selectors,
``promote.promote_collections``) runs as real, unmocked code against
isolated temporary directories, never the real ``data/``/``corpora/``.
"""

import hashlib
import json
import pathlib
import shutil
import tempfile
import unittest
import unittest.mock

from lcats.analysis.corpus import promote
from lcats.gatherers import downloaders
from lcats.utils import capture


def _make_fake_gatherer(
    collection_name: str, data_root: pathlib.Path, cache_root: pathlib.Path
) -> downloaders.DataGatherer:
    """Return a DataGatherer pointed at an isolated data root with a local,
    no-network resource cache in a *separate* directory tree -- the cache
    must not live inside data_root, or promote_collections would pick it up
    as a phantom empty collection. The "resource" passed to download() is
    the story text itself; canonicalize it to a safe cache filename via a
    hash rather than using the raw (arbitrary-length,
    special-character-bearing) text as a path component.
    """
    gatherer = downloaders.DataGatherer(collection_name, root=str(data_root))
    gatherer.resource_cache = downloaders.LambdaResourceCache(
        canonicalizer=lambda resource: hashlib.md5(
            resource.encode("utf-8")
        ).hexdigest(),
        acquirer=lambda resource: resource,
        root=str(cache_root),
    )
    return gatherer


def _fake_handler(contents):
    """A download handler with no network dependency: contents is already
    the plain story text the fake resource cache returned."""
    return "Fake Story", contents, {"source": "e2e-validation-fixture"}


class TestGatherThenPromoteEndToEnd(unittest.TestCase):
    """Real (non-network) write path -> real discovery -> real promote,
    against a small representative corpora tree."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.data_root = pathlib.Path(self.tmp) / "data"
        self.corpora_root = pathlib.Path(self.tmp) / "corpora"
        self.cache_root = pathlib.Path(self.tmp) / "resource_cache"
        # promote_collections() now writes a run_log.RunLog by default -
        # point it at an isolated directory too, consistent with this
        # test's own "never the real data/corpora/" guarantee
        # (WI-RUNLOG-0083).
        self._log_dir_patch = unittest.mock.patch.object(
            promote, "DEFAULT_PROMOTE_LOG_DIR", pathlib.Path(self.tmp) / "logs"
        )
        self._log_dir_patch.start()
        self.addCleanup(self._log_dir_patch.stop)

    def _gatherer(self, collection_name: str) -> downloaders.DataGatherer:
        return _make_fake_gatherer(collection_name, self.data_root, self.cache_root)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_clean_collection_gathers_writes_bucket_layout_and_promotes(self):
        """A story written via the real DataGatherer write path lands in
        bucket layout and is discoverable/promotable end-to-end."""
        gatherer = self._gatherer("lovecraft")
        with capture.suppress_output():
            gatherer.download(
                "the_call_of_cthulhu",
                "Ph'nglui mglw'nafh Cthulhu R'lyeh wgah'nagl fhtagn.",
                _fake_handler,
            )

        bucket_file = (
            self.data_root / "lovecraft" / "the_call_of_cthulhu" / "story.json"
        )
        self.assertTrue(
            bucket_file.is_file(),
            "DataGatherer.download did not write the canonical bucket file",
        )
        written = json.loads(bucket_file.read_text(encoding="utf-8"))
        self.assertEqual(written["name"], "Fake Story")

        report = promote.promote_collections(self.data_root, self.corpora_root)

        self.assertEqual(("lovecraft",), report.promoted)
        self.assertEqual((), report.blocked)
        promoted_file = (
            self.corpora_root / "lovecraft" / "the_call_of_cthulhu" / "story.json"
        )
        self.assertTrue(promoted_file.is_file())
        self.assertEqual(
            json.loads(promoted_file.read_text(encoding="utf-8"))["name"],
            "Fake Story",
        )

    def test_multi_story_collection_promotes_every_bucket(self):
        """Several stories gathered into the same collection all end up as
        separate promoted bucket directories."""
        gatherer = self._gatherer("wilde")
        with capture.suppress_output():
            for slug, text in [
                ("the_happy_prince", "High above the city..."),
                ("the_selfish_giant", "Every afternoon..."),
                ("the_nightingale_and_the_rose", "She said that..."),
            ]:
                gatherer.download(slug, text, _fake_handler)

        report = promote.promote_collections(self.data_root, self.corpora_root)

        self.assertEqual(("wilde",), report.promoted)
        promoted_dirs = sorted(
            p.name for p in (self.corpora_root / "wilde").iterdir() if p.is_dir()
        )
        self.assertEqual(
            ["the_happy_prince", "the_nightingale_and_the_rose", "the_selfish_giant"],
            promoted_dirs,
        )

    def test_writer_regression_leaving_only_sidecars_is_blocked_not_promoted(self):
        """Simulates the exact writer-regression scenario Decision 6's
        standing zero-story check exists to catch: a collection directory
        that has bucket subdirectories with sidecar files but no canonical
        story.json in any of them (e.g. a crash between creating the
        bucket dir and writing story.json) must not be promoted."""
        broken_dir = self.data_root / "anderson" / "the_ugly_duckling"
        broken_dir.mkdir(parents=True)
        (broken_dir / "audit.json").write_text(
            json.dumps({"note": "story.json write never completed"}),
            encoding="utf-8",
        )

        report = promote.promote_collections(self.data_root, self.corpora_root)

        self.assertEqual((), report.promoted)
        self.assertEqual(1, len(report.blocked))
        self.assertEqual("anderson", report.blocked[0].collection)
        self.assertEqual(0, report.blocked[0].story_count)
        self.assertFalse((self.corpora_root / "anderson").exists())

    def test_mixed_clean_and_broken_collections_are_gated_independently(self):
        """A representative multi-collection corpora tree: one clean
        collection promotes while a broken one is blocked, matching
        promote_collections's documented independent-gating behavior."""
        clean_gatherer = self._gatherer("lovecraft")
        with capture.suppress_output():
            clean_gatherer.download(
                "the_shadow_over_innsmouth", "The Innsmouth look...", _fake_handler
            )
        broken_dir = self.data_root / "wilde" / "an_ideal_husband"
        broken_dir.mkdir(parents=True)
        (broken_dir / "audit.json").write_text("{}", encoding="utf-8")

        report = promote.promote_collections(self.data_root, self.corpora_root)

        self.assertEqual(("lovecraft",), report.promoted)
        self.assertEqual(1, len(report.blocked))
        self.assertEqual("wilde", report.blocked[0].collection)
        self.assertTrue((self.corpora_root / "lovecraft").exists())
        self.assertFalse((self.corpora_root / "wilde").exists())


if __name__ == "__main__":
    unittest.main()
