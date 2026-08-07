# Fixture set for `run_pilot.py`'s targeted test harness

Small, fixed, offline, git-committed fixture set for `--story-list`
(given with no `FILE` argument — see `manifest.txt`) and for direct
`--story fixtures/<name>` targeting. Added by `WI-PILOT-0051` per
`PROP-LCATS-PILOT-COST-SUSTAINABILITY` Decision 2.

## Stories

Both copied verbatim from `corpora/mass_quantities/` (public domain,
Project Gutenberg — see `corpora/mass_quantities/LICENSE`), chosen for
small size (a cheap real run) and distinct segment/genre shapes.
Renamed here without their source-collection author suffix for a
shorter `--story fixtures/<name>` spec:

- `king_of_the_hill/story.json` — copied from
  `corpora/mass_quantities/king_of_the_hill__blish/story.json`
  (James Blish, ~300 words). Fixture genre label: `science fiction`.
- `five_o_clock_tea_farce/story.json` — copied from
  `corpora/mass_quantities/five_o_clock_tea_farce__howells/story.json`
  (W. D. Howells, ~330 words). Fixture genre label: `romance`.

Fixture genre labels exist to exercise `run_pilot.py`'s `--genre`
plumbing and this harness's zero-config default path — they are not a
validated genre classification of the source text (no genre-detect
call is made in targeted mode).

## Usage

```
python experiments/03_cross_segment_relation_pilot/run_pilot.py \
    --story-list --dry-run --output /tmp/pilot-fixture-smoke-test
```

Add `--story-list fixtures/manifest.txt` explicitly for the same
effect, or `--story fixtures/king_of_the_hill --genre "science fiction"`
to target a single fixture story directly.
