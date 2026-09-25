"""Tests for the resumable experiment-local POS audit helper."""

from __future__ import annotations

import argparse
import contextlib
import csv
import importlib.util
import io
import pathlib
import tempfile
import unittest

PATH = pathlib.Path(__file__).resolve().parent / "audit_pos.py"
SPEC = importlib.util.spec_from_file_location("audit_pos", PATH)
assert SPEC is not None and SPEC.loader is not None
audit_pos = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit_pos)


def write_packet(path: pathlib.Path) -> list[dict[str, str]]:
    rows = [
        {
            "story_id": "fantasy/one",
            "selection_genre": "fantasy",
            "audit_bucket": "NOUN",
            "audit_features": "ordinary",
            "token_key": "fantasy/one#g1",
            "sentence_index": "0",
            "token_index": "1",
            "global_token_index": "1",
            "text": "Machine",
            "lemma": "machine",
            "machine_upos": "NOUN",
            "context": "The Machine hums.",
            "gold_upos": "",
            "notes": "",
        },
        {
            "story_id": "mystery/two",
            "selection_genre": "mystery",
            "audit_bucket": "OTHER",
            "audit_features": "ordinary",
            "token_key": "mystery/two#g2",
            "sentence_index": "0",
            "token_index": "1",
            "global_token_index": "2",
            "text": "runs",
            "lemma": "run",
            "machine_upos": "VERB",
            "context": "It runs.",
            "gold_upos": "",
            "notes": "",
        },
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=audit_pos.IMMUTABLE_FIELDS + ("gold_upos", "notes")
        )
        writer.writeheader()
        writer.writerows(rows)
    return rows


class AuditPosTest(unittest.TestCase):
    def test_start_and_next_are_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            sample = root / "sample.csv"
            ledger_path = root / "ledger.json"
            rows = write_packet(sample)
            ledger = audit_pos.new_ledger(rows)
            audit_pos.write_json(ledger_path, ledger)

            self.assertEqual(rows[0]["token_key"], next(iter(ledger["entries"])))
            self.assertEqual([], audit_pos.validate_ledger(rows, ledger))
            self.assertEqual(
                rows[0]["token_key"],
                audit_pos.unresolved(ledger["entries"])[0]["token_key"],
            )

    def test_unresolved_rows_require_notes_and_scoring_waits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            rows = write_packet(root / "sample.csv")
            ledger = audit_pos.new_ledger(rows)
            self.assertEqual([], audit_pos.validate_ledger(rows, ledger))
            with self.assertRaisesRegex(ValueError, "cannot score audit"):
                audit_pos.score(rows, ledger)

    def test_recorded_issue_and_label_score_without_mutating_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            sample = root / "sample.csv"
            rows = write_packet(sample)
            original = sample.read_bytes()
            ledger = audit_pos.new_ledger(rows)
            first = ledger["entries"][rows[0]["token_key"]]
            first.update(
                {
                    "disposition": "reviewed",
                    "gold_upos": "NOUN",
                    "issue_codes": ["context"],
                    "reviewer": "tester",
                }
            )
            second = ledger["entries"][rows[1]["token_key"]]
            second.update({"disposition": "reviewed", "gold_upos": "OTHER"})
            result = audit_pos.score(rows, ledger)
            self.assertEqual(audit_pos.SCORED_SCHEMA_VERSION, result["schema_version"])
            self.assertEqual(["context"], result["rows"][0]["issue_codes"])
            self.assertEqual(original, sample.read_bytes())

    def test_stale_packet_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            sample = root / "sample.csv"
            rows = write_packet(sample)
            ledger = audit_pos.new_ledger(rows)
            rows[0]["text"] = "changed"
            self.assertIn(
                "packet fingerprint mismatch", audit_pos.validate_ledger(rows, ledger)
            )

    def test_guidance_identifies_ambiguous_features(self):
        guidance = audit_pos.audit_guidance(
            {"audit_features": "proper_name_candidate,noun_verb_ambiguous"}
        )
        self.assertTrue(any("named entity" in item for item in guidance))
        self.assertTrue(any("syntactic role" in item for item in guidance))

    def test_record_preserves_metadata_when_options_are_omitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            sample = root / "sample.csv"
            ledger_path = root / "ledger.json"
            rows = write_packet(sample)
            ledger = audit_pos.new_ledger(rows, sample)
            entry = ledger["entries"][rows[0]["token_key"]]
            entry.update(
                {
                    "disposition": "uncertain",
                    "issue_codes": ["segmentation"],
                    "notes": "Boundary needs adjudication.",
                    "reviewer": "tester",
                }
            )
            audit_pos.write_json(ledger_path, ledger)
            args = argparse.Namespace(
                sample=sample,
                ledger=ledger_path,
                token_key=rows[0]["token_key"],
                disposition="reviewed",
                label="NOUN",
                issue_code=None,
                notes=None,
                reviewer=None,
            )
            audit_pos.command_record(args)
            updated = audit_pos.load_ledger(ledger_path)["entries"][
                rows[0]["token_key"]
            ]
            self.assertEqual(["segmentation"], updated["issue_codes"])
            self.assertEqual("Boundary needs adjudication.", updated["notes"])
            self.assertEqual("tester", updated["reviewer"])

    def test_malformed_entry_is_rejected_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = write_packet(pathlib.Path(tmp) / "sample.csv")
            ledger = audit_pos.new_ledger(rows)
            ledger["entries"][rows[0]["token_key"]] = "not-an-object"
            errors = audit_pos.validate_ledger(rows, ledger)
            self.assertTrue(any("must be an object" in error for error in errors))

    def test_schema_and_row_count_mismatches_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = write_packet(pathlib.Path(tmp) / "sample.csv")
            ledger = audit_pos.new_ledger(rows)
            ledger["packet_schema_version"] = "wrong"
            ledger["row_count"] = 99
            errors = audit_pos.validate_ledger(rows, ledger)
            self.assertIn("packet schema version mismatch", errors)
            self.assertIn("ledger row count mismatch", errors)

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "ledger.json"
            path.write_text('{"schema_version":"x","schema_version":"y"}')
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                audit_pos.load_ledger(path)

    def test_start_command_refuses_existing_and_protected_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            sample = root / "sample.csv"
            ledger = root / "ledger.json"
            write_packet(sample)
            args = argparse.Namespace(sample=sample, ledger=ledger, force=False)
            audit_pos.command_start(args)
            self.assertEqual(2, len(audit_pos.load_ledger(ledger)["entries"]))
            with self.assertRaises(FileExistsError):
                audit_pos.command_start(args)
            with self.assertRaisesRegex(ValueError, "protected input"):
                audit_pos.command_start(
                    argparse.Namespace(sample=sample, ledger=sample, force=True)
                )

    def test_incomplete_packet_row_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "sample.csv"
            path.write_text(
                ",".join(audit_pos.PACKET_FIELDS) + "\n" + ",".join(["x"] * 12)
            )
            with self.assertRaisesRegex(ValueError, "canonical packet fields"):
                audit_pos.load_packet(path)

    def test_status_reports_missing_entries_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            sample = root / "sample.csv"
            ledger = root / "ledger.json"
            write_packet(sample)
            audit_pos.write_json(
                ledger,
                {
                    "schema_version": audit_pos.SCHEMA_VERSION,
                    "packet_schema_version": audit_pos.PACKET_SCHEMA_VERSION,
                },
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                audit_pos.command_status(
                    argparse.Namespace(sample=sample, ledger=ledger)
                )
            self.assertIn('"valid": false', output.getvalue())


if __name__ == "__main__":
    unittest.main()
