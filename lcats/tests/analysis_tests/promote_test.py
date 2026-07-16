"""Unit tests for lcats.analysis.corpus.promote and promote_cli."""

import io
import json
import pathlib
import tempfile
import unittest
import unittest.mock

from lcats.analysis.corpus import promote
from lcats.analysis.corpus import promote_cli


def _write_story(collection_dir: pathlib.Path, name: str, body: str) -> None:
    collection_dir.mkdir(parents=True, exist_ok=True)
    story_path = collection_dir / f"{name}.json"
    story_path.write_text(
        json.dumps({"name": name, "body": body, "metadata": {}}),
        encoding="utf-8",
    )


class DestinationNameTest(unittest.TestCase):
    """Tests for the collection-name mapping."""

    def test_mapping_is_identity_for_every_name(self):
        # As of 2026-07 (pre-external-release), data/'s current names are
        # canonical everywhere -- no rename/merge table.
        for name in [
            "ohenry-four_million",
            "ohenry-whirligigs",
            "wilde_happy_prince",
            "anderson",
        ]:
            with self.subTest(name=name):
                self.assertEqual(name, promote.destination_name(name))


class SurveyCollectionTest(unittest.TestCase):
    """Tests for the per-collection mojibake survey gate."""

    def test_clean_collection_has_no_findings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_dir = pathlib.Path(tmpdir) / "clean_collection"
            _write_story(collection_dir, "story_one", "A perfectly clean sentence.")

            result = promote.survey_collection(collection_dir)

            self.assertTrue(result.clean)
            self.assertEqual((), result.findings)
            self.assertEqual(1, result.story_count)

    def test_mojibake_collection_reports_blocking_findings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_dir = pathlib.Path(tmpdir) / "damaged_collection"
            _write_story(collection_dir, "story_one", "them a resumÃ©.")

            result = promote.survey_collection(collection_dir)

            self.assertFalse(result.clean)
            # The mojibake marker and its continuation byte are each reported
            # as a separate finding (Ã and © in "resumÃ©").
            self.assertEqual(2, len(result.findings))
            self.assertEqual(
                {"Ã", "©"}, {finding.character for finding in result.findings}
            )

    def test_legitimate_accented_letters_do_not_block(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_dir = pathlib.Path(tmpdir) / "legit_collection"
            _write_story(collection_dir, "story_one", "café, señorita, façade")

            result = promote.survey_collection(collection_dir)

            self.assertTrue(result.clean)


class PromoteCollectionsTest(unittest.TestCase):
    """Tests for the survey-gated promotion pass (acceptance criteria)."""

    def test_seeded_defect_blocks_promotion(self):
        # WI-PROMOTE-0020 acceptance: a seeded-defect test proves the gate
        # blocks promotion of damaged text.
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as dest_tmp:
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "damaged", "story_one", "them a resumÃ©.")

            report = promote.promote_collections(source_root, dest_root)

            self.assertEqual((), report.promoted)
            self.assertEqual(1, len(report.blocked))
            self.assertEqual("damaged", report.blocked[0].collection)
            self.assertFalse((dest_root / "damaged").exists())

    def test_clean_collection_is_promoted(self):
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as dest_tmp:
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "clean", "story_one", "A clean sentence.")

            report = promote.promote_collections(source_root, dest_root)

            self.assertEqual(("clean",), report.promoted)
            self.assertEqual((), report.blocked)
            self.assertTrue(report.all_promoted)
            promoted_story = dest_root / "clean" / "story_one.json"
            self.assertTrue(promoted_story.exists())
            self.assertEqual(
                "A clean sentence.",
                json.loads(promoted_story.read_text(encoding="utf-8"))["body"],
            )

    def test_mixed_collections_promote_clean_and_block_damaged_independently(self):
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as dest_tmp:
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "clean", "story_one", "A clean sentence.")
            _write_story(source_root / "damaged", "story_one", "them a resumÃ©.")

            report = promote.promote_collections(source_root, dest_root)

            self.assertEqual(("clean",), report.promoted)
            self.assertEqual(1, len(report.blocked))
            self.assertFalse(report.all_promoted)
            self.assertTrue((dest_root / "clean").exists())
            self.assertFalse((dest_root / "damaged").exists())

    def test_dry_run_does_not_copy_clean_collections(self):
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as dest_tmp:
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "clean", "story_one", "A clean sentence.")

            report = promote.promote_collections(source_root, dest_root, dry_run=True)

            self.assertEqual(("clean",), report.promoted)
            self.assertFalse((dest_root / "clean").exists())

    def test_promotion_wholesale_replaces_stale_destination_files(self):
        # A file present in a prior promotion but absent from the current
        # source must not survive re-promotion.
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as dest_tmp:
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            stale_dest = dest_root / "clean"
            stale_dest.mkdir(parents=True)
            (stale_dest / "removed_story.json").write_text("{}", encoding="utf-8")
            _write_story(source_root / "clean", "story_one", "A clean sentence.")

            promote.promote_collections(source_root, dest_root)

            self.assertFalse((dest_root / "clean" / "removed_story.json").exists())
            self.assertTrue((dest_root / "clean" / "story_one.json").exists())

    def test_collection_names_scopes_to_requested_collections(self):
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as dest_tmp:
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "one", "story_one", "A clean sentence.")
            _write_story(source_root / "two", "story_one", "Another clean sentence.")

            report = promote.promote_collections(
                source_root, dest_root, collection_names=["one"]
            )

            self.assertEqual(("one",), report.promoted)
            self.assertTrue((dest_root / "one").exists())
            self.assertFalse((dest_root / "two").exists())


class PromoteCliTest(unittest.TestCase):
    """Tests for the promote CLI exit-code and reporting behavior."""

    def test_exit_code_zero_when_all_collections_promote(self):
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as dest_tmp:
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "clean", "story_one", "A clean sentence.")

            output = io.StringIO()
            with unittest.mock.patch("sys.stdout", output):
                exit_code = promote_cli.run(
                    ["--source", str(source_root), "--dest", str(dest_root)]
                )

            self.assertEqual(0, exit_code)
            self.assertIn("promoted: clean", output.getvalue())

    def test_exit_code_nonzero_when_a_collection_is_blocked(self):
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as dest_tmp:
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "damaged", "story_one", "them a resumÃ©.")

            output = io.StringIO()
            error_output = io.StringIO()
            with unittest.mock.patch("sys.stdout", output), unittest.mock.patch(
                "sys.stderr", error_output
            ):
                exit_code = promote_cli.run(
                    ["--source", str(source_root), "--dest", str(dest_root)]
                )

            self.assertEqual(1, exit_code)
            self.assertIn("blocked: damaged", error_output.getvalue())


if __name__ == "__main__":
    unittest.main()
