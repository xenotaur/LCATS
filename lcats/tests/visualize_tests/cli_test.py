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


if __name__ == "__main__":
    unittest.main()
