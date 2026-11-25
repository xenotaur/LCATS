import json
import tempfile
import unittest
import pathlib
from lcats.gatherers.mass_quantities import extraction_records


class ExtractionRecordsTest(unittest.TestCase):

    def setUp(self):
        self.opening = '"Come back tomorrow," said Alice, stepping into the garden beside the wall.'
        self.body = (
            "An irrelevant magazine teaser.\n\n"
            + self.opening
            + "\n\nThe rest of the story.\n"
        )
        self.override = {
            "gutenberg_id": 42,
            "title": ["A Story"],
            "authors": ["Writer"],
            "first_narrative_text": self.opening,
            "original_opening": self.body,
            "override_datetime": "2026-11-24T00:00:00+00:00",
        }

    def test_valid_override_trims_only_prefix(self):
        output = extraction_records.apply_override(
            self.body, self.override, gutenberg_id=42, title="A Story"
        )
        self.assertEqual(output, self.opening + "\n\nThe rest of the story.\n")

    def test_override_never_splices_text_into_missing_narrative(self):
        with self.assertRaises(ValueError):
            extraction_records.apply_override(
                "Teaser only.\n", self.override, gutenberg_id=42, title="A Story"
            )

    def test_wrong_id_and_title_fail(self):
        with self.assertRaises(ValueError):
            extraction_records.apply_override(
                self.body, self.override, gutenberg_id=43, title="A Story"
            )
        with self.assertRaises(ValueError):
            extraction_records.apply_override(
                self.body, self.override, gutenberg_id=42, title="Other Title"
            )

    def test_short_anchor_refused(self):
        item = dict(self.override, first_narrative_text="SCENE")
        with self.assertRaises(ValueError):
            extraction_records.apply_override(
                self.body, item, gutenberg_id=42, title="A Story"
            )

    def test_duplicate_anchor_refused(self):
        with self.assertRaises(ValueError):
            extraction_records.apply_override(
                self.body + self.body, self.override, gutenberg_id=42, title="A Story"
            )

    def test_longer_review_disambiguates_repeated_opening(self):
        phrase = "The Wanderer sped onward through the silent darkness where no light could be found."
        body = (
            "Teaser.\n\n"
            + phrase
            + "\n\nOne ending.\n\n"
            + phrase
            + "\n\nA different continuation at the conclusion."
        )
        item = dict(self.override, first_narrative_text=phrase + "\n\nOne ending.")
        self.assertTrue(
            extraction_records.apply_override(
                body, item, gutenberg_id=42, title="A Story"
            ).startswith(phrase + "\n\nOne ending.")
        )

    def test_still_refuse_identical_long_repetitions(self):
        phrase = "The Wanderer sped onward through the silent darkness where no light could be found."
        body = (
            "Teaser.\n\n" + phrase + "\n\nOne ending.\n\n" + phrase + "\n\nOne ending."
        )
        item = dict(self.override, first_narrative_text=phrase + "\n\nOne ending.")
        with self.assertRaises(ValueError):
            extraction_records.apply_override(
                body, item, gutenberg_id=42, title="A Story"
            )

    def test_record_fields_and_lines(self):
        record = extraction_records.extraction_record(
            gutenberg_id=42,
            title="A Story",
            authors=["Writer"],
            raw_text="\n\nOne\nTwo\n",
            extracted_body=self.body,
            overridden=True,
            confidence="medium",
            raw_lines=3,
            extracted_lines=2,
            extracted_at="2026-11-24T14:00:00+00:00",
        )
        self.assertEqual(record["original_opening"], "\n\nOne\n")
        self.assertEqual(record["confidence"], "medium")
        self.assertTrue(record["override_applied"])
        self.assertEqual(record["extraction_datetime"], "2026-11-24T14:00:00+00:00")
        self.assertEqual(record["review_status"], "extracted")
        self.assertEqual(
            record["first_narrative_text"],
            extraction_records.opening_lines(self.body, 2),
        )

    def test_confidence_validation(self):
        args = dict(
            gutenberg_id=42,
            title="A Story",
            authors=["Writer"],
            raw_text="Title",
            extracted_body=self.body,
            overridden=False,
        )
        for confidence in ("high", "medium", "low"):
            with self.subTest(confidence=confidence):
                self.assertEqual(
                    extraction_records.extraction_record(**args, confidence=confidence)[
                        "confidence"
                    ],
                    confidence,
                )
        for confidence in ("HIGH", "unknown", "", None):
            with self.subTest(confidence=confidence):
                with self.assertRaises(ValueError):
                    extraction_records.extraction_record(**args, confidence=confidence)

    def test_save_requires_story_and_preserves_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp)
            original = json.dumps(self.override)
            (path / "override.json").write_text(original, encoding="utf-8")
            record = extraction_records.extraction_record(
                gutenberg_id=42,
                title="A Story",
                authors=["Writer"],
                raw_text=self.body,
                extracted_body=self.body,
                overridden=True,
                confidence="high",
            )
            with self.assertRaises(FileNotFoundError):
                extraction_records.save_extraction_record(path, record)
            (path / "story.json").write_text("{}", encoding="utf-8")
            result = extraction_records.save_extraction_record(path, record)
            self.assertEqual(json.loads(result.read_text(encoding="utf-8")), record)
            self.assertEqual(
                (path / "override.json").read_text(encoding="utf-8"), original
            )
            self.assertEqual(
                extraction_records.load_override(
                    path, gutenberg_id=42, title="A Story"
                ),
                self.override,
            )

    def test_bad_override_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp)
            (path / "override.json").mkdir()
            with self.assertRaises(ValueError):
                extraction_records.load_override(path, gutenberg_id=42, title="A Story")


if __name__ == "__main__":
    unittest.main()
