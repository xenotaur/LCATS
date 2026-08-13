"""Tests for experiments/04_genre_census/run_census.py local endpoint wiring."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest

from unittest.mock import patch


def _load_run_census():
    repo_root = pathlib.Path(__file__).resolve().parents[3]
    module_path = repo_root / "experiments" / "04_genre_census" / "run_census.py"
    spec = importlib.util.spec_from_file_location("run_census_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


run_census = _load_run_census()


class TestRunCensusLocalEndpoint(unittest.TestCase):
    def test_build_backend_passes_base_url_to_openai_backend(self):
        with patch("lcats.llm.openai_backend.OpenAIBackend") as mock_backend:
            backend, model = run_census._build_backend(
                "openai", "gpt-oss:20b", "http://localhost:11434/v1"
            )

        self.assertIs(backend, mock_backend.return_value)
        self.assertEqual(model, "gpt-oss:20b")
        mock_backend.assert_called_once_with(
            api_key="ollama", base_url="http://localhost:11434/v1"
        )

    def test_build_backend_does_not_use_ollama_key_for_remote_base_url(self):
        with patch("lcats.llm.openai_backend.OpenAIBackend") as mock_backend:
            backend, model = run_census._build_backend(
                "openai", "gpt-4o", "https://example.test/v1"
            )

        self.assertIs(backend, mock_backend.return_value)
        self.assertEqual(model, "gpt-4o")
        mock_backend.assert_called_once_with(base_url="https://example.test/v1")

    def test_build_backend_rejects_base_url_for_anthropic(self):
        with self.assertRaisesRegex(ValueError, "--base-url"):
            run_census._build_backend(
                "anthropic", "claude-opus-4-8", "http://localhost:11434/v1"
            )

    def test_fingerprint_includes_base_url(self):
        remote = run_census._fingerprint("gpt-oss:20b", "openai", "story", None)
        local = run_census._fingerprint(
            "gpt-oss:20b", "openai", "story", "http://localhost:11434/v1"
        )

        self.assertNotIn("base_url", remote)
        self.assertEqual(local["base_url"], "http://localhost:11434/v1")
        self.assertNotEqual(remote, local)

    def test_local_endpoint_cost_is_zero(self):
        cost = run_census._estimate_cost_usd(
            "gpt-oss:20b",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            is_local_endpoint=True,
        )

        self.assertEqual(cost, 0.0)

    def test_local_base_url_detects_only_loopback_hosts(self):
        self.assertTrue(run_census._is_local_base_url("http://localhost:11434/v1"))
        self.assertTrue(run_census._is_local_base_url("http://127.0.0.1:11434/v1"))
        self.assertFalse(run_census._is_local_base_url("https://example.test/v1"))
        self.assertFalse(run_census._is_local_base_url(None))

    def test_local_output_prefix_is_model_and_endpoint_scoped(self):
        self.assertEqual(
            run_census._output_prefix(
                "sample", "gpt-oss:20b", "http://localhost:11434/v1", False
            ),
            "census_gpt_oss_20b_http_localhost_11434_v1_sample",
        )
        self.assertEqual(
            run_census._output_prefix(
                "sample", "gpt-oss:20b", "http://localhost:11434/v1", True
            ),
            "census_gpt_oss_20b_http_localhost_11434_v1_dry_run_sample",
        )

    def test_output_prefix_distinguishes_endpoint_urls(self):
        self.assertNotEqual(
            run_census._output_prefix(
                "sample", "gpt-oss:20b", "http://localhost:11434/v1", False
            ),
            run_census._output_prefix(
                "sample", "gpt-oss:20b", "http://127.0.0.1:11434/v1", False
            ),
        )
        self.assertNotEqual(
            run_census._output_prefix(
                "sample", "gpt-oss:20b", "https://example.test/v1", False
            ),
            run_census._output_prefix(
                "sample", "gpt-oss:20b", "https://other.example/v1", False
            ),
        )

    def test_fresh_metered_call_count_excludes_cached_records(self):
        records = [
            {"from_cache": False, "input_tokens": 10, "output_tokens": 1},
            {"from_cache": True, "input_tokens": 10, "output_tokens": 1},
            {"from_cache": False, "input_tokens": 0, "output_tokens": 0},
        ]

        self.assertEqual(run_census._fresh_metered_call_count(records), 1)

    def test_normalize_detected_genre_alias_preserves_raw_value(self):
        record = {"detected_genre": "science_fiction"}

        normalized = run_census._normalize_record_detected_genre(record)

        self.assertIs(normalized, record)
        self.assertEqual(record["detected_genre"], "science fiction")
        self.assertEqual(record["detected_genre_raw"], "science_fiction")
        self.assertTrue(record["detected_genre_normalized"])

    def test_summarize_counts_detected_genre_aliases_as_canonical(self):
        summary = run_census.summarize(
            [
                {
                    "story_id": "a",
                    "detected_genre": "science_fiction",
                    "detected_genre_normalized": True,
                    "input_tokens": 1,
                    "output_tokens": 1,
                    "estimated_cost_usd": 0.0,
                    "elapsed_seconds": 0.0,
                }
            ]
        )

        self.assertEqual(summary["genre_counts"]["science fiction"], 1)
        self.assertNotIn("science_fiction", summary["genre_counts"])
        self.assertEqual(summary["detected_genre_normalized_count"], 1)

    def test_compare_detected_genres_reports_disagreements_by_story(self):
        candidate = [
            {"story_id": "a", "detected_genre": "science fiction"},
            {"story_id": "b", "detected_genre": "horror"},
            {"story_id": "c", "detected_genre": "fantasy"},
        ]
        reference = [
            {"story_id": "a", "detected_genre": "science fiction"},
            {"story_id": "b", "detected_genre": "mystery"},
            {"story_id": "d", "detected_genre": "humor"},
        ]

        comparison = run_census._compare_detected_genres(candidate, reference)

        self.assertEqual(comparison["common_story_count"], 2)
        self.assertEqual(comparison["detected_genre_exact_matches"], 1)
        self.assertEqual(comparison["missing_from_candidate"], ["d"])
        self.assertEqual(comparison["extra_in_candidate"], ["c"])
        self.assertEqual(
            comparison["detected_genre_disagreements"],
            [
                {
                    "story_id": "b",
                    "reference_detected_genre": "mystery",
                    "candidate_detected_genre": "horror",
                }
            ],
        )

    def test_compare_detected_genres_normalizes_aliases(self):
        comparison = run_census._compare_detected_genres(
            [{"story_id": "a", "detected_genre": "science_fiction"}],
            [{"story_id": "a", "detected_genre": "science fiction"}],
        )

        self.assertEqual(comparison["detected_genre_exact_matches"], 1)
        self.assertEqual(comparison["detected_genre_disagreements"], [])

    def test_add_reference_comparison_omits_malformed_reference(self):
        summary = {}
        records = [{"story_id": "a", "detected_genre": "science fiction"}]
        with tempfile.TemporaryDirectory() as tmp:
            reference_path = pathlib.Path(tmp) / "census_sample_stories.jsonl"
            reference_path.write_text("{not json}\n", encoding="utf-8")

            with patch("sys.stderr"):
                run_census._add_reference_comparison(summary, records, reference_path)

        self.assertNotIn("reference_comparison", summary)
        self.assertIn("reference_comparison_error", summary)

    def test_add_reference_comparison_records_valid_reference(self):
        summary = {}
        records = [{"story_id": "a", "detected_genre": "science fiction"}]
        with tempfile.TemporaryDirectory() as tmp:
            reference_path = pathlib.Path(tmp) / "census_sample_stories.jsonl"
            reference_path.write_text(
                json.dumps({"story_id": "a", "detected_genre": "horror"}) + "\n",
                encoding="utf-8",
            )

            run_census._add_reference_comparison(summary, records, reference_path)

        self.assertEqual(summary["reference_comparison"]["common_story_count"], 1)
        self.assertEqual(
            summary["reference_comparison"]["detected_genre_disagreements"],
            [
                {
                    "story_id": "a",
                    "reference_detected_genre": "horror",
                    "candidate_detected_genre": "science fiction",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
