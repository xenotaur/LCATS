"""Tests for the date-aware Heinlein record, its derivations and sidecar wiring."""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import unittest

from lcats.analysis.science_fiction import evidence
from lcats.analysis.science_fiction import heinlein_temporal
from lcats.analysis.science_fiction import models
from lcats.analysis.science_fiction import pipeline
from lcats.analysis.science_fiction import sidecar

ANALYSIS_DATE = "2026-10-31"


def _period(standing, start=None, end=None, basis="model_asserted"):
    return heinlein_temporal.StandingPeriod(
        standing=standing, basis=basis, from_date=start, to_date=end
    )


def _premise(
    premise_id="p1",
    *,
    timeline=None,
    materiality="central",
    novel="false",
    kind="ordinary",
    prediction=None,
):
    return heinlein_temporal.Premise(
        premise_id=premise_id,
        kind=kind,
        claim=f"Claim {premise_id}.",
        anchor=heinlein_temporal.PremiseAnchor(offset=10, quote=f"Quote {premise_id}."),
        materiality=materiality,
        novel_at_composition=novel,
        timeline=timeline or (_period("supported"),),
        dated_prediction=prediction,
    )


def _interval(earliest=None, latest=None):
    return heinlein_temporal.CompositionInterval(earliest=earliest, latest=latest)


# A Case of Sunburn: the blue-mist Mars was open until Mariner 4 (15 July 1965).
def _mars_timeline():
    return (_period("open", None, "1965-06"), _period("contradicted", "1965-07", None))


def _analysis(
    *,
    premises=None,
    composition=None,
    essential=None,
    causal=None,
    human=None,
    cutoff=None,
    existing=None,
    status="complete",
    failures=(),
    analysis_id="temporal-1",
):
    premises = (_premise(),) if premises is None else premises
    ids = tuple(premise.premise_id for premise in premises)
    return heinlein_temporal.HeinleinTemporalAnalysis(
        analysis_id=analysis_id,
        story_hash="story-hash",
        evidence_set_id="evidence-set-1",
        provenance=models.ProvenanceRecord(
            run_id="run-temporal",
            rubric_version=heinlein_temporal.TEMPORAL_RUBRIC_VERSION,
            generated_at="2026-10-31T00:00:00Z",
        ),
        analysis_date=ANALYSIS_DATE,
        premises=premises,
        composition=composition or _interval("1957-04", "1957-04"),
        essential=essential
        or heinlein_temporal.CriterionAssessment("present", ids[:1], "Essential."),
        causal=causal
        or heinlein_temporal.CriterionAssessment("present", ids[:1], "Causal."),
        human=human or heinlein_temporal.BorrowedHuman("present", "heinlein-1"),
        model_knowledge_cutoff=cutoff,
        existing_statuses=existing or {},
        status=status,
        failures=failures,
    )


class DateTest(unittest.TestCase):
    def test_bare_year_covers_twelve_months_and_a_month_covers_one(self):
        year = heinlein_temporal.month_range("1965")
        month = heinlein_temporal.month_range("1965-07")

        self.assertEqual(11, year[1] - year[0])
        self.assertEqual(month[0], month[1])
        self.assertTrue(year[0] <= month[0] <= year[1])
        self.assertEqual(month, heinlein_temporal.month_range("1965-07-15"))

    def test_touching_boundary_months_overlap(self):
        touching = (
            _period("open", None, "1965-07"),
            _period("contradicted", "1965-07", None),
        )
        premise = _premise(timeline=touching)

        status = heinlein_temporal.status_as_written(
            premise, _interval("1965-07", "1965-07"), ANALYSIS_DATE
        )

        self.assertEqual("ambiguous", status)

    def test_rejects_malformed_dates(self):
        for text in (
            "65",
            "1965-13",
            "July 1965",
            "",
            None,
            "2020\n",
            "2020-01-99",
            "2021-02-29",
            "２０２０",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                heinlein_temporal.month_range(text)


class TimelineTest(unittest.TestCase):
    def test_must_cover_all_time_without_a_gap(self):
        with self.assertRaises(ValueError):
            _premise(timeline=(_period("open", "1900", None),))
        with self.assertRaises(ValueError):
            _premise(timeline=(_period("open", None, "1900"),))
        with self.assertRaises(ValueError):
            _premise(
                timeline=(
                    _period("open", None, "1900"),
                    _period("supported", "1902", None),
                )
            )
        with self.assertRaises(ValueError):
            heinlein_temporal.validate_timeline(())

    def test_touching_and_adjacent_periods_are_accepted(self):
        _premise(
            timeline=(_period("open", None, "1965-07"), _period("supported", "1965-07"))
        )
        _premise(
            timeline=(_period("open", None, "1965-06"), _period("supported", "1965-07"))
        )

    def test_only_the_ends_of_the_timeline_may_be_open(self):
        with self.assertRaises(ValueError):
            _premise(timeline=(_period("open"), _period("contradicted", "1900", None)))

    def test_period_cannot_end_before_it_starts(self):
        with self.assertRaises(ValueError):
            _period("open", "1970", "1960")


class StatusOverIntervalTest(unittest.TestCase):
    def test_r2_present_absent_and_ambiguous(self):
        combine = heinlein_temporal.status_from_standings
        self.assertEqual("present", combine(("supported", "open")))
        self.assertEqual("absent", combine(("contradicted",)))
        self.assertEqual("ambiguous", combine(("open", "contradicted")))
        self.assertEqual("not_assessable", combine(()))

    def test_contested_standing_gives_ambiguous(self):
        timeline = (_period("open", None, "2014"), _period("contested", "2015", None))
        premise = _premise(timeline=timeline, novel="true")

        status = heinlein_temporal.status_as_written(
            premise, _interval("2015", "2015"), ANALYSIS_DATE
        )

        self.assertEqual("ambiguous", status)

    def test_sunburn_flips_at_mariner_4(self):
        premise = _premise(timeline=_mars_timeline(), novel="true")
        status = heinlein_temporal.status_as_written

        self.assertEqual(
            "present", status(premise, _interval("1957-04", "1957-04"), ANALYSIS_DATE)
        )
        self.assertEqual(
            "absent", status(premise, _interval("1970", "1970"), ANALYSIS_DATE)
        )
        # Mariner 4 flew on 15 July 1965, so July itself already has the new standing.
        self.assertEqual(
            "absent", status(premise, _interval("1965-07", "1965-07"), ANALYSIS_DATE)
        )
        self.assertEqual(
            "present", status(premise, _interval("1965-06", "1965-06"), ANALYSIS_DATE)
        )
        self.assertEqual(
            "ambiguous", status(premise, _interval("1957", "1970"), ANALYSIS_DATE)
        )

    def test_missing_interval_is_the_widest_interval(self):
        # A stable premise stays decisive; a time-sensitive one is ambiguous.
        stable = _premise(timeline=(_period("supported"),))
        sensitive = _premise(timeline=_mars_timeline())

        for premise, expected in ((stable, "present"), (sensitive, "ambiguous")):
            self.assertEqual(
                expected,
                heinlein_temporal.status_as_written(
                    premise, _interval(), ANALYSIS_DATE
                ),
            )

    def test_unbounded_latest_ends_at_the_analysis_date(self):
        premise = _premise(timeline=_mars_timeline())

        status = heinlein_temporal.status_as_written(
            premise, _interval("1970", None), ANALYSIS_DATE
        )

        self.assertEqual("absent", status)

    def test_today_is_a_point_interval(self):
        premise = _premise(timeline=_mars_timeline())

        self.assertEqual(
            "absent", heinlein_temporal.status_today(premise, ANALYSIS_DATE, None)
        )
        self.assertEqual(
            "present", heinlein_temporal.status_today(premise, "1960-01-01", None)
        )

    def test_unsettled_claim_beyond_the_cutoff_is_not_assessable(self):
        unsettled = _premise(timeline=(_period("open"),))
        settled = _premise(timeline=(_period("supported"),))
        today = heinlein_temporal.status_today

        self.assertEqual("not_assessable", today(unsettled, ANALYSIS_DATE, "2025-06"))
        self.assertEqual("present", today(unsettled, ANALYSIS_DATE, "2026-12"))
        self.assertEqual("present", today(settled, ANALYSIS_DATE, "2025-06"))


class RelationTest(unittest.TestCase):
    def _relation(self, written, today):
        # Two periods: standing at 1950 and standing now.
        premise = _premise(
            timeline=(_period(written, None, "1999"), _period(today, "2000", None))
        )
        return heinlein_temporal.relation_to_today(
            premise, _interval("1950", "1950"), ANALYSIS_DATE, None
        )

    def test_r3_pairs(self):
        expected = {
            ("supported", "supported"): "stable",
            ("contradicted", "contradicted"): "stable",
            ("open", "open"): "still_open",
            ("open", "supported"): "realized",
            ("contradicted", "supported"): "realized",
            ("supported", "contradicted"): "falsified",
            ("open", "contradicted"): "falsified",
            ("supported", "open"): "not_assessable",
            ("contradicted", "open"): "not_assessable",
            ("contested", "supported"): "not_assessable",
            ("supported", "contested"): "not_assessable",
        }
        for (written, today), relation in expected.items():
            with self.subTest(written=written, today=today):
                self.assertEqual(relation, self._relation(written, today))

    def test_straddling_interval_has_no_relation(self):
        premise = _premise(timeline=_mars_timeline())

        relation = heinlein_temporal.relation_to_today(
            premise, _interval("1957", "1970"), ANALYSIS_DATE, None
        )

        self.assertEqual("not_assessable", relation)

    def test_sunburn_is_falsified_when_composed_before_mariner_4(self):
        premise = _premise(timeline=_mars_timeline())

        relation = heinlein_temporal.relation_to_today(
            premise, _interval("1957-04", "1957-04"), ANALYSIS_DATE, None
        )

        self.assertEqual("falsified", relation)


class CalendarExpiredTest(unittest.TestCase):
    def _expired(self, date):
        premise = _premise(
            prediction=heinlein_temporal.DatedPrediction(date=date, claim="Claim.")
        )
        return heinlein_temporal.calendar_expired(premise, ANALYSIS_DATE)

    def test_past_prediction_is_expired_and_future_is_not(self):
        self.assertTrue(self._expired("2000"))
        self.assertTrue(self._expired("2026-09"))
        self.assertFalse(self._expired("2026"))
        self.assertFalse(self._expired("2026-10"))
        self.assertFalse(self._expired("2030"))

    def test_no_prediction_is_never_expired(self):
        self.assertFalse(heinlein_temporal.calendar_expired(_premise(), ANALYSIS_DATE))


class DifferentTest(unittest.TestCase):
    def test_setting_time_alone_is_never_a_difference(self):
        # Historical fiction faithful to the author's own history: not novel.
        historical = _premise(novel="false")

        self.assertEqual(
            "absent", heinlein_temporal.different_as_written((historical,))
        )

    def test_no_counted_premises_is_absent(self):
        incidental = _premise(materiality="incidental", novel="true")

        self.assertEqual("absent", heinlein_temporal.different_as_written(()))
        self.assertEqual(
            "absent", heinlein_temporal.different_as_written((incidental,))
        )

    def test_any_novel_counted_premise_is_present(self):
        self.assertEqual(
            "present",
            heinlein_temporal.different_as_written(
                (_premise("a", novel="false"), _premise("b", novel="true"))
            ),
        )

    def test_unknown_without_a_novel_premise_is_ambiguous(self):
        self.assertEqual(
            "ambiguous",
            heinlein_temporal.different_as_written(
                (_premise("a", novel="false"), _premise("b", novel="unknown"))
            ),
        )

    def test_counterfactual_divergence_is_novel_by_definition(self):
        with self.assertRaises(ValueError):
            _premise(kind="counterfactual_divergence", novel="false")
        divergence = _premise(kind="counterfactual_divergence", novel="true")

        self.assertEqual(
            "present", heinlein_temporal.different_as_written((divergence,))
        )

    def test_alternate_history_divergence_is_not_falsified_by_the_record(self):
        # The timeline describes the enabling mechanism, so a divergence that
        # history did not take is not a false fact.
        mechanism = (_period("open"),)
        divergence = _premise(
            kind="counterfactual_divergence", novel="true", timeline=mechanism
        )

        status = heinlein_temporal.status_as_written(
            divergence, _interval("2015", "2015"), ANALYSIS_DATE
        )

        self.assertEqual("present", status)


class SpeculativeAndProfileTest(unittest.TestCase):
    def test_flag_counts_novel_and_unsupported_counted_premises(self):
        premises = (
            _premise("a", novel="true", materiality="central"),
            _premise("b", timeline=_mars_timeline(), materiality="substantial"),
            _premise("c", novel="true", materiality="incidental"),
            _premise("d", materiality="central"),
        )

        flag = heinlein_temporal.speculative_flag(
            premises, _interval("1957", "1957"), ANALYSIS_DATE
        )

        self.assertEqual(
            {
                "has": True,
                "counted": 2,
                "by_materiality": {"central": 1, "substantial": 1},
            },
            flag,
        )

    def test_realist_story_has_no_speculative_premises(self):
        flag = heinlein_temporal.speculative_flag(
            (_premise("a"),), _interval("1908", "1908"), ANALYSIS_DATE
        )

        self.assertFalse(flag["has"])

    def test_profile_table_rows(self):
        category = heinlein_temporal.profile_category
        rows = [
            ("present", "present", "evergreen"),
            ("present", "absent", "overtaken"),
            ("present", "ambiguous", "plausible_when_written_today_undetermined"),
            ("present", "not_assessable", "plausible_when_written_today_undetermined"),
            ("absent", "present", "plausible_only_in_retrospect"),
            ("absent", "absent", "fails_when_written"),
            ("absent", "ambiguous", "fails_when_written"),
            ("absent", "not_assessable", "fails_when_written"),
            ("ambiguous", "present", "undetermined"),
            ("ambiguous", "absent", "undetermined"),
            ("not_assessable", "present", "undetermined"),
        ]
        for written, today, expected in rows:
            with self.subTest(written=written, today=today):
                self.assertEqual(expected, category(written, today, True))
                self.assertEqual("not_applicable", category(written, today, False))
        self.assertTrue(
            {row[2] for row in rows} | {"not_applicable"}
            == heinlein_temporal.PROFILE_CATEGORIES
        )


class VerdictTest(unittest.TestCase):
    def _statuses(self, **overrides):
        statuses = {name: "present" for name in models.HEINLEIN_CRITERION_IDS}
        statuses.update(overrides)
        return statuses

    def test_conjunction_over_five_statuses(self):
        verdict = heinlein_temporal.verdict_as_written
        self.assertEqual(("qualifies", "consistent", []), verdict(self._statuses()))
        self.assertEqual(
            "does_not_qualify", verdict(self._statuses(plausible="absent"))[0]
        )
        self.assertEqual("indeterminate", verdict(self._statuses(human="ambiguous"))[0])

    def test_not_computed_human_is_indeterminate_not_a_failure(self):
        verdict, consistency, _ = heinlein_temporal.verdict_as_written(
            self._statuses(human=heinlein_temporal.NOT_COMPUTED)
        )

        self.assertEqual(("indeterminate", "consistent"), (verdict, consistency))

    def test_prerequisite_violation_is_reported_not_forced(self):
        verdict, consistency, violations = heinlein_temporal.verdict_as_written(
            self._statuses(different="absent")
        )

        self.assertEqual(("indeterminate", "inconsistent"), (verdict, consistency))
        self.assertIn(["essential", "different"], violations)


class AnalysisTest(unittest.TestCase):
    def test_no_speculative_premises_is_present_and_not_applicable(self):
        # A realist story: the model reports essential and causal as absent.
        analysis = _analysis(
            premises=(_premise("a", materiality="central"),),
            composition=_interval("1908", "1908"),
            essential=heinlein_temporal.CriterionAssessment("absent"),
            causal=heinlein_temporal.CriterionAssessment("absent"),
        )

        assessment = analysis.assessment()

        self.assertEqual("present", assessment["plausible_as_written"])
        self.assertEqual("present", assessment["plausible_today"])
        self.assertFalse(assessment["speculative_premises"]["has"])
        self.assertEqual("not_applicable", assessment["category"])
        self.assertEqual("absent", assessment["different_as_written"])
        self.assertEqual("does_not_qualify", assessment["verdict_as_written"])

    def test_no_counted_premises_is_present_vacuously(self):
        analysis = _analysis(
            premises=(_premise("a", materiality="incidental"),),
            essential=heinlein_temporal.CriterionAssessment("absent"),
            causal=heinlein_temporal.CriterionAssessment("absent"),
        )

        assessment = analysis.assessment()

        self.assertEqual("present", assessment["plausible_as_written"])
        self.assertEqual("present", assessment["plausible_today"])
        self.assertIsNone(assessment["today_reason"])

    def test_sunburn_is_overtaken_with_a_stated_condition_when_date_unknown(self):
        premise = _premise("mars", timeline=_mars_timeline(), novel="true")
        known = _analysis(
            premises=(premise,), composition=_interval("1957-04", "1957-04")
        )
        unknown = _analysis(premises=(premise,), composition=_interval())

        self.assertEqual("overtaken", known.assessment()["category"])
        self.assertEqual("ambiguous", unknown.assessment()["plausible_as_written"])
        self.assertEqual("undetermined", unknown.assessment()["category"])
        self.assertIn("mars", unknown.assessment()["condition"])
        self.assertIsNone(known.assessment()["condition"])

    def test_expired_prediction_is_excluded_from_today_and_never_evergreen(self):
        expired = _premise(
            "future-history",
            timeline=(
                _period("open", None, "1961"),
                _period("contradicted", "1962", None),
            ),
            novel="true",
            prediction=heinlein_temporal.DatedPrediction("2000", "20 billion by 2000."),
        )
        analysis = _analysis(premises=(expired,), composition=_interval("1962", "1962"))

        assessment = analysis.assessment()

        self.assertTrue(assessment["per_premise"][0]["calendar_expired"])
        self.assertEqual("not_assessable", assessment["plausible_today"])
        self.assertEqual(
            heinlein_temporal.TODAY_REASON_ALL_EXPIRED, assessment["today_reason"]
        )
        self.assertTrue(assessment["speculative_premises"]["has"])
        self.assertNotEqual("evergreen", assessment["category"])

    def test_one_expired_premise_does_not_hide_the_others(self):
        expired = _premise(
            "dated",
            timeline=(_period("contradicted"),),
            prediction=heinlein_temporal.DatedPrediction("2000", "By 2000."),
        )
        live = _premise("live", novel="true", timeline=(_period("open"),))
        analysis = _analysis(
            premises=(expired, live), composition=_interval("1962", "1962")
        )

        assessment = analysis.assessment()

        self.assertEqual("absent", assessment["plausible_as_written"])
        self.assertEqual("present", assessment["plausible_today"])
        self.assertIsNone(assessment["today_reason"])

    def test_willstone_style_divergence_with_contested_theory(self):
        divergence = _premise(
            "antibiotics",
            kind="counterfactual_divergence",
            novel="true",
            timeline=(_period("open"),),
        )
        multiverse = _premise(
            "multiverse",
            novel="true",
            timeline=(
                _period("open", None, "2014"),
                _period("contested", "2015", None),
            ),
        )
        analysis = _analysis(
            premises=(divergence, multiverse), composition=_interval("2015", "2015")
        )

        assessment = analysis.assessment()

        self.assertEqual("present", assessment["different_as_written"])
        self.assertEqual("ambiguous", assessment["plausible_as_written"])
        self.assertEqual("undetermined", assessment["category"])

    def test_comparison_reports_only_differences_for_information(self):
        analysis = _analysis(existing={"different": "present", "plausible": "absent"})

        differences = analysis.assessment()["comparison_with_existing"]

        self.assertEqual(
            [
                {
                    "criterion_id": "plausible",
                    "temporal": "present",
                    "existing": "absent",
                },
            ],
            [d for d in differences if d["criterion_id"] == "plausible"],
        )
        self.assertNotIn("human", {d["criterion_id"] for d in differences})

    def test_criteria_must_cite_known_premises(self):
        with self.assertRaises(ValueError):
            _analysis(
                essential=heinlein_temporal.CriterionAssessment(
                    "present", ("nope",), "x"
                )
            )
        with self.assertRaises(ValueError):
            heinlein_temporal.CriterionAssessment("present", (), "x")

    def test_human_needs_a_source_unless_not_computed(self):
        with self.assertRaises(ValueError):
            heinlein_temporal.BorrowedHuman("present", None)
        heinlein_temporal.BorrowedHuman()

    def test_requires_its_own_provenance_version(self):
        with self.assertRaises(ValueError):
            dataclasses.replace(
                _analysis(),
                provenance=models.ProvenanceRecord(
                    run_id="r", rubric_version=models.HEINLEIN_RUBRIC_VERSION
                ),
            )

    def test_round_trips_through_serialized_form(self):
        analysis = _analysis(
            premises=(
                _premise(
                    "p1",
                    timeline=_mars_timeline(),
                    novel="true",
                    prediction=heinlein_temporal.DatedPrediction("1985", "Colony."),
                ),
            ),
            cutoff="2025-06",
            existing={"human": "present"},
        )
        data = analysis.to_dict()

        rebuilt = heinlein_temporal.analysis_from_dict(copy.deepcopy(data))

        self.assertEqual(data, rebuilt.to_dict())

    def test_parsing_rejects_unknown_keys_and_bad_shapes(self):
        data = _analysis().to_dict()
        for mutate in (
            lambda d: d["premises"][0].update(extra=1),
            lambda d: d["premises"][0]["timeline"][0].update(standing="maybe"),
            lambda d: d.update(premises="nope"),
            lambda d: d["composition"].update(earliest="x"),
        ):
            broken = copy.deepcopy(data)
            mutate(broken)
            with self.subTest(), self.assertRaises(ValueError):
                heinlein_temporal.analysis_from_dict(broken)


def _evidence_set() -> evidence.EvidenceSet:
    return evidence.EvidenceSet(
        evidence_set_id="evidence-set-1",
        story_hash="story-hash",
        records=(),
        quarantined=(),
        conflicts=(),
    )


def _inputs(*, with_temporal: bool, analysis=None) -> pipeline.SidecarAssemblyInputs:
    temporal = ()
    if with_temporal:
        temporal = (analysis or _analysis(),)
    return pipeline.SidecarAssemblyInputs(
        lcats_id="bucket/story",
        story_path="bucket/story/story.json",
        story_hash="story-hash",
        evidence_sets=(_evidence_set(),),
        heinlein_temporal_analyses=temporal,
    )


class SidecarWiringTest(unittest.TestCase):
    def _kinds(self, data) -> set[str]:
        return {finding.kind for finding in sidecar.validate_sidecar(data).findings}

    def test_new_fields_are_appended_last(self):
        for cls, previous_last in (
            (models.ScienceFictionSidecarEnvelope, "heinlein_analyses"),
            (pipeline.SidecarAssemblyInputs, "heinlein_analyses"),
            (models.CurrentPointers, "heinlein_analysis_id"),
        ):
            with self.subTest(cls=cls.__name__):
                names = [field.name for field in dataclasses.fields(cls)]
                self.assertEqual(names[-1].startswith("heinlein_temporal"), True, names)
                self.assertEqual(previous_last, names[-2])

    def test_sidecar_round_trips_with_current_pointer(self):
        data = pipeline.assemble_sidecar_data(_inputs(with_temporal=True))

        self.assertEqual("temporal-1", data["current"]["heinlein_temporal_analysis_id"])
        self.assertEqual(
            "heinlein-temporal-v1",
            data["analyses"]["heinlein_temporal"][0]["provenance"]["rubric_version"],
        )
        self.assertTrue(sidecar.validate_sidecar(data).valid)
        self.assertEqual(data, json.loads(sidecar.dumps_json(data)))

    def test_omitted_when_empty_and_existing_fingerprint_is_unchanged(self):
        inputs = _inputs(with_temporal=False)
        data = pipeline.assemble_sidecar_data(inputs)
        fingerprint = pipeline.effective_fingerprint(inputs)

        self.assertNotIn("heinlein_temporal", data["analyses"])
        self.assertNotIn("heinlein_temporal_analysis_id", data["current"])
        self.assertNotIn("heinlein_temporal_analyses", fingerprint["inputs"])
        self.assertEqual(models.SCIENCE_FICTION_SIDECAR_VERSION, data["schema_version"])
        self.assertTrue(sidecar.validate_sidecar(data).valid)

    def test_existing_hashes_match_the_values_computed_before_this_change(self):
        # Computed on origin/main before the heinlein_temporal kind existed, for
        # a story with an evidence set and no analyses. A change to either hash
        # would invalidate every existing sidecar and assembly checkpoint.
        inputs = _inputs(with_temporal=False)

        self.assertEqual(
            "53ace98844350fe1082264c4a6749a1a50fdd8623c77abe9df64efe1dcd52407",
            pipeline.effective_fingerprint(inputs)["sha256"],
        )
        self.assertEqual(
            "048275dda559f4321f16976c78be4a191f79c024649b499a5b1211bb61837331",
            hashlib.sha256(
                json.dumps(
                    pipeline.assemble_sidecar_data(inputs), sort_keys=True
                ).encode()
            ).hexdigest(),
        )

    def test_schema_version_is_not_bumped(self):
        self.assertEqual(
            "science-fiction-sidecar-v1", models.SCIENCE_FICTION_SIDECAR_VERSION
        )

    def test_adding_the_record_changes_the_fingerprint(self):
        without = pipeline.effective_fingerprint(_inputs(with_temporal=False))
        with_it = pipeline.effective_fingerprint(_inputs(with_temporal=True))

        self.assertNotEqual(without["sha256"], with_it["sha256"])

    def test_validator_rejects_a_hand_edited_assessment(self):
        data = pipeline.assemble_sidecar_data(_inputs(with_temporal=True))
        broken = copy.deepcopy(data)
        broken["analyses"]["heinlein_temporal"][0]["assessment"][
            "category"
        ] = "evergreen"

        self.assertIn("heinlein_temporal_assessment_mismatch", self._kinds(broken))

    def test_validator_rejects_invalid_inputs_wrong_rubric_and_dangling_pointer(self):
        data = pipeline.assemble_sidecar_data(_inputs(with_temporal=True))
        broken = copy.deepcopy(data)
        analysis = broken["analyses"]["heinlein_temporal"][0]
        analysis["premises"][0]["timeline"][0]["standing"] = "maybe"
        analysis["provenance"]["rubric_version"] = models.HEINLEIN_RUBRIC_VERSION
        broken["current"]["heinlein_temporal_analysis_id"] = "missing"

        self.assertTrue(
            {"invalid_heinlein_temporal", "invalid_rubric_version", "missing_reference"}
            <= self._kinds(broken)
        )

    def test_failed_record_never_becomes_current(self):
        failed = _analysis(
            status="failed",
            failures=(
                models.FailureRecord(
                    stage="heinlein_temporal", kind="Timeout", message="timed out"
                ),
            ),
        )

        data = pipeline.assemble_sidecar_data(
            _inputs(with_temporal=True, analysis=failed)
        )

        self.assertNotIn("heinlein_temporal_analysis_id", data["current"])

    def test_stage_is_accepted_as_partial_success(self):
        record = models.PartialSuccessRecord(
            completed_stages=("evidence",),
            failed_stages=(
                models.FailureRecord(
                    stage="heinlein_temporal", kind="Timeout", message="timed out"
                ),
            ),
        )
        inputs = dataclasses.replace(
            _inputs(with_temporal=False), partial_success=record
        )

        data = pipeline.assemble_sidecar_data(inputs)

        self.assertTrue(sidecar.validate_sidecar(data).valid)


if __name__ == "__main__":
    unittest.main()
