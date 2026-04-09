import importlib.util
import pathlib
import unittest
import unittest.mock


def load_module(module_path: pathlib.Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CorporaQualityCheckScriptTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        root = pathlib.Path(__file__).resolve().parents[2]
        cls.module = load_module(
            root / "scripts" / "utils" / "corpora_quality_check.py",
            "corpora_quality_check_script",
        )

    def test_run_special_characters_check_forwards_context(self):
        completed = unittest.mock.Mock()
        completed.returncode = 0
        completed.stdout = "U+00A9\t©\tCOPYRIGHT SIGN\t1\t2\tctx"
        completed.stderr = ""

        with unittest.mock.patch.object(
            self.module.subprocess, "run", return_value=completed
        ) as mock_run:
            output = self.module.run_special_characters_check(
                displayed_text="pi√©ce",
                extract_script="scripts/utils/extract_special_chars.py",
                allow_smart=True,
                excluded_codepoints=["00A0"],
                excluded_chars=["é"],
                context=10,
                nocontext=False,
                name_width=0,
                header=False,
            )

        self.assertIn("COPYRIGHT SIGN", output)
        cmd = mock_run.call_args.args[0]
        self.assertIn("--context=10", cmd)
        self.assertNotIn("--nocontext", cmd)

    def test_run_special_characters_check_uses_nocontext_flag(self):
        completed = unittest.mock.Mock()
        completed.returncode = 0
        completed.stdout = ""
        completed.stderr = ""

        with unittest.mock.patch.object(
            self.module.subprocess, "run", return_value=completed
        ) as mock_run:
            self.module.run_special_characters_check(
                displayed_text="pi√©ce",
                extract_script="scripts/utils/extract_special_chars.py",
                allow_smart=True,
                excluded_codepoints=[],
                excluded_chars=[],
                context=10,
                nocontext=True,
                name_width=12,
                header=True,
            )

        cmd = mock_run.call_args.args[0]
        self.assertIn("--nocontext", cmd)
        self.assertNotIn("--context=10", cmd)
        self.assertIn("--name-width=12", cmd)
        self.assertIn("--header", cmd)

    def test_parser_defaults_include_context(self):
        parser = self.module.build_parser()
        args = parser.parse_args([])
        self.assertEqual(10, args.context)
        self.assertFalse(args.nocontext)


if __name__ == "__main__":
    unittest.main()
