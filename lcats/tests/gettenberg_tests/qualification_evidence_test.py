"""Behavior checks for offline release-qualification experiment evidence."""

import dataclasses
import gzip
import importlib.util
import json
import pathlib
import signal
import sys
import tarfile
import tempfile
import types
import unittest
from unittest import mock

from lcats.gettenberg import lifecycle
from lcats.gettenberg import rdf
from tests.gettenberg_tests import catalog_test

SCRIPTS = (
    pathlib.Path(__file__).resolve().parents[3]
    / "experiments/10_gettenberg_qualification/scripts"
)


def load(name):
    """Load a durable experiment without invoking its CLI or historical imports."""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class QualificationEvidenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = pathlib.Path(temporary.name)

    def test_corpus_triage_never_labels_changed_or_refused_text_equal(self):
        module = load("summarize_corpus")
        row = {
            "status": "compared",
            "body_equal": False,
            "old_body_characters": 100,
            "first_difference": {
                "offset": 100,
                "after": "x" * 60 + "\nEnd of Gutenberg",
            },
        }
        self.assertEqual(module.classify(row), "appended_end_notice")
        row["first_difference"]["offset"] = 0
        self.assertEqual(module.classify(row), "earlier_body_difference")
        self.assertEqual(
            module.classify({"status": "cleanup_refused"}), "cleanup_refused"
        )
        self.assertEqual(
            module.classify({"status": "missing_cached_text"}), "missing_cached_text"
        )
        self.assertEqual(
            module.classify(
                {
                    "status": "compared",
                    "body_equal": True,
                    "retained_corpus_matches": False,
                }
            ),
            "retained_corpus_only",
        )

    def test_snapshot_checks_every_field_and_source_not_only_id(self):
        module = load("qualify_snapshot")
        raw = catalog_test.record(84, "Fixture")
        record = rdf.parse_record(raw, source_name="84.rdf")
        reader = types.SimpleNamespace(get=lambda _id: record)
        self.assertEqual(module.check_record(raw, "84.rdf", reader), record)
        changed = dataclasses.replace(
            record, ebook=dataclasses.replace(record.ebook, downloads=7)
        )
        with self.assertRaisesRegex(ValueError, "typed record mismatch"):
            module.check_record(
                raw, "84.rdf", types.SimpleNamespace(get=lambda _id: changed)
            )
        changed = dataclasses.replace(
            record, source=dataclasses.replace(record.source, source_name="other.rdf")
        )
        with self.assertRaisesRegex(ValueError, "source/diagnostic mismatch"):
            module.check_record(
                raw, "84.rdf", types.SimpleNamespace(get=lambda _id: changed)
            )

    def test_cached_text_is_bounded_utf8_and_missing_stays_missing(self):
        module = load("qualify_cached_corpus")
        self.assertIsNone(module.cached_text(self.root, 84))
        target = self.root / "84.txt.gz"
        target.write_bytes(gzip.compress("A café\r\n".encode()))
        text, compressed, decoded = module.cached_text(self.root, 84)
        self.assertEqual(text, "A café\r\n")
        self.assertEqual(compressed, module.digest(target.read_bytes()))
        self.assertEqual(decoded, module.digest(text))
        target.write_bytes(gzip.compress(b"x" * 1000))
        with mock.patch.object(module, "MAX_BYTES", 100):
            with self.assertRaisesRegex(ValueError, "expanded text exceeds"):
                module.cached_text(self.root, 84)
        target.write_bytes(gzip.compress(b"\xff"))
        with self.assertRaises(UnicodeDecodeError):
            module.cached_text(self.root, 84)

    def test_missing_or_empty_collection_records_failure_not_completion(self):
        module = load("qualify_cached_corpus")
        archive = self.root / "fixture.tar.bz2"
        archive.write_bytes(
            catalog_test.archive_bytes(
                [("84.rdf", catalog_test.record(84), tarfile.REGTYPE)]
            )
        )
        cache = self.root / "cache"
        lifecycle.CatalogManager(cache).setup(archive)
        empty = self.root / "empty"
        empty.mkdir()
        flat = self.root / "flat"
        flat.mkdir()
        (flat / "story.json").write_text("{}")
        # Historical gutenbergpy is deliberately absent from production/CI.
        # Stub that external import only; discovery, catalog and failure-report
        # writing remain real, and no cleaner should run for an invalid input.
        legacy = types.ModuleType("gutenbergpy")
        legacy.textget = types.SimpleNamespace(
            __file__=__file__,
            strip_headers=lambda _data: self.fail("unexpected cleaner call"),
        )
        self.addCleanup(signal.signal, signal.SIGALRM, signal.getsignal(signal.SIGALRM))
        with mock.patch.dict(sys.modules, {"gutenbergpy": legacy}):
            for collection in (self.root / "missing", empty, flat):
                with self.subTest(collection=collection.name):
                    output = self.root / f"{collection.name}-result.json"
                    with self.assertRaisesRegex(ValueError, "collection"):
                        module.main(
                            [str(cache), str(self.root), str(collection), str(output)]
                        )
                    report = json.loads(output.read_text())
                    self.assertFalse(report["completed"])
                    self.assertEqual(report["rows"], [])
                    self.assertIn("collection", report["error"])
                    self.assertNotIn("body_differences", report)

    def test_distinct_baseline_extractor_cannot_be_silently_replaced_by_current(self):
        module = load("qualify_cached_corpus")
        narrative = "\n\n".join(f"Narrative paragraph {i}." for i in range(15))
        metadata = types.SimpleNamespace(
            titles=("Story",),
            authors=("Smith, John",),
            aliases=(),
            languages=("en",),
            subjects=("PS", "Short stories"),
        )
        text = "Story\n\nJohn Smith\n\n" + narrative
        path = self.root / "story.json"
        path.write_text(
            json.dumps(
                {
                    "body": narrative,
                    "metadata": {"url": "https://www.gutenberg.org/ebooks/84"},
                }
            )
        )
        (self.root / "84.txt.gz").write_bytes(gzip.compress(text.encode()))
        source = types.SimpleNamespace(metadata=lambda _id: metadata)
        # A deliberately distinct deterministic baseline demonstrates that the
        # comparison routes each side separately, rather than silently running
        # the repaired extractor on both sides and reporting false equivalence.
        baseline = types.SimpleNamespace(body_of_text=lambda *_args: "Old fragment.")
        row = module.compare(
            path, self.root, source, lambda data: data, baseline_parser=baseline
        )
        self.assertEqual(row["legacy_extracted_sha256"], module.digest("Old fragment."))
        self.assertEqual(row["new_extracted_sha256"], module.digest(narrative))
        self.assertFalse(row["body_equal"])
        self.assertTrue(row["retained_corpus_matches"])

    def test_corpus_chapter_evidence_matches_inspection_and_keeps_metadata_rejection(
        self,
    ):
        from lcats.gatherers import parser
        from tests.gatherers_tests import live_gather_test

        module = load("qualify_cached_corpus")
        fixture = live_gather_test.LiveGatherTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        source = fixture.source()
        metadata = source.metadata(live_gather_test.BOOK_ID)
        # An unknown preface prevents destructive heading removal. Repeated book
        # titles remain in the body, but are not evidence of unnamed chapters.
        body = "Preface retained.\n\n" + "\n\n".join(
            ("THE BELL\n\n" if i % 4 == 0 else "") + paragraph
            for i, paragraph in enumerate(live_gather_test.PARAGRAPHS)
        )
        path = self.root / "story.json"
        path.write_text(
            json.dumps(
                {
                    "body": body,
                    "metadata": {
                        "url": f"https://www.gutenberg.org/ebooks/{live_gather_test.BOOK_ID}"
                    },
                }
            )
        )
        (self.root / f"{live_gather_test.BOOK_ID}.txt.gz").write_bytes(
            gzip.compress(body.encode())
        )
        # HistoricalText is the runner's explicit decoded-cache boundary; using
        # it exercises real inspection without fabricating original-byte receipts.
        narrative = load("qualify_narrative_cases")
        historical_source = narrative.HistoricalSource(
            source,
            narrative.HistoricalText(
                live_gather_test.BOOK_ID,
                narrative.cleanup.strip_boilerplate(body),
                module.digest(
                    (self.root / f"{live_gather_test.BOOK_ID}.txt.gz").read_bytes()
                ),
                module.digest(body),
            ),
        )
        report = parser.inspect_story(
            live_gather_test.BOOK_ID, source=historical_source
        )
        row = module.compare(path, self.root, source, lambda data: data)
        self.assertIsNone(report["rejection"])
        self.assertIsNone(row["publication_rejection"])
        self.assertEqual(
            row["chapter_assessment"], report["provenance"]["chapter_assessment"]
        )
        self.assertFalse(row["chapter_assessment"]["chaptered"])
        self.assertTrue(row["chapter_assessment"]["ignored_metadata_paragraphs"])

        ineligible = dataclasses.replace(metadata, languages=("fr",))
        row = module.compare(
            path,
            self.root,
            types.SimpleNamespace(metadata=lambda _id: ineligible),
            lambda data: data,
        )
        self.assertIsNone(row["new_rejection"])
        self.assertEqual(row["publication_rejection"], row["metadata_rejection"])
        self.assertIsNotNone(row["publication_rejection"])

    def test_narrative_case_publication_checks_source_identity_and_full_span(self):
        from tests.gatherers_tests import live_gather_test

        module = load("qualify_narrative_cases")
        fixture = live_gather_test.LiveGatherTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        source = fixture.source()
        raw = live_gather_test.ENVELOPE.encode()
        (self.root / f"{live_gather_test.BOOK_ID}.txt.gz").write_bytes(
            gzip.compress(raw)
        )
        case = {
            "id": live_gather_test.BOOK_ID,
            "decoded_utf8_sha256": module.corpus.digest(raw),
            "opening_anchor": live_gather_test.PARAGRAPHS[0],
            "closing_anchor": live_gather_test.PARAGRAPHS[-1],
        }
        row = module.check_case(case, self.root, source, self.root / "publication")
        self.assertTrue(row["complete_span_preserved"])
        self.assertTrue(row["publication_preserves_normalized_span"])
        self.assertTrue(row["existing_output_unchanged"])
        self.assertEqual(
            row["provenance"]["input_kind"], "historical_decoded_utf8_cache"
        )
        with self.assertRaisesRegex(ValueError, "source identity"):
            module.check_case(
                {**case, "decoded_utf8_sha256": "0" * 64},
                self.root,
                source,
                self.root / "bad",
            )
        with self.assertRaisesRegex(ValueError, "anchor"):
            module.check_case(
                {**case, "opening_anchor": "missing"},
                self.root,
                source,
                self.root / "bad",
            )

    def test_narrative_case_rejection_is_failed_publication_not_success(self):
        from tests.gatherers_tests import live_gather_test

        module = load("qualify_narrative_cases")
        fixture = live_gather_test.LiveGatherTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.source()
        raw = ("The Bell\n\nJohn Smith\n\nA short narrative.").encode()
        (self.root / f"{live_gather_test.BOOK_ID}.txt.gz").write_bytes(
            gzip.compress(raw)
        )
        cases = self.root / "cases.json"
        cases.write_text(
            json.dumps(
                {
                    "cases": [
                        {
                            "id": live_gather_test.BOOK_ID,
                            "decoded_utf8_sha256": module.corpus.digest(raw),
                            "opening_anchor": "A short",
                            "closing_anchor": "narrative.",
                        }
                    ]
                }
            )
        )
        output = self.root / "cases-result.json"
        self.addCleanup(signal.signal, signal.SIGALRM, signal.getsignal(signal.SIGALRM))
        status = module.main(
            [str(fixture.cache), str(self.root), str(cases), str(output)]
        )
        result = json.loads(output.read_text())
        self.assertEqual(status, 1)
        self.assertTrue(result["completed"])
        self.assertFalse(result["all_publication_checks_passed"])
        self.assertIn("too short", result["cases"][0]["rejection"])
        self.assertTrue(result["cases"][0]["complete_span_preserved"])
        self.assertFalse(result["cases"][0]["publication_preserves_normalized_span"])

    def test_missing_cache_and_cleanup_refusal_are_not_comparison_passes(self):
        module = load("qualify_cached_corpus")
        path = self.root / "story.json"
        path.write_text(
            json.dumps({"metadata": {"url": "https://www.gutenberg.org/ebooks/84"}})
        )
        # Missing bytes return before metadata access; never try another source.
        missing = module.compare(path, self.root, None, None)
        self.assertEqual(missing["status"], "missing_cached_text")
        metadata = types.SimpleNamespace(
            titles=("Story",),
            authors=("Author",),
            aliases=(),
            languages=("en",),
            subjects=("Short stories",),
        )
        source = types.SimpleNamespace(metadata=lambda _id: metadata)
        (self.root / "84.txt.gz").write_bytes(
            gzip.compress(b"*** START OF THE PROJECT GUTENBERG EBOOK STORY ***\nBody")
        )
        with mock.patch.object(module, "extract", return_value="Body"):
            refused = module.compare(path, self.root, source, lambda data: data)
        self.assertEqual(refused["status"], "cleanup_refused")
        self.assertIsNone(refused["body_equal"])
        self.assertIn("incomplete_pair", refused["cleanup_diagnostics"])


if __name__ == "__main__":
    unittest.main()
