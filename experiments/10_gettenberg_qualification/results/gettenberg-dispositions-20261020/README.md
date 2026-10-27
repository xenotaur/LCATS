# Source-disposition tranche — 2026-10-20

Continues WI-GETTENBERG-0010 / PR524 from `3d01fb82`. This is eight explicit
source reviews and a reproducible evidence ledger, not whole-corpus acceptance.
No library behavior, collection definition or canonical corpus was changed.

## Outcomes

See [source review](source-review-notes.md) and exact source anchors in
[review inputs](reviews-final.json). Reviewer attribution explicitly identifies
the Codex agent; none of these records is a claimed human signature.

- Six exclusions:27612,61198,64292,27709,61353,32769. Positive named/numbered
  narrative structure violates the existing unchaptered collection requirement.
  Several old bodies are truncated;27709 and32769 retain trailing advertisements.
  Structural review does not claim a complete literary reading of those six works.
- One approval:23762, Blessed Are the Meek, complete narrative reviewed. Select
  candidate Unicode [619,10495), 9,876 characters. It exactly equals the retained
  corpus body except for the last 10 characters (`\n\n\nTHE END`). The candidate
  also has 619 leading characters and 93 trailing characters of non-narrative
  matter; the latter includes the Gutenberg end notice. Original bytes retained.
- One deferral:63889, The Luminous Blonde, complete narrative reviewed. An interior
  illustration caption cannot be removed using one contiguous selection without
  losing story text. The old corpus already includes that caption. No approval.

The [reconciliation](reconciliation-repaired.json.gz) binds all eight judgments to
source/candidate/assessment/disposition/corpus identities and exact source excerpts.
All eight belong to the 1,642 changed-body set. Seven approve/exclude dispositions
are covered by this tranche; 1,635 changed IDs are **not covered by this tranche**,
including the deferred case. Full ID lists are retained. Do not subtract the eight
prior approval smoke cases without separate historical-difference reconciliation.
Neither changed bodies nor needs_review counts are counts of proven bad stories.

The 8-case actual publication check passes: one temporary publication, seven
needs_review outcomes. Exclude/defer are audit intent, not operational filtering;
they neither change membership nor suppress gather, and they cannot publish.
Temporary publication buckets are removed by the runner.

## Validation and reproduction

Use the [experiment instructions](../../README.md#source-disposition-tranche-reconciliation).
Original inputs are the pinned archive 358f177c30818027ad93b3478da2248d7996999475d83e59288ee74423050b28,
historical decoded UTF-8 gzip text cache, and unchanged mass_quantities collection.
Baseline census/comparison: `../gettenberg-readiness-20261020/census-final.json.gz`
and `full-corpus-final.json.gz`. Source anchors count exact decoded characters
(including CRLF); candidate spans count normalized candidate Unicode characters.
These historical approvals do not authorize original-wire acquisition bytes.

The previous /tmp catalog/queue were absent. Local CatalogManager.setup rebuilt
the pinned archive in 495.059s with sockets disabled and a 600s alarm. Queue recovery
reproduces all 1,659 statuses/identities and prior ten intents in 19.796s. No downloads.
Use cumulative-decisions.json and cumulative-annotations.json with
qualify_review_workflow.py to reproduce the new queue/dispositions. Feed its queue
and this directory's named dispositions plus reviews-final.json into
reconcile_review_tranche.py. Use cases.json and exported-new-decisions-final.json
with qualify_readiness_cases.py for actual publication/withholding. All outputs
must be new and outside canonical data. The runner's documented smoke tests are
part of this tranche's validation, not implicitly covered by package lint.

Final validation: 3,034 canonical tests pass in 97.312s; seven focused evidence
tests pass. Earlier 3,033-test evidence is retained as pre-repair history. Package
format/lint and explicit runner Black/Ruff checks pass. Initial focused test failure
was a wrong authored-fixture opening string; fixed to the actual fixture text,
with failure log preserved. A sandbox Ruff cache permission failure was rerun
with --no-cache successfully. No production fixes or assertion suppression.
The first approval rationale omitted the trailing Gutenberg notice; superseded
rationale is retained, final record is explicit, and publication was rerun using
the final export. The chosen span and narrative bytes did not change.

Post-run hashes check all 1,659 original compressed sources and canonical files
against the baseline. Product modules are unchanged from the last qualified wheel;
no fresh wheel qualification is claimed for this experiment-only addition.
The [independent review](review.md) found one P2 coverage-validation defect.
Coordinator reproduced and repaired it; narrow independent recheck is clear.
Final hosted status is recorded separately in the PR checkpoint.
WI0010, PR integration, main promotion and terminal closeout remain open.

Final cumulative replay completed in 20.165s with unchanged
source classifications: 1,640 review / 13 refusal / 5 ready / 1 ineligible. Inventory
is 1,622 unreviewed / 9 approve / 7 exclude / 2 defer, zero conflicts. The ten earlier
intents are replayed inputs; the eight named reviews are this tranche's new work.

## Final repair evidence

The first runner could silently omit an unreviewed comparison row with missing
body_equal. Actual archived data was intact; a deliberately damaged copy reproduced
the under-count. The repaired runner validates every population row, source/corpus
binding and supplied totals before deriving coverage. Red/green logs and regression
tests are retained. Final reports are reconciliation-repaired.json.gz,
repaired-workflow.json.gz and publication-repaired.json.gz; their runner hashes
match the independently rechecked code. Earlier reports remain historical evidence.
The source decisions, selected story bytes and all population counts are unchanged.

LRH validation initially ran from the repository root and reported missing focus;
rerunning from the required lcats/ package directory passes (zero errors /351
existing warnings). Two local edit attempts failed before the intended final
operation because of a wrong relative path/name; corrected commands completed.
No source/corpus edits occurred. These operational slips motivate pinning cwd and
keeping small reusable evidence runners; they are not product test failures.

Population ledgers are losslessly gzipped to keep the PR diff reviewable;
compression-map.json preserves old/new names and expanded hashes.
