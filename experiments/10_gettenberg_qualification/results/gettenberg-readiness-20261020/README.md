# Publication readiness qualification — 2026-10-20

This run implements the human-approved explicit review outcome, not whole-corpus
acceptance. See the [readiness contract](../../../../lcats/project/development/gettenberg-readiness-contract.md)
and [runlog](../../../../lcats/project/development/gettenberg-development-log.md).

## Final candidate

Product `dfbe837e54380f9ec7d2f015515e9ccd42622afe` is authoritative. Use
`census-final.json.gz`, `full-corpus-final.json.gz`, `readiness-cases-final.json.gz`,
`narratives-final.json.gz` and `review-decisions-derivation-bound.json` to reproduce
it. Unsuffixed files below preserve initial measurements. The first census
predates a final readiness-source edit; its source hash differs while classifications
match. All final report source ledgers match current product/runner bytes.

Independent review found one P2: unchanged text could retain approval across an
extraction/chapter policy change. The coordinator reproduced it; a regression
failed three drift subcases before repair. Full pre-readiness provenance is now
bound into review identity. A bounded independent recheck confirmed resolution,
including offset/diagnostic drift probes, with no new findings. Eight previously
reviewed recipes were explicitly reissued after verifying unchanged source,
metadata, extraction/chapter evidence, candidate/assessment and selected text.
Old decisions remain archived and correctly fail at the repaired identity.

Final validation: 2,998 canonical tests pass (97.466s), 90 focused repair checks,
package format/lint and all 15 experiment runners' format/lint. LRH has zero errors
and 351 pre-existing warnings. The wheel and installed package contain exactly
the same 169 Python modules as the source tree; no extra modules or legacy/VCS
dependency. Installed withholding/reviewed publication, CLI help and pip check
pass outside the checkout. A fresh venv resolved declared dependencies for the
initial candidate; the repaired wheel replaced it without dependency changes.
Its dirty version suffix reflects concurrent control-plane edits; exact product
byte equality is verified separately. The first nonisolated build failed due to
old packaging in the development environment; standard isolated builds succeeded.

`migration.json` retains the historical equality probe: all five outcomes match,
but three published JSON comparisons differ in provenance. It remains
`qualified:false`; the assertion was not relaxed. Readiness/publication acceptance
uses the separate tests and source replays, not this negative equality result.

## Initial measurements and unchanged classifications

- `census.json.gz`: 1,659 immutable cached sources: 1,640 needs_review,
  13 cleanup_refused, five automatically ready, one ineligible. The ready IDs are
  9222, 1761, 1762, 37146 and 1952. A ready classification means no unresolved
  policy cues, not proof of literary purity. No accepted corpus files were written.
- `pre-gate-census.json.gz`: earlier pure-assessment census before default gate
  activation, before boxed-note/transcription/bibliography cue repairs. Its nine
  ready results are historical; the later census supersedes its classifications.
- `full-corpus.json.gz`: full legacy/current comparison, 1,646 comparisons and
  13 cleanup refusals, 1,642 body differences. `preservation.json` verifies every
  input and candidate/normalized body hash equals the previous editorial run.
  This gate changes publication disposition, not candidate extraction. The
  1,642 differences still lack complete accepted editorial dispositions.
- `readiness-cases.json` and `readiness-cases-result.json.gz`: 28 source-bound
  cases: 13 temporary publications (eight explicitly reviewed, five automatic),
  14 preserved review candidates, one corroborated multi-work exclusion. Actual
  gather outcomes, candidate report equality, provenance and unchanged reuse pass.
- `review-decisions.json`: eight coordinator-authored reviewed selections,
  attributed to an agent rather than a human. Each selects complete paragraphs
  containing the previously reviewed unique narrative anchors. 22579 deliberately
  retains an interior illustration label, acknowledged in its rationale. These
  source identities describe historical decoded UTF-8 caches, not original wire
  bytes, and cannot authorize live original-byte publication.
- `reviewed-narratives-fixed.json.gz`: all eight complete anchor spans survive,
  pass explicit reviewed publication into temporary buckets, and reuse unchanged.
  The preceding attempt exposed tuple/list JSON representation drift in finding
  spans; the product now emits JSON-compatible lists and regression tests cover it.

Source and runner SHA256 ledgers are inside each report. Gzip files preserve the
original JSON bytes; the manifest identifies compressed and decompressed bytes.
Catalog snapshot SHA256 is
358f177c30818027ad93b3478da2248d7996999475d83e59288ee74423050b28.
Network bytes are zero. Historical evidence remains unchanged. The decoded cache
is not evidence of wire encoding or historical HTTP receipts.

## Independent source inspection

A cold read-only source audit checked the eight narrative cases and five disputed
chapter cases against decoded hashes and actual text. It found retained notes,
publication/illustration/advertisement matter and real named divisions. In
particular, 27612 has genuine italic scene headings despite misleading counted
all-caps evidence; it is not established as unchaptered. 32878 has six genuine
named sections. Both remain needs_review. 39216's numbered commercial list and
24936's SILENCE illustration caption do not alone establish narrative chapters.
63230 has corroborated compact contents and remains ineligible. The source audit
is evidence for these decisions, not a blanket disposition of similar sources.

## Reproduction

Use the commands in the [experiment README](../../README.md), fresh output paths,
the recorded local catalog/cache snapshot and this candidate's source ledgers.
`assess_cached_readiness.py` performs the census; `qualify_readiness_cases.py`
consumes the case/decision manifests; `qualify_narrative_cases.py` uses the preserved
2026-10-18 narrative anchors plus these decisions. The full comparison used
`--baseline-parser-ref 335855c04cd7ba936815d2635969d94fdd278c71`.
Do not substitute these decisions for independent review of other source contexts.

Final logs, validation.json, source-ledger.json, wheel-final.json and manifest.json
record validation and provenance. Full candidate bodies are not duplicated here.
