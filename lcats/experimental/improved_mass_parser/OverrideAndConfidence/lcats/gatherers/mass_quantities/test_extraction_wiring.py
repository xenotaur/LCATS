import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).parent

class WiringTests(unittest.TestCase):
    def test_parser_imports_module(self):
        tree=ast.parse((ROOT/'parser.py').read_text())
        self.assertTrue(any(isinstance(n,ast.ImportFrom) and n.module=='lcats.gatherers.mass_quantities' and any(a.name=='extraction_records' for a in n.names) for n in tree.body))

    def test_override_after_normalization_before_publishing(self):
        text=(ROOT/'parser.py').read_text()
        start=text.index('def gather_story_result(')
        s=text[start:]
        self.assertTrue(s.index('story_output.existing(existing)') < s.index('extraction_records.load_override('))
        self.assertTrue(s.index('normalization.normalize_story_dict(') < s.index('extraction_records.apply_override('))
        self.assertTrue(s.index('extraction_records.apply_override(') < s.index('story_output.publish('))
        self.assertTrue(s.index('story_output.publish(') < s.index('extraction_records.save_extraction_record('))
        self.assertTrue(s.index('extraction_records.save_extraction_record(') < s.index('registry.add_story(',s.index('story_output.publish(')))

    def test_confidence_flows_from_parser_diagnostics_to_record(self):
        text=(ROOT/'parser.py').read_text()
        inspect=text[text.index('def _inspect_metadata('):text.index('def inspect_story(')]
        gather=text[text.index('def gather_story_result('):]
        self.assertIn('return_diagnostics=True',inspect)
        self.assertIn('report["confidence"] = diagnostics["boundary_confidence"]',inspect)
        self.assertIn('confidence=report["confidence"]',gather)
        self.assertLess(gather.index('confidence=report["confidence"]'),
                        gather.index('story_output.publish('))

    def test_raw_record_populated_on_inspection(self):
        s=(ROOT/'parser.py').read_text()
        self.assertIn('report["raw_opening"] = extraction_records.opening_lines(',s)

if __name__=='__main__': unittest.main()
