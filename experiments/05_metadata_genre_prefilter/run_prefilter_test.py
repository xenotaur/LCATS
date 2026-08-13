"""Tests for the metadata genre prefilter dry-run scaffold."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest


_RUNNER_PATH = pathlib.Path(__file__).resolve().parent / "run_prefilter.py"
_SPEC = importlib.util.spec_from_file_location("run_prefilter", _RUNNER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
run_prefilter = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(run_prefilter)


def _write_story(
    corpus_root: pathlib.Path,
    collection: str,
    slug: str,
    *,
    url: str | None,
) -> pathlib.Path:
    story_dir = corpus_root / collection / slug
    story_dir.mkdir(parents=True)
    payload = {
        "name": f"{collection} - {slug}",
        "body": "A compact fixture story.",
        "metadata": {"author": "Test Author", "year": 1901, "name": slug},
    }
    if url is not None:
        payload["metadata"]["url"] = url
    story_path = story_dir / "story.json"
    story_path.write_text(json.dumps(payload), encoding="utf-8")
    return story_path


class TestGutenbergIdParsing(unittest.TestCase):
    def test_parses_common_gutenberg_url_forms(self):
        cases = {
            "https://www.gutenberg.org/cache/epub/1661/pg1661-images.html": 1661,
            "https://www.gutenberg.org/files/2591/2591-h/2591-h.htm": 2591,
            "https://www.gutenberg.org/ebooks/84": 84,
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(run_prefilter.parse_gutenberg_id(url), expected)

    def test_non_gutenberg_url_returns_none(self):
        self.assertIsNone(run_prefilter.parse_gutenberg_id("https://example.com"))


class TestDryRunScaffold(unittest.TestCase):
    def test_missing_cache_does_not_create_cache_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            cache_root = root / "missing_cache"
            cache_db = cache_root / "gutenbergindex.db"
            _write_story(
                corpus_root,
                "sherlock",
                "five_orange_pips",
                url="https://www.gutenberg.org/files/1661/1661-h/1661-h.htm",
            )
            _write_story(
                corpus_root,
                "sherlock",
                "speckled_band",
                url="https://www.gutenberg.org/cache/epub/1661/pg1661-images.html",
            )
            _write_story(corpus_root, "local", "no_url", url=None)
            _write_story(
                corpus_root, "external", "non_gutenberg", url="https://example.com"
            )
            _write_story(
                corpus_root,
                "broken",
                "bad_gutenberg",
                url="https://www.gutenberg.org/no-id-here",
            )

            summary = run_prefilter.run(
                corpus_root=corpus_root,
                output_dir=output_dir,
                cache_db=cache_db,
            )

            self.assertFalse(cache_root.exists())
            self.assertFalse((cache_root / "texts").exists())
            self.assertFalse((cache_root / "tmp").exists())
            self.assertFalse((cache_root / "rdf-files.tar.bz2").exists())
            self.assertFalse(cache_db.exists())
            self.assertEqual(summary["cache"]["status"], "missing")
            self.assertFalse(summary["cache"]["ready"])

            manifest_path = output_dir / "manifest.jsonl"
            rows = [
                json.loads(line)
                for line in manifest_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(
                [row["story_id"] for row in rows],
                [
                    "broken/bad_gutenberg",
                    "external/non_gutenberg",
                    "local/no_url",
                    "sherlock/five_orange_pips",
                    "sherlock/speckled_band",
                ],
            )
            self.assertEqual(rows[3]["gutenberg_id"], 1661)
            self.assertEqual(summary["gutenberg_id_parse_failure_count"], 1)
            self.assertEqual(
                summary["gutenberg_id_parse_failures"], ["broken/bad_gutenberg"]
            )
            self.assertEqual(summary["repeated_gutenberg_ids"][0]["gutenberg_id"], 1661)
            self.assertEqual(summary["repeated_gutenberg_ids"][0]["story_count"], 2)

    def test_ready_cache_is_opened_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_db = pathlib.Path(tmp) / "cache" / "gutenbergindex.db"
            cache_db.parent.mkdir()
            with sqlite3.connect(cache_db) as con:
                con.execute("CREATE TABLE books (id INTEGER)")
                con.execute("CREATE TABLE subjects (bookid INTEGER, subject TEXT)")

            before = cache_db.stat().st_mtime_ns
            status = run_prefilter.cache_readiness(cache_db)
            after = cache_db.stat().st_mtime_ns

            self.assertTrue(status["ready"])
            self.assertEqual(status["status"], "ready")
            self.assertEqual(before, after)

    def test_output_under_corpus_root_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus_root = pathlib.Path(tmp) / "corpora"
            output_dir = corpus_root / "results"
            cache_db = pathlib.Path(tmp) / "cache" / "gutenbergindex.db"

            with self.assertRaises(ValueError):
                run_prefilter.validate_output_dir(output_dir, corpus_root, cache_db)

    def test_output_under_cache_root_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            cache_db = root / "cache" / "gutenbergindex.db"

            with self.assertRaises(ValueError):
                run_prefilter.validate_output_dir(cache_db.parent, corpus_root, cache_db)

    def test_missing_or_empty_corpus_root_is_refused_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            cache_db = root / "cache" / "gutenbergindex.db"
            output_dir = root / "results"

            with self.assertRaises(ValueError):
                run_prefilter.run(
                    corpus_root=root / "missing",
                    output_dir=output_dir,
                    cache_db=cache_db,
                )
            self.assertFalse(output_dir.exists())

            empty_corpus = root / "empty_corpus"
            empty_corpus.mkdir()
            with self.assertRaises(ValueError):
                run_prefilter.run(
                    corpus_root=empty_corpus,
                    output_dir=output_dir,
                    cache_db=cache_db,
                )
            self.assertFalse(output_dir.exists())

    def test_import_does_not_load_mutating_gettenberg_cache_module(self):
        script = (
            "import importlib.util, pathlib, sys\n"
            f"path = pathlib.Path({str(_RUNNER_PATH)!r})\n"
            "spec = importlib.util.spec_from_file_location('isolated_run_prefilter', path)\n"
            "assert spec is not None and spec.loader is not None\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "print('lcats.gettenberg.cache' in sys.modules)\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.stdout.strip(), "False")


if __name__ == "__main__":
    unittest.main()
