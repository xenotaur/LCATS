# Narrow terminal-notice investigation — 2026-10-22

Status: **completed experiment and review; no product change or acceptance-policy adoption**.
User authorized this bounded investigation and recording its findings in PR #528.
The candidate is an isolated private-rule substitution in an experiment namespace,
not a production cleanup policy. The unchanged product ref is `6a873b611e3958bb9ddad8e84f2ad190831a9da7`.

## Result and interpretation

| Measurement | Result |
|---|---:|
| Archived input population | 1,659 |
| Compared / cleanup refusals | 1,646 / 13 |
| Original old/new normalized hashes reproduced | 3,292 / 3,292 |
| Candidate changes cleanup slice and normalized body | 470 |
| Changed bodies restored to legacy equality | 469 |
| Cleanup-induced differences before / after candidate | 902 / 433 |
| Previously equal bodies made different | 0 |
| Cleanup-refusal changes | 0 |
| Historical body-eligibility changes versus replacement | 1 |
| Historical body-eligibility differences versus legacy | 0 |

The candidate restores *Friend Island* (35401) from 2,620 to 26,080 characters and
restores the historical non-chaptered result for *Competition* (29632). The latter
body also regains exact legacy equality (17,079 characters). This does not establish
literary correctness or exercise publication. *The Dwindling Years* (50103) stays
truncated at 900 characters: its numeric envelope identifier does not corroborate
the title in its notice. The candidate does not solve every causal integration issue.

All 470 changed slices have the same start and an earlier end. Independent review
verified every removed suffix against exact cached bytes, character offsets, the
whole-line grammar and the recorded suffix hash. The other 1,189 cleanup outputs are
unchanged, including 13 refusals. All 744 formerly equal normalized outputs remain equal.
Of 470 affected bodies, 469 restore legacy equality; the other, 32655 (*The Last Gentleman*),
is exactly one leading LF plus the legacy body. That is still an unresolved comparison,
not an approved whitespace normalization or permission to alter product output.

`residual-inspection.json` is a coordinator follow-up inspection, separate from the
independently reviewed full comparison. It groups the 433 residuals mechanically:

- 376 have a whole-line notice in the new grammar, but the accepted envelope uses
  the matching numeric ebook ID rather than its title (including 50103).
- 56 fall outside this single-line notice grammar.
- One has the notice removed but retains the leading-LF difference (32655).

These groups are investigation queues, not qualified rules or editorial judgments.
No claim is made that permitting numeric markers would resolve all 376 cases safely.
No historical dispositions, source identities or canonical stories are changed.

## Exact mechanism and diagnostic intervention

The pinned parser is `335855c04cd7ba936815d2635969d94fdd278c71`, already migrated but
preserving the original body/heading/chapter functions. Both cleaners can select the
same late author-like chunk. The first extraction candidate is then accepted if
`len(final_body.split("\n\n")) > 10` (historical parser line 1291). Empty chunks count.
The retained notice and surrounding blank lines cross that threshold and suppress
fallback; this is not merely the notice's author being chosen as a new heading.

| Input / path | First candidate chars | Double-newline chunks | Fallback | Returned chars |
|---|---:|---:|---|---:|
|35401 legacy |2,540|9|yes|26,080|
|35401 replacement |2,620|13|no|2,620|
|35401 grammar candidate |2,540|9|yes|26,080|
|50103 legacy |818|10|yes|31,972|
|50103 replacement |900|13|no|900|
|50103 grammar candidate |900|13|no|900|
|50103 explicitly named literal removed |818|10|yes|31,972|

For 35401, the double-newline author match is chunk 69 in both original paths, a
narrative passage containing “by her ladylike behavior!” For 50103, both select chunk 152,
the closing Lester del Rey credit. The full trace includes bounded matched excerpts,
first-candidate hashes/tails and all heading decisions. Counters are diagnostic chunks,
not actual narrative paragraphs. Exact previously reviewed anchor-interval failures
can include typography/separator changes and are not automatically narrative loss.

`literal-counterfactuals.json.gz` independently reproduces the earlier conversational
probe: remove only the exact, unique, terminal notice named for 35401 or 50103, then run
the same old extractor. **Both legacy normalized hashes return.** This identifies a
cause, not a general recognition rule. It grants no authority to infer a notice from
an arbitrary numeric marker or delete arbitrary closing text. The general candidate
still requires title-to-title matching and therefore leaves 50103 unresolved.

## Candidate contract

`terminal_notice_candidate.py` loads the unchanged cleanup module into a separate
namespace and extends only `_END_NOTICE`. The existing `End of Project Gutenberg's
TITLE, by AUTHOR` form stays supported; the only added form is:

```text
End of the Project Gutenberg EBook of TITLE, by AUTHOR
```

Existing guards remain: unique corroborated envelope, exact whole physical line,
last nonblank line before its end marker, normalized notice-title/marker-identifier
equality, nonempty author, nonempty remaining content. No wrapped notice, arbitrary
footer, chapter policy, heading repair or metadata API is introduced. Existing author
corroboration is nonemptiness, not catalog-author equality. The module's existing
policy label is inherited in this isolated experiment; it is not a released version.

## Reproduce

From `lcats/` in the historical LCATS project environment, with `PYTHONPATH=src` and
`PYTHONDONTWRITEBYTECODE=1`. Historical gutenbergpy is required only to measure its
old cleanup; do not install it automatically or restore a production requirement.
The relevant imported product modules are bound to their actual worktree paths and
pinned Git bytes, and the legacy cleaner is bound to the earlier recorded hash.

```bash
python ../experiments/10_gettenberg_qualification/scripts/audit_terminal_notice.py \
  CATALOG_CACHE TEXT_CACHE /tmp/NEW_COMPARISON.json
python ../experiments/10_gettenberg_qualification/scripts/trace_literal_terminal_notices.py \
  CATALOG_CACHE TEXT_CACHE /tmp/NEW_LITERAL_PROBES.json
python -m unittest discover \
  -s ../experiments/10_gettenberg_qualification/scripts \
  -p test_terminal_notice_candidate.py -v
scripts/format --check --diff -- \
  ../experiments/10_gettenberg_qualification/scripts/audit_terminal_notice.py \
  ../experiments/10_gettenberg_qualification/scripts/terminal_notice_candidate.py \
  ../experiments/10_gettenberg_qualification/scripts/test_terminal_notice_candidate.py \
  ../experiments/10_gettenberg_qualification/scripts/trace_literal_terminal_notices.py
scripts/lint \
  ../experiments/10_gettenberg_qualification/scripts/audit_terminal_notice.py \
  ../experiments/10_gettenberg_qualification/scripts/terminal_notice_candidate.py \
  ../experiments/10_gettenberg_qualification/scripts/test_terminal_notice_candidate.py \
  ../experiments/10_gettenberg_qualification/scripts/trace_literal_terminal_notices.py
```

Inputs used here:

- Catalog cache `/tmp/gettenberg-dispositions-20261020/cache`, archive SHA
  `358f177c30818027ad93b3478da2248d7996999475d83e59288cee74423050b28`.
- Text cache `/Users/centaur/Tempspace/Projects/LCATS/cache/texts`.
- Original comparison `../gettenberg-qualification-20261018/corpus-after.json.gz`.
- Source anchors `../gettenberg-narrative-20261018/narrative-cases.json`.
- Corpus paths in the original comparison, verified against their recorded hashes.
  These are historical machine-local paths; the experiment requires those pinned
  inputs, not an arbitrary live corpus. Every source gzip and decoded text is verified.

No setup, refresh, download, source/cache/corpus publication or network socket creation
occurs during processing. The corpus runner has a 900-second POSIX alarm and completed
in 608. 522 seconds; literal probes have 120 seconds. Gzip input is limited to 32MiB compressed
and expanded, Git reads to 30 seconds. Output parent must exist; output must be new and
outside source/cache/repository roots. Failures raise without a completed report.
Temporary historical modules are removed. Whole-population output is about 0. 6MiB
compressed; no full story duplicates are archived. These are timing observations,
not performance guarantees. Historical decoded/re-encoded UTF-8 cache bytes cannot
prove original HTTP representation, resource selection or decoding equivalence.

## Evidence and validation

- `corpus-comparison.json.gz`: per-input identities, exact three-way outputs, slice
  evidence, historical body eligibility, trace probes and count summary.
- `literal-counterfactuals.json.gz`: final durable runner's explicitly keyed probes.
- `independent-probes.json.gz` and `independent-literal-counterfactuals.json.gz`:
  reviewer's transient diagnostic outputs, preserved before the literal runner was
  adapted into its durable, path-parameterized form; final literal rows match exactly.
- `review.json`: independent review scope, reviewed source hashes, repaired finding
  and limits. Reviewer recomputed every census count, checked 3,292 archived hashes,
  checked all 470 suffixes, and separately executed the six severe-case cells. Reviewer
  did not execute a second full census and did not approve literary correctness.
- `residual-inspection.json`: separately identified coordinator follow-up described
  above, with all group IDs and exact 32655 comparison; not a second qualified rule.
- `checks/`: captured commands, exit codes and stdout/stderr; `validation.json` records
  issues and final scope checks. Long LRH logs and verbatim help output are gzip-
  compressed without changing bytes. `manifest.json` binds all archive bytes except itself.

Eight deterministic tests pass, including the new numeric-marker exception. Reviewer
also ran six boundary probes. Help and existing-output/missing-cache/protected-output
negative smokes pass. Canonical package format/lint and explicit experiment checks
pass. LRH validation:0 errors /351 existing warnings. No full package suite or installed-
wheel/public-gather qualification was rerun for unchanged product sources.

The initial full-run launch failed before any rows/output because explicit source
routes were omitted; the corrected runner completed. The reviewer independently
identified that P2 and confirmed correction. Two initial Black diff checks failed
because the sandbox denied its local multiprocessing socket; exact authorized retries
passed, with failure and retry logs preserved. No new substantive product scope was
introduced to work around either diagnostic/environment issue.

## Decision boundary

Recommend carrying the minimal title-matched notice extension as a delivery-candidate
repair for later implementation review. It removes about 52% of the measured cleanup
body differences without changing gather algorithms. It is insufficient on its own:
50103 remains a demonstrated provider-triggered truncation. The next narrow question
is what evidence may corroborate a terminal notice when the envelope identifies an
ebook number—e.g. explicitly bound source metadata—followed by another fixed-extractor
comparison. Do not silently drop corroboration or broaden gather extraction to make
that case pass. Keep the remaining 56 other cases and 13 refusals visible; no new
editorial taxonomy is required by these results. A future delivery candidate still
needs metadata/resource and actual gather/usability qualification at its own head.

[Scope audit](../../../../lcats/project/development/gettenberg-scope-causality-audit.md).
[Runlog](../../../../lcats/project/development/gettenberg-development-log.md).
