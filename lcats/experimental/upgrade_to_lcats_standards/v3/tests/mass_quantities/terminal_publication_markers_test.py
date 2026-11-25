"""Behavioral tests for removal of terminal publishing markers and author credits."""

import unittest

from lcats.gatherers.mass_quantities import parser


OPENING = "A complicated machine woke in the morning while the operators waited nearby."
ENDING = "At last the lights faded and every operator went quietly home."


def _extract(*tail, authors=None, remove_the_end=True):
    """Build a deterministic Gutenberg-like source and return narrative text."""
    authors = authors if authors is not None else ["Example, Jane"]
    lines = [
        "Title: The Machine",
        "Author: Jane Example",
        "*** START OF THE PROJECT GUTENBERG EBOOK THE MACHINE ***",
        "", "The Machine", "By Jane Example", "", OPENING, "", ENDING, "",
        *tail, "", "*** END OF THE PROJECT GUTENBERG EBOOK THE MACHINE ***",
    ]
    return parser.clean_gutenberg_story(
        "\n".join(lines), title="The Machine", authors=authors,
        remove_the_end=remove_the_end,
    )


class TerminalPublicationMarkersTest(unittest.TestCase):
    """Ensure final publishing conventions, not actual fiction, are removed."""

    def test_the_end_removed_by_default(self):
        self.assertEqual(_extract("THE END").strip().splitlines()[-1], ENDING)

    def test_the_end_with_period_removed(self):
        self.assertNotIn("THE END", _extract("THE END."))

    def test_end_and_finis_variants_removed(self):
        for marker in ("END", "The End", "FINIS.", "FIN.", "FIN", "----THE END----"):
            with self.subTest(marker=marker):
                self.assertEqual(_extract(marker).strip().splitlines()[-1], ENDING)

    def test_explicit_opt_out_preserves_end_marker(self):
        self.assertIn("THE END", _extract("THE END", remove_the_end=False))

    def test_catalog_reordered_author_removed(self):
        result = _extract("--JANE EXAMPLE")
        self.assertEqual(result.strip().splitlines()[-1], ENDING)

    def test_bare_catalog_author_removed(self):
        result = _extract("JANE EXAMPLE")
        self.assertEqual(result.strip().splitlines()[-1], ENDING)

    def test_author_suffix_added_in_print(self):
        result = _extract("--BASCOM JONES, JR.", authors=["Jones, Bascom"])
        self.assertEqual(result.strip().splitlines()[-1], ENDING)

    def test_author_middle_initial_omitted_in_print(self):
        result = _extract("--JAMES McCONNELL", authors=["McConnell, James V."])
        self.assertEqual(result.strip().splitlines()[-1], ENDING)

    def test_author_compound_surname_spacing(self):
        result = _extract("--MIRIAM ALLEN DeFORD", authors=["De Ford, Miriam Allen"])
        self.assertEqual(result.strip().splitlines()[-1], ENDING)

    def test_author_without_blank_separator(self):
        result = _extract("--JANE EXAMPLE")
        self.assertEqual(result.strip().splitlines()[-1], ENDING)

    def test_joint_author_credit_removed(self):
        result = _extract("--MARK CLIFTON & ALEX APOSTOLIDES", authors=[
            "Clifton, Mark", "Apostolides, Alex",
        ])
        self.assertEqual(result.strip().splitlines()[-1], ENDING)

    def test_author_after_end_marker_removed(self):
        result = _extract("THE END", "", "--JANE EXAMPLE")
        self.assertEqual(result.strip().splitlines()[-1], ENDING)

    def test_end_after_author_removed(self):
        result = _extract("--JANE EXAMPLE", "", "THE END")
        self.assertEqual(result.strip().splitlines()[-1], ENDING)

    def test_italicized_or_decorated_credit_removed(self):
        result = _extract("--=JANE EXAMPLE=")
        self.assertEqual(result.strip().splitlines()[-1], ENDING)

    def test_unrelated_fictional_signature_preserved(self):
        result = _extract("--MICHELANGELO")
        self.assertIn("--MICHELANGELO", result)

    def test_interior_the_end_not_removed(self):
        result = _extract("THE END", "", "The journey was not yet finished.")
        self.assertIn("THE END", result)
        self.assertIn("The journey was not yet finished.", result)

    def test_end_inside_prose_not_removed(self):
        result = _extract("He typed THE END but kept writing.")
        self.assertIn("THE END", result)

    def test_character_letter_signature_preserved(self):
        result = _extract("The diary concluded with a declaration.", "", "--CAPTAIN LEE")
        self.assertIn("--CAPTAIN LEE", result)

    def test_terminal_note_end_marker_and_author(self):
        result = _extract("THE END", "", "--JANE EXAMPLE", "",
                          "_Transcribers note_: This text was prepared from a magazine.")
        self.assertEqual(result.strip().splitlines()[-1], ENDING)

    def test_one_line_end_does_not_remove_entire_body(self):
        self.assertIn(OPENING, _extract("THE END"))

    def test_multiword_author_not_matching_metadata_retained(self):
        result = _extract("--OTHER AUTHOR")
        self.assertIn("--OTHER AUTHOR", result)

    def test_narrative_end_after_metadata_author_stays(self):
        result = _extract("--JANE EXAMPLE", "", "The radio came alive again.")
        self.assertIn("--JANE EXAMPLE", result)
        self.assertIn("The radio came alive again.", result)

