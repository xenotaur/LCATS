"""Tests for tools/check_genre_story_binding.py (WI-PROMOTE-0133)."""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_TOOL_PATH = pathlib.Path(__file__).resolve().parents[2] / (
    "tools/check_genre_story_binding.py"
)
_ARCHIVE_PATH = (
    _REPO_ROOT
    / "experiments"
    / "05_metadata_genre_prefilter"
    / "archive_checkpoints.py"
)


def _load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


binding = _load("check_genre_story_binding", _TOOL_PATH)

BASELINE = binding.DEFAULT_BASELINE
CORPORA = _REPO_ROOT / "corpora"
EXPECTED_COUNT = 146


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_root(root: pathlib.Path, stories: dict[str, bytes]) -> None:
    for lcats_id, data in stories.items():
        story_dir = root / lcats_id
        story_dir.mkdir(parents=True, exist_ok=True)
        (story_dir / "story.json").write_bytes(data)


def _write_baseline(path: pathlib.Path, stories: dict[str, bytes]) -> None:
    rows = [
        json.dumps({"lcats_id": i, "story_content_hash": _sha(d)})
        for i, d in stories.items()
    ]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _snapshot(root: pathlib.Path) -> dict[str, tuple[int, int]]:
    return {
        str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime_ns)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _run_main(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = binding.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class LoadBaselineTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = pathlib.Path(self._tmp.name) / "baseline.jsonl"

    def _load_lines(self, *lines: str) -> dict[str, str]:
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return binding.load_baseline(self.path)

    def _row(self, lcats_id="a/b", story_hash=None) -> str:
        return json.dumps(
            {"lcats_id": lcats_id, "story_content_hash": story_hash or _sha(b"x")}
        )

    def test_reads_rows_and_ignores_extra_fields_and_blank_lines(self):
        row = json.loads(self._row("a/b"))
        row["archive_path"] = "ignored"
        loaded = self._load_lines(json.dumps(row), "", self._row("c/d"))
        self.assertEqual(loaded, {"a/b": _sha(b"x"), "c/d": _sha(b"x")})

    def test_rejects_bad_rows(self):
        cases = {
            "invalid json": "{not json",
            "not an object": "[1, 2]",
            "missing lcats_id": json.dumps({"story_content_hash": _sha(b"x")}),
            "non-string lcats_id": json.dumps(
                {"lcats_id": 3, "story_content_hash": _sha(b"x")}
            ),
            "missing hash": json.dumps({"lcats_id": "a/b"}),
            "short hash": self._row(story_hash="abc"),
            "uppercase hash": self._row(story_hash=_sha(b"x").upper()),
            "non-string hash": json.dumps({"lcats_id": "a/b", "story_content_hash": 7}),
        }
        for label, line in cases.items():
            with self.subTest(label), self.assertRaises(ValueError):
                self._load_lines(line)

    def test_rejects_unsafe_or_wrong_depth_ids(self):
        for lcats_id in ("a", "a/b/c", "../b", "a/..", "/a/b", "a//b", "a\\b/c", "./b"):
            with self.subTest(lcats_id), self.assertRaises(ValueError):
                self._load_lines(self._row(lcats_id))

    def test_rejects_duplicate_ids(self):
        with self.assertRaises(ValueError):
            self._load_lines(self._row("a/b"), self._row("a/b"))

    def test_rejects_an_empty_baseline(self):
        for content in ("", "\n\n"):
            self.path.write_text(content, encoding="utf-8")
            with self.subTest(content), self.assertRaises(ValueError):
                binding.load_baseline(self.path)

    def test_missing_file_raises_oserror(self):
        with self.assertRaises(OSError):
            binding.load_baseline(self.path)


class CheckRootTest(unittest.TestCase):
    STORIES = {"a/one": b'{"x": 1}', "a/two": b'{"x": 2}', "b/three": b'{"x": 3}'}

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = pathlib.Path(self._tmp.name) / "data"
        self.root.mkdir()
        _write_root(self.root, self.STORIES)
        self.baseline = {i: _sha(d) for i, d in self.STORIES.items()}

    def _problems(self):
        return binding.check_root(self.root, self.baseline)

    def test_match_reports_nothing(self):
        self.assertEqual(
            self._problems(), {"changed": [], "missing": [], "unlisted": []}
        )

    def test_changed_bytes_are_reported(self):
        (self.root / "a/two/story.json").write_bytes(b'{"x": 2} ')
        self.assertEqual(self._problems()["changed"], ["a/two"])

    def test_missing_story_is_reported(self):
        (self.root / "b/three/story.json").unlink()
        self.assertEqual(self._problems()["missing"], ["b/three"])

    def test_missing_collection_is_reported(self):
        for path in sorted((self.root / "b").rglob("*"), reverse=True):
            path.unlink() if path.is_file() else path.rmdir()
        (self.root / "b").rmdir()
        self.assertEqual(self._problems()["missing"], ["b/three"])

    def test_story_json_that_is_a_directory_counts_as_missing(self):
        (self.root / "a/one/story.json").unlink()
        (self.root / "a/one/story.json").mkdir()
        self.assertEqual(self._problems()["missing"], ["a/one"])

    def test_extra_story_with_genre_sidecar_is_unlisted(self):
        _write_root(self.root, {"c/extra": b"{}"})
        (self.root / "c/extra/genre.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self._problems()["unlisted"], ["c/extra"])

    def test_extra_story_without_genre_sidecar_is_not_reported(self):
        _write_root(self.root, {"c/extra": b"{}"})
        (self.root / "c/extra/scenes.json").write_text("{}", encoding="utf-8")
        self.assertEqual(
            self._problems(), {"changed": [], "missing": [], "unlisted": []}
        )

    def test_baseline_story_with_genre_sidecar_is_not_unlisted(self):
        (self.root / "a/one/genre.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self._problems()["unlisted"], [])

    def test_problems_are_sorted_and_reported_together(self):
        (self.root / "a/two/story.json").write_bytes(b"changed")
        (self.root / "a/one/story.json").write_bytes(b"changed")
        (self.root / "b/three/story.json").unlink()
        problems = self._problems()
        self.assertEqual(problems["changed"], ["a/one", "a/two"])
        self.assertEqual(problems["missing"], ["b/three"])

    def test_non_directory_root_raises_valueerror(self):
        with self.assertRaises(ValueError):
            binding.check_root(self.root / "nope", self.baseline)
        with self.assertRaises(ValueError):
            binding.check_root(self.root / "a/one/story.json", self.baseline)

    def test_check_never_writes_under_the_root(self):
        (self.root / "a/two/story.json").write_bytes(b"changed")
        _write_root(self.root, {"c/extra": b"{}"})
        (self.root / "c/extra/genre.json").write_text("{}", encoding="utf-8")
        before = _snapshot(self.root)
        self._problems()
        self.assertEqual(_snapshot(self.root), before)


class MainTest(unittest.TestCase):
    STORIES = CheckRootTest.STORIES

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = pathlib.Path(self._tmp.name)
        self.root = base / "data"
        self.root.mkdir()
        self.baseline = base / "baseline.jsonl"
        _write_root(self.root, self.STORIES)
        _write_baseline(self.baseline, self.STORIES)

    def _main(self):
        return _run_main("--root", str(self.root), "--baseline", str(self.baseline))

    def test_match_exits_0_with_a_single_ok_line_on_stdout(self):
        code, out, err = self._main()
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertEqual(
            out.splitlines(), [f"ok: 3 stories match the baseline under {self.root}"]
        )

    def test_problems_exit_1_and_list_every_kind_on_stderr(self):
        (self.root / "a/one/story.json").write_bytes(b"changed")
        (self.root / "b/three/story.json").unlink()
        _write_root(self.root, {"c/extra": b"{}"})
        (self.root / "c/extra/genre.json").write_text("{}", encoding="utf-8")
        code, out, err = self._main()
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        lines = err.splitlines()
        self.assertTrue(lines[0].startswith("changed: a/one "))
        self.assertTrue(lines[1].startswith("missing: b/three "))
        self.assertTrue(lines[2].startswith("unlisted: c/extra "))
        self.assertIn("check: 3 problem(s)", lines[3])

    def test_malformed_baseline_exits_2_and_checks_nothing(self):
        self.baseline.write_text("{broken\n", encoding="utf-8")
        code, out, err = self._main()
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("error: "))

    def test_missing_baseline_file_exits_2(self):
        self.baseline.unlink()
        code, _out, err = self._main()
        self.assertEqual(code, 2)
        self.assertTrue(err.startswith("error: "))

    def test_empty_baseline_exits_2_rather_than_passing(self):
        self.baseline.write_text("", encoding="utf-8")
        code, _out, _err = self._main()
        self.assertEqual(code, 2)

    def test_missing_root_exits_2(self):
        code, _out, err = _run_main(
            "--root", str(self.root / "nope"), "--baseline", str(self.baseline)
        )
        self.assertEqual(code, 2)
        self.assertIn("root is not a directory", err)

    def test_root_is_required(self):
        with (
            self.assertRaises(SystemExit) as raised,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            binding.main(["--baseline", str(self.baseline)])
        self.assertEqual(raised.exception.code, 2)


class RealBaselineTest(unittest.TestCase):
    def test_baseline_has_146_rows(self):
        self.assertEqual(len(binding.load_baseline(BASELINE)), EXPECTED_COUNT)

    def test_real_baseline_matches_current_corpora(self):
        problems = binding.check_root(CORPORA, binding.load_baseline(BASELINE))
        self.assertEqual(problems, {"changed": [], "missing": [], "unlisted": []})

    def test_script_runs_standalone_against_corpora(self):
        result = subprocess.run(
            [sys.executable, str(_TOOL_PATH), "--root", str(CORPORA)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            f"ok: {EXPECTED_COUNT} stories match the baseline under {CORPORA}",
        )
        self.assertEqual(result.stderr, "")


class AgreementWithArchiveVerifyTest(unittest.TestCase):
    """The tool and archive_checkpoints.py verify must not drift apart.

    ``verify`` also audits the archive and evidence, so only exit codes are
    compared. A root of symlinks to the real stories stands in for ``data/``; the
    one story that is altered is a real copy, so the corpus is never touched.
    """

    @classmethod
    def setUpClass(cls):
        cls.archive = _load("archive_checkpoints_for_agreement", _ARCHIVE_PATH)

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = pathlib.Path(self._tmp.name) / "stories"
        self.baseline = binding.load_baseline(BASELINE)
        for lcats_id in self.baseline:
            story_dir = self.root / lcats_id
            story_dir.mkdir(parents=True)
            os.symlink(CORPORA / lcats_id / "story.json", story_dir / "story.json")

    def _verify_exit(self) -> int:
        problems = self.archive.verify(
            self.archive.DEFAULT_ARCHIVE,
            self.archive.DEFAULT_MANIFEST,
            self.archive.DEFAULT_EVIDENCE,
            self.root,
        )
        return 1 if problems else 0

    def _tool_exit(self) -> int:
        code, _out, _err = _run_main("--root", str(self.root))
        return code

    def test_both_pass_on_an_unmodified_root(self):
        # Precondition: verify also fails on unrelated archive problems, so it
        # must be shown to pass here before its failure below means anything.
        self.assertEqual(self._verify_exit(), 0)
        self.assertEqual(self._tool_exit(), 0)

    def test_both_fail_when_one_story_changes(self):
        self.assertEqual(self._verify_exit(), 0)
        victim = sorted(self.baseline)[0]
        story = self.root / victim / "story.json"
        data = (CORPORA / victim / "story.json").read_bytes()
        story.unlink()
        story.write_bytes(data + b" ")
        self.assertEqual(self._verify_exit(), 1)
        self.assertEqual(self._tool_exit(), 1)


if __name__ == "__main__":
    unittest.main()
