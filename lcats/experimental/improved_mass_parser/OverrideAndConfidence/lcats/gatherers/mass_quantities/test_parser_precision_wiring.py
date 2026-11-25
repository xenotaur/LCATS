"""Verify the LCATS parser imports and invokes the precision boundary helper."""
import ast
from pathlib import Path
import unittest

PARSER = Path(__file__).with_name('parser.py')

class ParserWiringTests(unittest.TestCase):
    def test_imported_from_package(self):
        tree = ast.parse(PARSER.read_text(encoding='utf-8'))
        imports = [node for node in ast.walk(tree)
                   if isinstance(node, ast.ImportFrom)
                   and node.module == 'lcats.gatherers.mass_quantities.frontmatter_precision']
        self.assertTrue(any(any(alias.name == 'refine_promotional_blurb_boundary'
                                 for alias in node.names) for node in imports))

    def test_called_in_clean_gutenberg_story(self):
        tree = ast.parse(PARSER.read_text(encoding='utf-8'))
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == 'clean_gutenberg_story')
        calls = [node for node in ast.walk(function)
                 if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name)
                 and node.func.id == 'refine_promotional_blurb_boundary']
        self.assertEqual(len(calls), 1)
        self.assertEqual([arg.id for arg in calls[0].args],
                         ['lines', 'lo', 'hi', 'title', 'authors', 'warnings'])

if __name__ == '__main__':
    unittest.main()
