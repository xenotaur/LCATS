# Gettenberg /gather scope: Kenny meeting brief

2026-10-22. **Proposal for discussion, not an implementation change or merge approval.**

## The decision in one paragraph

Finish replacing gutenbergpy with gettenberg, including the gather regressions caused
by that replacement. Preserve the broader gather improvements we developed for a
separate reconciliation with Kenny when his code becomes available. Stop using full
historical editorial reconciliation as the proxy for provider correctness. Neither
wait for Kenny's code nor silently assume his agreement to our gather architecture.

## What is established

- Catalog, metadata, caching/acquisition, source-aware preparation, caller migration,
  dependency removal and CI work already exist at the PR524 base. They are not yet
  collectively qualified for final main delivery.
- The provider changed more than metadata: conservative Gutenberg cleanup changes
  what reaches the extractor. With identical metadata/input/extractor, two outputs
  shrink from 26,080 to 2,620 characters and 31,972 to 900. We must prevent those failures.
- Our extraction repair then expanded behavior. In case 42640, the historical chapter
  test changes result under either cleaner when the extractor is changed. The later
  readiness/review system flags all eight investigated stories under either cleaner.
- Therefore 1,628 unresolved historical comparisons are not 1,628 demonstrated provider
  defects. The backlog combines provider effects, extraction changes and editorial
  policy. It remains valuable evidence, not a delivery defect count.

The audit's 2×2 probe reproduced all 16 earlier comparison hashes for eight sources.
It is a function-level diagnostic, not whole-corpus or public-gather acceptance.

## Proposed ownership

| Work | Proposed treatment |
|---|---|
| Gutenberg catalog/resources/cache/cleanup and migrated callers | Retain in replacement delivery |
| Replacement-triggered extraction loss, error handling and usability | Our integration obligation; qualify the smallest safe mitigation |
| Chapter/editorial policy, review queues, ordered selections and batch curation | Preserve as separate gather work for later reconciliation |
| Kenny's changes and integration with them | Separate future task when code is available |

The source adapter already supplies typed titles/authors/aliases/subjects/languages,
selected decoded/cleaned text and provenance. That is a useful boundary for discussion;
we are not asking Kenny to adopt our review schema or publication policy.

## Recommended next step

Approve the three-way split and revised qualification criteria in the
[scope audit](gettenberg-scope-causality-audit.md). A subsequent bounded grant can
construct a narrower delivery candidate from the migration seam and selectively bring
forward the cleanup repair and justified integration fixes. Keep PR524/history and all
source/corpus evidence intact. Revalidate the actual candidate before main promotion.

We have not yet established the minimum integration patch. Reverting every gather
change restores known failures; retaining everything ships a gather overhaul. Removing
only review modules also breaks mixed parser/CLI/logging dependencies. This requires
selective construction and tests, not a mechanical revert or blanket bypass flag.

## Questions to settle together

1. Is the source adapter boundary suitable for Kenny's planned gathering work?
2. Which gather semantics should remain stable during provider migration—eligibility,
   body boundaries, naming, output reuse and error reporting?
3. Can we preserve the broad gather work as optional future material while delivering
   a smaller, qualified integration? Which ideas are useful to Kenny independently?

Kenny's answers can refine the interface and future reconciliation; no code transfer
is needed to discuss them. No canonical corpus rewrite, main merge, package release or
current readiness-policy change has occurred in this audit.

## LRH lesson

Locally successful repairs can still expand the task until its acceptance condition
becomes a different project. Add an escalation trigger for accumulating policy/subsystem
obligations, even when each bounded run passes tests and receives approval.

Evidence and detailed caveats: [audit](gettenberg-scope-causality-audit.md),
[experiment archive](../../../experiments/10_gettenberg_qualification/results/gettenberg-scope-audit-20261022/README.md),
[runlog](gettenberg-development-log.md).
