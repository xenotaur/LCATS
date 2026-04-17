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


if __name__ == "__main__":
    unittest.main()
