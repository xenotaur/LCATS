"""Offline selection contracts over lossless catalog resource metadata."""

import dataclasses
import unittest

from lcats.gettenberg import models
from lcats.gettenberg import resources


def ebook_with(*claims):
    """Build distinct resources, including absent or multiple format claims."""
    return models.Ebook(
        42,
        "urn:ebook:42",
        resources=tuple(
            models.Resource(
                f"https://example.org/{index}",
                formats=tuple(models.Term(models.Literal(claim)) for claim in formats),
            )
            for index, formats in enumerate(claims)
        ),
    )


class ResourceSelectionTest(unittest.TestCase):
    def test_defaults_rank_utf8_before_plain_before_html(self):
        ebook = ebook_with(
            ("text/html",), ("text/plain",), ("text/plain; charset=UTF-8",)
        )
        result = resources.select_resource(ebook)
        self.assertIs(result.resource, ebook.resources[2])
        self.assertEqual((result.source_index, result.preference_index), (2, 0))
        self.assertEqual(result.matched_format, "text/plain; charset=UTF-8")
        self.assertEqual(result.policy_version, "declared-media-v1")

    def test_plain_precedes_html_without_charset_guess(self):
        result = resources.select_resource(ebook_with(("text/html",), ("text/plain",)))
        self.assertEqual((result.source_index, result.preference_index), (1, 1))

    def test_html_fallback(self):
        result = resources.select_resource(
            ebook_with(("application/pdf",), ("text/html",))
        )
        self.assertEqual((result.source_index, result.preference_index), (1, 2))

    def test_equal_formats_preserve_source_order_and_identity(self):
        ebook = ebook_with(("text/plain",), ("text/plain",))
        before = dataclasses.asdict(ebook)
        result = resources.select_resource(ebook)
        self.assertIs(result.resource, ebook.resources[0])
        self.assertIn("source_order_tie", [d.code for d in result.diagnostics])
        self.assertEqual(before, dataclasses.asdict(ebook))
        self.assertEqual(result, resources.select_resource(ebook))

    def test_multiple_claims_find_best_without_discarding_metadata(self):
        ebook = ebook_with(("application/zip", "text/plain; charset=utf8"))
        result = resources.select_resource(ebook)
        self.assertEqual(result.preference_index, 0)
        self.assertIs(result.resource, ebook.resources[0])
        self.assertEqual(len(result.resource.formats), 2)

    def test_equal_claims_use_format_source_order(self):
        result = resources.select_resource(
            ebook_with(("text/plain; charset=utf8", "text/plain; charset=UTF-8"))
        )
        self.assertEqual(result.matched_format, "text/plain; charset=utf8")

    def test_case_quoted_parameters_and_codec_aliases(self):
        result = resources.select_resource(
            ebook_with(('Text/Plain; CHARSET="UTF_8"; note="a;b"',))
        )
        self.assertEqual(result.preference_index, 0)

    def test_custom_preference_order_overrides_defaults(self):
        ebook = ebook_with(("text/plain; charset=utf-8",), ("text/html",))
        result = resources.select_resource(
            ebook,
            preferences=(
                resources.ResourcePreference("TEXT/HTML"),
                resources.ResourcePreference("text/plain"),
            ),
        )
        self.assertIs(result.resource, ebook.resources[1])

    def test_unknown_charset_can_be_selected_explicitly(self):
        result = resources.select_resource(
            ebook_with(("text/plain; charset=X-FUTURE",)),
            preferences=(resources.ResourcePreference("text/plain", "x-future"),),
        )
        self.assertIsNotNone(result.resource)

    def test_conflicting_charset_does_not_win_utf8_preference(self):
        result = resources.select_resource(
            ebook_with(
                ("text/plain; charset=utf-8; charset=latin1",),
                ("text/plain; charset=utf8",),
            )
        )
        self.assertEqual(result.source_index, 1)
        self.assertIn("conflicting_charsets", [d.code for d in result.diagnostics])

    def test_conflicting_charset_remains_generic_plain_candidate(self):
        result = resources.select_resource(
            ebook_with(("text/plain; charset=utf8; charset=latin1",))
        )
        self.assertEqual(result.preference_index, 1)

    def test_repeated_equivalent_charset_is_not_conflict(self):
        result = resources.select_resource(
            ebook_with(("text/plain; charset=utf8; charset=UTF-8",))
        )
        self.assertEqual(result.preference_index, 0)
        self.assertNotIn("conflicting_charsets", [d.code for d in result.diagnostics])

    def test_no_match_for_absent_unsupported_or_empty_resources(self):
        for ebook in (ebook_with(), ebook_with(()), ebook_with(("application/pdf",))):
            with self.subTest(ebook=ebook):
                result = resources.select_resource(ebook)
                self.assertIsNone(result.resource)
                self.assertIsNone(result.source_index)
                self.assertIsNone(result.preference_index)
                self.assertIsNone(result.matched_format)
                self.assertEqual(result.diagnostics[-1].code, "no_match")

    def test_malformed_claims_never_default_to_plain_text(self):
        for claim in (
            "",
            "text",
            "text/plain;",
            "text/plain; charset",
            "text/plain\r\nX: y",
            'text/plain; charset="utf-8',
            "text/plain blah",
            'text/plain; charset="utf-8\x00"',
            'text/plain; charset="utf-8☃"',
            'text/plain; charset=""',
            "text/plain; charset*=utf-8''utf-8",
        ):
            with self.subTest(claim=claim):
                result = resources.select_resource(ebook_with((claim,)))
                self.assertIsNone(result.resource)
                diagnostic = result.diagnostics[0]
                self.assertEqual(
                    (
                        diagnostic.code,
                        diagnostic.resource_index,
                        diagnostic.format_index,
                    ),
                    ("invalid_format", 0, 0),
                )

    def test_no_extension_inference_and_all_formats_explicitly_retrievable(self):
        ebook = ebook_with(
            ("application/pdf",), ("audio/mpeg",), ("application/epub+zip",)
        )
        for index, media in enumerate(
            ("application/pdf", "audio/mpeg", "application/epub+zip")
        ):
            with self.subTest(media=media):
                result = resources.select_resource(
                    ebook, preferences=(resources.ResourcePreference(media),)
                )
                self.assertIs(result.resource, ebook.resources[index])
                request = resources.SourceRequest.from_url(result.resource.uri)
                self.assertEqual(request.request_url, ebook.resources[index].uri)
        renamed = dataclasses.replace(
            ebook, resources=(models.Resource("https://example.org/book-utf8.txt"),)
        )
        self.assertIsNone(resources.select_resource(renamed).resource)

    def test_invalid_preferences_raise_structured_input_error(self):
        for media, charset in (
            ("text/*", None),
            ("text/plain; charset=utf8", None),
            ("text", None),
            (None, None),
            ("text/plain", ""),
            ("text/plain", 42),
        ):
            with self.subTest(media=media, charset=charset):
                with self.assertRaises(resources.ResourceInputError):
                    resources.ResourcePreference(media, charset)
        for preferences in ((), [], ("text/plain",), None):
            with self.subTest(preferences=preferences):
                with self.assertRaises(resources.ResourceInputError):
                    resources.select_resource(ebook_with(), preferences=preferences)
        with self.assertRaises(resources.ResourceInputError):
            resources.select_resource(None)

    def test_charset_continuations_never_override_valid_resource(self):
        for parameter in (
            "charset*1=utf-8",
            "charset*0=utf-; charset*1=8",
            "charset*" + "9" * 5000 + "=utf-8",
        ):
            with self.subTest(parameter_length=len(parameter)):
                ebook = ebook_with(
                    ("text/plain; " + parameter,),
                    ("text/plain; charset=utf-8",),
                )
                result = resources.select_resource(ebook)
                self.assertIs(result.resource, ebook.resources[1])
                self.assertEqual(result.diagnostics[0].code, "invalid_format")

    def test_records_are_immutable(self):
        result = resources.select_resource(ebook_with(("text/plain",)))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.source_index = 99
        with self.assertRaises(dataclasses.FrozenInstanceError):
            resources.DEFAULT_PREFERENCES[0].charset = "latin1"


if __name__ == "__main__":
    unittest.main()
