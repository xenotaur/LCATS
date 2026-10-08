"""Tests for tools/build_genre_seed_manifest.py (WI-PROMOTE-0112)."""

import hashlib
import importlib.util
import json
import pathlib
import tempfile
import unittest

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
        row = json.dumps(_record("c/one", "x")) + "\n"
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
                json.dumps(_record("c/one", "x")) + "\n", encoding="utf-8"
            )
            out = pathlib.Path(tmp) / "no_such_dir" / "seed.jsonl"
            code = seed.main(["--evidence", str(evidence), "--manifest-out", str(out)])
            self.assertEqual(code, 2)
            self.assertFalse(out.parent.exists())

    def test_no_temp_files_left_behind_after_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = pathlib.Path(tmp) / "e.jsonl"
            evidence.write_text(
                json.dumps(_record("c/one", "x")) + "\n", encoding="utf-8"
            )
            out = pathlib.Path(tmp) / "seed.jsonl"
            self.assertEqual(
                seed.main(["--evidence", str(evidence), "--manifest-out", str(out)]), 0
            )
            self.assertEqual(
                sorted(p.name for p in pathlib.Path(tmp).iterdir()),
                ["e.jsonl", "seed.jsonl"],
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
