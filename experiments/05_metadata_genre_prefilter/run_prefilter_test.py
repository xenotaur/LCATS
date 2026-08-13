"""Tests for the metadata genre prefilter pilot."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import unittest.mock


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
    author: str = "Test Author",
) -> pathlib.Path:
    story_dir = corpus_root / collection / slug
    story_dir.mkdir(parents=True)
    payload = {
        "name": f"{collection} - {slug}",
        "body": "A compact fixture story.",
        "metadata": {"author": author, "year": 1901, "name": slug},
    }
    if url is not None:
        payload["metadata"]["url"] = url
    story_path = story_dir / "story.json"
    story_path.write_text(json.dumps(payload), encoding="utf-8")
    return story_path


def _write_normalized_cache(
    cache_db: pathlib.Path, subjects_by_gutenberg_id: dict[int, list[str]]
) -> None:
    cache_db.parent.mkdir(parents=True)
    with sqlite3.connect(cache_db) as con:
        con.execute("CREATE TABLE books (id INTEGER, gutenbergbookid INTEGER)")
        con.execute("CREATE TABLE subjects (id INTEGER, name TEXT)")
        con.execute("CREATE TABLE book_subjects (bookid INTEGER, subjectid INTEGER)")
        subject_id = 1
        for book_id, (gutenberg_id, subjects) in enumerate(
            subjects_by_gutenberg_id.items(), start=1
        ):
            con.execute(
                "INSERT INTO books (id, gutenbergbookid) VALUES (?, ?)",
                (book_id, gutenberg_id),
            )
            for subject in subjects:
                con.execute(
                    "INSERT INTO subjects (id, name) VALUES (?, ?)",
                    (subject_id, subject),
                )
                con.execute(
                    "INSERT INTO book_subjects (bookid, subjectid) VALUES (?, ?)",
                    (book_id, subject_id),
                )
                subject_id += 1


def _write_flat_cache(
    cache_db: pathlib.Path, subjects_by_gutenberg_id: dict[int, list[str]]
) -> None:
    cache_db.parent.mkdir(parents=True)
    with sqlite3.connect(cache_db) as con:
        con.execute("CREATE TABLE books (id INTEGER)")
        con.execute("CREATE TABLE subjects (bookid INTEGER, subject TEXT)")
        for gutenberg_id, subjects in subjects_by_gutenberg_id.items():
            con.execute("INSERT INTO books (id) VALUES (?)", (gutenberg_id,))
            for subject in subjects:
                con.execute(
                    "INSERT INTO subjects (bookid, subject) VALUES (?, ?)",
                    (gutenberg_id, subject),
                )


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


class TestMetadataEvidence(unittest.TestCase):
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

            rows = [
                json.loads(line)
                for line in (output_dir / "candidates.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertFalse((output_dir / "manifest.jsonl").is_file())
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
            self.assertEqual(rows[3]["gutenberg_subjects"], [])
            self.assertEqual(
                rows[3]["metadata_assessment"]["scope"],
                "gutenberg_volume",
            )
            self.assertEqual(summary["gutenberg_id_parse_failure_count"], 1)
            self.assertEqual(
                summary["gutenberg_id_parse_failures"], ["broken/bad_gutenberg"]
            )
            self.assertEqual(summary["repeated_gutenberg_ids"][0]["gutenberg_id"], 1661)
            self.assertEqual(summary["repeated_gutenberg_ids"][0]["story_count"], 2)

    def test_omitted_cache_db_does_not_read_default_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            _write_story(
                corpus_root,
                "sherlock",
                "five_orange_pips",
                url="https://www.gutenberg.org/files/1661/1661-h/1661-h.htm",
            )

            summary = run_prefilter.run(
                corpus_root=corpus_root,
                output_dir=output_dir,
                cache_db=None,
            )

            rows = [
                json.loads(line)
                for line in (output_dir / "candidates.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(summary["cache"]["status"], "not_supplied")
            self.assertEqual(summary["cache"]["cache_db_path"], None)
            self.assertEqual(rows[0]["gutenberg_subjects"], [])
            self.assertFalse((output_dir / "manifest.jsonl").exists())

    def test_ready_cache_is_opened_read_only_and_subjects_are_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_db = pathlib.Path(tmp) / "cache" / "gutenbergindex.db"
            _write_normalized_cache(
                cache_db,
                {
                    1661: [
                        "Detective and mystery stories",
                        "Crime -- Fiction",
                    ]
                },
            )

            before = cache_db.stat().st_mtime_ns
            status = run_prefilter.cache_readiness(cache_db)
            subjects = run_prefilter.read_subjects_from_cache(
                cache_db, 1661, cache_ready=status["ready"]
            )
            after = cache_db.stat().st_mtime_ns

            self.assertTrue(status["ready"])
            self.assertEqual(status["status"], "ready")
            self.assertEqual(
                subjects,
                ["Crime -- Fiction", "Detective and mystery stories"],
            )
            self.assertEqual(before, after)

    def test_flat_fixture_cache_schema_is_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_db = pathlib.Path(tmp) / "cache" / "gutenbergindex.db"
            _write_flat_cache(cache_db, {84: ["Horror tales", "Gothic fiction"]})

            self.assertTrue(run_prefilter.cache_readiness(cache_db)["ready"])
            self.assertEqual(
                run_prefilter.read_subjects_from_cache(cache_db, 84, cache_ready=True),
                ["Gothic fiction", "Horror tales"],
            )

    def test_subject_table_without_supported_columns_is_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_db = pathlib.Path(tmp) / "cache" / "gutenbergindex.db"
            cache_db.parent.mkdir()
            with sqlite3.connect(cache_db) as con:
                con.execute("CREATE TABLE books (id INTEGER)")
                con.execute("CREATE TABLE subjects (id INTEGER)")

            status = run_prefilter.cache_readiness(cache_db)

            self.assertFalse(status["ready"])
            self.assertEqual(status["status"], "missing_tables")
            self.assertIn("supported subjects schema", status["warnings"][0])

    def test_normalized_cache_missing_join_columns_is_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_db = pathlib.Path(tmp) / "cache" / "gutenbergindex.db"
            cache_db.parent.mkdir()
            with sqlite3.connect(cache_db) as con:
                con.execute("CREATE TABLE books (id INTEGER, gutenbergbookid INTEGER)")
                con.execute("CREATE TABLE subjects (id INTEGER, name TEXT)")
                con.execute("CREATE TABLE book_subjects (id INTEGER)")

            status = run_prefilter.cache_readiness(cache_db)

            self.assertFalse(status["ready"])
            self.assertEqual(status["status"], "missing_tables")
            self.assertEqual(
                run_prefilter.read_subjects_from_cache(
                    cache_db, 1661, cache_ready=status["ready"]
                ),
                [],
            )

    def test_enrich_rows_reuses_existing_cache_status(self):
        rows = [
            {
                "story_id": "sherlock/five_orange_pips",
                "story_path": "sherlock/five_orange_pips/story.json",
                "gutenberg_id": 1661,
                "gutenberg_url": "https://www.gutenberg.org/files/1661/1661-h.htm",
            },
            {
                "story_id": "sherlock/speckled_band",
                "story_path": "sherlock/speckled_band/story.json",
                "gutenberg_id": 1661,
                "gutenberg_url": "https://www.gutenberg.org/files/1661/1661-h.htm",
            },
        ]
        cache_status = {
            "cache_db_path": "/missing/gutenbergindex.db",
            "status": "missing",
            "ready": False,
        }

        with unittest.mock.patch.object(
            run_prefilter,
            "cache_readiness",
            side_effect=AssertionError("cache_readiness should not be called"),
        ):
            enriched = run_prefilter.enrich_rows(
                rows,
                pathlib.Path("/missing/gutenbergindex.db"),
                cache_status,
            )

        self.assertEqual(len(enriched), 2)
        self.assertEqual(enriched[0]["gutenberg_subjects"], [])

    def test_rule_extraction_records_all_matches_and_normalizes(self):
        subjects = [
            "Science fiction",
            "Adventure stories",
            "Crime -- Fiction",
            "Humorous stories",
            "Sea stories",
        ]

        matches = run_prefilter.rule_matches(subjects)
        normalized = run_prefilter.normalize_matches(matches)

        self.assertEqual(
            [match["label"] for match in matches],
            ["SF", "Crime", "Adventure", "Sea", "Humor / satire"],
        )
        self.assertEqual(
            normalized["target_candidates"],
            ["science fiction", "adventure", "humor"],
        )
        self.assertEqual(normalized["suggestive_target_candidates"], ["mystery"])
        self.assertEqual(normalized["secondary_signals"], ["Crime", "Sea"])

    def test_assessment_shape_contains_provenance_and_result(self):
        row = {
            "story_id": "sherlock/five_orange_pips",
            "story_path": "sherlock/five_orange_pips/story.json",
            "gutenberg_id": 1661,
            "gutenberg_url": "https://www.gutenberg.org/files/1661/1661-h.htm",
        }
        subjects = ["Detective and mystery stories"]
        matches = run_prefilter.rule_matches(subjects)
        normalized = run_prefilter.normalize_matches(matches)

        assessment = run_prefilter.build_metadata_assessment(
            row,
            subjects,
            matches,
            normalized,
            "2026-08-13T16:00:00Z",
            {"cache_db_path": "/cache/gutenbergindex.db", "status": "ready"},
        )

        self.assertEqual(assessment["label"], "gutenberg_metadata_rules")
        self.assertEqual(assessment["generated_at"], "2026-08-13T16:00:00Z")
        self.assertEqual(assessment["scope"], "gutenberg_volume")
        self.assertEqual(assessment["method"]["pipeline"], run_prefilter.PIPELINE_NAME)
        self.assertEqual(assessment["provenance"]["story_id"], row["story_id"])
        self.assertEqual(assessment["evidence"]["raw_subjects"], subjects)
        self.assertEqual(assessment["evidence"]["raw_rule_matches"], matches)
        self.assertEqual(assessment["result"]["target_candidates"], ["mystery"])

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
                run_prefilter.validate_output_dir(
                    cache_db.parent, corpus_root, cache_db
                )

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


class TestPilotSelection(unittest.TestCase):
    def test_selects_deterministic_40_story_pilot_and_reports_cap(self):
        rows = []
        for collection in (
            "lovecraft",
            "sherlock",
            "ohenry-four_million",
            "mass_quantities",
        ):
            for index in range(12):
                rows.append(
                    {
                        "story_id": f"{collection}/story_{index:02d}",
                        "story_path": f"{collection}/story_{index:02d}/story.json",
                        "collection": collection,
                        "story_slug": f"story_{index:02d}",
                        "gutenberg_id": 1000 + index,
                    }
                )

        selected, diagnostics = run_prefilter.select_pilot_rows(rows)

        self.assertEqual(len(selected), 40)
        self.assertEqual(
            diagnostics["selected_counts"],
            {
                "lovecraft": 10,
                "sherlock": 10,
                "ohenry": 10,
                "mass_quantities": 10,
            },
        )
        self.assertEqual(selected[0]["story_id"], "lovecraft/story_00")
        self.assertEqual(selected[10]["story_id"], "sherlock/story_00")
        self.assertEqual(selected[20]["story_id"], "ohenry-four_million/story_00")
        self.assertEqual(selected[30]["story_id"], "mass_quantities/story_00")

    def test_optional_gutenberg_cap_reports_shortfalls(self):
        rows = [
            {
                "story_id": f"sherlock/story_{index:02d}",
                "story_path": f"sherlock/story_{index:02d}/story.json",
                "collection": "sherlock",
                "story_slug": f"story_{index:02d}",
                "gutenberg_id": 1661,
            }
            for index in range(12)
        ]

        selected, diagnostics = run_prefilter.select_pilot_rows(
            rows,
            max_per_gutenberg_id=2,
        )

        self.assertEqual(len(selected), 2)
        self.assertEqual(diagnostics["selected_counts"]["sherlock"], 2)
        self.assertEqual(diagnostics["shortfalls"]["sherlock"], 8)
        self.assertEqual(diagnostics["skipped_by_gutenberg_cap"]["sherlock"], 10)


if __name__ == "__main__":
    unittest.main()
