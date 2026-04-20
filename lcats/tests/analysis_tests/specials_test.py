"""Unit tests for lcats.analysis.corpus.specials."""

import unittest

from lcats.analysis.corpus import specials


class SpecialsTest(unittest.TestCase):
    """Tests for in-process special-character extraction."""

    def test_iter_special_characters_returns_core_fields(self):
        text = "A √ and ©"
        results = list(
            specials.iter_special_characters(
                text=text,
                allow_smart=False,
                excluded=set(),
                allowlist=specials.AllowlistConfig(),
                context=4,
                name_width=0,
            )
        )

        self.assertEqual(2, len(results))
        first = results[0]
        self.assertEqual("√", first.character)
        self.assertEqual("U+221A", first.codepoint)
        self.assertEqual("SQUARE ROOT", first.unicode_name)
        self.assertEqual(1, first.occurrence_index)
        self.assertEqual(2, first.offset)
        self.assertEqual("A √ and", first.context)

    def test_iter_special_characters_handles_empty_and_ascii(self):
        empty = list(
            specials.iter_special_characters(
                text="",
                allow_smart=False,
                excluded=set(),
                allowlist=specials.AllowlistConfig(),
                context=4,
                name_width=0,
            )
        )
        ascii_only = list(
            specials.iter_special_characters(
                text="plain ascii",
                allow_smart=True,
                excluded=set(),
                allowlist=specials.AllowlistConfig(),
                context=4,
                name_width=0,
            )
        )

        self.assertEqual([], empty)
        self.assertEqual([], ascii_only)

    def test_build_special_character_report_with_header(self):
        report = specials.build_special_character_report(
            text="©",
            allow_smart=False,
            excluded=set(),
            allowlist=specials.AllowlistConfig(),
            context=0,
            name_width=0,
            header=True,
        )

        lines = report.splitlines()
        self.assertEqual("\t".join(specials.TSV_COLUMNS), lines[0])
        self.assertEqual("U+00A9", lines[1].split("\t")[0])
        self.assertEqual("", lines[1].split("\t")[5])

    def test_classify_character_likely_good_for_lexical_diacritic(self):
        classification, evidence = specials.classify_character("naïve", 2, "ï")

        self.assertEqual("likely_good", classification)
        self.assertIn("lexical-latin-diacritic", evidence)

    def test_classify_character_likely_repairable_for_mojibake_sequence(self):
        text = "Broken punctuation â€™ in corpus text."
        index = text.index("â")
        classification, evidence = specials.classify_character(text, index, "â")

        self.assertEqual("likely_repairable", classification)
        self.assertIn("mojibake-pattern", evidence)

    def test_classify_character_mojibake_sequences_out_rank_lexical_diacritics(self):
        cases = [
            ("ÃŸ", "Ã"),
            ("Ã©", "Ã"),
            ("seÃ±or", "Ã"),
            ("coÃ¶rdinate", "Ã"),
        ]
        for text, character in cases:
            with self.subTest(text=text):
                index = text.index(character)
                classification, evidence = specials.classify_character(
                    text, index, character
                )
                self.assertEqual("likely_repairable", classification)
                self.assertIn("mojibake-pattern", evidence)

    def test_classify_character_valid_lexical_diacritics_remain_likely_good(self):
        cases = [
            ("Muñoz", "ñ"),
            ("façade", "ç"),
            ("naïve", "ï"),
            ("Zoë", "ë"),
        ]
        for text, character in cases:
            with self.subTest(text=text):
                index = text.index(character)
                classification, evidence = specials.classify_character(
                    text, index, character
                )
                self.assertEqual("likely_good", classification)
                self.assertIn("lexical-latin-diacritic", evidence)

    def test_classify_character_prefers_mojibake_over_lexical_rule(self):
        classification, evidence = specials.classify_character("ÃŸ", 0, "Ã")

        self.assertEqual("likely_repairable", classification)
        self.assertIn("mojibake-pattern", evidence)
        self.assertNotIn("lexical-latin-diacritic", evidence)

    def test_classify_character_review_needed_for_uncommon_symbol(self):
        classification, evidence = specials.classify_character(
            "Contains √ symbol", 9, "√"
        )

        self.assertEqual("review_needed", classification)
        self.assertIn("residual-review", evidence)


if __name__ == "__main__":
    unittest.main()
