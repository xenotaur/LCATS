# Worldcon Knight/Novum Spike Report

- Report version: `worldcon-knight-novum-spike-report-v1`
- Work item: `WI-SF-0012`
- Current committed run: no-cost fake smoke
- Output root: `experimental/science_fiction_analysis_trial/results/worldcon_spike`
- Summary: `experimental/science_fiction_analysis_trial/results/worldcon_spike/worldcon_spike_summary.json`

## Smoke Result

The no-cost 3-story smoke run completed structurally for all selected stories:

- `mass_quantities/2_b_r_0_2_b__vonnegut`
- `lovecraft/the_colour_out_of_space`
- `anderson/bell`

The smoke produced validated experiment-local `science-fiction.json` sidecars,
per-story Knight intervals, Suvin qualified-novum counts, token estimates, and
a run-local report. It did not make paid calls, write corpus sidecars, modify
annotation or promotion commands, or claim Phase 2 validation.

## Go/No-Go Note

The runner is structurally ready for the next gate: a reviewed 5-10 story
local-model and/or paid sample decision. Paid execution still requires an
approval manifest update naming the backend/model, pinned configuration,
estimated cost, estimated wall-clock time, output root, and stop conditions,
plus the explicit `--approve-paid` flag.

The 146-story Worldcon-scale run remains separately gated by a successful smoke
summary, explicit `--approve-full-sample`, and the same paid-run safeguards if a
paid backend is selected.
