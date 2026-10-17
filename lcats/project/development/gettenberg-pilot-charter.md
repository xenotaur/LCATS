# Gettenberg bounded execution charter

Status amendment (2026-10-14): approved in PR #503; the human explicitly
started run `gettenberg-20261014` at 07:55:39 UTC. Its bounded grant and
09:55:39 UTC deadline are recorded in the [development log](gettenberg-development-log.md).
The original planning status was "proposed for review; no implementation run
has started." The authorization terms below are unchanged; this amendment
records activation and does not renew or enlarge the grant.

## Purpose and activation

Pilot coordinator-led implementation of the
[approved design](../design/proposals/proposed/lcats-gettenberg-redesign/00_proposal.md)
under [WS-GETTENBERG](../workstreams/proposed/WS-GETTENBERG.md). Preserve LRH
scope, evidence, review, and lifecycle discipline while delegating routine
engineering decisions. The first two-hour run may deliver a qualified subset;
it does not promise the entire replacement within that budget.

The human authorized drafting this charter and initial plan in one review PR.
It becomes an operating grant only after approval of its concrete revision
and an explicit instruction to start. Filing or merging this planning PR alone
does not launch implementation. Record the grant and charter commit in the
first checkpoint. No persistent chain-defaults, skip-consent, installed-skill,
or global policy changes occur. The earlier one-run exception for landing
proposal PR #501 does not carry over.

## Roles and authority

| Actor | Delegated authority | Boundary |
|---|---|---|
| Human owner | Approve charter, start/renew a run, approve material redesign and main promotion | Retains publication and budget-extension decisions |
| Coordinator | Scope child WIs within the design, sequence, choose bounded engineering details, delegate, repair, review, and integrate | Cannot enlarge its grant, weaken acceptance, or represent agent decisions as human approval |
| Worker | Execute one scoped assignment at a recorded base commit and return changes/evidence | No integration merges, shared planning updates, recursive delegation, or scope expansion |
| Independent reviewer | Inspect the specified diff and acceptance evidence at the current head | Must not be the author of the reviewed changes; cannot authorize main promotion |

The coordinator may choose signatures, normalized schema, parser, locking,
measured resource targets, and command/error details left open by the design.
Record the decision and evidence before implementing it. Material changes to
agreed user behavior, feature reductions, new external services, destructive
data migration, and fundamental redesign return to the human. LCATS AGENTS.md
and STYLE.md remain applicable. No new paid external model calls or publication
are authorized. Use the session's selected model without automatic upgrades.

## First-run resource budget

| Resource | Proposed limit/allocation | Measurement |
|---|---|---|
| Elapsed time | 120 minutes maximum | UTC start/deadline, including tools, CI waits, worker waits, and recovery |
| Concurrent agents | Three total including coordinator | At most two live delegated assignments |
| Delegated assignments | Four maximum, including review | Each new/restarted assignment counts, even when reusing an agent |
| Cumulative worker occupancy | 60 minutes maximum | Sum dispatch-to-completion/interruption intervals, including tool waits |
| Individual assignment | 30 minutes or remaining worker allowance, whichever is smaller | Deadline in assignment packet |
| Worker review reserve | 20 of the 60 minutes | Not available for new implementation |
| Final verification/checkpoint | Last 30 elapsed minutes | No new features after minute 90; bounded repair, validation, review, and handoff only |

This recommends at most 180 aggregate agent-minutes of occupancy: 120
coordinator plus 60 workers. It is a usage proxy, not a token/credit/dollar cap
or pricing estimate. Record available per-run token/cost telemetry with units
and provenance; otherwise write `unavailable`. Account-wide usage changes are
not attributable per-run consumption while other sessions run. A strict credit
ceiling requires an observable, enforceable meter and a separately agreed
threshold before launch; do not invent a token conversion.

Limits are enforced by coordinator checks, not a new runtime scheduler. Check
time and allowances before dispatch, after tool completion, and at least every
15 minutes. Keep waits bounded; avoid operations unlikely to fit the remaining
time. Stop workers and checkpoint before the deadline; leave no autonomous
work running after it. If a tool cannot be interrupted promptly, record the
overrun and cause rather than claiming exact enforcement. Compaction, restart,
or handoff does not reset budgets. This planning PR consumes none of the future
run allowance. The first exhausted limit governs; further execution requires
a new human grant. Finish early when scoped acceptance is satisfied.

## Launch preflight

Record repository/base SHA, LRH CLI version, selected model/backend, actual
loaded skill paths and content fingerprints, project environment, and applicable
local instructions. Inspect gate-policy status and distinguish stale persistent
consent from this explicit run grant. Verify each CLI operation used by the
adapter exists; a skill requiring an unavailable command is a real capability
gap. Do not silently restamp consent, reinstall skills, or repair the LRH repo.
If a mismatch prevents a required check, report it before implementation; a
harmless unrelated LRH follow-up need not stop the pilot. Record permissions
and telemetry actually available rather than claiming runtime enforcement.

## Branch and lifecycle protocol

Start from freshly fetched main containing this planning PR and its closeout.
Record the main SHA and create an integration branch under `codex/`. Worker
worktrees use named integrated base SHAs and disjoint write ownership. Only
the coordinator updates shared planning, execution, and log files. A branch
or worktree does not replace filesystem/network/data-access permissions.

Use small work-item PRs targeting the integration branch. After independent
review and required validation, the coordinator may accept and merge them
under this charter, recording the exact head and base SHAs. Recheck the PR
base immediately before merging; a retargeted PR never inherits main-merge
authority. Workers return commits and evidence to the coordinator.

| Existing LRH behavior | Scoped pilot adaptation | Evidence retained |
|---|---|---|
| Per-item human plan confirmation | Coordinator approves bounded plans under the human charter grant | WI, authority source, scope, acceptance, validation, base SHA |
| Execute requires WI on origin/main and resolved dependencies | Bootstrap WI must be on main; later WIs may be authored on integration before dispatch | Each dependency is canonically resolved or verified within this run at an integrated SHA |
| Stop on any failing CI or uncleared finding | Bounded diagnosis/repair; no integration with blocking failures | Failure, hypothesis, fix, rerun, re-verification |
| Human merge gate | Coordinator approves integration-branch PRs only; main stays human-approved | Agent decision, current head/base, review/check evidence |
| Closeout after merge | Internal integration is staged delivery; canonical closeout waits for main | Execution stays in_progress and WI nonterminal until main delivery |

Do not invoke unchanged `/lrh-execute` or `/lrh-land` and fabricate their human
responses or main-branch state. Read and reuse their compatible procedures
under this explicitly approved adapter. Preserve idempotence, evidence,
readiness, validation, and all non-conflicting constraints. Unexpected policy
conflicts require escalation. Use native CLI/schema support where compatible;
never invent statuses to force the protocol through validation.

A staged dependency requires an acceptance-to-evidence mapping, independent
review, relevant passing tests, and proof that the verified integrated commit
is an ancestor of the child's base SHA. Keep native prompt-readiness separate from the
pilot dependency decision. If a prerequisite is invalidated, stop descendants
and revalidate. Every child has an LRH execution record; the log links the tree.

Default to one final promotion PR to main after full qualification. Propose
an earlier milestone only for review size, integration risk, or a design
issue; human approval remains required. Do not mark records landed, resolve
WIs, adopt the proposal as implemented, or close the workstream merely because
an internal PR merged. Actual main closeout reconciles all child PRs and
records against the main merge. Partial promotion resolves only verified,
delivered items. WI-RELEASE-0039 still runs near actual publication.

## Assignment and review contract

Every packet names the WI, parent run, objective, base SHA, allowed paths,
interfaces, acceptance, validation commands, expected output, deadline, and
remaining allowance. Reports include commits/files, commands and outcomes,
limitations, and unexpected findings. No recursive delegation. An independent
reviewer receives the governing specification and current diff, not only the
author's summary.

Start sequentially through core model/ingestion contracts. Delegate bounded
audits, fixtures, or separate implementation only when interfaces and ownership
are clear. Independently review substantive changes before integration;
recheck findings after fixes at the new head. No unresolved P0-P2 findings may
integrate. Lower-priority deferrals need rationale and linked follow-up;
correctness/security issues cannot be relabeled to pass. If review cannot fit
the allowance, preserve the work as staged and unaccepted.

## Stabilization and escalation

- Diagnose routine failures within item/run allowances. Do not repeat identical
  attempts without a new evidence-based hypothesis.
- After two unsuccessful repair cycles, pause affected descendants and examine
  the design/approach. The coordinator may make one documented replan within
  approved scope. Continued failure after that stops the affected item; only
  safe, useful, independent work may continue within the original budget.
- Fundamental design/scope conflict, missing authority, unavailable indispensable
  dependency, untrustworthy validation, or exhausted run budget stops the run.
  Preserve a resumable checkpoint and present the human with a concrete
  decision, alternatives, and supporting evidence.

## Validation and data stewardship

Define acceptance before implementation. Preserve regression tests; justify
test changes from the specification rather than the need to clear failures.
Use real SQLite/parser fixtures and deterministic boundary tests. Run applicable
checks from `lcats/` in the project environment, with imports resolving to
the intended worktree: `scripts/format --check --diff`, `scripts/lint`,
`scripts/test`, and `lrh validate`.

Inventory required checks from workflows and branch requirements. Tie evidence
to the exact candidate head. Missing, unexpectedly skipped, queued, or stale
checks are not passes. If internal PR base filters omit CI, record that fact
and run equivalent local checks; final main-target CI remains required.
CI changes need a separately scoped WI and cannot weaken required validation.

One coordinator owns bulk Gutenberg acquisition. Reuse valid cached snapshots
and record source/hash/size; share immutable inputs. Workers may not separately
fetch bulk catalogs. Set concrete resource/request bounds before acquisition;
until then use fixtures. Do not refresh valid caches or mutate the canonical
corpus as a test side effect. Isolate generated catalogs and comparison outputs.
Unit tests remain offline; full-snapshot qualification is separately measured.

## Checkpoints and completion

Use [the development log](gettenberg-development-log.md) for compact process
observations; WIs/execution records remain authoritative for scope/delivery.
Checkpoint at start, completed items, replans/failures, at least every 15
minutes, and before suspension. Include UTC time, charter/grant, main/base/head
SHAs, active assignments, staged dependency evidence, time/worker allowances,
validation/review state, unresolved findings, remaining scope, and exact next
action. Append explicit amendments rather than silently revising history.
Do not commit transcripts or secrets. Communicate progress and material blockers.

The final report distinguishes qualified delivery, staged/unreviewed work, and
unattempted scope. A two-hour run ending does not complete the workstream.
Full completion requires every design criterion: migration, first-use/offline
behavior, resource/corpus comparisons, exercised Diataxis docs, main promotion,
and accurate closeout. A later run needs a renewed bounded grant.

## Learning objectives

Measure human interventions, elapsed/wait time, worker occupancy, assignments,
observed tokens/cost where available, repair/replan cycles, review findings,
and coordination overhead. Separate observations, interpretations, and proposed
LRH changes. One pilot does not prove causal speedup. Feed evidence into existing
LRH run-tree/execution-framework/assistant work, without building a competing
runtime here. Each recommendation needs an observed example and a proposed
acceptance test, including branch-aware dependencies, delegated decisions,
budget enforcement, or checkpoint recovery.

## Run 2 amendment — approved and activated 2026-10-14

The human approved the revised plan in this session and explicitly instructed
the next run to proceed. This amendment supersedes conflicting first-run budget
and fresh-main launch provisions for run `gettenberg-20261014-2` only. Resume
the existing integration branch at718058627cbfbb7942f117f8dfe3cda39796769d;
WI-0002's qualified staged merge3793d152 is an ancestor. Scope is WI-0003 only.

- Start17:13:39 UTC; target/feature freeze18:13:39; hard stop18:43:39.
- Normally coordinator plus one worker, four agents total maximum.
- Six assignments maximum. Up to two repair/recheck follow-ups on the same
  review scope remain in that assignment; expanded scope counts separately.
- Worker occupancy target20–30 minutes, hard45 cumulative minutes including
  waits; reserve15 for review. Individual assignments remain bounded by the
  original30-minute ceiling and remaining allowance.
- Reassess progress at minute45. No new features after minute60; final30
  minutes are for bounded repairs, qualification and checkpointing.
- Record available shared-account usage at launch, around minute30 and before
  optional additional delegation. No numerical usage stop threshold is agreed.
- Use compact assignment packets and linked authoritative evidence. Focused
  tests during development; qualify stable source after review. Repeat relevant
  qualification when repairs invalidate its source identity.

All other authority, data stewardship, independent review, repair/escalation,
exact-head CI and human main-promotion requirements remain unchanged. This
renewal does not resolve native WIs or grant future runs.

## Run 3 amendment — approved and activated 2026-10-14

The human accepted the recommendation to proceed with WI-0004 using the same
bounded single-item plan and instructed "Please proceed". Run
`gettenberg-20261014-3` starts19:27:21 UTC, target/feature freeze20:27:21,
hard stop20:57:21. Resume integration at1bc04c29384a1f727cde6a3a5c55d9c4107f20c9,
with qualified WI-0003 mergeb2aa080a as an ancestor. WI-0004 only; reassess
promotion at completion, without granting main promotion.

Inherit run2 budgets: normally coordinator plus one worker, four agents total
maximum; six assignments; up to two same-scope review repair/recheck follow-ups
per assignment;45 cumulative worker minutes,15 reserved for review; individual
assignments at most30 minutes and bounded by remaining allowance. Usage at
launch, minute30 and before optional delegation; minute45 reassessment. No
numeric usage threshold. All other charter safeguards and nonterminal native
status rules remain. No persistent consent/gate changes or future-run grant.

## Short planning grant — approved and activated 2026-10-15

The human explicitly approved a 15-minute sprint for the next logical step.
Run `gettenberg-20261015-plan` starts 00:07:30 UTC; content freeze 00:17:30;
hard stop 00:22:30, including tools and checkpointing. Finish early if complete.
One coordinator only, no delegated assignments. Scope is WI-0005 design/readiness:
record acquisition decisions, API boundaries, an acceptance matrix and resumable
handoff. No implementation, bulk downloads, independent-review claim, main merge,
WI resolution or future implementation grant. Small official-documentation reads
and Git synchronization are permitted; no Gutenberg data acquisition.

Base is freshly fetched main 2f14e4e886c1f3fd6a6f021e3f72db6621cbb3a2;
planning branch codex/gettenberg-acquisition. The final five minutes are reserved
for documentation/control-plane validation, commit and checkpoint. A branch push
may preserve the checkpoint; no PR/review/CI wait is required for this planning
tranche. Product source and measured evidence remain unchanged. Other charter
scope, stewardship and escalation rules continue; persistent consent is unchanged.

## Short routing grant — approved and activated 2026-10-15

The human authorized the proposed 5–10 minute routing qualification sprint with
"Go for it!" Run `gettenberg-20261015-routes` starts 00:23:20 UTC, target
00:30:20, hard stop 00:33:20. One coordinator only; no delegation. Scope: existing
RDF fixtures and official documentation, a grounded routing table, explicit
uncertainties, runlog and resumable branch checkpoint. No implementation, ebook
or catalog download, PR/main promotion, WI resolution or future-run grant.
Reserve the final three minutes for validation and checkpointing; finish early
if complete. Continue codex/gettenberg-acquisition at a528ebfd; branch push is
permitted. Other stewardship, review and persistent-policy boundaries remain.

## Acquisition implementation grant — approved and activated 2026-10-15

The human approved the proposed restaurant run with "Go for it!" Run
`gettenberg-20261015-core` starts 00:59:27 UTC, target 01:59:27, hard stop
02:14:27. Checkpoints at minutes 20/40; feature freeze no later than minute 45
(01:44:27). The last allowance is for review, repair, validation and checkpoint.
Scope: one coherent tested WI-0005 acquisition tranche, not a promise to finish
all routing, refresh, decoding and provenance. Continue the acquisition planning
base bd2998a8; fetched main remains 2f14e4e8. Implement on a child branch
codex/gettenberg-acquisition-core, with PR base codex/gettenberg-acquisition.

Coordinator plus one independent reviewer planned. Inherit ceilings of four
concurrent agents, six assignments and 45 cumulative worker minutes, with at
least 15 reserved for review; no recursive delegation or automatic expansion.
No new bulk download, main promotion or persistent-consent change. The existing
coordinator plan/repair/integration adapter applies to lrh-implement; the human's
run grant authorizes bounded engineering choices without another per-item gate.
Independent review and canonical validation remain required before integration.
Finish early if the scoped tranche is complete; preserve unfinished WI criteria.

## Preparation run grant — approved and activated 2026-10-17

The human approved the longer unattended WI-GETTENBERG-0007 run with
"Go for it!" Start 01:54:42 UTC; two-hour target/feature freeze 03:54:42;
three-hour hard stop 04:54:42, including reviews and checkpointing. Normally
coordinator plus one independent reviewer; four agents maximum, six assignments.
Additional repair-verification dispatches count toward those six assignments;
the earlier two-recheck allowance is superseded for this run. Retain the
conservative 45 cumulative worker-minute limit, 15 reserved for review, and
30-minute individual limit. Check time every 15 minutes and usage at launch,
minute30 and before additional delegation. No automatic renewal.

Core scope: source-aware preparation and explicit setup policy. CLI wiring may
proceed where prerequisite evidence and budget support it. Default mirror
qualification is separate; no live automatic/bulk acquisition in this run.
Routine design, bounded repairs and qualified integration-branch merges are
authorized. No main promotion, corpus changes, dependency removal, persistent
consent changes or material redesign. Preserve nonterminal native records.

## Overnight live-gather grant — approved and activated 2026-10-17

Human approved "Go for it!" after a two-hour target / three-hour hard-stop proposal.
Start07:57:23 UTC (00:57 PDT); feature freeze/target09:57:23; hard stop10:57:23.
Normally coordinator plus one reviewer, four total maximum, six assignments,
45 cumulative worker minutes with15 reserved for review, individual at most30.
All repair-verification dispatches consume assignment slots. Check elapsed time
every15 minutes and shared usage at launch/hourly/before additional delegation.
Final hour is repairs, validation, integration and checkpointing only. Finish early
when qualified; no renewal, scope expansion, main promotion or broad dependency
removal. No live Gutenberg bulk downloads or corpus changes. Explicit source
configuration only; operational default mirror qualification remains separate.

Scope: WI0007 mass_quantities live access via new catalog/acquisition/decoding/
cleanup, setup approval and genuine offline enforcement, preservation/comparison
fixtures and docs. Narrow adjacent curated-cache policy plumbing is necessary to
make the command-wide offline flag truthful. The approved coordinator LRH adapter
continues; internal qualified PR merges only, native records nonterminal until main.
