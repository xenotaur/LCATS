# Ordered retained spans qualification — 2026-10-21

WI-GETTENBERG-0010 / PR #524 continuation from c90b3fc3. The human approved
versioned ordered retained spans, confirmed blurbs preserved separately, ambiguous
cases unresolved, and a longer overnight bounded run under six hours. The
[approved milestone](../../../../lcats/project/development/gettenberg-batch-review-milestone.md)
records the contract. No integration, main promotion or canonical corpus changes.

## Results

| Measurement | Result |
|---|---:|
| Immutable corpus inputs checked | 1,659 |
| Qualified exact notice transformations | 734 |
| Two retained spans (interior notice) | 688 |
| One retained span (boundary notice) | 46 |
| Selected readiness and retained-label checks pass | 216 |
| New historically reconciled approvals | 0 |
| Existing historical resolutions preserved | 8 |
| Historical changed bodies still unresolved | 1,634 |

Full final measurement takes 22.722 seconds. All 734 transformations remove only
complete paragraphs matching the existing finite publication-notice grammar and
associated separators, preserving all other characters in source order. The
[ledger](ledger.json.gz) binds every input, exact omission and reconstructed output.
The [summary](summary.json.gz) separates transformation/readiness/historical counts;
[coverage](coverage.json) records overlapping blocker counts. None of the proposals
is publication approval. No new disposition is recorded; cumulative inventory stays
1,621 unreviewed / 10 approve / 7 exclude / 2 defer. These are recorded intents,
not historical resolution counts. All original 1,659 source/corpus identities are
rechecked after tests in [preservation evidence](preservation-final.json).

734 minus 216 is 518 candidates whose transformed bodies still fail mechanical
checks (one becomes ineligible); blockers can overlap. The 216 includes 204 interior
cases. Remaining baseline differences are not accepted merely because mechanical
checks pass. No automatic blurb classification or silent narrative deletion occurs.

## Implementation and validation

V2 `OrderedReviewDecision` validates the complete ordered partition, source and
assessment bindings, omitted hashes and exact concatenated output hash. V1 records
remain readable without rewriting. CLI `--omissions`, disposition export, conflict
inventory, direct inspection and batch publication support both versions. Confirmed
publisher blurbs are separately preserved with exact text, source offsets, hashes,
evidence and attribution. Unknown roles remain for review. See the
[reference](../../../../lcats/docs/reference/gettenberg-review.md#ordered-retained-spans-and-editorial-metadata).

The authored installed-wheel fixture publishes a genuinely noncontiguous narrative
and preserves its confirmed blurb separately. The real five-case publication replay
retains the existing 70154 approval and withholds four unresolved cases; no unreviewed
real source is approved just to demonstrate the feature. Both use disposable outputs.
[Installed checks](installed-final.json), [publication](publication.json), and
[wheel equality](wheel.json) confirm 172 Python modules and two JSON resources match
source/wheel/isolated installation exactly, with no gutenbergpy or VCS dependency.
The wheel's dirty SCM version names the starting head; file hashes identify actual
qualified content. Build dependencies may contact PyPI; source replay disables network.

Canonical validation: 3075 tests pass in 104.557 seconds. Package and all
three changed experiment runners pass format/lint. Executable documentation commands,
source/assessment/hash/partition rejection, v1 preservation, blurb placement conflicts
and actual ordered recording-mode export have authored regressions. Raw successful
and failed logs are retained; [validation](validation.json) explains repairs. LRH validation reports zero errors and 351 pre-existing warnings.

Independent review found two P2 compatibility/accounting defects: a versionless v1
record could fail reconciliation, and equivalent v1/v2 selections could become a
false conflict. The coordinator reproduced both before repair. Permanent regressions,
red/green evidence and [independent recheck](independent-recheck.json) verify fixes.
Initial [review](independent-review.json) is historical, not a claim of remaining
unfixed findings. Temporary reproduction paths in that report are not required for
replay; use the regression tests and recorded baseline/final Git commits.

## Replay and remaining work

Use the [documented batch invocation](../../README.md#ordered-span-qualification)
with the original census/comparison, exact candidate queue and cumulative prior
19 dispositions, adding `--rule ordered`. Measurement does not record approvals;
`--record-qualified` remains explicit and has no eligible new inputs in this corpus.
Use a new output directory. The ledger contains hashes and bounded removed notices,
not a second copy of the source corpus. Manifest entries bind archived bytes and
expanded gzip content. No executable code is stored in the project control plane.

The capability is qualified; the corpus is not accepted. Next work is source-grounded
classification of surviving material and complete historical-difference explanations,
using these ordered selections when appropriate. Blurb policy is approved and the
representation works; assigning that role to real inputs still needs positive
per-input evidence. Existing integration/main/closeout gates remain unchanged.
