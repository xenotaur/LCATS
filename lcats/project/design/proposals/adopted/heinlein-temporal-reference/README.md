---
id: PROP-LCATS-HEINLEIN-TEMPORAL-REFERENCE
type: design_proposal_set
status: adopted
implementation_status: not_started
---

# Judge the Heinlein Conditions Against the Author's World at the Time of Writing

This proposal set records the design for judging Heinlein's five conditions against the
world the author lived in when the story was written, instead of the day the analysis runs.
An optional, separate stage estimates a composition-date interval, lists a story's material
factual premises with the windows in which each one's truth changed, and reports date-aware
plausibility, an outcome relation to today, a calendar-expired flag and a speculative-premises
flag, combined into a profile by deterministic rules. The existing `heinlein-five-v1` record
is unchanged.

## Documents

- [`00_proposal.md`](00_proposal.md) — background, prior-art check, design decisions, options
  compared, compatibility, implementation plan, and open questions.
- Evidence: `lcats/experimental/science_fiction_analysis_trial/heinlein_temporal_premise_trial.md`,
  the six-story premise trial this design rests on.
