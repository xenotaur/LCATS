# Batch review throughput checkpoint —2026-10-20

Status: recommendations approved by the human on 2026-10-21; the scoped implementation and qualification are recorded
in the result checkpoint below. The original measurement below is preserved. The human approved narrow rules with per-input evidence and keeping
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

## Approved scoped implementation contract — 2026-10-21

Implement ordered retained spans with a v2 review decision. Preserve v1 record
bytes and accept them as single-span decisions. A v2 selection partitions the
unchanged Unicode candidate into ordered retained ranges and evidenced omissions;
no overlaps, reordering, substitution, invented separators or silent normalization.
Each omission records kind, reason, evidence and exact text hash. Construction from
omissions derives retained ranges; validation checks the complete partition and
output hash. Existing normalization remains a separate downstream operation.

Confirmed publisher blurbs may leave the narrative body only with explicit evidence;
retain their exact text/source range/identity/attribution separately in published
editorial metadata. Ambiguous opening text remains unresolved. No general classifier
or position-based blurb rule is authorized. The first automated extension removes
only complete paragraphs matching the finite publication-notice grammar, retaining
all surrounding non-notice text and existing separators. This establishes a safe
transformation, not publication or historical acceptance.

A rule proposal has no approval authority. Explicit approvals still require the
separate readiness/historical accounting gates; surviving findings and unexplained
differences stay unresolved. Keep existing integration/main/corpus gates.


## Implementation checkpoint — 2026-10-21

[The scoped result](../../../experiments/10_gettenberg_qualification/results/gettenberg-ordered-20261021/README.md)
qualifies v2 selection/publication and the conservative interior notice rule. All734
recognized notice transformations preserve remaining characters;216 resulting bodies
pass mechanical checks. Historical resolutions stay8 /1,634 unresolved; no automatic
blurb classification or new publication approval follows from those counts. Existing
integration/main/closeout gates remain open. Further work can now express safe interior
edits, but still needs positive evidence for surviving editorial roles and explanations
of every material historical difference.
