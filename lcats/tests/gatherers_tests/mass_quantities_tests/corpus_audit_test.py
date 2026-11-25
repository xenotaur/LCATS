"""Optional offline corpus check. Set LCATS_CORPUS_ZIP to stories ZIP to enable."""

import json
import os
import re
import unittest
import zipfile
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _tokens(s):
    return re.findall("[^\\W_]+", s.casefold())


@unittest.skipUnless(
    os.environ.get("LCATS_CORPUS_ZIP"), "Set LCATS_CORPUS_ZIP to run the corpus audit"
)
class CorpusAuditTest(unittest.TestCase):

    def test_extracted_stories_match_corrected_openings(self):
        rows = json.loads((ROOT / "ground_truth.json").read_text(encoding="utf-8"))
        indexed = {r["gutenberg_id"]: r for r in rows}
        filename = os.environ["LCATS_CORPUS_ZIP"]
        checked = 0
        failures = []
        with zipfile.ZipFile(filename) as z:
            for name in z.namelist():
                if not name.endswith("/story.json"):
                    continue
                try:
                    story = json.loads(z.read(name).decode("utf-8"))
                except (UnicodeError, ValueError) as exc:
                    failures.append((name, "invalid story.json", str(exc)))
                    continue
                prefix = name.rsplit("/", 1)[0]
                rec = prefix + "/extraction.json"
                if rec not in z.namelist():
                    continue
                meta = json.loads(z.read(rec))
                sid = meta.get("gutenberg_id")
                if sid not in indexed:
                    continue
                target = _tokens(indexed[sid]["first_narrative_text"])[:15]
                actual = _tokens(story.get("body", ""))[: len(target)]
                if target and actual != target:
                    failures.append((sid, target, actual))
                checked += 1
        self.assertGreater(
            checked,
            0,
            "No matching extraction.json records; audit cannot identify story IDs",
        )
        self.assertFalse(failures, f"First mismatches: {failures[:12]}")


if __name__ == "__main__":
    unittest.main()
