"""Unit tests for lcats.analysis.corpus.promote and promote_cli."""

import io
import json
import pathlib
import tempfile
import unittest
import unittest.mock

from lcats.analysis.corpus import promote
from lcats.analysis.corpus import promote_cli
from lcats.analysis.corpus import sidecar_validators


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
        """A genre.json with neither the legacy detected_genre key nor a
        recognizable v1 shape blocks promotion either way -- it is
        checked against genre_sidecar.validate_sidecar() (not the legacy
        top-level-key check) since it isn't legacy-flat per
        is_legacy_flat_sidecar()'s own definition (WI-GENRE-0076,
        review finding PR #357)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_dir = pathlib.Path(tmpdir) / "broken_sidecar_collection"
            _write_story(collection_dir, "story_one", "A clean sentence.")
            (collection_dir / "story_one" / "genre.json").write_text(
                json.dumps({"unrelated_key": "value"}), encoding="utf-8"
            )

            result = promote.survey_collection(collection_dir)

            self.assertFalse(result.clean)
            self.assertEqual(1, len(result.sidecar_findings))
            self.assertIn("schema_version", result.sidecar_findings[0].error)

    def test_missing_required_key_scenes_sidecar_blocks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_dir = pathlib.Path(tmpdir) / "broken_sidecar_collection"
            _write_story(collection_dir, "story_one", "A clean sentence.")
            (collection_dir / "story_one" / "scenes.json").write_text(
                json.dumps({"unrelated_key": "value"}), encoding="utf-8"
            )

            result = promote.survey_collection(collection_dir)

            self.assertFalse(result.clean)
            self.assertEqual(1, len(result.sidecar_findings))
            self.assertIn("segments", result.sidecar_findings[0].error)

    def test_valid_v1_genre_sidecar_does_not_block(self):
        """A genre-sidecar-v1 record written by lcats annotate's new
        append-mode path (WI-GENRE-0076) must not be wrongly flagged
        malformed by the legacy top-level detected_genre check -- it is
        checked via genre_sidecar.validate_sidecar() instead (review
        finding, PR #357)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_dir = pathlib.Path(tmpdir) / "annotated_collection"
            _write_story(collection_dir, "story_one", "A clean sentence.")
            v1_sidecar = {
                "schema_version": "genre-sidecar-v1",
                "lcats_id": "annotated_collection/story_one",
                "story_path": "annotated_collection/story_one/story.json",
                "assessments": [
                    {
                        "assessment_id": "model_detect:story_one:2026-08-22T00:00:00+00:00",
                        "label": "model_detect",
                        "generated_at": "2026-08-22T00:00:00+00:00",
                        "scope": "story",
                        "method": {"name": "assess_story", "version": "v1"},
                        "provenance": {
                            "run_id": "2026-08-22T00:00:00+00:00",
                        },
                        "evidence": {},
                        "result": {"detected_genre": "horror"},
                        "run_id": "2026-08-22T00:00:00+00:00",
                    }
                ],
            }
            (collection_dir / "story_one" / "genre.json").write_text(
                json.dumps(v1_sidecar), encoding="utf-8"
            )

            result = promote.survey_collection(collection_dir)

            self.assertTrue(result.clean)
            self.assertEqual((), result.sidecar_findings)

    def test_invalid_v1_genre_sidecar_blocks(self):
        """A v1-shaped genre.json (has schema_version, not legacy-flat)
        with a genuinely invalid assessments[] entry must still block,
        via genre_sidecar.validate_sidecar()'s own findings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_dir = pathlib.Path(tmpdir) / "broken_sidecar_collection"
            _write_story(collection_dir, "story_one", "A clean sentence.")
            invalid_v1 = {
                "schema_version": "genre-sidecar-v1",
                "lcats_id": "broken_sidecar_collection/story_one",
                "story_path": "broken_sidecar_collection/story_one/story.json",
                "assessments": [{"label": "model_detect"}],
            }
            (collection_dir / "story_one" / "genre.json").write_text(
                json.dumps(invalid_v1), encoding="utf-8"
            )

            result = promote.survey_collection(collection_dir)

            self.assertFalse(result.clean)
            self.assertEqual(1, len(result.sidecar_findings))

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

    def setUp(self):
        # promote_collections() now writes a run_log.RunLog by default -
        # point every call in this class at a throwaway directory rather
        # than the real default (logs/promote/ relative to cwd), so
        # these unit tests don't leave real files behind in whatever
        # directory happens to run them (WI-RUNLOG-0083). Patching the
        # module-level constant (not passing log_dir= at each call site)
        # works because promote_collections() resolves None -> the
        # constant at call time, not at function-definition time.
        self._log_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._log_tmp.cleanup)
        self._log_dir_patch = unittest.mock.patch.object(
            promote, "DEFAULT_PROMOTE_LOG_DIR", pathlib.Path(self._log_tmp.name)
        )
        self._log_dir_patch.start()
        self.addCleanup(self._log_dir_patch.stop)

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


class PromoteCollectionsRunLoggingTest(unittest.TestCase):
    """WI-RUNLOG-0083: promote_collections() gets a crash-safe,
    incremental run-event log via lcats.utils.run_log.RunLog, written
    outside both --source and --dest (both protected roots by default)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp_path = pathlib.Path(self._tmp.name)
        self.log_dir = self.tmp_path / "promote_logs"

    def test_run_log_records_start_promote_and_end_in_order(self):
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "clean", "story_one", "A clean sentence.")

            report = promote.promote_collections(
                source_root, dest_root, log_dir=self.log_dir
            )

            self.assertEqual(("clean",), report.promoted)

        log_path = self.log_dir / "promote_run_log.jsonl"
        self.assertTrue(log_path.exists())
        events = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
        ]
        event_names = [e["event"] for e in events]
        self.assertEqual(
            event_names, ["run_start", "promote_start", "promote_end", "run_end"]
        )
        self.assertEqual(events[0]["collection_names"], ["clean"])
        self.assertEqual(events[1]["collection"], "clean")

    def test_blocked_collection_logs_collection_blocked_not_promote_events(self):
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "damaged", "story_one", "them a resumÃ©.")

            report = promote.promote_collections(
                source_root, dest_root, log_dir=self.log_dir
            )

            self.assertEqual((), report.promoted)

        log_path = self.log_dir / "promote_run_log.jsonl"
        events = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
        ]
        event_names = [e["event"] for e in events]
        self.assertIn("collection_blocked", event_names)
        self.assertNotIn("promote_start", event_names)
        self.assertNotIn("promote_end", event_names)
        blocked_event = next(e for e in events if e["event"] == "collection_blocked")
        self.assertEqual(blocked_event["collection"], "damaged")

    def test_crash_mid_copy_leaves_a_readable_partial_log(self):
        """An uncaught _copy_collection failure partway through multiple
        collections must not corrupt already-written log entries, and
        must surface as run_aborted_unexpected - promote.py has no
        FatalPromoteError class, so nothing here could ever be
        classified run_aborted_fatal instead."""
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "a_clean", "story_one", "A clean sentence.")
            _write_story(source_root / "b_clean", "story_one", "Another sentence.")

            with unittest.mock.patch.object(
                promote,
                "_copy_collection",
                side_effect=[None, OSError("simulated disk failure")],
            ):
                with self.assertRaises(OSError):
                    promote.promote_collections(
                        source_root, dest_root, log_dir=self.log_dir
                    )

        log_path = self.log_dir / "promote_run_log.jsonl"
        events = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
        ]
        event_names = [e["event"] for e in events]
        self.assertEqual(event_names[0], "run_start")
        # a_clean completed (promote_start + promote_end); b_clean only
        # got as far as promote_start before the simulated crash.
        self.assertEqual(event_names.count("promote_start"), 2)
        self.assertEqual(event_names.count("promote_end"), 1)
        self.assertEqual(event_names[-1], "run_aborted_unexpected")

    def test_log_dir_nested_under_source_root_is_rejected(self):
        """A log_dir inside source_root would get wholesale-copied into
        dest_root by _copy_collection's own unfiltered copytree,
        contaminating the promoted corpus with an operational log file
        (review finding, PR #407) - must be rejected before any file is
        ever written, not merely produce a corrupted promotion."""
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "clean", "story_one", "A clean sentence.")
            nested_log_dir = source_root / "clean" / "logs"

            with self.assertRaises(ValueError) as ctx:
                promote.promote_collections(
                    source_root, dest_root, log_dir=nested_log_dir
                )

            self.assertIn("source_root", str(ctx.exception))
            # Nothing was promoted or logged - the rejection happens
            # before entering the RunLog scope at all.
            self.assertFalse((dest_root / "clean").exists())

    def test_log_dir_nested_under_dest_root_is_rejected(self):
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "clean", "story_one", "A clean sentence.")
            nested_log_dir = dest_root / "logs"

            with self.assertRaises(ValueError) as ctx:
                promote.promote_collections(
                    source_root, dest_root, log_dir=nested_log_dir
                )

            self.assertIn("dest_root", str(ctx.exception))

    def test_allowlist_load_failure_is_captured_as_run_aborted_unexpected(self):
        """The allowlist config load moved inside the RunLog scope
        (review finding, PR #407) - an unexpected failure there must
        produce run_start then run_aborted_unexpected, not escape the
        run log entirely."""
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "clean", "story_one", "A clean sentence.")

            with unittest.mock.patch.object(
                promote.specials,
                "load_allowlist_config",
                side_effect=RuntimeError("simulated config load failure"),
            ):
                with self.assertRaises(RuntimeError):
                    promote.promote_collections(
                        source_root, dest_root, log_dir=self.log_dir
                    )

        log_path = self.log_dir / "promote_run_log.jsonl"
        events = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
        ]
        event_names = [e["event"] for e in events]
        self.assertEqual(event_names, ["run_start", "run_aborted_unexpected"])


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


def _envelope(lcats_id: str, payload) -> dict:
    return {"lcats_id": lcats_id, "payload": payload}


def _write_manifest(manifest_path: pathlib.Path, records: list) -> None:
    lines = [json.dumps(record) for record in records]
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class PromoteSidecarInsertUpsertTest(unittest.TestCase):
    """Tests for the insert/upsert sidecar-manifest promotion modes
    (WI-PROMOTE-0097; generalizes WI-GENRE-0075's promote_sidecar_tranche
    into a manifest-identity-envelope shape, per PR #401's review
    finding)."""

    def test_valid_records_are_promoted_without_touching_other_files(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            payload = _valid_sidecar_record("anderson/bell", "anderson/bell/story.json")
            _write_manifest(manifest_path, [_envelope("anderson/bell", payload)])

            # A pre-existing, unrelated file in the destination story
            # bucket must survive promotion untouched.
            bucket_dir = dest_root / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )

            report = promote.promote_sidecar_insert(manifest_path, dest_root, "genre")

            self.assertEqual(("anderson/bell",), report.promoted)
            self.assertEqual((), report.rejected)
            self.assertTrue(report.all_promoted)
            written = json.loads(
                (bucket_dir / "genre.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload, written)
            # story.json is untouched.
            self.assertEqual(
                {"name": "bell"},
                json.loads((bucket_dir / "story.json").read_text(encoding="utf-8")),
            )

    def test_invalid_payload_is_rejected_and_not_written(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            # Missing "assessments" entirely -- validate_sidecar rejects.
            invalid_payload = {
                "schema_version": "genre-sidecar-v1",
                "lcats_id": "anderson/bell",
                "story_path": "anderson/bell/story.json",
            }
            _write_manifest(
                manifest_path, [_envelope("anderson/bell", invalid_payload)]
            )

            report = promote.promote_sidecar_insert(manifest_path, dest_root, "genre")

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
            payload = _valid_sidecar_record("anderson/bell", "anderson/bell/story.json")
            _write_manifest(manifest_path, [_envelope("anderson/bell", payload)])

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

            # Even upsert (create-or-overwrite) must refuse a legacy flat
            # sidecar at the destination -- converting it in place is
            # lcats annotate's job, not this function's.
            report = promote.promote_sidecar_upsert(manifest_path, dest_root, "genre")

            self.assertEqual((), report.promoted)
            self.assertEqual(1, len(report.rejected))
            self.assertIn("legacy", report.rejected[0].error)
            # The legacy sidecar must survive untouched, not be overwritten.
            self.assertEqual(
                legacy_sidecar,
                json.loads((bucket_dir / "genre.json").read_text(encoding="utf-8")),
            )

    def test_insert_refuses_when_destination_already_exists(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            payload = _valid_sidecar_record("anderson/bell", "anderson/bell/story.json")
            _write_manifest(manifest_path, [_envelope("anderson/bell", payload)])

            bucket_dir = dest_root / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )
            existing = _valid_sidecar_record(
                "anderson/bell", "anderson/bell/story.json"
            )
            (bucket_dir / "genre.json").write_text(
                json.dumps(existing), encoding="utf-8"
            )

            report = promote.promote_sidecar_insert(manifest_path, dest_root, "genre")

            self.assertEqual((), report.promoted)
            self.assertEqual(1, len(report.rejected))
            self.assertIn("already exists", report.rejected[0].error)
            self.assertEqual(
                existing,
                json.loads((bucket_dir / "genre.json").read_text(encoding="utf-8")),
            )

    def test_upsert_overwrites_an_existing_destination(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            new_payload = _valid_sidecar_record(
                "anderson/bell", "anderson/bell/story.json"
            )
            _write_manifest(manifest_path, [_envelope("anderson/bell", new_payload)])

            bucket_dir = dest_root / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )
            old_payload = _valid_sidecar_record(
                "anderson/bell", "anderson/bell/story.json"
            )
            old_payload["story_path"] = "stale"
            (bucket_dir / "genre.json").write_text(
                json.dumps(old_payload), encoding="utf-8"
            )

            report = promote.promote_sidecar_upsert(manifest_path, dest_root, "genre")

            self.assertEqual(("anderson/bell",), report.promoted)
            self.assertEqual((), report.rejected)
            self.assertEqual(
                new_payload,
                json.loads((bucket_dir / "genre.json").read_text(encoding="utf-8")),
            )

    def test_dry_run_makes_no_writes(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            payload = _valid_sidecar_record("anderson/bell", "anderson/bell/story.json")
            _write_manifest(manifest_path, [_envelope("anderson/bell", payload)])

            bucket_dir = dest_root / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )

            report = promote.promote_sidecar_insert(
                manifest_path, dest_root, "genre", dry_run=True
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
                _envelope(
                    lcats_id,
                    _valid_sidecar_record(lcats_id, f"{lcats_id}/story.json"),
                )
                for lcats_id in escaping_ids
            ]
            _write_manifest(manifest_path, records)

            report = promote.promote_sidecar_insert(manifest_path, dest_root, "genre")

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
            payload = _valid_sidecar_record(
                "anderson/typo_d_id", "anderson/typo_d_id/story.json"
            )
            _write_manifest(manifest_path, [_envelope("anderson/typo_d_id", payload)])

            report = promote.promote_sidecar_insert(manifest_path, dest_root, "genre")

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
            good_payload = _valid_sidecar_record(
                "anderson/bell", "anderson/bell/story.json"
            )
            manifest_path.write_text(
                "not valid json\n"
                + json.dumps(_envelope("anderson/bell", good_payload))
                + "\n",
                encoding="utf-8",
            )
            bucket_dir = dest_root / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )

            report = promote.promote_sidecar_insert(manifest_path, dest_root, "genre")

            self.assertEqual(("anderson/bell",), report.promoted)
            self.assertEqual(1, len(report.rejected))
            self.assertIn("<line 1>", report.rejected[0].lcats_id)

    def test_envelope_with_neither_payload_nor_own_lcats_id_is_rejected(self):
        # No "payload" field, and no top-level lcats_id either -- so
        # neither the envelope path nor the bare-record compatibility
        # path (which requires the record's own lcats_id) can apply.
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            _write_manifest(manifest_path, [{"unrelated": "value"}])

            report = promote.promote_sidecar_insert(manifest_path, dest_root, "genre")

            self.assertEqual((), report.promoted)
            self.assertEqual(1, len(report.rejected))
            self.assertIn("payload", report.rejected[0].error)

    def test_scenes_payload_with_no_identity_field_is_promoted_via_envelope(self):
        """The whole point of the manifest-identity envelope (review
        finding, PR #401): scenes.json payloads (annotate.py's
        _annotate_scenes() output) carry no story-identity field of their
        own, unlike genre-sidecar-v1 payloads -- routing must come from
        the envelope's lcats_id, never the payload's own fields."""
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            scenes_payload = {
                "segments": [{"start": 0, "end": 10}],
                "segment_count": 1,
                "model": "gpt-4o",
                "input_tokens": 100,
                "output_tokens": 50,
            }
            _write_manifest(manifest_path, [_envelope("anderson/bell", scenes_payload)])

            bucket_dir = dest_root / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )

            report = promote.promote_sidecar_insert(manifest_path, dest_root, "scenes")

            self.assertEqual(("anderson/bell",), report.promoted)
            self.assertEqual(
                scenes_payload,
                json.loads((bucket_dir / "scenes.json").read_text(encoding="utf-8")),
            )

    def test_unregistered_sidecar_kind_is_refused_by_default(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            _write_manifest(
                manifest_path, [_envelope("anderson/bell", {"anything": True})]
            )

            with self.assertRaises(ValueError) as ctx:
                promote.promote_sidecar_insert(
                    manifest_path, dest_root, "wordcloud.png"
                )
            self.assertIn("no registered validator", str(ctx.exception))

    def test_allow_unvalidated_permits_an_unregistered_sidecar_kind(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            payload = {"anything": True}
            _write_manifest(manifest_path, [_envelope("anderson/bell", payload)])

            bucket_dir = dest_root / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )

            report = promote.promote_sidecar_insert(
                manifest_path,
                dest_root,
                "wordcloud.png",
                allow_unvalidated=True,
            )

            self.assertEqual(("anderson/bell",), report.promoted)
            self.assertEqual(
                payload,
                json.loads((bucket_dir / "wordcloud.png").read_text(encoding="utf-8")),
            )

    def test_allow_unvalidated_does_not_bypass_a_registered_validators_rejection(self):
        """--allow-unvalidated only covers the no-registered-validator
        case; a registered validator's own rejection of malformed content
        is never bypassable (resolves the adopted proposal's Open
        Question; WI-PROMOTE-0097 acceptance)."""
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            # "genre" IS registered, so allow_unvalidated must not matter
            # here -- this invalid payload must still be rejected.
            invalid_payload = {
                "schema_version": "genre-sidecar-v1",
                "lcats_id": "anderson/bell",
                "story_path": "anderson/bell/story.json",
            }
            _write_manifest(
                manifest_path, [_envelope("anderson/bell", invalid_payload)]
            )

            report = promote.promote_sidecar_insert(
                manifest_path, dest_root, "genre", allow_unvalidated=True
            )

            self.assertEqual((), report.promoted)
            self.assertEqual(1, len(report.rejected))

    def test_unsafe_sidecar_filename_is_rejected_even_with_allow_unvalidated(self):
        """P1 review finding, PR #405: --allow-unvalidated must not let an
        arbitrary --sidecar value escape the story bucket (path traversal)
        or overwrite the canonical story.json itself."""
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            _write_manifest(
                manifest_path, [_envelope("anderson/bell", {"anything": True})]
            )

            unsafe_names = [
                "../escape.json",
                "/etc/passwd",
                "sub/dir.json",
                "story.json",
                ".",
                "..",
            ]
            for unsafe_name in unsafe_names:
                with self.subTest(sidecar=unsafe_name):
                    with self.assertRaises(ValueError) as ctx:
                        promote.promote_sidecar_upsert(
                            manifest_path,
                            dest_root,
                            unsafe_name,
                            allow_unvalidated=True,
                        )
                    self.assertIn("unsafe sidecar filename", str(ctx.exception))

    def test_payload_lcats_id_mismatch_with_envelope_is_rejected(self):
        """P1 review finding, PR #405: an identity-bearing payload (e.g.
        genre-sidecar-v1) whose own lcats_id disagrees with the envelope's
        routing lcats_id must be rejected, not silently written into the
        wrong story's bucket."""
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            # Payload self-identifies as "anderson/other", but the envelope
            # routes it to "anderson/bell".
            payload = _valid_sidecar_record(
                "anderson/other", "anderson/other/story.json"
            )
            _write_manifest(manifest_path, [_envelope("anderson/bell", payload)])

            bucket_dir = dest_root / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )

            report = promote.promote_sidecar_insert(manifest_path, dest_root, "genre")

            self.assertEqual((), report.promoted)
            self.assertEqual(1, len(report.rejected))
            self.assertIn("does not match", report.rejected[0].error)
            self.assertFalse((bucket_dir / "genre.json").exists())

    def test_payload_lcats_id_agreeing_with_envelope_is_promoted(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            payload = _valid_sidecar_record("anderson/bell", "anderson/bell/story.json")
            _write_manifest(manifest_path, [_envelope("anderson/bell", payload)])

            bucket_dir = dest_root / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )

            report = promote.promote_sidecar_insert(manifest_path, dest_root, "genre")

            self.assertEqual(("anderson/bell",), report.promoted)

    def test_write_failure_is_a_per_line_rejection_not_a_fatal_abort(self):
        """P2 review finding, PR #405: a write-path exception (here, a
        payload json.dumps can't serialize) must be recorded as a
        per-line rejection like any other validation failure, not abort
        the whole manifest run."""
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            good_payload = _valid_sidecar_record(
                "anderson/bell", "anderson/bell/story.json"
            )
            _write_manifest(manifest_path, [_envelope("anderson/bell", good_payload)])

            for name in ("anderson/bell",):
                bucket_dir = dest_root / name
                bucket_dir.mkdir(parents=True)
                (bucket_dir / "story.json").write_text(
                    json.dumps({"name": "bell"}), encoding="utf-8"
                )

            with unittest.mock.patch(
                "lcats.analysis.corpus.promote._atomic_write_text",
                side_effect=OSError("disk full"),
            ):
                report = promote.promote_sidecar_insert(
                    manifest_path, dest_root, "genre"
                )

            self.assertEqual((), report.promoted)
            self.assertEqual(1, len(report.rejected))
            self.assertIn("failed to write sidecar", report.rejected[0].error)

    def test_bare_legacy_record_without_payload_wrapper_is_promoted(self):
        """Compatibility path (P1 review finding, PR #405): existing
        genre-sidecar-v1 manifests (e.g. WI-GENRE-0004's
        validation_results.jsonl, produced by
        experiments/05_metadata_genre_prefilter/run_prefilter.py and
        consumed by WI-GENRE-0077) have no "payload" wrapper -- they must
        stay promotable without a migration."""
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            bare_record = _valid_sidecar_record(
                "anderson/bell", "anderson/bell/story.json"
            )
            _write_manifest(manifest_path, [bare_record])

            bucket_dir = dest_root / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )

            report = promote.promote_sidecar_insert(manifest_path, dest_root, "genre")

            self.assertEqual(("anderson/bell",), report.promoted)
            self.assertEqual(
                bare_record,
                json.loads((bucket_dir / "genre.json").read_text(encoding="utf-8")),
            )

    def test_bare_record_with_no_identity_field_is_rejected(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            dest_root = pathlib.Path(dest_tmp)
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            _write_manifest(manifest_path, [{"segments": []}])

            report = promote.promote_sidecar_insert(manifest_path, dest_root, "scenes")

            self.assertEqual((), report.promoted)
            self.assertEqual(1, len(report.rejected))
            self.assertIn("no 'payload' field", report.rejected[0].error)

    def test_wholesale_promote_collections_is_unaffected(self):
        # Sanity check: adding the tranche path did not change
        # promote_collections' own wholesale behavior or shape.
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
            tempfile.TemporaryDirectory() as log_tmp,
        ):
            source_root = pathlib.Path(source_tmp)
            dest_root = pathlib.Path(dest_tmp)
            _write_story(source_root / "clean", "story_one", "A clean sentence.")

            report = promote.promote_collections(
                source_root, dest_root, log_dir=pathlib.Path(log_tmp)
            )

            self.assertEqual(("clean",), report.promoted)
            self.assertTrue(report.all_promoted)


class PromoteCliTest(unittest.TestCase):
    """Tests for the promote CLI exit-code and reporting behavior."""

    def setUp(self):
        # See PromoteCollectionsTest.setUp - same rationale, since
        # promote_cli.run(["replace", ...]) reaches the same
        # promote_collections() default log_dir.
        self._log_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._log_tmp.cleanup)
        self._log_dir_patch = unittest.mock.patch.object(
            promote, "DEFAULT_PROMOTE_LOG_DIR", pathlib.Path(self._log_tmp.name)
        )
        self._log_dir_patch.start()
        self.addCleanup(self._log_dir_patch.stop)

    def test_bare_invocation_with_no_mode_refuses(self):
        # WI-PROMOTE-0097 acceptance: an explicit mode is mandatory; a
        # bare invocation must refuse rather than defaulting to any
        # behavior.
        error_output = io.StringIO()
        with (
            unittest.mock.patch("sys.stderr", error_output),
            self.assertRaises(SystemExit) as ctx,
        ):
            promote_cli.run([])

        self.assertNotEqual(0, ctx.exception.code)

    def test_replace_mode_exit_code_zero_when_all_collections_promote(self):
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
                    ["replace", "--source", str(source_root), "--dest", str(dest_root)]
                )

            self.assertEqual(0, exit_code)
            self.assertIn("promoted: clean", output.getvalue())

    def test_replace_mode_exit_code_nonzero_when_a_collection_is_blocked(self):
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
                    ["replace", "--source", str(source_root), "--dest", str(dest_root)]
                )

            self.assertEqual(1, exit_code)
            self.assertIn("blocked: damaged", error_output.getvalue())

    def test_replace_mode_missing_source_directory_reports_clean_error_not_traceback(
        self,
    ):
        with tempfile.TemporaryDirectory() as dest_tmp:
            missing_source = pathlib.Path(dest_tmp) / "does_not_exist"

            error_output = io.StringIO()
            with unittest.mock.patch("sys.stderr", error_output):
                exit_code = promote_cli.run(
                    [
                        "replace",
                        "--source",
                        str(missing_source),
                        "--dest",
                        dest_tmp,
                        "some_collection",
                    ]
                )

            self.assertEqual(2, exit_code)
            self.assertIn("error:", error_output.getvalue())

    def test_replace_mode_source_equals_dest_reports_clean_error_not_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            error_output = io.StringIO()
            with unittest.mock.patch("sys.stderr", error_output):
                exit_code = promote_cli.run(["replace", "--source", tmp, "--dest", tmp])

            self.assertEqual(2, exit_code)
            self.assertIn("error:", error_output.getvalue())
            self.assertIn("same directory", error_output.getvalue())

    def test_insert_mode_reaches_the_insert_promotion_function(self):
        # The whole point of Required Change 1: the CLI must actually
        # invoke promote_sidecar_insert, not just the library function
        # called directly in tests above.
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            payload = _valid_sidecar_record("anderson/bell", "anderson/bell/story.json")
            _write_manifest(manifest_path, [_envelope("anderson/bell", payload)])
            bucket_dir = pathlib.Path(dest_tmp) / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )

            output = io.StringIO()
            with unittest.mock.patch("sys.stdout", output):
                exit_code = promote_cli.run(
                    [
                        "insert",
                        "--dest",
                        dest_tmp,
                        "--sidecar",
                        "genre",
                        "--tranche-manifest",
                        str(manifest_path),
                    ]
                )

            self.assertEqual(0, exit_code)
            self.assertIn("promoted sidecar: anderson/bell", output.getvalue())
            self.assertTrue(
                (pathlib.Path(dest_tmp) / "anderson" / "bell" / "genre.json").is_file()
            )

    def test_insert_mode_second_pass_on_same_destination_is_refused(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            payload = _valid_sidecar_record("anderson/bell", "anderson/bell/story.json")
            _write_manifest(manifest_path, [_envelope("anderson/bell", payload)])
            bucket_dir = pathlib.Path(dest_tmp) / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )
            insert_args = [
                "insert",
                "--dest",
                dest_tmp,
                "--sidecar",
                "genre",
                "--tranche-manifest",
                str(manifest_path),
            ]

            with unittest.mock.patch("sys.stdout", io.StringIO()):
                first_exit_code = promote_cli.run(insert_args)

            error_output = io.StringIO()
            with unittest.mock.patch("sys.stderr", error_output):
                second_exit_code = promote_cli.run(insert_args)

            self.assertEqual(0, first_exit_code)
            self.assertEqual(1, second_exit_code)
            self.assertIn("already exists", error_output.getvalue())

    def test_upsert_mode_reaches_the_upsert_promotion_function(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            payload = _valid_sidecar_record("anderson/bell", "anderson/bell/story.json")
            _write_manifest(manifest_path, [_envelope("anderson/bell", payload)])
            bucket_dir = pathlib.Path(dest_tmp) / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )
            (bucket_dir / "genre.json").write_text(
                json.dumps(payload | {"story_path": "stale"}), encoding="utf-8"
            )

            output = io.StringIO()
            with unittest.mock.patch("sys.stdout", output):
                exit_code = promote_cli.run(
                    [
                        "upsert",
                        "--dest",
                        dest_tmp,
                        "--sidecar",
                        "genre",
                        "--tranche-manifest",
                        str(manifest_path),
                    ]
                )

            self.assertEqual(0, exit_code)
            self.assertIn("promoted sidecar: anderson/bell", output.getvalue())
            self.assertEqual(
                payload,
                json.loads((bucket_dir / "genre.json").read_text(encoding="utf-8")),
            )

    def test_sidecar_flag_reports_rejections_and_nonzero_exit(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            invalid_payload = {
                "schema_version": "genre-sidecar-v1",
                "lcats_id": "anderson/bell",
                "story_path": "anderson/bell/story.json",
            }
            _write_manifest(
                manifest_path, [_envelope("anderson/bell", invalid_payload)]
            )

            error_output = io.StringIO()
            with unittest.mock.patch("sys.stderr", error_output):
                exit_code = promote_cli.run(
                    [
                        "insert",
                        "--dest",
                        dest_tmp,
                        "--sidecar",
                        "genre",
                        "--tranche-manifest",
                        str(manifest_path),
                    ]
                )

            self.assertEqual(1, exit_code)
            self.assertIn("rejected: anderson/bell", error_output.getvalue())

    def test_sidecar_flag_dry_run_makes_no_writes_via_cli(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            payload = _valid_sidecar_record("anderson/bell", "anderson/bell/story.json")
            _write_manifest(manifest_path, [_envelope("anderson/bell", payload)])
            bucket_dir = pathlib.Path(dest_tmp) / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )

            output = io.StringIO()
            with unittest.mock.patch("sys.stdout", output):
                exit_code = promote_cli.run(
                    [
                        "insert",
                        "--dest",
                        dest_tmp,
                        "--sidecar",
                        "genre",
                        "--tranche-manifest",
                        str(manifest_path),
                        "--dry-run",
                    ]
                )

            self.assertEqual(0, exit_code)
            self.assertIn("would promote sidecar: anderson/bell", output.getvalue())
            self.assertFalse((bucket_dir / "genre.json").exists())

    def test_allow_unvalidated_flag_reaches_the_promotion_function(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            _write_manifest(
                manifest_path, [_envelope("anderson/bell", {"anything": True})]
            )
            bucket_dir = pathlib.Path(dest_tmp) / "anderson" / "bell"
            bucket_dir.mkdir(parents=True)
            (bucket_dir / "story.json").write_text(
                json.dumps({"name": "bell"}), encoding="utf-8"
            )

            output = io.StringIO()
            with unittest.mock.patch("sys.stdout", output):
                exit_code = promote_cli.run(
                    [
                        "insert",
                        "--dest",
                        dest_tmp,
                        "--sidecar",
                        "wordcloud.png",
                        "--tranche-manifest",
                        str(manifest_path),
                        "--allow-unvalidated",
                    ]
                )

            self.assertEqual(0, exit_code)
            self.assertIn("promoted sidecar: anderson/bell", output.getvalue())

    def test_unvalidated_sidecar_without_the_flag_reports_clean_error(self):
        with (
            tempfile.TemporaryDirectory() as manifest_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            manifest_path = pathlib.Path(manifest_tmp) / "manifest.jsonl"
            _write_manifest(
                manifest_path, [_envelope("anderson/bell", {"anything": True})]
            )

            error_output = io.StringIO()
            with unittest.mock.patch("sys.stderr", error_output):
                exit_code = promote_cli.run(
                    [
                        "insert",
                        "--dest",
                        dest_tmp,
                        "--sidecar",
                        "wordcloud.png",
                        "--tranche-manifest",
                        str(manifest_path),
                    ]
                )

            self.assertEqual(2, exit_code)
            self.assertIn("no registered validator", error_output.getvalue())

    def test_replace_mode_is_unaffected_by_insert_upsert_additions(self):
        # Sanity check: the existing wholesale replace path and its exit
        # codes are unchanged now that it is reached only via the
        # explicit "replace" mode name.
        with (
            tempfile.TemporaryDirectory() as source_tmp,
            tempfile.TemporaryDirectory() as dest_tmp,
        ):
            source_root = pathlib.Path(source_tmp)
            _write_story(source_root / "clean", "story_one", "A clean sentence.")

            output = io.StringIO()
            with unittest.mock.patch("sys.stdout", output):
                exit_code = promote_cli.run(
                    ["replace", "--source", str(source_root), "--dest", dest_tmp]
                )

            self.assertEqual(0, exit_code)
            self.assertIn("promoted: clean", output.getvalue())


class SidecarValidatorsRegistryTest(unittest.TestCase):
    """Tests for the shared sidecar-validator registry (WI-PROMOTE-0097,
    PROP-LCATS-PROMOTE-MODE-REDESIGN Decision 5)."""

    def test_all_four_produced_kinds_are_registered(self):
        registered = sidecar_validators.registered_filenames()
        self.assertIn("genre.json", registered)
        self.assertIn("scenes.json", registered)
        self.assertIn("linguistics.json", registered)
        self.assertIn("linguistics.tokens.json", registered)
        self.assertEqual(4, len(registered))

    def test_get_validator_returns_none_for_unregistered_filename(self):
        self.assertIsNone(sidecar_validators.get_validator("wordcloud.png"))

    def test_get_validator_dispatches_genre(self):
        validator = sidecar_validators.get_validator("genre.json")
        result = validator({"not": "a genre sidecar"})
        self.assertFalse(result.valid)

    def test_get_validator_dispatches_scenes(self):
        validator = sidecar_validators.get_validator("scenes.json")
        self.assertTrue(validator({"segments": []}).valid)
        self.assertFalse(validator({"segments": None}).valid)
        self.assertFalse(validator(["not", "a", "dict"]).valid)

    def test_bare_name_assumes_json_extension(self):
        self.assertEqual(
            "genre.json", sidecar_validators.resolve_sidecar_filename("genre")
        )

    def test_name_with_extension_is_matched_exactly(self):
        self.assertEqual(
            "wordcloud.png",
            sidecar_validators.resolve_sidecar_filename("wordcloud.png"),
        )
        # "linguistics.tokens" contains a dot -- treated as an exact name,
        # not inferred as the compound linguistics.tokens.json filename.
        self.assertEqual(
            "linguistics.tokens",
            sidecar_validators.resolve_sidecar_filename("linguistics.tokens"),
        )

    def test_basename_collision_is_rejected_at_registration_time(self):
        colliding_registry = {
            "linguistics.json": sidecar_validators._validate_linguistics,
            "linguistics.png": sidecar_validators._validate_linguistics,
        }
        with self.assertRaises(ValueError) as ctx:
            sidecar_validators._check_no_basename_collisions(colliding_registry)
        self.assertIn("collision", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
