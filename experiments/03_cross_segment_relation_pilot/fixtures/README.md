# Fixture set for `run_pilot.py`'s targeted test harness

Small, fixed, offline, git-committed fixture set for `--story-list`
(given with no `FILE` argument — see `manifest.txt`) and for direct
`--story fixtures/<name>` targeting. Added by `WI-PILOT-0051` per
`PROP-LCATS-PILOT-COST-SUSTAINABILITY` Decision 2.

## Stories

These stories were copied from `corpora/mass_quantities/` (public
domain, Project Gutenberg - see `corpora/mass_quantities/LICENSE`),
chosen for small size (a cheap real run) and distinct segment shapes.
Renamed here without their source-collection author suffix for a shorter
`--story fixtures/<name>` spec:

- `king_of_the_hill/story.json` — copied from
  `corpora/mass_quantities/king_of_the_hill__blish/story.json`
  (James Blish, ~300 words). Fixture genre label: `science fiction`.
- `five_o_clock_tea_farce/story.json` — copied from
  `corpora/mass_quantities/five_o_clock_tea_farce__howells/story.json`
  (W. D. Howells, ~330 words). This fixture is retained for historical
  WI-PILOT-0051/0060 evidence, but `genre_ground_truth.json` marks it
  `wellformed: false`; it is not part of the WI-PILOT-0067
  `stability_gate_manifest.txt`.
- `unwelcomed_visitor/story.json` - copied from
  `corpora/mass_quantities/unwelcomed_visitor__samachson/story.json`
  (Joseph Samachson, ~460 words). Validated genre label: `science
  fiction`.

Manifest genre labels exist to exercise `run_pilot.py`'s `--genre`
plumbing and this harness's zero-config default path. Validated
wellformedness and genre adjudications are recorded separately in
`genre_ground_truth.json`; no genre-detect call is made in targeted mode.

## Usage

```
python experiments/03_cross_segment_relation_pilot/run_pilot.py \
    --story-list --dry-run --output /tmp/pilot-fixture-smoke-test
```

Add `--story-list fixtures/manifest.txt` explicitly for the same effect,
or `--story fixtures/king_of_the_hill --genre "science fiction"` to
target a single fixture story directly.

`stability_gate_manifest.txt` is deliberately separate from the default
manifest. It is used by `run_stability_gate.py` for WI-PILOT-0067 so that
the stability gate can use `unwelcomed_visitor` without changing
`run_pilot.py --story-list` with no FILE argument.
