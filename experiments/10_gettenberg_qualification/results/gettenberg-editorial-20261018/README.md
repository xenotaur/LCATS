# Editorial/chapter qualification checkpoint —2026-10-18

Product commit `68156dbc39e9194d294c70bdc5d4048721cbae71`. This remains an
**unaccepted checkpoint**, not permission to regenerate or promote the corpus.

- `corpus.json.gz`: exact final repaired full replay: 1,659 inputs, 1,646 comparisons,
  13 cleanup refusals, 1,642 changed normalized bodies, 15 chapter rejections.
  Runtime 210.403s. No new Gutenberg requests or canonical output writes.
- `corpus-summary.json.gz`: one review-index row per input. Its classification labels
  are mechanical triage; the 1,642 body differences are still unaccepted. Metadata
  eligibility, body rejection and publication rejection remain separate.
- `narrative-cases-result.json`: all eight existing source-anchored narratives
  survive completely and pass actual temporary publication, provenance equality
  and existing-output reuse. The anchors remain in the earlier narrative results.
- `chapter-dispositions.json`: coordinator source annotations for 31 cases with
  chapter evidence before or after metadata exclusions on the final body. 16 weak
  heading rejections disappear; 15 remain: 10 source-supported divided works or
  collections and 5 editorial false positives. This is classification review, not
  acceptance of those bodies or independent review of all annotations.
- `publication-probes.json`: coordinator manual checks of actual temporary
  publication. 44327 publishes after the quote-matching fix; 63230 remains rejected
  as two works. An authored long editorial-only input still publishes: that probe
  is explicitly failed qualification, not a passing safety test. It records the
  complete authored input, exact sources and observation for reproduction.
- `wheel.json`: all 166 wheel/installed Python modules equal candidate sources;
  no extra modules, legacy/VCS requirements or installed gutenbergpy. A new venv
  resolved declared dependencies, then the repaired wheel replaced the initial
  candidate without dependency changes. Outside-checkout smoke, CLI help and
  `pip check` passed. Wheel identity is recorded separately from Git identity.
- `validation.json`, `canonical-test.log.gz`: 2,976 canonical tests passed 82.217s;
  package plus 13 experiment runners pass format/lint; LRH: 0 errors / 351 existing
  warnings. 191 focused tests passed after two independently found P2 repairs.
- `source-ledger.json`: exact final product and runner hashes. Against the earlier
  full-snapshot qualification ledger, only gatherers/parser.py changed and
  gatherers/story_body.py was added. Earlier catalog/resource/cleanup measurements
  are reusable for unchanged components, not as acceptance of changed extraction.
- `pre-contents-corpus.json.gz` and `pre-review-corpus.json.gz`: untouched earlier
  replays from this run. Neither qualifies the final source. The review repairs
  changed zero extracted or normalized bodies across all 1,646 comparisons.
- `manifest.json`: compressed and decompressed byte identities.

The [experiment instructions](../../README.md) document canonical runner commands,
inputs, limits and failure semantics. Use the final corpus runner with pinned
baseline 335855c0 and the existing eight-case manifest. Source quotes in chapter
annotations address the final report's `new_extracted_sha256` and paragraph basis;
verify them by decoding the identified cache entry, applying cleanup and
`story_body.extract`, then `body.split("\n\n")`. Truncated excerpts are labeled.
These manual annotations are not a new classifier or silently generated approval.

The two real publication probes use the existing narrative runner's
`HistoricalText`/`HistoricalSource` with the recorded decoded hashes, followed by
`inspect_story` and `gather_story` in a TemporaryDirectory. The authored limitation
probe uses `LiveGatherTests.acquire` with its recorded input, then the real offline
`run_gather`; it is a manual negative-control observation, not a portable standalone
runner or normative unit test locking in the defect. No archival executable is
placed in the control plane.

See the [human milestone](../../../../lcats/project/development/gettenberg-editorial-milestone.md)
for the unresolved publication-policy decision and proposed next scope. The cold
review verified the earlier candidate and found two P2s; the coordinator reproduced
and repaired both. No independent re-review of those repairs is claimed.

The per-input review index was relocated from `corpus-summary.json` to
`corpus-summary.json.gz` without changing its decompressed bytes, keeping generated
rows out of the code-review diff. No measurement or disposition changed.
