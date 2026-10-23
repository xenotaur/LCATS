# Narrow gettenberg delivery candidate

Status: construction/qualification checkpoint, **not release acceptance**.
Review: [draft PR #530](https://github.com/xenotaur/LCATS/pull/530), targeting
`codex/gettenberg-acquisition`.
Approved scope: [scope and causality audit](gettenberg-scope-causality-audit.md),
Q1–Q8 in [WI-GETTENBERG-0010](../work_items/proposed/WI-GETTENBERG-0010.md).

## Construction and preserved identities

- Base: `ed20e9c297bf5e50e1911b84722e53f5db3edee3`, the provider/caller migration seam,
  also `codex/gettenberg-acquisition` at construction time.
- Preserved combined work: `b1254805c85bc34c0924e112732822c5e1436df5`,
  `codex/gettenberg-qualification`, PR #524. No reset, deletion or replacement of it.
- Candidate: `codex/gettenberg-narrow-delivery`, independently constructed from the
  migration seam. Later control-plane history and experiment archives are carried
  forward for traceability. Historical outputs remain byte-identical.

## Product decisions

Retain the catalog, resource store, routing, decoding, refresh, provenance, CLI
setup and migrated consumers from the base. Add exactly the approved title/numeric
terminal-notice repairs as cleanup policy v3. Numeric cleanup receives immutable
source/catalog/title context; source identity comes from the selected resource URI.
Unknown or disagreeing identity preserves the notice. Originals remain unchanged.

Retain the migration-seam parser, CLI and gather return contracts. Retain the
installed-wheel log-directory safeguard independently of the review subsystem:
check runtime data/corpora and available checkout roots before using the RunLog
explicit-root escape hatch. Log cleanup refusal distinctly, then preserve the
existing fail-fast operational contract. This does not claim satisfactory full
batch yield: the 13 refused inputs must still be accounted for under Q5.

Separate the later opening-prefix/chapter redesign, readiness rules, ordered spans,
editorial/historical review APIs, review CLI/store and structured gather outcomes.
Their dedicated tests and guides remain with that preserved subsystem. Mixed
parser/CLI/gather tests retain the migration baseline; new narrow integration,
context and corpus checks protect the causal repairs. This is contract separation,
not ignoring failing assertions against an unchanged implementation.

## Later product/test/document paths

The table enumerates every src/tests/docs path changed between the seam and the
preserved combined revision. Additional candidate-only paths are described below.

| Path | Candidate treatment |
|---|---|
| `lcats/docs/explanation/gettenberg-architecture.md` | Retain/adapt provider documentation to narrow API. |
| `lcats/docs/how-to/gettenberg-catalog.md` | Retain/adapt provider documentation to narrow API. |
| `lcats/docs/how-to/gettenberg-cleanup.md` | Retain/adapt provider documentation to narrow API. |
| `lcats/docs/how-to/gettenberg-gather.md` | Retain/adapt provider documentation to narrow API. |
| `lcats/docs/how-to/gettenberg-migration.md` | Retain/adapt provider documentation to narrow API. |
| `lcats/docs/how-to/gettenberg-preparation.md` | Retain/adapt provider documentation to narrow API. |
| `lcats/docs/how-to/gettenberg-review.md` | Separate review guide; preserved combined revision. |
| `lcats/docs/how-to/gettenberg-routing.md` | Retain/adapt provider documentation to narrow API. |
| `lcats/docs/index.md` | Retain/adapt provider documentation to narrow API. |
| `lcats/docs/reference/gettenberg-catalog.md` | Retain/adapt provider documentation to narrow API. |
| `lcats/docs/reference/gettenberg-cleanup.md` | Retain/adapt provider documentation to narrow API. |
| `lcats/docs/reference/gettenberg-gather.md` | Retain/adapt provider documentation to narrow API. |
| `lcats/docs/reference/gettenberg-records.md` | Retain/adapt provider documentation to narrow API. |
| `lcats/docs/reference/gettenberg-review.md` | Separate review guide; preserved combined revision. |
| `lcats/docs/tutorials/gettenberg-first-catalog.md` | Retain/adapt provider documentation to narrow API. |
| `lcats/src/lcats/cli.py` | Migration-seam version; later broad changes preserved separately. |
| `lcats/src/lcats/gatherers/candidate_review.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/src/lcats/gatherers/editorial_evidence.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/src/lcats/gatherers/gather_result.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/src/lcats/gatherers/historical_review.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/src/lcats/gatherers/main.py` | Migration-seam version; later broad changes preserved separately. |
| `lcats/src/lcats/gatherers/mass_quantities/gatherer.py` | Base contract plus log safety and distinct refusal event. |
| `lcats/src/lcats/gatherers/parser.py` | Migration-seam version; later broad changes preserved separately. |
| `lcats/src/lcats/gatherers/readiness.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/src/lcats/gatherers/review_cli.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/src/lcats/gatherers/review_rules.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/src/lcats/gatherers/review_store.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/src/lcats/gatherers/story_body.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/src/lcats/gatherers/story_output.py` | Migration-seam version; later broad changes preserved separately. |
| `lcats/src/lcats/gettenberg/cleanup.py` | Retain conservative policy; add approved v3 notice rules. |
| `lcats/tests/cli_test.py` | Migration-seam version; later broad changes preserved separately. |
| `lcats/tests/gatherers_tests/candidate_review_test.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/tests/gatherers_tests/editorial_evidence_test.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/tests/gatherers_tests/historical_review_test.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/tests/gatherers_tests/live_gather_test.py` | Migration-seam version; later broad changes preserved separately. |
| `lcats/tests/gatherers_tests/mass_quantities_test.py` | Migration-seam version; later broad changes preserved separately. |
| `lcats/tests/gatherers_tests/ordered_review_test.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/tests/gatherers_tests/parser_test.py` | Migration-seam version; later broad changes preserved separately. |
| `lcats/tests/gatherers_tests/readiness_test.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/tests/gatherers_tests/review_rules_test.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/tests/gatherers_tests/review_store_test.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/tests/gatherers_tests/story_body_test.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/tests/gatherers_tests/trailing_notice_test.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/tests/gettenberg_tests/boundary_groups_evidence_test.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/tests/gettenberg_tests/cleanup_test.py` | Retain provider cleanup regressions; extend v3 coverage. |
| `lcats/tests/gettenberg_tests/disposition_tranche_evidence_test.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/tests/gettenberg_tests/documentation_test.py` | Retain/adapt provider examples; review-guide test stays with separated guide. |
| `lcats/tests/gettenberg_tests/editorial_evidence_runner_test.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/tests/gettenberg_tests/qualification_evidence_test.py` | Mixed split: snapshot field/source-fidelity regression retained in qualification_helpers_test; broader corpus/review evidence tests preserved separately. |
| `lcats/tests/gettenberg_tests/qualification_helpers_test.py` | Explicit current provider runner coverage; historical runners pinned separately. |
| `lcats/tests/gettenberg_tests/review_batch_evidence_test.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/tests/gettenberg_tests/review_workflow_evidence_test.py` | Separate dedicated subsystem/test; preserved combined revision. |
| `lcats/tests/gettenberg_tests/terminal_batch_evidence_test.py` | Separate dedicated subsystem/test; preserved combined revision. |

Candidate-only additions: `gutenberg_source.py` explicit context/provenance;
`cleanup_context_test.py` and `narrow_integration_test.py`; two narrow experiment
runners. The current migration runner again unpacks the baseline tuple contract.
Provider documentation examples are executed with network forbidden.

## Qualification and remaining decisions

Constructing a narrow branch does not approve old output, erase evidence or settle
a difference. The prior experiment left **67 body differences and 13 refusals**;
these remain unresolved pending per-input causal dispositions. Preserve the
separate metadata/selection analysis and classify new-source effects separately
from preexisting extractor/editorial issues. Material unknowns block delivery.

This checkpoint must report focused/full tests, exact product bytes, independent
review, frozen-cohort replay and an installed-wheel smoke. Fixture publication is
not a full-corpus yield claim. Final acceptance additionally needs all Q1–Q8,
including demonstrated useful actual gathering, consumer/selection coverage,
material-regression dispositions, exact-head CI and human main promotion.

Do not merge the combined PR #524 as a shortcut. Reconcile the separated gather
work with Kenny's implementation as a separate task when available. A candidate
PR targets the acquisition branch; promotion to main remains a human milestone.

Run-specific outcomes and limitations are appended to the
[development log](gettenberg-development-log.md) and fresh experiment results.

## 2026-10-22 candidate checkpoint

Product commit `91f1b42281418d613bc1744b77ada73b42405bfc`: all 1,659 cleanup outcomes
and 1,646 bodies reproduce the approved experiment with actual resource-derived
context. Clean installed wheel passes two publication fixtures and one refusal;
all 165 Python files and declared JSON data match the candidate. Canonical 2,955 tests,
package/experiment lint and independent review pass. See the
[fresh evidence](../../../experiments/10_gettenberg_qualification/results/gettenberg-narrow-delivery-20261022/README.md).

The first wheel was rejected for nine stale separated modules in build staging;
the fresh complete closure check resolves that finding. This is construction
qualification only.67 differences and 13 refusals, full actual-gather yield and the
remaining Q1–Q8 decisions still block delivery. PR checks/promotion are separate.

## Gate status at the 2026-10-22 construction checkpoint

| Gate | Evidence now available | Still required before delivery |
|---|---|---|
| Q1: provider and independence | Provider foundation retained; clean wheel has no legacy dependency or separated runtime. | Complete candidate-level transfer of the existing feature/full-snapshot evidence with source assumptions checked. |
| Q2: consumer contracts | Canonical consumer tests pass; tuple/exit contracts remain; cleanup context and distinct refusal logging are documented and tested. | Include these in the final acceptance-to-evidence map. |
| Q3: causal comparison | All 1,659 controlled inputs accounted for; resource-derived context and body comparison are pinned. Prior metadata/selection analysis is retained. | Complete causal dispositions for the 67 differences and 13 refusals; keep selection effects separate. |
| Q4: regression mitigation | Both severe truncations repaired; authored counterexamples and full-population replay pass. | Determine whether residuals contain other material replacement-induced regressions. |
| Q5: operational usability | Actual installed gathering publishes/reuses authored stories and distinguishes a refusal. | Measure representative/full disposable gather yield, including the effect of fail-fast refusals. Body eligibility counts alone do not prove publication yield. |
| Q6: evidence gaps | Unknowns and decoded-cache provenance limits remain explicit. | Investigate or narrowly contain material provider effects; prove independent defects before assigning separate follow-up. |
| Q7: exact candidate validation | Local tests/lint, installed closure/smoke and independent review pass against unchanged product bytes. | Check final PR-head CI and complete the final acceptance map. |
| Q8: delivery/lifecycle | Separate draft candidate; combined work preserved. | Human main promotion, truthful native closeout and downstream release verification. |

## 2026-10-23 causal accounting and actual gather-yield checkpoint

Production remains unchanged from `91f1b422`. The
[new causal/yield evidence](../../../experiments/10_gettenberg_qualification/results/gettenberg-causal-yield-20261023/README.md)
accounts for all 67 body differences and 13 refusals with per-input identities and
controlled probes; these are no longer an unexplained residual queue. Causal
accounting is not acceptance: all 80 retain explicit pending delivery/editorial
status. The 67 legacy-control bodies independently match the checked-in historical
bodies; both controlled cleaner paths hold source, metadata, parser and normalization
fixed. The remaining 1,579 equal cases retain the pinned full-census evidence.

Body mechanisms: 55 terminal-notice-only additions; 9 additions also containing other
material; 1 leading newline; 1 source-prefix restoration; 1 mixed frontmatter/tail
interaction. Refusal mechanisms: 6 wrapped markers, 3 interior *END* candidates,
3 unsupported first-line headers and 1 mismatched identifier. No body-eligibility
change among the 67. ID 23552 proves a separate unchanged-parser final-paragraph
loss without either cleaner, so blindly restoring legacy footer cuts is unsafe.

Actual production gathering on disposable decoded-source fixtures measures the
configured-order intersection with the 1,659 cohort, not all 5,492 configured IDs:

- Cold batch publishes 41, refuses 3699 and leaves 1,617 unattempted.
- Repetition reuses 41 and stops at 3699 again.
- Separate one-item calls publish 1,646 unique outputs and refuse 13; no other errors,
  skips, body mismatches or owner collisions. This is experimental isolation,
  not current batch/CLI continuation behavior.
- All 1,646 successful outputs reuse unchanged with an empty source cache.

The initial cache inventory found no matching verified receipts in either supplied
root. Fixtures are explicitly derived from historical decoded UTF-8, not original
Gutenberg transport. The evidence cannot establish historical wire fidelity or
full configured-collection yield. No network acquisition/canonical publication.

Q3 now has per-residual causal observations; Q4/Q6 require explicit bounded
contract/disposition decisions rather than additional unexplained-case discovery.
Q5 has measured useful per-item publication but a known fail-fast batch blocker;
this is not operational acceptance. Q1 transfer, final Q2/Q7 acceptance mapping,
wire/selection boundaries and Q8 human main promotion remain pending.

Recommendation for the next human decision: approve an explicit narrow collection
policy for per-input cleanup refusals, preserving strict source cleanup and visible
incomplete-run reporting. Keep this separate from notice matching and general
exception handling. Give the 55 notice-only records an explicit body-contract
accept-or-repair decision; do not automatically approve the richer suffixes or
mixed frontmatter case. Preserve 23552 for separate gather reconciliation and as a
regression anchor for any later notice repair. No production behavior or acceptance
criterion was changed by this evidence run; PR #530 remains a draft.
