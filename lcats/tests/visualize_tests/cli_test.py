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


if __name__ == "__main__":
    unittest.main()
