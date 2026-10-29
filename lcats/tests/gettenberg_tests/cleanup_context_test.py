"""Offline evidence boundaries for explicitly corroborated terminal notices."""

import dataclasses
import json
import socket
import unittest
from unittest import mock

from lcats.gettenberg import cleanup
from lcats.gettenberg import resources
from tests.gatherers_tests import live_gather_test


class CleanupContextTests(unittest.TestCase):
    """Require exact context, preserve ambiguous text and physical coordinates."""

    def setUp(self):
        self.context = cleanup.CleanupContext(50103, 50103, ("A Story",))
        self.notice = "End of the Project Gutenberg EBook of A Story, by An Author"

    def envelope(self, *, marker="50103", body=None, newline="\n"):
        """Author an independent source envelope without a fixture network call."""
        if body is None:
            body = "Narrative.\n\n" + self.notice + "\n\n"
        return (
            f"*** START OF THE PROJECT GUTENBERG EBOOK {marker} ***\n"
            + body
            + f"*** END OF THE PROJECT GUTENBERG EBOOK {marker} ***\n"
        ).replace("\n", newline)

    def test_title_notice_forms_need_no_numeric_context(self):
        for notice in (self.notice, "End of Project Gutenberg's A Story, by An Author"):
            raw = self.envelope(marker="A Story", body="Narrative.\n" + notice + "\n")
            result = cleanup.strip_boilerplate(raw)
            self.assertEqual(result.text, "Narrative.\n")
            self.assertEqual(
                [d.code for d in result.diagnostics],
                ["end_notice_removed", "envelope_removed"],
            )
            self.assertIsNone(result.context)

    def test_numeric_context_preserves_exact_offsets_and_newlines(self):
        for newline in ("\n", "\r\n", "\r"):
            for notice in (
                self.notice,
                "End of Project Gutenberg's A Story, by An Author",
            ):
                with self.subTest(newline=newline, notice=notice):
                    raw = self.envelope(
                        body="Narrative.\n\n" + notice + "\n\n", newline=newline
                    )
                    result = cleanup.strip_boilerplate(raw, context=self.context)
                    self.assertEqual(result.text, "Narrative." + newline * 2)
                    self.assertIs(result.original, raw)
                    self.assertEqual(result.content_end, raw.index(notice))
                    self.assertEqual(result.markers[1].line, 4)
                    self.assertEqual(
                        raw[result.markers[1].start : result.markers[1].end],
                        notice + newline,
                    )
                    self.assertEqual(
                        [d.code for d in result.diagnostics],
                        ["envelope_removed", "numeric_notice_removed"],
                    )
                    self.assertEqual(result.policy_version, "gutenberg-boundaries-v3")
                    self.assertIs(result.context, self.context)
                    self.assertEqual(
                        raw[: result.content_start]
                        + result.text
                        + raw[result.content_end :],
                        raw,
                    )
                    json.dumps(dataclasses.asdict(result))

    def test_missing_or_disagreeing_evidence_preserves_numeric_notice(self):
        contexts = (
            None,
            cleanup.CleanupContext(1, 50103, ("A Story",)),
            cleanup.CleanupContext(50103, 1, ("A Story",)),
            cleanup.CleanupContext(50103, 50103, ()),
            cleanup.CleanupContext(50103, 50103, ("Another Story",)),
            cleanup.CleanupContext(50103, 50103, ("A—Story",)),
            cleanup.CleanupContext(50103, 50103, ("A Story!",)),
        )
        for context in contexts:
            with self.subTest(context=context):
                result = cleanup.strip_boilerplate(self.envelope(), context=context)
                self.assertIn(self.notice, result.text)
                self.assertEqual(
                    [d.code for d in result.diagnostics], ["envelope_removed"]
                )
                self.assertEqual(result.context, context)
        self.assertIn(
            self.notice,
            cleanup.strip_boilerplate(
                self.envelope(marker="050103"), context=self.context
            ).text,
        )

    def test_exact_existing_case_horizontal_space_semantics(self):
        result = cleanup.strip_boilerplate(
            self.envelope(), context=cleanup.CleanupContext(50103, 50103, ("a\tSTORY",))
        )
        self.assertNotIn(self.notice, result.text)

    def test_context_is_frozen_and_invalid_shapes_reject_before_scanning(self):
        with self.assertRaises(dataclasses.FrozenInstanceError):
            self.context.source_id = 1
        for context in (
            {},
            "50103",
            cleanup.CleanupContext(True, 50103, ("A Story",)),
            cleanup.CleanupContext("50103", 50103, ("A Story",)),
            cleanup.CleanupContext(50103, None, ("A Story",)),
            cleanup.CleanupContext(0, 50103, ("A Story",)),
            cleanup.CleanupContext(50103, -1, ("A Story",)),
            cleanup.CleanupContext(50103, 50103, ["A Story"]),
            cleanup.CleanupContext(50103, 50103, (None,)),
        ):
            with (
                self.subTest(context=context),
                self.assertRaises(cleanup.CleanupInputError) as error,
            ):
                cleanup.strip_boilerplate("", context=context)
            self.assertEqual(error.exception.code, "invalid_context")

    def test_nonterminal_quoted_wrapped_or_empty_notices_are_preserved(self):
        for notice in (
            self.notice + "\nMore narrative.",
            '"' + self.notice + '"',
            self.notice.replace(", by", ",\nby"),
            self.notice.replace("An Author", "  "),
            "A narrator says: " + self.notice,
        ):
            with self.subTest(notice=notice):
                body = "Narrative.\n" + notice + "\n"
                result = cleanup.strip_boilerplate(
                    self.envelope(body=body), context=self.context
                )
                self.assertEqual(result.text, body)

    def test_numeric_rule_cannot_rescue_refused_or_empty_envelopes(self):
        good = self.envelope()
        for raw in (
            good + good,
            good + "Unverified footer.\n",
            "Unverified header.\n" + good,
            good.replace("*** START", "*** BEGIN"),
            self.notice,
        ):
            with self.subTest(raw=raw):
                result = cleanup.strip_boilerplate(raw, context=self.context)
                self.assertEqual(result.text, raw)
                self.assertNotIn(
                    "numeric_notice_removed", [d.code for d in result.diagnostics]
                )
        # The numeric extension leaves the already accepted envelope intact if
        # removing its note would leave no story; it never emits an empty body.
        result = cleanup.strip_boilerplate(
            self.envelope(body=self.notice + "\n"), context=self.context
        )
        self.assertEqual(result.text, self.notice + "\n")

    def test_terminal_notice_does_not_remove_internal_matching_prose(self):
        body = "Narrative.\n" + self.notice + "\nMore narrative.\n" + self.notice + "\n"
        result = cleanup.strip_boilerplate(
            self.envelope(body=body), context=self.context
        )
        self.assertEqual(
            result.text, "Narrative.\n" + self.notice + "\nMore narrative.\n"
        )


class SourceCleanupContextTests(unittest.TestCase):
    """Exercise the real catalog, cached resource, decoding and source adapter."""

    def setUp(self):
        # Reuse authored catalog/transport fixture construction, not its test methods.
        self.fixture = live_gather_test.LiveGatherTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def raw(self, marker=None):
        marker = live_gather_test.BOOK_ID if marker is None else marker
        return (
            f"*** START OF THE PROJECT GUTENBERG EBOOK {marker} ***\r\n"
            + live_gather_test.CONTENT.replace("\n", "\r\n")
            + "\r\nEnd of the Project Gutenberg EBook of The Bell, by John Smith\r\n"
            + f"*** END OF THE PROJECT GUTENBERG EBOOK {marker} ***\r\n"
        ).encode()

    def test_selected_source_and_catalog_context_are_recorded_without_network(self):
        raw = self.raw()
        source, artifact = self.fixture.acquire(raw)
        source.policy = resources.NetworkPolicy()
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network")):
            result = source.read(source.metadata(live_gather_test.BOOK_ID))
        self.assertNotIn("End of the Project Gutenberg", result.cleaned.text)
        self.assertEqual(artifact.path.read_bytes(), raw)
        self.assertEqual(result.cleaned.original.encode(), raw)
        provenance = result.provenance()
        self.assertEqual(provenance["cleanup_policy"], "gutenberg-boundaries-v3")
        self.assertEqual(
            provenance["cleanup_context"],
            {
                "source_id": live_gather_test.BOOK_ID,
                "catalog_id": live_gather_test.BOOK_ID,
                "titles": ["The Bell"],
            },
        )
        self.assertEqual(provenance["original_sha256"], artifact.sha256)
        json.dumps(provenance)

    def test_catalog_identity_or_title_disagreement_keeps_notice(self):
        source, artifact = self.fixture.acquire(self.raw())
        source.policy = resources.NetworkPolicy()
        metadata = source.metadata(live_gather_test.BOOK_ID)
        variants = (
            dataclasses.replace(
                metadata,
                ebook=dataclasses.replace(
                    metadata.ebook, gutenberg_id=live_gather_test.BOOK_ID + 1
                ),
            ),
            dataclasses.replace(metadata, titles=("Different Title",)),
        )
        for item in variants:
            with self.subTest(metadata=item):
                result = source.read(item)
                self.assertIn("End of the Project Gutenberg", result.cleaned.text)
                self.assertEqual(
                    result.cleaned.context.source_id, live_gather_test.BOOK_ID
                )
                self.assertEqual(
                    result.cleaned.context.catalog_id, item.ebook.gutenberg_id
                )
                self.assertEqual(
                    result.provenance()["original_sha256"], artifact.sha256
                )


if __name__ == "__main__":
    unittest.main()
