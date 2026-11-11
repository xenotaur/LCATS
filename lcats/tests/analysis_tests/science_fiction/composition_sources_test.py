"""Tests for composition-date sources and interval construction (WI-SF-0128).

The story dates below are the values the premise-first trial used. Where the
trial could not confirm a date, the test says so; none of these tests is
evidence that a date is right, only that the intersection logic handles it.
No test reads the network.
"""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from lcats.analysis.science_fiction import composition_sources as cs
from lcats.analysis.science_fiction import heinlein_temporal


def _bib(date, confidence=None, caveats=()):
    return cs.BibliographicRecord(
        first_publication=date,
        basis="test citation",
        confidence=confidence,
        caveats=caveats,
    )


def _life(born, died, caveats=()):
    return cs.AuthorLifespan(
        born=born, died=died, basis="test lifespan", caveats=caveats
    )


def _kinds(interval):
    return [source.kind for source in interval.sources]


class IntersectionTest(unittest.TestCase):
    def test_a_bibliographic_date_is_only_an_upper_bound(self):
        interval = cs.build_interval(bibliographic=_bib("1957-04"))

        self.assertIsNone(interval.earliest)
        self.assertEqual("1957-04", interval.latest)
        self.assertFalse(interval.override)

    def test_lifespan_gives_birth_as_lower_and_death_as_a_hard_upper_bound(self):
        interval = cs.build_interval(lifespan=_life("1917", "2007"))

        self.assertEqual(("1917", "2007"), (interval.earliest, interval.latest))
        self.assertTrue(interval.sources[0].hard_bound)

    def test_a_living_author_has_no_death_bound_and_no_hard_bound(self):
        interval = cs.build_interval(lifespan=_life("1950", None))

        self.assertEqual("1950", interval.earliest)
        self.assertIsNone(interval.latest)
        self.assertFalse(interval.sources[0].hard_bound)

    def test_sources_are_intersected_and_each_is_recorded(self):
        # A Case of Sunburn (trial): April 1957 from audiobook listings only,
        # author 1917-2007.
        interval = cs.build_interval(
            bibliographic=_bib("1957-04", confidence=0.5),
            lifespan=_life("1917", "2007"),
        )

        self.assertEqual(("1917", "1957-04"), (interval.earliest, interval.latest))
        self.assertEqual(["bibliographic", "author_lifespan"], _kinds(interval))
        recorded = interval.sources[0]
        self.assertEqual("test citation", recorded.basis)
        self.assertEqual(0.5, recorded.confidence)
        self.assertIn("1957-04", recorded.value)

    def test_death_wins_over_a_later_posthumous_publication(self):
        interval = cs.build_interval(
            bibliographic=_bib("1990"), lifespan=_life("1900", "1950")
        )

        self.assertEqual(("1900", "1950"), (interval.earliest, interval.latest))

    def test_internal_evidence_narrows_but_never_widens(self):
        # Brown Wolf (trial): no confirmed publication date; the text sets the
        # story about 1901 and a collection dates to 1906 (an inference).
        interval = cs.build_interval(
            lifespan=_life("1876", "1916"),
            internal=cs.InternalEvidence(
                earliest="1901", latest="1906", basis="text and collection date"
            ),
        )
        wider = cs.build_interval(
            lifespan=_life("1876", "1916"),
            internal=cs.InternalEvidence(
                earliest="1850", latest="1950", basis="too wide"
            ),
        )

        self.assertEqual(("1901", "1906"), (interval.earliest, interval.latest))
        self.assertEqual(("1876", "1916"), (wider.earliest, wider.latest))
        # A consistent but wider source is recorded as evidence that agreed.
        self.assertEqual(["author_lifespan", "internal_evidence"], _kinds(wider))

    def test_the_trial_stories_known_cases(self):
        cases = {
            "bell": (_bib("1845"), _life("1805", "1875"), ("1805", "1845")),
            "2br02b": (_bib("1962-01"), _life("1922", "2007"), ("1922", "1962-01")),
            "leiber": (_bib("1953-07"), _life("1910", "1992"), ("1910", "1953-07")),
            "blue cross": (
                _bib("1910-07-23"),
                _life("1874", "1936"),
                ("1874", "1910-07-23"),
            ),
        }
        for name, (bibliographic, lifespan, expected) in cases.items():
            with self.subTest(name):
                interval = cs.build_interval(
                    bibliographic=bibliographic, lifespan=lifespan
                )
                self.assertEqual(expected, (interval.earliest, interval.latest))

    def test_a_bare_year_upper_bound_covers_its_whole_year(self):
        # 1957 as an upper bound allows composition through December 1957, so
        # an internal lower bound of June 1957 is consistent, not a conflict.
        interval = cs.build_interval(
            bibliographic=_bib("1957"),
            internal=cs.InternalEvidence(
                earliest="1957-06", latest=None, basis="mentions a June event"
            ),
        )

        self.assertEqual(("1957-06", "1957"), (interval.earliest, interval.latest))
        self.assertEqual(["bibliographic", "internal_evidence"], _kinds(interval))
        self.assertFalse(any("not applied" in c for c in interval.caveats))

    def test_a_bare_year_lower_bound_starts_in_january(self):
        interval = cs.build_interval(
            bibliographic=_bib("1957-01"),
            internal=cs.InternalEvidence(
                earliest="1957", latest=None, basis="a year-only lower bound"
            ),
        )

        self.assertEqual(("1957", "1957-01"), (interval.earliest, interval.latest))

    def test_comparison_is_by_month_so_two_days_in_one_month_never_conflict(self):
        # Documented limit: the comparison is at month granularity, so a lower
        # bound later in the month than the upper bound does not conflict.
        interval = cs.build_interval(
            bibliographic=_bib("1910-07-10"),
            internal=cs.InternalEvidence(
                earliest="1910-07-30", latest=None, basis="a later day, same month"
            ),
        )

        self.assertEqual(
            ("1910-07-30", "1910-07-10"), (interval.earliest, interval.latest)
        )
        self.assertFalse(any("not applied" in c for c in interval.caveats))

    def test_the_result_is_a_valid_composition_interval(self):
        interval = cs.build_interval(
            bibliographic=_bib("1957-04"), lifespan=_life("1917", "2007")
        )

        heinlein_temporal.validate_composition_window(interval, "2026-11-10")
        self.assertEqual(
            {"earliest", "latest", "sources", "override", "caveats"},
            set(interval.to_dict()),
        )


class UnknownAndConflictTest(unittest.TestCase):
    def test_no_source_gives_an_unbounded_interval_never_a_guess(self):
        interval = cs.build_interval()

        self.assertIsNone(interval.earliest)
        self.assertIsNone(interval.latest)
        self.assertEqual((), interval.sources)
        self.assertEqual((cs.UNBOUNDED_CAVEAT,), interval.caveats)

    def test_a_conflicting_weaker_source_is_not_applied_and_is_named(self):
        # A bibliographic record that precedes the author's birth is wrong
        # somewhere; neither side is guessed at.
        interval = cs.build_interval(
            bibliographic=_bib("1800"), lifespan=_life("1850", "1920")
        )

        self.assertEqual(["bibliographic"], _kinds(interval))
        self.assertEqual((None, "1800"), (interval.earliest, interval.latest))
        self.assertTrue(
            any(
                "author_lifespan" in caveat and "not applied" in caveat
                for caveat in interval.caveats
            )
        )

    def test_a_conflict_with_every_source_still_yields_a_valid_interval(self):
        interval = cs.build_interval(
            lifespan=_life("1900", "1950"),
            internal=cs.InternalEvidence(
                earliest="1990", latest="2000", basis="contradicts the lifespan"
            ),
        )

        self.assertEqual(("1900", "1950"), (interval.earliest, interval.latest))
        self.assertTrue(any("internal_evidence" in c for c in interval.caveats))

    def test_source_caveats_are_carried_into_the_record(self):
        interval = cs.build_interval(
            lifespan=_life("1917", "2007", caveats=("posthumous revision",)),
            bibliographic=_bib("1957", caveats=("serialised",)),
        )

        self.assertEqual({"posthumous revision", "serialised"}, set(interval.caveats))

    def test_invalid_source_inputs_are_rejected(self):
        bad = (
            lambda: _bib("nineteen fifty"),
            lambda: _bib(""),
            lambda: _life("1950", "1900"),
            lambda: _life(None, None),
            lambda: cs.AuthorLifespan("1900", "1950", basis=""),
            lambda: cs.BibliographicRecord("1957", basis="x", confidence=1.5),
            lambda: cs.BibliographicRecord("1957", basis="x", confidence=True),
            lambda: cs.InternalEvidence(None, None, basis="x"),
            lambda: cs.InternalEvidence("1960", "1950", basis="x"),
        )
        for make in bad:
            with self.subTest():
                with self.assertRaises(ValueError):
                    make()


class OwnerOverrideTest(unittest.TestCase):
    def _owner(self, **updates):
        arguments = dict(
            story_id="mass_quantities/a_case_of_sunburn__fontenay",
            earliest="1956",
            latest="1957-03",
            basis="Test basis",
            caveats=("written for the April issue",),
        )
        arguments.update(updates)
        return cs.OwnerDates(**arguments)

    def test_owner_dates_override_every_other_source_and_are_recorded(self):
        interval = cs.build_interval(
            owner=self._owner(),
            bibliographic=_bib("1957-04"),
            lifespan=_life("1917", "2007"),
        )

        self.assertTrue(interval.override)
        self.assertEqual(("1956", "1957-03"), (interval.earliest, interval.latest))
        self.assertEqual(["owner_supplied"], _kinds(interval))
        self.assertEqual("Test basis", interval.sources[0].basis)
        self.assertIn("written for the April issue", interval.caveats)

    def test_the_override_names_the_computed_interval_it_replaced(self):
        interval = cs.build_interval(
            owner=self._owner(), lifespan=_life("1917", "2007")
        )

        self.assertIn("overrides the computed interval 1917 to 2007", interval.caveats)

    def test_an_owner_override_with_no_other_source_has_no_replacement_caveat(self):
        interval = cs.build_interval(owner=self._owner())

        self.assertEqual(("written for the April issue",), interval.caveats)

    def test_the_owner_wins_even_when_it_contradicts_the_other_sources(self):
        interval = cs.build_interval(
            owner=self._owner(earliest="1990", latest="1995"),
            lifespan=_life("1900", "1950"),
        )

        self.assertEqual(("1990", "1995"), (interval.earliest, interval.latest))

    def test_owner_dates_may_give_only_one_bound(self):
        interval = cs.build_interval(owner=self._owner(earliest=None))

        self.assertEqual((None, "1957-03"), (interval.earliest, interval.latest))

    def test_owner_caveats_are_stored_as_a_tuple(self):
        owner = self._owner(caveats=["a list is normalised"])

        self.assertEqual(("a list is normalised",), owner.caveats)

    def test_invalid_owner_dates_are_rejected(self):
        bad = (
            dict(earliest=None, latest=None),
            dict(earliest="1960", latest="1950"),
            dict(earliest="garbage"),
            dict(basis=""),
            dict(story_id=""),
            dict(caveats=("",)),
        )
        for updates in bad:
            with self.subTest(**updates):
                with self.assertRaises(ValueError):
                    self._owner(**updates)


class OwnerFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, text):
        path = self.root / "dates.json"
        path.write_text(text, encoding="utf-8")
        return path

    def _file(self, **stories):
        return json.dumps(
            {"version": cs.OWNER_DATES_VERSION, "stories": stories}, indent=2
        )

    def test_loads_a_reviewable_file(self):
        path = self._write(
            self._file(
                **{
                    "anderson/bell": {
                        "earliest": "1845",
                        "latest": "1845",
                        "basis": "Owner check of the Danish first edition",
                        "caveats": ["translation; the original date applies"],
                    },
                    "london/brown_wolf": {"latest": "1906", "basis": "Owner check"},
                }
            )
        )

        loaded = cs.load_owner_dates(path)

        self.assertEqual({"anderson/bell", "london/brown_wolf"}, set(loaded))
        self.assertEqual("1845", loaded["anderson/bell"].earliest)
        self.assertIsNone(loaded["london/brown_wolf"].earliest)
        self.assertEqual((), loaded["london/brown_wolf"].caveats)
        interval = cs.build_interval(owner=loaded["anderson/bell"])
        self.assertTrue(interval.override)

    def test_rejects_malformed_files(self):
        entry = {"earliest": "1845", "basis": "x"}
        bad = {
            "wrong version": json.dumps({"version": "v0", "stories": {}}),
            "unknown top key": json.dumps(
                {"version": cs.OWNER_DATES_VERSION, "stories": {}, "extra": 1}
            ),
            "stories not an object": json.dumps(
                {"version": cs.OWNER_DATES_VERSION, "stories": []}
            ),
            "unknown entry key": self._file(a=dict(entry, extra=1)),
            "missing basis": self._file(a={"earliest": "1845"}),
            "no dates": self._file(a={"basis": "x"}),
            "bad date": self._file(a=dict(entry, earliest="eighteen")),
            "inverted": self._file(a=dict(entry, earliest="1900", latest="1800")),
            "caveats not a list": self._file(a=dict(entry, caveats="oops")),
            "entry not an object": self._file(a="1845"),
            "not an object": "[]",
        }
        for name, text in bad.items():
            with self.subTest(name):
                with self.assertRaises(ValueError):
                    cs.load_owner_dates(self._write(text))

    def test_a_duplicate_story_id_is_an_error_not_silently_the_last(self):
        text = (
            '{"version": "lcats-composition-dates-v1", "stories": '
            '{"a": {"earliest": "1845", "basis": "x"}, '
            '"a": {"earliest": "1900", "basis": "y"}}}'
        )

        with self.assertRaises(ValueError):
            cs.load_owner_dates(self._write(text))

    def test_an_empty_stories_object_is_a_valid_empty_file(self):
        self.assertEqual({}, cs.load_owner_dates(self._write(self._file())))


if __name__ == "__main__":
    unittest.main()
