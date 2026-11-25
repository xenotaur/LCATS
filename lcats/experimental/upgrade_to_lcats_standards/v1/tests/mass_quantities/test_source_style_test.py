"""Prevent multiple statements on one physical line in test sources."""

import ast
import tokenize
import unittest
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestSourceStyleTest(unittest.TestCase):
    def test_one_statement_per_line(self):
        paths = set(ROOT.rglob("*_test.py"))
        paths.update(ROOT.rglob("test_*.py"))
        for path in sorted(paths):
            with self.subTest(file=str(path.relative_to(ROOT))):
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source)
                counts = {}
                for node in ast.walk(tree):
                    if isinstance(node, ast.stmt):
                        counts[node.lineno] = counts.get(node.lineno, 0) + 1
                duplicates = [line for line, count in counts.items() if count > 1]
                self.assertEqual(duplicates, [])
                with path.open("rb") as handle:
                    semicolons = [token.start[0] for token in tokenize.tokenize(handle.readline) if token.type == tokenize.OP and token.string == ";"]
                self.assertEqual(semicolons, [])


if __name__ == "__main__":
    unittest.main()
