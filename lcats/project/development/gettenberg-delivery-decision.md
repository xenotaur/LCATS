# Gettenberg narrower delivery: human acceptance decision

**Human accepted A–D on 2026-10-24, conditional on a durable post-adoption
backlog.** The [backlog](gettenberg-post-adoption-backlog.md) records all four groups,
per-input details, evidence and completion criteria; the condition is now documented.
Recommendation: proceed to the internal-integration workflow after final-head checks.
PR #530 was subsequently integrated at `df055256`; the
[main-promotion review guide](gettenberg-main-promotion.md) records the next gate.
Main promotion has not occurred.
This accepts bounded replacement delivery, not an editorially clean corpus.

Reviewed product: `823f33c23836aff220fab80046ab84b80584c063`; target integration base:
`ed20e9c297bf5e50e1911b84722e53f5db3edee3`. The bounded review changes experiment
validation and documentation only. The [evidence bundle](../../../experiments/10_gettenberg_qualification/results/gettenberg-delivery-review-20261024/README.md)
contains the independent review, fresh wheel/CLI results and the per-input proposed
acceptance ledger. Its historical proposed flags remain unchanged; the separate
[acceptance record](gettenberg-adoption-acceptance.json) pins that ledger and records
the human's subsequent disposition without rewriting measurement history.

## What is established

The replacement catalog/resource library is independent of gutenbergpy. The narrow
candidate retains the provider and migration seam, two narrowly corroborated terminal-
notice repairs and required per-item cleanup-refusal continuation. It separates the
broader editorial/ordered-span/extractor redesign preserved on PR #524.

The actual normal batch on the frozen cohort publishes **1,646**, refuses **13**, and
leaves **zero unattempted**; repetition reuses all 1,646 without output-byte changes.
These are the existing corrected yield measurements, independently reconciled now,
not substituted one-item success counts. A fresh installed CLI success/refusal/success
probe additionally verifies continuation, logs and exit 2 on both cold and repeat runs.

All 1,659 cleanup results and all 67 differing bodies independently reproduce. The
67 contain no measured eligibility changes; 66 preserve the entire legacy body. The
remaining case changes known frontmatter/tail text while retaining the narrative.
The reviewer found no unresolved P0–P2 code or measurement-validity issues. Known
body-contract choices below have now been explicitly accepted with follow-up; this
does not make the outputs editorially clean or resolve the backlog.

## Human acceptance — 2026-10-24

The human accepted A's exclusions with a requirement to document them durably;
accepted B as a known limitation with a post-adoption backlog entry; accepted C
provided it is added to the backlog; and accepted D as sufficient evidence for
delivery provided its limits are also recorded there. No additional production
change was requested. GPA-A through GPA-D in the linked backlog fulfill these
conditions and remain open. Triage owner is xenotaur; implementation assignment
and grants remain separate. Historical source/evidence identities are preserved.

## Decisions presented for review — accepted with the backlog condition

The recommendations below retain the detail presented to the human. Their acceptance
is recorded above; hypothetical acceptance language is not a pending decision.

### A. Accept 13 explicit exclusions for this delivery

Recommend accepting these supported-policy limits without bypassing strict cleanup.
Original sources stay intact; no story is emitted for a refusal; later items continue;
logs identify each refusal and the CLI returns incomplete status 2. The refusal does
not establish that the source is corrupt or unsuitable for future support.

IDs: 3699, 3724, 20257, 35759, 35770, 35879, 38287, 38302, 53402, 70349, 70923, 71085, 72379.

Mechanisms: six wrapped markers, three interior `*END*` candidates, three unsupported
first-line headers and one mismatched identifier. These are 13/1,659 (0.78%) of the
measured cohort. A later narrowly specified provider-format extension can reconsider
individual inputs with adversarial tests; it is not a prerequisite for this bounded
delivery if these exclusions are approved.

### B. Accept 55 notice-only additions as a documented limitation

Recommend accepting these exact source/body identities, because the complete legacy
body is retained and eligibility/publication remain stable. The additional Gutenberg
notice is still non-story content. This approval would allow the provider replacement
to ship with that known limitation; it would not label these outputs clean editorial
artifacts or approve arbitrary future additions. The proposed ledger enumerates all
55 rather than relying on a blanket additive-difference rule.

### C. Accept the following 12 specific body effects

| IDs | Verified effect | Recommended bounded disposition |
|---|---|---|
| 32655 | One leading newline; complete old body preserved. | Accept whitespace variation. |
| 70645, *Sam Bass* | Restores a 16,465-character prefix including magazine blurb and story opening; complete old body preserved. | Keep source-backed restoration, explicitly including the blurb limitation. No unsupported claim about a legacy header rule: its recorded legacy cleanup trace is empty. |
| 22967, 27921, 29181, 29206, 30010, 30035 | Transcriber notes plus terminal notices; complete old bodies preserved. | Accept retained source paratext as a known body limitation; defer editorial removal. |
| 23161 | Author signature and terminal notice; complete old body preserved. | Accept retained source paratext. |
| 23252 | Illustration caption and terminal notice; complete old body preserved. | Accept retained source paratext. |
| 23552, *The Phantom of Bogue Holauba* | Restores the final 387-character narrative paragraph, plus a notice. The unchanged parser independently deletes that paragraph when terminal. | Keep the restored ending and accept the notice limitation. Preserve as a regression anchor for any later footer cleanup. |
| 42640, *The Last Christmas Tree* | Removes 166 characters of prior-publication note/title, retains narrative, and adds 230 characters of colophon/notice. Exact line hunks distinguish this from a misleading large contiguous diff. | Accept this specific frontmatter/tail variation; do not generalize it to permission to remove narrative. |

The nine richer suffix cases are the six transcriber-note records, signature, caption
and restored ending. With the newline, source prefix and mixed frontmatter case they
account for all 12 cases outside the 55 notice-only additions. All 67 retain their
source, metadata and old/new body hashes in the linked ledger. This is a finite
acceptance list; a newly observed unexplained material effect remains a blocker.

### D. Accept the measured delivery boundary and separate follow-up

Recommend qualifying the complete frozen **1,659-input** comparison cohort, with
separate full metadata-snapshot and authored transport/acquisition evidence. This is
not a claim of actual publication yield across all **5,492 configured IDs**. Historical
cached texts are decoded/re-encoded UTF-8, not recovered original wire bytes; the
previously approved provenance boundary remains. No canonical corpus regeneration or
promotion, live bulk download, package publication or universal-format support follows.

The full metadata snapshot still covers 78,937 records and exact public-field/raw-RDF
round trips. Its English-query comparison found 37 additional records (62,726 versus
62,689), all due to English appearing later in multivalued language metadata, with no
legacy-only records. That documented metadata correction is separate from the pinned
cleaner-substitution comparison; it does not prove yield for newly selected stories.

Separate follow-up remains with the LCATS maintenance backlog. Proposed triage owner:
xenotaur, consistent with WI-GETTENBERG-0010; implementation ownership remains to be
assigned, with no implied assignment to Kenny. Follow-ups: unsupported source-format coverage; retained
paratext and existing parser heuristics including the independently reproduced 23552
ending loss; broader corpus quality and reconciliation with Kenny's work; expanded
configured-collection acquisition/yield if desired. Preserve PR #524 and all historical
evidence. Do not silently import its broader gather redesign into this delivery.

## Qualification map for the reviewed candidate

“Evidence supported” describes technical findings. Human acceptance of A–D is
recorded above; open follow-up is not evidence of implemented remediation. The final
documentation/evidence commit must preserve the reviewed runtime/test/config bytes
and pass its PR checks before integration.

| Gate | Candidate evidence and present status |
|---|---|
| Q1 Provider independence | Feature matrix, migration inventory and full snapshot/index/lifecycle evidence transfer with verified source identities; fresh wheel has exactly 165 Python modules and two JSON files, no gutenbergpy/VCS requirement. Evidence supported with dated-environment limits. |
| Q2 Consumer contract | Tests/docs cover metadata projection, resource/decode/cleanup provenance, ownership/naming, source-aware first use, cached/offline/non-Gutenberg behavior; narrow ready/skipped/refused result, historical gather_stories pair and incomplete CLI status 2. Fresh installed CLI and 41 documentation/live tests pass. Evidence supported. |
| Q3 Causal comparison | All 1,659 inputs accounted; source, metadata, parser and normalization pinned; 67 old controls match historical bodies; current differing bodies independently reproduced. No unknown residual queue. B/C accepted with GPA-B/GPA-C open. |
| Q4 Regression mitigation | Both demonstrated severe truncations repaired; narrow title/numeric context rules and adversarial tests; current all-input cleanup replay. No new code blocker found. B/C accepted with explicit backlog limitations. |
| Q5 Operational usability | Corrected normal cold/repeat batch: 1,646 published/reused, 13 refused, zero unattempted; fresh installed mixed CLI test confirms status/log semantics. A/D accepted with GPA-A/GPA-D open. |
| Q6 Gaps/independent defects | Exact per-input residual identities and source-grounded descriptions; independent no-cleaner reproduction of 23552 parser defect; explicit decoded-wire/full-selection limits. C/D accepted with GPA-C/GPA-D open. |
| Q7 Exact-candidate checks | Reviewed runtime equals the previously passing 2,956-test product; four hosted checks green at 823f33c2. New focused canonical 112, experiment 26, docs/live 41 (overlapping), wheel/CLI/pip checks and independent review pass. Final evidence commit validation/checks must also pass. |
| Q8 Delivery/lifecycle | Internal integration completed via PR #530 at df055256. Human main promotion, truthful native closeout and downstream release verification remain pending. No main delivery claimed. |

The [original qualification index](gettenberg-qualification.md#capability-mapping)
provides capability-level evidence, with [full snapshot artifacts](../../../experiments/10_gettenberg_qualification/results/gettenberg-qualification-20261018/)
and the [caller inventory](gettenberg-migration.md). Transfer does not carry historical
cleanup conclusions: only 161/165 product files match that ledger, and the four
changed cleanup/gather modules are requalified by the current evidence. The catalog
snapshot/lifecycle source lists each have 27 unchanged modules plus cleanup; cleanup
is outside their measured catalog path. Historical resource measurements remain dated
observations under Python 3.11.9, SQLite 3.46.0, lxml 5.2.2/libxml2 2.12.6. They do not
establish performance on every dependency version or a general speedup over gutenbergpy.

| Governing design completion criterion | Exact-candidate evidence / remaining action |
|---|---|
| 1 Remove active legacy dependency | Complete fresh wheel closure, installed origins, metadata/import guard tests; historical legacy experiments remain archival. |
| 2 Feature/evidence matrix | Existing capability matrix plus source-verified full snapshot/index/accounting/lifecycle reports and current cleanup evidence (Q1/Q4). |
| 3 First/cached/offline/unattended gather | Executed Diataxis examples, preparation/live-gather tests, current installed CLI and measured cold/repeat batch (Q2/Q5). A/D accepted with open follow-up. |
| 4 Unrelated sources avoid Gutenberg | Source-aware preparation and live-gather non-Gutenberg tests; unchanged implementation/source transfer. |
| 5 Refresh preserves last valid catalog | Lifecycle/catalog-receipt/refresh tests and unchanged full local lifecycle evidence. No production cache touched. |
| 6 Inspectable metadata/transformation provenance | Full raw/field round trips; immutable source/receipt/cleanup spans; per-input causal/yield identities and installed output provenance. |
| 7 Caller migration/archive disposition | Migration inventory, preserved notebook identities and research/import guard tests; no newly introduced caller dependency. |
| 8 Corpus/resource comparison reviewed | Complete causal ledger, normal batch yield, independently checked residuals and dated resource measurements; human A–D accepted with open follow-up. |
| 9 Required checks | Existing unchanged-product full canonical/format/lint evidence plus new targeted/experiment/installed review and final evidence-commit validation/CI (Q7). |
| 10 Accurate docs/control plane | This sheet, runlog, evidence manifest and nonterminal execution/WI records; final main closeout remains pending. |

## Integration and delivery sequence

1. Completed: human accepted A–D subject to durable backlog capture. The acceptance
   record and GPA-A through GPA-D fulfill that condition; historical evidence remains
   unchanged. Reconsideration of a group requires its own scoped decision.
2. Completed after explicit human instruction: verified final head/checks and no
   unresolved threads, then integrated #530 into `codex/gettenberg-acquisition` at
   `df055256`. Its tree equals the accepted PR head. See the promotion guide.
3. Prepare one reviewable promotion PR to main with the full replacement diff,
   accepted limitations, migration instructions, source/evidence map and closeout plan.
   Human main approval remains a separate gate. Recheck CI after integration/promotion.
4. After actual main delivery, reconcile native work items/executions/workstream and
   proposal status truthfully. Verify WI-RELEASE-0037 / WI-RELEASE-0039 separately;
   package publication and corpus promotion are not implied.

This review recommends delivery under explicit known limitations. It does not require
hundreds of editorial runs, restore the separated subsystem, or silently weaken the
rule that unexplained material replacement effects block qualification.
