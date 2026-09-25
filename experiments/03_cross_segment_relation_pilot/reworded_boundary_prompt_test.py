from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lcats" / "src"))

import reworded_boundary_prompt as variant  # noqa: E402
from lcats.analysis import scene_analysis  # noqa: E402


class RewordedBoundaryPromptTest(unittest.TestCase):
    def test_reworded_prompt_matches_production_everywhere_except_the_targeted_block(
        self,
    ):
        original_lines = scene_analysis.SCENE_SEQUEL_SYSTEM_PROMPT.splitlines()
        reworded_lines = variant.REWORDED_SYSTEM_PROMPT.splitlines()

        original_block_lines = variant._ORIGINAL_LOCATION_SELECTOR_BLOCK.splitlines()
        reworded_block_lines = variant._REWORDED_LOCATION_SELECTOR_BLOCK.splitlines()

        start = None
        for i in range(len(original_lines) - len(original_block_lines) + 1):
            if (
                original_lines[i : i + len(original_block_lines)]
                == original_block_lines
            ):
                start = i
                break
        self.assertIsNotNone(
            start, "original location-selector block not found verbatim"
        )
        end = start + len(original_block_lines)

        self.assertEqual(original_lines[:start], reworded_lines[:start])
        self.assertEqual(
            reworded_lines[start : start + len(reworded_block_lines)],
            reworded_block_lines,
        )
        self.assertEqual(
            original_lines[end:],
            reworded_lines[start + len(reworded_block_lines) :],
        )

    def test_reworded_prompt_still_asks_for_every_original_field(self):
        for field in (
            "start_par_id",
            "end_par_id",
            "start_exact",
            "end_exact",
            "start_prefix",
            "end_suffix",
        ):
            self.assertIn(field, variant.REWORDED_SYSTEM_PROMPT)

    def test_reworded_prompt_specifies_the_cross_paragraph_rule(self):
        self.assertIn("LAST character of end_exact", variant.REWORDED_SYSTEM_PROMPT)
        self.assertIn("FIRST character of start_exact", variant.REWORDED_SYSTEM_PROMPT)

    def test_reworded_extractor_reuses_production_schema_and_template(self):
        from lcats.llm import fake_backend

        extractor = variant.make_reworded_segment_extractor(fake_backend.FakeBackend())
        self.assertEqual(
            extractor.user_prompt_template,
            scene_analysis.SCENE_SEQUEL_USER_PROMPT_TEMPLATE,
        )
        self.assertEqual(extractor.tool_schema, scene_analysis.SEGMENT_TOOL_SCHEMA)
        self.assertEqual(extractor.system_prompt, variant.REWORDED_SYSTEM_PROMPT)
        self.assertNotEqual(
            extractor.system_prompt, scene_analysis.SCENE_SEQUEL_SYSTEM_PROMPT
        )


if __name__ == "__main__":
    unittest.main()
