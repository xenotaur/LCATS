# Narrative repair checkpoint —2026-10-18 morning

This candidate is **not accepted for integration or corpus regeneration**.

- `narrative-cases.json`: coordinator-reviewed source opening/ending anchors and
  immutable decoded-input identities for eight previously observed differences.
- `narrative-cases-result.json`: all eight complete narrative spans survive;
  seven pass real temporary publication/provenance/reuse checks.42640 fails the
  existing chapter heuristic; exit1 and the failed publication flag are intentional.
  All recorded runner/product hashes match this checkpoint's sources.
- `initial-policy-corpus.json.gz`: verbatim full1,659-input replay before the
  editorial-recognition review repair, using pinned pre-repair parser335855c0 on
  the historical side.1,646 comparisons,13 refusals,1,642 differences. This is
  **not final-source corpus qualification**.
- `initial-policy-summary.json`: descriptive counts and31 changed eligibility
  outcomes. Those include actual retained sections and front-matter false
  positives; individual reviewed dispositions remain outstanding.
- `validation.json`, `canonical-test.log.gz`: final canonical checkpoint checks;
  2,963 tests passed. Expected error-path output in the raw test log is not a suite
  failure. Tests do not override failed corpus acceptance.
- `manifest.json`: byte hashes, including decompressed report/log identities.

Original caches/corpus and earlier measurements are unchanged. Historical decoded
UTF-8 is explicitly distinguished from original HTTP bytes. No Gutenberg requests
were made. The source-anchored audit is reproducible with
`qualify_narrative_cases.py`; complete commands/constraints are in the parent
experiment README. No fresh wheel or final full-corpus replay was performed.

The first independent review found an editorial-prefix narrative deletion, which
the coordinator reproduced and repaired. Its recheck started after its deadline
and stopped; final independent review remains open. See the development runlog and
native execution records for the stop, timing uncertainty and next scope.
