"""Offline source-contract checks for LCATS gather_batch and publisher integration."""
import ast
import unittest
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2] / 'lcats' / 'gatherers' / 'mass_quantities'

class GathererWiringTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / 'gatherer.py').read_text(encoding='utf-8')
        cls.tree = ast.parse(cls.text)

    def test_explicit_source_required(self):
        s = self.text.split('def gather_batch(', 1)[1].split('def main(', 1)[0]
        self.assertIn('if source is None:', s)
        self.assertIn('raise ValueError(', s)

    def test_run_log_path_validated(self):
        self.assertIn('_log_directory(log_dir)', self.text)
        self.assertIn('env.data_root()', self.text)
        self.assertIn('env.corpora_root()', self.text)

    def test_batch_result_tracks_reused_and_incomplete(self):
        cls = next((n for n in self.tree.body if isinstance(n, ast.ClassDef) and n.name == 'BatchResult'))
        props = {n.name for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertTrue({'written', 'incomplete', 'summary'}.issubset(props))

    def test_writes_in_parser_not_direct_download(self):
        s = (ROOT / 'parser.py').read_text(encoding='utf-8')
        self.assertIn('registry.check_story(', s)
        self.assertIn('story_output.existing(', s)
        self.assertIn('story_output.publish(', s)
if __name__ == '__main__':
    unittest.main()
