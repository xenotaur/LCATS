"""Offline content-preservation contracts for independently authored envelopes."""

import dataclasses
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

from lcats.gettenberg import cleanup
from lcats.gettenberg import resources
from lcats.utils import capture


_START = "*** START OF THE PROJECT GUTENBERG EBOOK THE LANTERN ***"
_END = "*** END OF THE PROJECT GUTENBERG EBOOK THE LANTERN ***"


def envelope(body="A small light.\n", *, start=_START, end=_END):
    """Wrap authored content; do not encode the implementation's detection rules."""
    return start + "\n" + body + end


class CleanupTests(unittest.TestCase):
    def preserved(self, text, code):
        """Assert that refusal leaves the complete source and offsets intact."""
        result = cleanup.strip_boilerplate(text)
        self.assertIs(result.original, text)
        self.assertEqual(result.text, text)
        self.assertEqual((result.content_start, result.content_end), (0, len(text)))
        self.assertFalse(result.changed)
        self.assertIn(code, [diagnostic.code for diagnostic in result.diagnostics])
        return result

    def test_authored_modern_and_historical_fixtures(self):
        path = pathlib.Path(__file__).parent / "fixtures/cleanup/cases.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("independently authored", data["provenance"]["kind"])
        for case in data["cases"]:
            with self.subTest(case=case["name"]):
                result = cleanup.strip_boilerplate(case["input"])
                self.assertTrue(result.changed)
                self.assertEqual(result.text, case["expected"])
                self.assertIs(result.original, case["input"])

    def test_offsets_line_numbers_and_reconstruction_with_unicode_crlf(self):
        prefix = "\ufeffThe Project Gutenberg eBook of 🕯\r\n\r\n"
        opening = " \t*** START OF THE PROJECT GUTENBERG EBOOK 🕯 ***\r\n"
        body = "\r\nCafé e\u0301 🕯\r\n\r\n"
        closing = "*** END OF THE PROJECT GUTENBERG EBOOK 🕯 ***\r\n"
        suffix = "THE FULL PROJECT GUTENBERG™ LICENSE\r\n"
        original = prefix + opening + body + closing + suffix
        result = cleanup.strip_boilerplate(original)
        self.assertEqual(result.text, body)
        self.assertEqual(result.content_start, len(prefix + opening))
        self.assertEqual(result.content_end, len(prefix + opening + body))
        self.assertEqual(result.markers[0].line, 3)
        self.assertEqual(result.markers[1].line, 7)
        self.assertEqual(
            original[result.markers[0].start : result.markers[0].end], opening
        )
        self.assertEqual(
            original[result.markers[1].start : result.markers[1].end], closing
        )
        self.assertEqual(
            original[: result.content_start]
            + result.text
            + original[result.content_end :],
            original,
        )
        self.assertEqual(result.policy_version, "gutenberg-boundaries-v1")

    def test_lf_crlf_cr_and_missing_final_newline(self):
        for newline in ("\n", "\r\n", "\r"):
            for terminal in ("", newline):
                with self.subTest(newline=newline, terminal=terminal):
                    text = _START + newline + " x " + newline + _END + terminal
                    result = cleanup.strip_boilerplate(text)
                    self.assertEqual(result.text, " x " + newline)
                    self.assertEqual([marker.line for marker in result.markers], [1, 3])
                    self.assertEqual(result.markers[-1].end, len(text))

    def test_initial_bom_and_horizontal_indentation(self):
        text = "\ufeff\t" + _START + "\nBody\n\t" + _END + "  \n"
        result = cleanup.strip_boilerplate(text)
        self.assertEqual(result.text, "Body\n")
        self.assertEqual(result.markers[0].start, 0)

    def test_case_and_horizontal_spacing_compare_without_rewriting(self):
        start = "***start\tOF  THE PROJECT\tGUTENBERG EBOOK Straẞe  light***"
        end = "*** END OF THE PROJECT GUTENBERG EBOOK strasse\tLIGHT ***"
        result = cleanup.strip_boilerplate(
            envelope("  unchanged\t\n", start=start, end=end)
        )
        self.assertEqual(result.text, "  unchanged\t\n")
        self.assertEqual(result.markers[0].identifier, "Straẞe  light")
        self.assertEqual(result.markers[1].identifier, "strasse\tLIGHT")

    def test_absent_markers_and_ordinary_narrative_are_untouched(self):
        for text in (
            "",
            " ",
            "Once upon a time.\nTHE END\n",
            "End of Project Gutenberg's Example, by Someone\n",
            "Produced by a volunteer\n",
            'She said "' + _START + '".\n',
            "A quotation: " + _END,
            "> " + _START + "\n> " + _END,
        ):
            with self.subTest(text=text):
                self.preserved(text, "no_markers")

    def test_one_sided_boundaries_preserve_all_content(self):
        for text in (_START + "\nBody", "Body\n" + _END):
            with self.subTest(text=text):
                self.preserved(text, "incomplete_pair")

    def test_ordinary_narrative_around_standalone_pair_is_refused(self):
        self.preserved(
            "A narrator quoted this file:\n" + envelope(), "unverified_header"
        )
        self.preserved(envelope() + "\nThe narrator kept talking.", "unverified_footer")

    def test_repeated_nested_and_concatenated_envelopes_preserve_all(self):
        for text in (
            envelope() + "\n" + envelope(),
            envelope(_START + "\nMore\n"),
            envelope("Body\n" + _END + "\nMore\n"),
        ):
            with self.subTest(text=text):
                self.preserved(text, "multiple_markers")

    def test_reversed_mismatched_titles_and_styles_are_refused(self):
        self.preserved(envelope(start=_END, end=_START), "reversed_pair")
        self.preserved(
            envelope(end=_END.replace("LANTERN", "CLOCK")), "mismatched_pair"
        )
        self.preserved(
            envelope(end=_END.replace("OF THE", "OF THIS")), "mismatched_pair"
        )

    def test_malformed_or_unsupported_markers_block_otherwise_valid_pair(self):
        for marker in (
            _START[:-3],
            _START.replace("***", "**"),
            _START.replace("EBOOK", "ETEXT"),
            _START.replace("THE LANTERN", "   "),
            _START + " trailing prose",
            _START.replace("THE LANTERN", "a\x00b"),
            _START.replace("THE LANTERN", "a*b"),
        ):
            with self.subTest(marker=marker):
                text = envelope("Body\n" + marker + "\nMore\n")
                result = self.preserved(text, "unrecognized_marker")
                self.assertIn("unrecognized", [item.kind for item in result.markers])

    def test_unsupported_marker_whitespace_cannot_hide_extra_boundaries(self):
        # Candidate discovery must be broader than the accepted ASCII syntax,
        # including when the malformed line would otherwise be removed as boilerplate.
        for space in ("\u00a0", "\u2003", "\u2028", "\u2029", "\v", "\f"):
            variants = (
                _START.replace("PROJECT GUTENBERG", "PROJECT" + space + "GUTENBERG"),
                _START.replace(" ", space, 1),
                space + _START,
            )
            for marker in variants:
                documents = (
                    "The Project Gutenberg eBook of THE LANTERN\n"
                    + marker
                    + "\n"
                    + envelope(),
                    envelope("Body\n" + marker + "\nMore\n"),
                    envelope() + "\n" + marker + "\nTHE FULL PROJECT GUTENBERG LICENSE",
                )
                for text in documents:
                    with self.subTest(space=space, marker=marker, text=text):
                        self.preserved(text, "unrecognized_marker")

    def test_damaged_outer_markers_do_not_select_a_nested_example(self):
        for stars in ("*", "**"):
            text = (
                "The Project Gutenberg eBook of THE LANTERN\n"
                + _START.replace("***", stars)
                + "\nOuter narrative.\n"
                + envelope("Example only.\n")
                + "\nMore outer narrative.\n"
                + _END.replace("***", stars)
                + "\nTHE FULL PROJECT GUTENBERG LICENSE"
            )
            with self.subTest(stars=stars):
                self.preserved(text, "unrecognized_marker")

    def test_wrapped_or_incomplete_candidates_block_partial_book_selection(self):
        for separator in ("\n", "\r\n", "\r"):
            for phrase in ("PROJECT GUTENBERG", "THE PROJECT"):
                text = (
                    envelope("First story.\n")
                    + "\n"
                    + _START.replace(phrase, phrase.replace(" ", separator))
                    + "\nSecond story.\n"
                    + _END.replace(phrase, phrase.replace(" ", separator))
                    + "\nTHE FULL PROJECT GUTENBERG LICENSE"
                )
                with self.subTest(separator=separator, phrase=phrase):
                    self.preserved(text, "unrecognized_marker")
        # A starred START/END line needs no complete Gutenberg name to force a
        # conservative refusal. It is never enough to authorize removal itself.
        self.preserved(envelope("Body\n*** START EXAMPLE ***\n"), "unrecognized_marker")

    def test_historical_license_separator_is_not_a_book_boundary(self):
        separator = "*** START: FULL LICENSE ***"
        for newline in ("\n", "\r\n", "\r"):
            body = "A story." + newline
            text = (
                _START.replace("OF THE", "OF THIS")
                + newline
                + body
                + _END.replace("OF THE", "OF THIS")
                + newline
                + "\t"
                + separator
                + "  "
                + newline
                + "THE FULL PROJECT GUTENBERG LICENSE"
                + newline
            )
            with self.subTest(newline=newline):
                result = cleanup.strip_boilerplate(text)
                self.assertEqual(result.text, body)
                self.assertEqual(text[result.content_start : result.content_end], body)
                self.assertEqual([m.kind for m in result.markers], ["start", "end"])
        # The exemption cannot authorize a cut on its own or waive footer evidence.
        self.preserved(separator, "no_markers")
        self.preserved(envelope() + "\n" + separator, "unverified_footer")
        self.assertEqual(
            cleanup.strip_boilerplate(envelope(separator + "\n")).text, separator + "\n"
        )
        for damaged in (
            "*** START: FULL LICENSE EXTRA ***",
            "* START: FULL LICENSE *",
            "*** START: PROJECT GUTENBERG EBOOK THE LANTERN ***",
        ):
            self.preserved(envelope("Body\n" + damaged + "\n"), "unrecognized_marker")

    def test_empty_or_whitespace_content_never_disappears(self):
        for body in ("", " \t\n", "\u2003\n"):
            with self.subTest(body=body):
                self.preserved(envelope(body), "empty_content")

    def test_short_content_and_body_whitespace_are_preserved_exactly(self):
        for body in ("a\n", "\n  a \t\n\n", "\x00\n", "e\u0301\n"):
            with self.subTest(body=body):
                self.assertEqual(cleanup.strip_boilerplate(envelope(body)).text, body)

    def test_unicode_line_separators_do_not_create_marker_lines(self):
        for separator in ("\u2028", "\u2029", "\x85", "\v", "\f"):
            with self.subTest(separator=separator):
                text = "Narrative" + separator + _START + "\nBody\n" + _END
                self.preserved(text, "incomplete_pair")
                body = "A" + separator + "B\n"
                self.assertEqual(cleanup.strip_boilerplate(envelope(body)).text, body)

    def test_license_heading_must_be_in_removed_suffix(self):
        text = (
            "The Project Gutenberg eBook of The Lantern\nTHE FULL PROJECT GUTENBERG LICENSE\n"
            + envelope()
            + "\nUnverified tail"
        )
        self.preserved(text, "unverified_footer")
        self.preserved(
            envelope() + "\nIt mentions THE FULL PROJECT GUTENBERG LICENSE here.",
            "unverified_footer",
        )
        self.preserved(
            envelope() + "\n> THE FULL PROJECT GUTENBERG LICENSE", "unverified_footer"
        )

    def test_unknown_prefix_is_not_certified_by_a_later_banner(self):
        text = (
            "A reader's account:\nThe Project Gutenberg eBook of The Lantern\n"
            + envelope()
        )
        self.preserved(text, "unverified_header")

    def test_footer_variants_and_whitespace_only_envelopes(self):
        for heading in (
            "THE FULL PROJECT GUTENBERG LICENSE",
            "THE FULL PROJECT GUTENBERG™ LICENSE",
            "THE FULL PROJECT GUTENBERG-tm LICENSE",
        ):
            result = cleanup.strip_boilerplate(
                envelope() + "\n" + heading + "\nFixture footer"
            )
            self.assertTrue(result.changed)
        self.assertEqual(
            cleanup.strip_boilerplate("\n\t\n" + envelope() + "\n \t").text,
            "A small light.\n",
        )

    def test_unicode_whitespace_only_outer_regions_are_not_narrative(self):
        result = cleanup.strip_boilerplate("\u2003\n" + envelope() + "\n\u2003")
        self.assertEqual(result.text, "A small light.\n")

    def test_matching_end_notice_is_recorded_and_removed_with_corroboration(self):
        body = "Body\n\n"
        notice = "End of Project Gutenberg's The Lantern, by Fixture Author\n"
        text = envelope(body + notice + "\n\n")
        result = cleanup.strip_boilerplate(text)
        self.assertEqual(result.text, body)
        self.assertEqual(
            [marker.kind for marker in result.markers], ["start", "end_notice", "end"]
        )
        self.assertEqual(
            result.original[result.markers[1].start : result.markers[1].end], notice
        )
        self.assertEqual(result.markers[1].style, result.markers[2].style)
        self.assertIn("end_notice_removed", [item.code for item in result.diagnostics])

    def test_unmatched_quoted_or_nonadjacent_end_notice_remains_content(self):
        for note in (
            "End of Project Gutenberg's Other Book, by LCATS\n",
            "End of Project Gutenberg's The Lantern, by \n",
            '"End of Project Gutenberg\'s The Lantern, by LCATS"\n',
            "End of Project Gutenberg's The Lantern, by LCATS\nA final sentence.\n",
        ):
            with self.subTest(note=note):
                body = "Body\n" + note
                result = cleanup.strip_boilerplate(envelope(body))
                self.assertEqual(result.text, body)
                self.assertEqual(len(result.markers), 2)
        self.preserved(
            "Body\nEnd of Project Gutenberg's The Lantern, by LCATS", "no_markers"
        )

    def test_end_notice_cannot_make_content_empty(self):
        self.preserved(
            envelope("End of Project Gutenberg's The Lantern, by LCATS\n"),
            "empty_content",
        )

    def test_candidate_budget_preserves_input_and_reports_truncated_scan(self):
        text = (_START + "\n") * 1000 + "Body\n" + _END
        result = self.preserved(text, "candidate_limit")
        self.assertLess(len(result.markers), 1000)
        self.assertEqual(result.diagnostics[-1].line, len(result.markers) + 1)

    def test_invalid_input_and_character_budget(self):
        for text in (b"text", bytearray(b"text"), None, 3, True):
            with self.subTest(text=text):
                with self.assertRaises(cleanup.CleanupInputError) as error:
                    cleanup.strip_boilerplate(text)
                self.assertEqual(error.exception.code, "invalid_text")
        for bound in (None, True, False, 0, -1, 2.0, "2"):
            with self.subTest(bound=bound):
                with self.assertRaises(cleanup.CleanupInputError) as error:
                    cleanup.strip_boilerplate("x", max_characters=bound)
                self.assertEqual(error.exception.code, "invalid_limit")
        with self.assertRaises(cleanup.CleanupInputError) as error:
            cleanup.strip_boilerplate("🕯🕯", max_characters=1)
        self.assertEqual(error.exception.code, "input_too_large")
        self.assertEqual(cleanup.strip_boilerplate("🕯", max_characters=1).text, "🕯")

    def test_results_are_immutable_deterministic_and_json_serializable(self):
        text = envelope("🕯\n")
        first = cleanup.strip_boilerplate(text)
        self.assertEqual(first, cleanup.strip_boilerplate(text))
        exported = json.loads(json.dumps(dataclasses.asdict(first)))
        self.assertEqual(
            exported["original"][exported["content_start"] : exported["content_end"]],
            first.text,
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            first.content_start = 0
        with self.assertRaises(dataclasses.FrozenInstanceError):
            first.markers[0].start = 0
        self.assertFalse(cleanup.strip_boilerplate(first.text).changed)

    def test_decoding_is_an_explicit_separate_operation(self):
        raw = envelope("Café\n").encode("latin-1")
        with self.assertRaises(cleanup.CleanupInputError):
            cleanup.strip_boilerplate(raw)
        decoded = resources.decode_text(
            raw, options=resources.DecodeOptions(encoding_override="latin-1")
        )
        result = cleanup.strip_boilerplate(decoded.text)
        self.assertEqual(result.text, "Café\n")
        self.assertEqual(raw.decode("latin-1"), result.original)

    def test_existing_boundary_contamination_fixture_is_preserved_without_start(self):
        path = (
            pathlib.Path(__file__).parents[1]
            / "analysis_tests/fixtures/boundary_contamination/end_gutenberg.txt"
        )
        self.preserved(path.read_text(encoding="utf-8"), "incomplete_pair")

    def test_import_and_cleanup_need_no_gutenbergpy_files_or_network(self):
        code = """
import sys
class DenyLegacy:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "gutenbergpy" or fullname.startswith("gutenbergpy."):
            raise AssertionError("legacy dependency requested")
sys.meta_path.insert(0, DenyLegacy())
from lcats.gettenberg import cleanup
assert "gutenbergpy" not in sys.modules
# Audit after import: library calls may not open files or create sockets.
def audit(event, args):
    if event == "open" or event.startswith("socket."):
        raise AssertionError(event)
sys.addaudithook(audit)
assert cleanup.strip_boilerplate("a story").text == "a story"
"""
        with tempfile.TemporaryDirectory() as directory:
            environment = dict(
                os.environ, LCATS_CACHE_DIR=str(pathlib.Path(directory) / "cache")
            )
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=directory,
                env=environment,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(pathlib.Path(directory).iterdir()), [])

    def test_long_malformed_line_and_many_lines_finish_within_process_budget(self):
        # A bounded subprocess catches accidental catastrophic regex backtracking
        # without asserting a machine-specific microbenchmark or retaining data.
        code = """
from lcats.gettenberg import cleanup
text = "*** START OF THE PROJECT GUTENBERG EBOOK X" + " " * 200000 + "missing terminator"
assert not cleanup.strip_boilerplate(text).changed
# Spaces before the identifier must not overlap the separator's repetition.
text = "*** START OF THE PROJECT GUTENBERG EBOOK " + " " * 200000 + "X"
assert not cleanup.strip_boilerplate(text).changed
# The analogous historical-notice separator must also fail in bounded time.
notice = "End of Project Gutenberg's " + " " * 200000 + "X"
text = "*** START OF THE PROJECT GUTENBERG EBOOK X ***\\n" + notice + "\\n*** END OF THE PROJECT GUTENBERG EBOOK X ***"
assert cleanup.strip_boilerplate(text).text == notice + "\\n"
text = ("ordinary line\\n" * 100000)
assert cleanup.strip_boilerplate(text).text == text
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class CleanupDocumentationTests(unittest.TestCase):
    def test_all_how_to_blocks_execute_offline(self):
        path = (
            pathlib.Path(__file__).resolve().parents[2]
            / "docs/how-to/gettenberg-cleanup.md"
        )
        blocks = re.findall(
            r"```python\n(.*?)```", path.read_text(encoding="utf-8"), re.S
        )
        self.assertEqual(len(blocks), 4)
        namespace = {}
        with capture.capture_output():
            for block in blocks:
                exec(compile(block, str(path), "exec"), namespace)
        self.assertTrue(namespace["result"].changed)
        self.assertFalse(namespace["preserved"].changed)
        json.dumps(namespace["record"])
