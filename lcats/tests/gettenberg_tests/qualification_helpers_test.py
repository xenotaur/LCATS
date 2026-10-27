"""Offline regressions for the archived qualification entry points."""

import dataclasses
import hashlib
import importlib.util
import io
import json
import pathlib
import sqlite3
import signal
import subprocess
import sys
import tarfile
import tempfile
import types
import unittest
from unittest import mock

from lcats.gettenberg import rdf
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
        # These entry points belong to provider qualification. Historical gather
        # review runners remain reproducible on the preserved qualification branch,
        # where their separated runtime dependencies exist; they are not clients
        # of this narrower package. Keep all supported provider CLIs covered.
        names = (
            "measure_baseline.py",
            "probe_legacy.py",
            "probe_parser.py",
            "qualify_catalog.py",
            "qualify_lifecycle.py",
            "qualify_migration.py",
            "reproduce_scope_facts.py",
            "qualify_snapshot.py",
            "qualify_index_counts.py",
        )
        paths = [SCRIPTS / name for name in names]
        paths.extend(sorted(SCRIPTS.glob("qualify_narrow_*.py")))
        for path in paths:
            with self.subTest(script=path.name):
                imported = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        "import pathlib,runpy,sys; "
                        "sys.path.insert(0,str(pathlib.Path(sys.argv[1]).parent)); "
                        "sys.modules['gutenbergpy']=None; "
                        "runpy.run_path(sys.argv[1])",
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

    def test_parser_probe_does_not_retain_archive_member_headers(self):
        # Long member names amplify retained TarInfo memory, independently of
        # ebook count or native XML allocations. Both archives are real files.
        retained = []
        for count in (20, 600):
            archive = self.directory / f"members-{count}.tar.bz2"
            data = catalog_test.record(84, "Fixture")
            with tarfile.open(archive, "w:bz2", format=tarfile.GNU_FORMAT) as output:
                for index in range(count):
                    member = tarfile.TarInfo(f"{'x' * 8192}/{index}.rdf")
                    member.size = len(data)
                    output.addfile(member, io.BytesIO(data))
            measure = """
import contextlib, io, runpy, sys, tracemalloc
probe = runpy.run_path(sys.argv[1])
tracemalloc.start()
live = [None]
def sample(frame, event, _argument):
    if event == 'return' and frame.f_code.co_name == 'parse_record':
        live[0] = tracemalloc.get_traced_memory()[0]
sys.setprofile(sample)
try:
    with contextlib.redirect_stdout(io.StringIO()):
        probe['main'](sys.argv[2:])
finally:
    sys.setprofile(None)
print(live[0])
"""
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    measure,
                    str(SCRIPTS / "probe_parser.py"),
                    str(archive),
                    str(self.directory / f"members-{count}.json"),
                ],
                cwd=ROOT / "lcats",
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            retained.append(int(result.stdout.strip()))
        # Sample live allocations at the last record, avoiding transient bz2
        # expansion peaks. Retaining 580 extra 8-KiB names alone exceeds 4 MiB;
        # permit 2 MiB of buffer noise while requiring bounded header retention.
        self.assertLess(retained[1] - retained[0], 2 * 1024**2, retained)

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

    def test_causal_replay_rejects_changed_missing_and_added_product_sources(self):
        # A tiny real Git tree exercises the closure guard independently of LCATS
        # imports. A transitive module must be pinned before it is ever loaded.
        spec = importlib.util.spec_from_file_location(
            "audit_cleanup_causality", SCRIPTS / "audit_cleanup_causality.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        root = self.directory / "repository"
        product = root / "lcats/src/lcats"
        product.mkdir(parents=True)
        helper = product / "transitive.py"
        helper.write_text("VALUE = 1\n", encoding="utf-8")
        for arguments in (["init", "--quiet"], ["add", "."]):
            subprocess.run(
                ["git", *arguments], cwd=root, check=True, capture_output=True
            )
        tree = subprocess.check_output(
            ["git", "write-tree"], cwd=root, text=True
        ).strip()
        self.assertEqual(set(module.product_tree_guard(root, tree)), {"transitive.py"})
        helper.write_text("VALUE = 2\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed runtime product"):
            module.product_tree_guard(root, tree)
        helper.unlink()
        with self.assertRaisesRegex(ValueError, "added or missing"):
            module.product_tree_guard(root, tree)
        helper.write_text("VALUE = 1\n", encoding="utf-8")
        (product / "extra.py").write_text("VALUE = 3\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "added or missing"):
            module.product_tree_guard(root, tree)

    def test_causal_replay_rejects_shadow_imports_including_late_imports(self):
        spec = importlib.util.spec_from_file_location(
            "audit_cleanup_causality", SCRIPTS / "audit_cleanup_causality.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # The archived runner intentionally pins old product code, but the package
        # suite must allow future product changes. Use an isolated package fixture.
        product = self.directory / "lcats/src/lcats"
        product.mkdir(parents=True)
        package_path = product / "__init__.py"
        helper_path = product / "transitive.py"
        package_path.touch()
        helper_path.touch()
        package_spec = importlib.util.spec_from_file_location("lcats", package_path)
        helper_spec = importlib.util.spec_from_file_location(
            "lcats.transitive", helper_path
        )
        package = importlib.util.module_from_spec(package_spec)
        helper = importlib.util.module_from_spec(helper_spec)
        expected = {"__init__.py": "fixture", "transitive.py": "fixture"}
        with mock.patch.dict(
            sys.modules, {"lcats": package, "lcats.transitive": helper}, clear=True
        ):
            module.product_import_guard(root=self.directory, expected_paths=expected)
            # A module loaded during measurement must not come from another tree.
            helper.__file__ = str(self.directory / "shadow.py")
            with self.assertRaisesRegex(ValueError, "wrong imported module"):
                module.product_import_guard(
                    root=self.directory, expected_paths=expected
                )

    def test_snapshot_checks_every_field_and_source_not_only_id(self):
        spec = importlib.util.spec_from_file_location(
            "qualify_snapshot", SCRIPTS / "qualify_snapshot.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
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
