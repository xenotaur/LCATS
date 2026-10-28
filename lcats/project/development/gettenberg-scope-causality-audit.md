# Gettenberg scope and causality audit

Status: **human-approved scope and qualification amendment, 2026-10-22; no production implementation change**.
User authorized this audit after identifying overlapping ownership of gather fixes.
Kenny's code is unavailable. Its reconciliation is a separate future task, not a
prerequisite for this scope decision. Audit began 2026-10-22 07:49:48 UTC.

Pinned product head: `6a873b611e3958bb9ddad8e84f2ad190831a9da7`.
PR #524 integration base: `ed20e9c297bf5e50e1911b84722e53f5db3edee3`.
Documentation/evidence branch: `codex/gettenberg-scope-audit`, stacked on the
qualification branch. This audit does not integrate or approve PR #524.

## Approved decision

Separate (A) the Gutenberg provider replacement, (B) its causal gather integration
obligations, and (C) broader gather improvements. Preserve the combined qualification
branch and all evidence. Under a subsequent bounded implementation grant, construct
and qualify a narrower delivery candidate; do not revert or merge the current branch wholesale.

The original design assigns catalog, acquisition and conservative Gutenberg cleanup
to gettenberg; story interpretation stays with gatherers. The baseline migration
inventory explicitly preserves extraction, naming and normalization. However, a new
provider can trigger an old extractor defect: that is still our integration obligation.
A defect is not independent merely because the faulty code predates this project.

The present 1,628 unresolved historical comparisons are not a count of replacement
bugs. They include effects of our later extractor and editorial-policy changes. The
scope decision should not require completing literary curation, and should not excuse
unexplained harmful provider effects. Unknown causality stays unknown.

## Evidence and what it establishes

### Architectural separation

`ed20e9c2` already contains the replacement, migrated callers and CI work. Between
that base and the pinned product head, the only changed product file inside
`src/lcats/gettenberg/` is `cleanup.py`: the narrow v2 comma-banner /END: FULL LICENSE
repair. All other product changes are in `gatherers` and `cli.py`. A text search finds
no gather/readiness/review imports inside gettenberg; this establishes a useful static
boundary, not a complete runtime dependency proof.

The pre-repair parser `335855c04cd7ba936815d2635969d94fdd278c71` is already migrated.
AST comparison with original baseline `5cfd2d71caf6f3eedfdfc0b830b5c5ff1a74ba3b`
finds 47 common functions; only `gather_story` differs. Its body/chapter/heading
algorithms therefore preserve the original implementation. Do not call the whole
module or runtime an untouched historical installation.

### Two different population comparisons

The October 18 cleanup-v2 comparison holds metadata, source text, extraction and
normalization constant: 1,659 inputs, 1,646 compared, 13 cleanup refusals, 902 changed
bodies. Its mechanical groups are 696 appended end notices, 122 transcriber notes,
57 byline/separator starts, 19 other suffixes and eight earlier-position changes.
These labels explain where to investigate; they are not permission to remove prose.
There are 744 equal old/new comparisons; 742 also match the retained corpus, while
two have retained-corpus-only differences.

Later comparisons use a pinned old parser on one path and the new extractor on the
other. The 1,642 historical differences (14 resolved /1,628 unresolved at this audit)
therefore combine provider effects and gather changes. They remain valuable evidence,
but cannot directly measure the replacement's defect count or a narrower candidate's
acceptance. No old disposition or unresolved judgment is changed here.

### New eight-case controlled replay

The experiment crosses legacy/replacement cleanup with pre-repair/current body
extraction. All four cells receive the same decoded input, current metadata and
normalization. It reproduces **all 16 normalized hashes** from the earlier eight-case
cleanup comparison. It does not run actual story publication.

| ID | Legacy cleanup + pre-repair extraction | Replacement cleanup + pre-repair extraction | Legacy cleanup + current extraction | Replacement cleanup + current extraction |
|---|---:|---:|---:|---:|
| 22579 | 30,908 | 31,105 | 31,696 | 31,696 |
| 23148 | 15,074 | 15,449 | 15,582 | 15,582 |
| 35401 | 26,080 | 2,620 | 26,521 | 26,521 |
| 70645 | 10,078 | 26,543 | 46,083 | 26,931 |
| 23104 | 30,384 | 30,484 | 30,404 | 30,543 |
| 50103 | 31,972 | 900 | 32,888 | 32,888 |
| 42640 | 22,705 | 22,769 | 23,159 | 23,159 |
| 32655 | 14,735 | 14,814 | 15,164 | 15,164 |

Numbers are normalized character counts, not quality scores. The decisive contrasts:

- **35401 /50103:** replacement cleanup with the same extractor reproduces the severe
  truncations. Some integration mitigation is necessary. Current extraction avoids
  these failures, but the experiment does not establish that every current rule is
  necessary or the smallest solution.
- **42640:** the historical chapter predicate is false on both pre-repair outputs
  and true on both current-extractor outputs. Thus our extraction repair itself can
  expand eligibility problems even under legacy cleanup. This does not prove whether
  the work is actually chaptered.
- All eight current-extractor bodies receive `needs_review` under either cleaner.
  The broad readiness policy is not specific to replacement cleanup. This does not
  establish what a complete legacy-provider/current-gather run would do.
- Current extraction retains all eight exact, previously reviewed anchor intervals
  under both cleaners. Failure of exact interval retention on historical outputs can
  reflect typography changes; it is not automatically proof of narrative deletion.
- **70645** retains a substantial cleanup effect even with current extraction. Six
  identical current-extractor pairs do not prove cleanup irrelevant for all cases.

The new runner pins/hashes its relevant product modules, the historical parser,
legacy cleaner and source inputs. It relies on the historical measurement environment
for gutenbergpy; it is not a production dependency. Historical cache entries are
already decoded/re-encoded UTF-8 and cannot establish original HTTP encoding/resource
identity. Existing authored original-byte tests remain separate evidence.

### Terminal-notice follow-up — 2026-10-22 16:00 UTC

A subsequent user-authorized, experiment-only investigation refines the mechanism.
The historical parser chooses the same late author-like chunk under both cleaners
for 35401/50103. Its first candidate has 9/10 double-newline chunks under legacy cleanup
but 13 under replacement cleanup. Retained notice/blank lines suppress the fallback
at historical parser line 1291 (`> 10`); those chunks include empty strings. Explicitly
removing each known literal suffix restores both archived legacy hashes. This is a
causal probe, not a generally qualified recognition rule.

A minimal candidate extends only the existing cleaner's terminal-notice grammar to
`End of the Project Gutenberg EBook of TITLE, by AUTHOR`, preserving all envelope,
whole-line, matching-title and nonempty-author guards. With the same pre-repair
extractor, metadata and normalization across all 1,659 inputs:

- All 3,292 archived old/new normalized hashes reproduce; 1,646 inputs compare and
  the same 13 remain refused.
- 470 cleanup/body changes restore 469 legacy equalities; 902 differences become 433.
  No formerly equal body becomes different, and no refusal changes.
- 35401 returns 26,080 characters again. One chapter exclusion (29632) also returns
  to the legacy result; all candidate body-eligibility results match the legacy path.
- 50103 remains 900 characters: its marker is numeric 50103 and cannot corroborate
  the title in its notice under this rule. Known-literal removal restores 31,972,
  but does not authorize relaxing the general rule.
- The only affected non-equal body, 32655, is exactly one leading LF plus legacy text.
  Coordinator follow-up groups the other 432 residuals as 376 terminal notices with
  matching numeric ebook markers and 56 outside this notice grammar. These are
  mechanical investigation groups, not qualified families or approvals.

Independent review verified the counts, original hashes, all 470 removal spans and
six severe-case cells; 8 focused boundary tests pass. Product, active gates and corpus
remain unchanged. See the [full experiment and exact trace table](../../../experiments/10_gettenberg_qualification/results/gettenberg-terminal-notice-audit-20261022/README.md).

**Updated mitigation recommendation:** retain this precise grammar extension as a
candidate for later implementation review; investigate numeric-marker corroboration
at the provider/source boundary next. Do not broaden gather extraction or claim the
replacement safe while 50103 remains. This evidence reduces the justification for
retaining the full extractor overhaul, but does not by itself qualify the delivery
split or adopt Q1–Q8. Remaining provider effects still need causal accounting.

### Numeric-marker follow-up — 2026-10-22 17:36 UTC

The next human-authorized experiment adds explicit source/catalog corroboration for
numeric markers. Positive source ID, catalog ebook ID and both marker identifiers
must agree exactly; the terminal notice title must match a projected catalog title
under existing case/horizontal-space rules. All other envelope/whole-line/nonempty
checks remain. No fuzzy matching, product change or gather algorithm change.

Fresh combined-candidate extraction runs on all 1,646 accepted inputs, after verifying
all 1,659 original source/corpus identities and unchanged metadata/product modules.
The previous old-cleaner/replacement/title-candidate outputs are explicitly reused as
pinned evidence, not falsely reported as newly executed. Numeric cleanup changes 367
slices but 366 bodies: 61499 already had the same body. The additional 366 equalities
reduce 433 residuals to 67; together both candidates restore 835 of 902 original body
comparisons. No previously equal body becomes different, no additional eligibility
change occurs, and the same 13 refusals remain.

50103 now regains its exact 31,972-character legacy body through the corroborated
rule; 35401 keeps its 26,080-character repair. Both diagnosed fallback-suppression cases
are therefore repaired by narrow provider/source rules in the experiment. Remaining:
10 title mismatches, 56 outside this notice grammar, one known leading LF. These are
unresolved comparisons, not approvals or a count of proven remaining bugs.

**Next decision:** stop widening the notice family and review the scope split/Q1–Q8
proposal before production implementation. A narrower delivery candidate can carry
these two supported repairs, with explicit metadata context and derivation provenance,
then account for the 67 residuals and 13 refusals and qualify real gather behavior.
Do not hide catalog access inside the pure cleaner or infer safe final delivery from
historical equality. The wider gather enhancements remain preserved for reconciliation.

[Numeric-notice evidence and reproduction](../../../experiments/10_gettenberg_qualification/results/gettenberg-numeric-notice-audit-20261022/README.md).

### Metadata is a separate contrast

The full catalog audit recorded 37 additional English-query IDs from source languages
that the old first-language schema omitted; no old IDs disappeared. None of these
37 is in the 1,659-input historical comparison population. Two occur in configured
`SINGLE_STORIES`, but all 37 fail the existing only-English filter because they are
multilingual. They are not 37 newly published stories or a cause of this body backlog.
Both early and later census metadata-rejection fields are null for all 1,659 rows.

This does not settle every metadata effect. Titles, author/alias ordering, contributor
role projection, resource preference and output naming need a bounded interface audit
on the eventual delivery candidate. Do not infer their equivalence from the cleanup
experiment, which deliberately holds metadata constant.

## Retain / separate / defer plan

These dispositions were approved by the human on 2026-10-22; they are not
implementation edits. File locations are under `lcats/src/lcats/` unless otherwise
stated. “Retain” still requires final-candidate qualification.

| Surface | Approved disposition | Reason / required boundary |
|---|---|---|
| gettenberg catalog, models, ingestion, lifecycle, queries | Retain | Core replacement; richer metadata is an intended capability, not a demand for old SQL compatibility |
| gettenberg resource selection, routes, original bytes, decode, refresh, cache/provenance | Retain | Core replacement; qualify stated contracts without inventing missing historical wire receipts |
| gettenberg cleanup-v2 | Retain | Narrow Gutenberg envelope repair; preserve original text and conservative refusal |
| Title-matched and explicitly corroborated numeric terminal notices | Carry as proposed narrow repair candidates, subject to implementation review | Both diagnosed fallback truncations regain legacy hashes without replacing extraction; explicit context/provenance and residual qualification remain required |
| `gutenberg_source.py`, source-aware preparation and caller migration | Retain | Necessary interface; audit projection/selection/naming effects separately |
| Packaging, CI migration, genre caller, approved notebook migration/archives | Retain | Explicit original scope; a path outside gettenberg is not automatically scope expansion |
| `story_output.py` atomic/no-overwrite behavior | Retain core; separate result-contract changes | Predates PR524; its boolean return was added for later outcome reporting |
| `parser.body_of_text` /`story_body.extract` | Hold as integration candidate; split by behavior | The two notice candidates repair the diagnosed interaction without this overhaul. Broad front matter/typography behavior is not automatically necessary; residual material effects still require qualification |
| `story_body` production credits, illustration labels, terminal notice handling | Evaluate separately | Shared file does not establish shared necessity; exact Gutenberg notices differ from general editorial interpretation |
| Chapter assessment and metadata heading exemptions | Hold causal subset; separate general redesign | Some changes compensate for retained headings; 42640 shows the extractor can itself cause this interaction |
| `readiness.py` default policy, ordered selections and editorial metadata | Separate as gather enhancement | New publication contract; preserve current protections until a safe replacement integration plan is approved |
| `candidate_review`, `review_store`, `review_cli`, `gather-review` command | Separate with callers/tests/docs | General review workflow, not a provider requirement |
| `review_rules`, `historical_review`, `editorial_evidence` | Separate with their experiment/tooling dependencies | Useful follow-up work; source acquisition does not depend on it |
| `gather_result`, batch/main/CLI results, cleanup refusals and logs | Split mixed requirements | Review outcomes/exit 3 belong with review policy; operational error distinctions and installed logging safety may be essential integration fixes |
| Historical outputs, candidates, dispositions, experiment results and native records | Preserve | No deletion, reclassification as “approved”, or rewritten historical evidence to simplify delivery |
| Complete editorial reconciliation, new paratext taxonomy/source acquisition, Kenny implementation reconciliation | Defer to separately scoped work | No prerequisite for provider replacement unless a specific causal integration obligation is established |

### Why a mechanical revert is unsafe

`parser.py` combines migrated source ownership, candidate extraction, chapter logic
and approval handling. `main.py`, the mass-quantities gatherer and `cli.py` consume
review records and structured outcomes. Removing review modules alone breaks those
callers. `review_store.working_root` also supplies the installed-wheel logging-root
safety check; removing review must not remove that protection. `story_body` supplies
both extraction and metadata classification helpers. These are hunk/API dependencies,
not clean whole-commit ownership boundaries.

Tests and docs must follow the split. Preserve narrative-loss regression assertions,
rework mixed live-gather/batch/CLI tests to the agreed contract, and move dedicated
review suites/docs with their implementation. Do not remove a failing assertion just
to restore old behavior. Historical runners remain reproducible at recorded revisions;
the separated delivery need not pretend every historical runner is a current API client.

## Approved qualification criteria — adopted 2026-10-22

The human approved replacing the corpus portion of WI0010's scope and completion
mapping with the following. Preserve original criteria 1–7 and 9–10, including first-use,
offline/recovery, documentation, package independence and human main-promotion gates.
Clarify governing criterion 8 with this explicit definition rather than silently
interpreting the existing words differently.

> Qualify the provider replacement and its material effects on gathering using pinned,
> immutable inputs and stage-specific contrasts. Account for every measured input and
> material replacement-induced difference as an intended documented change, a repaired
> regression, an explicit operational refusal, or an unresolved blocker. Independently
> reproduced pre-existing gather defects and separately introduced gather enhancements
> retain their evidence and follow-up ownership; complete editorial curation is not a
> provider acceptance requirement. Missing evidence never establishes equivalence.

| Approved gate | Required evidence / pass condition |
|---|---|
| Q1. Provider capability and independence | Existing feature matrix, full-snapshot field/index evidence, cache/lifecycle/failure contracts and fresh wheel without gutenbergpy/VCS dependency attributable to candidate sources |
| Q2. Consumer contract | Explicit metadata projection, resource preferences, decode/cleanup/refusal, source ownership and naming contract; tests of first-use/cached/offline/non-Gutenberg behavior and public return/exit/log behavior |
| Q3. Causal comparison | Stage-pinned comparison on all available 1,659 cached inputs; separate metadata/selection effects; exact inputs, extractor, normalization and candidate sources identified; every input accounted for |
| Q4. Regression mitigation | Demonstrated truncations and other material provider interactions repaired or narrowly contained; authored adversarial tests plus real-source anchors; full-population replay of chosen mitigation; no broad editorial classifier required |
| Q5. Honest operational usability | Actual disposable gather tests show successful publication/reuse, distinct refusal/error reporting and narrative protection. Quantify changed eligibility/yield. Withholding nearly everything is not accepted merely because it is conservative |
| Q6. Evidence gaps and independent defects | Unknown material provider effects remain blockers until investigated or explicitly contained. Establish independent defects by controlled reproduction, not age of code. Record owner/follow-up and user-visible limitations; irrecoverable legacy wire-provenance limits require explicit acceptance of the evidence boundary, not a fictitious replay |
| Q7. Exact-head validation and review | Canonical checks, relevant experiment checks, installed-wheel smoke and independent review on the actual split candidate; carry older component evidence only with verified unchanged sources and assumptions |
| Q8. Delivery and lifecycle | Human-reviewed main promotion, truthful native closeout and downstream release-item verification. No canonical corpus promotion or PyPI publication inferred |

The current audit passes none of these new gates on behalf of a future candidate.
Its controlled probes and terminal-notice census support scope decisions, not
qualification of the eventual delivery candidate or actual public gathering.
A harmless additive difference can have per-input mechanical evidence under an agreed
contract; it need not require literary approval. “Additive” alone is insufficient if
it changes chapter/eligibility behavior, violates the story-body contract, or affects
publication/naming. Necessary containment must be measured and usable, not a blanket
unknown-material refusal disguised as compatibility.

The intended new Q3/Q4 workload is bounded causal accounting, not solving all 1,628
editorial cases. Maintain a causal ledger distinct from the historical approval ledger.
Cases can be unresolved editorially while their provider effect is known; the converse
can also occur. Do not collapse those statuses into one resolved count.

## Implementation choices for the next grant

1. **Recommended: construct a narrower candidate from the migration seam.** Use
   `ed20e9c2` as a comparison/construction reference, retain the cleanup-v2 repair,
   and qualify a minimal integration mitigation. Preserve approved replacement docs
   and applicable checks developed later. Do not reset existing history or assume
   the seam itself is safe. The exact patch is a later reviewed deliverable.
2. **Alternative: retain current extraction but separate review tooling.** Less
   extraction rework, but inherits wider retained-text and chapter effects. It needs
   the same causal/usability qualification; deleting readiness is not proof of safety.
3. **Alternative: expose the library before migrating gathering.** A useful partial
   milestone but leaves the old active dependency, so does not complete this task.
4. **Not recommended: continue full editorial resolution or revert all gather work.**
   The former reproduces unbounded scope growth; the latter restores known integration
   failures unless separately mitigated.

No production mitigation is implemented or qualified by this audit. The title and
explicitly corroborated numeric-marker candidates repair both diagnosed truncations
in the experiment, leaving 67 body comparisons and 13 refusals for causal accounting.
Carry these two narrow candidates into implementation review; do not widen title
matching or presume a heading-selection overhaul is needed. Any refusal contract
must identify affected classes and measured usable yield. If qualification requires a
new editorial subsystem or broad heuristic redesign, stop for a scope decision.

## Human decisions and next sequence — 2026-10-22

The human explicitly approved all four recommendations after the PR walkthrough:

1. Approve the three-way scope split and separate causal versus editorial ledgers.
2. Adopt Q1–Q8 as the qualification amendment, including operational-yield review and
   explicit acceptance that missing historical wire/provenance receipts cannot be
   reconstructed. This evidence boundary is not a waiver of unknown material provider
   regressions. Original criteria 1–7 and 9–10 and main-promotion gates remain.
3. Prefer a separate candidate constructed from migration reference `ed20e9c2`, bringing
   forward necessary replacement improvements and the two supported notice repairs.
   No wholesale rollback or presumption that the earlier revision is already safe.
4. Preserve PR #524, historical evidence and broader gather work for later reconciliation;
   do not assume Kenny has accepted their design or ownership.

Current authorization is to record these decisions, correct stale text, validate and
land PR #528 into `codex/gettenberg-qualification`, with a hard stop at 11:20 PDT
(18:20 UTC). Routine landing repairs remain bounded by that deadline; blocking CI or
P0–P2 findings prevent integration. This is an audit/planning integration, not acceptance
of the product under Q1–Q8. A subsequent bounded grant constructs and qualifies the
narrower candidate. No production changes, main promotion, canonical corpus promotion,
package publication, PR #524 merge or terminal work-item/execution closeout are inferred.

Internal closeout plan: retain execution records as `in_progress`, WI0010 and WS
nonterminal; record verified PR528 head/base/merge SHAs in the runlog if integration
succeeds. Actual main-delivery qualification and canonical closeout remain pending.

## LRH process finding

The earlier escalation rule already stops repeated repair failure and fundamental
scope conflicts. This case exposes a different failure: successive locally successful
runs introduced new policy obligations while global acceptance stayed unresolved.
Per-run approvals and passing tests did not reveal the accumulating subsystem scope.

Proposed additional guardrail: before each continuation, show the original deliverable,
current blocker, causal owner and new obligations added since the last milestone.
If a repair requires a new product policy/subsystem or repeatedly increases the
acceptance surface without closing the original blocker, stop for an ownership and
causality audit even when the individual patches are technically sound. Do not use
approval-count targets as a substitute for correctness or scope control. This is a
process recommendation for LRH, not an LRH implementation in LCATS.

## Evidence navigation

- [Experiment archive and reproduction](../../../experiments/10_gettenberg_qualification/results/gettenberg-scope-audit-20261022/README.md).
- [Meeting brief](gettenberg-scope-meeting-brief.md).
- [Runlog](gettenberg-development-log.md), scope-audit grant and completion checkpoint.
- [Original responsibilities](../design/proposals/adopted/lcats-gettenberg-redesign/00_proposal.md), lines125–143 and334–337.
- [Baseline caller inventory](gettenberg-baseline.md), lines140–155.
- [Original causal repair evidence](gettenberg-corpus-repair-plan.md), lines8–33.
- [Qualification population evidence](gettenberg-qualification.md), lines83–100,157–178 and220–245.
- [Current readiness contract](gettenberg-readiness-contract.md), lines8–52.
- [Current WI0010 scope/gates](../work_items/resolved/WI-GETTENBERG-0010.md), lines79–92.
- [Current source adapter](../../src/lcats/gatherers/gutenberg_source.py), lines99–156.
- [Current body extraction](../../src/lcats/gatherers/story_body.py), lines63–96 and125–182.
- [Current parser](../../src/lcats/gatherers/parser.py), lines1275–1283 and1345–1512.
- [Installed logging dependency](../../src/lcats/gatherers/mass_quantities/gatherer.py), lines79–108.

Source line citations refer to pinned product head6a873b61; prior historical checkpoint
claims retain their original dates and do not describe newly accepted behavior.
