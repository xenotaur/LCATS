"""Tests for tools/rewrite_genre_cache_db_path.py (WI-GENRE-0109)."""

import importlib.util
import json
import pathlib
import tempfile
import unittest

_TOOL_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / "tools"
    / "rewrite_genre_cache_db_path.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "rewrite_genre_cache_db_path", _TOOL_PATH
)
rewrite = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rewrite)


def _sidecar(*provenances):
    return {
        "schema_version": "genre-sidecar-v1",
        "lcats_id": "c/s",
        "story_path": "c/s/story.json",
        "assessments": [
            (
                {"assessment_id": f"a{i}", "provenance": p}
                if p is not None
                else {"assessment_id": f"a{i}"}
            )
            for i, p in enumerate(provenances)
        ],
    }


class RewriteCacheDbPathTest(unittest.TestCase):
    def test_absolute_posix_path_becomes_basename(self):
        original = _sidecar({"cache_db_path": "/Users/x/proj/cache/gutenbergindex.db"})
        rewritten, changed = rewrite.rewrite_cache_db_path(original)
        self.assertEqual(changed, 1)
        self.assertEqual(
            rewritten["assessments"][0]["provenance"]["cache_db_path"],
            "gutenbergindex.db",
        )

    def test_windows_path_becomes_basename(self):
        original = _sidecar({"cache_db_path": "C:\\Users\\x\\cache\\gutenbergindex.db"})
        rewritten, changed = rewrite.rewrite_cache_db_path(original)
        self.assertEqual(changed, 1)
        self.assertEqual(
            rewritten["assessments"][0]["provenance"]["cache_db_path"],
            "gutenbergindex.db",
        )

    def test_already_basename_is_unchanged(self):
        original = _sidecar({"cache_db_path": "gutenbergindex.db"})
        rewritten, changed = rewrite.rewrite_cache_db_path(original)
        self.assertEqual(changed, 0)
        self.assertEqual(rewritten, original)

    def test_missing_provenance_and_missing_field_are_unchanged(self):
        original = _sidecar(None, {"backend_model": "m"})
        rewritten, changed = rewrite.rewrite_cache_db_path(original)
        self.assertEqual(changed, 0)
        self.assertEqual(rewritten, original)

    def test_only_cache_db_path_changes(self):
        original = _sidecar(
            {"cache_db_path": "/a/b/c.db", "cache_root": "/a/b", "backend": "x"}
        )
        rewritten, _ = rewrite.rewrite_cache_db_path(original)
        expected = json.loads(json.dumps(original))
        expected["assessments"][0]["provenance"]["cache_db_path"] = "c.db"
        self.assertEqual(rewritten, expected)

    def test_does_not_mutate_input(self):
        original = _sidecar({"cache_db_path": "/a/b/c.db"})
        snapshot = json.loads(json.dumps(original))
        rewrite.rewrite_cache_db_path(original)
        self.assertEqual(original, snapshot)

    def test_non_dict_sidecar_shapes_are_tolerated(self):
        for bad in ({}, {"assessments": "x"}, {"assessments": [1, None]}):
            rewritten, changed = rewrite.rewrite_cache_db_path(bad)
            self.assertEqual(changed, 0)
            self.assertEqual(rewritten, bad)

    def test_manifest_records_cover_only_changed_sidecars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for name, path in (("one", "/abs/cache/x.db"), ("two", "x.db")):
                bucket = root / "coll" / name
                bucket.mkdir(parents=True)
                (bucket / "genre.json").write_text(
                    json.dumps(_sidecar({"cache_db_path": path})), encoding="utf-8"
                )
            records, scanned, values = rewrite.build_manifest_records(root)
        self.assertEqual(scanned, 2)
        self.assertEqual(values, 1)
        self.assertEqual([r["lcats_id"] for r in records], ["coll/one"])
        self.assertEqual(
            records[0]["payload"]["assessments"][0]["provenance"]["cache_db_path"],
            "x.db",
        )

    def test_non_genre_files_are_ignored_and_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            genre_bucket = root / "coll" / "one"
            genre_bucket.mkdir(parents=True)
            (genre_bucket / "genre.json").write_text(
                json.dumps(_sidecar({"cache_db_path": "/abs/x.db"})),
                encoding="utf-8",
            )
            other_bucket = root / "coll" / "two"
            other_bucket.mkdir(parents=True)
            broken = other_bucket / "scenes.json"
            broken.write_text("{ not valid json", encoding="utf-8")
            lookalike = other_bucket / "linguistics.json"
            lookalike_text = json.dumps(_sidecar({"cache_db_path": "/abs/y.db"}))
            lookalike.write_text(lookalike_text, encoding="utf-8")
            near_miss = genre_bucket / "genre.json.bak"
            near_miss_text = json.dumps(_sidecar({"cache_db_path": "/abs/z.db"}))
            near_miss.write_text(near_miss_text, encoding="utf-8")

            records, scanned, values = rewrite.build_manifest_records(root)

            self.assertEqual(scanned, 1)
            self.assertEqual(values, 1)
            self.assertEqual([r["lcats_id"] for r in records], ["coll/one"])
            self.assertEqual(broken.read_text(encoding="utf-8"), "{ not valid json")
            self.assertEqual(lookalike.read_text(encoding="utf-8"), lookalike_text)
            self.assertEqual(near_miss.read_text(encoding="utf-8"), near_miss_text)

    def test_main_writes_manifest_and_leaves_corpora_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "corpora"
            bucket = root / "coll" / "one"
            bucket.mkdir(parents=True)
            sidecar_path = bucket / "genre.json"
            before = json.dumps(_sidecar({"cache_db_path": "/abs/x.db"}), indent=2)
            sidecar_path.write_text(before, encoding="utf-8")
            manifest = pathlib.Path(tmp) / "manifest.jsonl"
            code = rewrite.main(
                ["--corpora-dir", str(root), "--manifest-out", str(manifest)]
            )
            self.assertEqual(code, 0)
            self.assertEqual(sidecar_path.read_text(encoding="utf-8"), before)
            lines = manifest.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)

    def test_main_reports_missing_corpora_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = rewrite.main(
                [
                    "--corpora-dir",
                    str(pathlib.Path(tmp) / "nope"),
                    "--manifest-out",
                    str(pathlib.Path(tmp) / "m.jsonl"),
                ]
            )
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
