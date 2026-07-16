"""Unit tests for lcats.analysis.corpus.specials."""

import pathlib
import unittest

from lcats.analysis.corpus import review
from lcats.analysis.corpus import specials

CORPUS_ALLOWLIST = (
    pathlib.Path(specials.__file__).parent / "allowlists" / "corpus_specials.json"
)


class CorpusAllowlistTest(unittest.TestCase):
    """Tests for the seeded corpus special-character allowlist (WI-RESIDUAL-0019)."""

    def setUp(self):
        self.config = specials.load_allowlist_config(str(CORPUS_ALLOWLIST))

    def test_allows_legitimate_accented_letters_and_symbols(self):
        for char in ["é", "ñ", "æ", "ō", "ç", "£", "°", "¢", "½", "\xa0"]:
            with self.subTest(char=char):
                self.assertTrue(self.config.is_allowed(char))

    def test_does_not_allow_defect_or_boundary_artifacts(self):
        # The corrupted degree sign (override) and boundary artifacts stay
        # flagged rather than being allowlisted.
        for char in ["째", "\ufeff", "■"]:
            with self.subTest(char=char):
                self.assertFalse(self.config.is_allowed(char))


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
        # Real Latin-1 mojibake: a marker (Ã) followed by a UTF-8 continuation
        # char (U+0080-U+00BF). "resumÃ©"/"seÃ±or"/"coÃ¶rdinate" are sampled forms.
        cases = [
            ("resumÃ©", "Ã"),
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
        # "Ã©" is a marker + continuation char, so mojibake wins over the
        # lexical-diacritic rule even though Ã is itself a Latin letter.
        classification, evidence = specials.classify_character("Ã©", 0, "Ã")

        self.assertEqual("likely_repairable", classification)
        self.assertIn("mojibake-pattern", evidence)
        self.assertNotIn("lexical-latin-diacritic", evidence)

    def test_classify_character_lexical_a_circumflex_is_not_mojibake(self):
        # Regression (WI-RESIDUAL-0019): a-circumflex followed by an ASCII
        # letter is a legitimate diacritic (French "pâle", the name "Atlaanât"),
        # not mojibake -- the old broad "â." pattern flagged these as repairable.
        for text, index in [("pâle", 1), ("Atlaanât", 7)]:
            with self.subTest(text=text):
                classification, evidence = specials.classify_character(text, index, "â")
                self.assertEqual("likely_good", classification)
                self.assertIn("lexical-latin-diacritic", evidence)

    def test_classify_character_marker_plus_continuation_is_mojibake(self):
        # The trailing continuation char of a corrupted sequence classifies as
        # mojibake via its preceding marker.
        classification, evidence = specials.classify_character("Â°", 1, "°")

        self.assertEqual("likely_repairable", classification)
        self.assertIn("mojibake-pattern", evidence)

    def test_classify_character_review_needed_for_uncommon_symbol(self):
        classification, evidence = specials.classify_character(
            "Contains √ symbol", 9, "√"
        )

        self.assertEqual("review_needed", classification)
        self.assertIn("residual-review", evidence)

    def test_classify_character_likely_repairable_for_macroman_sequences(self):
        """Measured Mac-Roman mojibake pairs (√ + specific second char) must
        classify repairable, while bare mathematical √ stays review_needed
        (previous test)."""
        cases = [
            ("blas√© eyes", "√©"),
            ("fin de si√®cle", "√®"),
            ("se√±orita", "√±"),
            ("Tha√ºle?", "√º"),
            ("Ragnar√∂k.", "√∂"),
            ("Niccol√≤ Tartaglia", "√≤"),
            ("hypnop√¶dic language", "√¶"),
        ]
        for text, sequence in cases:
            with self.subTest(sequence=sequence):
                index = text.index("√")
                classification, evidence = specials.classify_character(text, index, "√")
                self.assertEqual("likely_repairable", classification)
                self.assertIn(f"fragment={sequence}", evidence)

    def test_build_special_character_report_applies_review_allow_rules(self):
        decision_store = review.ReviewDecisionStore(
            allowed_special_cases=(
                review.AllowedSpecialCase(
                    character="√",
                    classification="review_needed",
                    evidence_contains="residual-review",
                ),
            )
        )

        report = specials.build_special_character_report(
            text="A √ and ©",
            allow_smart=False,
            excluded=set(),
            allowlist=specials.AllowlistConfig(),
            context=4,
            name_width=0,
            header=False,
            decision_store=decision_store,
        )

        self.assertIn("©", report)
        self.assertNotIn("√", report)


if __name__ == "__main__":
    unittest.main()
