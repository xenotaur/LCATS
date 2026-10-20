"""Exercise real saved-candidate review and exported publication without network."""

import copy
import dataclasses
import json
import os
import pathlib
import socket
import tempfile
import unittest
from unittest import mock

from lcats import cli
from lcats.gatherers import candidate_review
from lcats.gatherers import downloaders
from lcats.gatherers import parser
from lcats.gatherers import readiness
from lcats.gatherers import review_store
from lcats.utils import capture
from tests.gatherers_tests import mass_quantities_test


class CandidateReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = pathlib.Path(temporary.name)
        self.queue = self.root / "queue"
        self.dispositions = self.root / "dispositions"
        patch = mock.patch.dict(
            os.environ,
            LCATS_DATA_DIR=str(self.root / "data"),
            LCATS_CORPORA_DIR=str(self.root / "corpora"),
        )
        patch.start()
        self.addCleanup(patch.stop)
        network = mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        )
        network.start()
        self.addCleanup(network.stop)
        self.body = mass_quantities_test.BODY + "\n\nThe traveler said “café 🦉”."
        self.text = "Transcriber's Note\n\n" + self.body
        self.source = mass_quantities_test.MemorySource({1: self.text})
        self.report = parser.inspect_story(1, source=self.source)
        self.path = pathlib.Path(
            review_store.save(
                self.report, directory=self.queue, data_root=self.root / "data"
            )
        )
        self.start = self.text.index(self.body)

    def record(self, outcome="approve", **kwargs):
        options = dict(
            outcome=outcome,
            reviewer="fixture reviewer",
            rationale="Reviewed the full authored narrative.",
            directory=self.dispositions,
        )
        if outcome == "approve":
            options.update(start=self.start, end=len(self.text))
        options.update(kwargs)
        return pathlib.Path(candidate_review.record_disposition(self.path, **options))

    def write_candidate(self, record):
        path = self.queue / f"1-{readiness.identity(record)}.candidate.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        return path

    def test_cli_workflow_exports_exact_selection_and_real_gather_publishes(self):
        message, status = cli.dispatch(
            "gather-review",
            [
                "show",
                str(self.path),
                "--start",
                str(self.start),
                "--end",
                str(len(self.text)),
            ],
        )
        self.assertEqual(status, 0, message)
        packet = json.loads(message)
        self.assertEqual(packet["window"]["text"], self.body)
        self.assertEqual(packet["omitted_before"], self.start)
        self.assertEqual(packet["omitted_after"], 0)
        message, status = cli.dispatch(
            "gather-review",
            [
                "record",
                str(self.path),
                "--outcome",
                "approve",
                "--reviewer",
                "fixture reviewer",
                "--rationale",
                "Complete authored body.",
                "--start",
                str(self.start),
                "--end",
                str(len(self.text)),
                "--directory",
                str(self.dispositions),
            ],
        )
        self.assertEqual(status, 0, message)
        disposition = pathlib.Path(json.loads(message)["disposition"])
        output = self.root / "approvals.json"
        message, status = cli.dispatch(
            "gather-review",
            [
                "export",
                str(disposition),
                "--candidates",
                str(self.queue),
                "--output",
                str(output),
            ],
        )
        self.assertEqual(status, 0, message)
        self.assertEqual(list(self.root.rglob("story.json")), [])
        decisions = readiness.load_decisions(output)
        with capture.capture_output():
            result = parser.gather_story(
                downloaders.DataGatherer("test", root=self.root / "data"),
                1,
                source=self.source,
                review_decision=decisions[1],
            )
        self.assertEqual(result.status, "published")
        self.assertEqual(
            json.loads(pathlib.Path(result.path).read_text())["body"], self.body
        )
        # The export validates saved evidence; a changed acquisition still fails.
        self.source.inputs[1] += "\n\nAnother source sentence."
        with self.assertRaisesRegex(ValueError, "stale"):
            parser.inspect_story(1, source=self.source, review_decision=decisions[1])

    def test_preview_exposes_omissions_and_exact_unicode_offsets(self):
        packet = candidate_review.preview(
            self.path, start=len(self.text) - 7, end=len(self.text)
        )
        self.assertEqual(packet["window"]["text"], self.text[-7:])
        self.assertGreater(packet["omitted_before"], 0)
        first = candidate_review.preview(self.path, end=5)
        self.assertEqual(first["next_start"], 5)
        self.assertEqual(first["window"]["text"], self.text[:5])
        self.assertEqual(first["finding_count"], 1)
        for start, end in [
            (True, 5),
            (-1, 5),
            (0, 0),
            (0, len(self.text) + 1),
            (0, False),
        ]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                candidate_review.preview(self.path, start=start, end=end)

    def test_inventory_reports_generations_conflicts_and_no_latest_wins(self):
        self.assertEqual(
            candidate_review.inventory(self.queue)["counts"], {"unreviewed": 1}
        )
        approval = self.record()
        self.assertEqual(
            candidate_review.inventory(self.queue, dispositions=self.dispositions)[
                "counts"
            ],
            {"approve": 1},
        )
        self.record("defer", rationale="Need another source review.")
        self.assertEqual(
            candidate_review.inventory(self.queue, dispositions=self.dispositions)[
                "counts"
            ],
            {"conflict": 1},
        )
        self.source.inputs[1] += "\n\nAdditional source text."
        report = parser.inspect_story(1, source=self.source)
        review_store.save(report, directory=self.queue, data_root=self.root / "data")
        inventory = candidate_review.inventory(
            self.queue, dispositions=self.dispositions
        )
        self.assertEqual(inventory["multiple_generation_ids"], [1])
        self.assertEqual(inventory["counts"], {"conflict": 1, "unreviewed": 1})
        # Export is an explicit record selection, never inferred from this conflict.
        candidate_review.export_approvals(
            [approval], candidates=self.queue, output=self.root / "selected.json"
        )

    def test_nonapproval_dispositions_never_export_or_publish(self):
        for outcome in ("exclude", "defer"):
            path = self.record(outcome)
            record = candidate_review.load_disposition(path)
            self.assertIsNone(record["approval"])
            with self.assertRaisesRegex(ValueError, "only explicit approval"):
                candidate_review.export_approvals(
                    [path], candidates=self.queue, output=self.root / "bad.json"
                )
            with self.assertRaisesRegex(ValueError, "only approval"):
                self.record(outcome, start=0)
        self.assertFalse((self.root / "bad.json").exists())
        self.assertEqual(list(self.root.rglob("story.json")), [])

    def test_idempotent_records_and_exports_do_not_replace_unequal_files(self):
        path = self.record()
        original = path.read_bytes()
        self.assertEqual(path, self.record())
        self.assertEqual(path.read_bytes(), original)
        output = self.root / "approvals.json"
        candidate_review.export_approvals([path], candidates=self.queue, output=output)
        before = output.read_bytes()
        candidate_review.export_approvals([path], candidates=self.queue, output=output)
        self.assertEqual(output.read_bytes(), before)
        output.write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "differs"):
            candidate_review.export_approvals(
                [path], candidates=self.queue, output=output
            )
        self.assertEqual(output.read_text(), "[]")

    def test_candidate_renaming_does_not_hide_inconsistent_internal_hashes(self):
        for field in ("body", "metadata", "source", "assessment", "span"):
            record = copy.deepcopy(json.loads(self.path.read_text()))
            report = record["report"]
            if field == "body":
                report["body"] += "x"
                report["selected_span"][1] += 1
            elif field == "metadata":
                report["metadata"]["titles"] = ["Another title"]
            elif field == "source":
                report["provenance"]["source_uri"] = "https://other.invalid/"
            elif field == "assessment":
                report["provenance"]["publication_readiness"]["policy"] = "new-policy"
            else:
                report["provenance"]["publication_readiness"]["findings"][0]["span"] = [
                    0,
                    len(self.text) + 1,
                ]
            altered = self.write_candidate(record)
            with self.subTest(field=field), self.assertRaises(ValueError):
                candidate_review.load_candidate(altered)

    def test_filename_duplicate_fields_and_nonfinite_json_are_rejected(self):
        wrong = self.queue / "wrong.candidate.json"
        wrong.write_bytes(self.path.read_bytes())
        with self.assertRaisesRegex(ValueError, "filename"):
            candidate_review.load_candidate(wrong)
        for value in ('{"schema_version":1,"schema_version":1}', '{"x":NaN}'):
            wrong.write_text(value, encoding="utf-8")
            with self.assertRaises(ValueError):
                candidate_review.load_candidate(wrong)

    def test_missing_wrong_candidate_and_repeated_ids_block_export(self):
        path = self.record()
        with self.assertRaisesRegex(ValueError, "duplicate Gutenberg"):
            candidate_review.export_approvals(
                [path, path], candidates=self.queue, output=self.root / "out.json"
            )
        self.path.unlink()
        inventory = candidate_review.inventory(
            self.queue, dispositions=self.dispositions
        )
        self.assertEqual(inventory["candidate_count"], 0)
        self.assertEqual(len(inventory["unmatched_disposition_candidates"]), 1)
        with self.assertRaises(ValueError):
            candidate_review.export_approvals(
                [path], candidates=self.queue, output=self.root / "out.json"
            )
        self.assertFalse((self.root / "out.json").exists())

    def test_tampered_approval_span_hash_is_rejected_even_with_new_record_name(self):
        path = self.record()
        record = json.loads(path.read_text())
        record["approval"]["selected_sha256"] = "0" * 64
        altered = path.parent / f"1-{readiness.identity(record)}.disposition.json"
        altered.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "stale"):
            candidate_review.export_approvals(
                [altered], candidates=self.queue, output=self.root / "out.json"
            )

    def test_records_and_exports_refuse_collection_roots_and_symlinks(self):
        for name in ("data", "corpora"):
            with (
                self.subTest(name=name),
                self.assertRaisesRegex(ValueError, "outside data/corpora"),
            ):
                self.record(directory=self.root / name)
        alias = self.root / "alias"
        alias.symlink_to(self.root / "data", target_is_directory=True)
        with self.assertRaises(ValueError):
            self.record(directory=alias)
        path = self.record()
        target = self.root / "target"
        target.write_text("untouched")
        output = self.root / "out.json"
        output.symlink_to(target)
        with self.assertRaises(OSError):
            candidate_review.export_approvals(
                [path], candidates=self.queue, output=output
            )
        self.assertEqual(target.read_text(), "untouched")

    def test_bounds_fail_explicitly_without_unbounded_inventory_or_output(self):
        with mock.patch.object(candidate_review, "MAX_CANDIDATE_BYTES", 10):
            with self.assertRaisesRegex(ValueError, "exceeds"):
                candidate_review.load_candidate(self.path)
        with mock.patch.object(candidate_review, "MAX_FILES", 0):
            with self.assertRaisesRegex(ValueError, "exceeds"):
                candidate_review.inventory(self.queue)
        with mock.patch.object(candidate_review, "MAX_SCAN_BYTES", 10):
            with self.assertRaisesRegex(ValueError, "scan exceeds"):
                candidate_review.inventory(self.queue)
        with mock.patch.object(candidate_review, "MAX_DISPOSITION_BYTES", 20):
            with self.assertRaisesRegex(ValueError, "output exceeds"):
                self.record()
        self.assertFalse(self.dispositions.exists())

    def test_cli_errors_are_nonzero_and_do_not_publish(self):
        for args in (
            ["show", str(self.root / "missing")],
            [
                "record",
                str(self.path),
                "--outcome",
                "approve",
                "--reviewer",
                "me",
                "--rationale",
                "why",
            ],
            ["list", str(self.root / "missing")],
        ):
            message, status = cli.dispatch("gather-review", args)
            self.assertEqual(status, 2, message)
        self.assertEqual(list(self.root.rglob("story.json")), [])

    def test_malformed_disposition_types_fail_as_input_errors(self):
        original = json.loads(self.record().read_text())
        for field, value in (
            ("outcome", []),
            ("approval", []),
            ("gutenberg_id", True),
            ("schema_version", True),
            ("reviewer", None),
            ("candidate_record_sha256", 1),
        ):
            record = {**original, field: value}
            path = (
                self.dispositions / f"1-{readiness.identity(record)}.disposition.json"
            )
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.subTest(field=field), self.assertRaises(ValueError):
                candidate_review.load_disposition(path)

    def test_export_matches_existing_explicit_approval_contract(self):
        path = self.record()
        decision = readiness.ReviewDecision.for_report(
            self.report,
            start=self.start,
            end=len(self.text),
            reviewer="fixture reviewer",
            rationale="Reviewed the full authored narrative.",
        )
        self.assertEqual(
            candidate_review.load_disposition(path)["approval"],
            dataclasses.asdict(decision),
        )

    def test_malformed_candidate_shapes_fail_as_cli_input_errors(self):
        original = json.loads(self.path.read_text())
        for field, value in (
            ("report", []),
            ("provenance", []),
            ("metadata", None),
            ("selected_span", [False, len(self.text)]),
            ("findings", [None]),
            ("findings", [{"kind": "cue", "span": [0, 1], "message": "x"}]),
        ):
            record = copy.deepcopy(original)
            if field == "report":
                record[field] = value
            elif field == "findings":
                record["report"]["provenance"]["publication_readiness"][field] = value
            else:
                record["report"][field] = value
            path = self.write_candidate(record)
            message, code = cli.dispatch("gather-review", ["show", str(path)])
            with self.subTest(field=field, value=value):
                self.assertEqual(code, 2, message)

    def test_preview_window_limit_and_symlink_input_are_rejected(self):
        with mock.patch.object(candidate_review, "MAX_WINDOW", 10):
            with self.assertRaisesRegex(ValueError, "at most 10"):
                candidate_review.preview(self.path, end=11)
        alias = self.root / self.path.name
        alias.symlink_to(self.path)
        with self.assertRaisesRegex(ValueError, "non-symlink"):
            candidate_review.load_candidate(alias)

    def test_aggregate_export_bound_counts_candidates_as_well_as_decisions(self):
        path = self.record()
        with mock.patch.object(candidate_review, "MAX_SCAN_BYTES", path.stat().st_size):
            with self.assertRaisesRegex(ValueError, "candidate scan"):
                candidate_review.export_approvals(
                    [path], candidates=self.queue, output=self.root / "out.json"
                )
        self.assertFalse((self.root / "out.json").exists())

    def test_identical_intents_with_different_reviewers_do_not_conflict(self):
        self.record()
        self.record(reviewer="second reviewer", rationale="Independent same span.")
        inventory = candidate_review.inventory(
            self.queue, dispositions=self.dispositions
        )
        self.assertEqual(inventory["counts"], {"approve": 1})
        self.assertEqual(len(inventory["candidates"][0]["dispositions"]), 2)
        self.record(start=self.start + 1)
        self.assertEqual(
            candidate_review.inventory(self.queue, dispositions=self.dispositions)[
                "counts"
            ],
            {"conflict": 1},
        )

    def test_empty_export_and_wrong_attribution_cannot_create_outputs(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            candidate_review.export_approvals(
                [], candidates=self.queue, output=self.root / "out.json"
            )
        original = json.loads(self.record().read_text())
        altered = {**original, "reviewer": "another reviewer"}
        path = self.dispositions / f"1-{readiness.identity(altered)}.disposition.json"
        path.write_text(json.dumps(altered))
        with self.assertRaisesRegex(ValueError, "attribution"):
            candidate_review.load_disposition(path)
        self.assertFalse((self.root / "out.json").exists())

    def test_json_number_type_changes_are_not_equal_output_reuse(self):
        path = self.record()
        original = json.loads(path.read_text())
        altered = {**original, "schema_version": True}
        path.write_text(json.dumps(altered))
        with self.assertRaisesRegex(ValueError, "differs"):
            self.record()
        self.assertEqual(json.loads(path.read_text())["schema_version"], True)
        path.write_text(json.dumps(original))
        output = self.root / "out.json"
        candidate_review.export_approvals([path], candidates=self.queue, output=output)
        altered = json.loads(output.read_text())
        altered[0]["gutenberg_id"] = float(altered[0]["gutenberg_id"])
        output.write_text(json.dumps(altered))
        with self.assertRaisesRegex(ValueError, "differs"):
            candidate_review.export_approvals(
                [path], candidates=self.queue, output=output
            )
