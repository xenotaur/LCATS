# Reporting clarity and live ebook 1367 reproduction — 2026-10-26

Human-authorized follow-up in PR #534. Product and runners are committed at
`39e5e1ac7f1f866792e47b31fa2c2f807173c9f1`, based on `f32e45fd`.
No main merge, corpus regeneration, extraction change or alternate-route repair.

## Findings

The user's existing run recorded 1,661 ready, 3,831 skipped, zero cleanup refusals
and zero unavailable inputs. Its 1367 event was `story_ready`. The existing
Findelkind output predated the run (August 1), so the parser returned it before
source acquisition/cleanup. Selected original events are preserved in
[warm-run-observation.json](warm-run-observation.json); this was not rerun.
Zero observed HTTP failures does not prove download availability, and reused
outputs are not requalified under the new cleanup policy.

The first isolated source-tree run at 22:35 UTC and final installed-wheel run
both made exactly one real GET to:

```text
https://gutenberg.pglaf.org/cache/epub/1367/pg1367.txt
```

Both received HTTP 404, finished the one-item batch, returned CLI status 2, wrote
zero stories and cached no source/error body or partial acquisition file. The
final installed run reported:

```text
Gathering incomplete: cleanup refusals or unavailable sources remain.
mass_quantities: 0 ready (0 newly written, 0 existing outputs reused), 0 skipped, 0 cleanup refused, 1 download attempts returning HTTP 404
```

Exactly **two live requests** were made in this follow-up (one per experiment).
No retry, redirect, alternate host, format fallback or full metadata download.
This confirms Kenny's missing selected representation and the per-item repair;
it does not recover ebook 1367 or establish availability at another endpoint.

## Isolation and reproduction

[Runner](../../scripts/reproduce_1367.py) documents invocation and bounds. It
opens the original catalog read-only, retains the exact [1367 RDF](1367.rdf),
and builds a one-record catalog in a disposable directory. Output, source cache,
logs, working directory and data/corpora environment roots are isolated. The real
CLI and HTTP stack execute; only the input list is replaced with `[1367]`, and a
pass-through observer allows at most one request to the selected URL. A POSIX
120-second alarm bounds each run; completed temporary state is removed.

The original catalog's size/mtime and Findelkind SHA-256 match before and after
both runs. We do not claim a full hash census of the shared data/cache trees.
No writer was given those roots; the existing story was fingerprinted only.
Reports retain original catalog identity, RDF hash, module hashes, request URL,
status, CLI text, logs, output/cache state and preservation observations.

- [Initial source-tree observation](initial-source.json) and [events](initial-source.jsonl).
  This preceded the final repeated-ID attempt-count field; its module hashes
  identify that intermediate state. It is not substituted for final validation.
- [Final installed observation](final-installed.json) and [events](final-installed.jsonl).
  All six recorded loaded-module hashes match the committed product.

## Reporting contract and verification

Ready output counts partition unique IDs into newly written and existing outputs
reused. A write can use cached source bytes; it is not necessarily a download.
An ID written then repeated remains written in the aggregate. Per-event
`disposition` still records what each invocation did. A concurrent writer winning
publication is correctly reported as reuse. Existing tuple-returning
`gather_story` and pair-returning `gather_stories` APIs are preserved.

`http_404_attempts` counts actual observed failures, including repeated IDs;
`unavailable` retains unique IDs. No status or continuation policy changes.

- Canonical `scripts/test`: **2,979 tests pass in 101.177s**, clean output.
- Focused final live-gather tests: 35 pass; includes mixed cached-source/new-output
  reporting, repeats, existing-output acquisition bypass and publication races.
- Canonical format/lint pass; both changed experiment runners explicitly pass
  Black/Ruff. Their smoke checks are the executed CLI/live experiments.
- LRH validates with zero errors and 354 preexisting combined-tree warnings.
- Clean wheel from committed source, force-reinstalled into the prior isolated
  dependency environment (not a fresh dependency installation); `pip check` passes.
  Qualification version `0.1.0+qualification.reporting` is not release-version proof.
- [Wheel closure](wheel-closure.json): all 165 Python and two JSON files match
  committed source, wheel and physical installation. No gutenbergpy/VCS/direct-URL
  dependency. Both fixture CLI reports verify 98 loaded-module hashes.
- Installed [HTTP 404](installed-cli-404.json) and
  [cleanup-refusal](installed-cli-refusal.json) scenarios each write two successful
  outputs initially, reuse both byte-identically on repeat, and return status 2
  both times. HTTP scenario requests only the failed input on repeat. Synthetic
  fixture evidence is separate from the actual one-item Gutenberg observation.

Raw validation/build/install logs are compressed alongside these reports.
[Artifact manifest](artifact-manifest.json) fingerprints the report/data/log files;
it excludes itself and this README. Historical cohort/body acceptance evidence
and its limitations are unchanged. Exact final-head CI is tracked in PR #534;
this packet does not predeclare hosted checks or main promotion.
