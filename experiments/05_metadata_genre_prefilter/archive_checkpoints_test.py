"""Tests for the genre-evidence checkpoint archive tool (WI-PROMOTE-0124)."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

_TOOL_PATH = pathlib.Path(__file__).resolve().parent / "archive_checkpoints.py"
_SPEC = importlib.util.spec_from_file_location("archive_checkpoints", _TOOL_PATH)
assert _SPEC is not None and _SPEC.loader is not None
tool = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(tool)

# One ordinary id, one whose story name contains a double underscore (as 84 of the
# real 146 do), so the forward-only name mapping is exercised.
IDS = ("coll/alpha", "mass/the_x__bacon")


def _model_assessment(lcats_id: str) -> dict:
    return {
        "assessment_id": f"model-{lcats_id}",
        "generated_at": "2026-08-21T19:00:00Z",
        "method": {"name": "lcats.analysis.corpus.assess.assess_story"},
        "result": {"detected_genre": "horror"},
        "provenance": {"input_tokens": 100},
    }


def _write_json(path: pathlib.Path, obj: dict) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    # No trailing newline, like the real checkpoint files.
    data = json.dumps(obj, indent=2).encode("utf-8")
    path.write_bytes(data)
    return data


class _Fixture:
    """A fake source tree, evidence file and corpora, all consistent."""

    def __init__(self, root: pathlib.Path) -> None:
        self.root = root
        self.source = root / "source"
        self.archive = root / "archive"
        self.manifest = root / "baseline.jsonl"
        self.evidence = root / "validation_results.jsonl"
        self.corpora = root / "corpora"
        lines = []
        for lcats_id in IDS:
            story = self.corpora / lcats_id / "story.json"
            _write_json(story, {"body": f"text of {lcats_id}"})
            model = _model_assessment(lcats_id)
            for kind, source_name, _archived in tool.KINDS:
                _write_json(
                    tool.source_file(self.source, lcats_id, source_name),
                    {
                        "outcome": "success",
                        "fingerprint": {
                            "model": kind,
                            "story_content_hash": self._hash_for(lcats_id),
                        },
                        "data": {"model_assessment": model, "input_tokens": 100},
                    },
                )
            lines.append(
                json.dumps(
                    {
                        "lcats_id": lcats_id,
                        "assessments": [
                            {"method": {"name": "gutenberg_subject_rules"}},
                            model,
                        ],
                    }
                )
            )
        self.evidence.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _hash_for(self, lcats_id: str) -> str:
        story = self.corpora / lcats_id / "story.json"
        return tool.sha256_bytes(story.read_bytes())

    def archive_all(self) -> list[dict]:
        ids = list(tool.load_evidence(self.evidence))
        rows = tool.archive_checkpoints(self.source, self.archive, ids)
        tool.write_jsonl_atomically(self.archive / tool.INDEX_NAME, rows)
        tool.write_jsonl_atomically(
            self.manifest, tool.derive_manifest(self.archive, ids)
        )
        return rows

    def problems(self) -> list[str]:
        return tool.verify(self.archive, self.manifest, self.evidence, self.corpora)


class _TempDirCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.fx = _Fixture(pathlib.Path(self._tmp.name))


class ArchiveTest(_TempDirCase):
    def test_copies_every_file_byte_for_byte_nested_by_id(self) -> None:
        rows = self.fx.archive_all()
        self.assertEqual(len(rows), len(IDS) * len(tool.KINDS))
        for lcats_id in IDS:
            for _kind, source_name, archived in tool.KINDS:
                src = tool.source_file(self.fx.source, lcats_id, source_name)
                dest = self.fx.archive / lcats_id / archived
                self.assertEqual(dest.read_bytes(), src.read_bytes())

    def test_double_underscore_story_name_stays_a_single_directory(self) -> None:
        self.fx.archive_all()
        self.assertTrue(
            (
                self.fx.archive / "mass" / "the_x__bacon" / "opus-checkpoint.json"
            ).is_file()
        )

    def test_index_records_sha256_and_size_sorted(self) -> None:
        rows = self.fx.archive_all()
        self.assertEqual(rows, sorted(rows, key=lambda r: (r["lcats_id"], r["kind"])))
        for row in rows:
            data = (self.fx.archive / row["archive_path"]).read_bytes()
            self.assertEqual(row["sha256"], tool.sha256_bytes(data))
            self.assertEqual(row["bytes"], len(data))

    def test_source_files_are_never_modified(self) -> None:
        before = {
            p: p.read_bytes() for p in self.fx.source.rglob("*.json") if p.is_file()
        }
        self.fx.archive_all()
        after = {
            p: p.read_bytes() for p in self.fx.source.rglob("*.json") if p.is_file()
        }
        self.assertEqual(before, after)

    def test_rerun_over_identical_archive_is_a_no_op(self) -> None:
        first = self.fx.archive_all()
        second = self.fx.archive_all()
        self.assertEqual(first, second)

    def test_missing_source_writes_nothing(self) -> None:
        victim = tool.source_file(
            self.fx.source, IDS[1], tool.KINDS[1][1]
        )  # a gpt-oss file
        victim.unlink()
        with self.assertRaises(tool.ArchiveError):
            tool.archive_checkpoints(self.fx.source, self.fx.archive, list(IDS))
        self.assertFalse(self.fx.archive.exists())

    def test_conflicting_archive_content_is_refused_and_untouched(self) -> None:
        self.fx.archive_all()
        target = self.fx.archive / IDS[0] / "opus-checkpoint.json"
        target.write_bytes(b"tampered")
        with self.assertRaises(tool.ArchiveError):
            tool.archive_checkpoints(self.fx.source, self.fx.archive, list(IDS))
        self.assertEqual(target.read_bytes(), b"tampered")

    def test_unsafe_ids_are_rejected(self) -> None:
        for bad in ("../x/y", "a/b/c", "nocollection", "a/.."):
            with self.assertRaises(tool.ArchiveError):
                tool._require_safe_id(bad, "test")


class ManifestTest(_TempDirCase):
    def test_manifest_comes_from_the_opus_files_only(self) -> None:
        self.fx.archive_all()
        # Corrupt the gpt-oss hash: the manifest must not change.
        gpt = self.fx.archive / IDS[0] / "gpt-oss-20b-checkpoint.json"
        data = json.loads(gpt.read_text(encoding="utf-8"))
        data["fingerprint"]["story_content_hash"] = "0" * 64
        gpt.write_text(json.dumps(data), encoding="utf-8")
        rows = tool.derive_manifest(self.fx.archive, list(IDS))
        self.assertEqual(
            [r["story_content_hash"] for r in rows],
            [self.fx._hash_for(i) for i in IDS],
        )

    def test_manifest_has_one_unique_row_per_id(self) -> None:
        self.fx.archive_all()
        rows = [
            json.loads(line)
            for line in self.fx.manifest.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual([r["lcats_id"] for r in rows], list(IDS))

    def test_invalid_fingerprint_is_an_error(self) -> None:
        self.fx.archive_all()
        opus = self.fx.archive / IDS[0] / "opus-checkpoint.json"
        data = json.loads(opus.read_text(encoding="utf-8"))
        data["fingerprint"]["story_content_hash"] = "not-a-hash"
        opus.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(tool.ArchiveError):
            tool.derive_manifest(self.fx.archive, list(IDS))


class VerifyTest(_TempDirCase):
    def test_clean_archive_verifies(self) -> None:
        self.fx.archive_all()
        self.assertEqual(self.fx.problems(), [])

    def test_changed_archived_file_is_detected_by_the_index(self) -> None:
        self.fx.archive_all()
        (self.fx.archive / IDS[0] / "opus-checkpoint.json").write_bytes(b"{}")
        self.assertTrue(any("differs from the index" in p for p in self.fx.problems()))

    def test_manifest_drift_is_detected(self) -> None:
        self.fx.archive_all()
        rows = [
            json.loads(line)
            for line in self.fx.manifest.read_text(encoding="utf-8").splitlines()
        ]
        rows[0]["story_content_hash"] = "1" * 64
        tool.write_jsonl_atomically(self.fx.manifest, rows)
        self.assertTrue(any("manifest hash differs" in p for p in self.fx.problems()))

    def test_manifest_with_a_missing_row_is_detected(self) -> None:
        self.fx.archive_all()
        rows = [
            json.loads(line)
            for line in self.fx.manifest.read_text(encoding="utf-8").splitlines()
        ]
        tool.write_jsonl_atomically(self.fx.manifest, rows[:1])
        self.assertTrue(any("manifest has 1 rows" in p for p in self.fx.problems()))

    def test_changed_corpora_story_is_detected(self) -> None:
        self.fx.archive_all()
        story = self.fx.corpora / IDS[1] / "story.json"
        story.write_bytes(story.read_bytes() + b" ")
        self.assertTrue(
            any("current story.json differs" in p for p in self.fx.problems())
        )

    def test_missing_corpora_story_is_detected(self) -> None:
        self.fx.archive_all()
        shutil.rmtree(self.fx.corpora / IDS[0])
        self.assertTrue(any("no story.json" in p for p in self.fx.problems()))

    def test_model_assessment_difference_is_detected_in_full(self) -> None:
        self.fx.archive_all()
        # Same generated_at and input_tokens, different result: must still fail.
        opus = self.fx.archive / IDS[0] / "opus-checkpoint.json"
        data = json.loads(opus.read_text(encoding="utf-8"))
        data["data"]["model_assessment"]["result"]["detected_genre"] = "western"
        new_bytes = json.dumps(data).encode("utf-8")
        opus.write_bytes(new_bytes)
        rows = [
            json.loads(line)
            for line in (self.fx.archive / tool.INDEX_NAME)
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        for row in rows:
            if row["archive_path"] == f"{IDS[0]}/opus-checkpoint.json":
                row["sha256"] = tool.sha256_bytes(new_bytes)
                row["bytes"] = len(new_bytes)
        tool.write_jsonl_atomically(self.fx.archive / tool.INDEX_NAME, rows)
        problems = self.fx.problems()
        self.assertTrue(
            any("model_assessment differs" in p for p in problems), problems
        )
        self.assertFalse(any("differs from the index" in p for p in problems))

    def test_gpt_oss_hash_mismatch_is_detected(self) -> None:
        self.fx.archive_all()
        gpt = self.fx.archive / IDS[0] / "gpt-oss-20b-checkpoint.json"
        data = json.loads(gpt.read_text(encoding="utf-8"))
        data["fingerprint"]["story_content_hash"] = "2" * 64
        new_bytes = json.dumps(data).encode("utf-8")
        gpt.write_bytes(new_bytes)
        rows = [
            json.loads(line)
            for line in (self.fx.archive / tool.INDEX_NAME)
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        for row in rows:
            if row["archive_path"] == f"{IDS[0]}/gpt-oss-20b-checkpoint.json":
                row["sha256"] = tool.sha256_bytes(new_bytes)
                row["bytes"] = len(new_bytes)
        tool.write_jsonl_atomically(self.fx.archive / tool.INDEX_NAME, rows)
        self.assertTrue(any("gpt-oss hash differs" in p for p in self.fx.problems()))

    def test_manifest_archive_sha256_and_path_drift_are_detected(self) -> None:
        self.fx.archive_all()
        rows = [
            json.loads(line)
            for line in self.fx.manifest.read_text(encoding="utf-8").splitlines()
        ]
        rows[0]["archive_sha256"] = "0" * 64
        tool.write_jsonl_atomically(self.fx.manifest, rows)
        self.assertTrue(
            any("archive_path or archive_sha256" in p for p in self.fx.problems())
        )
        rows[0]["archive_sha256"] = tool.sha256_file(
            self.fx.archive / rows[0]["archive_path"]
        )
        rows[1]["archive_path"] = "bogus"
        tool.write_jsonl_atomically(self.fx.manifest, rows)
        self.assertTrue(
            any("archive_path or archive_sha256" in p for p in self.fx.problems())
        )

    def test_duplicate_index_row_is_detected(self) -> None:
        rows = self.fx.archive_all()
        tool.write_jsonl_atomically(self.fx.archive / tool.INDEX_NAME, rows + [rows[0]])
        self.assertTrue(any("duplicate row" in p for p in self.fx.problems()))

    def test_wrong_archive_path_in_the_index_is_detected(self) -> None:
        rows = self.fx.archive_all()
        rows[0] = {**rows[0], "archive_path": "somewhere/else.json"}
        tool.write_jsonl_atomically(self.fx.archive / tool.INDEX_NAME, rows)
        self.assertTrue(
            any("index archive_path wrong" in p for p in self.fx.problems())
        )

    def test_corrupt_archived_json_is_a_problem_not_a_traceback(self) -> None:
        self.fx.archive_all()
        (self.fx.archive / IDS[0] / "opus-checkpoint.json").write_bytes(b"{not json")
        problems = self.fx.problems()
        self.assertTrue(any("unreadable archived checkpoint" in p for p in problems))
        self.assertTrue(any("differs from the index" in p for p in problems))

    def test_copies_leave_no_temporary_files(self) -> None:
        self.fx.archive_all()
        self.assertEqual(list(self.fx.archive.rglob("*.tmp")), [])

    def test_unexpected_file_in_archive_is_detected(self) -> None:
        self.fx.archive_all()
        (self.fx.archive / "stray.txt").write_text("x", encoding="utf-8")
        self.assertTrue(any("unexpected file" in p for p in self.fx.problems()))

    def test_readme_beside_the_archive_is_allowed(self) -> None:
        self.fx.archive_all()
        (self.fx.archive / tool.README_NAME).write_text("notes", encoding="utf-8")
        self.assertEqual(self.fx.problems(), [])


class CliTest(_TempDirCase):
    def _argv(self, command: str) -> list[str]:
        argv = [
            command,
            "--evidence",
            str(self.fx.evidence),
            "--archive-root",
            str(self.fx.archive),
            "--manifest",
            str(self.fx.manifest),
            "--corpora",
            str(self.fx.corpora),
        ]
        if command == "archive":
            argv += ["--source", str(self.fx.source)]
        return argv

    def _run(self, argv: list[str]) -> tuple[int, str]:
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = tool.main(argv)
        return code, err.getvalue()

    def test_archive_then_verify_exit_zero(self) -> None:
        self.assertEqual(self._run(self._argv("archive"))[0], 0)
        self.assertEqual(self._run(self._argv("verify"))[0], 0)

    def test_missing_source_exits_two_and_writes_nothing(self) -> None:
        shutil.rmtree(self.fx.source)
        code, err = self._run(self._argv("archive"))
        self.assertEqual(code, 2)
        self.assertIn("missing", err)
        self.assertFalse(self.fx.archive.exists())

    def test_malformed_evidence_exits_two_not_a_traceback(self) -> None:
        self.fx.evidence.write_text("{not json\n", encoding="utf-8")
        code, err = self._run(self._argv("verify"))
        self.assertEqual(code, 2)
        self.assertIn("malformed", err)

    def test_missing_evidence_file_exits_two(self) -> None:
        self.fx.evidence.unlink()
        self.assertEqual(self._run(self._argv("verify"))[0], 2)

    def test_corrupt_archived_checkpoint_exits_one(self) -> None:
        self._run(self._argv("archive"))
        (self.fx.archive / IDS[0] / "opus-checkpoint.json").write_bytes(b"{not json")
        self.assertEqual(self._run(self._argv("verify"))[0], 1)

    def test_verify_problem_exits_one(self) -> None:
        self._run(self._argv("archive"))
        story = self.fx.corpora / IDS[0] / "story.json"
        story.write_bytes(story.read_bytes() + b" ")
        self.assertEqual(self._run(self._argv("verify"))[0], 1)


@unittest.skipUnless(
    (tool.DEFAULT_ARCHIVE / tool.INDEX_NAME).is_file(),
    "the real checkpoint archive is not present",
)
class RealArchiveTest(unittest.TestCase):
    """The committed archive against the committed evidence and current corpora."""

    def test_real_archive_verifies(self) -> None:
        problems = tool.verify(
            tool.DEFAULT_ARCHIVE,
            tool.DEFAULT_MANIFEST,
            tool.DEFAULT_EVIDENCE,
            tool.DEFAULT_CORPORA,
        )
        self.assertEqual(problems, [])

    def test_real_archive_has_the_expected_shape(self) -> None:
        ids = list(tool.load_evidence(tool.DEFAULT_EVIDENCE))
        self.assertEqual(len(ids), 146)
        files = [
            tool.DEFAULT_ARCHIVE / i / archived
            for i in ids
            for _k, _s, archived in tool.KINDS
        ]
        self.assertEqual(len(files), 292)
        self.assertTrue(all(f.is_file() for f in files))

    def test_no_archived_path_is_ignored_by_git(self) -> None:
        ids = list(tool.load_evidence(tool.DEFAULT_EVIDENCE))
        paths = [
            str((tool.DEFAULT_ARCHIVE / i / archived).relative_to(tool.REPO_ROOT))
            for i in ids
            for _k, _s, archived in tool.KINDS
        ]
        try:
            result = subprocess.run(
                ["git", "check-ignore", "--stdin"],
                input="\n".join(paths),
                capture_output=True,
                text=True,
                cwd=tool.REPO_ROOT,
                check=False,
            )
        except FileNotFoundError:
            self.skipTest("git is not available")
        if result.returncode not in (0, 1):
            self.skipTest(f"git check-ignore unavailable: {result.stderr.strip()}")
        # Exit 1 means no path is ignored.
        self.assertEqual(result.returncode, 1, result.stdout)


if __name__ == "__main__":
    unittest.main()
