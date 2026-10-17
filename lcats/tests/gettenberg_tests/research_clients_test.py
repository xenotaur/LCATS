"""Execute maintained research clients against local fixtures, without network."""

import contextlib
import json
import os
import pathlib
import socket
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

from lcats.gettenberg import ingestion
from lcats.utils import capture
from tests.gettenberg_tests import catalog_test

PACKAGE = pathlib.Path(__file__).resolve().parents[2]


@contextlib.contextmanager
def working_directory(path):
    """Temporarily change cwd on all supported Python versions, including 3.10."""
    previous = pathlib.Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(previous)


class ResearchClientTests(unittest.TestCase):
    def execute_notebook(self, name, cwd):
        """Run every code cell without a kernel or saved outputs."""
        notebook = json.loads((PACKAGE / "notebooks" / name).read_text())
        namespace = {}
        with (
            working_directory(cwd),
            capture.suppress_output(),
            mock.patch.object(
                socket, "socket", side_effect=AssertionError("network forbidden")
            ),
        ):
            for cell in notebook["cells"]:
                if cell["cell_type"] == "code":
                    exec(compile("".join(cell["source"]), name, "exec"), namespace)
        return namespace

    def test_offline_html_and_catalog_notebooks_execute(self):
        for name in ("01_gatherers.ipynb", "02_extractors.ipynb"):
            with self.subTest(name=name):
                self.execute_notebook(name, PACKAGE)

    def test_reconciliation_notebook_and_script_use_test_collections(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            project = root / "lcats"
            project.mkdir()
            (project / "pyproject.toml").write_text("")
            data = {
                "name": "Example",
                "author": ["Author"],
                "body": "Text",
                "metadata": {"url": "https://www.gutenberg.org/ebooks/84"},
            }
            for collection in (
                root / "corpora/mass_quantities",
                project / "data/mass_quantities",
            ):
                bucket = collection / "example"
                bucket.mkdir(parents=True)
                (bucket / "story.json").write_text(json.dumps(data))
            namespace = self.execute_notebook("15_reconcile_files.ipynb", project)
            comparison = namespace["comparison"]
            self.assertTrue(comparison[0]["bodies_match"])
            command = [
                sys.executable,
                str(PACKAGE / "notebooks/15_reconcile_files.py"),
                str(root / "corpora/mass_quantities"),
                str(project / "data/mass_quantities"),
            ]
            process = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(json.loads(process.stdout), comparison)

    def test_genre_script_uses_an_explicit_catalog_and_corpus(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            database = self.database
            bucket = root / "corpus/example/story"
            bucket.mkdir(parents=True)
            (bucket / "story.json").write_text(
                json.dumps(
                    {
                        "name": "Fixture",
                        "body": "Fixture",
                        "metadata": {"url": "https://www.gutenberg.org/ebooks/84"},
                    }
                )
            )
            process = subprocess.run(
                [
                    sys.executable,
                    str(PACKAGE / "KMo/genre.py"),
                    str(database),
                    str(root / "corpus"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(sum(json.loads(process.stdout).values()), 1)

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        root = pathlib.Path(cls.directory.name)
        archive = root / "source.tar.bz2"
        fixture = catalog_test.FIXTURES / "pg84.rdf"
        archive.write_bytes(
            catalog_test.archive_bytes(
                [(fixture.name, fixture.read_bytes(), tarfile.REGTYPE)]
            )
        )
        cls.database = root / "catalog.sqlite"
        ingestion.build_catalog(archive, cls.database)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()


if __name__ == "__main__":
    unittest.main()
