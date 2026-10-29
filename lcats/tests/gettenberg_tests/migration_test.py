"""Real-catalog migration and retired-dependency regression coverage."""

import hashlib
import os
import pathlib
import subprocess
import sys
import tarfile
import tempfile
import types
import unittest

from lcats.gettenberg import catalog
from lcats.gettenberg import errors
from lcats.gettenberg import identifiers
from lcats.gettenberg import ingestion
from lcats.utils import genre
from tests.gettenberg_tests import catalog_test


class MigrationTests(unittest.TestCase):
    def test_source_identity_accepts_known_paths_and_rejects_unrelated_urls(self):
        for url in (
            "https://www.gutenberg.org/cache/epub/84/pg84.txt",
            "http://www.gutenberg.org/files/84/84-0.txt",
            "https://gutenberg.org/ebooks/84?download=1#section",
            "https://www.gutenberg.org/ebooks/84.txt.utf-8",
        ):
            with self.subTest(url=url):
                self.assertEqual(identifiers.ebook_id_from_url(url), 84)
        for url in (
            None,
            "",
            "https://example.com/files/84/84.txt",
            "https://gutenberg.org.evil.invalid/ebooks/84",
            "https://name@gutenberg.org/ebooks/84",
            "https://www.gutenberg.org/ebooks/0",
            "/ebooks/84",
            "file://www.gutenberg.org/ebooks/84",
            "https://www.gutenberg.org:444/ebooks/84",
            "https://www.gutenberg.org/ebooks/nope",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                identifiers.ebook_id_from_url(url)

    def test_nested_html_sources_keep_existing_corpus_identities(self):
        # Actual URL shapes in the Sherlock, O. Henry and Chesterton collections.
        # Exercise the story-facing adapter as well as the URL parser.
        for book_id in (1661, 1595, 204):
            url = (
                f"https://www.gutenberg.org/files/{book_id}/{book_id}-h/{book_id}-h.htm"
            )
            with self.subTest(url=url):
                story = types.SimpleNamespace(metadata={"url": url})
                self.assertEqual(genre.get_id_for_story(story), book_id)
        with self.assertRaises(ValueError):
            identifiers.ebook_id_from_url(
                "https://example.com/files/1661/1661-h/1661-h.htm"
            )

    def test_real_catalog_keeps_ids_titles_aliases_and_genre_associated(self):
        # Authored regression records using historical notebook IDs. These are
        # not assertions about the real content of ebooks 24927 or 3115.
        records = [
            catalog_test.record(
                24927,
                "First title",
                """
                <dc:alternative>Alternative first title</dc:alternative>
                <dc:creator><pg:agent rdf:about="2009/agents/3115">
                  <pg:name>First Author</pg:name><pg:alias>First Alias</pg:alias>
                </pg:agent></dc:creator>
                <dc:subject><rdf:Description><rdf:value>Science fiction</rdf:value></rdf:Description></dc:subject>
            """,
            ),
            catalog_test.record(
                3115,
                "Second title",
                """
                <dc:creator><pg:agent rdf:about="2009/agents/24927">
                  <pg:name>Second Author</pg:name><pg:alias>Second Alias</pg:alias>
                </pg:agent></dc:creator>
                <dc:subject><rdf:Description><rdf:value>Ghost stories</rdf:value></rdf:Description></dc:subject>
            """,
            ),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            archive = root / "source.tar.bz2"
            archive.write_bytes(
                catalog_test.archive_bytes(
                    [
                        (f"fixture-{i}.rdf", data, tarfile.REGTYPE)
                        for i, data in enumerate(records)
                    ]
                )
            )
            database = root / "catalog.sqlite"
            ingestion.build_catalog(archive, database)
            before = hashlib.sha256(database.read_bytes()).hexdigest()
            with catalog.Catalog(database) as library:
                first, second = library.get_many([24927, 3115])
                self.assertEqual(
                    [v.value.text for v in first.ebook.titles],
                    ["First title", "Alternative first title"],
                )
                self.assertEqual(
                    second.ebook.contributors[0].agent.aliases[0].text, "Second Alias"
                )
                self.assertEqual(
                    first.ebook.contributors[0].agent.aliases[0].text, "First Alias"
                )
                self.assertEqual(genre.get_genre_by_id(24927, catalog=library), "SF")
                self.assertEqual(genre.get_genre_by_id(3115, catalog=library), "Horror")
                self.assertEqual(
                    genre.get_genre_by_id(42, catalog=library), "Unclassified"
                )
                story = types.SimpleNamespace(
                    metadata={"url": "https://www.gutenberg.org/ebooks/24927"}
                )
                self.assertEqual(
                    genre.find_all_stories_for_genre([story], "SF", catalog=library),
                    [story],
                )
                with self.assertRaises(errors.CatalogInputError):
                    genre.get_genre_by_id(True, catalog=library)
            with self.assertRaises(errors.CatalogClosedError):
                genre.get_genre_by_id(24927, catalog=library)
            self.assertEqual(hashlib.sha256(database.read_bytes()).hexdigest(), before)

    def test_public_consumers_import_without_legacy_or_cache_side_effects(self):
        code = """
import importlib.abc, pathlib, sys
class DenyLegacy(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "gutenbergpy" or fullname.startswith("gutenbergpy."):
            raise AssertionError("retired dependency imported: " + fullname)
sys.meta_path.insert(0, DenyLegacy())
from lcats import cli
from lcats.utils import genre
from lcats.analysis.corpus import clean_cli, reconciliation
from lcats.gatherers import parser, main
from lcats.gettenberg import catalog, lifecycle, resources, cleanup
assert not pathlib.Path("cache").exists()
assert "gutenbergpy" not in sys.modules
"""
        with tempfile.TemporaryDirectory() as root:
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=root,
                env={
                    **os.environ,
                    "LCATS_CACHE_DIR": str(pathlib.Path(root) / "cache"),
                },
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
