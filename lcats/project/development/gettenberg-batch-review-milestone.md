# Batch review throughput checkpoint —2026-10-20

Status: measured direction for discussion; no new extraction or corpus policy is
approved here. The human approved narrow rules with per-input evidence and keeping
exceptions unresolved. This checkpoint tests that approach against the whole corpus.

## What the experiment establishes

A complete 1,659-input ledger can be computed in seconds from cached inputs. The
pipeline checks every input/source identity, prior disposition, exact transformation
and historical comparison. Review effort can be organized around tested rules with
individual proof records; machine replay is not the current throughput bottleneck.

The first narrow grammar finds 734 complete publication notices. Of those, 688 are
interior to the candidate, after other text; 46 are at a boundary. Twelve boundary
selections pass readiness plus retained-label checks, but only one also fully explains
the historical difference. Apparent blurbs survive in several of the others. These
are observed counts for this finite grammar, not recall estimates or labels for all
sources. Exceptions are not accepted to achieve a target coverage percentage.

## Why more identical runs would not solve the problem

The current review decision selects one contiguous span. Removing an interior note
would require discarding text on one side, whose role may be narrative, a blurb,
credits or other matter. A familiar notice does not establish that the surrounding
text is disposable. Moreover, readiness is a cue detector, not a literary oracle;
passing it does not explain an unmatched historical difference.

## Recommended next decision

Before another disposition tranche, decide a scoped extension to source-bound review:

1. Consider ordered retained spans, with explicit omitted spans and exact reconstruction
   evidence. This could remove a fully recognized interior editorial block while
   preserving every other character. It needs a versioned decision schema, stale-source
   rejection, publication integration and narrative-preservation qualification.
2. Decide how the target collection should treat publisher blurbs and similar material:
   retain separately as editorial metadata, omit only with explicit evidence, or keep
   affected candidates unresolved. Do not silently label all opening prose editorial.
3. Keep transformation qualification, collection publication readiness and historical
   migration acceptance separate in the ledger. If library delivery should be separable
   from complete corpus curation, approve that as an explicit change to WI0010's gates.

Ordered spans alone do not automatically resolve 688 cases: other material and other
historical differences may remain. The recommendation is a concrete design milestone,
not higher agent concurrency or hundreds of repeated tiny manual-review runs. Main
promotion, integration and canonical corpus changes remain outside this grant.
