"""Tests for lcats.visualize.nway_outputs."""

import csv
import json
import pathlib
import tempfile
import unittest

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # non-interactive backend for testing

from parameterized import parameterized

from lcats.utils import capture
from lcats.visualize import comparison
from lcats.visualize import nway_outputs
from lcats.visualize import rendering


def _corpus():
    return comparison.ComparisonCorpus(
        documents=(
            comparison.ComparisonDocument(
                "a/one",
                "dragon dragon castle shared",
                candidate_genres=("fantasy",),
            ),
            comparison.ComparisonDocument(
                "b/two",
                "rocket rocket shared castle",
                candidate_genres=("science fiction", "fantasy"),
            ),
            comparison.ComparisonDocument(
                "c/three",
                "detective clue shared clue",
                candidate_genres=("mystery",),
            ),
            comparison.ComparisonDocument(
                "d/four",
                "ghost ghost shared dragon",
                candidate_genres=("horror",),
            ),
        ),
        source_path="fixture",
        source_revision="rev",
    )


def _result(panel_mode=comparison.NWayPanelMode.DIRECT):
    genres = ("fantasy", "science fiction", "mystery", "horror")
    return comparison.compare_many(
        _corpus(),
        comparison.NWayComparisonSpec(
            universe=comparison.UniverseSpec(),
            reference=comparison.Selector(comparison.SelectorKind.ALL, label="U"),
            panels=tuple(
                comparison.NWayPanelSpec(
                    genre.replace(" ", "_"),
                    comparison.Selector(
                        comparison.SelectorKind.GENRE, genre=genre, label=genre
                    ),
                )
                for genre in genres
            ),
            metric=comparison.MetricSpec(comparison.MetricName.PER_MILLION),
            vocabulary=comparison.NWayVocabularySpec(top_k=6),
            panel_mode=panel_mode,
        ),
    )


def _read_csv(path):
    with pathlib.Path(path).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


class TestWriteNWayOutputs(unittest.TestCase):
    """Figures, CSV, and manifest are written as one reproducible bundle."""

    def tearDown(self):
        plt.close("all")

    def _write(self, output_dir, **kwargs):
        options = {
            "stem": "nway",
            "render_spec": rendering.NWayRenderSpec.from_preset("kabob", max_columns=3),
            "formats": ("png", "svg", "pdf"),
        }
        options.update(kwargs)
        with capture.suppress_output():
            return nway_outputs.write_nway_outputs(
                _result(), output_dir=output_dir, **options
            )

    def test_every_output_hash_matches_the_written_file(self):
        """Manifest hashes are computed from the bytes on disk."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest = self._write(tmp_dir)
            outputs = manifest["outputs"]
            written = json.loads(
                (pathlib.Path(tmp_dir) / "nway_manifest.json").read_text()
            )
            for entry in [outputs["csv"], *outputs["figures"]]:
                with self.subTest(path=entry["path"]):
                    self.assertEqual(
                        nway_outputs.sha256_file(pathlib.Path(tmp_dir) / entry["path"]),
                        entry["sha256"],
                    )

        self.assertEqual(written, json.loads(json.dumps(manifest)))
        self.assertEqual(
            [figure["format"] for figure in outputs["figures"]], ["png", "svg", "pdf"]
        )

    def test_csv_reproduces_every_plotted_value_and_layout_decision(self):
        """Each CSV row matches the plan's plotted value, limits, and position."""
        result = _result()
        spec = rendering.NWayRenderSpec.from_preset("kabob", max_columns=3)
        plan = rendering.build_nway_render_plan(result, spec)
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest = self._write(tmp_dir, render_spec=spec)
            records = _read_csv(pathlib.Path(tmp_dir) / "nway.csv")

        self.assertEqual(len(records), manifest["outputs"]["csv"]["row_count"])
        self.assertEqual(len(records), len(result.rows) * len(plan.panel_keys))
        for record in records:
            with self.subTest(term=record["term"], panel=record["panel_key"]):
                self.assertAlmostEqual(
                    float(record["plotted_value"]),
                    float(record["value"]) - float(record["reference_value"]),
                )
                self.assertEqual(
                    (float(record["axis_min"]), float(record["axis_max"])),
                    plan.panel_limits[record["panel_key"]],
                )
                self.assertEqual(
                    (int(record["layout_band"]), int(record["layout_column"])),
                    plan.panel_position(record["panel_key"]),
                )
        self.assertEqual(manifest["rendering"]["layout"]["band_count"], 2)
        self.assertEqual(
            {
                (r["panel_key"], r["term"])
                for r in records
                if r["highlighted"] == "True"
            },
            set(plan.highlighted),
        )

    def test_shared_scale_panels_have_identical_limits_in_manifest(self):
        """The manifest proves the common visible scale."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest = self._write(tmp_dir)

        limits = manifest["rendering"]["scale"]["panel_axis_limits"]
        self.assertEqual(len({tuple(value) for value in limits.values()}), 1)
        self.assertEqual(manifest["rendering"]["scale"]["policy"], "shared")

    def test_rewriting_same_inputs_is_byte_identical(self):
        """Stripped metadata makes CSV and figures reproducible."""
        with (
            tempfile.TemporaryDirectory() as first,
            tempfile.TemporaryDirectory() as second,
        ):
            first_manifest = self._write(first)
            second_manifest = self._write(second)

        self.assertEqual(first_manifest["outputs"], second_manifest["outputs"])

    def test_complement_panels_record_construction_in_written_manifest(self):
        """Complement provenance survives into the written manifest."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with capture.suppress_output():
                manifest = nway_outputs.write_nway_outputs(
                    _result(comparison.NWayPanelMode.COMPLEMENT),
                    output_dir=tmp_dir,
                    stem="complements",
                    formats=("svg",),
                )

        self.assertEqual(len(manifest["complements"]), 4)
        self.assertTrue(
            all(
                record["verified_equals_universe_minus_base"]
                for record in manifest["complements"]
            )
        )

    def test_extra_manifest_is_recorded_under_generator(self):
        """Caller provenance is kept separate from analysis provenance."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest = self._write(
                tmp_dir, formats=("png",), extra_manifest={"command": "test"}
            )

        self.assertEqual(manifest["generator"], {"command": "test"})

    @parameterized.expand(
        [
            ("unsupported_format", {"formats": ("gif",)}, "unsupported"),
            ("empty_formats", {"formats": ()}, "at least one"),
            ("repeated_format", {"formats": ("png", "png")}, "repeat"),
            ("path_stem", {"stem": "../escape"}, "simple file stem"),
        ]
    )
    def test_invalid_output_requests_raise_before_writing(
        self, _name, overrides, message
    ):
        """Invalid requests fail without leaving partial outputs."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(ValueError, message):
                self._write(tmp_dir, **overrides)
            self.assertEqual(list(pathlib.Path(tmp_dir).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
