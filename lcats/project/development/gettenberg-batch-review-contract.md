# Batch review contract — 2026-10-20

The human approved qualifying narrow rules with per-input evidence as the batch
review method, keeping exceptions unresolved. This extends the individual-only
method in the readiness contract and candidate review workflow; their source
identity, no blanket approval and publication exclusion protections remain intact.

## Evidence and acceptance

- A finding pattern or sampled source never approves other inputs.
- Qualify an exact bounded transformation with authored positive/negative fixtures,
  real source inspection and independent review. Check every application against
  the complete candidate and bind rule/version, source, metadata, assessment,
  removed spans and retained bytes. Reject nonmatching or ambiguous cases.
- Distinguish rule applicability, publication eligibility and historical-difference
  reconciliation. Old output equality is evidence, never a literary-quality oracle.
  A safe boundary edit alone does not prove a complete story or resolve unrelated
  differences. Prior approve/exclude/defer intents remain visible and conflicts
  must not become last-writer-wins decisions.
- Successful qualified applications may produce explicitly attributed rule-based
  review decisions; do not claim individual human or complete literary readings.
  The ordinary publication path revalidates source/context/selection bindings.
- Retain all exceptions and deferrals. Do not weaken a rule to reach a target count.
  Do not change default gather behavior or canonical corpus during this experiment.
- Report full population accounting, actual coverage and limitations, runtime,
  account-wide usage, review findings and next steps. No automatic corpus acceptance,
  integration, main promotion or terminal closeout.

## Initial rule investigation

Investigate complete delimited publication/copyright notices at candidate boundaries,
optionally preceded by exact catalog-matched headings. No generic note-section,
byline, caption or narrative deletion. Final grammar and measured limitations must
be documented with evidence before any rule-based approval export.


## Qualified candidate rule and conservative accounting

The implementation candidate is `delimited-publication-notice-v1` in
`src/lcats/gatherers/review_rules.py`; the [API reference](../../docs/reference/gettenberg-review.md#opt-in-boundary-rule-proposals)
specifies its complete grammar and exclusions. It removes only complete first/last
notice paragraphs, with surrounding separator whitespace. It preserves the exact
contiguous remainder, checks every removed piece, recomputes readiness and refuses
known retained editorial labels. No default extraction behavior changes.

The experiment's additional recording gate requires no prior intent and exact
historical-baseline equality after separately recorded existing normalization.
This is intentionally stricter than matching the rule. An unlabelled blurb may pass
readiness; unexplained added text still prevents historical resolution. Prior source
review evidence must be included in cumulative inventory. Inconsistent equality
flags/hashes fail the entire run rather than disappearing from unresolved counts.

The first measurement is a throughput/limitations result, not acceptance of the
other 1,635 differences or of arbitrary future sources. Generalized internal edits,
blurb policy and whole-corpus acceptance require further scoped decisions.


## Approved ordered-span extension — 2026-10-21

The human approved the [milestone contract](gettenberg-batch-review-milestone.md#approved-scoped-implementation-contract--2026-10-21).
V2 reviewed selections preserve exact ordered ranges and evidence for every omission;
confirmed publisher blurbs move to separate editorial metadata, while uncertain
cases stay unresolved. Historical v1 records remain unchanged. The first automatic
extension uses the existing complete publication-notice grammar at interior paragraph
positions. No blurb classifier, default extraction change, corpus acceptance or gate
relaxation is authorized. Rule proposals do not authorize publication. The runner
continues its stricter no-prior-intent/readiness/full-baseline recording gate and
reports transformation coverage separately, including when no new approvals result.
