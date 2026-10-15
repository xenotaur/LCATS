# Gettenberg development process log

For [WS-GETTENBERG](../workstreams/proposed/WS-GETTENBERG.md) under the
[pilot charter](gettenberg-pilot-charter.md). WIs/execution records remain
authoritative for scope/delivery. Historical entries retain their original state;
current run checkpoints appear below.

## Entry and checkpoint format

Entries record UTC time, run/parent and WI/execution links, actor role,
base/head SHAs, decision/hypothesis, action/result, verification evidence,
friction/rework, and proposed LRH improvement. Label observations separately
from interpretations and proposals. Amend explicitly; omit transcripts/secrets.

Checkpoints add charter revision/grant, start/deadline, elapsed and worker
minutes, assignment count/active workers, measured usage or unavailable,
staged dependency evidence, review/check status, remaining scope, unresolved
findings, and exact next action. Live state belongs in this log and execution
records, never an assistant role directory. Avoid duplicating WI statuses.

## 2026-10-14 — Planning capture; execution not started

- Authority: human requested one review PR for charter/initial plan; accepted
  three maximum agents, two-hour first-run ceiling, and one final promotion
  unless review size, integration risk, or a design issue justifies an earlier
  milestone proposal.
- Planning base: LCATS `75eaf9e6`; governing design merged in PR #501.
- Observation: `/lrh-execute` requires origin/main availability and resolved
  dependencies; current chain defaults stop on failing CI. These differ from
  the proposed integration-branch repair loop.
- Interpretation: a scoped adapter requires explicit authority and staged
  dependency evidence; unchanged skill invocation would misrepresent lifecycle.
- Proposed procedure: preserve native records/checks; distinguish staged
  integration from main landing and agent decisions from human approval.
- Proposed usage: 120 coordinator plus 60 cumulative worker minutes; four
  assignments; 20 worker minutes reserved for review; final 30 elapsed minutes
  for verification/checkpoint. This is not a credit guarantee. No pilot token
  or monetary consumption has been measured.
- Hypothesis: bounded delegation reduces human interruptions while retaining
  review quality at acceptable total effort. No speedup is established.
- LRH recommendation candidate: represent branch-scoped dependency acceptance
  and delegated integration separately from main delivery/human approval.
  Future acceptance test: staged evidence may unblock a scoped child but cannot
  resolve a global WI or authorize main merge.
- Evidence: [workstream/charter creation](../executions/AD_HOC/2026_10_14_06_19_47_WS_GETTENBERG.md)
  and [bootstrap item creation](../executions/AD_HOC/2026_10_14_06_19_47_WI_GETTENBERG_0001.md)
  record planning validation; they do not represent implementation.
- Next: review/land the planning PR, then obtain explicit start authority and
  create the first run checkpoint. No execution grant or deadline is implied.

## 2026-10-14 07:55:39 UTC — Run 1 authorized and started

- Run: `gettenberg-20261014`; human explicitly instructed "Please start the
  two-hour pilot as previously discussed." Charter revision `1dff24a94f37a5f341d11c30301a9cc50cdffe6a`;
  main/base `5cfd2d71caf6f3eedfdfc0b830b5c5ff1a74ba3b` includes planning closeout
  and the separately confirmed gate restamp. Integration branch:
  `codex/gettenberg-pilot-20261014`.
- Deadline: 09:55:39 UTC; no new features after 09:25:39 UTC. Limits: 3 live
  agents, 4 assignments, 60 worker minutes including waits; 20 reserved for
  review. No runtime-enforced credit meter; per-run tokens/cost unavailable.
- Coordinator plan accepted under charter: execute WI-GETTENBERG-0001 first,
  modifying baseline/evidence, development log, release reconciliation, and
  scoped downstream WIs. No library, notebook, CI, dependency, or corpus edits
  in this item. Prior-art check present; native readiness true with no warnings;
  prompt idempotence check returned no records.
- Prompt: `PROMPT(WI-GETTENBERG-0001:WI_GETTENBERG_0001)[2026-10-14T07:56:37+00:00]`.
  Validation: project environment, bound imports, version/format/lint/test,
  LRH validation, native WI readiness, manual matrix/caller evidence trace,
  independent review and exact-head checks before internal integration.
- [Preflight](evidence/gettenberg-pilot-20261014/preflight.json): CLI
  `0.2.5.dev3596+gd86755f50`; all 18 watched Claude/Codex fingerprints fresh;
  skip consent invalid as expected. Explicit charter grant supplies run authority.
  No restamp or consent writes. CLI prompt/readiness/merge operations available.
- Observation: installed validation guidance supports `scripts/test --log`, but
  LCATS's actual script forwards that option to unittest. Adapter uses output
  redirection around `scripts/test`; it preserves tests without modifying tools.
- Assignment 1: `pilot_caller_audit`, read-only, base equal to main, dispatched
  about 07:57 UTC, deadline 08:12 UTC, 15-minute ceiling. No allowed write paths,
  no recursive delegation/network acquisition. Returns cited caller inventory
  and migration/library-extraction recommendations to coordinator. Other agents
  from earlier planning runs are completed/errored, not live assignments.
- Review state: none yet; no staged prerequisites accepted. Remaining scope:
  baseline, reconciliation, downstream planning, then only qualified work that
  fits the budget. Next action: inspect current upstream capabilities/cache
  inputs and establish offline baseline evidence.

## 2026-10-14 08:10 UTC — Bootstrap evidence prepared

- Main/base remains `5cfd2d71`; integration checkpoint `de93431b`; scoped branch
  `codex/gettenberg-baseline-0001`. No production/CI/notebook/dependency changes.
- Assignment 1 completed before 08:05:14 UTC. Conservatively account 9 worker
  minutes (including dispatch uncertainty); 51 remain, 20 reserved for review.
  Assignments used: 1/4; no active worker. Elapsed about 15 minutes; about 105
  remain to the 09:55:39 deadline. Next assignment is independent bootstrap
  review with a 12-minute ceiling, not another implementation worker.
- [Baseline](gettenberg-baseline.md) records a complete 78,937-record cached
  archive audit, input hashes, all observed XML elements, caller dispositions,
  fixture plan and remaining measurement/provenance gaps. No bulk downloads.
- Observation: canonical suite passes 2,550 tests while actual wrapper English
  query returns zero IDs versus 62,689 upstream. Interpretation: fake-row tests
  masked contract mismatch. Recommendation: real parser/storage/public-API
  acceptance tests; acceptance test for LRH: a green suite cannot substitute
  for a capability's missing behavioral evidence.
- Observation: audit found old notebooks, raw SQLite experiment access and eager
  indirect imports. Recommendation: combine import closure, notebook source
  inspection and raw-schema searches; test an audit fixture with each hidden
  dependency form and verify each receives an owner/disposition.
- Coordinator scoped WI-GETTENBERG-0002 through 0010 and reconciled release
  planning. Every new item is native prompt-ready, but none has an accepted
  staged dependency yet. WI-RELEASE-0039 remains near-publication only.
- Canonical baseline: format/lint/test pass. LRH zero errors, 351 warnings
  (two pre-existing unquoted prose warnings removed by release-WI rewrites).
- Next: independent review against bootstrap acceptance, verify/fix findings,
  create its internal PR and integrate only with exact-head validation.

## 2026-10-14 08:19 UTC — Independent bootstrap review repaired

- Assignment 2 reviewed candidate `bcdcc565` against `5cfd2d71`, dispatched
  08:11:14 and returned by 08:17:42. Account 7 minutes; cumulative worker
  occupancy 16/60, assignments 2/4, no active workers. About 97 run minutes
  remain; feature freeze remains 09:25:39, deadline 09:55:39 UTC.
- Reviewer found P2 circular qualification/closeout sequencing and P3 tracked
  path count mismatch. Coordinator reproduced both and repaired them. Original
  review rejected the unfixed P2; coordinator verifies the narrow repairs,
  without claiming another independent review or human approval.
- Observation: uniform acceptance boilerplate incorrectly made a delivery
  condition a prerequisite for internal staging. Recommendation: LRH acceptance
  should distinguish staging, promotion and closeout phases; proposed test:
  reject a dependency graph requiring its own future delivery before staging.
- Main/base unchanged. Existing 2550-test baseline still covers unchanged
  production code. Next: validate repaired metadata, create internal PR, verify
  exact-head CI/base and integrate under the charter. No staged dependency is
  accepted until that evidence is recorded. Final qualification and main
  promotion remain pending.

## 2026-10-14 08:30 UTC — Bootstrap integrated; parser scoped

- PR #504 merged only into `codex/gettenberg-pilot-20261014`, merge
  `1299f9800871fcbb44a012554749675ea25b71c9`, verified head
  `c8beac9c078353369e4299db2eb9469ec6b01351`. Base rechecked immediately
  before merge; test (push and PR), coverage and lint all passed at that head.
  All three automated review threads resolved after verified repairs. Independent
  review and acceptance mapping are linked in WI-0001's execution record.
- Staged WI-0001 accepted by coordinator under charter: complete baseline,
  caller/fixture/measurement matrix, release reconciliation and scoped next WIs.
  Native WI/execution remain nonterminal. `git merge-base --is-ancestor`
  verifies the accepted integration commit is an ancestor of WI-0002's base.
- Final local rerun initially failed five tests due to sandbox denial of their
  temporary worktree files. Same suite with authorized worktree writes passed
  all 2550 tests in 61.422s. This was an environment repair, not a code/test
  change. Optimized-mode sparse-file probe also verified explicit audit bounds.
- Automated review found assert-based audit limits and stale charter activation
  text; both fixed. Observation: evidence helpers need optimized-mode safety
  checks; proposed LRH test: run resource-limit probes with `python -O`.
- Elapsed about 35 minutes; 85 remain. No active workers; 2/4 assignments and
  16/60 worker minutes used, 44 available. Freeze/deadline unchanged.
- Coordinator accepts WI-0002 plan at base `1299f980`: additive immutable typed
  records, pure bounded parser, offline fixture/security tests, reference docs
  and direct lxml declaration. No catalog/CLI/caller migration in this item.
- Decisions before implementation: tuple-valued source metadata preserves
  multiplicity and order (including multiple extents/modification claims);
  literals retain language/datatype, contributor roles use full URIs, dates
  retain source lexical values, and RDF bytes serialize as base64 with SHA-256.
  Every unsupported predicate has a diagnostic path and retained source bytes.
  Reject unsupported known shapes and ambiguous identities rather than silently
  reporting partial modeled metadata. Use lxml with DTD/entity/network loading
  disabled, reject DOCTYPE, and enforce 2 MiB before parsing. No general RDF
  graph resolution is claimed. Source labels never become network locations.
- Validation plan: real cached records 10000/10040/84/10001 plus authored edge
  cases, fresh-process import/no-network checks, canonical suite and independent
  review. A bounded full-archive parse probe may establish feasibility but is
  not catalog-build or corpus qualification. Next: implement this scope.

## 2026-10-14 08:42 UTC — Full-source probe corrects the parser profile

- First parser prototype passed 2575 canonical tests in 60.240s, including 25
  new focused tests and executable docs. Full cached-source probe parsed 78897
  of 78937 records, rejected 40, in 287.003s / 104480768-byte peak RSS. These
  exploratory results precede the final candidate and are not acceptance.
- Inspection of actual rejected records 15813/16264 confirms in-record URI
  references to agents already defined under another role. Record 11008 has
  spaces in file URLs. No external graph fetch is needed. Hypothesis: the
  observed profile includes local agent links and malformed-but-preservable
  source URL spelling; the initial fixture set missed both.
- Scoped decision before repair: resolve contributor URI references only to
  agents defined inside the same record, rejecting missing or conflicting
  definitions. Percent-encode whitespace in non-ebook URI claims with explicit
  normalization diagnostics and retain exact original RDF. Strict ebook-ID
  validation remains unchanged. This expands source fidelity within the
  approved design; it does not introduce graph/network access or weaken the
  archive completeness gate. Add real fixtures and authored ambiguity cases.
- Avoid computing diagnostic paths for every successfully modeled element;
  create paths only for actual notices. Re-run the full probe with source hashes
  and identical bounds after repair. No catalog-build performance claim.
- Budget: about 47 elapsed / 73 remaining minutes; no active worker; assignments
  2/4, worker minutes 16/60. No descendants dispatched. Next: repair and obtain
  independent review of the candidate with complete source-accounting evidence.

## 2026-10-14 08:52 UTC — Core parser review repaired; export review running

- Assignment 3 independently found four P2 issues: comment/PI literal tails,
  unsupported mixed RDF shapes, inconsistent agent-identity validation, and
  quadratic repeated-reference allocation. Coordinator reproduced all four;
  reviewer independently verified repairs at `3460bf4` within the original
  assignment. Account 7 worker minutes conservatively: 23/60 cumulative.
- A real-data-only pass would have missed these valid/hostile edge cases.
  Observation: full-source evidence and adversarial independent review found
  different defects. Recommendation: require both; proposed LRH acceptance
  test supplies a fixture-complete implementation with an expansion/tail bug
  and verifies the review gate remains independent of the passing corpus probe.
- Pre-review candidate `682e0de` parsed all 78937 records, 2018879 resources and
  109170 contributions in 221.172s / 97189888-byte peak RSS; 223 explicit URI
  normalizations (222 file claims, one webpage). No rejected records or unknown
  predicates. This is pre-repair evidence, not final-head qualification.
- Reviewer flagged export expansion as a limitation. Coordinator bounded
  to_dict traversal and cumulative text, raising ExportLimitError without a
  partial export; explicit overrides preserve caller control. Successful
  exports preserve the same schema and original evidence. Decision stays
  within resource-safety/API scope and has focused rejection/real-fixture tests.
- Assignment 4 (last allowed), `pilot_export_review`, dispatched about 08:51
  UTC at `fb90bfe8`, read-only, no network/recursion, deadline 09:03 UTC and
  12-minute ceiling. Before dispatch 37 worker minutes remained; no new
  assignments can follow. Core source is frozen while final full-source probe,
  canonical tests and independent export review run.
- Elapsed about 57 / 63 minutes remain. Hard deadline and feature freeze remain
  09:55:39 and 09:25:39 UTC. No descendant implementation has started. Next:
  qualify this candidate and its exact-head internal PR; preserve a resumable
  boundary rather than dispatch work that cannot receive independent review.

## 2026-10-14 08:57 UTC — Review budget exhausted; qualified boundary selected

- Assignment 4 completed before 08:56 after independently rechecking repairs at
  `d77c30df`: source-label surrogate accounting (P2) and generated wrapper budget
  accounting (P3). No unresolved findings. Conservatively account 6 worker
  minutes, total 29/60; 4/4 assignments used, no active workers. About 62 elapsed
  / 58 minutes remain, but assignment allowance cannot be renewed implicitly.
- Coordinator selects the baseline + parser as this run's bounded deliverable.
  WI-0003 onward remain unattempted; starting another substantive item without
  an available independent-review assignment would undermine the charter.
  No permission to extend the run or promote main is inferred.
- Source evidence: final parser probe at `fb90bfe8` accounts for all 78937 records,
  2018879 resources and 109170 contributions, zero rejects, 223 explicit URL
  normalizations, 266.204s / 96927744 bytes peak RSS. Current rdf.py/errors.py are
  hash-identical; later model changes are export-only and independently tested.
  Full-source evidence and prototype failure are retained under evidence/.
- Process finding: review reserve was useful, but assignment count became the
  binding dispatch limit before elapsed time/worker minutes. Recommendation:
  future LRH run planning should forecast review/repair assignments separately
  from worker minutes; proposed test refuses a fifth dispatch despite spare
  elapsed/occupancy budget and produces a resumable accepted boundary.
- Next: final canonical checks, internal parser PR, exact-head CI and thread
  verification, integration-only merge, then final checkpoint/handoff. Do not
  close native records or create a main promotion PR for this partial scope.

## 2026-10-14 09:10 UTC — Automated review repairs in final qualification

- PR #505 targets the integration branch at base `1299f980`; its previous head
  `5d9f0b9f` passed all four expected CI checks. Copilot reported no findings;
  the configured Codex review reported two P2 findings: term-description
  identity loss and silently ignored structured text. Both were reproduced.
- Scoped decision: preserve rdf:about and rdf:nodeID explicitly on typed terms,
  including JSON export, rather than reject identities used throughout the real
  catalog. Preserve record-local blank-node labels without graph resolution.
  Reject nonwhitespace text/tails outside structured properties. Coordinator
  implemented these narrow review fixes at `2687a94b`; 39 focused tests pass.
- Core and export independent reviews remain recorded at their reviewed heads;
  this is coordinator re-verification of later automated findings, not a fifth
  delegated review. Full canonical checks and a fresh bounded full-source probe
  are running because parser/model source changed. Previous passing probes are
  historical evidence, not qualification of this new source.
- About 75 minutes elapsed /45 remain; assignments 4/4 and conservative worker
  occupancy 29/60 minutes, no active workers. No new work items or features.
  Next: record actual validation, push the repaired candidate, recheck exact-head
  CI/review threads, and integrate only if every required gate passes.

## 2026-10-14 09:19 UTC — Qualified boundary and final handoff

- Development stopped at this boundary, about 83 minutes 22 seconds after the
  07:55:39 start; final checkpoint publication/verification remains within the
  original 09:55:39 deadline. No further implementation or assignments in this
  run. All four assignments completed, conservative occupancy 29/60 minutes,
  maximum observed concurrency two including coordinator; no live workers.
  No human intervention was requested after the explicit start instruction.
  Per-run tokens/credits/cost and a complete tool-wait breakdown are unavailable;
  elapsed time includes CI and tool waits, not just implementation.
- Qualified staged delivery: WI-0001 baseline/caller audit/release reconciliation
  and downstream plan (PR #504, head c8beac9c, merge1299f980), plus WI-0002 typed
  records/pure bounded RDF parsing/export/tests/reference docs (PR #505, head
  c755d295, merge3793d152). Each exact PR head passed both test checks, coverage
  and lint; all review threads resolved after verification. Base was checked
  immediately before each integration-only merge. No unresolved P0-P2 findings.
- Acceptance mappings and review provenance remain in each WI execution and
  linked AD_HOC review records. [Integration evidence](evidence/gettenberg-pilot-20261014/integration-evidence.json)
  records exact full SHAs/check URLs and the final parser thread state. Verified
  1299f980 is an ancestor of3793d152. No unreviewed implementation is being
  described as accepted, and earlier reviewer heads are not relabeled as newer
  reviews. Narrow later automated findings received coordinator regression
  checks plus full canonical/source validation, explicitly recorded.
- Final source qualification at2687a94b (unchanged implementation in PR head and
  integration merge): 2589 canonical tests in60.784s,39 focused tests, formatting
  and lint clean; LRH zero errors/351 existing warnings. Full cached-source
  probe:78937/78937 records,2018879 resources,109170 contributions,zero rejects,
  223 explicit URI normalizations,272.997s,98091008-byte peak RSS. Exact source
  hashes and original failed probes are retained; no claim of catalog-build or
  corpus equivalence. Zero bulk-download bytes; canonical corpus untouched.
- WI-0003 through WI-0010 are unattempted. gutenbergpy remains required by the
  existing callers. No main promotion, publication, native closeout, persistent
  gate changes or LRH tooling changes. WIs stay proposed and executions
  in_progress pending actual main delivery. Integration branch is
  codex/gettenberg-pilot-20261014; reviewed implementation head3793d152, followed
  only by this control-plane checkpoint. No separate main promotion PR.
- Resumption requires a renewed bounded human grant. Start from the fetched
  integration branch, verify clean state, current instructions and gate status,
  and the accepted merge ancestry/evidence. Next item is WI-GETTENBERG-0003:
  first record normalized SQLite schema/index/query decisions, then implement
  bounded local-archive ingestion and read-only queries. No network/activation
  or caller migration in that item. Do not reuse expired time/assignment budget.

### Process findings for LRH

- Observation: full-source probing exposed40 real-record gaps after passing
  unit tests; independent review exposed text-loss/identity/expansion defects
  after a zero-rejection full-source pass. Interpretation: these evidence types
  complement each other. Recommendation/test: a run cannot substitute a passing
  corpus probe for independent edge-case review, or vice versa. Preserve failed
  probe identity and source hashes when repairs change the candidate.
- Observation: four assignment slots were consumed by one audit and three
  independent reviews, with31 worker minutes still available. Interpretation:
  assignment count, rather than occupancy or wall time, bounded new work.
  Recommendation/test: forecast review assignments explicitly and stop new
  dispatch at the assignment cap even if time remains; produce a qualified
  resumable subset rather than silently waive review or renew the grant.
- Observation: native LRH statuses cannot express integration-only acceptance,
  and generic WI boilerplate initially required future closeout before staging.
  Recommendation/test: model branch-scoped dependency evidence separately from
  main delivery, checking ancestor SHA and acceptance mapping while keeping
  native WIs nonterminal; reject circular staging/promotion prerequisites.
- Observation: checkpoints survived compaction with the original deadlines,
  limits, exact candidate hashes and pending checks intact. Recommendation/test:
  recover an active run from its persisted checkpoint without resetting budget
  or treating old-head checks as current-head passes. Also record review head
  and repair-verification actor separately instead of flattening them to a
  single misleading reviewed flag.
- Observation: no user decision interruptions were needed, but this one pilot
  has no matched manual-process baseline or attributable credit meter. It does
  not establish a causal speedup or cost saving. Future experiments should
  instrument phase waits and usage where available without converting occupancy
  into invented token/cost estimates.

## 2026-10-14 17:13:39 UTC — Run 2 started

Human explicitly authorized the revised bounded plan. Scope WI-0003 only;
base718058627cbfbb7942f117f8dfe3cda39796769d matches fetched integration.
Verified accepted WI-0002 merge3793d152 ancestry and existing acceptance links.
Gate fingerprints fresh, persistent skip consent invalid as before; explicit
charter grant is authority, no persistent policy changes. Native readiness
passes; no previous WI-0003 slug execution. Project Python3.11 environment,
SQLite3.46.0/lxml5.2.2 verified. Target/freeze18:13:39, stop18:43:39 UTC.
Assignments0/6; worker occupancy0/45 minutes,15 reserved review. Shared weekly
usage33% at launch; attributable per-run tokens/cost unavailable. No credit
reset or purchase authorized. Next: record schema/API decision, implement and
independently review before exact-head integration.

## 2026-10-14 17:27 UTC — Run 2 candidate ready for independent review

Schema/API decision is [gettenberg-catalog-design.md](gettenberg-catalog-design.md).
Assignment1 delivered normalized storage; conservative occupancy5/45 minutes,
no worker active. Coordinator implemented bounded ingestion/query API and real
archive/SQLite tests. Focused tests24 pass, including executable reference docs.
Decisions: lossless per-record zlib reduces source footprint; batch source-byte
budget bounds aggregate decoding; final complete status follows all allocating
evidence writes and integrity checks. No source acquisition or activation.
Next: assignment2 combined independent review, then final canonical/full-source
qualification. No new item. Deadline18:43:39/freeze18:13:39 unchanged.

Run2 review dispatch: assignment2 `catalog_review`,17:27UTC at7e4084c0,
read-only combined implementation/spec review; deadline17:47UTC. Source is
frozen during review. Worker accounting5/45 minutes used before dispatch;
40 remain including15 review reserve. Shared weekly usage34% at dispatch
(+1 percentage point from launch; not attributable run-only consumption).
Coordinator prepares only the reproducible qualification helper while review
runs. No full-source or canonical reruns until the candidate is stable.

## 2026-10-14 17:35 UTC — Run 2 independently reviewed source qualifying

Assignment2 cleared cde945dd after two bounded repair/recheck follow-ups.
See its execution record for findings and independent probes. Worker occupancy
13/45 minutes conservatively (5 implementation +8 review), assignments2/6,
no active workers. Elapsed about21 minutes; freeze/deadline unchanged.
Canonical checks and full cached-source build/query qualification now run on
that exact source. Candidate is private /tmp only, using original cached input.
No further implementation planned unless qualification exposes a defect.
Process observation: bounded review follow-ups preserved one review context
and assignment slot while still independently checking the changed source.

## 2026-10-14 17:44 UTC — Run 2 local qualification passed

Full cached-source build/query qualification passed on cde945dd:78937 records,
zero rejected/uncommitted, all expected relationships and seven fixture round
trips. Build435.864s, peak RSS71630848 bytes, database2177388544 bytes; all
configured targets pass. Canonical2617 tests, formatting, lint and LRH pass.
Central evidence is in `evidence/gettenberg-pilot-run2-20261014/`; no duplicate
full result tables here. Zero network-download bytes and no active catalog.
Thirty-minute usage observation38%, launch33% (+5 shared-account percentage
points; not attributable run-only consumption). Assignments2/6, occupancy13/45,
no active agents. Only evidence/docs changed after reviewed source cde945dd.
Next: internal PR and exact-head checks; no additional item or review dispatch.

## 2026-10-14 17:53 UTC — Run 2 automatic review repair

PR506 exact-head d1548a8e passed all four CI checks. Automatic Copilot and
Codex reviews identified SQLite FULL/INTERRUPT misclassified as build_failed;
Copilot also identified duplicated error-code text and a spacing typo. All
verified and repaired at fc2b97bb. Real SQLite regression probes additionally
exposed fatal-error savepoint cleanup masking the original SQLite code; outer
cleanup now preserves it. Two initial authored probes used unsupported RDF term
shapes and failed before SQLite; corrected to valid alternative-title fixtures.
Thirty focused tests pass. This is a bounded repair, not a design replan.

Assignment3 `catalog_error_review`, dispatched17:52UTC, new focused independent
review of d1548a8e..fc2b97bb, maximum5 minutes and deadline17:58UTC. Assignments3/6;
13/45 worker minutes used before dispatch. No recursive delegation. Account
usage38% before dispatch. Coordinator repeats canonical and full-source checks
on fc2b97bb; prior measurements remain retained with their actual source hash.
No next item, network download, activation or main promotion. Hard stop18:43:39,
feature freeze18:13:39 unchanged. Next: review clearance, final evidence/CI,
resolve verified findings, then internal integration.

## 2026-10-14 17:58 UTC — Run 2 minute45 reassessment

Scope remains WI-0003 only. Independent focused repair review cleared fc2b97bb;
canonical2619 tests/format/lint/LRH pass. PR506 head a42df73a differs only in
records/evidence from reviewed source. Four automated review threads resolved
after real SQLite regression checks and independent verification. Final source
full-build rerun has51968 committed records at17:58:06, within budgets; original
qualification is retained separately. Final-head CI is running. Assignments3/6,
worker occupancy15/45 minutes conservatively, no active workers. No new features
or assignments planned. Target18:13:39 and hard stop18:43:39 remain unchanged.
Next: complete qualification, inspect final-head checks/threads, integrate only
if all acceptance gates pass, then checkpoint. No new human decision needed.

## 2026-10-14 18:01 UTC — Run 2 qualified integration and stopping checkpoint

WI-0003 qualified and staged via PR506, final PR head
`a42df73af45853b3e59b754c251ff6e8349687e0`, merged only into
`codex/gettenberg-pilot-20261014` as
`b2aa080a098b0fc938ac5e3ec71a5eb2e42c7a80` from base861458dd.
The original accepted WI-0002 merge3793d152 remains an ancestor. Final source
fc2b97bb independently reviewed and unchanged through integration; subsequent
changes are evidence/records only. Exact source hashes, final canonical/full
qualification and exact-head CI/review gates are centrally retained under
`evidence/gettenberg-pilot-run2-20261014/`. Full source:78937 records, zero
rejected/uncommitted,451.130s,69566464-byte peak RSS,2177388544-byte database;
all targets pass. All2619 canonical tests pass;30 focused catalog tests.

No active assignments. Three of six assignments used; conservative worker
occupancy15/45 minutes (5 storage +8 combined review +2 focused repair review).
Implementation/integration completed about47.5 minutes after17:13:39 start;
final checkpoint validation/push follows. Target18:13:39, hard18:43:39 were not
extended. Shared weekly usage33% at launch and40% at18:01:05 (+7 percentage
points), rounded account-wide observations, not attributable tokens/cost.
No human decision interruptions, no requested paid reviews, no credit resets.
Automatic repository reviews were allowed to finish and all findings addressed.

Zero Gutenberg network-download bytes; original cached archive is unchanged.
Private final candidate remains at
`/tmp/gettenberg-pilot-run2-20261014/qualified-final.sqlite`; earlier redundant
candidate removed after retaining its qualification evidence. No activation,
main promotion, publication, caller migration or canonical corpus changes.
Native WI stays proposed and execution records in_progress pending actual
human-approved main delivery. gutenbergpy remains required by existing callers.

WI-0004 through WI-0010 remain unattempted. Resumption requires a renewed
bounded grant, fetch/clean-state and instruction/gate checks, and ancestor
verification of b2aa080a plus its acceptance evidence. Next intended item is
WI-0004, recoverable generations and offline lifecycle: writer locking, atomic
activation, pinned readers and interruption tests. Its remote-acquisition
coordination belongs to WI-0005; do not silently expand scope or start it now.
No unresolved correctness findings or unreviewed source changes remain.

### Run 2 process findings for LRH

- Observation: one combined review plus two same-scope follow-ups covered the
  first implementation; automatic review later found a distinct error-contract
  gap and a third narrow assignment verified its repair in about one minute.
  Interpretation: follow-ups saved repeated context, but a cap must still count
  new scope honestly. Recommendation/test: persist assignment identity, reviewed
  SHA, remaining follow-ups and explicit new-assignment reasons in a run tree.
- Observation: full-catalog and canonical qualification succeeded twice; the
  second was repeated after source changed, with separate source hashes and
  results. Interpretation: successful bulk ingestion alone did not expose
  failure-category bugs. Recommendation/test: acceptance should include actual
  SQLite FULL/INTERRUPT and transaction accounting, not only happy-path counts.
- Observation: record links were populated in a separate push after PR creation,
  restarting CI; final measurement evidence was instead checkpointed after
  verified integration. Recommendation/test: native planning should distinguish
  source qualification from evidence-only finalization, while still requiring
  exact final PR-head CI and never relabeling old source evidence as new.
- Observation: about47.5 minutes reached integration using3 assignments/15
  conservative worker minutes versus the previous broader86-minute pilot.
  This is a differently scoped item, not a controlled speed/cost comparison.
  Recommendation/test: keep one-deliverable grants and record source coding,
  review, qualification, external-check waits and account-usage observations
  separately; do not infer efficiency from elapsed time or rounded usage alone.

## 2026-10-14 19:27:21 UTC — Run 3 started

Human renewed the bounded plan for WI-0004 only. Integration1bc04c29 matches
fetched origin; qualified WI-0003 b2aa080a ancestry verified. Acceptance mapping
and evidence are in its execution record and run2 evidence directory. Readiness
passes; exact prompt and slug checks find no previous WI-0004 execution. LRH
0.2.5.dev3596+gd86755f50; watched fingerprints fresh, existing skip consent
invalid; explicit charter adapter is authority, no policy changes. Python3.11.9,
SQLite3.46.0,lxml5.2.2 project environment verified. AGENTS/STYLE/tests guidance
read. Compatible lrh-implement traceability/validation steps reused; approved
charter supersedes repeated plan gates, main-base and closeout rules. No claim
that unchanged native execute/land was invoked. Prior-art check present in WI.

Start19:27:21, target/freeze20:27:21, hard stop20:57:21 UTC. Assignments0/6,
worker occupancy0/45 with15 review reserve. Shared weekly usage40%; attributable
per-run cost unavailable. Decision record: gettenberg-lifecycle-design.md.
Plan branch codex/gettenberg-lifecycle-0004; expected lifecycle module, bounded
filesystem/lock helpers, errors, real lifecycle tests, Diataxis how-to/reference
and evidence. Canonical format/lint/scripts/test/LRH/readiness/diff checks.
Main promotion remains a final recommendation only. Next: implement the recorded
contracts, independent review, qualify, internal PR and evidence checkpoint.

## 2026-10-14 19:37 UTC — Run 3 candidate entering independent review

Decision contract implemented; initial local tests found error-wrapper masking
of CatalogMissingError (also an OSError subclass), corrected without changing
contract. Initial test assertions were corrected to typed Title.value.text and
resolved macOS temp paths.18 lifecycle tests and25 I/O tests pass. Worker1 used
about4 minutes, conservatively5/45; no workers currently active. Assignment2
will review complete current diff, including new files, against3de743cd. Review
reserve remains15 minutes; assignments2/6 including upcoming review. No source
edits during review except verified requested repairs. Target20:27:21 and hard
stop20:57:21 unchanged. Full canonical/source qualification follows stable
reviewed source under approved pilot adapter, not repeated exploratory reruns.

## 2026-10-14 19:42 UTC — Run 3 minute15 checkpoint and review repairs

Initial review380f7c41 found two P2s: atomic pointer replacement conflicted with
strict pathname identity checks; implicit retained-source rebuild failed to bind
copied bytes to the prior manifest hash. Coordinator directly reproduced both:
998 successful opens plus2 failures during400 real public-API activations, and
same-size replacement source silently activating a different title/SHA.
Repairff072c13 gives JSON readers opened-file snapshot semantics while retaining
strict archive/hash identity checks, and binds implicit rebuild to expected
archive SHA/size.187 gettenberg tests pass, including deterministic filesystem
boundary regressions. Source is frozen pending assignment2 repair/recheck1.

Assignments2/6, worker1 conservatively5 minutes; reviewer dispatched19:37:39,
active with hard assignment deadline19:53. Run target/freeze20:27:21 and hard
stop20:57:21 unchanged. Shared usage42% observed19:37:39 (launch40%). No design
replan or new scope. Qualification helper prepared; full-source/canonical
qualification waits for stable independently cleared source. No network calls,
main promotion, native closeout or WI-0005 work.

## 2026-10-14 19:43 UTC — Run 3 stable source qualified for final checks

Independent recheck cleared ff072c13 at19:42:29.187 gettenberg tests pass;
real400-activation concurrency probe produced998 successful opens and zero
errors. Retained-source substitution now fails before build/activation and
in-place JSON changes still fail. Review record retains original findings and
coordinator reproduction evidence. Assignments2/6, worker occupancy11/45
conservatively (5 I/O +6 review), no active agents. About16 elapsed minutes;
original target/freeze20:27:21 and stop20:57:21 unchanged. No new scope planned.
Next: canonical suite and actual cached full-archive setup/activation/reuse
qualification in a new private cache, then exact-head internal PR checks.

## 2026-10-14 20:09 UTC — Run 3 execution-gap observation

UTC advanced from the19:43 qualification-preparation checkpoint to20:08:33 at
the next observed clock. Host process/file evidence shows actual validation
jobs started about20:08:10 (full-source log birth20:08:09.680; canonical tests
log birth20:08:13.761). At20:08:54 the full build had11008 committed records;
process inspection shortly afterward showed about58 seconds elapsed and55 CPU
seconds for qualification, consistent with active progress rather than a stuck
24-minute build. Cause of the preceding gap is unknown; do not attribute it to
code, sleep or tooling without evidence. Both clocks agree at20:09. No deadline
or budget reset. The delayed usage observation is44% shared weekly, launch40%.

Canonical/full-source processes are running on8bccd4c4, whose implementation
matches independently reviewed ff072c13. Assignments2/6,11 worker minutes, no
active agents. Target20:27:21/hard stop20:57:21 unchanged. Remaining work is
qualification, PR/automatic review/CI, bounded repairs if needed, integration
and checkpoint. No new item. Minute45 reassessment remains20:12:21.

## 2026-10-14 20:14 UTC — Run 3 minute45 reassessment

Checkpoint observed about2 minutes after the planned20:12:21 reassessment.
PR507 targets integration3de743cd; initial heada96f7559. Canonical2665 tests,
format/lint, readiness and LRH validation pass. All four initial-head CI checks
pass; automatic Codex review remains running. Full cached-source qualification
started20:08:10 and is still running within its900-second process ceiling.
No implementation change since independently reviewed ff072c13. Records linked
to PR507 in this checkpoint; its resulting head must receive fresh CI.

Assignments2/6, conservative worker occupancy11/45, no active agents. Scope
unchanged. Continue qualification and review toward target20:27:21; hard stop
20:57:21 unchanged. No new item or main promotion. If qualification or review
fails, apply only verified bounded repairs or preserve a resumable checkpoint.

## 2026-10-14 20:20 UTC — Run 3 hosted repair checkpoint

Full-source lifecycle qualification at8bccd4c4 passed:78937 ebooks/sources/members,
2018879 resources,109170 contributions,223 diagnostics; setup453.153 seconds,
reuse0.004 seconds, peak79757312 bytes, zero network. Preserve original evidence
and source hashes; do not relabel its timing as later repaired-head evidence.

Hosted review found missing parent-directory fsync. Coordinator verified and
fixed744076ba, with fresh nested-cache/retry tests. Assignment3 independently
cleared that repair:23 tests plus concurrent first setup and read-only probes.
Canonical2667 tests also passed; existing full-catalog reuse/activation and full
hash/integrity/accounting verification passed23.078 seconds at744076ba.

Copilot then identified retained-source rejection leaving an orphan archive and
candidate-manifest sync failure falsely reporting possible activation. Coordinator
reproduced both (one orphan; published=True with unchanged active pointer), then
fixed6b163fc4: identity check before archive publication and candidate-specific
error translation.190 focused tests pass. Assignment4 independently reviews
these new fixes; expanded scope consumes another assignment rather than silently
extending assignment3. Assignments4/6; completed workers14/45 conservative
minutes, assignment4 active with deadline20:26. Shared usage47% (launch40%).
Target/freeze20:27:21, hard stop20:57:21 unchanged; only repairs and qualification
remain. Automatic first reviews completed; no paid retrigger requested.

## 2026-10-14 20:23 UTC — Run 3 final source qualified

Assignment4 found adjacent recovery P2: activate did not repeat a failed
candidate-directory sync. Coordinator confirmed with real filesystem probe and
fixed2e868578; repair/recheck1 cleared that exact source, including failure
preserving old active/candidate and successful retry. No remaining scoped P0-P2.
All workers done:4/6 assignments,17/45 conservative worker minutes. No new scope.

Final2668 canonical tests pass in64.618 seconds,190 gettenberg tests; format,
lint, readiness and LRH pass (0 errors,351 existing warnings). Full-catalog
verification/reactivation on final source passes in22.053 seconds without network.
qualification-map.json separates original bulk-import evidence from repaired-head
boundary/full-catalog evidence; unchanged bulk components verified by source hash.
Next push evidence/repairs, verify all four exact-head CI checks and resolve only
verified fixed review threads; integrate only into pilot branch. Target20:27:21
and hard stop20:57:21 unchanged. Promotion recommendation follows checkpoint.

## 2026-10-14 20:27 UTC — Run 3 integrated checkpoint and reassessment

PR507 merged only into codex/gettenberg-pilot-20261014 as1ea08da3, confirmed by
20:26:41 (59m20s after launch). Exact candidatef061633b passed test(push),
test(PR), coverage and lint; all three hosted review threads resolved after
independently verified repairs. Integration/source equivalence verified.
Evidence: gettenberg-pilot-run3-20261014/integration.json and qualification-map.json.
Working source is frozen; checkpoint bookkeeping/automatic branch checks only.
Original60-minute target and90-minute hard stop never changed. No new scope.

Four of six assignments,17 of45 conservative worker minutes, no active workers.
Shared weekly usage40% launch to48% checkpoint; account-wide rounded observation,
not attributable run cost. No numeric usage stop threshold was agreed. Canonical
2668 tests and final-source190 focused tests pass; format/lint/LRH/readiness pass.
No bulk network; canonical corpus untouched. Unexplained19:43–20:08 execution gap
remains explicitly unattributed, so do not infer speed/cost efficiency from this
single run. Five relevant correctness issues were independently raised across
local/hosted reviews (two pre-push, three hosted), plus one adjacent recovery
finding during repair review; all resolved before integration.

Recommend earlier human-reviewed main promotion for the offline foundation
(WI-0001 through WI-0004), before acquisition WI-0005. This is the charter's
review-size exception: relative to fetched main5cfd2d71,26 code/test/doc files
add8024 lines including fixtures, and a coherent local catalog lifecycle boundary
is now qualified. Main remains unchanged; no promotion PR or native closeout was
performed. WI-0005 onward and the actual gutenbergpy dependency removal remain
unattempted. No later run is granted by this checkpoint.

Process observations and candidate LRH improvements:

- Expanded assignment capacity allowed two distinct hosted-repair reviews without
  a new human gate; reuse of a reviewer was still counted as a new assignment for
  expanded scope. Keep identity/scope/deadline/followup accounting separate.
  Acceptance test: scope expansion consumes a slot; same-scope repair does not
  reset its deadline; occupancy includes waits and totals remain observable.
- Directory durability needed failure/retry coverage beyond process-death tests.
  Add a publication-boundary matrix to filesystem review packets: file contents,
  directory entries, containing hierarchy, recovery retries and error commit
  semantics. Acceptance test: injected sync failures never produce misleading
  activation claims, and recovery retries the necessary barrier before success.
- Repeating full ingestion after capture/durability-only repairs would add avoidable
  delay. Keep exact source hashes and a reviewer-approved affected-check map.
  Acceptance test: unchanged parser/store/import hashes retain original evidence;
  changed boundary tests and final full-catalog verification run, with old timing
  never relabeled as final-head timing.
- The unexplained execution gap and delayed minute45 observation motivate a host
  watchdog/elapsed-deadline reminder rather than reliance on agent recollection.
  Acceptance test: injected suspension preserves absolute deadlines and reports
  last completed action plus pending qualification, without silently renewing.

## 2026-10-14 20:46 UTC — Human milestone preparation

Human requested presentation of the offline-foundation milestone and a runlog
record. Run3 remains finished; this is separately requested presentation work,
not a grant renewal or main-merge approval. Verified clean pushed checkpoint
6970d504, main5cfd2d71 ancestor, and no duplicate open promotion PR. Created fixed
branch codex/gettenberg-offline-milestone so future pilot work cannot silently
enlarge this review. No implementation, dependency, CI or corpus changes made.

Prepared gettenberg-offline-milestone.md: scope/evidence for WI-0001 through0004,
review-size justification, operating limits, remaining replacement work, human
main gate and closeout procedure. Generated closeout-map.json by primary/side
record relationships:4 WIs,15 records,4 internal PRs; verified each integrated
commit is an ancestor. Preserved native statuses and original PR attribution.
Promotion execution record2026_10_14_20_45_26_GETTENBERG_OFFLINE_MILESTONE tracks
this separate operation. Next: presentation checks, main-target review PR,
record its URL and report the concrete human decision with current gate status.

## 2026-10-14 20:48 UTC — Human milestone PR opened

Opened https://github.com/xenotaur/LCATS/pull/508 against main from fixed branch
codex/gettenberg-offline-milestone, initial head11499215. Attached it to this
chat and linked the promotion record, review packet and closeout map. Main is
unchanged. Required current-head CI and automatic first reviews are pending;
no manual hosted retrigger or new worker assignment was requested.

Presentation format/lint/diff checks pass; all13 local packet links resolve;
LRH reports0 errors/351 existing warnings. Verified no src/tests/docs/package
change from qualified6970d504. Existing2668-test evidence remains source-valid;
main-target CI runs afresh. Human decision is partial promotion of WI-0001–0004
with documented limits, followed by accurate closeout after actual merge. It
does not approve WI-0005 execution or claim the dependency replacement complete.

## 2026-10-14 23:25 UTC — Human review: code placement and rendered examples

Human reviewed PR508 and requested discussion/decision on repository placement,
better helper commentary and verified rich Markdown rendering before repair and
landing. Investigation only; layout choice remains pending human decision.

Confirmed competing guidance: experiments/README.md:31–33 places experiment
scripts/results together and reusable code in lcats/src/lcats, while canonical
lcats/STYLE.md:91 says no code in experiments. Its package-path diagram also
predates src/lcats. project/README.md calls project the planning/memory layer
but lacks an explicit executable-code prohibition. Current inventory finds
exactly five Python files under project/, all introduced by this gettenberg
pilot. Default scripts/format and scripts/lint cover src/tests/tools only;
passing those checks did not qualify formatting of the evidence helpers.

Rendered the actual lifecycle how-to through GitHub's Markdown API, and rendered
a temporary fenced variant without changing tracked documentation. Original:
9 nested blockquotes and1 code block; fenced variant:0 blockquotes and4 code
blocks. The >>> prompts are parsed as quote markers outside fences. The API
emits some explicit line breaks, so this does not claim reproduction of the
reviewer's exact overlapping-rich-diff appearance. All13 doctest examples in
the temporary pycon-fenced variant passed with real temporary fixture caches.

Recommendation for discussion: retain documentation/data-only project control
plane, temporary work under lcats/experimental, durable qualification scripts
and measured results under a numbered experiments entry, reusable/domain logic
under tested src/lcats. Keep planning/CI/review/usage evidence in project;
move archival technical measurements with reproducing scripts, preserve bytes
and original source attribution, and update current links with a relocation map.
Do not promote legacy snapshot-specific probes into the distributed package.

PR508 current head00327640 has four passing CI checks, but review is not clear:
there are outstanding bot reports on surrogate-escaped manifest paths,
optimization disabling qualification asserts, and relative candidate URI paths,
in addition to human documentation/layout comments. Verify and resolve these
in the eventual repair scope; moves/comments alone are insufficient. Document
all retained helpers' purpose, invocation, inputs/outputs, bounds, side effects,
platform assumptions and failure semantics, and explicitly format/lint/test them.
No convention was adopted and no implementation or main merge occurred in this
investigation. The next action is the human layout/repair decision.

## 2026-10-14 23:46 UTC — Approved convention and repair implementation

Human approved the proposed four-way convention and repair plan and said proceed.
This covers repair/stabilization/landing of508, not a new bounded implementation
run. Reused LRH review-response/landing procedures under explicit task authority;
no persistent consent changes. Gate definitions fresh; skip consent remains invalid.

Root agent guidance and canonical STYLE now agree: documentation/data-only
project, experimental prototypes, archival experiment code/results, tested reusable
library. Corrected stale package path and contradictory no-code-in-experiments
rule. Five runners and nine measurement files moved to experiment10; original
measurement bytes/hashes preserved, relocation map added, current links updated,
historical execution/runlog/measurement identities retained. Runners have named
CLI arguments, import-safe main entry points, usage and algorithm comments.

All seven review comments are in scope: fenced pycon fixes rendered quote parsing;
experiment README explains repeated predicate URI diagnostics; explicit lifecycle
checks survive -O; candidate paths resolve before URI conversion. Non-UTF-8 path
preflight prevents expensive late failure. Initial all-ASCII JSON change violated
two existing tests and was discarded in favor of early input rejection; strict
JSON behavior retained. Mac byte-filename creation itself fails, so regression
checks the portable early boundary without depending on filesystem support.
Next: focused/canonical checks, independent review, CI and authorized main closeout.

## 2026-10-14 23:48 UTC — Repair validation passed

All 2,675 canonical tests passed in 72 seconds; all 197 gettenberg tests passed.
Canonical formatting/lint and explicit experiment formatting/lint passed, as did
LRH validation (0 errors, 351 existing warnings), diff hygiene, nine original
measurement SHA256 checks and 24 current local links. Log hashes are retained in
milestone repair-validation.json; full logs are local temporary artifacts.
No full-source measurement was repeated or relabelled. All seven original
review threads have concrete repairs or documented answers; final classification,
current-head CI and independent PR review precede the authorized main merge.

## 2026-10-14 23:53 UTC — Independent review caught a helper regression

One cold-context PR review found a P2 in the relocated parser probe: header
cleanup was accidentally outside the member loop. Parent inspection verified
the regression against the original helper. Restored per-member clearing and
added a real long-name archive retained-memory test (20 versus 600 members).
The test fails on a temporary copy of the old loop and passes on the repair.
Peak RSS was unsuitable for this regression because transient bz2 expansion
masked retention; the final check samples live Python allocations at the last
parsed record. Seven original GitHub threads are resolved. No other independent
review finding was verified. New canonical checks and a fresh current-head
review follow before the authorized landing.

Follow-up canonical validation: 2,676 tests pass in 71 seconds; 198 gettenberg
tests pass. Canonical/experiment formatting and lint pass; LRH reports 0 errors
and 351 existing warnings. Evidence log hashes are in repair-validation.json.

## 2026-10-14 23:58 UTC — Main promotion and partial closeout

PR #508 merged as 35f80fb53c1820ff70708df0ab049266f25dc3c7, from exact reviewed head
12fa03be342e2d0f98ba584efd925c1e52e9cad5. Four current-head CI checks passed,
all seven GitHub threads were resolved, and the second independent review
reported no findings. Parent verification confirmed per-member header release
and the real-archive regression. Two independent review assignments were used;
the first surfaced one repaired P2, the second verified the final source.

Native closeout marks 21 execution records landed (15 original and six promotion/
review/closeout records) and moves WI-0001 through WI-0004 to resolved. Original
record bodies and internal PR attribution were verified unchanged. Current
navigation and the closeout map were updated. WS-GETTENBERG, the redesign and
release/dependency-removal gates remain open; no new implementation grant began.

Process lesson: encode placement rules in human and agent guidance before large
runs. Default package checks omit experiment scripts, so explicitly validate
archival runners. Preserve measured bytes and source identity during relocation;
review helper control flow as carefully as product code. These lessons are
already captured in repository guidance and this log; no separate memory needed.

Closeout validation: LRH reports 0 errors and 351 existing warnings; diff hygiene
passes. Native closeout-sync completed, mirroring 20 local Claude archive files,
harvesting no exports and reconciling no child aliases. This does not export this
Codex session; its durable pointer is retained. No raw transcripts were committed.
No separate memory was written because the durable lessons are already in the
committed guidance and runlog. Only control-plane files change after the reviewed
main merge; product code, tests, docs and archival measurements remain identical.

## 2026-10-15 00:07 UTC — Short acquisition planning grant

Human explicitly approved a 15-minute sprint. Run gettenberg-20261015-plan starts
00:07:30, content freeze 00:17:30, hard stop 00:22:30 UTC. One coordinator, zero
worker assignments; no implementation, data downloads or main promotion. Branch
codex/gettenberg-acquisition starts at fetched main 2f14e4e8. Native WI-0005
readiness passes with no warnings; WI-0002 and WI-0004 are canonically resolved.
LRH 0.2.5.dev3596+gd86755f50 is available; installed gate definitions are fresh,
skip consent remains invalid, and this explicit grant supplies task authority.
No skill file was invoked or changed for this planning-only grant; applicable
charter, AGENTS and STYLE were read. Native prompt/readiness/validation commands
are used directly. Selected session model identity is not exposed by these tools;
no model change or delegated model call was made.

Python 3.11.9 is available in the LCATS environment. Initial import inspection
revealed its editable install points to the sibling LCATS clone; absolute
PYTHONPATH bound it to the managed worktree and the resolved import was verified.
No environment repair/install was needed. Account-wide weekly usage at launch
was 55%; per-run tokens/cost are unavailable and concurrent-session usage cannot
be attributed to this sprint.

## 2026-10-15 00:13 UTC — Acquisition decisions and handoff

Inspected actual Resource/lifecycle/legacy-cache/downloader boundaries and
primary HTTP/Python/Gutenberg access documentation. Recorded the acquisition
contract and 22 acceptance scenarios. Important boundaries: explicit online
permission, no requests on valid cache hits, separate refresh, immutable raw-body
receipts, no network within CatalogManager, strict separately versioned decoding,
and one cache-root request coordinator. Concrete mirror route qualification and
cooperative timeout semantics are explicit implementation preflight tasks.
No live source data was downloaded. No claim of implementation or independent
review is made. Next: self-check contract consistency, validate documentation and
native readiness, commit a resumable planning checkpoint before the hard stop.

## 2026-10-15 00:15 UTC — Planning validation checkpoint

Canonical format/lint pass; LRH reports 0 errors and 351 existing warnings.
WI-0005 readiness is clean. Verified 18 current local links/line anchors,
fence balance and dependency ancestry. Product code/tests/docs and experimental
measurements are unchanged; no unit-test rerun or implementation acceptance claim.
The execution record and validation.json capture this planning-only scope.
Single-agent self-check clarified retry/redirect budgets, corrupt-state recovery
boundaries and conflicting encoding declarations. Independent implementation
review remains required in the next grant. Next: commit/push a planning checkpoint
and report its exact identity with remaining scope.
