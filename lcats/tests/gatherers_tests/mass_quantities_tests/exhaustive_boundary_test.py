"""Slow historical boundary invariants, opt in with LCATS_EXHAUSTIVE=1."""

import json
import os
import unittest
import pathlib
from lcats.gatherers.mass_quantities import evaluate
from lcats.gatherers.mass_quantities import study_frontmatter

ROOT = pathlib.Path(__file__).resolve().parents[2]


@unittest.skipUnless(
    os.environ.get("LCATS_EXHAUSTIVE") == "1",
    "Set LCATS_EXHAUSTIVE=1 for slow boundary scan",
)
class ExhaustiveBoundaryTest(unittest.TestCase):

    def test_training_and_testing_boundary_invariants(self):
        rows = json.loads((ROOT / "ground_truth.json").read_text(encoding="utf-8"))
        for row in rows:
            with self.subTest(id=row["gutenberg_id"]):
                base = evaluate.estimate(row, guarded=False)
                guarded = evaluate.estimate(row, guarded=True)
                self.assertLessEqual(guarded, base)
                a, _ = study_frontmatter.predict(row, apply_precision=True)
                b, _ = study_frontmatter.predict(row, apply_precision=False)
                ref = evaluate.reference_line(row)
                if ref is not None:
                    self.assertLessEqual(a, max(b, ref))


if __name__ == "__main__":
    unittest.main()
