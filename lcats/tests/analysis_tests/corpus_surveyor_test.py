"""Unit tests for lcats.analysis.corpus_surveyor."""

import json
import numbers
import pathlib
import unittest
from unittest import mock

import tiktoken

from lcats import test_utils
from lcats.analysis import corpus_surveyor


class TestComputeCorpusStats(test_utils.TestCaseWithData):
    """Unit tests for corpus_surveyor.compute_corpus_stats."""

    def setUp(self):
        super().setUp()

        # Corpus root in the temp dir
        self.root = pathlib.Path(self.test_temp_dir) / "data"
        (self.root / "lovecraft").mkdir(parents=True, exist_ok=True)
        (self.root / "wilde").mkdir(parents=True, exist_ok=True)
        (self.root / "cache" / "gutenberg").mkdir(
            parents=True, exist_ok=True
        )  # realism

        def write_json(relpath: str, payload: dict) -> pathlib.Path:
            p = self.root / pathlib.Path(relpath)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(payload), encoding="utf-8")
            return p

        # 1) story1: title + authors list; body plain text
        self.p1 = write_json(
            "lovecraft/story1.json",
            {
                "name": "Alpha Tale",
                "author": ["Alice", "Bob"],
                "body": "One two three four",
                "metadata": {},
            },
        )

        # 2) story2: duplicate of story1 (different case/whitespace & author order)
        self.p2 = write_json(
            "lovecraft/story2.json",
            {
                "name": "  alpha   tale ",
                "author": ["bob", "ALICE"],
                "body": "One two three four",
                "metadata": {},
            },
        )

        # 3) story3: different title; authors as a string
        self.p3 = write_json(
            "wilde/story3.json",
            {
                "name": "Beta",
                "author": "Alice",
                "body": "Hi",
                "metadata": {},
            },
        )

        # 4) story4: title from metadata.name; no authors -> excluded from author_stats
        self.p4 = write_json(
            "wilde/story4.json",
            {
                "metadata": {"name": "Gamma"},
                "body": "X Y",
            },
        )

        # 5) story5: bytes-literal body; one author overlaps with story1
        self.p5 = write_json(
            "lovecraft/story5.json",
            {
                "name": "Delta",
                "author": ["Bob"],
                "body": "b'Z z z'",
            },
        )

        self.paths = [self.p1, self.p2, self.p3, self.p4, self.p5]

    def _preferred_encoder(self):
        """Mirror survey's preference: o200k_base -> cl100k_base -> gpt-4 fallback."""
        enc = None
        for name in ("o200k_base", "cl100k_base"):
            try:
                enc = tiktoken.get_encoding(name)
                break
            except Exception:
                continue
        if enc is None:
            enc = tiktoken.encoding_for_model("gpt-4")
        return enc

    def test_basic_aggregation_with_dedupe(self):
        """Deduplicate duplicate stories; aggregate author/story stats correctly."""
        story_stats, author_stats = corpus_surveyor.compute_corpus_stats(
            self.paths, dedupe=True
        )

        # Story frame has expected columns
        expected_story_cols = {
            "path",
            "story_id",
            "title",
            "authors",
            "n_authors",
            "title_words",
            "title_chars",
            "title_tokens",
            "body_words",
            "body_chars",
            "body_tokens",
        }
        self.assertTrue(expected_story_cols.issubset(set(story_stats.columns)))

        # Duplicate p2 pruned -> 4 unique stories
        self.assertEqual(len(story_stats), 4)

        # Validate per-story metrics for p1
        s1 = story_stats[story_stats["path"] == str(self.p1)].iloc[0]
        self.assertEqual(s1["title"], "Alpha Tale")
        self.assertEqual(s1["title_words"], 2)
        self.assertEqual(s1["title_chars"], len("Alpha Tale"))
        self.assertEqual(s1["body_words"], 4)  # "One two three four"
        self.assertEqual(s1["body_chars"], len("One two three four"))
        self.assertIsInstance(s1["title_tokens"], numbers.Integral)
        self.assertIsInstance(s1["body_tokens"], numbers.Integral)
        self.assertGreater(s1["title_tokens"], 0)
        self.assertGreater(s1["body_tokens"], 0)

        # Title fallback from metadata.name (p4)
        s4 = story_stats[story_stats["path"] == str(self.p4)].iloc[0]
        self.assertEqual(s4["title"], "Gamma")

        # Author aggregation frame
        expected_author_cols = {
            "author",
            "stories",
            "body_words",
            "body_chars",
            "body_tokens",
        }
        self.assertTrue(expected_author_cols.issubset(set(author_stats.columns)))

        # Alice: story1 + story3
        row_alice = author_stats[author_stats["author"] == "Alice"].iloc[0]
        self.assertEqual(row_alice["stories"], 2)
        self.assertEqual(row_alice["body_words"], 4 + 1)  # 4 (p1) + 1 (p3)
        self.assertEqual(row_alice["body_chars"], len("One two three four") + len("Hi"))
        self.assertGreater(row_alice["body_tokens"], 0)

        # Bob: story1 + story5; p5 body "b'Z z z'" -> "Z z z"
        row_bob = author_stats[author_stats["author"] == "Bob"].iloc[0]
        self.assertEqual(row_bob["stories"], 2)
        self.assertEqual(row_bob["body_words"], 4 + 3)
        self.assertEqual(
            row_bob["body_chars"], len("One two three four") + len("Z z z")
        )
        self.assertGreater(row_bob["body_tokens"], 0)

        # No anonymous authors in author_stats
        self.assertTrue((author_stats["author"].str.len() > 0).all())

    def test_dedupe_false_keeps_duplicate_row_but_author_story_counts_stay_unique(self):
        """When dedupe=False, keep duplicates; author 'stories' remains unique by story_id."""
        story_stats, author_stats = corpus_surveyor.compute_corpus_stats(
            self.paths, dedupe=False
        )

        # Both p1 and its duplicate p2 should appear now
        self.assertEqual(len(story_stats), 5)
        self.assertIn(str(self.p1), set(story_stats["path"]))
        self.assertIn(str(self.p2), set(story_stats["path"]))

        # 'stories' uses nunique(story_id), so duplicates don't inflate counts
        row_alice = author_stats[author_stats["author"] == "Alice"].iloc[0]
        self.assertEqual(row_alice["stories"], 2)  # still 2: story1 + story3

    def test_token_counts_match_selected_encoder(self):
        """Exact token counts match the encoder preference used by the implementation."""
        enc = self._preferred_encoder()

        story_stats, _ = corpus_surveyor.compute_corpus_stats([self.p3], dedupe=True)
        row = story_stats.iloc[0]

        self.assertEqual(row["title"], "Beta")
        self.assertEqual(
            row["title_tokens"], len(enc.encode("Beta", disallowed_special=()))
        )
        self.assertEqual(
            row["body_tokens"], len(enc.encode("Hi", disallowed_special=()))
        )


class TestFindCorpusStories(test_utils.TestCaseWithData):
    """Unit tests for corpus_surveyor.find_corpus_stories."""

    def setUp(self):
        super().setUp()
        self.root = pathlib.Path(self.test_temp_dir) / "corpus"
        self.root.mkdir()

    def _write(self, relpath):
        p = self.root / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}", encoding="utf-8")
        return p

    def test_finds_json_files(self):
        p = self._write("a/story.json")
        found = corpus_surveyor.find_corpus_stories(self.root)
        self.assertIn(p, found)

    def test_ignores_cache_dir_by_default(self):
        cached = self._write("cache/cached.json")
        found = corpus_surveyor.find_corpus_stories(self.root)
        self.assertNotIn(cached, found)

    def test_custom_ignore_dir_names(self):
        p = self._write("excluded/story.json")
        found = corpus_surveyor.find_corpus_stories(
            self.root, ignore_dir_names=["excluded"]
        )
        self.assertNotIn(p, found)

    def test_returns_sorted_by_default(self):
        self._write("b/b.json")
        self._write("a/a.json")
        found = corpus_surveyor.find_corpus_stories(self.root)
        self.assertEqual(found, sorted(found))

    def test_sort_false_returns_all_files(self):
        self._write("a/a.json")
        self._write("b/b.json")
        found = corpus_surveyor.find_corpus_stories(self.root, sort=False)
        self.assertEqual(len(found), 2)

    def test_raises_if_root_not_found(self):
        with self.assertRaises(FileNotFoundError):
            corpus_surveyor.find_corpus_stories(self.root / "nonexistent")

    def test_raises_if_root_not_directory(self):
        f = self.root / "file.txt"
        f.write_text("x", encoding="utf-8")
        with self.assertRaises(NotADirectoryError):
            corpus_surveyor.find_corpus_stories(f)

    def test_skips_non_json_files(self):
        (self.root / "readme.txt").write_text("hi", encoding="utf-8")
        found = corpus_surveyor.find_corpus_stories(self.root)
        self.assertEqual(found, [])

    def test_ignore_hidden_dirs(self):
        hidden = self._write(".hidden/story.json")
        visible = self._write("visible/story.json")
        found = corpus_surveyor.find_corpus_stories(self.root, ignore_hidden=True)
        self.assertNotIn(hidden, found)
        self.assertIn(visible, found)

    def test_ignore_hidden_files(self):
        hidden = self._write("a/.hidden.json")
        found = corpus_surveyor.find_corpus_stories(self.root, ignore_hidden=True)
        self.assertNotIn(hidden, found)

    def test_empty_corpus_returns_empty_list(self):
        found = corpus_surveyor.find_corpus_stories(self.root)
        self.assertEqual(found, [])

    def test_returns_list_of_paths(self):
        self._write("a/story.json")
        found = corpus_surveyor.find_corpus_stories(self.root)
        self.assertIsInstance(found, list)
        self.assertIsInstance(found[0], pathlib.Path)

    def test_nested_dirs_are_searched(self):
        p = self._write("a/b/c/deep.json")
        found = corpus_surveyor.find_corpus_stories(self.root)
        self.assertIn(p, found)

    def test_ignore_dir_names_case_insensitive(self):
        # "CACHE" should be pruned when ignore set contains "cache"
        cached = self._write("CACHE/story.json")
        found = corpus_surveyor.find_corpus_stories(
            self.root, ignore_dir_names=["cache"]
        )
        self.assertNotIn(cached, found)

    def test_accepts_string_root(self):
        self._write("story.json")
        found = corpus_surveyor.find_corpus_stories(str(self.root))
        self.assertEqual(len(found), 1)


class TestComputeJobDir(test_utils.TestCaseWithData):
    """Unit tests for corpus_surveyor.compute_job_dir."""

    def setUp(self):
        super().setUp()
        self.root = pathlib.Path(self.test_temp_dir)

    def test_with_simple_label(self):
        result = corpus_surveyor.compute_job_dir(self.root, "my_job")
        self.assertEqual(result, self.root / "my_job")

    def test_label_spaces_become_underscores(self):
        result = corpus_surveyor.compute_job_dir(self.root, "my job label")
        self.assertEqual(result.name, "my_job_label")

    def test_label_special_chars_sanitized(self):
        result = corpus_surveyor.compute_job_dir(self.root, "job@!#label")
        self.assertRegex(result.name, r"^[A-Za-z0-9._\-]+$")

    def test_without_label_generates_timestamped_name(self):
        result = corpus_surveyor.compute_job_dir(self.root, None)
        self.assertRegex(result.name, r"^job_\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}$")
        self.assertEqual(result.parent, self.root)

    def test_result_is_under_output_root(self):
        result = corpus_surveyor.compute_job_dir(self.root, "myjob")
        self.assertEqual(result.parent, self.root)

    def test_empty_string_label_generates_timestamped_name(self):
        # Empty string is falsy; should fall through to timestamp branch
        result = corpus_surveyor.compute_job_dir(self.root, "")
        self.assertRegex(result.name, r"^job_\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}$")


class TestProcessFile(test_utils.TestCaseWithData):
    """Unit tests for corpus_surveyor.process_file."""

    def setUp(self):
        super().setUp()
        self.corpus_root = pathlib.Path(self.test_temp_dir) / "corpus"
        self.corpus_root.mkdir()
        self.job_dir = pathlib.Path(self.test_temp_dir) / "job"
        self.job_dir.mkdir()

    def _write_json(self, relpath, data):
        p = self.corpus_root / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def _simple_processor(self, data):
        return {"echo": data}

    def test_returns_processed_status(self):
        in_path = self._write_json("story.json", {"key": "value"})
        result = corpus_surveyor.process_file(
            in_path,
            corpora_root=self.corpus_root,
            job_dir=self.job_dir,
            processor_function=self._simple_processor,
        )
        self.assertEqual(result["status"], "processed")

    def test_output_file_is_written(self):
        in_path = self._write_json("story.json", {"key": "value"})
        result = corpus_surveyor.process_file(
            in_path,
            corpora_root=self.corpus_root,
            job_dir=self.job_dir,
            processor_function=self._simple_processor,
        )
        self.assertTrue(result["output"].exists())

    def test_output_is_valid_json(self):
        in_path = self._write_json("story.json", {"key": "value"})
        result = corpus_surveyor.process_file(
            in_path,
            corpora_root=self.corpus_root,
            job_dir=self.job_dir,
            processor_function=self._simple_processor,
        )
        content = result["output"].read_text(encoding="utf-8")
        parsed = json.loads(content)
        self.assertIsInstance(parsed, dict)

    def test_skips_when_output_exists_and_not_forced(self):
        in_path = self._write_json("story.json", {"key": "value"})
        out_path = self.job_dir / "story.json"
        out_path.write_text("{}", encoding="utf-8")

        called = []

        def counting_processor(data):
            called.append(True)
            return {"result": "x"}

        result = corpus_surveyor.process_file(
            in_path,
            corpora_root=self.corpus_root,
            job_dir=self.job_dir,
            processor_function=counting_processor,
            force=False,
        )
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(called, [])

    def test_force_overwrites_existing_output(self):
        in_path = self._write_json("story.json", {"key": "value"})
        out_path = self.job_dir / "story.json"
        out_path.write_text("{}", encoding="utf-8")

        result = corpus_surveyor.process_file(
            in_path,
            corpora_root=self.corpus_root,
            job_dir=self.job_dir,
            processor_function=self._simple_processor,
            force=True,
        )
        self.assertEqual(result["status"], "processed")

    def test_error_status_on_processor_exception(self):
        in_path = self._write_json("story.json", {"key": "value"})

        def failing_processor(data):
            raise ValueError("deliberate failure")

        result = corpus_surveyor.process_file(
            in_path,
            corpora_root=self.corpus_root,
            job_dir=self.job_dir,
            processor_function=failing_processor,
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("ValueError", result["error"])
        self.assertIn("deliberate failure", result["error"])

    def test_result_has_input_and_output_keys(self):
        in_path = self._write_json("story.json", {"key": "value"})
        result = corpus_surveyor.process_file(
            in_path,
            corpora_root=self.corpus_root,
            job_dir=self.job_dir,
            processor_function=self._simple_processor,
        )
        self.assertIn("input", result)
        self.assertIn("output", result)
        self.assertIn("status", result)
        self.assertIn("error", result)

    def test_file_outside_corpora_root_falls_back_to_filename(self):
        outside = pathlib.Path(self.test_temp_dir) / "outside.json"
        outside.write_text(json.dumps({"key": "value"}), encoding="utf-8")

        result = corpus_surveyor.process_file(
            outside,
            corpora_root=self.corpus_root,
            job_dir=self.job_dir,
            processor_function=self._simple_processor,
        )
        self.assertEqual(result["status"], "processed")
        self.assertEqual(result["output"].name, "outside.json")

    def test_verbose_true_does_not_raise(self):
        in_path = self._write_json("story.json", {"key": "value"})
        # Should not raise; just prints to stdout
        result = corpus_surveyor.process_file(
            in_path,
            corpora_root=self.corpus_root,
            job_dir=self.job_dir,
            processor_function=self._simple_processor,
            verbose=True,
        )
        self.assertEqual(result["status"], "processed")

    def test_verbose_skip_does_not_raise(self):
        in_path = self._write_json("skip_story.json", {"key": "value"})
        out_path = self.job_dir / "skip_story.json"
        out_path.write_text("{}", encoding="utf-8")
        # With verbose=True and output existing, the skip branch prints
        result = corpus_surveyor.process_file(
            in_path,
            corpora_root=self.corpus_root,
            job_dir=self.job_dir,
            processor_function=self._simple_processor,
            force=False,
            verbose=True,
        )
        self.assertEqual(result["status"], "skipped")

    def test_verbose_error_does_not_raise(self):
        in_path = self._write_json("err_story.json", {"key": "value"})

        def failing_processor(data):
            raise RuntimeError("verbose error test")

        result = corpus_surveyor.process_file(
            in_path,
            corpora_root=self.corpus_root,
            job_dir=self.job_dir,
            processor_function=failing_processor,
            verbose=True,
        )
        self.assertEqual(result["status"], "error")

    def test_abort_batch_on_fatal_api_error(self):
        in_path = self._write_json("story.json", {"key": "value"})

        def aborting_processor(data):
            return {
                "api_error": {
                    "should_abort_batch": True,
                    "category": "auth",
                    "code": 401,
                    "message": "Unauthorized",
                }
            }

        result = corpus_surveyor.process_file(
            in_path,
            corpora_root=self.corpus_root,
            job_dir=self.job_dir,
            processor_function=aborting_processor,
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("Fatal API error", result["error"])


class TestProcessFiles(test_utils.TestCaseWithData):
    """Unit tests for corpus_surveyor.process_files."""

    def setUp(self):
        super().setUp()
        self.corpus_root = pathlib.Path(self.test_temp_dir) / "corpus"
        self.corpus_root.mkdir()
        self.output_root = pathlib.Path(self.test_temp_dir) / "output"
        self.output_root.mkdir()

    def _write_json(self, relpath, data):
        p = self.corpus_root / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def _identity_processor(self, data):
        return data

    def test_basic_processing(self):
        p1 = self._write_json("a.json", {"x": 1})
        p2 = self._write_json("b.json", {"x": 2})
        summary = corpus_surveyor.process_files(
            [p1, p2],
            corpora_root=self.corpus_root,
            output_root=self.output_root,
            processor_function=self._identity_processor,
            job_label="test_basic",
        )
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["processed"], 2)
        self.assertEqual(summary["skipped"], 0)
        self.assertEqual(len(summary["errors"]), 0)

    def test_empty_file_list(self):
        summary = corpus_surveyor.process_files(
            [],
            corpora_root=self.corpus_root,
            output_root=self.output_root,
            processor_function=self._identity_processor,
            job_label="empty_job",
        )
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["processed"], 0)
        self.assertEqual(summary["skipped"], 0)

    def test_skips_existing_outputs_when_not_forced(self):
        p1 = self._write_json("story.json", {"x": 1})
        summary1 = corpus_surveyor.process_files(
            [p1],
            corpora_root=self.corpus_root,
            output_root=self.output_root,
            processor_function=self._identity_processor,
            job_label="skip_test",
        )
        self.assertEqual(summary1["processed"], 1)

        summary2 = corpus_surveyor.process_files(
            [p1],
            corpora_root=self.corpus_root,
            output_root=self.output_root,
            processor_function=self._identity_processor,
            job_label="skip_test",
            force=False,
        )
        self.assertEqual(summary2["skipped"], 1)

    def test_force_reprocesses_existing_outputs(self):
        p1 = self._write_json("story.json", {"x": 1})
        corpus_surveyor.process_files(
            [p1],
            corpora_root=self.corpus_root,
            output_root=self.output_root,
            processor_function=self._identity_processor,
            job_label="force_test",
        )
        summary = corpus_surveyor.process_files(
            [p1],
            corpora_root=self.corpus_root,
            output_root=self.output_root,
            processor_function=self._identity_processor,
            job_label="force_test",
            force=True,
        )
        self.assertEqual(summary["processed"], 1)
        self.assertEqual(summary["skipped"], 0)

    def test_summary_contains_expected_keys(self):
        p1 = self._write_json("story.json", {"x": 1})
        summary = corpus_surveyor.process_files(
            [p1],
            corpora_root=self.corpus_root,
            output_root=self.output_root,
            processor_function=self._identity_processor,
            job_label="keys_test",
        )
        for key in ("job_dir", "total", "processed", "skipped", "errors", "results"):
            self.assertIn(key, summary)

    def test_errors_are_reported(self):
        p1 = self._write_json("bad.json", {"x": 1})

        def failing_processor(data):
            raise RuntimeError("boom")

        summary = corpus_surveyor.process_files(
            [p1],
            corpora_root=self.corpus_root,
            output_root=self.output_root,
            processor_function=failing_processor,
            job_label="error_test",
        )
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["processed"], 0)
        self.assertEqual(len(summary["errors"]), 1)

    def test_job_dir_created_under_output_root(self):
        p1 = self._write_json("story.json", {"x": 1})
        summary = corpus_surveyor.process_files(
            [p1],
            corpora_root=self.corpus_root,
            output_root=self.output_root,
            processor_function=self._identity_processor,
            job_label="dir_test",
        )
        job_dir = summary["job_dir"].resolve()
        output_root = self.output_root.resolve()
        self.assertTrue(job_dir.is_dir())
        self.assertTrue(job_dir.relative_to(output_root))

    def test_sort_true_processes_files_in_order(self):
        p_b = self._write_json("b.json", {"n": 2})
        p_a = self._write_json("a.json", {"n": 1})
        order = []

        def tracking_processor(data):
            order.append(data["n"])
            return data

        corpus_surveyor.process_files(
            [p_b, p_a],
            corpora_root=self.corpus_root,
            output_root=self.output_root,
            processor_function=tracking_processor,
            job_label="sort_test",
            sort=True,
        )
        self.assertEqual(order, [1, 2])


class TestProcessCorpora(test_utils.TestCaseWithData):
    """Unit tests for corpus_surveyor.process_corpora."""

    def setUp(self):
        super().setUp()
        self.corpus_root = pathlib.Path(self.test_temp_dir) / "corpus"
        self.corpus_root.mkdir()
        self.output_root = pathlib.Path(self.test_temp_dir) / "output"
        self.output_root.mkdir()

    def _write_json(self, relpath, data):
        p = self.corpus_root / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def _identity_processor(self, data):
        return data

    def test_processes_discovered_files(self):
        self._write_json("author/story.json", {"title": "Story", "body": "hello"})
        summary = corpus_surveyor.process_corpora(
            self.corpus_root,
            self.output_root,
            self._identity_processor,
            job_label="corpora_basic",
        )
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["processed"], 1)

    def test_ignores_cache_dir(self):
        self._write_json("author/story.json", {"title": "Story"})
        (self.corpus_root / "cache").mkdir(parents=True, exist_ok=True)
        self._write_json("cache/cached.json", {"title": "Cached"})

        summary = corpus_surveyor.process_corpora(
            self.corpus_root,
            self.output_root,
            self._identity_processor,
            job_label="cache_test",
        )
        self.assertEqual(summary["total"], 1)

    def test_raises_on_missing_corpora_root(self):
        with self.assertRaises(FileNotFoundError):
            corpus_surveyor.process_corpora(
                self.corpus_root / "nonexistent",
                self.output_root,
                self._identity_processor,
            )

    def test_raises_on_non_directory_corpora_root(self):
        f = self.corpus_root / "file.txt"
        f.write_text("x", encoding="utf-8")
        with self.assertRaises(NotADirectoryError):
            corpus_surveyor.process_corpora(
                f,
                self.output_root,
                self._identity_processor,
            )

    def test_summary_contains_expected_keys(self):
        self._write_json("story.json", {"title": "A"})
        summary = corpus_surveyor.process_corpora(
            self.corpus_root,
            self.output_root,
            self._identity_processor,
            job_label="keys_test",
        )
        for key in ("job_dir", "total", "processed", "skipped", "errors", "results"):
            self.assertIn(key, summary)

    def test_empty_corpus_produces_zero_totals(self):
        summary = corpus_surveyor.process_corpora(
            self.corpus_root,
            self.output_root,
            self._identity_processor,
            job_label="empty_corpora",
        )
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["processed"], 0)


class TestComputeCorpusStatsWithMockedEncoder(test_utils.TestCaseWithData):
    """Tests for compute_corpus_stats with a mocked tiktoken encoder."""

    def setUp(self):
        super().setUp()
        self.root = pathlib.Path(self.test_temp_dir) / "data"
        self.root.mkdir()

        def write_json(relpath, payload):
            p = self.root / pathlib.Path(relpath)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(payload), encoding="utf-8")
            return p

        self.p_story = write_json(
            "a/story.json",
            {"name": "My Title", "author": ["Alice"], "body": "Hello world"},
        )
        self.p_noauthor = write_json(
            "b/anon.json",
            {"name": "Anon Story", "body": "Some text"},
        )

        # Mock encoder returns words as tokens (one token per word approximation).
        self._mock_enc = mock.MagicMock()
        self._mock_enc.encode.side_effect = lambda text, **kw: text.split()

    def _run_stats(self, paths, **kwargs):
        with mock.patch(
            "lcats.analysis.story_analysis.get_encoder",
            return_value=self._mock_enc,
        ):
            return corpus_surveyor.compute_corpus_stats(paths, **kwargs)

    def test_returns_two_dataframes(self):
        story_stats, author_stats = self._run_stats([self.p_story])
        import pandas as pd

        self.assertIsInstance(story_stats, pd.DataFrame)
        self.assertIsInstance(author_stats, pd.DataFrame)

    def test_story_stats_columns(self):
        story_stats, _ = self._run_stats([self.p_story])
        expected = {
            "path",
            "story_id",
            "title",
            "authors",
            "n_authors",
            "title_words",
            "title_chars",
            "title_tokens",
            "body_words",
            "body_chars",
            "body_tokens",
        }
        self.assertTrue(expected.issubset(set(story_stats.columns)))

    def test_author_stats_columns(self):
        _, author_stats = self._run_stats([self.p_story])
        expected = {"author", "stories", "body_words", "body_chars", "body_tokens"}
        self.assertTrue(expected.issubset(set(author_stats.columns)))

    def test_word_and_char_counts_are_correct(self):
        story_stats, _ = self._run_stats([self.p_story])
        row = story_stats.iloc[0]
        self.assertEqual(row["title"], "My Title")
        self.assertEqual(row["title_words"], 2)
        self.assertEqual(row["title_chars"], len("My Title"))
        self.assertEqual(row["body_words"], 2)  # "Hello world"
        self.assertEqual(row["body_chars"], len("Hello world"))

    def test_dedupe_removes_duplicate(self):
        root2 = pathlib.Path(self.test_temp_dir) / "data2"
        root2.mkdir()
        p1 = root2 / "orig.json"
        p2 = root2 / "dup.json"
        payload = {"name": "Same Title", "author": ["Bob"], "body": "Text"}
        p1.write_text(json.dumps(payload), encoding="utf-8")
        p2.write_text(json.dumps(payload), encoding="utf-8")

        story_stats, _ = self._run_stats([p1, p2], dedupe=True)
        self.assertEqual(len(story_stats), 1)

    def test_dedupe_false_keeps_duplicates(self):
        root2 = pathlib.Path(self.test_temp_dir) / "data3"
        root2.mkdir()
        p1 = root2 / "orig.json"
        p2 = root2 / "dup.json"
        payload = {"name": "Same Title", "author": ["Bob"], "body": "Text"}
        p1.write_text(json.dumps(payload), encoding="utf-8")
        p2.write_text(json.dumps(payload), encoding="utf-8")

        story_stats, _ = self._run_stats([p1, p2], dedupe=False)
        self.assertEqual(len(story_stats), 2)

    def test_empty_input_returns_empty_frames(self):
        story_stats, author_stats = self._run_stats([])
        self.assertTrue(story_stats.empty)
        self.assertTrue(author_stats.empty)

    def test_anonymous_author_excluded_from_author_stats(self):
        _, author_stats = self._run_stats([self.p_noauthor])
        self.assertTrue(author_stats.empty)

    def test_invalid_json_is_skipped_with_warning(self):
        bad = pathlib.Path(self.test_temp_dir) / "bad.json"
        bad.write_text("not valid json", encoding="utf-8")

        story_stats, _ = self._run_stats([self.p_story, bad])
        # Only the valid file should appear
        self.assertEqual(len(story_stats), 1)

    def test_author_stats_aggregates_multiple_stories(self):
        root2 = pathlib.Path(self.test_temp_dir) / "multi"
        root2.mkdir()
        p1 = root2 / "s1.json"
        p2 = root2 / "s2.json"
        p1.write_text(
            json.dumps({"name": "S1", "author": ["Alice"], "body": "One two"}),
            encoding="utf-8",
        )
        p2.write_text(
            json.dumps({"name": "S2", "author": ["Alice"], "body": "Three"}),
            encoding="utf-8",
        )

        _, author_stats = self._run_stats([p1, p2])
        row = author_stats[author_stats["author"] == "Alice"].iloc[0]
        self.assertEqual(row["stories"], 2)
        self.assertEqual(row["body_words"], 3)  # 2 + 1

    def test_story_id_includes_authors(self):
        story_stats, _ = self._run_stats([self.p_story])
        row = story_stats.iloc[0]
        self.assertIn("alice", row["story_id"])

    def test_n_authors_is_correct(self):
        root2 = pathlib.Path(self.test_temp_dir) / "nauth"
        root2.mkdir()
        p = root2 / "s.json"
        p.write_text(
            json.dumps({"name": "Multi", "author": ["A", "B", "C"], "body": "text"}),
            encoding="utf-8",
        )
        story_stats, _ = self._run_stats([p])
        self.assertEqual(story_stats.iloc[0]["n_authors"], 3)


if __name__ == "__main__":
    unittest.main()
