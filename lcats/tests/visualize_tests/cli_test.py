"""Integration/smoke tests for lcats.visualize.cli."""

import json
import tempfile
import unittest
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # non-interactive backend for testing

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


if __name__ == "__main__":
    unittest.main()
