import importlib.util
import pathlib
import unittest
import unittest.mock


class ExtractSpecialCharsScriptTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = pathlib.Path(__file__).resolve().parents[2]
        module_path = root / "scripts" / "utils" / "extract_special_chars.py"
        spec = importlib.util.spec_from_file_location(
            "extract_special_chars_script", module_path
        )
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_main_delegates_to_canonical_specials_cli(self):
        with unittest.mock.patch.object(
            self.module.specials_cli, "main", return_value=7
        ) as mock_main:
            result = self.module.main(["--header"])

        self.assertEqual(7, result)
        mock_main.assert_called_once_with(["--header"])


if __name__ == "__main__":
    unittest.main()
