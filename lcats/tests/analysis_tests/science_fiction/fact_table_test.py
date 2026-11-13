"""Tests for the curated fact table and its audit of model-asserted premises.

No test reads the network. The shipped table's sources were opened and read by
the author of the table; these tests check the table's structure and the
matcher's logic, not the truth of the astronomy.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import tempfile
import unittest

from lcats.analysis.science_fiction import fact_table
from lcats.analysis.science_fiction import heinlein_temporal
from lcats.analysis.science_fiction import pipeline
from lcats.analysis.science_fiction import sidecar
from tests.analysis_tests.science_fiction import heinlein_temporal_test as base


def _premise(claim, timeline, premise_id="p1"):
    premise = base._premise(premise_id, timeline=tuple(timeline), novel="true")
    return dataclasses.replace(premise, claim=claim)


def _p(standing, start=None, end=None):
    return base._period(standing, start, end)


MARS_CLAIM = "Mars has a thick, breathable atmosphere."
VENUS_CLAIM = "Venus has a temperate, habitable surface."
MERCURY_CLAIM = "Mercury is tidally locked, always keeping the same face to the Sun."


def _table_dict():
    return copy.deepcopy(json.loads(fact_table.DEFAULT_TABLE_PATH.read_text("utf-8")))


class ShippedTableTest(unittest.TestCase):
    def test_the_shipped_table_loads_with_the_required_cases(self):
        table = fact_table.default_table()

        ids = {fact.fact_id for fact in table.facts}
        self.assertTrue(
            {
                "mars_thick_atmosphere",
                "venus_temperate_surface",
                "mercury_synchronous_rotation",
            }
            <= ids
        )

    def test_every_entry_cites_an_opened_source_with_evidence(self):
        table = fact_table.default_table()

        for fact in table.facts:
            with self.subTest(fact.fact_id):
                opened = [
                    table.source(source_id)
                    for source_id in fact.source_ids
                    if table.source(source_id).opened
                ]
                self.assertTrue(opened)
                for source in opened:
                    self.assertTrue(source.url.startswith("https://"))
                    self.assertTrue(source.evidence)

    def test_the_mars_boundary_is_the_mariner_4_flyby_month(self):
        fact = next(
            f
            for f in fact_table.default_table().facts
            if f.fact_id == "mars_thick_atmosphere"
        )

        self.assertEqual("1965-07", fact.change_at)
        self.assertEqual("contradicted", fact.final_standing)

    def test_unconfirmed_earlier_standings_are_labelled_unconfirmed(self):
        for fact in fact_table.default_table().facts:
            with self.subTest(fact.fact_id):
                self.assertFalse(fact.before_confirmed)
                self.assertTrue(fact.before_note)

    def test_the_table_ships_as_package_data(self):
        text = (
            pathlib.Path(__file__).resolve().parents[3] / "pyproject.toml"
        ).read_text("utf-8")

        self.assertIn('"lcats.analysis.science_fiction" = ["facts/*.json"]', text)
        self.assertTrue(fact_table.DEFAULT_TABLE_PATH.is_file())


class ValidationTest(unittest.TestCase):
    def test_malformed_tables_are_rejected(self):
        def mutate(change):
            data = _table_dict()
            change(data)
            return data

        cases = {
            "wrong version": lambda d: d.update(version="v0"),
            "unknown top key": lambda d: d.update(extra=1),
            "unknown fact key": lambda d: d["facts"][0].update(extra=1),
            "missing fact key": lambda d: d["facts"][0].pop("note"),
            "unknown source key": lambda d: d["sources"][0].update(extra=1),
            "missing source key": lambda d: d["sources"][0].pop("evidence"),
            "duplicate fact id": lambda d: d["facts"].append(
                copy.deepcopy(d["facts"][0])
            ),
            "duplicate source id": lambda d: d["sources"].append(
                copy.deepcopy(d["sources"][0])
            ),
            "unknown source id": lambda d: d["facts"][0].update(source_ids=["nope"]),
            "no source ids": lambda d: d["facts"][0].update(source_ids=[]),
            "uppercase term": lambda d: d["facts"][0].update(match=[["Mars"]]),
            "empty group": lambda d: d["facts"][0].update(match=[[]]),
            "no groups": lambda d: d["facts"][0].update(match=[]),
            "bad standing": lambda d: d["facts"][0].update(final_standing="maybe"),
            "bad boundary": lambda d: d["facts"][0].update(change_at="soon"),
            "non-bool opened": lambda d: d["sources"][0].update(opened="yes"),
            "non-bool before_confirmed": lambda d: d["facts"][0].update(
                before_confirmed="no"
            ),
            "facts not a list": lambda d: d.update(facts={}),
        }
        for name, change in cases.items():
            with self.subTest(name):
                with self.assertRaises(ValueError):
                    fact_table.table_from_dict(mutate(change))

    def test_an_entry_whose_only_sources_were_not_opened_is_rejected(self):
        data = _table_dict()
        for source in data["sources"]:
            source["opened"] = False

        with self.assertRaisesRegex(ValueError, "opened and read"):
            fact_table.table_from_dict(data)

    def test_an_unopened_extra_source_is_allowed_but_not_counted(self):
        data = _table_dict()
        data["sources"].append(
            {
                "id": "unread",
                "title": "A page not opened",
                "url": "https://example.org/unread",
                "retrieved": "2026-11-13",
                "opened": False,
                "evidence": "UNCONFIRMED: not opened",
            }
        )
        data["facts"][0]["source_ids"] = ["unread"]

        with self.assertRaisesRegex(ValueError, "opened and read"):
            fact_table.table_from_dict(data)
        data["facts"][0]["source_ids"].append("nssdca_mariner_4")
        fact_table.table_from_dict(data)

    def test_a_duplicate_json_key_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "table.json"
            path.write_text(
                '{"version": "lcats-heinlein-fact-table-v1", "version": "x"}',
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                fact_table.load_table(path)


class ClaimMatchingTest(unittest.TestCase):
    def _entry(self, fact_id):
        return next(f for f in fact_table.default_table().facts if f.fact_id == fact_id)

    def test_a_claim_matches_only_when_every_group_has_a_term(self):
        mars = self._entry("mars_thick_atmosphere")

        self.assertTrue(fact_table.claim_matches(MARS_CLAIM, mars))
        self.assertTrue(
            fact_table.claim_matches("The Martian air is thick and rich.", mars)
        )
        self.assertFalse(fact_table.claim_matches("Mars has a thin atmosphere.", mars))
        self.assertFalse(
            fact_table.claim_matches("The atmosphere is thick and breathable.", mars)
        )
        self.assertFalse(fact_table.claim_matches("Mars has two moons.", mars))

    def test_terms_match_whole_words_not_fragments(self):
        mars = self._entry("mars_thick_atmosphere")

        self.assertFalse(
            fact_table.claim_matches("The marshal found a thick atmosphere.", mars)
        )

    def test_multiword_and_hyphenated_terms_match(self):
        mercury = self._entry("mercury_synchronous_rotation")

        self.assertTrue(fact_table.claim_matches(MERCURY_CLAIM, mercury))
        self.assertTrue(
            fact_table.claim_matches("Mercury is tidally  locked to the Sun.", mercury)
        )
        self.assertFalse(
            fact_table.claim_matches("Mercury is the smallest planet.", mercury)
        )

    def test_a_negated_claim_is_never_matched(self):
        for claim in (
            "Mars does NOT have a thick atmosphere.",
            "Mars has no breathable air.",
            "Mars never had a thick atmosphere.",
            "Venus surface isn't habitable.",
            "Venus has a surface without a temperate climate.",
            "Mercury is not tidally locked to the Sun.",
        ):
            with self.subTest(claim):
                for entry in fact_table.default_table().facts:
                    self.assertFalse(fact_table.claim_matches(claim, entry))

    def test_typographic_apostrophes_count_as_negation(self):
        for claim in (
            "Mars doesn\u2019t have a thick atmosphere.",
            "Mars doesn\u2018t have a thick atmosphere.",
            "Venus surface isn\u2019t habitable.",
            "Venus surface isn\u02bct habitable.",
            "Mercury isn\u2019t tidally locked to the Sun.",
            "Mars doesn`t have a thick atmosphere.",
        ):
            with self.subTest(claim):
                for entry in fact_table.default_table().facts:
                    self.assertFalse(fact_table.claim_matches(claim, entry))

    def test_the_metal_and_generic_sides_do_not_match_the_planet_entry(self):
        mercury = self._entry("mercury_synchronous_rotation")

        for claim in (
            "The thermometer (mercury) shows the same side of the room.",
            "Mercury poisoning; one side of the story.",
        ):
            with self.subTest(claim):
                self.assertFalse(fact_table.claim_matches(claim, mercury))

    def test_venus_needs_a_surface_word_and_a_habitability_word(self):
        venus = self._entry("venus_temperate_surface")

        self.assertTrue(fact_table.claim_matches(VENUS_CLAIM, venus))
        self.assertFalse(fact_table.claim_matches("Venus is a bright planet.", venus))
        self.assertFalse(
            fact_table.claim_matches("Venus has a temperate mood in the story.", venus)
        )


class AuditTest(unittest.TestCase):
    def test_agreement_marks_the_final_period_table_confirmed(self):
        premise = _premise(
            MARS_CLAIM,
            [_p("open", None, "1965-07"), _p("contradicted", "1965-07", None)],
        )

        audit = fact_table.audit_premise(premise)

        self.assertEqual("table_confirmed", audit.outcome)
        self.assertEqual("mars_thick_atmosphere", audit.fact_id)
        self.assertEqual("terms", audit.method)
        self.assertIn("nssdca_mariner_4", audit.reasons[0])

    def test_a_coarser_model_boundary_that_covers_the_month_agrees(self):
        premise = _premise(
            MARS_CLAIM, [_p("open", None, "1965"), _p("contradicted", "1965", None)]
        )

        self.assertEqual("table_confirmed", fact_table.audit_premise(premise).outcome)

    def test_the_earlier_standing_is_informational_and_not_enforced(self):
        for before in ("open", "supported", "contested"):
            premise = _premise(
                MERCURY_CLAIM,
                [_p(before, None, "1965"), _p("contradicted", "1965", None)],
            )
            with self.subTest(before):
                self.assertEqual(
                    "table_confirmed", fact_table.audit_premise(premise).outcome
                )

    def test_a_different_final_standing_is_a_disagreement(self):
        premise = _premise(
            VENUS_CLAIM, [_p("open", None, "1962-12"), _p("supported", "1962-12", None)]
        )

        audit = fact_table.audit_premise(premise)

        self.assertEqual("disagreement", audit.outcome)
        self.assertIn("venus_temperate_surface", audit.fact_id)
        self.assertTrue(any("supported" in reason for reason in audit.reasons))

    def test_a_premise_with_no_change_disagrees_with_a_table_change(self):
        premise = _premise(MARS_CLAIM, [_p("contradicted")])

        audit = fact_table.audit_premise(premise)

        self.assertEqual("disagreement", audit.outcome)
        self.assertTrue(any("records no change" in reason for reason in audit.reasons))

    def test_a_boundary_that_does_not_overlap_is_a_disagreement(self):
        premise = _premise(
            MARS_CLAIM, [_p("open", None, "1975"), _p("contradicted", "1975", None)]
        )

        audit = fact_table.audit_premise(premise)

        self.assertEqual("disagreement", audit.outcome)
        self.assertTrue(any("1975" in reason for reason in audit.reasons))

    def test_a_boundary_disagreement_says_what_the_table_boundary_means(self):
        premise = _premise(
            MARS_CLAIM, [_p("open", None, "1964"), _p("contradicted", "1964", None)]
        )

        audit = fact_table.audit_premise(premise)

        self.assertEqual("disagreement", audit.outcome)
        self.assertTrue(any("first measurement" in reason for reason in audit.reasons))

    def test_a_negated_typographic_claim_gets_no_audit_not_a_confirmation(self):
        premise = _premise(
            "Mars doesn\u2019t have a thick atmosphere.",
            [_p("open", None, "1965-07"), _p("contradicted", "1965-07", None)],
        )

        self.assertIsNone(fact_table.audit_premise(premise))

    def test_a_counterfactual_divergence_is_not_compared(self):
        premise = base._premise(
            "p1",
            kind="counterfactual_divergence",
            novel="true",
            timeline=(_p("open", None, "2100"), _p("supported", "2100", None)),
        )
        premise = dataclasses.replace(premise, claim=MARS_CLAIM)

        audit = fact_table.audit_premise(premise)

        self.assertEqual("not_comparable", audit.outcome)
        self.assertEqual("mars_thick_atmosphere", audit.fact_id)
        self.assertIn("enabling mechanism", audit.reasons[0])

    def test_a_counterfactual_matched_premise_is_not_relabelled(self):
        premise = base._premise(
            "p1",
            kind="counterfactual_divergence",
            novel="true",
            timeline=(_p("open", None, "1965-07"), _p("contradicted", "1965-07", None)),
        )
        premise = dataclasses.replace(premise, claim=MARS_CLAIM)

        audited = fact_table.apply_to_analysis(base._analysis(premises=(premise,)))

        self.assertEqual(
            {"model_asserted"}, {p.basis for p in audited.premises[0].timeline}
        )
        self.assertEqual(["not_comparable"], [a.outcome for a in audited.fact_audit])

    def test_repeated_standings_are_one_change_at_the_start_of_the_run(self):
        # contradicted since 1950, then another contradicted period at 1965-07:
        # the change was in 1950, so the table's 1965-07 boundary disagrees.
        early = _premise(
            MARS_CLAIM,
            [
                _p("open", None, "1950"),
                _p("contradicted", "1950", "1965-07"),
                _p("contradicted", "1965-07", None),
            ],
        )
        # the same fact with a later split of an already-contradicted run
        split = _premise(
            MARS_CLAIM,
            [
                _p("open", None, "1965-07"),
                _p("contradicted", "1965-07", "1970"),
                _p("contradicted", "1970", None),
            ],
        )

        self.assertEqual("disagreement", fact_table.audit_premise(early).outcome)
        self.assertEqual("table_confirmed", fact_table.audit_premise(split).outcome)

    def test_every_period_since_the_change_is_relabelled_and_earlier_ones_are_not(self):
        split = _premise(
            MARS_CLAIM,
            [
                _p("open", None, "1965-07"),
                _p("contradicted", "1965-07", "1970"),
                _p("contradicted", "1970", None),
            ],
        )

        audited = fact_table.apply_to_analysis(base._analysis(premises=(split,)))

        self.assertEqual(
            ["model_asserted", "table_confirmed", "table_confirmed"],
            [p.basis for p in audited.premises[0].timeline],
        )

    def test_all_one_standing_across_several_periods_is_no_change(self):
        premise = _premise(
            MARS_CLAIM,
            [_p("contradicted", None, "1900"), _p("contradicted", "1900", None)],
        )

        audit = fact_table.audit_premise(premise)

        self.assertEqual("disagreement", audit.outcome)
        self.assertTrue(any("records no change" in r for r in audit.reasons))

    def test_a_confirmation_lists_only_opened_sources(self):
        data = _table_dict()
        data["sources"].append(
            {
                "id": "unread_page",
                "title": "A page not opened",
                "url": "https://example.org/unread",
                "retrieved": "2026-11-12",
                "opened": False,
                "evidence": "UNCONFIRMED: not opened",
            }
        )
        data["facts"][0]["source_ids"].append("unread_page")
        table = fact_table.table_from_dict(data)
        premise = _premise(
            MARS_CLAIM,
            [_p("open", None, "1965-07"), _p("contradicted", "1965-07", None)],
        )

        audit = fact_table.audit_premise(premise, table)

        self.assertEqual("table_confirmed", audit.outcome)
        self.assertNotIn("unread_page", audit.reasons[0])
        self.assertIn("nssdca_mariner_4", audit.reasons[0])

    def test_an_unmatched_claim_gets_no_audit(self):
        premise = _premise("The sea was calm that morning.", [_p("supported")])

        self.assertIsNone(fact_table.audit_premise(premise))

    def test_an_empty_timeline_is_not_comparable(self):
        premise = _premise(MARS_CLAIM, [])

        audit = fact_table.audit_premise(premise)

        self.assertEqual("not_comparable", audit.outcome)

    def test_a_claim_matching_two_entries_is_ambiguous_and_not_decided(self):
        data = _table_dict()
        twin = copy.deepcopy(data["facts"][0])
        twin["fact_id"] = "mars_twin"
        data["facts"].append(twin)
        table = fact_table.table_from_dict(data)
        premise = _premise(
            MARS_CLAIM,
            [_p("open", None, "1965-07"), _p("contradicted", "1965-07", None)],
        )

        audit = fact_table.audit_premise(premise, table)

        self.assertEqual("ambiguous_match", audit.outcome)
        self.assertIsNone(audit.fact_id)
        self.assertIn("mars_twin", audit.reasons[0])


class ApplyToAnalysisTest(unittest.TestCase):
    def _analysis(self, *premises):
        return base._analysis(premises=premises)

    def _mars(self, *timeline):
        return _premise(
            MARS_CLAIM,
            timeline
            or [_p("open", None, "1965-07"), _p("contradicted", "1965-07", None)],
        )

    def test_a_confirmed_premise_gets_only_its_final_period_relabelled(self):
        analysis = self._analysis(self._mars())

        audited = fact_table.apply_to_analysis(analysis)

        bases = [period.basis for period in audited.premises[0].timeline]
        self.assertEqual(["model_asserted", "table_confirmed"], bases)
        self.assertEqual(
            [period.standing for period in analysis.premises[0].timeline],
            [period.standing for period in audited.premises[0].timeline],
        )
        self.assertEqual(["table_confirmed"], [a.outcome for a in audited.fact_audit])

    def test_the_audit_never_changes_a_derived_status(self):
        analysis = self._analysis(self._mars())

        audited = fact_table.apply_to_analysis(analysis)

        self.assertEqual(analysis.assessment(), audited.assessment())

    def test_a_disagreement_is_reported_and_leaves_the_premise_unchanged(self):
        analysis = self._analysis(self._mars(_p("contradicted")))

        audited = fact_table.apply_to_analysis(analysis)

        self.assertEqual(analysis.premises, audited.premises)
        self.assertEqual(["disagreement"], [a.outcome for a in audited.fact_audit])
        self.assertEqual(analysis.assessment(), audited.assessment())

    def test_an_analysis_with_no_matches_is_returned_unchanged(self):
        analysis = self._analysis(base._premise("p1"))

        audited = fact_table.apply_to_analysis(analysis)

        self.assertIs(analysis, audited)
        self.assertNotIn("fact_audit", audited.to_dict())

    def test_the_audit_round_trips_and_is_checked_on_load(self):
        audited = fact_table.apply_to_analysis(self._analysis(self._mars()))

        data = audited.to_dict()
        rebuilt = heinlein_temporal.analysis_from_dict(data)

        self.assertEqual(audited.fact_audit, rebuilt.fact_audit)
        self.assertEqual(data, rebuilt.to_dict())
        broken = copy.deepcopy(data)
        broken["fact_audit"][0]["premise_id"] = "ghost"
        with self.assertRaises(ValueError):
            heinlein_temporal.analysis_from_dict(broken)
        broken = copy.deepcopy(data)
        broken["fact_audit"][0]["outcome"] = "approved"
        with self.assertRaises(ValueError):
            heinlein_temporal.analysis_from_dict(broken)
        broken = copy.deepcopy(data)
        broken["fact_audit"][0]["extra"] = 1
        with self.assertRaises(ValueError):
            heinlein_temporal.analysis_from_dict(broken)

    def test_an_audited_record_validates_in_a_sidecar_and_a_malformed_audit_is_caught(
        self,
    ):
        audited = fact_table.apply_to_analysis(self._analysis(self._mars()))
        data = pipeline.assemble_sidecar_data(
            base._inputs(with_temporal=True, analysis=audited)
        )

        self.assertTrue(sidecar.validate_sidecar(data).valid)
        stored = data["analyses"]["heinlein_temporal"][0]["fact_audit"]
        self.assertEqual("table_confirmed", stored[0]["outcome"])
        for name, change in {
            "unknown premise": lambda a: a.update(premise_id="ghost"),
            "invalid outcome": lambda a: a.update(outcome="approved"),
            "unknown key": lambda a: a.update(extra=1),
        }.items():
            broken = copy.deepcopy(data)
            change(broken["analyses"]["heinlein_temporal"][0]["fact_audit"][0])
            with self.subTest(name):
                self.assertFalse(sidecar.validate_sidecar(broken).valid)

    def test_the_audit_is_an_annotation_and_is_not_re_derived_on_load(self):
        # Documented limit: the table grows, so a stored audit is shape-checked
        # but not recomputed. A flipped outcome therefore still validates.
        audited = fact_table.apply_to_analysis(self._analysis(self._mars()))
        data = pipeline.assemble_sidecar_data(
            base._inputs(with_temporal=True, analysis=audited)
        )
        data["analyses"]["heinlein_temporal"][0]["fact_audit"][0][
            "outcome"
        ] = "ambiguous_match"

        self.assertTrue(sidecar.validate_sidecar(data).valid)

    def test_fact_audit_records_validate_their_own_fields(self):
        bad = (
            dict(premise_id="", outcome="table_confirmed", method="terms", fact_id="x"),
            dict(premise_id="p", outcome="nope", method="terms"),
            dict(premise_id="p", outcome="table_confirmed", method="terms"),
            dict(premise_id="p", outcome="disagreement", method="terms"),
            dict(premise_id="p", outcome="ambiguous_match", method=""),
            dict(
                premise_id="p", outcome="ambiguous_match", method="terms", reasons=("",)
            ),
        )
        for arguments in bad:
            with self.subTest(**arguments):
                with self.assertRaises(ValueError):
                    heinlein_temporal.FactAudit(**arguments)


if __name__ == "__main__":
    unittest.main()
