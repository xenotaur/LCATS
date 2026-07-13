"""Unit tests for lcats.analysis.corpus.repairs_cli."""

import io
import json
import pathlib
import tempfile
import unittest
import unittest.mock

from lcats.analysis.corpus import repairs
from lcats.analysis.corpus import repairs_cli


class RepairsCliTest(unittest.TestCase):
    """Tests for non-destructive dry-run repair proposal workflow."""

    def test_dry_run_does_not_modify_source_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = pathlib.Path(tmpdir) / "sample.txt"
            original_text = "A broken token: resumÃ©\n"
            file_path.write_text(original_text, encoding="utf-8")

            output = io.StringIO()
            with unittest.mock.patch("sys.stdout", output):
                exit_code = repairs_cli.run(["--header", str(file_path)])

            self.assertEqual(0, exit_code)
            self.assertEqual(original_text, file_path.read_text(encoding="utf-8"))

    def test_dry_run_output_includes_before_after_and_rule(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = pathlib.Path(tmpdir) / "sample.txt"
            file_path.write_text("trumpets of Ragnar√∂k.", encoding="utf-8")

            output = io.StringIO()
            with unittest.mock.patch("sys.stdout", output):
                repairs_cli.run([str(file_path)])

            report = output.getvalue().strip()
            self.assertIn("mojibake-macroman-o-diaeresis", report)
            self.assertIn("√∂", report)
            self.assertIn("ö", report)

    def test_story_json_input_scans_decoded_body(self):
        """Story JSON stores non-ASCII as ASCII escapes (json.dump default);
        the CLI must scan the decoded body field or every defect is an
        invisible false negative (WI-RULES-0016)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = pathlib.Path(tmpdir) / "story.json"
            story = {
                "name": "The Marrying Man",
                "body": "unnerving even to the blas√© eyes of Marilyn.",
                "metadata": {"author": "Test"},
            }
            with open(file_path, "w", encoding="utf-8") as handle:
                json.dump(story, handle, indent=4)

            raw = file_path.read_text(encoding="utf-8")
            self.assertNotIn("√", raw)  # escaped on disk — raw scan sees nothing

            output = io.StringIO()
            with unittest.mock.patch("sys.stdout", output):
                exit_code = repairs_cli.run(["--format", "jsonl", str(file_path)])

            self.assertEqual(0, exit_code)
            lines = output.getvalue().strip().splitlines()
            self.assertEqual(1, len(lines))
            payload = json.loads(lines[0])
            self.assertEqual("mojibake-macroman-e-acute", payload["rule_id"])
            self.assertEqual("√©", payload["original_text"])
            self.assertEqual("é", payload["replacement_text"])

    def test_non_story_json_input_falls_back_to_raw_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = pathlib.Path(tmpdir) / "notes.json"
            file_path.write_text('["se√±orita fixture"]', encoding="utf-8")

            output = io.StringIO()
            with unittest.mock.patch("sys.stdout", output):
                repairs_cli.run([str(file_path)])

            report = output.getvalue().strip()
            self.assertIn("mojibake-macroman-n-tilde", report)

    def test_build_dry_run_report_is_deterministic_and_auditable(self):
        suggestion = repairs.RepairSuggestion(
            rule_id="mojibake-right-single-quote",
            start=9,
            end=12,
            original_text="â€™",
            replacement_text="’",
            finding_offset=9,
            evidence="rule=mojibake-pattern; fragment=â€™",
            confidence="high",
            rationale="Broken UTF-8 right single quote sequence.",
        )

        report = repairs.build_dry_run_report([suggestion], file_label="story.txt")

        self.assertIn("story.txt:9-12", report)
        self.assertIn("before=â€™", report)
        self.assertIn("after=’", report)
        self.assertIn("confidence=high", report)

    def test_jsonl_output_is_machine_parseable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = pathlib.Path(tmpdir) / "sample.txt"
            file_path.write_text("she pay 90Â¢ for", encoding="utf-8")

            output = io.StringIO()
            with unittest.mock.patch("sys.stdout", output):
                repairs_cli.run(["--format", "jsonl", str(file_path)])

            lines = output.getvalue().strip().splitlines()
            self.assertEqual(1, len(lines))
            payload = json.loads(lines[0])
            self.assertEqual(str(file_path), payload["path"])
            self.assertEqual("Â¢", payload["original_text"])
            self.assertEqual("¢", payload["replacement_text"])


if __name__ == "__main__":
    unittest.main()
