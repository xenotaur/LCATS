"""Unit tests for lcats.analysis.corpus.repairs_cli."""

import io
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
            original_text = "A broken token: â€™\n"
            file_path.write_text(original_text, encoding="utf-8")

            output = io.StringIO()
            with unittest.mock.patch("sys.stdout", output):
                exit_code = repairs_cli.run(["--header", str(file_path)])

            self.assertEqual(0, exit_code)
            self.assertEqual(original_text, file_path.read_text(encoding="utf-8"))

    def test_dry_run_output_includes_before_after_and_rule(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = pathlib.Path(tmpdir) / "sample.txt"
            file_path.write_text("Example â€¦ token", encoding="utf-8")

            output = io.StringIO()
            with unittest.mock.patch("sys.stdout", output):
                repairs_cli.run([str(file_path)])

            report = output.getvalue().strip()
            self.assertIn("mojibake-ellipsis", report)
            self.assertIn("â€¦", report)
            self.assertIn("…", report)

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


if __name__ == "__main__":
    unittest.main()
