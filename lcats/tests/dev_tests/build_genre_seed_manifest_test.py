"""Tests for tools/build_genre_seed_manifest.py (WI-PROMOTE-0112)."""

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from lcats.analysis.corpus import genre_sidecar

_TOOL_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / "tools"
    / "build_genre_seed_manifest.py"
)
_SPEC = importlib.util.spec_from_file_location("build_genre_seed_manifest", _TOOL_PATH)
seed = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(seed)

EVIDENCE = seed.DEFAULT_EVIDENCE
CORPORA = EVIDENCE.parents[4] / "corpora"
EXPECTED_COUNT = 146


def _record(lcats_id, *cache_paths):
    return {
        "schema_version": "genre-sidecar-v1",
        "lcats_id": lcats_id,
        "story_path": f"{lcats_id}/story.json",
        "assessments": [
            (
                {"assessment_id": f"a{i}", "provenance": {"cache_db_path": p}}
                if p is not None
                else {"assessment_id": f"a{i}"}
            )
            for i, p in enumerate(cache_paths)
        ],
    }


def _valid_record(lcats_id, cache_path="/Users/x/cache/gutenbergindex.db"):
    """A genre-sidecar-v1 record that passes the real validator.

    Derived from a real evidence record so it can never drift from the schema.
    """
    record = copy.deepcopy(seed.load_evidence_records(EVIDENCE)[0])
    record["lcats_id"] = lcats_id
    record["story_path"] = f"{lcats_id}/story.json"
    for assessment in record["assessments"]:
        provenance = assessment.get("provenance")
        if isinstance(provenance, dict) and "cache_db_path" in provenance:
            provenance["cache_db_path"] = cache_path
    return record


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RealEvidenceTest(unittest.TestCase):
    """Behavior against the tracked evidence file and the current corpora/."""

    @classmethod
    def setUpClass(cls):
        cls.evidence = seed.load_evidence_records(EVIDENCE)
        cls.records, cls.changed = seed.build_seed_records(cls.evidence)

    def test_builds_exactly_the_expected_record_count(self):
        self.assertEqual(len(self.evidence), EXPECTED_COUNT)
        self.assertEqual(len(self.records), EXPECTED_COUNT)

    def test_envelope_shape(self):
        for record in self.records:
            self.assertEqual(set(record), {"lcats_id", "payload"})
            self.assertEqual(record["lcats_id"], record["payload"]["lcats_id"])

    def test_no_absolute_cache_db_path_remains(self):
        for record in self.records:
            for assessment in record["payload"]["assessments"]:
                value = (assessment.get("provenance") or {}).get("cache_db_path")
                if isinstance(value, str):
                    self.assertNotIn("/", value, record["lcats_id"])
                    self.assertNotIn("\\", value, record["lcats_id"])
        self.assertEqual(self.changed, EXPECTED_COUNT)

    def test_every_payload_validates(self):
        for record in self.records:
            result = genre_sidecar.validate_sidecar(record["payload"])
            self.assertTrue(result.valid, record["lcats_id"])

    def test_lcats_ids_are_unique(self):
        ids = [record["lcats_id"] for record in self.records]
        self.assertEqual(len(ids), len(set(ids)))

    def test_payloads_equal_current_corpora_sidecars(self):
        """Drift guard: the seed must reproduce what corpora/ holds today."""
        self.assertTrue(CORPORA.is_dir(), f"corpora/ not found at {CORPORA}")
        for record in self.records:
            sidecar_path = CORPORA / record["lcats_id"] / "genre.json"
            self.assertTrue(sidecar_path.is_file(), record["lcats_id"])
            current = json.loads(sidecar_path.read_text(encoding="utf-8"))
            self.assertEqual(record["payload"], current, record["lcats_id"])

    def test_main_leaves_evidence_unmodified(self):
        before = _sha(EVIDENCE)
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "seed.jsonl"
            code = seed.main(
                ["--manifest-out", str(out), "--expect-count", str(EXPECTED_COUNT)]
            )
            lines = out.read_text(encoding="utf-8").splitlines()
        self.assertEqual(code, 0)
        self.assertEqual(len(lines), EXPECTED_COUNT)
        self.assertEqual(_sha(EVIDENCE), before)


class SyntheticEvidenceTest(unittest.TestCase):
    def test_sanitizes_posix_and_windows_paths(self):
        evidence = [
            _record("c/one", "/Users/x/cache/gutenbergindex.db"),
            _record("c/two", "C:\\Users\\x\\cache\\gutenbergindex.db"),
        ]
        records, changed = seed.build_seed_records(evidence)
        self.assertEqual(changed, 2)
        for record in records:
            value = record["payload"]["assessments"][0]["provenance"]["cache_db_path"]
            self.assertEqual(value, "gutenbergindex.db")

    def test_every_record_is_emitted_even_if_already_clean(self):
        evidence = [_record("c/one", "gutenbergindex.db"), _record("c/two", None)]
        records, changed = seed.build_seed_records(evidence)
        self.assertEqual(changed, 0)
        self.assertEqual([r["lcats_id"] for r in records], ["c/one", "c/two"])

    def test_idempotent_on_already_sanitized_input(self):
        evidence = [_record("c/one", "/a/b/c.db")]
        first, _ = seed.build_seed_records(evidence)
        second, changed = seed.build_seed_records([first[0]["payload"]])
        self.assertEqual(changed, 0)
        self.assertEqual(second[0]["payload"], first[0]["payload"])

    def test_does_not_mutate_input_records(self):
        evidence = [_record("c/one", "/a/b/c.db")]
        snapshot = json.loads(json.dumps(evidence))
        seed.build_seed_records(evidence)
        self.assertEqual(evidence, snapshot)

    def test_blank_lines_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "e.jsonl"
            path.write_text(
                json.dumps(_record("c/one", "x")) + "\n\n   \n", encoding="utf-8"
            )
            self.assertEqual(len(seed.load_evidence_records(path)), 1)

    def _run(self, text, *extra):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = pathlib.Path(tmp) / "e.jsonl"
            evidence.write_text(text, encoding="utf-8")
            out = pathlib.Path(tmp) / "seed.jsonl"
            code = seed.main(
                ["--evidence", str(evidence), "--manifest-out", str(out), *extra]
            )
            return code, out.exists()

    def test_malformed_json_fails_and_writes_nothing(self):
        good = json.dumps(_record("c/one", "/a/b.db")) + "\n"
        code, wrote = self._run(good + "{ not json\n")
        self.assertEqual(code, 1)
        self.assertFalse(wrote)

    def test_non_object_record_fails(self):
        code, wrote = self._run("[1, 2]\n")
        self.assertEqual(code, 1)
        self.assertFalse(wrote)

    def test_missing_lcats_id_fails(self):
        row = _record("c/one", "x")
        del row["lcats_id"]
        code, wrote = self._run(json.dumps(row) + "\n")
        self.assertEqual(code, 1)
        self.assertFalse(wrote)

    def test_duplicate_lcats_id_fails(self):
        row = json.dumps(_record("c/one", "x")) + "\n"
        code, wrote = self._run(row + row)
        self.assertEqual(code, 1)
        self.assertFalse(wrote)

    def test_expect_count_mismatch_fails_and_writes_nothing(self):
        row = json.dumps(_record("c/one", "x")) + "\n"
        code, wrote = self._run(row, "--expect-count", "2")
        self.assertEqual(code, 1)
        self.assertFalse(wrote)

    def test_expect_count_match_succeeds(self):
        row = json.dumps(_valid_record("c/one")) + "\n"
        code, wrote = self._run(row, "--expect-count", "1")
        self.assertEqual(code, 0)
        self.assertTrue(wrote)

    def test_missing_evidence_file_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = seed.main(
                [
                    "--evidence",
                    str(pathlib.Path(tmp) / "nope.jsonl"),
                    "--manifest-out",
                    str(pathlib.Path(tmp) / "seed.jsonl"),
                ]
            )
        self.assertEqual(code, 2)

    def test_unwritable_manifest_location_exits_2_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = pathlib.Path(tmp) / "e.jsonl"
            evidence.write_text(
                json.dumps(_valid_record("c/one")) + "\n", encoding="utf-8"
            )
            out = pathlib.Path(tmp) / "no_such_dir" / "seed.jsonl"
            code = seed.main(["--evidence", str(evidence), "--manifest-out", str(out)])
            self.assertEqual(code, 2)
            self.assertFalse(out.parent.exists())

    def test_no_temp_files_left_behind_after_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = pathlib.Path(tmp) / "e.jsonl"
            evidence.write_text(
                json.dumps(_valid_record("c/one")) + "\n", encoding="utf-8"
            )
            out = pathlib.Path(tmp) / "seed.jsonl"
            self.assertEqual(
                seed.main(["--evidence", str(evidence), "--manifest-out", str(out)]), 0
            )
            self.assertEqual(
                sorted(p.name for p in pathlib.Path(tmp).iterdir()),
                ["e.jsonl", "seed.jsonl"],
            )

    def _run_capture(self, text):
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            evidence = pathlib.Path(tmp) / "e.jsonl"
            evidence.write_text(text, encoding="utf-8")
            out = pathlib.Path(tmp) / "seed.jsonl"
            with contextlib.redirect_stderr(err):
                code = seed.main(
                    ["--evidence", str(evidence), "--manifest-out", str(out)]
                )
            return code, out.exists(), err.getvalue()

    def test_invalid_payload_fails_and_writes_nothing(self):
        code, wrote, err = self._run_capture('{"lcats_id": "c/story"}\n')
        self.assertEqual(code, 1)
        self.assertFalse(wrote)
        self.assertIn("c/story", err)
        self.assertIn("nothing written", err)

    def test_one_invalid_payload_among_valid_ones_blocks_the_whole_manifest(self):
        rows = [
            json.dumps(_valid_record("c/one")),
            json.dumps({"lcats_id": "c/bad"}),
            json.dumps(_valid_record("c/two")),
        ]
        code, wrote, err = self._run_capture("\n".join(rows) + "\n")
        self.assertEqual(code, 1)
        self.assertFalse(wrote)
        self.assertIn("1 of 3", err)
        self.assertIn("c/bad", err)
        self.assertNotIn("c/one:", err)

    def test_many_invalid_payloads_are_summarized(self):
        rows = [json.dumps({"lcats_id": f"c/bad{i}"}) for i in range(13)]
        code, wrote, err = self._run_capture("\n".join(rows) + "\n")
        self.assertEqual(code, 1)
        self.assertFalse(wrote)
        self.assertIn("13 of 13", err)
        self.assertIn("and 3 more", err)

    def test_find_invalid_payloads_accepts_valid_and_flags_invalid(self):
        good = {"lcats_id": "c/one", "payload": _valid_record("c/one")}
        bad = {"lcats_id": "c/bad", "payload": {"lcats_id": "c/bad"}}
        self.assertEqual(seed.find_invalid_payloads([good]), [])
        problems = seed.find_invalid_payloads([good, bad])
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("c/bad: "))

    def test_unreadable_evidence_exits_2_without_traceback(self):
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            evidence = pathlib.Path(tmp) / "e.jsonl"
            evidence.write_text("{}\n", encoding="utf-8")
            out = pathlib.Path(tmp) / "seed.jsonl"
            with (
                mock.patch.object(
                    seed, "load_evidence_records", side_effect=PermissionError("denied")
                ),
                contextlib.redirect_stderr(err),
            ):
                code = seed.main(
                    ["--evidence", str(evidence), "--manifest-out", str(out)]
                )
            wrote = out.exists()
        self.assertEqual(code, 2)
        self.assertFalse(wrote)
        self.assertIn("cannot read", err.getvalue())

    def _main_with(self, out, env_overrides=None):
        """Run main() against a one-record evidence file; return (code, stderr)."""
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            evidence = pathlib.Path(tmp) / "e.jsonl"
            evidence.write_text(
                json.dumps(_valid_record("c/one")) + "\n", encoding="utf-8"
            )
            with (
                mock.patch.dict(os.environ, env_overrides or {}),
                contextlib.redirect_stderr(err),
            ):
                code = seed.main(
                    ["--evidence", str(evidence), "--manifest-out", str(out)]
                )
        return code, err.getvalue()

    def test_output_inside_repo_corpora_is_refused(self):
        out = seed._REPO_ROOT / "corpora" / "zz_no_such_collection" / "seed.jsonl"
        code, err = self._main_with(out)
        self.assertEqual(code, 2)
        self.assertIn("protected", err)
        self.assertFalse(out.parent.exists())

    def test_output_inside_repo_lcats_data_is_refused(self):
        out = seed._REPO_ROOT / "lcats" / "data" / "zz_no_such" / "seed.jsonl"
        code, err = self._main_with(out)
        self.assertEqual(code, 2)
        self.assertIn("protected", err)
        self.assertFalse(out.parent.exists())

    def test_output_inside_configured_roots_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            corpora, data = tmp / "cc", tmp / "dd"
            corpora.mkdir()
            data.mkdir()
            overrides = {
                "LCATS_CORPORA_DIR": str(corpora),
                "LCATS_DATA_DIR": str(data),
            }
            for root in (corpora, data):
                code, err = self._main_with(root / "seed.jsonl", overrides)
                self.assertEqual(code, 2, root)
                self.assertIn("protected", err)
                self.assertFalse((root / "seed.jsonl").exists())

    def test_symlinked_parent_into_protected_tree_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            corpora = tmp / "cc"
            corpora.mkdir()
            link = tmp / "link"
            link.symlink_to(corpora, target_is_directory=True)
            code, err = self._main_with(
                link / "seed.jsonl", {"LCATS_CORPORA_DIR": str(corpora)}
            )
            self.assertEqual(code, 2)
            self.assertIn("protected", err)
            self.assertFalse((corpora / "seed.jsonl").exists())

    def test_existing_file_in_protected_tree_is_left_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            sidecar = tmp / "cc" / "s" / "genre.json"
            sidecar.parent.mkdir(parents=True)
            sidecar.write_text('{"keep": "me"}', encoding="utf-8")
            code, _ = self._main_with(sidecar, {"LCATS_CORPORA_DIR": str(tmp / "cc")})
            self.assertEqual(code, 2)
            self.assertEqual(sidecar.read_text(encoding="utf-8"), '{"keep": "me"}')

    def test_miscased_path_into_protected_tree_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            corpora = tmp / "cc"
            corpora.mkdir()
            if not (tmp / "CC").exists():
                self.skipTest("filesystem is case-sensitive; nothing to bypass")
            code, err = self._main_with(
                tmp / "CC" / "seed.jsonl", {"LCATS_CORPORA_DIR": str(corpora)}
            )
            self.assertEqual(code, 2)
            self.assertIn("protected", err)
            self.assertEqual(list(corpora.iterdir()), [])

    def test_nonexistent_configured_root_still_protects_by_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            root = tmp / "not_created_yet"
            code, err = self._main_with(
                root / "seed.jsonl", {"LCATS_DATA_DIR": str(root)}
            )
            self.assertEqual(code, 2)
            self.assertIn("protected", err)
            self.assertFalse(root.exists())

    def test_same_or_inside_by_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            root = tmp / "cc"
            (root / "s").mkdir(parents=True)
            self.assertTrue(seed._same_or_inside_by_identity(root, root))
            self.assertTrue(
                seed._same_or_inside_by_identity(root / "s" / "x" / "y.jsonl", root)
            )
            self.assertFalse(seed._same_or_inside_by_identity(tmp / "other", root))
            self.assertFalse(
                seed._same_or_inside_by_identity(root / "s", tmp / "missing_root")
            )

    def test_normal_output_path_is_not_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(
                seed.find_protected_tree(pathlib.Path(tmp) / "seed.jsonl")
            )

    def test_refuses_to_overwrite_the_evidence_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = pathlib.Path(tmp) / "e.jsonl"
            text = json.dumps(_record("c/one", "x")) + "\n"
            evidence.write_text(text, encoding="utf-8")
            code = seed.main(
                ["--evidence", str(evidence), "--manifest-out", str(evidence)]
            )
            self.assertEqual(evidence.read_text(encoding="utf-8"), text)
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
