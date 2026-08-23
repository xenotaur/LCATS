---
resolution: "Implemented and merged in PR #378 (commit b72c3ebd)."
blocked_reason: null
blocked: false
id: WI-VISUALIZE-0089
title: Usage documentation and examples for lcats visualize
type: deliverable
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
  - edit_file
  - write_docs
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - implement_new_architecture
  - promote_sidecars
  - modify_lcats_annotate
  - modify_lcats_promote
acceptance:
  - "A documentation page (or README section) exists covering all 4 `lcats visualize` commands (`genres`, `words`, `tfidf`, `topics`): what each produces, its key options, and its preprocessing/methodology defaults (reusing, not duplicating, each command's own `--help` disclosure established by `WI-VISUALIZE-0085`'s help-text acceptance criterion and expected to be followed by `WI-VISUALIZE-0086`/`-0087`)"
  - "At least one concrete, runnable example invocation per command is included, each demonstrating a real (not placeholder) selector/parameter combination against the checked-in corpus"
  - "The documentation explicitly states the input-revision/content-identity disclosure convention every command follows, and how to use it to regenerate or audit a figure"
  - "The documentation location follows this repo's existing documentation conventions (e.g. alongside other command-family docs, or in the package's own README) rather than introducing a new, one-off documentation location"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
artifacts_expected:
  - Documentation file(s) covering lcats visualize (exact path to be determined during implementation, consistent with this repo's existing documentation conventions)
---

# Work Item: WI-VISUALIZE-0089

## Summary

Write usage documentation and runnable examples for the complete `lcats
visualize` command family (`genres`, `words`, `tfidf`, `topics`). This is
item 6 of `WS-CORPUS-TEXT-VISUALIZATION`'s decomposition, and the last item
needed to satisfy the workstream's own "usage documentation/examples exist"
exit criterion.

## Problem / Context

Each individual `lcats visualize` command documents its own preprocessing
defaults in `--help` text (an acceptance criterion `WI-VISUALIZE-0085`
established and `WI-VISUALIZE-0086`/`-0087` are expected to follow), but no
single place currently describes the family as a whole, how the commands
relate to each other, or gives a new user a concrete starting example per
command. This work item closes that gap.

### Prior Art Check

- In-repo: no existing documentation page for `lcats visualize` was found
  at proposal-adoption time (confirmed via the same search run for
  `WS-CORPUS-TEXT-VISUALIZATION`'s own closeout review: no top-level
  README/CLAUDE.md references `lcats visualize genres` or `words` outside
  design/work-item files themselves). This work item is the first to
  create one.
- Sibling repos / external libraries: not applicable.
- Demand: `WS-CORPUS-TEXT-VISUALIZATION`'s own exit criteria are the
  originating request; no other open work item or proposal requests this
  independently.

## Scope

- A documentation page/section covering all 4 commands' purpose, key
  options, and preprocessing/methodology defaults.
- At least one runnable example invocation per command against the real
  corpus.
- An explanation of the input-revision/content-identity disclosure
  convention and how to use it for regeneration/audit.

## Out of Scope

- Implementing or modifying any command's behavior -- this item documents
  the existing, already-implemented family; a documentation gap that
  reveals a real code gap becomes a separate work item, not scope creep
  into this one.
- The dogfooding figures themselves -- that is item 5
  (`WI-VISUALIZE-0088`), a distinct work item; this item may reference or
  reuse example invocations similar to what dogfooding produced, but does
  not depend on committing paper figures.

## Required Changes

1. Identify this repo's existing documentation convention for a CLI command
   family (e.g. how `stats`/`assess` or other existing `lcats` subcommands
   are documented, if at all) and follow it rather than inventing a new
   location.
2. Write the documentation page/section: overview of the 4 commands, their
   relationship (shared substrate, source/analysis/rendering/CLI split),
   key options per command, and preprocessing defaults (cross-referencing
   each command's own `--help`, not duplicating its exact wording
   verbatim where a reference suffices).
3. Include one concrete, runnable example invocation per command, using
   real selector/parameter values (e.g. `--genre fantasy`) rather than
   placeholders.
4. Document the input-revision/content-identity convention and its
   regeneration/audit use.

## Likely Files

- A documentation location to be confirmed during implementation, following
  this repo's existing conventions (candidates: `lcats/README.md`, a
  `lcats/docs/` file, or a package-level README under
  `lcats/src/lcats/visualize/`)

## Validation

- `lrh validate`
- Manual review: each of the 4 example invocations actually runs
  successfully against the real corpus as documented

## Risk Notes

- **Documentation drift risk.** Since this item is sequenced after
  `-0086`/`-0087`, and those commands' own `--help` text is the
  authoritative source for preprocessing defaults, prefer referencing
  `--help` output over duplicating exact wording, to reduce the chance of
  the documentation silently drifting out of sync with a later command
  change.
