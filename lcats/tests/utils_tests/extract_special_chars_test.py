import importlib.util
import io
import pathlib
import tempfile
import unittest
import unittest.mock


def load_module(module_path: pathlib.Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExtractSpecialCharsScriptTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        root = pathlib.Path(__file__).resolve().parents[2]
        cls.module = load_module(
            root / "scripts" / "utils" / "extract_special_chars.py",
            "extract_special_chars_script",
        )

    def test_default_context_extracts_left_and_right_characters(self):
        text = "0123456789pi√©ce"
        rows = list(
            self.module.iter_special_character_rows(
                path="stdin",
                text=text,
                allow_smart=False,
                excluded=set(),
                allowlist=self.module.AllowlistConfig(),
                context=10,
                name_width=0,
            )
        )

        self.assertEqual(2, len(rows))
        first = rows[0].split("\t")
        second = rows[1].split("\t")

        self.assertEqual("U+221A", first[1])
        self.assertEqual("23456789pi√©ce", first[6])
        self.assertEqual("U+00A9", second[1])
        self.assertEqual("3456789pi√©ce", second[6])

    def test_context_zero_suppresses_context_column_value(self):
        text = "pi√©ce"
        rows = list(
            self.module.iter_special_character_rows(
                path="stdin",
                text=text,
                allow_smart=False,
                excluded=set(),
                allowlist=self.module.AllowlistConfig(),
                context=0,
                name_width=0,
            )
        )

        for row in rows:
            parts = row.split("\t")
            self.assertEqual("", parts[6])

    def test_occurrence_reporting_counts_repeated_character(self):
        text = "x©y©z"
        rows = list(
            self.module.iter_special_character_rows(
                path="stdin",
                text=text,
                allow_smart=False,
                excluded=set(),
                allowlist=self.module.AllowlistConfig(),
                context=10,
                name_width=0,
            )
        )

        self.assertEqual(2, len(rows))
        self.assertEqual("1", rows[0].split("\t")[4])
        self.assertEqual("2", rows[1].split("\t")[4])
        self.assertEqual("1", rows[0].split("\t")[5])
        self.assertEqual("3", rows[1].split("\t")[5])

    def test_tsv_escaping_and_target_character_present(self):
        text = "a\t©\n\rb"
        rows = list(
            self.module.iter_special_character_rows(
                path="stdin",
                text=text,
                allow_smart=False,
                excluded=set(),
                allowlist=self.module.AllowlistConfig(),
                context=10,
                name_width=0,
            )
        )

        fields = rows[0].split("\t")
        self.assertEqual("©", fields[2])
        self.assertIn("\\t", fields[6])
        self.assertIn("\\n", fields[6])
        self.assertIn("\\r", fields[6])
        self.assertIn("©", fields[6])

    def test_unicode_name_fallback_for_unnamed_char(self):
        unnamed_char = chr(0x0378)
        rows = list(
            self.module.iter_special_character_rows(
                path="stdin",
                text=unnamed_char,
                allow_smart=False,
                excluded=set(),
                allowlist=self.module.AllowlistConfig(),
                context=10,
                name_width=0,
            )
        )

        fields = rows[0].split("\t")
        self.assertEqual("UNKNOWN", fields[3])

    def test_name_width_truncates_unicode_name(self):
        text = "√"
        rows = list(
            self.module.iter_special_character_rows(
                path="stdin",
                text=text,
                allow_smart=False,
                excluded=set(),
                allowlist=self.module.AllowlistConfig(),
                context=10,
                name_width=6,
            )
        )

        self.assertEqual("SQUAR…", rows[0].split("\t")[3])

    def test_deterministic_ordering_is_by_offset(self):
        text = "©√"
        rows = list(
            self.module.iter_special_character_rows(
                path="stdin",
                text=text,
                allow_smart=False,
                excluded=set(),
                allowlist=self.module.AllowlistConfig(),
                context=10,
                name_width=0,
            )
        )

        self.assertEqual("U+00A9", rows[0].split("\t")[1])
        self.assertEqual("U+221A", rows[1].split("\t")[1])

    def test_cli_nocontext_sets_context_to_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = pathlib.Path(tmpdir) / "sample.txt"
            file_path.write_text("pi√©ce", encoding="utf-8")
            output = io.StringIO()
            with unittest.mock.patch("sys.stdout", output):
                exit_code = self.module.main(["--nocontext", str(file_path)])

        self.assertEqual(0, exit_code)
        lines = [line for line in output.getvalue().splitlines() if line.strip()]
        self.assertEqual(2, len(lines))
        self.assertEqual("", lines[0].split("\t")[6])

    def test_classification_distinguishes_good_repairable_and_review(self):
        text = "‘quote’ Ã©      √"
        rows = list(
            self.module.iter_special_character_rows(
                path="stdin",
                text=text,
                allow_smart=False,
                excluded=set(),
                allowlist=self.module.AllowlistConfig(),
                context=10,
                name_width=0,
            )
        )

        classifications = [row.split("\t")[7] for row in rows]
        self.assertIn("likely_good", classifications)
        self.assertIn("likely_repairable", classifications)
        self.assertIn("review_needed", classifications)

    def test_allowlist_config_allows_configured_character(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir) / "allowlist.json"
            config_path.write_text(
                '{"allowed_codepoints":["00A9"]}',
                encoding="utf-8",
            )
            allowlist = self.module.load_allowlist_config(str(config_path))

        rows = list(
            self.module.iter_special_character_rows(
                path="stdin",
                text="©",
                allow_smart=False,
                excluded=set(),
                allowlist=allowlist,
                context=10,
                name_width=0,
            )
        )
        self.assertEqual([], rows)

    def test_legacy_wrapper_delegates_to_corpus_specials_library(self):
        with unittest.mock.patch.object(
            self.module.specials, "iter_special_character_rows", return_value=["x\ty"]
        ) as mock_rows:
            rows = list(
                self.module.iter_special_character_rows(
                    path="stdin",
                    text="©",
                    allow_smart=False,
                    excluded=set(),
                    allowlist=self.module.AllowlistConfig(),
                    context=10,
                    name_width=0,
                )
            )

        self.assertEqual(["stdin\tx\ty"], rows)
        mock_rows.assert_called_once()


if __name__ == "__main__":
    unittest.main()
