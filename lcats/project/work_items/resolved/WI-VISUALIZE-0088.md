---
resolution: "Implemented and merged in PR #375 (commit 2bcc40fc)."
blocked_reason: null
blocked: false
id: WI-VISUALIZE-0088
title: Dogfood lcats visualize against the Worldcon 2026 paper's real figures
type: operation
status: resolved
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams:
  - WS-CORPUS-TEXT-VISUALIZATION
related_design:
  - project/design/proposals/adopted/corpus-text-visualization/00_proposal.md
  - lcats/src/lcats/visualize/
depends_on:
  - WI-VISUALIZE-0073
  - WI-VISUALIZE-0085
  - WI-VISUALIZE-0086
  - WI-VISUALIZE-0087
blocked_by:
  - WI-VISUALIZE-0086
  - WI-VISUALIZE-0087
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - implement_new_architecture
  - promote_sidecars
  - modify_lcats_annotate
  - modify_lcats_promote
acceptance:
  - "Every command in the `lcats visualize` family (`genres`, `words`, `tfidf`, `topics`) has been run at least once against the real, checked-in LCATS corpus (not synthetic test fixtures) to produce a real, reviewable figure -- not just exercised via unit/integration tests"
  - "At least one figure from each command is committed as an actual paper artifact for the Worldcon 2026 paper (e.g. under a paper-figures directory, or referenced/embedded in the paper's own source), demonstrating the command family is genuinely usable for its stated purpose, not merely functionally correct in isolation"
  - "Any real-corpus finding that surfaces during dogfooding and requires a code fix (e.g. a preprocessing default that produces a degenerate figure at full corpus scale, a performance issue only visible at 1868-story scale) is fixed as part of this work item or explicitly logged as a documented follow-up, not silently absorbed or ignored"
  - "This work item does not implement any new `lcats visualize` command or option -- if dogfooding surfaces a genuine missing capability (e.g. a new selector, a new output format), that becomes a new work item or a documented Open Question, not scope creep into this one"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
artifacts_expected:
  - Real figure output files (PNG/SVG) from all 4 lcats visualize commands, run against the real corpus
  - A paper-figures location (exact path to be determined during implementation, consistent with wherever the Worldcon 2026 paper's other figures/artifacts live) containing at least one committed figure per command
---

# Work Item: WI-VISUALIZE-0088

## Summary

Dogfood the complete `lcats visualize` command family (`genres`, `words`,
`tfidf`, `topics`) against the real LCATS corpus to produce actual figures
for the Worldcon 2026 paper, closing the gap between "the commands pass
their own tests" and "the commands were genuinely used for their stated
purpose." This is item 5 of `WS-CORPUS-TEXT-VISUALIZATION`'s decomposition.

## Problem / Context

Each of `WI-VISUALIZE-0073`, `-0085`, `-0086`, and `-0087` validates its own
command with real-corpus CLI runs as part of implementation (this is
already an established, enforced pattern in this workstream -- see e.g.
`WI-VISUALIZE-0085`'s own Validation section). What none of them individually
cover is producing and committing an actual figure intended for paper use,
and confirming the family works together as a coherent set for the paper's
real needs -- the governing proposal's own exit criterion ("the visualize
command family is dogfooded to produce real figures used in the Worldcon
2026 paper") is about paper usage, not just per-command correctness.

### Prior Art Check

- In-repo: no existing "paper figures" directory or convention was found
  for this repo at proposal-adoption time; the exact location should be
  confirmed against the current state of the Worldcon 2026 paper's own
  source/assets during implementation, since this work item explicitly
  depends on `WI-VISUALIZE-0086`/`-0087` landing first and the paper's own
  structure may evolve independently in the meantime.
- Sibling repos / external libraries: not applicable -- this is an
  operational/validation work item, not new library-dependent code.
- Demand: `WS-CORPUS-TEXT-VISUALIZATION`'s own exit criteria are the
  originating request; no other open work item or proposal requests this
  independently.

## Scope

- Run all 4 `lcats visualize` commands against the real, checked-in corpus.
- Select and commit at least one figure per command as an actual paper
  artifact.
- Fix any real-corpus-scale issue discovered during dogfooding, or log it
  as an explicit follow-up if out of this item's immediate scope.

## Out of Scope

- Implementing any new command, option, or selector -- this item validates
  and uses the existing family; new capability needs become a new work
  item.
- Writing the paper's prose or narrative around the figures -- this item
  produces and places the figures; paper authorship is a separate concern.
- Documentation/usage-examples work -- that is item 6
  (`WI-VISUALIZE-0089`), a distinct work item in this decomposition.

## Required Changes

1. Run `lcats visualize genres`, `words`, `tfidf`, and `topics` against the
   real corpus with parameters appropriate for actual paper use (not just
   smoke-test defaults).
2. Review the resulting figures for genuine paper suitability (legibility,
   correct labeling, sensible parameter choices) -- not just "the file was
   created and is non-empty."
3. Commit at least one figure per command to the paper-figures location,
   following whatever the Worldcon 2026 paper's actual structure expects.
4. Document (in this work item's own execution record, and/or the paper
   source) which command/parameters/corpus-revision produced each
   committed figure, so it remains traceable to the input-revision values
   each command already discloses.
5. Fix or explicitly log any real-corpus-scale finding.

## Likely Files

- Whatever the Worldcon 2026 paper's figures directory turns out to be
  (to be confirmed during implementation)
- Possibly minor fixes to `lcats/src/lcats/visualize/*.py` if dogfooding
  surfaces a real bug

## Validation

- `lrh validate`
- Manual review: each of the 4 commands' real-corpus output reviewed for
  paper suitability, not just file-creation success
- At least one figure per command present in the paper-figures location,
  each traceable to its producing command/parameters/input-revision

## Risk Notes

- **This item is sequenced after `-0086`/`-0087`.** It cannot meaningfully
  dogfood `tfidf`/`topics` before those commands exist; `blocked_by`
  reflects this directly rather than leaving it implicit.
- **Paper structure may shift.** The exact commit location for figures is
  intentionally left open pending the paper's actual state at
  implementation time, rather than guessed now and potentially wrong.
