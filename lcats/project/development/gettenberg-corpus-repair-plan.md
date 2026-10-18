# Corpus compatibility repair scope after WI0010 qualification

Status: implementation authorized by the renewed bounded run on 2026-10-18;
**not yet accepted corpus output**. The WI0010 qualification run discovered a blocking composition problem
between conservative cleanup and the existing heuristic story extractor. Keep
WI0010 and main promotion open until this is repaired and independently reviewed.

## Observed evidence

The pre-repair comparison uses 1,659 existing mass_quantities stories and matching
legacy decoded UTF-8 cache entries, with current metadata on both paths. It compares
old cleanup/new cleanup followed by the identical current extractor and replayable
normalization. 1,605 inputs reached comparison; 54 were explicitly refused. Among
compared inputs, 892 bodies differ: 884 preserve the old body as an exact prefix and
append text; 8 change an earlier position. The source bytes/corpus files are unchanged.
This is not proof that the old extractor's output is always correct.

The suffix triage contains 687 end-notice starts, 122 transcriber-note starts,
57 byline/separator starts and 18 other starts. These are mechanical review labels,
not a blanket decision to delete those suffixes. The eight earlier differences
are IDs 22579, 23148, 35401, 70645, 23104, 50103, 42640 and 32655. Two particularly severe
examples deserve explicit narrative-preservation tests:

- **35401, Friend Island:** old normalized extraction 26,080 characters; new 2,620.
- **50103, The Dwindling Years:** old 31,972; new 900, beginning at a transcriber note.

The existing `find_author_line` and `find_title_line` deliberately return the last
matching location, and `body_of_text` uses those locations to discard a prefix.
Retaining footer metadata changes the extractor's input and can change its heading
selection. This is a source-grounded mechanism to investigate, not yet proof that
one patch explains every difference. Reproduce each earlier-position change before
choosing a repair. The old path also appears to omit legitimate content in at least
some cases; equality with it must not become the only acceptance oracle.

## Recommended boundaries

Keep pure gettenberg cleanup conservative and evidence preserving. It should still
return original text, selected span, markers, diagnostics and policy identity.
Do not solve this by pasting upstream marker lists, deleting arbitrary text after
“End”, relaxing mismatched markers, or silently trimming every differing suffix.

Put narrative/editorial interpretation in the gatherer layer when it needs title,
author or collection context. Consider a small explicit preparation result carrying
recognized editorial boundaries and diagnostics before heading/body extraction.
Alternatively tighten heading selection so corroborated footer metadata cannot
become a title/author boundary, then remove only clearly identified editorial
suffixes. Prefer the smallest approach that preserves narrative and supports
transparent diagnostics. Record the chosen design before implementation.

Do not treat transcriber notes, bylines, footnotes or typography notes as universally
discardable. Separate those policies from Gutenberg license/end delimiters. Where
confidence is insufficient, return an explicit review/refusal outcome rather than
publishing a short fragment as a valid story. Define that operational behavior
before changing it; broad new refusals would need a human decision.

## Required acceptance and evidence

1. Independently authored regression fixtures reproduce heading/footer interference,
   title/author mentions inside narrative, wrapped notice text, genuine bylines,
   trailing transcriber/typography notes and ambiguous boundaries. Assert expected
   narrative paragraphs/ordering, not only equality to the old implementation.
2. Reproduce all eight earlier-position changes on the immutable cached inputs and
   document the correct expected narrative boundaries. Retained corpus is evidence,
   not automatically an oracle; preserve justified repairs and explain corrections.
3. Rerun all 1,659 comparisons with the new source hashes. Every material difference
   has an explicit reviewed disposition; no bulk suppression or normalized-away
   comparison. Keep cleanup refusal, eligibility rejection and operational failure
   separate from a matched story. Record the remaining wrapped/mismatched forms.
4. Exercise actual gather publication on representative real cached-text replays
   with provenance honestly labeled as historical decoded input, plus authored
   original-byte acquisition fixtures. Prove a footer-only/short fragment cannot be
   silently accepted and an existing corpus bucket is never overwritten by tests.
5. Preserve first-use/offline/source isolation, original bytes, explicit policy and
   versioned provenance; run canonical checks, focused experiment tests and cold/
   hosted review. Rebuild installed-wheel evidence for changed product sources.
6. Reconcile WI0010's matrix only after these checks pass. Its pre-integration gates
   remain unchanged; a partial qualification PR stays unmerged. Human approval is
   still required for eventual main promotion and terminal closeout.

The current run's narrow v2 cleanup change recognizes comma-form Gutenberg banners
and exact END: FULL LICENSE separators. It deliberately does not implement this
broader repair. Its before/after reports quantify the smaller change separately.

## 2026-10-18 investigation checkpoint

The renewed run stopped before implementation because its read-only audit
assignment exceeded its deadline and the cumulative worker allowance. The execution
record and runlog retain the overrun and preliminary source observations. This
plan remains unimplemented; no new regression or corpus acceptance evidence was
produced. Continuation requires a new grant under the charter's stop rule.
