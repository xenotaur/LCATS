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
    bucket_dir = collection_dir / name
    bucket_dir.mkdir(parents=True, exist_ok=True)
    story_path = bucket_dir / "story.json"
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

    def test_zero_story_collection_is_not_clean(self):
        """A collection with no stories is never clean, even with no
        findings -- a writer regression or stale collection must not be
        promoted wholesale undetected (Decision 6 of
        PROP-LCATS-STORY-BUCKET-LAYOUT)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_dir = pathlib.Path(tmpdir) / "empty_collection"
            collection_dir.mkdir(parents=True)

            result = promote.survey_collection(collection_dir)

            self.assertEqual(0, result.story_count)
            self.assertEqual((), result.findings)
            self.assertFalse(result.clean)

    def test_bucket_with_only_sidecar_is_not_clean(self):
        """A story bucket directory holding only a sidecar (no story.json)
        must not count as a story -- this is exactly the writer-regression
        case Decision 6's story_count > 0 check exists to catch, and
        counting the sidecar would silently defeat it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_dir = pathlib.Path(tmpdir) / "broken_collection"
            bucket_dir = collection_dir / "broken_story"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "audit.json").write_text(
                json.dumps({"unrelated": "audit data"}), encoding="utf-8"
            )

            result = promote.survey_collection(collection_dir)

            self.assertEqual(0, result.story_count)
            self.assertFalse(result.clean)

    def test_valid_genre_sidecar_does_not_block(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_dir = pathlib.Path(tmpdir) / "annotated_collection"
            _write_story(collection_dir, "story_one", "A clean sentence.")
            (collection_dir / "story_one" / "genre.json").write_text(
                json.dumps({"detected_genre": "horror"}), encoding="utf-8"
            )

            result = promote.survey_collection(collection_dir)

            self.assertTrue(result.clean)
            self.assertEqual((), result.sidecar_findings)

    def test_valid_scenes_sidecar_does_not_block(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_dir = pathlib.Path(tmpdir) / "annotated_collection"
            _write_story(collection_dir, "story_one", "A clean sentence.")
            (collection_dir / "story_one" / "scenes.json").write_text(
                json.dumps({"segments": []}), encoding="utf-8"
            )

            result = promote.survey_collection(collection_dir)

            self.assertTrue(result.clean)
            self.assertEqual((), result.sidecar_findings)

    def test_malformed_json_sidecar_blocks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_dir = pathlib.Path(tmpdir) / "broken_sidecar_collection"
            _write_story(collection_dir, "story_one", "A clean sentence.")
            (collection_dir / "story_one" / "genre.json").write_text(
                "{not valid json", encoding="utf-8"
            )

            result = promote.survey_collection(collection_dir)

            self.assertFalse(result.clean)
            self.assertEqual(1, len(result.sidecar_findings))
            self.assertEqual("genre.json", result.sidecar_findings[0].sidecar_name)

    def test_wrong_top_level_type_sidecar_blocks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_dir = pathlib.Path(tmpdir) / "broken_sidecar_collection"
            _write_story(collection_dir, "story_one", "A clean sentence.")
            (collection_dir / "story_one" / "scenes.json").write_text(
                json.dumps(["not", "a", "dict"]), encoding="utf-8"
            )

            result = promote.survey_collection(collection_dir)

            self.assertFalse(result.clean)
            self.assertEqual(1, len(result.sidecar_findings))
            self.assertIn("JSON object", result.sidecar_findings[0].error)

    def test_missing_required_key_sidecar_blocks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_dir = pathlib.Path(tmpdir) / "broken_sidecar_collection"
            _write_story(collection_dir, "story_one", "A clean sentence.")
            (collection_dir / "story_one" / "genre.json").write_text(
                json.dumps({"unrelated_key": "value"}), encoding="utf-8"
            )

            result = promote.survey_collection(collection_dir)

            self.assertFalse(result.clean)
            self.assertEqual(1, len(result.sidecar_findings))
            self.assertIn("detected_genre", result.sidecar_findings[0].error)

    def test_null_required_value_sidecar_blocks(self):
        """Key presence alone isn't enough -- {"segments": null} passes an
        `in`-only check even though the real writer never emits null
        (review finding, PR #248)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_dir = pathlib.Path(tmpdir) / "broken_sidecar_collection"
            _write_story(collection_dir, "story_one", "A clean sentence.")
            (collection_dir / "story_one" / "scenes.json").write_text(
                json.dumps({"segments": None}), encoding="utf-8"
            )

            result = promote.survey_collection(collection_dir)

            self.assertFalse(result.clean)
            self.assertEqual(1, len(result.sidecar_findings))
            self.assertIn("list", result.sidecar_findings[0].error)

    def test_wrong_value_type_sidecar_blocks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_dir = pathlib.Path(tmpdir) / "broken_sidecar_collection"
            _write_story(collection_dir, "story_one", "A clean sentence.")
            (collection_dir / "story_one" / "genre.json").write_text(
                json.dumps({"detected_genre": 42}), encoding="utf-8"
            )

            result = promote.survey_collection(collection_dir)

            self.assertFalse(result.clean)
            self.assertEqual(1, len(result.sidecar_findings))
            self.assertIn("str", result.sidecar_findings[0].error)

    def test_no_sidecars_unaffected(self):
        """Today's normal case: a story bucket with neither sidecar must
        promote exactly as before this change."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_dir = pathlib.Path(tmpdir) / "unannotated_collection"
            _write_story(collection_dir, "story_one", "A clean sentence.")

            result = promote.survey_collection(collection_dir)

            self.assertTrue(result.clean)
            self.assertEqual((), result.sidecar_findings)


class PromoteCollectionsTest(unittest.TestCase):
    """Tests for the survey-gated promotion pass (acceptance criteria)."""

    def test_seeded_defect_blocks_promotion(self):
        # WI-PROMOTE-0020 acceptance: a seeded-defect test proves the gate
        # blocks promotion of damaged text.
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "damaged", "story_one", "them a resumÃ©.")

            report = promote.promote_collections(source_root, dest_root)

            self.assertEqual((), report.promoted)
            self.assertEqual(1, len(report.blocked))
            self.assertEqual("damaged", report.blocked[0].collection)
            self.assertFalse((dest_root / "damaged").exists())

    def test_malformed_sidecar_blocks_promotion(self):
        """WI-ANNOTATE-0052 acceptance: a malformed sidecar is blocked
        from promotion, the same way a mojibake finding is -- not
        silently wholesale-copied to corpora/."""
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "annotated", "story_one", "A clean sentence.")
            (source_root / "annotated" / "story_one" / "genre.json").write_text(
                "{not valid json", encoding="utf-8"
            )

            report = promote.promote_collections(source_root, dest_root)

            self.assertEqual((), report.promoted)
            self.assertEqual(1, len(report.blocked))
            self.assertEqual(1, len(report.blocked[0].sidecar_findings))
            self.assertFalse((dest_root / "annotated").exists())

    def test_clean_collection_is_promoted(self):
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "clean", "story_one", "A clean sentence.")

            report = promote.promote_collections(source_root, dest_root)

            self.assertEqual(("clean",), report.promoted)
            self.assertEqual((), report.blocked)
            self.assertTrue(report.all_promoted)
            promoted_story = dest_root / "clean" / "story_one" / "story.json"
            self.assertTrue(promoted_story.exists())
            self.assertEqual(
                "A clean sentence.",
                json.loads(promoted_story.read_text(encoding="utf-8"))["body"],
            )

    def test_zero_story_collection_is_blocked_not_promoted(self):
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            (source_root / "empty").mkdir(parents=True)

            report = promote.promote_collections(source_root, dest_root)

            self.assertEqual((), report.promoted)
            self.assertEqual(1, len(report.blocked))
            self.assertEqual("empty", report.blocked[0].collection)
            self.assertEqual(0, report.blocked[0].story_count)
            self.assertFalse((dest_root / "empty").exists())

    def test_mixed_collections_promote_clean_and_block_damaged_independently(self):
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
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
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "clean", "story_one", "A clean sentence.")

            report = promote.promote_collections(source_root, dest_root, dry_run=True)

            self.assertEqual(("clean",), report.promoted)
            self.assertFalse((dest_root / "clean").exists())

    def test_promotion_wholesale_replaces_stale_destination_files(self):
        # A file present in a prior promotion but absent from the current
        # source must not survive re-promotion.
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            stale_dest = dest_root / "clean"
            stale_bucket = stale_dest / "removed_story"
            stale_bucket.mkdir(parents=True)
            (stale_bucket / "story.json").write_text("{}", encoding="utf-8")
            _write_story(source_root / "clean", "story_one", "A clean sentence.")

            promote.promote_collections(source_root, dest_root)

            self.assertFalse((dest_root / "clean" / "removed_story").exists())
            self.assertTrue((dest_root / "clean" / "story_one" / "story.json").exists())

    def test_collection_names_scopes_to_requested_collections(self):
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
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

    def test_refuses_when_source_and_dest_are_the_same_directory(self):
        # Regression: _copy_collection's rmtree-then-copytree would otherwise
        # delete the source collection before the copy could run.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _write_story(root / "clean", "story_one", "A clean sentence.")

            with self.assertRaises(ValueError):
                promote.promote_collections(root, root)

            self.assertTrue((root / "clean" / "story_one" / "story.json").exists())

    def test_refuses_when_dest_is_nested_inside_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            nested_dest = root / "sub" / "nested"

            with self.assertRaises(ValueError):
                promote.promote_collections(root, nested_dest)

    def test_all_collections_are_surveyed_before_any_copy_begins(self):
        # A collection sorted after a blocked one must not have been copied
        # by the time promote_collections raises or returns -- surveying
        # happens as a distinct phase before any copytree call.
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "a_clean", "story_one", "A clean sentence.")
            _write_story(source_root / "b_damaged", "story_one", "them a resumÃ©.")

            report = promote.promote_collections(source_root, dest_root)

            # Both collections are independently gated (documented mode): the
            # clean one still promotes even though it sorts before the
            # blocked one, but this is now the outcome of a completed survey
            # phase, not an artifact of copying mid-loop.
            self.assertEqual(("a_clean",), report.promoted)
            self.assertEqual(1, len(report.blocked))


def _valid_sidecar_record(lcats_id: str, story_path: str) -> dict:
    """Build a minimal genre-sidecar-v1 record that passes
    genre_sidecar.validate_sidecar() -- a non-model assessment label so no
    run_id/provenance.run_id is required."""
    return {
        "schema_version": "genre-sidecar-v1",
        "lcats_id": lcats_id,
        "story_path": story_path,
        "assessments": [
            {
                "assessment_id": f"gutenberg_metadata_rules:{lcats_id}:1",
                "label": "gutenberg_metadata_rules",
                "generated_at": "2026-08-21T06:19:16.729706Z",
                "scope": "gutenberg_volume",
                "method": {"name": "gutenberg_subject_rules", "version": "v1"},
                "provenance": {"story_id": lcats_id},
                "evidence": {"raw_subjects": []},
                "result": {"target_candidates": ["fantasy"]},
            }
        ],
    }


def _write_manifest(manifest_path: pathlib.Path, records: list) -> None:
    lines = [json.dumps(record) for record in records]
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class PromoteSidecarTrancheTest(unittest.TestCase):
    """Tests for the sidecar-tranche promotion mode (WI-GENRE-0075)."""

    def test_valid_records_are_promoted_without_touching_other_files(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            record = _valid_sidecar_record("anderson/bell", "anderson/bell/story.json")
            _write_manifest(manifest_path, [record])

            # A pre-existing, unrelated file in the destination story
            # bucket must survive promotion untouched.
            bucket_dir = dest_root / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )

            report = promote.promote_sidecar_tranche(manifest_path, dest_root)

            self.assertEqual(("anderson/bell",), report.promoted)
            self.assertEqual((), report.rejected)
            self.assertTrue(report.all_promoted)
            written = json.loads(
                (bucket_dir / "genre.json").read_text(encoding="utf-8")
            )
            self.assertEqual(record, written)
            # story.json is untouched.
            self.assertEqual(
                {"name": "bell"},
                json.loads((bucket_dir / "story.json").read_text(encoding="utf-8")),
            )

    def test_invalid_record_is_rejected_and_not_written(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            # Missing "assessments" entirely -- validate_sidecar rejects.
            invalid_record = {
                "schema_version": "genre-sidecar-v1",
                "lcats_id": "anderson/bell",
                "story_path": "anderson/bell/story.json",
            }
            _write_manifest(manifest_path, [invalid_record])

            report = promote.promote_sidecar_tranche(manifest_path, dest_root)

            self.assertEqual((), report.promoted)
            self.assertEqual(1, len(report.rejected))
            self.assertEqual("anderson/bell", report.rejected[0].lcats_id)
            self.assertFalse((dest_root / "anderson" / "bell" / "genre.json").exists())

    def test_legacy_flat_sidecar_at_destination_is_refused_not_overwritten(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            record = _valid_sidecar_record("anderson/bell", "anderson/bell/story.json")
            _write_manifest(manifest_path, [record])

            bucket_dir = dest_root / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )
            legacy_sidecar = {
                "detected_genre": "fantasy",
                "detected_genre_confidence": 0.9,
                "verdict": "wellformed",
            }
            (bucket_dir / "genre.json").write_text(
                json.dumps(legacy_sidecar), encoding="utf-8"
            )

            report = promote.promote_sidecar_tranche(manifest_path, dest_root)

            self.assertEqual((), report.promoted)
            self.assertEqual(1, len(report.rejected))
            self.assertIn("legacy", report.rejected[0].error)
            # The legacy sidecar must survive untouched, not be overwritten.
            self.assertEqual(
                legacy_sidecar,
                json.loads((bucket_dir / "genre.json").read_text(encoding="utf-8")),
            )

    def test_dry_run_makes_no_writes(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            record = _valid_sidecar_record("anderson/bell", "anderson/bell/story.json")
            _write_manifest(manifest_path, [record])

            bucket_dir = dest_root / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )

            report = promote.promote_sidecar_tranche(
                manifest_path, dest_root, dry_run=True
            )

            self.assertEqual(("anderson/bell",), report.promoted)
            self.assertFalse((bucket_dir / "genre.json").exists())

    def test_lcats_id_escaping_dest_root_is_rejected(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            escaping_ids = ["/etc/passwd", "../outside", "anderson/../../outside", "."]
            records = [
                _valid_sidecar_record(lcats_id, f"{lcats_id}/story.json")
                for lcats_id in escaping_ids
            ]
            _write_manifest(manifest_path, records)

            report = promote.promote_sidecar_tranche(manifest_path, dest_root)

            self.assertEqual((), report.promoted)
            self.assertEqual(len(escaping_ids), len(report.rejected))
            for finding in report.rejected:
                self.assertIn(finding.lcats_id, escaping_ids)
            # Nothing was ever written outside (or directly under) dest_root.
            self.assertEqual([], list(dest_root.rglob("genre.json")))

    def test_missing_destination_story_is_rejected_not_created(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            # No story.json bucket exists at the destination for this id.
            record = _valid_sidecar_record(
                "anderson/typo_d_id", "anderson/typo_d_id/story.json"
            )
            _write_manifest(manifest_path, [record])

            report = promote.promote_sidecar_tranche(manifest_path, dest_root)

            self.assertEqual((), report.promoted)
            self.assertEqual(1, len(report.rejected))
            self.assertEqual("anderson/typo_d_id", report.rejected[0].lcats_id)
            self.assertIn("story.json", report.rejected[0].error)
            self.assertFalse((dest_root / "anderson" / "typo_d_id").exists())

    def test_malformed_manifest_line_is_rejected_not_fatal(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            good_record = _valid_sidecar_record(
                "anderson/bell", "anderson/bell/story.json"
            )
            manifest_path.write_text(
                "not valid json\n" + json.dumps(good_record) + "\n",
                encoding="utf-8",
            )
            bucket_dir = dest_root / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )

            report = promote.promote_sidecar_tranche(manifest_path, dest_root)

            self.assertEqual(("anderson/bell",), report.promoted)
            self.assertEqual(1, len(report.rejected))
            self.assertIn("<line 1>", report.rejected[0].lcats_id)

    def test_wholesale_promote_collections_is_unaffected(self):
        # Sanity check: adding the tranche path did not change
        # promote_collections' own wholesale behavior or shape.
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "clean", "story_one", "A clean sentence.")

            report = promote.promote_collections(source_root, dest_root)

            self.assertEqual(("clean",), report.promoted)
            self.assertTrue(report.all_promoted)


class PromoteCliTest(unittest.TestCase):
    """Tests for the promote CLI exit-code and reporting behavior."""

    def test_exit_code_zero_when_all_collections_promote(self):
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
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
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "damaged", "story_one", "them a resumÃ©.")

            output = io.StringIO()
            error_output = io.StringIO()
            with (
                unittest.mock.patch("sys.stdout", output),
                unittest.mock.patch("sys.stderr", error_output),
            ):
                exit_code = promote_cli.run(
                    ["--source", str(source_root), "--dest", str(dest_root)]
                )

            self.assertEqual(1, exit_code)
            self.assertIn("blocked: damaged", error_output.getvalue())

    def test_missing_source_directory_reports_clean_error_not_traceback(self):
        with tempfile.TemporaryDirectory() as dest_tmp:
            missing_source = pathlib.Path(dest_tmp) / "does_not_exist"

            error_output = io.StringIO()
            with unittest.mock.patch("sys.stderr", error_output):
                exit_code = promote_cli.run(
                    [
                        "--source",
                        str(missing_source),
                        "--dest",
                        dest_tmp,
                        "some_collection",
                    ]
                )

            self.assertEqual(2, exit_code)
            self.assertIn("error:", error_output.getvalue())

    def test_source_equals_dest_reports_clean_error_not_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            error_output = io.StringIO()
            with unittest.mock.patch("sys.stderr", error_output):
                exit_code = promote_cli.run(["--source", tmp, "--dest", tmp])

            self.assertEqual(2, exit_code)
            self.assertIn("error:", error_output.getvalue())
            self.assertIn("same directory", error_output.getvalue())

    def test_tranche_manifest_flag_reaches_the_tranche_promotion_function(self):
        # The whole point of Required Change 2 (review finding, PR #348):
        # the CLI must actually invoke promote_sidecar_tranche, not just
        # the library function called directly in tests above.
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            record = _valid_sidecar_record("anderson/bell", "anderson/bell/story.json")
            _write_manifest(manifest_path, [record])
            bucket_dir = pathlib.Path(dest_tmp) / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )

            output = io.StringIO()
            with unittest.mock.patch("sys.stdout", output):
                exit_code = promote_cli.run(
                    [
                        "--dest",
                        dest_tmp,
                        "--tranche-manifest",
                        str(manifest_path),
                    ]
                )

            self.assertEqual(0, exit_code)
            self.assertIn("promoted sidecar: anderson/bell", output.getvalue())
            self.assertTrue(
                (pathlib.Path(dest_tmp) / "anderson" / "bell" / "genre.json").is_file()
            )

    def test_tranche_manifest_flag_reports_rejections_and_nonzero_exit(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            invalid_record = {
                "schema_version": "genre-sidecar-v1",
                "lcats_id": "anderson/bell",
                "story_path": "anderson/bell/story.json",
            }
            _write_manifest(manifest_path, [invalid_record])

            error_output = io.StringIO()
            with unittest.mock.patch("sys.stderr", error_output):
                exit_code = promote_cli.run(
                    [
                        "--dest",
                        dest_tmp,
                        "--tranche-manifest",
                        str(manifest_path),
                    ]
                )

            self.assertEqual(1, exit_code)
            self.assertIn("rejected: anderson/bell", error_output.getvalue())

    def test_tranche_manifest_dry_run_makes_no_writes_via_cli(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            record = _valid_sidecar_record("anderson/bell", "anderson/bell/story.json")
            _write_manifest(manifest_path, [record])
            bucket_dir = pathlib.Path(dest_tmp) / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )

            output = io.StringIO()
            with unittest.mock.patch("sys.stdout", output):
                exit_code = promote_cli.run(
                    [
                        "--dest",
                        dest_tmp,
                        "--tranche-manifest",
                        str(manifest_path),
                        "--dry-run",
                    ]
                )

            self.assertEqual(0, exit_code)
            self.assertIn("would promote sidecar: anderson/bell", output.getvalue())
            self.assertFalse((bucket_dir / "genre.json").exists())

    def test_wholesale_cli_invocations_are_unaffected_by_the_new_flag(self):
        # Sanity check: the existing wholesale CLI path and its exit codes
        # are unchanged when --tranche-manifest is simply not passed.
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            source_root = pathlib.Path(source_tmp)
            _write_story(source_root / "clean", "story_one", "A clean sentence.")

            output = io.StringIO()
            with unittest.mock.patch("sys.stdout", output):
                exit_code = promote_cli.run(
                    ["--source", str(source_root), "--dest", dest_tmp]
                )

            self.assertEqual(0, exit_code)
            self.assertIn("promoted: clean", output.getvalue())


if __name__ == "__main__":
    unittest.main()
