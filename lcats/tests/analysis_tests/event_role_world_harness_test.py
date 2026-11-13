"""NLP discovery and smoke-runner regressions without optional dependencies."""

import ast
import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from lcats.utils import capture
from tests.smoke import resources
from tests.smoke import run


class FixtureCase:
    """Minimal test identity handed to the real subprocess coordinator."""

    backend_name = "spacy"

    def __init__(self, name):
        self.name = name

    def id(self):
        return self.name


class DiscoveryIsolationTest(unittest.TestCase):
    def test_full_discovery_never_attempts_optional_native_imports(self):
        # BaseException prevents an old broad `except Exception` availability
        # probe from masking the forbidden import. This runs in a fresh process,
        # regardless of which native packages the developer has installed.
        code = """
import importlib.abc
import sys
import unittest
class NativeImportAttempt(BaseException):
    pass
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'spacy', 'stanza', 'torch', 'en_core_web_sm'}:
            raise NativeImportAttempt(fullname)
sys.meta_path.insert(0, Guard())
loader = unittest.TestLoader()
suite = loader.discover('tests', pattern='*_test.py')
assert not loader.errors, loader.errors
assert suite.countTestCases() > 1000, suite.countTestCases()
print(suite.countTestCases())
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=run.PACKAGE_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_four_real_checks_and_121_ordinary_event_role_world_methods_remain(self):
        cases = run.discover()
        self.assertEqual(len(cases), 4)
        self.assertEqual(
            sorted(c.backend_name for c in cases), ["spacy"] * 3 + ["stanza"]
        )
        path = run.PACKAGE_ROOT / "tests/analysis_tests/event_role_world_test.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        methods = [
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
        ]
        self.assertEqual(len(methods), 121)


class SmokeHarnessTest(unittest.TestCase):
    def test_cpu_environment_does_not_mutate_parent(self):
        with mock.patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "2"}):
            child = run.child_environment()
            self.assertEqual(child["CUDA_VISIBLE_DEVICES"], "-1")
            self.assertEqual(os.environ["CUDA_VISIBLE_DEVICES"], "2")

    def test_child_sees_cpu_and_offline_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp) / "child"
            result = run.run_child(
                [
                    sys.executable,
                    "-c",
                    "import os; assert os.environ['CUDA_VISIBLE_DEVICES']=='-1'; assert os.environ['HF_HUB_OFFLINE']=='1'",
                ],
                directory,
                10,
            )
            self.assertEqual(result["returncode"], 0)

    def test_success_and_failures_continue_with_incremental_logs(self):
        names = ["success", "failure", "no-receipt", "zero", "skip", "success"]
        with tempfile.TemporaryDirectory() as tmp, capture.suppress_output():
            root = pathlib.Path(tmp)
            status = run.run_cases(
                [FixtureCase(n) for n in names],
                root,
                10,
                worker_module="tests.smoke.fixture_worker",
            )
            summary = json.loads(next(root.glob("run-*/summary.json")).read_text())
            self.assertEqual(status, 1)
            self.assertEqual(
                [r["ok"] for r in summary], [True, False, False, False, False, True]
            )
            for row in summary:
                self.assertIn(
                    "fixture stdout",
                    pathlib.Path(row["logs"], "stdout.log").read_text(),
                )
                self.assertIn(
                    "fixture native stderr",
                    pathlib.Path(row["logs"], "stderr.log").read_text(),
                )

    @unittest.skipUnless(os.name == "posix", "POSIX signal return codes")
    def test_signal_and_timeout_are_diagnosed_and_later_child_runs(self):
        with tempfile.TemporaryDirectory() as tmp, capture.suppress_output():
            root = pathlib.Path(tmp)
            status = run.run_cases(
                [FixtureCase(n) for n in ["signal", "timeout", "success"]],
                root,
                1,
                worker_module="tests.smoke.fixture_worker",
            )
            rows = json.loads(next(root.glob("run-*/summary.json")).read_text())
            self.assertEqual(status, 1)
            self.assertIn("SIGTERM", rows[0]["reason"])
            self.assertEqual(rows[1]["reason"], "timeout")
            self.assertTrue(rows[2]["ok"])

    def test_zero_selection_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "No smoke checks"):
                run.run_cases([], pathlib.Path(tmp), 1)

    def test_worker_requires_actual_assertion_success_and_rejects_skips(self):
        # Replace only the external prerequisite boundary inside a disposable
        # interpreter; assertions and unittest result handling remain real.
        for body, expected in [
            ("assert False, 'controlled assertion'", 1),
            ("self.skipTest('controlled skip')", 1),
            ("pass", 0),
        ]:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as tmp:
                code = f"""
import pathlib, unittest
from tests.smoke import run, resources
resources.check = lambda backend: {{'fixture': 'controlled'}}
class Check(unittest.TestCase):
    def test_case(self):
        {body}
raise SystemExit(run.worker('__main__.Check.test_case', 'spacy', pathlib.Path({tmp!r})))
"""
                result = subprocess.run(
                    [sys.executable, "-c", code],
                    cwd=run.PACKAGE_ROOT,
                    capture_output=True,
                    timeout=10,
                )
                self.assertEqual(result.returncode, expected, result.stderr)
                receipt = json.loads(pathlib.Path(tmp, "receipt.json").read_text())
                self.assertEqual(receipt["tests_run"], 1)

    def test_missing_prerequisite_fails_without_optional_installs(self):
        # -S removes site-packages even when the parent has NLP extras installed.
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "-S",
                    "-m",
                    "tests.smoke.run",
                    "--worker",
                    "unused",
                    "--backend",
                    "spacy",
                    "--worker-dir",
                    tmp,
                ],
                cwd=run.PACKAGE_ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("PackageNotFoundError", result.stderr)
            self.assertFalse(pathlib.Path(tmp, "receipt.json").exists())

    @unittest.skipUnless(os.name == "posix", "POSIX native abort diagnostics")
    def test_fault_log_survives_native_abort_and_fd_suppression(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = f"""
import os, pathlib, resource, unittest
from tests.smoke import run, resources
from lcats.utils import capture
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
resources.check = lambda backend: {{'fixture': 'controlled'}}
class Check(unittest.TestCase):
    def test_abort(self):
        with capture.suppress_output(suppress_file_descriptors=True):
            os.abort()
raise SystemExit(run.worker('__main__.Check.test_abort', 'spacy', pathlib.Path({tmp!r})))
"""
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=run.PACKAGE_ROOT,
                capture_output=True,
                timeout=10,
            )
            self.assertLess(result.returncode, 0)
            fault = pathlib.Path(tmp, "fault.log").read_text()
            self.assertIn("Fatal Python error", fault)
            self.assertIn("test_abort", fault)
            self.assertFalse(pathlib.Path(tmp, "receipt.json").exists())

    def test_network_is_rejected_in_disposable_child(self):
        code = "from tests.smoke import run; import sys,socket; sys.addaudithook(run.block_network); socket.create_connection(('example.com',443))"
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=run.PACKAGE_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Smoke execution is offline", result.stderr)

    def test_dry_run_lists_four_checks_without_running_children(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(run.main(["--dry-run"]), 0)
        self.assertEqual(len(out.getvalue().splitlines()), 4)

    def test_invalid_timeouts_fail(self):
        for value in ["0", "-1", "nan", "inf"]:
            with self.subTest(value=value), capture.suppress_output():
                with self.assertRaises(SystemExit):
                    run.main(["--timeout", value])

    def test_missing_and_corrupt_model_files_are_rejected(self):
        spec = {
            "packages": {"stanza": "1", "torch": "1"},
            "stanza_resources_sha256": "wrong",
        }
        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.dict(os.environ, {"STANZA_RESOURCES_DIR": tmp}),
            mock.patch.object(resources, "manifest", return_value=spec),
            mock.patch.object(
                resources.importlib.metadata, "version", return_value="1"
            ),
        ):
            with self.assertRaises(FileNotFoundError):
                resources.check("stanza")
            pathlib.Path(tmp, "resources.json").write_text("{}")
            with self.assertRaisesRegex(RuntimeError, "differs"):
                resources.check("stanza")
