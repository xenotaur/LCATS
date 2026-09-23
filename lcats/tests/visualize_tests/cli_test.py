"""Integration/smoke tests for lcats.visualize.cli."""

import json
import tempfile
import unittest
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # non-interactive backend for testing

from parameterized import parameterized

from lcats.utils import capture
from lcats.visualize import cli as visualize_cli


def _write_summary(tmp_path, *, primary_counts, no_usable_signal_count, story_count):
    summary_path = Path(tmp_path) / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "story_count": story_count,
                "genre_coverage": {
                    "primary_target_genre_counts": primary_counts,
                    "no_usable_signal_count": no_usable_signal_count,
                },
            }
        ),
        encoding="utf-8",
    )
    return summary_path


class TestRunGenres(unittest.TestCase):
    """CLI integration/smoke tests for `lcats visualize genres`."""

    def tearDown(self):
        plt.close("all")

    def test_creates_expected_output_files(self):
        """Running genres creates PNG/SVG figures and a manifest, all non-empty."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            summary_path = _write_summary(
                tmp_dir,
                primary_counts={"fantasy": 3, "horror": 2},
                no_usable_signal_count=1,
                story_count=6,
            )
            output_dir = Path(tmp_dir) / "out"
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "genres",
                    "--summary-json",
                    str(summary_path),
                    "--output-dir",
                    str(output_dir),
                    "--formats",
                    "png,svg",
                ]
            )
            with capture.suppress_output():
                status = visualize_cli.run(parsed_args=args)

            self.assertEqual(status, 0)
            for name in (
                "genres_wordcloud.png",
                "genres_wordcloud.svg",
                "genres_bar.png",
                "genres_bar.svg",
                "genres_manifest.json",
            ):
                path = output_dir / name
                self.assertTrue(path.exists(), f"missing {name}")
                self.assertGreater(path.stat().st_size, 0, f"empty {name}")

    def test_manifest_counts_sum_to_story_count(self):
        """The manifest's counted total matches the source story_count."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            summary_path = _write_summary(
                tmp_dir,
                primary_counts={"fantasy": 3, "horror": 2},
                no_usable_signal_count=1,
                story_count=6,
            )
            output_dir = Path(tmp_dir) / "out"
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "genres",
                    "--summary-json",
                    str(summary_path),
                    "--output-dir",
                    str(output_dir),
                    "--formats",
                    "png",
                ]
            )
            with capture.suppress_output():
                visualize_cli.run(parsed_args=args)
            manifest = json.loads((output_dir / "genres_manifest.json").read_text())

        self.assertEqual(manifest["counted_total"], manifest["total_stories"])
        self.assertEqual(manifest["total_stories"], 6)
        self.assertIn("source_revision", manifest)

    def test_no_subcommand_returns_nonzero(self):
        """Running visualize with no subcommand fails and prints help."""
        parser = visualize_cli.build_visualize_parser()
        args = parser.parse_args([])
        with capture.suppress_output():
            status = visualize_cli.run(parsed_args=args)
        self.assertEqual(status, 1)

    def test_parser_prog_matches_top_level_invocation(self):
        """Usage/help text reflects `lcats visualize`, not a bare script name."""
        parser = visualize_cli.build_visualize_parser()
        self.assertEqual(parser.prog, "lcats visualize")


def _write_story(corpora_root, collection, slug, *, body):
    story_dir = Path(corpora_root) / collection / slug
    story_dir.mkdir(parents=True, exist_ok=True)
    (story_dir / "story.json").write_text(
        json.dumps({"name": slug, "body": body, "metadata": {}}), encoding="utf-8"
    )


def _write_candidates_jsonl(tmp_path, rows):
    path = Path(tmp_path) / "candidates.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for story_id, target_candidates in rows.items():
            f.write(
                json.dumps(
                    {
                        "story_id": story_id,
                        "metadata_assessment": {
                            "result": {"target_candidates": target_candidates}
                        },
                    }
                )
                + "\n"
            )
    return path


def _write_selection_manifest(tmp_path, rows):
    path = Path(tmp_path) / "manifest.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for story_id, selection_genre in rows.items():
            f.write(
                json.dumps(
                    {
                        "story_id": story_id,
                        "selection_genre": selection_genre,
                    }
                )
                + "\n"
            )
    return path


class TestRunWords(unittest.TestCase):
    """CLI integration/smoke tests for `lcats visualize words`."""

    def tearDown(self):
        plt.close("all")

    def test_whole_corpus_creates_expected_output_files(self):
        """Running words with no --genre creates figures and a manifest."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "anderson", "bell", body="dragon castle knight")
            _write_story(
                corpora_root, "anderson", "fir_tree", body="forest dragon shadow"
            )
            output_dir = Path(tmp_dir) / "out"
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "words",
                    "--corpus-root",
                    str(corpora_root),
                    "--output-dir",
                    str(output_dir),
                    "--formats",
                    "png,svg",
                ]
            )
            with capture.suppress_output():
                status = visualize_cli.run(parsed_args=args)

            self.assertEqual(status, 0)
            for name in (
                "words_wordcloud.png",
                "words_wordcloud.svg",
                "words_bar.png",
                "words_bar.svg",
                "words_manifest.json",
            ):
                path = output_dir / name
                self.assertTrue(path.exists(), f"missing {name}")
                self.assertGreater(path.stat().st_size, 0, f"empty {name}")

            manifest = json.loads((output_dir / "words_manifest.json").read_text())
            self.assertEqual(manifest["story_count"], 2)
            self.assertIn("corpus_source_revision", manifest)
            self.assertNotIn("genre", manifest)
            self.assertEqual(manifest["top_words"]["dragon"], 2)

    def test_genre_subset_filters_and_emits_dual_revision(self):
        """--genre restricts to matching stories and discloses both snapshots."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "anderson", "bell", body="dragon castle")
            _write_story(corpora_root, "anderson", "fir_tree", body="detective clue")
            candidates_path = _write_candidates_jsonl(
                tmp_dir,
                {
                    "anderson/bell": ["fantasy"],
                    "anderson/fir_tree": ["mystery"],
                },
            )
            output_dir = Path(tmp_dir) / "out"
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "words",
                    "--corpus-root",
                    str(corpora_root),
                    "--genre",
                    "fantasy",
                    "--candidates-jsonl",
                    str(candidates_path),
                    "--output-dir",
                    str(output_dir),
                    "--formats",
                    "png",
                ]
            )
            with capture.suppress_output():
                status = visualize_cli.run(parsed_args=args)
            manifest = json.loads((output_dir / "words_manifest.json").read_text())

        self.assertEqual(status, 0)
        self.assertEqual(manifest["story_count"], 1)
        self.assertEqual(manifest["genre"], "fantasy")
        self.assertIn("candidates_source_revision", manifest)
        self.assertIn("corpus_source_revision", manifest)
        self.assertIn("dragon", manifest["top_words"])
        self.assertNotIn("detective", manifest["top_words"])

    def test_missing_story_in_corpus_raises(self):
        """A candidates.jsonl story_id absent from the corpus snapshot raises."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "anderson", "bell", body="dragon castle")
            candidates_path = _write_candidates_jsonl(
                tmp_dir, {"anderson/nonexistent": ["fantasy"]}
            )
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "words",
                    "--corpus-root",
                    str(corpora_root),
                    "--genre",
                    "fantasy",
                    "--candidates-jsonl",
                    str(candidates_path),
                    "--output-dir",
                    str(Path(tmp_dir) / "out"),
                ]
            )
            with capture.suppress_output(), self.assertRaises(ValueError):
                visualize_cli.run(parsed_args=args)

    def test_missing_story_in_candidates_raises(self):
        """A corpus story absent from candidates.jsonl also raises (bidirectional)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "anderson", "bell", body="dragon castle")
            _write_story(corpora_root, "anderson", "fir_tree", body="detective clue")
            candidates_path = _write_candidates_jsonl(
                tmp_dir, {"anderson/bell": ["fantasy"]}
            )
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "words",
                    "--corpus-root",
                    str(corpora_root),
                    "--genre",
                    "fantasy",
                    "--candidates-jsonl",
                    str(candidates_path),
                    "--output-dir",
                    str(Path(tmp_dir) / "out"),
                ]
            )
            with capture.suppress_output(), self.assertRaises(ValueError):
                visualize_cli.run(parsed_args=args)

    def test_non_positive_top_k_raises(self):
        """--top-k below 1 raises a clear ValueError, not a rendering crash."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "anderson", "bell", body="dragon castle knight")
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "words",
                    "--corpus-root",
                    str(corpora_root),
                    "--top-k",
                    "0",
                    "--output-dir",
                    str(Path(tmp_dir) / "out"),
                ]
            )
            with capture.suppress_output(), self.assertRaises(ValueError):
                visualize_cli.run(parsed_args=args)

    def test_empty_frequencies_raises_before_rendering(self):
        """A selection with no usable tokens raises a clear error, not a WordCloud crash."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "anderson", "bell", body="a an to")
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "words",
                    "--corpus-root",
                    str(corpora_root),
                    "--output-dir",
                    str(Path(tmp_dir) / "out"),
                ]
            )
            with capture.suppress_output(), self.assertRaises(ValueError):
                visualize_cli.run(parsed_args=args)

    def test_help_discloses_preprocessing_defaults(self):
        """words --help documents the tokenization/stopword defaults."""
        parser = visualize_cli.build_visualize_parser()
        with capture.capture_output() as captured, self.assertRaises(SystemExit):
            parser.parse_args(["words", "--help"])
        help_text = captured.stdout.getvalue()
        for term in ("lowercased", "alphabetic", "3", "stopword"):
            self.assertIn(term, help_text)


class TestRunTfidf(unittest.TestCase):
    """CLI integration/smoke tests for `lcats visualize tfidf`."""

    def tearDown(self):
        plt.close("all")

    def test_whole_corpus_creates_expected_output_files(self):
        """Running tfidf with no --genre creates figures and a manifest."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "anderson", "bell", body="dragon castle knight")
            _write_story(
                corpora_root, "anderson", "fir_tree", body="forest dragon shadow"
            )
            output_dir = Path(tmp_dir) / "out"
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "tfidf",
                    "--corpus-root",
                    str(corpora_root),
                    "--output-dir",
                    str(output_dir),
                    "--formats",
                    "png,svg",
                ]
            )
            with capture.suppress_output():
                status = visualize_cli.run(parsed_args=args)

            self.assertEqual(status, 0)
            for name in ("tfidf_bar.png", "tfidf_bar.svg", "tfidf_manifest.json"):
                path = output_dir / name
                self.assertTrue(path.exists(), f"missing {name}")
                self.assertGreater(path.stat().st_size, 0, f"empty {name}")

            manifest = json.loads((output_dir / "tfidf_manifest.json").read_text())
            self.assertEqual(manifest["story_count"], 2)
            self.assertIn("corpus_source_revision", manifest)
            self.assertNotIn("genre", manifest)
            self.assertIn("dragon", manifest["top_terms"])
            self.assertEqual(manifest["mode"], "salience")

    def test_genre_subset_filters_and_emits_dual_revision(self):
        """--genre restricts the group and discloses both snapshots."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "anderson", "bell", body="dragon castle")
            _write_story(corpora_root, "anderson", "fir_tree", body="detective clue")
            candidates_path = _write_candidates_jsonl(
                tmp_dir,
                {
                    "anderson/bell": ["fantasy"],
                    "anderson/fir_tree": ["mystery"],
                },
            )
            output_dir = Path(tmp_dir) / "out"
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "tfidf",
                    "--corpus-root",
                    str(corpora_root),
                    "--genre",
                    "fantasy",
                    "--candidates-jsonl",
                    str(candidates_path),
                    "--output-dir",
                    str(output_dir),
                    "--formats",
                    "png",
                ]
            )
            with capture.suppress_output():
                status = visualize_cli.run(parsed_args=args)
            manifest = json.loads((output_dir / "tfidf_manifest.json").read_text())

        self.assertEqual(status, 0)
        self.assertEqual(manifest["story_count"], 1)
        self.assertEqual(manifest["genre"], "fantasy")
        self.assertIn("candidates_source_revision", manifest)
        self.assertIn("corpus_source_revision", manifest)
        self.assertIn("dragon", manifest["top_terms"])
        self.assertNotIn("detective", manifest["top_terms"])

    def test_missing_story_in_corpus_raises(self):
        """A candidates.jsonl story_id absent from the corpus snapshot raises."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "anderson", "bell", body="dragon castle")
            candidates_path = _write_candidates_jsonl(
                tmp_dir, {"anderson/nonexistent": ["fantasy"]}
            )
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "tfidf",
                    "--corpus-root",
                    str(corpora_root),
                    "--genre",
                    "fantasy",
                    "--candidates-jsonl",
                    str(candidates_path),
                    "--output-dir",
                    str(Path(tmp_dir) / "out"),
                ]
            )
            with capture.suppress_output(), self.assertRaises(ValueError):
                visualize_cli.run(parsed_args=args)

    def test_non_positive_top_k_raises(self):
        """--top-k below 1 raises a clear ValueError, not a rendering crash."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "anderson", "bell", body="dragon castle knight")
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "tfidf",
                    "--corpus-root",
                    str(corpora_root),
                    "--top-k",
                    "0",
                    "--output-dir",
                    str(Path(tmp_dir) / "out"),
                ]
            )
            with capture.suppress_output(), self.assertRaises(ValueError):
                visualize_cli.run(parsed_args=args)

    def test_help_discloses_preprocessing_defaults(self):
        """tfidf --help documents the tokenization/stopword defaults."""
        parser = visualize_cli.build_visualize_parser()
        with capture.capture_output() as captured, self.assertRaises(SystemExit):
            parser.parse_args(["tfidf", "--help"])
        help_text = captured.stdout.getvalue()
        for term in ("lowercased", "alphabetic", "3", "stopword"):
            self.assertIn(term, help_text)

    def test_contrast_without_genre_raises(self):
        """--contrast with no --genre raises a clear, documented error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "anderson", "bell", body="dragon castle knight")
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "tfidf",
                    "--corpus-root",
                    str(corpora_root),
                    "--contrast",
                    "--output-dir",
                    str(Path(tmp_dir) / "out"),
                ]
            )
            with capture.suppress_output(), self.assertRaises(ValueError) as ctx:
                visualize_cli.run(parsed_args=args)
            self.assertIn("--contrast requires --genre", str(ctx.exception))

    def test_contrast_produces_distinct_result_and_discloses_mode(self):
        """--contrast with --genre yields a genuine group-vs-rest ranking,
        visibly different from the default salience-mode ranking for the
        same genre, and discloses mode: contrast in the manifest."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(
                corpora_root, "anderson", "bell", body="dragon dragon castle shared"
            )
            _write_story(
                corpora_root, "anderson", "fir_tree", body="shared detective clue clue"
            )
            candidates_path = _write_candidates_jsonl(
                tmp_dir,
                {
                    "anderson/bell": ["fantasy"],
                    "anderson/fir_tree": ["mystery"],
                },
            )
            common_args = [
                "--corpus-root",
                str(corpora_root),
                "--genre",
                "fantasy",
                "--candidates-jsonl",
                str(candidates_path),
                "--formats",
                "png",
            ]
            parser = visualize_cli.build_visualize_parser()

            salience_dir = Path(tmp_dir) / "out_salience"
            salience_args = parser.parse_args(
                ["tfidf", *common_args, "--output-dir", str(salience_dir)]
            )
            with capture.suppress_output():
                salience_status = visualize_cli.run(parsed_args=salience_args)
            salience_manifest = json.loads(
                (salience_dir / "tfidf_manifest.json").read_text()
            )

            contrast_dir = Path(tmp_dir) / "out_contrast"
            contrast_args = parser.parse_args(
                [
                    "tfidf",
                    *common_args,
                    "--contrast",
                    "--output-dir",
                    str(contrast_dir),
                ]
            )
            with capture.suppress_output():
                contrast_status = visualize_cli.run(parsed_args=contrast_args)
            contrast_manifest = json.loads(
                (contrast_dir / "tfidf_manifest.json").read_text()
            )

        self.assertEqual(salience_status, 0)
        self.assertEqual(contrast_status, 0)
        self.assertEqual(salience_manifest["mode"], "salience")
        self.assertEqual(contrast_manifest["mode"], "contrast")
        self.assertNotEqual(
            salience_manifest["top_terms"], contrast_manifest["top_terms"]
        )
        self.assertIn("dragon", contrast_manifest["top_terms"])
        self.assertNotIn("shared", contrast_manifest["top_terms"])


class TestRunTopics(unittest.TestCase):
    """CLI integration/smoke tests for `lcats visualize topics`."""

    def tearDown(self):
        plt.close("all")

    def test_creates_expected_output_files(self):
        """Running topics creates one bar chart per topic and a manifest."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(
                corpora_root,
                "anderson",
                "bell",
                body="dragon castle knight dragon castle knight dragon",
            )
            _write_story(
                corpora_root,
                "anderson",
                "fir_tree",
                body="ocean ship sailor ocean ship sailor ocean",
            )
            output_dir = Path(tmp_dir) / "out"
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "topics",
                    "--corpus-root",
                    str(corpora_root),
                    "--n-topics",
                    "2",
                    "--top-k",
                    "5",
                    "--output-dir",
                    str(output_dir),
                    "--formats",
                    "png,svg",
                ]
            )
            with capture.suppress_output():
                status = visualize_cli.run(parsed_args=args)

            self.assertEqual(status, 0)
            manifest = json.loads((output_dir / "topics_manifest.json").read_text())

            self.assertEqual(manifest["story_count"], 2)
            self.assertEqual(manifest["n_topics"], 2)
            self.assertIn("corpus_source_revision", manifest)
            self.assertEqual(manifest["seed"], 42)
            for topic_label in manifest["topics"]:
                for fmt in ("png", "svg"):
                    path = output_dir / f"{topic_label}_bar.{fmt}"
                    self.assertTrue(path.exists(), f"missing {path.name}")
                    self.assertGreater(path.stat().st_size, 0, f"empty {path.name}")

    def test_n_topics_clamped_does_not_raise(self):
        """Requesting more topics than the corpus supports does not crash."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "anderson", "bell", body="dragon castle knight")
            output_dir = Path(tmp_dir) / "out"
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "topics",
                    "--corpus-root",
                    str(corpora_root),
                    "--n-topics",
                    "10",
                    "--output-dir",
                    str(output_dir),
                ]
            )
            with capture.suppress_output():
                status = visualize_cli.run(parsed_args=args)
            self.assertEqual(status, 0)

    def test_non_positive_n_topics_raises(self):
        """--n-topics below 1 raises a clear ValueError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "anderson", "bell", body="dragon castle knight")
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "topics",
                    "--corpus-root",
                    str(corpora_root),
                    "--n-topics",
                    "0",
                    "--output-dir",
                    str(Path(tmp_dir) / "out"),
                ]
            )
            with capture.suppress_output(), self.assertRaises(ValueError):
                visualize_cli.run(parsed_args=args)

    def test_non_positive_top_k_raises(self):
        """--top-k below 1 raises a clear ValueError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "anderson", "bell", body="dragon castle knight")
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "topics",
                    "--corpus-root",
                    str(corpora_root),
                    "--top-k",
                    "0",
                    "--output-dir",
                    str(Path(tmp_dir) / "out"),
                ]
            )
            with capture.suppress_output(), self.assertRaises(ValueError):
                visualize_cli.run(parsed_args=args)

    def test_non_positive_max_iter_raises(self):
        """--max-iter below 1 raises a clear ValueError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "anderson", "bell", body="dragon castle knight")
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "topics",
                    "--corpus-root",
                    str(corpora_root),
                    "--max-iter",
                    "0",
                    "--output-dir",
                    str(Path(tmp_dir) / "out"),
                ]
            )
            with capture.suppress_output(), self.assertRaises(ValueError):
                visualize_cli.run(parsed_args=args)

    def test_max_iter_disclosed_in_manifest(self):
        """The manifest discloses the max_iter hyperparameter used."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(
                corpora_root,
                "anderson",
                "bell",
                body="dragon castle knight dragon castle knight dragon",
            )
            output_dir = Path(tmp_dir) / "out"
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "topics",
                    "--corpus-root",
                    str(corpora_root),
                    "--n-topics",
                    "1",
                    "--max-iter",
                    "50",
                    "--output-dir",
                    str(output_dir),
                ]
            )
            with capture.suppress_output():
                status = visualize_cli.run(parsed_args=args)
            manifest = json.loads((output_dir / "topics_manifest.json").read_text())

        self.assertEqual(status, 0)
        self.assertEqual(manifest["max_iter"], 50)

    def test_init_option_disclosed_in_manifest(self):
        """--init is honored and disclosed in the manifest."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(
                corpora_root,
                "anderson",
                "bell",
                body="dragon castle knight dragon castle knight dragon",
            )
            output_dir = Path(tmp_dir) / "out"
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "topics",
                    "--corpus-root",
                    str(corpora_root),
                    "--n-topics",
                    "1",
                    "--init",
                    "random",
                    "--output-dir",
                    str(output_dir),
                ]
            )
            with capture.suppress_output():
                status = visualize_cli.run(parsed_args=args)
            manifest = json.loads((output_dir / "topics_manifest.json").read_text())

        self.assertEqual(status, 0)
        self.assertEqual(manifest["init"], "random")

    def test_help_discloses_preprocessing_defaults(self):
        """topics --help documents the tokenization/stopword defaults."""
        parser = visualize_cli.build_visualize_parser()
        with capture.capture_output() as captured, self.assertRaises(SystemExit):
            parser.parse_args(["topics", "--help"])
        help_text = captured.stdout.getvalue()
        for term in ("lowercased", "alphabetic", "3", "stopword"):
            self.assertIn(term, help_text)


class TestRunCompare(unittest.TestCase):
    """CLI integration/smoke tests for `lcats visualize compare`."""

    def tearDown(self):
        plt.close("all")

    def test_manifest_genre_vs_complement_creates_figures_data_and_manifest(self):
        """Running compare writes figures, authoritative CSV, and manifest."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(
                corpora_root,
                "sf",
                "rocket",
                body="rocket rocket planet shared",
            )
            _write_story(
                corpora_root,
                "fantasy",
                "dragon",
                body="dragon dragon castle shared",
            )
            candidates_path = _write_candidates_jsonl(
                tmp_dir,
                {
                    "sf/rocket": ["science fiction"],
                    "fantasy/dragon": ["fantasy"],
                },
            )
            manifest_path = _write_selection_manifest(
                tmp_dir,
                {
                    "sf/rocket": "science fiction",
                    "fantasy/dragon": "fantasy",
                },
            )
            output_dir = Path(tmp_dir) / "out"
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "compare",
                    "--corpus-root",
                    str(corpora_root),
                    "--candidates-jsonl",
                    str(candidates_path),
                    "--universe",
                    "manifest",
                    "--manifest",
                    str(manifest_path),
                    "--right-genre",
                    "science fiction",
                    "--right-reference",
                    "complement",
                    "--metric",
                    "per_million",
                    "--output-dir",
                    str(output_dir),
                    "--formats",
                    "png,svg",
                ]
            )

            with capture.suppress_output():
                status = visualize_cli.run(parsed_args=args)

            expected_files = (
                "comparison_mirrored.png",
                "comparison_mirrored.svg",
                "comparison.csv",
                "comparison_manifest.json",
            )
            for name in expected_files:
                path = output_dir / name
                self.assertTrue(path.exists(), f"missing {name}")
                self.assertGreater(path.stat().st_size, 0, f"empty {name}")
            manifest = json.loads((output_dir / "comparison_manifest.json").read_text())

        self.assertEqual(status, 0)
        self.assertEqual(manifest["schema_version"], "lcats-comparison-v1")
        self.assertEqual(manifest["universe"]["story_count"], 2)
        self.assertEqual(manifest["right"]["story_count"], 1)
        self.assertEqual(manifest["left"]["story_count"], 1)
        self.assertEqual(manifest["metrics"]["left"]["name"], "per_million")
        self.assertEqual(manifest["style"], "mirrored")
        self.assertIn("figures", manifest["cli"]["outputs"])

    def test_selection_membership_loads_manifest_for_corpus_universe(self):
        """Selection labels are loaded even when U remains the whole corpus."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(
                corpora_root,
                "sf",
                "rocket",
                body="rocket rocket planet shared",
            )
            _write_story(
                corpora_root,
                "fantasy",
                "dragon",
                body="dragon dragon castle shared",
            )
            _write_story(
                corpora_root,
                "mystery",
                "clue",
                body="detective clue shared",
            )
            candidates_path = _write_candidates_jsonl(
                tmp_dir,
                {
                    "sf/rocket": ["science fiction"],
                    "fantasy/dragon": ["fantasy"],
                    "mystery/clue": ["mystery"],
                },
            )
            manifest_path = _write_selection_manifest(
                tmp_dir,
                {
                    "sf/rocket": "selection-sf",
                },
            )
            output_dir = Path(tmp_dir) / "out"
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "compare",
                    "--corpus-root",
                    str(corpora_root),
                    "--candidates-jsonl",
                    str(candidates_path),
                    "--universe",
                    "corpus",
                    "--manifest",
                    str(manifest_path),
                    "--membership-mode",
                    "selection",
                    "--right-genre",
                    "selection-sf",
                    "--right-reference",
                    "complement",
                    "--metric",
                    "raw_count",
                    "--top-k",
                    "3",
                    "--output-dir",
                    str(output_dir),
                    "--formats",
                    "png",
                ]
            )

            with capture.suppress_output():
                status = visualize_cli.run(parsed_args=args)
            manifest = json.loads((output_dir / "comparison_manifest.json").read_text())

        self.assertEqual(status, 0)
        self.assertEqual(manifest["universe"]["kind"], "corpus")
        self.assertEqual(manifest["universe"]["story_count"], 3)
        self.assertEqual(manifest["right"]["story_count"], 1)
        self.assertEqual(manifest["left"]["story_count"], 2)

    def test_reference_overlay_rejects_incompatible_side_metrics(self):
        """Overlay CLI requests fail before a figure is written when metrics differ."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "sf", "rocket", body="rocket planet")
            _write_story(corpora_root, "fantasy", "dragon", body="dragon castle")
            candidates_path = _write_candidates_jsonl(
                tmp_dir,
                {
                    "sf/rocket": ["science fiction"],
                    "fantasy/dragon": ["fantasy"],
                },
            )
            output_dir = Path(tmp_dir) / "out"
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "compare",
                    "--corpus-root",
                    str(corpora_root),
                    "--candidates-jsonl",
                    str(candidates_path),
                    "--right-genre",
                    "science fiction",
                    "--right-reference",
                    "complement",
                    "--style",
                    "reference-overlay",
                    "--left-metric",
                    "raw_count",
                    "--right-metric",
                    "per_million",
                    "--output-dir",
                    str(output_dir),
                ]
            )

            with capture.suppress_output(), self.assertRaises(ValueError):
                visualize_cli.run(parsed_args=args)

            self.assertFalse(output_dir.exists())

    def test_primary_membership_mode_rejected_until_source_adapter_exists(self):
        """Primary genre membership cannot silently produce empty selections."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "sf", "rocket", body="rocket planet")
            candidates_path = _write_candidates_jsonl(
                tmp_dir, {"sf/rocket": ["science fiction"]}
            )
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "compare",
                    "--corpus-root",
                    str(corpora_root),
                    "--candidates-jsonl",
                    str(candidates_path),
                    "--right-genre",
                    "science fiction",
                    "--membership-mode",
                    "primary",
                    "--output-dir",
                    str(Path(tmp_dir) / "out"),
                ]
            )

            with capture.suppress_output(), self.assertRaises(ValueError) as ctx:
                visualize_cli.run(parsed_args=args)

        self.assertIn("primary is not available", str(ctx.exception))

    def test_selection_membership_requires_manifest_source(self):
        """Selection membership cannot silently run without selection labels."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "sf", "rocket", body="rocket planet")
            candidates_path = _write_candidates_jsonl(
                tmp_dir, {"sf/rocket": ["science fiction"]}
            )
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "compare",
                    "--corpus-root",
                    str(corpora_root),
                    "--candidates-jsonl",
                    str(candidates_path),
                    "--right-genre",
                    "science fiction",
                    "--membership-mode",
                    "selection",
                    "--output-dir",
                    str(Path(tmp_dir) / "out"),
                ]
            )

            with capture.suppress_output(), self.assertRaises(ValueError) as ctx:
                visualize_cli.run(parsed_args=args)

        self.assertIn("selection requires --manifest", str(ctx.exception))

    def test_explicit_ordering_rejected_until_explicit_terms_are_exposed(self):
        """Explicit ordering cannot degrade into alphabetical ordering."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "sf", "rocket", body="rocket planet")
            candidates_path = _write_candidates_jsonl(
                tmp_dir, {"sf/rocket": ["science fiction"]}
            )
            parser = visualize_cli.build_visualize_parser()
            args = parser.parse_args(
                [
                    "compare",
                    "--corpus-root",
                    str(corpora_root),
                    "--candidates-jsonl",
                    str(candidates_path),
                    "--right-genre",
                    "science fiction",
                    "--order-by",
                    "explicit",
                    "--output-dir",
                    str(Path(tmp_dir) / "out"),
                ]
            )

            with capture.suppress_output(), self.assertRaises(ValueError) as ctx:
                visualize_cli.run(parsed_args=args)

        self.assertIn("--order-by explicit requires", str(ctx.exception))

    def test_compare_help_lists_selector_and_output_controls(self):
        """compare --help documents the new selector and output options."""
        parser = visualize_cli.build_visualize_parser()
        with capture.capture_output() as captured, self.assertRaises(SystemExit):
            parser.parse_args(["compare", "--help"])
        help_text = captured.stdout.getvalue()
        for term in ("--universe", "--right-genre", "--right-reference", "--style"):
            self.assertIn(term, help_text)


class TestRunCompareMany(unittest.TestCase):
    """CLI integration tests for `lcats visualize compare-many`."""

    def tearDown(self):
        plt.close("all")

    def _fixture(self, tmp_dir):
        corpora_root = Path(tmp_dir) / "corpora"
        stories = {
            "sf/rocket": ("rocket rocket planet shared", ["science fiction"]),
            "fantasy/dragon": ("dragon dragon castle shared", ["fantasy"]),
            "fantasy/elf": ("elf castle shared rocket", ["fantasy", "science fiction"]),
            "mystery/clue": ("detective clue shared", ["mystery"]),
        }
        for story_id, (body, _) in stories.items():
            collection, slug = story_id.split("/")
            _write_story(corpora_root, collection, slug, body=body)
        candidates_path = _write_candidates_jsonl(
            tmp_dir, {story_id: genres for story_id, (_, genres) in stories.items()}
        )
        return corpora_root, candidates_path

    def _run(self, tmp_dir, *extra):
        corpora_root, candidates_path = self._fixture(tmp_dir)
        output_dir = Path(tmp_dir) / "out"
        parser = visualize_cli.build_visualize_parser()
        args = parser.parse_args(
            [
                "compare-many",
                "--corpus-root",
                str(corpora_root),
                "--candidates-jsonl",
                str(candidates_path),
                "--output-dir",
                str(output_dir),
                *extra,
            ]
        )
        with capture.suppress_output():
            status = visualize_cli.run(parsed_args=args)
        manifest = json.loads(
            (output_dir / "comparison_nway_manifest.json").read_text()
        )
        return status, output_dir, manifest

    def test_direct_panels_write_figures_csv_and_manifest(self):
        """Three ordered panels produce hashed figures, CSV, and a manifest."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            status, output_dir, manifest = self._run(
                tmp_dir,
                "--panels",
                "science fiction,fantasy,mystery",
                "--formats",
                "png,svg,pdf",
            )
            names = sorted(path.name for path in output_dir.iterdir())

        self.assertEqual(status, 0)
        self.assertEqual(
            names,
            [
                "comparison_nway.csv",
                "comparison_nway.pdf",
                "comparison_nway.png",
                "comparison_nway.svg",
                "comparison_nway_manifest.json",
            ],
        )
        self.assertEqual(manifest["schema_version"], "lcats-nway-comparison-v2")
        self.assertEqual(
            [panel["key"] for panel in manifest["panels"]],
            ["science_fiction", "fantasy", "mystery"],
        )
        self.assertEqual(manifest["reference_policy"], "common")
        self.assertEqual(manifest["vocabulary"]["policy"], "reference_value")
        self.assertEqual(
            manifest["generator"]["command"], "lcats visualize compare-many"
        )
        overlap = manifest["panel_overlaps"][0]
        self.assertEqual(overlap["story_ids"], ["fantasy/elf"])
        self.assertFalse(manifest["membership"]["partition_claim"])

    def test_complement_panels_with_per_panel_reference(self):
        """Complement panels are compared with their own bases, S."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            status, _, manifest = self._run(
                tmp_dir,
                "--panels",
                "fantasy,mystery",
                "--panel-mode",
                "complement",
                "--reference",
                "per-panel-complement",
                "--formats",
                "svg",
            )

        self.assertEqual(status, 0)
        self.assertEqual(manifest["panel_mode"], "complement")
        self.assertEqual(manifest["vocabulary"]["policy"], "max_absolute_deviation")
        self.assertEqual(
            [record["role"] for record in manifest["complements"]],
            ["panel", "reference", "panel", "reference"],
        )
        references = {ref["panel_key"]: ref for ref in manifest["references"]}
        self.assertEqual(
            references["fantasy"]["story_ids"], ["fantasy/dragon", "fantasy/elf"]
        )

    def test_kabob_layout_flags_are_recorded(self):
        """Preset choice and explicit overrides reach the rendering manifest."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            _, _, manifest = self._run(
                tmp_dir,
                "--panels",
                "science fiction,fantasy,mystery",
                "--layout",
                "kabob",
                "--no-hatching",
                "--highlight",
                "global",
                "--max-columns",
                "2",
                "--formats",
                "png",
            )

        spec = manifest["rendering"]["render_spec"]
        self.assertEqual(spec["preset"], "kabob")
        self.assertEqual(spec["reference_direction"], "right")
        self.assertEqual(spec["term_labels"], "outside-right")
        self.assertFalse(spec["hatching"])
        self.assertEqual(spec["highlight"], "global")
        self.assertEqual(
            manifest["rendering"]["layout"]["bands"],
            [["science_fiction", "fantasy"], ["mystery"]],
        )

    def test_no_reference_uses_panel_values(self):
        """The no-reference policy writes values and no deviations."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            _, output_dir, manifest = self._run(
                tmp_dir,
                "--panels",
                "fantasy,mystery",
                "--reference",
                "none",
                "--formats",
                "png",
            )
            with (output_dir / "comparison_nway.csv").open(encoding="utf-8") as f:
                header = f.readline()

        self.assertEqual(manifest["rendering"]["plotted_quantity"], "value")
        self.assertIn("plotted_value", header)
        self.assertEqual(manifest["references"], [])

    @parameterized.expand(
        [
            ("one_panel", ["--panels", "fantasy"], "at least two"),
            ("repeated_panel", ["--panels", "fantasy,fantasy"], "must not repeat"),
            (
                "genre_reference_without_genre",
                ["--panels", "fantasy,mystery", "--reference", "genre"],
                "--reference-genre",
            ),
            (
                "reference_genre_without_genre_policy",
                ["--panels", "fantasy,mystery", "--reference-genre", "fantasy"],
                "only valid",
            ),
            (
                "zero_columns",
                ["--panels", "fantasy,mystery", "--max-columns", "0"],
                "--max-columns",
            ),
            (
                "reference_value_without_reference",
                [
                    "--panels",
                    "fantasy,mystery",
                    "--reference",
                    "none",
                    "--vocabulary",
                    "reference_value",
                ],
                "reference_value",
            ),
        ]
    )
    def test_invalid_requests_raise(self, _name, extra, message):
        """Invalid panel, reference, and layout requests fail clearly."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root, candidates_path = self._fixture(tmp_dir)
            args = visualize_cli.build_visualize_parser().parse_args(
                [
                    "compare-many",
                    "--corpus-root",
                    str(corpora_root),
                    "--candidates-jsonl",
                    str(candidates_path),
                    "--output-dir",
                    str(Path(tmp_dir) / "out"),
                    *extra,
                ]
            )
            with self.assertRaisesRegex(ValueError, message):
                visualize_cli.run(parsed_args=args)

    def test_compare_many_help_lists_policy_and_layout_controls(self):
        """compare-many --help documents reference, scale, and layout options."""
        parser = visualize_cli.build_visualize_parser()
        with capture.capture_output() as captured, self.assertRaises(SystemExit):
            parser.parse_args(["compare-many", "--help"])
        help_text = captured.stdout.getvalue()
        for term in (
            "--panels",
            "--panel-mode",
            "--reference",
            "--scale",
            "--layout",
            "--max-columns",
            "--term-labels",
        ):
            self.assertIn(term, help_text)


if __name__ == "__main__":
    unittest.main()
