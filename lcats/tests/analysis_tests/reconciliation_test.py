"""Offline source-identity comparisons with real story bucket files."""

import json
import pathlib
import tempfile
import unittest

from lcats.analysis.corpus import reconciliation


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.left, self.right = self.root / "left", self.root / "right"
        self.left.mkdir()
        self.right.mkdir()

    def story(self, root, bucket, url, *, author=None, title="Title", body="Text"):
        path = root / bucket / "story.json"
        path.parent.mkdir()
        data = {"name": title, "body": body, "metadata": {"url": url}}
        if author is not None:
            data["author"] = author
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_empty_and_one_sided_collections_have_stable_shape(self):
        self.assertEqual(reconciliation.compare_collections(self.left, self.right), [])
        self.story(self.left, "first", "url-a")
        self.story(self.right, "second", "url-b")
        result = reconciliation.compare_collections(self.left, self.right)
        self.assertEqual([row["url"] for row in result], ["url-a", "url-b"])
        self.assertTrue(all(not row["appears_in_both"] for row in result))
        self.assertTrue(all(row["titles_match"] is None for row in result))
        self.assertEqual(result[0]["left"][0]["bucket"], "first")
        json.dumps(result)

    def test_duplicate_sources_remain_visible_without_cartesian_join(self):
        self.story(self.left, "z", "url", author=["One", "Two"])
        self.story(self.left, "a", "url", author=["One", "Two"])
        self.story(self.right, "b", "url", author=["One", "Two"])
        result = reconciliation.compare_collections(self.left, self.right)
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["duplicate_url"])
        self.assertEqual([r["bucket"] for r in result[0]["left"]], ["a", "z"])
        self.assertIsNone(result[0]["authors_match"])
        self.assertEqual(
            result, reconciliation.compare_collections(self.left, self.right)
        )

    def test_missing_and_list_authors_and_body_differences_are_explicit(self):
        left = self.story(self.left, "a", "url", author=["One", "Two"])
        right = self.story(
            self.right, "b", "url", author=["Two", "One"], body="Changed"
        )
        before = {p: p.read_bytes() for p in (left, right)}
        result = reconciliation.compare_collections(self.left, self.right)[0]
        self.assertTrue(result["titles_match"])
        self.assertFalse(result["authors_match"])
        self.assertFalse(result["bodies_match"])
        self.assertEqual({p: p.read_bytes() for p in before}, before)
        self.story(self.left, "missing", "url-missing")
        self.story(self.right, "empty", "url-missing", author=[])
        self.assertFalse(
            reconciliation.compare_collections(self.left, self.right)[1][
                "authors_match"
            ]
        )

    def test_sidecars_are_not_stories_and_invalid_identity_is_not_silently_joined(self):
        path = self.story(self.left, "a", "url")
        (path.parent / "genre.json").write_text("{}")
        self.assertEqual(len(reconciliation.collate_stories(self.left)["url"]), 1)
        path.write_text('{"body": "text", "metadata": {}}')
        with self.assertRaisesRegex(ValueError, "invalid story"):
            reconciliation.collate_stories(self.left)
        with self.assertRaises(NotADirectoryError):
            reconciliation.collate_stories(self.root / "missing")


if __name__ == "__main__":
    unittest.main()
