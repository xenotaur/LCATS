# Human milestone: narrative preservation versus publication readiness

2026-10-18; WI-GETTENBERG-0010; PR524. **Recommended explicit review outcome
approved by the human on 2026-10-20.** The human subsequently authorized the
readiness implementation/measurement run recorded in the charter and runlog.
This approves the direction below, not corpus acceptance, integration, or main
promotion. Historical findings below describe the 2026-10-18 checkpoint.

## What the new evidence establishes

The opening-prefix policy fixes the reproduced late-title/byline truncations.
All eight reviewed narrative spans now survive actual temporary publication.
Chapter assessment exposes paragraph evidence, excludes whole metadata headings
(including curly/straight quote variants), and corroborates compact contents lists
against later headings. The two cold-review P2 findings have coordinator-verified
red/green fixes. Neither fix changed any of the 1,646 compared bodies.

The [archived results](../../../experiments/10_gettenberg_qualification/results/gettenberg-editorial-20261018/README.md)
identify every source, runner, output and limitation. 2,976 canonical tests pass;
the fresh wheel is independent of gutenbergpy and matches all 166 product modules.
These are implementation/measurement results, not corpus acceptance.

## What remains unresolved

There are 1,642 changed bodies and 13 conservative cleanup refusals. Every material
body difference still needs an explicit reviewed disposition. Preserving text does
not establish that all retained material belongs in an analysis-ready story.

Source-grounded chapter review leaves15 rejections. Ten contain actual sections or
multiple works under the existing collection filter. Five are false positives:

| ID | Source evidence counted as chapters |
|---|---|
|27612|Wrapped title fragment, publisher and the narrative exclamation THE BABY!|
|70391|Opening magazine label and two signs quoted within the narrative|
|59724|Advertisements for other books before the story|
|39216|A numbered advertisement list, illustration and publisher labels|
|24936|Copyright/illustration/page labels and the narrative caption SILENCE!|

The 16 corrected metadata-heading cases are not automatically approved bodies.
Likewise, detecting real sections does not prove a work has no literary value;
it applies the existing collection filter. This run did not redefine that filter.

More fundamentally, a source consisting of title, author, “Transcriber’s Note”
and 15 correction paragraphs passes current length/chapter eligibility and is
actually published in the temporary probe. Its provenance warns that an editorial
note was retained, but that warning does not stop publication. The independent
review and coordinator reproduced this. It is not an established introduced
regression; it exposes an acceptance claim the current mechanism cannot support.

The mechanism is visible in [story_body.py](../../src/lcats/gatherers/story_body.py)
and [parser.py](../../src/lcats/gatherers/parser.py): unknown material is preserved,
then eligibility considers chapters and paragraph count. These are different
questions from whether the retained span is narrative. Existing
[corpus boundary detectors](../../src/lcats/analysis/corpus/detectors/boundary.py)
produce warning findings and use heuristic byline/title patterns; they are useful
review cues, not a safe deletion oracle. Existing
[overrides](../../src/lcats/gatherers/overrides.py) are replayable substitutions
applied after eligibility; they do not currently supply an extraction-readiness
contract or source-hash-bound boundaries.

## Recommended decision

Separate **preserved candidate text** from **publication readiness** in the gatherer
contract. Keep original bytes and inspectable spans. Add an explicit `needs_review`
outcome for identified unresolved editorial/boundary evidence, separate from
metadata ineligibility, cleanup refusal and operational failure. Such candidates
must not silently become ordinary accepted story outputs. Keep clean/qualified
stories and unrelated sources usable; summarize review needs in batches rather
than introducing a prompt for every book. Do not treat download approval (`--yes`)
as approval of uncertain content.

Combine that default with narrowly tested editorial templates and reviewed,
source-bound annotations where necessary. Recognized credits may improve automatic
coverage, but broad transcriber-note/byline deletion must not return. An explicit
annotation must fail visibly when its source or anchor identity changes. First
measure prospective review volume on the same immutable1,659-input corpus; do not
promise a coverage target before that census.

This is a proposed direction, not an implemented API. The existing repair scope
says: “broad new refusals would need a human decision.” Enabling a new default
publication gate changes first-use behavior and may affect many stories, so the
bounded coordinator adapter does not substitute for that decision.

## Alternatives and tradeoffs

| Option | Benefit | Limitation |
|---|---|---|
|Explicit review outcome plus conservative recognition (recommended)|Observable uncertainty; protects publication without deleting source; reusable across collections|New behavior and review volume need human approval and measured qualification|
|Curate source-bound recipes for the existing corpus first|Concrete, auditable dispositions; can improve current coverage|Maintenance cost; cannot alone establish behavior for arbitrary future ebooks|
|Publish uncertain candidates with warnings (current effective behavior)|Low friction and preserved text|Does not meet the approved editorial-only/uncertainty acceptance boundary; would require an explicit scope change|
|Restore broad legacy stripping|Could resemble older outputs|Disqualified by reproduced narrative loss; old corpus equality is not ground truth|

## Proposed next bounded scope after the decision

1. Specify readiness states, provenance and batch/CLI behavior; measure the impact
   before enabling a broad default refusal. Reuse existing Finding/span concepts
   where suitable without treating warning regexes as deletion instructions.
2. Cover the authored editorial-only negative control, five false chapter cases,
   eight narrative-preservation cases and genuine multi-work rejection. Keep
   source identity and full-span preservation in every positive recipe.
3. Produce per-input reviewed dispositions for material differences, retaining
   unresolved cases explicitly. Rerun publication, canonical checks, fresh-wheel
   evidence and independent review before considering internal integration.

Main promotion and terminal closeout remain separate human gates. This milestone
neither resolves WI0010 nor changes its acceptance criteria.
