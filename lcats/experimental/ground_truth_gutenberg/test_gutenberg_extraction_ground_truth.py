import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from contextlib import contextmanager
import sys
import types
from zipfile import ZipFile

from build_gutenberg_extraction_ground_truth import (
    corpus_records,
    generate_ground_truth,
    opening_text,
    open_cached_gutenberg_source,
    main,
)


class OpeningTest(unittest.TestCase):
    def test_blank_lines_are_physical_lines(self):
        text = "Heading\n\nBy A\n\n" + "Story continues here with many extra words and characters that create a paragraph.\n" * 25
        result, count = opening_text(text)
        self.assertEqual(count, 20)
        self.assertEqual(result.splitlines()[1], "")
        self.assertTrue(result.startswith("Heading\n\nBy A\n\n"))

    def test_extension_when_only_front_matter(self):
        text = "HEADING\n" * 25 + "A real paragraph with many many words and enough characters to identify this as plausible story prose.\n"
        result, count = opening_text(text)
        self.assertEqual(count, 26)
        self.assertIn("A real paragraph", result)

    def test_dataset_keeps_exact_duplicate_initially(self):
        with TemporaryDirectory() as root:
            archive = Path(root) / "new.zip"
            with ZipFile(archive, "w") as zipped:
                zipped.writestr("data/item/story.json", json.dumps({
                    "name": "Test", "author": ["Example, A"],
                    "metadata": {"gettenberg": {"gutenberg_id": 42}},
                }))
            source = Mock()
            source.metadata.return_value.titles = ["Test"]
            source.metadata.return_value.authors = ["Example, A"]
            source.read.return_value.cleaned.text = "TEST\n\nBy A\n\n\"Hello!\"\n"
            output = Path(root) / "ground_truth.json"
            result = generate_ground_truth(source=source, archive=archive, output=output)
            self.assertEqual(result["records_written"], 1)
            entry = json.loads(output.read_text(encoding="utf-8"))[0]
            self.assertEqual(entry["first_narrative_text"], entry["original_opening"])
            self.assertEqual(entry["first_narrative_text"], "TEST\n\nBy A\n\n\"Hello!\"\n")
            self.assertEqual(entry["review_status"], "pending")
            source.metadata.assert_called_once_with(42)
            source.read.assert_called_once_with(source.metadata.return_value)
            with self.assertRaises(FileExistsError):
                generate_ground_truth(source=source, archive=archive, output=output)

    def test_missing_cache_recorded(self):
        with TemporaryDirectory() as root:
            archive = Path(root) / "new.zip"
            with ZipFile(archive, "w") as zipped:
                zipped.writestr("data/item/story.json", json.dumps({
                    "metadata": {"gettenberg": {"gutenberg_id": 42}},
                }))
            source = Mock()
            source.metadata.side_effect = FileNotFoundError("offline cache miss")
            output = Path(root) / "ground_truth.json"
            result = generate_ground_truth(source=source, archive=archive, output=output)
            self.assertEqual(result["records_written"], 0)
            self.assertEqual(result["failed_ids"], 1)
            errors = json.loads((Path(root) / "ground_truth_errors.json").read_text())
            self.assertEqual(errors[0]["gutenberg_id"], 42)


class SourceSetupTest(unittest.TestCase):
    def test_source_uses_lcats_offline_service_setup(self):
        # Create minimal fake LCATS modules; the real package is not needed
        # for this unit test, but the constructor call sequence is verified.
        lcats = types.ModuleType("lcats")
        lcats.__path__ = []
        gettenberg = types.ModuleType("lcats.gettenberg")
        gettenberg.__path__ = []
        gatherers = types.ModuleType("lcats.gatherers")
        gatherers.__path__ = []
        prep = types.ModuleType("lcats.gettenberg.preparation")
        resources = types.ModuleType("lcats.gettenberg.resources")
        sources_cli = types.ModuleType("lcats.gettenberg.sources_cli")
        gutenberg_source = types.ModuleType("lcats.gatherers.gutenberg_source")
        prep.CatalogPreparation = Mock()
        resources.NetworkPolicy = Mock()
        sources_cli.gutenberg_routes = Mock(
            return_value=Mock(
                main_root="https://www.gutenberg.org/",
                generated_root="https://www.gutenberg.org/ebooks/",
            )
        )
        sources_cli.catalog_request = Mock(return_value=None)
        gutenberg_source.GutenbergStorySource = Mock()
        service = prep.CatalogPreparation.return_value
        catalog = object()
        service.store = object()
        service.manager.open.return_value.__enter__ = Mock(return_value=catalog)
        service.manager.open.return_value.__exit__ = Mock(return_value=False)
        modules = {
            "lcats": lcats,
            "lcats.gettenberg": gettenberg,
            "lcats.gettenberg.preparation": prep,
            "lcats.gettenberg.resources": resources,
            "lcats.gettenberg.sources_cli": sources_cli,
            "lcats.gatherers": gatherers,
            "lcats.gatherers.gutenberg_source": gutenberg_source,
        }
        with patch.dict(sys.modules, modules):
            with open_cached_gutenberg_source() as source:
                self.assertIs(source, gutenberg_source.GutenbergStorySource.return_value)
                self.assertTrue(service.manager.open.return_value.__enter__.called)
            self.assertTrue(service.manager.open.return_value.__exit__.called)
        resources.NetworkPolicy.assert_called_once()
        self.assertFalse(resources.NetworkPolicy.call_args.kwargs["online"])
        self.assertTrue(prep.CatalogPreparation.call_args.kwargs["offline"])
        service.prepare.assert_called_once_with(approved=False)
        gutenberg_source.GutenbergStorySource.assert_called_once_with(
            catalog,
            service.store,
            routes=sources_cli.gutenberg_routes.return_value,
            policy=resources.NetworkPolicy.return_value,
        )

    def test_cli_runs_without_source_factory(self):
        @contextmanager
        def fake_source(**kwargs):
            yield Mock()

        with patch(
            "build_gutenberg_extraction_ground_truth.open_cached_gutenberg_source",
            side_effect=fake_source,
        ) as opening:
            with patch(
                "build_gutenberg_extraction_ground_truth.generate_ground_truth",
                return_value={"failed_ids": 0, "records_written": 1},
            ) as generate:
                result = main(["--archive", "fixture.zip", "--output", "out.json"])
        self.assertEqual(result, 0)
        opening.assert_called_once()
        self.assertEqual(str(generate.call_args.kwargs["archive"]), "fixture.zip")
        self.assertEqual(str(generate.call_args.kwargs["output"]), "out.json")


if __name__ == "__main__":
    unittest.main()
