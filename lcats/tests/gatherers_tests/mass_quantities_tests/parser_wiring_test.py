import ast
import pathlib
import unittest

ROOT = (
    pathlib.Path(__file__).resolve().parents[2]
    / "lcats"
    / "gatherers"
    / "mass_quantities"
)


class ParserWiringTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "parser.py").read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_dependencies_imported(self):
        imports = "\n".join(
            (
                ast.unparse(node)
                for node in self.tree.body
                if isinstance(node, (ast.Import, ast.ImportFrom))
            )
        )
        for name in (
            "structural_screen",
            "boundary_features",
            "frontmatter_precision",
            "extraction_records",
            "registry",
            "story_output",
        ):
            with self.subTest(module=name):
                self.assertIn(name, imports)

    def test_raw_screen_before_cleaning(self):
        part = self.source.split("def _inspect_metadata(", 1)[1].split(
            "def inspect_story(", 1
        )[0]
        self.assertLess(
            part.index("inspect_structure("), part.index("clean_gutenberg_story(")
        )
        self.assertIn("return_diagnostics=True", part)
        self.assertIn('report["confidence"] = diagnostics["boundary_confidence"]', part)

    def test_reuse_skips_override_and_source_read(self):
        part = self.source.split("def gather_story_result(", 1)[1]
        self.assertLess(
            part.index("story_output.existing(existing)"),
            part.index("report = _inspect_metadata("),
        )
        self.assertLess(
            part.index("story_output.existing(existing)"),
            part.index("extraction_records.load_override("),
        )

    def test_override_after_normalization_before_publication(self):
        part = self.source.split("def gather_story_result(", 1)[1]
        for earlier, later in [
            (
                "normalization.normalize_story_dict(",
                "extraction_records.apply_override(",
            ),
            ("extraction_records.apply_override(", "story_output.publish("),
            ("story_output.publish(", "extraction_records.save_extraction_record("),
        ]:
            with self.subTest(earlier=earlier):
                self.assertLess(part.index(earlier), part.index(later))

    def test_record_tracks_confidence_and_override(self):
        part = self.source.split("def gather_story_result(", 1)[1]
        self.assertIn('confidence=report["confidence"]', part)
        self.assertIn("overridden=override is not None", part)

    def test_registry_only_after_success(self):
        part = self.source.split("def gather_story_result(", 1)[1]
        self.assertLess(
            part.index("story_output.publish("),
            part.index("registry.add_story(", part.index("story_output.publish(")),
        )


if __name__ == "__main__":
    unittest.main()
