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

    def test_main_delegates_to_library_main(self):
        with unittest.mock.patch.object(
            self.module.corpus_survey, "main", return_value=7
        ) as mock_main:
            result = self.module.main()
        self.assertEqual(7, result)
        mock_main.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
