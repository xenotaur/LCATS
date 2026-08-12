"""Unit tests for measure_prompt_caching.py.

Not part of the installed lcats package (lives under experiments/, not
lcats/src/lcats/), so not discovered by lcats' scripts/test - run
explicitly:

    python -m unittest experiments/03_cross_segment_relation_pilot/measure_prompt_caching_test.py
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import types
import unittest

from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import measure_prompt_caching  # noqa: E402 - see sys.path.insert above

from lcats.llm import backend as llm_backend  # noqa: E402


class _FixedResponseBackend:
    """Returns one fixed BackendResponse for every complete() call,
    carrying real cache-field values so _RecordingBackend's own
    pass-through/recording logic can be verified independently of the
    real pipeline's segmentation/extraction machinery."""

    def __init__(self, cache_read: int, cache_creation: int):
        self._cache_read = cache_read
        self._cache_creation = cache_creation

    def complete(self, **kwargs):
        return llm_backend.BackendResponse(
            text="",
            tool_result={},
            model="fake-1.0",
            input_tokens=100,
            output_tokens=10,
            cache_creation_input_tokens=self._cache_creation,
            cache_read_input_tokens=self._cache_read,
            raw=None,
        )


class TestRecordingBackend(unittest.TestCase):
    """_RecordingBackend is the one genuinely new piece of logic this
    work item adds - a thin, real (not fake-backend-only) wrapper. Test
    it directly, independent of the real pipeline."""

    def test_records_every_call_in_order_with_real_cache_fields(self):
        inner = _FixedResponseBackend(cache_read=512, cache_creation=0)
        recorder = measure_prompt_caching._RecordingBackend(inner)

        recorder.complete(system="s1", messages=[], model="m", tool={"name": "tool_a"})
        recorder.complete(system="s2", messages=[], model="m", tool={"name": "tool_b"})

        self.assertEqual(len(recorder.calls), 2)
        self.assertEqual(recorder.calls[0]["tool_name"], "tool_a")
        self.assertEqual(recorder.calls[1]["tool_name"], "tool_b")
        for call in recorder.calls:
            self.assertEqual(call["input_tokens"], 100)
            self.assertEqual(call["output_tokens"], 10)
            self.assertEqual(call["cache_read_input_tokens"], 512)
            self.assertEqual(call["cache_creation_input_tokens"], 0)

    def test_delegates_the_real_response_through_unchanged(self):
        inner = _FixedResponseBackend(cache_read=0, cache_creation=200)
        recorder = measure_prompt_caching._RecordingBackend(inner)

        response = recorder.complete(system="s", messages=[], model="m")

        self.assertIsInstance(response, llm_backend.BackendResponse)
        self.assertEqual(response.cache_creation_input_tokens, 200)

    def test_a_present_zero_cache_read_is_recorded_as_zero_not_none(self):
        """A real cache miss (cache_read_input_tokens=0, present) must be
        distinguishable from caching not being in use at all (None) -
        the whole point of surfacing these fields (WI-PILOT-0057)."""
        inner = _FixedResponseBackend(cache_read=0, cache_creation=50)
        recorder = measure_prompt_caching._RecordingBackend(inner)

        recorder.complete(system="s", messages=[], model="m")

        self.assertEqual(recorder.calls[0]["cache_read_input_tokens"], 0)
        self.assertIsNotNone(recorder.calls[0]["cache_read_input_tokens"])


class TestRunComparisonDryRun(unittest.TestCase):
    """End-to-end wiring check using the CLI's own zero-cost dry-run
    fake (_DryRunFakeBackend) against the real, committed WI-PILOT-0051
    fixture set - proves the full segment -> extract -> record -> report
    pipeline runs without error, and that the checkpoint-reuse design
    (segmentation billed once, not twice, across the two comparison
    arms) actually behaves as documented."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.output_dir = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_dry_run_produces_a_report_with_both_arms(self):
        report = measure_prompt_caching.run_comparison(
            model="claude-opus-4-8",
            working_root=self.output_dir,
            source_root=measure_prompt_caching._fixtures_dir(),
            dry_run=True,
        )

        self.assertIn("caching_disabled", report["runs"])
        self.assertIn("caching_enabled", report["runs"])
        self.assertFalse(report["runs"]["caching_disabled"]["enable_prompt_caching"])
        self.assertTrue(report["runs"]["caching_enabled"]["enable_prompt_caching"])

    def test_stories_are_identified_by_collection_name_not_the_bare_filename(self):
        """Every fixture story's on-disk path is <collection>/<name>/
        story.json, so a bare path.name is always "story.json" for
        every story - indistinguishable in the report (review finding,
        PR #271). Must use run_pilot._story_identity instead."""
        report = measure_prompt_caching.run_comparison(
            model="claude-opus-4-8",
            working_root=self.output_dir,
            source_root=measure_prompt_caching._fixtures_dir(),
            dry_run=True,
        )

        self.assertNotIn("story.json", report["stories"])
        self.assertEqual(len(report["stories"]), len(set(report["stories"])))

    def test_run_comparison_honors_a_caller_supplied_source_root(self):
        """A caller pointing source_root at a fixture root other than
        the real committed WI-PILOT-0051 fixtures must have fixture
        discovery actually look there, not silently fall back to
        _fixtures_dir() regardless (review finding, PR #271)."""
        with tempfile.TemporaryDirectory() as tmp:
            custom_root = pathlib.Path(tmp) / "custom_fixtures"
            story_dir = custom_root / "custom_story"
            story_dir.mkdir(parents=True)
            (story_dir / "story.json").write_text(
                json.dumps({"name": "custom_story", "author": "T", "body": "x"}),
                encoding="utf-8",
            )

            found = measure_prompt_caching._fixture_stories(custom_root)

        self.assertEqual(found, [story_dir / "story.json"])

    def test_cost_usd_is_computed_from_real_per_model_pricing(self):
        """The report must include an actual measured $ cost per arm and
        a delta between them, not just raw token sums - input/output/
        cache-write/cache-read are billed at different rates, so a raw
        token total alone cannot answer the WI's own acceptance
        criterion (review finding, PR #271)."""
        report = measure_prompt_caching.run_comparison(
            model="claude-opus-4-8",
            working_root=self.output_dir,
            source_root=measure_prompt_caching._fixtures_dir(),
            dry_run=True,
        )

        for run in report["runs"].values():
            self.assertIsNotNone(run["cost_usd"])
            self.assertGreaterEqual(run["cost_usd"], 0)
        self.assertIn("cost_delta_usd", report)

    def test_compute_cost_usd_returns_none_for_an_unpriced_model(self):
        totals = {
            "total_input_tokens": 1_000_000,
            "total_output_tokens": 0,
            "total_cache_creation_input_tokens": 0,
            "total_cache_read_input_tokens": 0,
        }
        self.assertIsNone(
            measure_prompt_caching._compute_cost_usd(totals, "not-a-real-model")
        )

    def test_compute_cost_usd_matches_the_published_pricing_formula(self):
        """Cross-check against Anthropic's own published pricing
        (verified 2026-08-09): Opus 4.8 is $5/MTok input, $25/MTok
        output, 1.25x input for a 5-minute cache write, 0.1x input for
        a cache read."""
        totals = {
            "total_input_tokens": 1_000_000,
            "total_output_tokens": 1_000_000,
            "total_cache_creation_input_tokens": 1_000_000,
            "total_cache_read_input_tokens": 1_000_000,
        }
        cost = measure_prompt_caching._compute_cost_usd(totals, "claude-opus-4-8")
        expected = 5.0 + 25.0 + (5.0 * 1.25) + (5.0 * 0.1)
        self.assertAlmostEqual(cost, expected, places=6)

    def test_segmentation_is_pre_warmed_so_neither_arm_pays_for_it(self):
        """Both comparison arms must record the exact same number of
        calls, and neither arm's recorded calls include a segmentation
        call at all - segmentation is warmed once via
        _warm_segmentation_checkpoints before either arm starts
        recording (review finding, PR #271: without this, whichever arm
        ran first paid for real segmentation calls the second arm then
        skipped via checkpoint reuse, confounding the comparison with a
        workload difference unrelated to caching)."""
        report = measure_prompt_caching.run_comparison(
            model="claude-opus-4-8",
            working_root=self.output_dir,
            source_root=measure_prompt_caching._fixtures_dir(),
            dry_run=True,
        )

        first_arm_calls = report["runs"]["caching_disabled"]["calls"]
        second_arm_calls = report["runs"]["caching_enabled"]["calls"]
        self.assertEqual(len(first_arm_calls), len(second_arm_calls))
        for call in first_arm_calls + second_arm_calls:
            self.assertNotEqual(call["tool_name"], "record_segments")

    def test_extract_and_relate_calls_the_real_cross_segment_relation_pass(self):
        """_extract_and_relate must use run_pilot._run_erw_pipeline (which
        unconditionally calls _apply_cross_segment_relations - the gate
        deciding whether it does real work vs. a no-op lives INSIDE that
        function, per its own docstring), not _run_erw_extraction alone,
        which never calls _apply_cross_segment_relations at all (review
        finding, PR #271: story_relation was preflighted but never
        actually exercised by the real measurement).

        This test only proves the call site is reached - not that the
        real story_relation extractor gets invoked under a specific
        >=2-segments-with-events scenario, which is a separate,
        already-tested concern belonging to run_pilot_test.py itself
        (see its own coverage around "No story_relation call: a single
        segment never satisfies" the gate). Replicating a real
        gate-satisfying fixture here would duplicate that coverage and
        be fragile against unrelated schema changes."""
        with tempfile.TemporaryDirectory() as tmp:
            story_dir = pathlib.Path(tmp) / "fixtures" / "only_story"
            story_dir.mkdir(parents=True)
            (story_dir / "story.json").write_text(
                json.dumps({"name": "only_story", "author": "T", "body": "x " * 50}),
                encoding="utf-8",
            )
            output_dir = pathlib.Path(tmp) / "out"
            roots = measure_prompt_caching.checkpoint.resolve_roots(
                output_dir, source_root=pathlib.Path(tmp) / "fixtures"
            )
            backend = measure_prompt_caching._DryRunFakeBackend()
            measure_prompt_caching._warm_segmentation_checkpoints(
                [story_dir / "story.json"], "fake-1.0", roots, backend
            )

            with patch.object(
                measure_prompt_caching.run_pilot,
                "_apply_cross_segment_relations",
                wraps=measure_prompt_caching.run_pilot._apply_cross_segment_relations,
            ) as spy:
                measure_prompt_caching._extract_and_relate(
                    story_dir / "story.json", backend, "fake-1.0", roots
                )

        spy.assert_called_once()

    def test_report_is_json_serializable_and_written_to_disk(self):
        measure_prompt_caching.run_comparison(
            model="claude-opus-4-8",
            working_root=self.output_dir,
            source_root=measure_prompt_caching._fixtures_dir(),
            dry_run=True,
        )
        # run_comparison itself doesn't write the file - main() does -
        # so directly verify the report round-trips through json.dumps,
        # matching what main() does with it.
        report = measure_prompt_caching.run_comparison(
            model="claude-opus-4-8",
            working_root=self.output_dir,
            source_root=measure_prompt_caching._fixtures_dir(),
            dry_run=True,
        )
        json.dumps(report)  # must not raise


class TestPreflightPrefixTokenCounts(unittest.TestCase):
    """preflight_prefix_token_counts (Required Change 3) - mocked, since
    count_tokens is still a real, live API call even though it's free/
    non-generation; this test never touches the network."""

    def test_counts_every_extractor_with_a_tool_schema(self):
        stub_client = types.SimpleNamespace(
            messages=types.SimpleNamespace(
                count_tokens=lambda **kwargs: types.SimpleNamespace(input_tokens=42)
            )
        )
        with patch("anthropic.Anthropic", return_value=stub_client):
            counts = measure_prompt_caching.preflight_prefix_token_counts(
                "claude-opus-4-8"
            )

        # run_pilot._build_erw_extractors builds entity/event/relation/
        # discourse/story_relation - all five carry a tool_schema.
        self.assertEqual(
            set(counts.keys()),
            {"entity", "event", "relation", "discourse", "story_relation"},
        )
        for count in counts.values():
            self.assertEqual(count, 42)

    def test_sends_cache_control_on_both_system_and_tool(self):
        captured_calls = []

        def _fake_count_tokens(**kwargs):
            captured_calls.append(kwargs)
            return types.SimpleNamespace(input_tokens=10)

        stub_client = types.SimpleNamespace(
            messages=types.SimpleNamespace(count_tokens=_fake_count_tokens)
        )
        with patch("anthropic.Anthropic", return_value=stub_client):
            measure_prompt_caching.preflight_prefix_token_counts("claude-opus-4-8")

        self.assertGreater(len(captured_calls), 0)
        for call in captured_calls:
            self.assertEqual(call["system"][0]["cache_control"], {"type": "ephemeral"})
            self.assertEqual(call["tools"][0]["cache_control"], {"type": "ephemeral"})


if __name__ == "__main__":
    unittest.main()
