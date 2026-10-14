"""Offline regressions for the archived qualification entry points."""

import hashlib
import importlib.util
import json
import pathlib
import sqlite3
import signal
import subprocess
import sys
import tarfile
import tempfile
import unittest

from tests.gettenberg_tests import catalog_test

ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "experiments/10_gettenberg_qualification/scripts"


class QualificationHelpersTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = pathlib.Path(temporary.name)
        self.archive = self.directory / "tiny.tar.bz2"
        self.archive.write_bytes(
            catalog_test.archive_bytes(
                [("pg84.rdf", catalog_test.record(84, "Tiny fixture"), tarfile.REGTYPE)]
            )
        )

    def run_script(self, name, *arguments, optimized=False):
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command += [str(SCRIPTS / name), *map(str, arguments)]
        return subprocess.run(
            command, cwd=ROOT / "lcats", capture_output=True, text=True, timeout=30
        )

    def test_imports_do_not_execute_measurements_and_help_is_available(self):
        for path in sorted(SCRIPTS.glob("*.py")):
            with self.subTest(script=path.name):
                imported = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        "import runpy,sys; runpy.run_path(sys.argv[1])",
                        str(path),
                    ],
                    cwd=ROOT / "lcats",
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(imported.returncode, 0, imported.stderr)
                self.assertEqual(imported.stdout, "")
                helped = self.run_script(path.name, "--help")
                self.assertEqual(helped.returncode, 0, helped.stderr)
                self.assertIn("usage:", helped.stdout)

    def test_relative_candidate_paths_support_sqlite_uri_before_build(self):
        spec = importlib.util.spec_from_file_location(
            "qualification_catalog", SCRIPTS / "qualify_catalog.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        archive, candidate, output = module.parse_arguments(
            ["relative.tar.bz2", "./candidate.sqlite", "result.json"]
        )
        for path in (archive, candidate, output):
            self.assertTrue(path.is_absolute())
            self.assertTrue(path.as_uri().startswith("file:"))

    @unittest.skipUnless(hasattr(signal, "SIGALRM"), "POSIX qualification runner")
    def test_optimized_python_still_rejects_wrong_snapshot_before_setup(self):
        for optimized in (False, True):
            with self.subTest(optimized=optimized):
                cache = self.directory / ("optimized" if optimized else "normal")
                output = cache.with_suffix(".json")
                process = self.run_script(
                    "qualify_lifecycle.py",
                    self.archive,
                    cache,
                    output,
                    optimized=optimized,
                )
                self.assertNotEqual(process.returncode, 0)
                evidence = json.loads(output.read_text())
                self.assertFalse(evidence["qualified"])
                self.assertIn("digest == EXPECTED_ARCHIVE", evidence["error"])
                self.assertFalse(cache.exists())

    def test_catalog_failure_saves_evidence_after_tiny_fixture_build(self):
        output = self.directory / "catalog.json"
        result = self.run_script(
            "qualify_catalog.py",
            self.archive,
            self.directory / "catalog.sqlite",
            output,
        )
        self.assertNotEqual(result.returncode, 0)
        evidence = json.loads(output.read_text())
        self.assertFalse(evidence["qualified"])
        self.assertIn("differs from the recorded baseline", evidence["failure"])
        self.assertEqual(evidence["build"]["imported"], 1)

    def test_parser_probe_preserves_input_and_counts_real_fixture(self):
        output = self.directory / "parser.json"
        digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        result = self.run_script("probe_parser.py", self.archive, output)
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(output.read_text())
        self.assertEqual(evidence["counts"]["parsed"], 1)
        self.assertEqual(evidence["archive_sha256"], digest)
        self.assertEqual(hashlib.sha256(self.archive.read_bytes()).hexdigest(), digest)

    def test_baseline_reads_legacy_database_without_mutation(self):
        database = self.directory / "legacy.sqlite"
        with sqlite3.connect(database) as connection:
            connection.executescript(
                "CREATE TABLE languages(id INTEGER,name TEXT); INSERT INTO languages VALUES(1,'en'); CREATE TABLE books(gutenbergbookid INTEGER,languageid INTEGER); INSERT INTO books VALUES(84,1);"
            )
        original = database.read_bytes()
        output = self.directory / "baseline.json"
        result = self.run_script("measure_baseline.py", self.archive, database, output)
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(output.read_text())
        self.assertEqual(evidence["database_table_counts"]["books"], 1)
        self.assertEqual(database.read_bytes(), original)
        self.assertTrue(output.with_name("rdf_samples.json").is_file())
