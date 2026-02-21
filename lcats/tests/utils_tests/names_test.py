# tests/test_names.py
import re
import unittest
from lcats.utils import names


class TestAsciiTransliterate(unittest.TestCase):
    def test_ascii_passthrough(self):
        self.assertEqual(
            names.ascii_transliterate("simple ascii 123"), "simple ascii 123"
        )

    def test_diacritics_removed(self):
        # Works with or without unidecode
        out = names.ascii_transliterate("Curaçao café déjà vu")
        self.assertIn("curacao", out)
        self.assertIn("cafe", out)
        self.assertIn("deja vu", out)
        # ensure ASCII-only
        out.encode("ascii")  # should not raise

    def test_non_latin_handling(self):
        # With unidecode installed, may transliterate; without, gets dropped.
        out = names.ascii_transliterate("Файл №7 — 标题")
        out.encode("ascii")  # ASCII-only
        self.assertIn("7", out)  # at least digit survives


class TestIsValidBasename(unittest.TestCase):
    def test_valid_examples(self):
        for s in ["hello", "hello_world", "a1_b2", "a", "abc123", "a_b_c"]:
            with self.subTest(s=s):
                self.assertTrue(names.is_valid_basename(s))

    def test_invalid_examples(self):
        for s in ["Hello", "_hi", "hi_", "h__i", "", "hello-world", "sp ace", "ümlaut"]:
            with self.subTest(s=s):
                self.assertFalse(names.is_valid_basename(s))

    def test_length_limit(self):
        s_ok = "a" * names.BASENAME_MAXIMUM_LENGTH
        s_bad = "a" * (names.BASENAME_MAXIMUM_LENGTH + 1)
        self.assertTrue(names.is_valid_basename(s_ok))
        self.assertFalse(names.is_valid_basename(s_bad))

    def test_max_len_zero_returns_false(self):
        self.assertFalse(names.is_valid_basename("hello", max_len=0))

    def test_custom_pattern(self):
        letters_only = re.compile(r"^[a-z]+\Z")
        self.assertTrue(names.is_valid_basename("hello", pattern=letters_only))
        self.assertFalse(names.is_valid_basename("hello123", pattern=letters_only))


class TestRepairBasename(unittest.TestCase):
    def test_max_len_zero_raises(self):
        with self.assertRaises(ValueError):
            names.repair_basename("hello", max_len=0)

    def test_basic_repairs(self):
        self.assertEqual(names.repair_basename('Hello, "World"!'), "hello_world")
        self.assertEqual(names.repair_basename("__HI__"), "hi")
        self.assertEqual(names.repair_basename("a__b"), "a_b")
        self.assertEqual(names.repair_basename("  spaced   out  "), "spaced_out")

    def test_unicode_title(self):
        out = names.repair_basename("Curaçao — №7")
        # deterministic with unidecode pinned
        self.assertEqual(out, "curacao_no_7")

        # keep the policy checks too (nice guardrails)
        self.assertTrue(all(c.islower() or c.isdigit() or c == "_" for c in out))
        self.assertTrue(out.endswith("7"))

    def test_all_removed_yields_empty(self):
        self.assertEqual(names.repair_basename("---"), "")

    def test_truncation_and_cleanup(self):
        raw = "x" * 100
        out = names.repair_basename(raw, max_len=10)
        self.assertEqual(out, "xxxxxxxxxx")
        raw2 = "a" * 5 + "__" + "b" * 100
        out2 = names.repair_basename(raw2, max_len=10)
        self.assertTrue(len(out2) <= 10)
        # no leading/trailing underscores; no doubles
        self.assertFalse(out2.startswith("_") or out2.endswith("_"))
        self.assertNotIn("__", out2)


class TestTitleToFilename(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(names.title_to_filename('Hello, "World"!'), "hello_world.json")

    def test_truncation(self):
        t = "A" * 100
        self.assertEqual(names.title_to_filename(t, max_len=10), "aaaaaaaaaa.json")

    def test_invalid_extension(self):
        with self.assertRaises(ValueError):
            names.title_to_filename("ok", ext=".J*")
        with self.assertRaises(ValueError):
            # even without dot it becomes ".bad!" and fails
            names.title_to_filename("ok", ext="bad!")

    def test_allow_empty(self):
        self.assertEqual(names.title_to_filename("— — —", allow_empty=True), ".json")
        with self.assertRaises(ValueError):
            names.title_to_filename("— — —", allow_empty=False)

    def test_extension_normalization(self):
        self.assertEqual(names.title_to_filename("ok", ext="JSON"), "ok.json")
        self.assertEqual(names.title_to_filename("ok", ext=".Json"), "ok.json")


class TestNormalizeBasename(unittest.TestCase):
    def test_already_valid(self):
        out, changed = names.normalize_basename("good_name")
        self.assertEqual(out, "good_name")
        self.assertFalse(changed)

    def test_repaired(self):
        out, changed = names.normalize_basename("Bad Name!?")
        self.assertTrue(changed)
        self.assertTrue(names.is_valid_basename(out))
        self.assertEqual(out, "bad_name")

    def test_empty_after_repair(self):
        out, changed = names.normalize_basename("— — —")
        self.assertEqual(out, "")  # caller must decide how to handle
        self.assertTrue(changed)

    def test_custom_max_len(self):
        out, changed = names.normalize_basename("hello_world", max_len=5)
        self.assertEqual(out, "hello")
        self.assertTrue(changed)
        out2, changed2 = names.normalize_basename("hello", max_len=5)
        self.assertEqual(out2, "hello")
        self.assertFalse(changed2)


class TestTitleAndAuthorToFilename(unittest.TestCase):
    def test_single_author(self):
        result = names.title_and_author_to_filename(
            "Hello World", ["Ada Lovelace"]
        )
        self.assertEqual(result, "hello_world__lovelace.json")

    def test_multiple_authors(self):
        result = names.title_and_author_to_filename(
            "Hello World", ["Ada Lovelace", "Grace Hopper"]
        )
        self.assertEqual(result, "hello_world__lovelace_hopper.json")


if __name__ == "__main__":
    unittest.main()
