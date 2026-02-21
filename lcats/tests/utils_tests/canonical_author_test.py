import unittest

from parameterized import parameterized

from lcats.utils import canonical_author


class TestParseName(unittest.TestCase):
    """Tests for the parse_name function in the canonical_author module."""

    def test_parse_name_raises_on_empty_input(self):
        """Test that parse_name raises a ValueError on empty string or with only whitespace."""
        for raw in ["", "   "]:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    canonical_author.parse_name(raw)

    def test_parse_name_supports_space_and_comma_formats(self):
        """Test both "First Middle Last" and "Last, First Middle" formats correctly."""
        cases = [
            (
                "Ada Augusta Lovelace",
                canonical_author.ParsedName(
                    first="Ada", middles=["Augusta"], last="Lovelace", suffix=None
                ),
            ),
            (
                "Lovelace, Ada Augusta",
                canonical_author.ParsedName(
                    first="Ada", middles=["Augusta"], last="Lovelace", suffix=None
                ),
            ),
        ]

        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(canonical_author.parse_name(raw), expected)

    def test_parse_name_strips_honorific_suffix_and_diacritics(self):
        """Test honorifics / suffixes stripped, and diacritics are removed when ascii_only=True."""
        parsed = canonical_author.parse_name("Dr. José de la Cruz, Jr.")

        self.assertEqual(parsed.first, "Jose")
        self.assertEqual(parsed.middles, [])
        self.assertEqual(parsed.last, "De La Cruz")
        self.assertEqual(parsed.suffix, "Jr")

    def test_parse_name_keeps_diacritics_when_ascii_only_false(self):
        """Test that diacritics are preserved when ascii_only=False."""
        parsed = canonical_author.parse_name("José Núñez", ascii_only=False)

        self.assertEqual(parsed.first, "José")
        self.assertEqual(parsed.last, "Núñez")

    def test_parse_name_applies_nickname_map_to_first_name(self):
        """Test that the nickname map is applied to the first name."""
        parsed = canonical_author.parse_name(
            "Bill Nye", nickname_map={"bill": "William"}
        )

        self.assertEqual(parsed.first, "William")
        self.assertEqual(parsed.last, "Nye")


class TestCanonicalKey(unittest.TestCase):
    """Tests for the canonical_key function in the canonical_author module."""

    def test_canonical_key_defaults_to_last_first_lower(self):
        """Test that the default behavior of canonical_key is to return last_first in lowercase."""
        self.assertEqual(
            canonical_author.canonical_key("Ada Augusta Lovelace"), "lovelace_ada"
        )

    def test_canonical_key_includes_middles_and_suffix_and_case(self):
        """Test that canonical_key can include middles / suffix, and apply case transformations."""
        self.assertEqual(
            canonical_author.canonical_key(
                "Dr. Jose de la Cruz Jr.",
                include_middles=True,
                include_suffix=True,
                case="upper",
            ),
            "DE_LA_CRUZ_JOSE_JR",
        )

        self.assertEqual(
            canonical_author.canonical_key(
                "Lovelace, Ada Augusta", include_middles=True, case="title"
            ),
            "Lovelace_Ada_Augusta",
        )

    def test_canonical_key_rejects_invalid_case(self):
        """Test that canonical_key raises a ValueError for an invalid case."""
        with self.assertRaises(ValueError):
            canonical_author.canonical_key("Ada Lovelace", case="camel")


class TestCanonicalNameHelpers(unittest.TestCase):
    """Tests for helper functions that operate on canonical keys, like last_name / first_name."""

    def test_last_name_handles_two_and_three_part_keys(self):
        """Test that last_name correctly extracts the last name from keys with two / three parts."""
        self.assertEqual(canonical_author.last_name("lovelace_ada"), "lovelace")
        self.assertEqual(
            canonical_author.last_name("van_der_waals"),
            "van_der",
        )

    def test_first_name_handles_one_two_and_three_part_keys(self):
        """Test correctly extracts the first name from keys with one / two / three parts."""
        self.assertEqual(canonical_author.first_name(""), "")
        self.assertEqual(canonical_author.first_name("lovelace_ada"), "ada")
        self.assertEqual(canonical_author.first_name("van_der_waals"), "waals")


class TestAddAuthors(unittest.TestCase):
    """Tests for the add_authors function in the canonical_author module."""

    def test_add_authors_builds_expected_filename(self):
        """Test add_authors constructs expected filename given base name and list of authors."""
        out = canonical_author.add_authors(
            "paper.json", ["Ada Lovelace", "Grace Hopper"]
        )

        self.assertEqual(out, "paper__lovelace_ada-hopper_grace.json")

    def test_add_authors_truncates_to_max_len(self):
        """Test that add_authors truncates the resulting filename to max_len if provided."""
        out = canonical_author.add_authors(
            "paper.json", ["Ada Lovelace", "Grace Hopper"], max_len=20
        )

        self.assertEqual(len(out), 20)
        self.assertEqual(out, "paper__lovelace_ada-")


class TestParseNameEdgeCases(unittest.TestCase):
    """Tests for parse_name branches not covered by the base test class."""

    @parameterized.expand(
        [
            # Single-token name: no last name (covers line 152 + empty-string tpart, line 186)
            ("single_token", "Madonna", "Madonna", [], ""),
            # All tokens before the last are particles: core is empty → first="" (line 163 + 186)
            ("all_particle_prefix", "van Smith", "", [], "Van Smith"),
            # Comma form, all first tokens stripped as honorific → first="" (line 174)
            ("comma_form_no_first", "Smith, Dr.", "", [], "Smith"),
        ]
    )
    def test_parse_name_first_middles_last(
        self, _name, raw, expected_first, expected_middles, expected_last
    ):
        """Parameterized: exercise edge cases for first/middles/last assignment."""
        parsed = canonical_author.parse_name(raw)
        self.assertEqual(parsed.first, expected_first)
        self.assertEqual(parsed.middles, expected_middles)
        self.assertEqual(parsed.last, expected_last)

    def test_parse_name_comma_form_multi_token_last(self):
        """Comma form with a multi-word last name is joined correctly (line 172)."""
        parsed = canonical_author.parse_name("Van der Waals, Johannes")
        self.assertEqual(parsed.first, "Johannes")
        self.assertEqual(parsed.last, "Van Der Waals")
        self.assertEqual(parsed.middles, [])

    @parameterized.expand(
        [
            # Apostrophe in last name triggers the "'" branch in tpart (line 189)
            ("apostrophe_last", "Sean O'Neill", "Sean", "O_Neill"),
            # Hyphen in first name triggers the "-" branch in tpart (line 191)
            ("hyphen_first", "Mary-Jane Watson", "Mary_Jane", "Watson"),
        ]
    )
    def test_parse_name_special_char_in_name(self, _name, raw, expected_first, expected_last):
        """Parameterized: names with apostrophes or hyphens are title-cased correctly."""
        parsed = canonical_author.parse_name(raw)
        self.assertEqual(parsed.first, expected_first)
        self.assertEqual(parsed.last, expected_last)


class TestPrivateHelpers(unittest.TestCase):
    """Direct unit tests for private helper functions."""

    @parameterized.expand(
        [
            ("accented_e", "café", "cafe"),
            ("spanish_tilde", "Núñez", "Nunez"),
            ("plain_ascii", "hello", "hello"),
        ]
    )
    def test_strip_diacritics(self, _name, text, expected):
        """_strip_diacritics removes combining characters from a unicode string."""
        self.assertEqual(canonical_author._strip_diacritics(text), expected)

    @parameterized.expand(
        [
            ("removes_dots", "Dr.", "Dr"),
            ("removes_trailing_punct", "hello!!", "hello"),
            ("keeps_hyphen", "mary-jane", "mary-jane"),
            ("keeps_apostrophe", "o'brien", "o'brien"),
            ("normalizes_curly_quote", "o\u2019brien", "o'brien"),
        ]
    )
    def test_clean_token(self, _name, token, expected):
        """_clean_token strips dots, curly quotes, and non-word punctuation."""
        self.assertEqual(canonical_author._clean_token(token), expected)

    @parameterized.expand(
        [
            ("multi_space", "hello   world", "hello world"),
            ("leading_trailing", "  hello  ", "hello"),
            ("tab_and_newline", "a\t b\n c", "a b c"),
        ]
    )
    def test_normalize_space(self, _name, text, expected):
        """_normalize_space collapses runs of whitespace to a single space."""
        self.assertEqual(canonical_author._normalize_space(text), expected)


if __name__ == "__main__":
    unittest.main()
