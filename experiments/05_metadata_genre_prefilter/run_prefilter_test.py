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


def _row_with_target_candidates(
    story_id: str, target_candidates: list[str], gutenberg_id: int | None = None
) -> dict:
    return {
        "story_id": story_id,
        "story_path": f"{story_id}/story.json",
        "collection": story_id.split("/")[0],
        "gutenberg_id": gutenberg_id,
        "metadata_assessment": {
            "result": {
                "target_candidates": target_candidates,
                "suggestive_target_candidates": [],
                "secondary_signals": [],
            }
        },
    }


class TestGenreBalancedSelection(unittest.TestCase):
    def test_distributes_evenly_across_target_genres_and_reports_shortfalls(self):
        rows = []
        # 5 stories each for science fiction and fantasy; horror gets none.
        for genre in ("science fiction", "fantasy"):
            for index in range(5):
                rows.append(
                    _row_with_target_candidates(
                        f"{genre.replace(' ', '_')}/story_{index}", [genre]
                    )
                )
        rows.append(_row_with_target_candidates("unclassified/story_0", []))

        selected, diagnostics = run_prefilter.select_genre_balanced_rows(
            rows, target_total=16  # per_genre_target = 16 // 8 = 2
        )

        self.assertEqual(diagnostics["per_genre_target"], 2)
        self.assertEqual(diagnostics["selected_counts"]["science fiction"], 2)
        self.assertEqual(diagnostics["selected_counts"]["fantasy"], 2)
        self.assertEqual(diagnostics["selected_counts"]["horror"], 0)
        self.assertEqual(diagnostics["shortfalls"]["horror"], 2)
        self.assertNotIn("science fiction", diagnostics["shortfalls"])
        self.assertEqual(diagnostics["unclassified_count"], 1)
        self.assertEqual(len(selected), 4)
        for row in selected:
            self.assertIn("selection_genre", row)

    def test_excludes_rows_with_no_target_candidates(self):
        rows = [
            _row_with_target_candidates("a/story", []),
            _row_with_target_candidates("b/story", ["horror"]),
        ]

        selected, diagnostics = run_prefilter.select_genre_balanced_rows(
            rows, target_total=8
        )

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["story_id"], "b/story")
        self.assertEqual(diagnostics["unclassified_count"], 1)

    def test_deterministic_given_same_input_order(self):
        rows = [
            _row_with_target_candidates(f"horror/story_{i}", ["horror"])
            for i in range(5)
        ]

        first, _ = run_prefilter.select_genre_balanced_rows(rows, target_total=8)
        second, _ = run_prefilter.select_genre_balanced_rows(rows, target_total=8)

        self.assertEqual(
            [row["story_id"] for row in first], [row["story_id"] for row in second]
        )

    def test_respects_gutenberg_id_cap_and_reports_skips(self):
        rows = [
            _row_with_target_candidates(
                f"horror/story_{i}", ["horror"], gutenberg_id=42
            )
            for i in range(5)
        ]

        selected, diagnostics = run_prefilter.select_genre_balanced_rows(
            rows, target_total=24, max_per_gutenberg_id=2  # per_genre_target = 3
        )

        self.assertEqual(len(selected), 2)
        self.assertEqual(diagnostics["skipped_by_gutenberg_cap"]["horror"], 3)

    def test_target_total_not_divisible_by_8_still_selects_exactly_target_total(
        self,
    ):
        # Plenty of candidates per genre so the remainder distribution is
        # the only limiting factor, not availability.
        rows = []
        for genre in run_prefilter.TARGET_GENRES:
            for index in range(20):
                rows.append(
                    _row_with_target_candidates(
                        f"{genre.replace(' ', '_')}/story_{index}", [genre]
                    )
                )

        selected, diagnostics = run_prefilter.select_genre_balanced_rows(
            rows, target_total=100  # 100 // 8 = 12, remainder 4
        )

        self.assertEqual(len(selected), 100)
        self.assertEqual(diagnostics["selected_count"], 100)
        self.assertEqual(sum(diagnostics["target_counts"].values()), 100)
        # Deterministic remainder assignment: the first 4 genres in
        # TARGET_GENRES' own fixed order get 13, the rest get 12.
        for index, genre in enumerate(run_prefilter.TARGET_GENRES):
            expected = 13 if index < 4 else 12
            self.assertEqual(diagnostics["target_counts"][genre], expected)
            self.assertEqual(diagnostics["selected_counts"][genre], expected)


class _FakeAssessmentResult:
    def __init__(
        self,
        detected_genre="horror",
        detected_genre_confidence=0.9,
        error="",
        input_tokens=100,
        output_tokens=50,
        backend_model="claude-opus-4-8",
    ):
        self.detected_genre = detected_genre
        self.detected_genre_confidence = detected_genre_confidence
        self.error = error
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.backend_model = backend_model


class TestModelAssessment(unittest.TestCase):
    def test_builds_valid_sidecar_shaped_assessment_and_detects_agreement(self):
        row = _row_with_target_candidates("horror/story", ["horror"])
        result = _FakeAssessmentResult(detected_genre="horror")

        assessment = run_prefilter.build_model_assessment(
            row, result, "run-1", "2026-08-20T00:00:00Z"
        )

        self.assertEqual(assessment["label"], "model_detect")
        self.assertEqual(assessment["run_id"], "run-1")
        self.assertEqual(assessment["provenance"]["run_id"], "run-1")
        self.assertTrue(assessment["result"]["agrees_with_metadata_rules"])

    def test_detects_disagreement(self):
        row = _row_with_target_candidates("horror/story", ["horror"])
        result = _FakeAssessmentResult(detected_genre="romance")

        assessment = run_prefilter.build_model_assessment(
            row, result, "run-1", "2026-08-20T00:00:00Z"
        )

        self.assertFalse(assessment["result"]["agrees_with_metadata_rules"])

    def test_error_result_has_no_agreement_verdict(self):
        row = _row_with_target_candidates("horror/story", ["horror"])
        result = _FakeAssessmentResult(error="backend timeout")

        assessment = run_prefilter.build_model_assessment(
            row, result, "run-1", "2026-08-20T00:00:00Z"
        )

        self.assertIsNone(assessment["result"]["agrees_with_metadata_rules"])
        self.assertEqual(assessment["evidence"]["error"], "backend timeout")

    def test_agreement_by_genre_separates_genres_and_excludes_errors_from_rate(self):
        def _result(genre, agreement):
            return {
                "selection_genre": genre,
                "model_assessment": {
                    "result": {"agrees_with_metadata_rules": agreement}
                },
            }

        results = [
            _result("horror", True),
            _result("horror", False),
            _result("horror", None),  # error case - excluded from rate
            _result("romance", True),
            _result("romance", True),
        ]

        by_genre = run_prefilter.build_agreement_by_genre(results)

        self.assertEqual(
            by_genre["horror"],
            {
                "validated_count": 2,
                "error_count": 1,
                "agreement_count": 1,
                "disagreement_count": 1,
                "agreement_rate": 0.5,
            },
        )
        self.assertEqual(
            by_genre["romance"],
            {
                "validated_count": 2,
                "error_count": 0,
                "agreement_count": 2,
                "disagreement_count": 0,
                "agreement_rate": 1.0,
            },
        )
        self.assertNotIn("fantasy", by_genre)


class TestSidecarRecords(unittest.TestCase):
    def test_builds_and_validates_sidecar_records(self):
        row = _row_with_target_candidates("horror/story", ["horror"])
        row["metadata_assessment"] = {
            "assessment_id": "gutenberg_metadata_rules:horror__story:2026-08-20T00:00:00Z",
            "label": "gutenberg_metadata_rules",
            "generated_at": "2026-08-20T00:00:00Z",
            "scope": "gutenberg_volume",
            "method": {"name": "gutenberg_subject_rules", "version": "v1"},
            "provenance": {"story_id": row["story_id"]},
            "evidence": {"raw_subjects": ["horror"], "raw_rule_matches": []},
            "result": row["metadata_assessment"]["result"],
        }
        model_assessment = run_prefilter.build_model_assessment(
            row, _FakeAssessmentResult(), "run-1", "2026-08-20T00:00:00Z"
        )

        sidecars = run_prefilter.build_sidecar_records(
            [
                {
                    "story_id": row["story_id"],
                    "story_path": row["story_path"],
                    "metadata_assessment": row["metadata_assessment"],
                    "model_assessment": model_assessment,
                }
            ]
        )

        self.assertEqual(len(sidecars), 1)
        self.assertEqual(sidecars[0]["schema_version"], "genre-sidecar-v1")
        self.assertEqual(sidecars[0]["lcats_id"], row["story_id"])
        self.assertEqual(len(sidecars[0]["assessments"]), 2)

    def test_raises_on_invalid_assessment(self):
        with self.assertRaises(ValueError):
            run_prefilter.build_sidecar_records(
                [
                    {
                        "story_id": "broken/story",
                        "story_path": "broken/story/story.json",
                        "metadata_assessment": {"label": "gutenberg_metadata_rules"},
                        "model_assessment": {"label": "model_detect"},
                    }
                ]
            )


class TestValidationCostGate(unittest.TestCase):
    def test_default_cost_estimate_matches_the_real_measured_sample(self):
        # experiments/04_genre_census/results/census_sample_summary.json:
        # 268,975 input / 8,310 output tokens over 20 real claude-opus-4-8
        # calls ($4.657875 total) - the defaults must derive from this,
        # not an invented placeholder (review finding: Codex P1, this PR -
        # an earlier draft understated the estimate by ~3.5x).
        estimate_for_20 = run_prefilter.estimate_validation_cost_usd(
            20, "claude-opus-4-8"
        )
        self.assertAlmostEqual(estimate_for_20, 4.657875, places=2)

    def test_estimate_mode_makes_no_api_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = pathlib.Path(tmp) / "results"
            output_dir.mkdir()
            manifest_path = output_dir / run_prefilter.GENRE_BALANCED_MANIFEST_FILENAME
            run_prefilter.write_jsonl(
                manifest_path,
                [_row_with_target_candidates("horror/story", ["horror"])],
            )
            args = run_prefilter.parse_args(
                [
                    "--validate",
                    "--output",
                    str(output_dir),
                    "--corpus-root",
                    str(pathlib.Path(tmp) / "corpora"),
                ]
            )

            with unittest.mock.patch(
                "lcats.analysis.corpus.assess.assess_story"
            ) as mock_assess:
                summary = run_prefilter._run_validate_mode(args)

            mock_assess.assert_not_called()
            self.assertEqual(summary["mode"], "validate-estimate-only")
            self.assertIn("estimated_cost_usd", summary)

    def test_estimate_reports_zero_selected_when_no_manifest_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = pathlib.Path(tmp) / "results"
            output_dir.mkdir()
            run_prefilter.write_jsonl(
                output_dir / run_prefilter.GENRE_BALANCED_MANIFEST_FILENAME, []
            )
            args = run_prefilter.parse_args(
                [
                    "--validate",
                    "--output",
                    str(output_dir),
                    "--corpus-root",
                    str(pathlib.Path(tmp) / "corpora"),
                ]
            )

            summary = run_prefilter._run_validate_mode(args)

            self.assertEqual(summary["selected_count"], 0)
            self.assertEqual(summary["estimated_cost_usd"], 0.0)

    def test_missing_manifest_raises_before_any_api_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = pathlib.Path(tmp) / "results"
            output_dir.mkdir()
            args = run_prefilter.parse_args(
                [
                    "--validate",
                    "--run-real-validation",
                    "--output",
                    str(output_dir),
                    "--corpus-root",
                    str(pathlib.Path(tmp) / "corpora"),
                ]
            )

            with unittest.mock.patch(
                "lcats.analysis.corpus.assess.assess_story"
            ) as mock_assess:
                with self.assertRaises(ValueError):
                    run_prefilter._run_validate_mode(args)

            mock_assess.assert_not_called()

    def test_full_scan_and_validate_are_mutually_exclusive(self):
        with self.assertRaises(SystemExit):
            run_prefilter.parse_args(["--full-scan", "--validate"])

    def test_validate_refuses_output_under_corpus_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus_root = pathlib.Path(tmp) / "corpora"
            corpus_root.mkdir()
            args = run_prefilter.parse_args(
                [
                    "--validate",
                    "--run-real-validation",
                    "--output",
                    str(corpus_root),
                    "--corpus-root",
                    str(corpus_root),
                ]
            )

            with unittest.mock.patch(
                "lcats.analysis.corpus.assess.assess_story"
            ) as mock_assess:
                with self.assertRaises(ValueError):
                    run_prefilter._run_validate_mode(args)

            mock_assess.assert_not_called()

    def test_real_run_calls_assess_story_once_per_row_and_writes_sidecars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            output_dir.mkdir(parents=True)
            _write_story(corpus_root, "horror_col", "story_a", url=None, author="A")
            row = _row_with_target_candidates("horror_col/story_a", ["horror"])
            row["selection_genre"] = "horror"  # select_genre_balanced_rows() output
            row["gutenberg_id"] = None
            row["gutenberg_url"] = None
            row["metadata_assessment"] = run_prefilter.build_metadata_assessment(
                row,
                ["horror"],
                [],
                row["metadata_assessment"]["result"],
                "2026-08-20T00:00:00Z",
                {"cache_db_path": None, "status": "not_supplied"},
            )
            manifest_path = output_dir / run_prefilter.GENRE_BALANCED_MANIFEST_FILENAME
            run_prefilter.write_jsonl(manifest_path, [row])
            args = run_prefilter.parse_args(
                [
                    "--validate",
                    "--run-real-validation",
                    "--output",
                    str(output_dir),
                    "--corpus-root",
                    str(corpus_root),
                ]
            )

            with unittest.mock.patch(
                "lcats.analysis.corpus.assess.assess_story"
            ) as mock_assess:
                mock_assess.return_value = _FakeAssessmentResult(
                    detected_genre="horror"
                )
                with unittest.mock.patch(
                    "lcats.llm.anthropic_backend.AnthropicBackend"
                ):
                    summary = run_prefilter._run_validate_mode(args)

            mock_assess.assert_called_once()
            called_path = mock_assess.call_args[0][0]
            self.assertEqual(called_path, corpus_root / row["story_path"])
            self.assertEqual(summary["selected_count"], 1)
            self.assertEqual(summary["agreement_count"], 1)
            self.assertEqual(
                summary["agreement_by_genre"]["horror"],
                {
                    "validated_count": 1,
                    "error_count": 0,
                    "agreement_count": 1,
                    "disagreement_count": 0,
                    "agreement_rate": 1.0,
                },
            )
            results_path = output_dir / run_prefilter.VALIDATION_RESULTS_FILENAME
            self.assertTrue(results_path.exists())
            written = [
                json.loads(line)
                for line in results_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(written), 1)
            self.assertEqual(written[0]["schema_version"], "genre-sidecar-v1")


class TestFullScanIntegration(unittest.TestCase):
    def test_full_scan_reports_genre_coverage_and_writes_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            cache_db = root / "cache" / "gutenbergindex.db"
            for index in range(3):
                _write_story(
                    corpus_root,
                    "sf_collection",
                    f"sf_story_{index}",
                    url=f"https://www.gutenberg.org/ebooks/{1000 + index}",
                )
            _write_story(
                corpus_root,
                "plain_collection",
                "no_url_story",
                url=None,
            )
            _write_normalized_cache(
                cache_db,
                {1000 + index: ["science fiction"] for index in range(3)},
            )

            summary = run_prefilter.run_full_scan(
                corpus_root=corpus_root,
                output_dir=output_dir,
                cache_db=cache_db,
                target_total=24,  # per_genre_target = 3
            )

            self.assertEqual(
                summary["genre_coverage"]["primary_target_genre_counts"][
                    "science fiction"
                ],
                3,
            )
            self.assertEqual(summary["genre_coverage"]["no_usable_signal_count"], 1)
            self.assertEqual(
                summary["genre_balanced_selection"]["selected_counts"][
                    "science fiction"
                ],
                3,
            )
            self.assertIn("estimated_validation_cost_usd", summary)
            manifest_rows = [
                json.loads(line)
                for line in (
                    output_dir / run_prefilter.GENRE_BALANCED_MANIFEST_FILENAME
                )
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(len(manifest_rows), 3)


if __name__ == "__main__":
    unittest.main()
