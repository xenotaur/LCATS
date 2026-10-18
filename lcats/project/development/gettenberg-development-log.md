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

## 2026-10-15 00:16 UTC — Short sprint completion checkpoint

Planning commit ceeeb8449eb2e6fe347af04cf1b6240b0342b246 is pushed to
codex/gettenberg-acquisition. Design and 22-scenario handoff are complete within
the grant; only recording this checkpoint and verifying its push remain. No PR,
main merge, implementation, data download or worker assignment was started.
Native WI/record status remains nonterminal pending reviewed delivery to main.
Account-wide weekly usage reads 57% versus 55% at launch; this is not an isolated
sprint cost measurement. No model upgrade or external paid model call occurred.

Resume after the move with a new bounded WI-0005 implementation grant. Start from
this branch, reconcile freshly fetched main, verify absolute PYTHONPATH, and use
gettenberg-acquisition-design.md. The two explicit qualification tasks are the
default route mapping and transport timeout semantics. The sprint required no
human intervention after activation. Observation: a narrow planning-only grant
produced a resumable contract without implementation/review/CI wait overhead;
its impact on the next run remains unmeasured. No work continues automatically.

## 2026-10-15 00:23 UTC — Routing sprint activation

Human approved the proposed routing qualification sprint. Start 00:23:20,
seven-minute target 00:30:20, ten-minute hard stop 00:33:20. Single coordinator,
no assignments or production changes. Clean acquisition branch starts a528ebfd;
fetched main remains 2f14e4e8. The sandboxed LRH idempotence query could not reach
GitHub; the authorized network retry succeeded and found no prior execution.
Native AD_HOC record created. No persistent consent changes.

## 2026-10-15 00:26 UTC — Route evidence and limits

Official mirror/catalog listings establish endpoint candidates and an exact RDF
archive link. Seven local RDF fixtures contain 113 resource nodes (65 ebooks
aliases, 27 files paths, 21 cache paths). Added a nine-case input/output table,
separating documented structure, inferred files-path conversion and unresolved
ebooks aliases. Alias prevalence exposes a selection/planning interface detail:
account for route capability offline, without request-based fallback or assumed
byte equivalence. A22 remains open; the full format scope is unchanged.

A single mirror root-index read timed out; a historical upstream mailing-list
page could not be retrieved. Neither is treated as a proven service failure or
conclusive mapping evidence. No ebook/archive bodies were requested. Lesson:
short qualification grants can reveal a material hidden coverage assumption
before implementation; retaining explicit uncertainty is useful output. Proposed
LRH acceptance check: a route qualification record distinguishes source facts,
inference, unsupported cases and live verification rather than one green flag.

## 2026-10-15 00:27 UTC — Routing validation and checkpoint

Nine-case handoff and hashed fixture inventory complete. Canonical format/lint
pass; LRH 0 errors and 351 existing warnings. Local links/line bounds and fence
checks pass. Product code/tests and historical measurements are unchanged; unit
tests were not rerun. No independent implementation review is claimed. A22 remains
open, with concrete upstream-alias, selection and operational checks recorded.
Proceeding only to commit/push and verify the clean checkpoint, then stop within
the short grant. No intervention was needed after activation. Next implementation
requires a separate grant; all WI-0005 acceptance obligations remain intact.

## 2026-10-15 00:27 UTC — Routing sprint completion

Routing checkpoint 05b68cba3e8b9b75084bf2d71ac6ad2c7b423ea6 was committed
and pushed; branch status was clean and synchronized. Finishing early after
approximately four minutes of the seven-minute target. This final log correction
uses the observed UTC clock and records the pushed checkpoint; no further domain
work continues. The handoff remains staged, not promoted to main. The execution
record remains nonterminal under the charter. No per-run cost estimate is claimed.

## 2026-10-15 00:59 UTC — Acquisition core run activation

Human approved the 60-minute target / 75-minute hard-stop plan. Run starts
00:59:27, freeze by 01:44:27, target 01:59:27, hard stop 02:14:27 UTC. Base
bd2998a8, freshly fetched main 2f14e4e8; WI-0002/0004 canonically resolved,
WI-0005 readiness clean and prior-art check present. Native prompt:
PROMPT(WI-GETTENBERG-0005:WI_GETTENBERG_0005_ACQUISITION_CORE)[2026-10-15T01:00:16+00:00].
No prior execution for this tranche slug. lrh-implement and its references read;
charter adapter replaces repeated per-item confirmation and main branching.
Gate definitions fresh, stored skip consent invalid; explicit human grant applies.
No policy changes. Python 3.11.9, Black 25.11.0, Ruff 0.15.0; absolute PYTHONPATH
verified against managed worktree. Shared weekly usage 58%; per-run cost unknown.
The editable distribution reports an older version, so source SHA/import path,
not installed package version, identifies this run. No package reinstall.

## 2026-10-15 01:03 UTC — Core tranche decision before implementation

Implement explicit-URL original-byte acquisition: typed request/policy/errors,
read-only plan, bounded streaming GET, per-cache serialization/pacing, retry and
redirect policy, immutable hash-verified body/receipt publication and offline
reuse. Archives share lifecycle's retained archive namespace. Defer conditional
refresh, decoding, catalog receipt ingestion and automatic Gutenberg resource
mapping/selection to later WI-0005 tranches; full WI acceptance remains open.
A caller-supplied permitted concrete URL is sufficient to test this independent
transport/cache boundary; no unqualified mirror becomes a built-in default.

Read upstream gutenbergsite at 407d5ef950923046fa86aadad57036dfdf5faafc and
autocat3 at f33e7105cc1113e86a9244f127f43633cc196bb2 in temporary checkouts.
The harvest implementation uses database filenames; HTMLFormatter.py:86–87
substitutes generated aliases. Neither inspected path establishes an invertible
alias-to-filename rule. No upstream implementation is copied. Preserve A22's
remaining qualification rather than guessing suffixes. This is a scope boundary,
not a reduction of the final all-format requirement.

API choices: SourceRequest keeps source URI and explicit request URL; NetworkPolicy
is offline by default and requires explicit allowed origins. GET representation
is fixed (identity Content-Encoding request, no cookies/auth/proxies). Cache keys
include storage kind as well as canonical URL and representation version, so the
same URL requested as archive/resource cannot collide across storage namespaces.
Reuse private lifecycle I/O through an error-translating resource adapter, without
changing catalog behavior. Persistent SQLite lock plus atomically persisted pacing
state; no lock on cache hits/plans. Deadlines are cooperative between bounded I/O
operations, not hard DNS cancellation. Independent review receives these limits.

## 2026-10-15 01:16 UTC — Acquisition core initial qualification

Explicit-URL core and Diataxis docs implemented. 48 focused tests pass, including
real-process duplicate suppression and killed lock recovery, HTTP framing/redirect/
retry boundaries, corruption/no-clobber publication and clock discontinuities.
Initial test failure was a macOS /var versus /private/var path assertion; resolving
the temporary root corrected the assertion. No product regression was hidden.
The format wrapper with empty flags hits an existing Bash empty-array nounset
issue; supported --quiet/--check flags work. No unrelated wrapper fix is included.

Full canonical suite is running before independent review. No agent assignment
has been used yet. Feature work is frozen for this tranche now, ahead of the
minute-45 ceiling; next work is review, validation and bounded repairs. Shared
usage extraction at this point was unavailable; no cost estimate is inferred.
The one planned cold review will use a compact specification and exact source
snapshot, not full session history. No additional item is starting.

## 2026-10-15 01:20 UTC — Checkpoint and independent review dispatch

At the 20-minute checkpoint scope remains the acquisition core; no extra feature
or item has been added. Initial full suite passed 2724 tests, then 2727 after
malformed-input/documentation regressions. Focused snapshot now passes 52 tests;
one additional Retry-After obsolete-date repair is undergoing final full-suite
qualification. Fail-first numeric-overflow regression demonstrated an untyped
OverflowError from corrupt pacing JSON; corrected to ResourceIntegrityError.
The how-to's three code blocks execute against a local fixture in the test suite.

Independent cold-context assignment 1, acquisition_core_review, dispatched
01:20:28 UTC; deadline 01:35:30 (15 minutes), no recursive delegation or writes.
Source/test/doc files frozen at /tmp review-files.json hashes; full diff snapshot
SHA256 1c539ec207fd28fd6457741cc3bc88e500595f490ad8cec9fe70d412ac57e801.
Native source HEAD bd2998a8 with uncommitted reviewed changes. Canonical full-suite
recheck runs alongside report-only review; integration waits for both. This small
sequencing adaptation keeps checks independent without idle elapsed time.
Weekly shared usage 60% versus 58% at launch, not attributable per-run cost.
Remaining wall allowance approximately 54 minutes; review occupancy allowance
15 minutes assigned out of 45 cumulative. No implementation worker was needed.


## 2026-10-15 01:29 UTC — Review findings and bounded repairs

Independent assignment 1 returned four verified P2 findings around 01:25 UTC:
trickling headers/chunk framing could exceed the deadline; post-reference hard-link
cleanup changed ctime during concurrent verification; unsupported transfer coding
could enter cached originals; pacing fsync errors incorrectly claimed resource
publication. Coordinator directly read and ran the top reproduction before fixing:
0.2-second budgets took 1.313/1.317 seconds for header/chunk trickles. The same
probe reproduced the cleanup/error-translation cases. Findings were accepted on
reproduction, not reviewer assertion. Frozen initial snapshot full suite passed
2728 tests; statement coverage of the four new modules was 95%, which did not
substitute for adversarial review and missed these behavioral defects.

Repairs add a deadline-aware raw socket reader below HTTP framing; finish hard-link
cleanup before reference visibility; reject unsupported/ambiguous transfer coding;
and translate possible-publication errors only at reference replacement. New local
regressions cover headers, chunk extensions/trailers, supported/unsupported framing,
a deterministic real publisher/reader overlap and pacing durability injection.
Coordinator also reproduced a huge finite socket timeout overflow and resource
warning; policy now bounds I/O timeouts at one day before socket creation. Pacing
metadata capacity conservatively collapses pending origins to the latest global
cooldown instead of losing a new Retry-After. Both have regression tests.

58 focused tests pass with ResourceWarning promoted to error. Same-assignment
repair recheck 1 dispatched 01:28:35, deadline 01:38:30; current seven-file hashes
frozen in review-files-repaired.json. Initial review occupancy approximately five
minutes; this recheck has ten minutes maximum. No second worker or new feature
assignment. Canonical full-suite/format/lint requalification runs in parallel with
report-only recheck. Primary and native AD_HOC _SELFREVIEW records remain nonterminal.

Process observation: a single compact cold review found substantive issues despite
broad unit coverage. Reserve real time for repairs and behavior-level probes; a
coverage percentage alone would have supported a false completion claim. Added
regressions belong in tests/, temporary probes stay outside the control plane.


## 2026-10-15 01:32 UTC — Scoped qualification complete before PR

Independent repair recheck completed 01:30:17 UTC, all four findings resolved and
no additional actionable regressions. Exact seven-file hashes match the repaired
snapshot. Reviewer verified real local HTTPS as well as HTTP framing, pacing
failure and concurrent publication. Coordinator full canonical suite passes 2734
tests in 76.017 seconds; 58 focused tests, format/lint, LRH and readiness pass.
One assignment with one recheck used less than seven cumulative worker minutes
(conservative initial completion bound 01:25:40). No additional assignment needed.
Shared weekly usage observed 63% at minute30; account-wide, not per-run attribution.

qualification.json and review.md preserve source hashes, commands, log hashes,
accepted repairs and the partial A01–A22 mapping. Native WI is not resolved. Next:
commit/push child PR targeting acquisition integration branch; inspect first
hosted review and exact-head CI before any internal merge. Main remains untouched.


## 2026-10-15 01:34 UTC — Internal PR opened

Implementation commit 7a00da1c1d78b481811b1803652606840da604eb pushed;
[PR #510](https://github.com/xenotaur/LCATS/pull/510) targets
codex/gettenberg-acquisition at bd2998a8, not main. First automatic Codex review
is running; test, coverage and lint checks are running. No manual retrigger.
Backfill the PR link in both native execution records, keeping status in_progress.
This bookkeeping-only follow-up preserves every reviewed product/test/doc hash;
CI must qualify the resulting exact head before internal integration.


## 2026-10-15 01:40 UTC — Minute-40 checkpoint and hosted review repair

Current pushed head bac92db3, base bd2998a8; first hosted Codex review at source
commit 7a00da1c found one P2: local temporary-file/publish OSError was caught by
the network retry handler. The finding is present on current source, valid and
feasible within scope. A filesystem TimeoutError/ConnectionError could cause
another GET. No CI failure or main promotion; all current-head checks passed
before this new repair, which invalidates their source qualification.

lrh-review-response loaded with its references; the charter's explicit bounded
repair authority supplies the coordinator confirmation, not fabricated human
approval. Identity matches PR #510. Slug/prompt checks found no previous response.
Native response prompt minted 01:38:16 and linked record created 01:40:13. Primary
provenance is the explicitly authored WI-0005 acquisition-core execution; the
SELFREVIEW sibling is not selected as primary. No comments skipped.

Fail-first regression covers local open/write/flush/fsync/close/publish with
OSError, TimeoutError and ConnectionError (18 cases): 6 errors/12 failures before
repair. Translate only local filesystem calls before they reach the network
handler, leaving HTTP reads as network operations. 59 focused tests now pass with
resource warnings enabled. Canonical format/lint/full-suite rerun underway.
Same-assignment recheck 2 (final allowed) dispatched 01:39:50, deadline 01:48:30,
no new scope or worker. Source snapshot review-files-hosted-fix.json frozen.

At minute40, feature work remains frozen and this is one bounded review repair.
Approximately20 minutes to target /35 to hard stop remain; if qualification cannot
finish, preserve the open PR without integration. The first hosted review was not
skipped or manually retriggered. Pending findings are not treated as acceptance.


## 2026-10-15 01:45 UTC — Cross-boundary review adjustment

First automatic Copilot review supplied three additional actionable findings:
shared archive publication could race catalog retention across hard-link cleanup;
slow pacing persistence could consume the next-start interval before GET dispatch;
permanent HTTPException subclasses were retried. All were directly reproduced by
new fail-first local regressions: catalog Source-changed error with unchanged
bytes, zero-second dispatch gap after a three-second save, and three GETs for a
malformed status line. No findings were waived. First Codex local-I/O repair had
already passed independent recheck and full suite (2735), but new fixes require
fresh qualification. This is additional boundary coverage from the first hosted
round, not evidence that the previously repaired cases regressed.

Coordinator replan within the approved scope: introduce a shared archive-publication
leaf lock in the existing lifecycle I/O module, used by both catalog retention and
resource publication through temporary-link cleanup. Keep strict inode stability
checks; do not weaken mutation detection or hold both resource and catalog outer
locks. Resource-network or catalog-writer → archive-publication is the order;
never reverse it. Lock waits are bounded and cache hits remain lock-free. This
small lifecycle adaptation is necessary to satisfy the already-required shared
archive namespace, and is explicitly reflected in design/reference docs.

Pacing now persists an in-flight marker before dispatch and renews spacing after
each attempt. A killed holder's uncertain dispatch time incurs a fresh conservative
interval; slow writes cannot shorten actual starts. Retry classification excludes
malformed status/header protocol errors. All 261 gettenberg tests pass, including
existing lifecycle tests and the new cross-publisher/slow-save/protocol cases.

The original independent assignment has used both permitted same-scope rechecks
and is complete. A second explicit, cold-context boundary-review assignment was
dispatched around01:45, deadline01:54:30, reviewing all hosted repairs and the
lifecycle interface adjustment. This is assignment2 of6, not a third follow-up
hidden under assignment1; cumulative occupancy remains below45minutes. Canonical
full qualification runs concurrently; product/docs frozen at the 11-file boundary
snapshot. No new feature work, main promotion or acceptance waiver. If review/CI
cannot finish by the hard stop, leave an open, clearly unaccepted PR checkpoint.


## 2026-10-15 01:54 UTC — Final boundary repairs qualified

Second independent reviewer reproduced post-publication pacing reporting, failed
archive publication cleanup, killed-publisher linked-orphan cleanup and later
cleanup racing post-retention catalog verification. Coordinator directly ran both
archive probes before repairs and after; final probes show expected acquisition
failure with successful concurrent catalog verification, and offline reuse with
linked orphans preserved. Completion-pacing failure now reports published=True;
pre-publication pacing failure remains an integrity error. Cleanup-stat errors
cannot mask the primary failure. All fixes have permanent boundary regressions.

Archive cleanup is now deliberately conservative: cleanup in the original shared
leaf-lock section removes temporary links; later cleanup preserves nlink>1 because
readers may already be verifying the published inode without that lock. Strict
mutation detection is retained. This is a documented recovery tradeoff, not silent
orphan deletion or an acceptance waiver. A new fault-test initially omitted its
patch context and failed its own injection assertion; the harness was corrected,
not the product behavior or specification.

Final reviewer signal01:52:34 clean across11 hashes;68 resource/50 lifecycle tests.
Coordinator full canonical suite passes2744 in74.632s; format/lint pass.
Two assignments total; original reviewer with two rechecks used under9minutes,
second assignment under8minutes, total under17 of45. No further delegation.
Shared weekly usage68% near minute53 versus58% launch; account-wide, not per-run
cost. The pre-second-assignment usage read was missed and taken afterward; record
this process miss rather than claiming a timely checkpoint. No numerical usage
stop threshold was agreed. Next is one repair push, current-head CI and thread
verification; no feature work or main promotion.


## 2026-10-15 01:58 UTC — Qualified internal integration and run stop

[PR #510](https://github.com/xenotaur/LCATS/pull/510) merged at01:58:01 UTC into
codex/gettenberg-acquisition, merge735961f15066f1ead2755faf77c97b07f244db5f.
Verified head7649979714fdb7d6904908f11bb082a0cc54d07a/basebd2998a8,
all four hosted checks (lint,coverage,two test runs) successful and all four first-round
review threads resolved before coordinator merge. Both hosted reviewers were observed;
no manual retrigger. All11 independently reviewed file hashes match the integrated
tree. 80 local doc links and Markdown fence pairing pass; no executable control-plane
files. Main remains2f14e4e8. No branch deletion, package publishing or bulk data download.

Completion evidence: [completion.json](evidence/gettenberg-acquisition-core-20261015/completion.json).
Final canonical suite2744 passing tests;68 acquisition tests. Native WI-0005 stays
proposed and execution records stayin_progress. Internal integration is staged
delivery, not main delivery or completion of the Gutenberg replacement. Existing
merged execution bodies remain historical; this entry records the subsequent outcome.

Process observations: second boundary review was valuable because shared ownership
exposed failures that isolated resource tests missed. Model the complete publisher /
reader / cleanup interaction, including process death and post-commit errors, before
broadening consumer adoption. Preserve a review/repair reserve even for a one-hour
run. Initial statement coverage did not establish those guarantees. A PR-link-only
push restarted CI; future native record creation can include known PR metadata in
one repair push. One final LRH invocation accidentally ran at repository root,
reported missing focus/current_focus.md and did not stop its shell sequence; rerun
from lcats/ passed0errors/351existingwarnings before integration. Use fail-fast
validation sequences with an explicit package working directory in future runs.
The usage read before assignment2 was missed; subsequent readings are recorded
honestly. Final shared weekly meter69% versus58% launch is not attributable run cost.

Two assignments, under17cumulative worker minutes, no active workers or further
feature work. Domain work stops after roughly59minutes, within the60-minute target
and75-minute hard ceiling; only this final documentation/checkpoint push remains.
Remaining WI-0005: conditional refresh/304 and provenance composition, pure resource
selection, strict text/container decoding, and qualified automatic Gutenberg routes.
Next bounded grant should select one of those coherent tranches; do not interpret
this run's success as authorization for another run or main promotion.

## 2026-10-15 02:09 UTC — Resource selection sprint grant

Human accepted the proposed A17-only sprint with "go for it!". Start 02:09:18 UTC,
target 02:24:18, hard stop 02:29:18, including review/checkpoint. Final 7–8 minutes
reserved for qualification. Base c447c15be9f2314201750b9615fdef04af7bf5d9 on
codex/gettenberg-acquisition; child codex/gettenberg-resource-selection. One cold
review assignment, maximum 8 worker minutes, two concurrent agents including
coordinator; no recursive delegation. No main promotion, WI completion, live
Gutenberg requests, policy changes or automatic renewal. Existing charter adapter
authorizes routine bounded implementation and internal integration only.

Plan: resources.select_resource with immutable preferences/results/diagnostics,
private pure selection module, focused unittest coverage, reference/how-to updates.
Default UTF-8 plain text, other plain text, HTML; explicit media preferences may
select any catalog format without promising an extractor. Stable source-order
ties; no URL/extension guesses, I/O, downloads or mutation. No match is a typed
result, malformed caller preferences a ResourceInputError. MIME claims are parsed
conservatively; malformed claims are diagnosed rather than treated as text/plain.
Multiple format claims remain preserved. Selection is evidence of a declared
format, not verified byte encoding or route qualification.

Readiness yes/no warnings; prior-art verdict already in WI, no select_resource
implementation found in current gettenberg. Demand WI-0005/A17 remains partial.
WI-0002 canonically resolved on main and inherited at base. Skill lrh-implement
and its required references, lrh-self-review and workflow read under charter
adapter; package/root AGENTS and STYLE apply. LRH 0.2.5.dev3596+gd86755f50;
watched gates not stale, persistent skip consent invalid; explicit human run grant
is authority, consent untouched. Python environment LCATS, explicit worktree
PYTHONPATH. Canonical format/lint/test/LRH/readiness/diff checks required.
Shared account weekly meter 70% at launch; per-run cost unavailable.

### Selection sprint qualification checkpoint — 02:15 UTC

17 focused tests pass. Coordinator boundary probe reproduced a NUL-containing
charset raising ValueError and an invalid non-ASCII codec suffix being normalized
as UTF-8; source claims now reject controls/non-ASCII and invalid/extended charset
parameters with invalid_format diagnostics. New regression subcases cover these.
First canonical run 2761 tests/78.420s failed one executable-documentation test:
it expected three code blocks, now five. Expanded its real metadata fixture and
executed all five examples, asserting selection leaves the one-request count
unchanged; full rerun in progress. No tests skipped or assertions weakened.

One cold independent review dispatched 02:15:18, deadline 02:22:18 (7 minutes),
against the full diff including new files at base c447c15b. It runs concurrently
with the repaired canonical test run to preserve the short-run review reserve;
this is a sequencing adaptation, not waived validation or early PR qualification.
Shared weekly meter 71% immediately before dispatch. Exact reviewed hashes and
coordinator verification of findings will be retained. No second assignment.

### Selection review repair — 02:18 UTC

The first corrected canonical suite passed 2761 tests. Cold review then found
one P2 in stdlib email parameter normalization: malformed charset*1 became UTF-8,
and a 5000-digit continuation index raised raw ValueError. Coordinator directly
reproduced both before accepting the finding. Replaced general email parsing with
validated raw parameter parsing; all charset continuations are explicitly rejected.
18 focused tests pass, including missing-zero/split/huge continuation regressions.
Same-assignment recheck and canonical validation run concurrently. No new features.

### Selection qualification complete — 02:20 UTC

Final canonical suite passes 2762 tests in 77.397 seconds; 18 focused tests.
Format/lint pass (260 Python files); LRH 0 errors / 351 existing warnings.
Reviewer recheck cleared the P2 and reported no further actionable findings;
coordinator matched all six product/test/doc SHA256 values. One assignment with
one same-scope recheck used under 4 worker minutes. No active reviewer remains.
A17 maps to selection_test.py and the five-example loopback documentation test.
Qualification JSON preserves exact reviewed content and the initial failed run.
Opening an internal PR; main and native WI/execution lifecycle remain untouched.

### Hosted review repair and stop decision — 02:26 UTC

All four checks passed on a1a766a7; first Codex review completed without findings.
Copilot then reported one P2 at the 15-minute target: regex finditer rescanned
whitespace padding quadratically. Coordinator reproduced 5000/10000 spaces at
0.129/0.509 seconds. Repaired with stripped input and parameter matches anchored
to the preceding match end, while retaining the original matched_format claim.
Added 100000-space surrounding/inter-parameter regression. After repair the same
probe measured 0.00048/0.00093 seconds, and 100000 spaces took 0.00949 seconds.
These are local diagnostic measurements, not a portable performance guarantee.

Final same-assignment recheck (second of two) resumed within the eight-minute
cumulative reviewer allowance; its new stop is 02:27:15, within the run hard stop.
Full tests rerun. Internal integration is deferred: repair-head hosted CI cannot
be assumed from the prior green head. Preserve the qualified repair/checkpoint,
record pending hosted validation, and stop without main or integration merge.
Process lesson: reserve time for the first hosted round even when cold review is
clean. Small pure APIs can still have metadata-parser performance edge cases.

### Selection sprint stop checkpoint — 02:27 UTC

Final repaired suite passes 2763 tests in 76.797 seconds; 19 focused selection
tests. Format/lint and diff checks pass; LRH 0 errors / 351 existing warnings.
All six final independently reviewed hashes match. One review assignment, two
same-scope rechecks, under five cumulative worker minutes; no active workers.

PR511 remains open against codex/gettenberg-acquisition. Previous head a1a766a7
had all four hosted checks green; final repair requires its own hosted checks.
No integration/main merge, force push, branch deletion or bulk download occurred.
Execution records stay in_progress and WI-0005 stays proposed. Next action is
verify repair-head CI and review state, then coordinator integration under a new
grant. Remaining feature scope is refresh, decoding, catalog provenance and routing.

Final evidence: [hosted-repair.json](evidence/gettenberg-selection-20261015/hosted-repair.json).
Shared weekly meter rose from70% to72%; this is account-wide, not per-run cost.
The sprint used approximately18minutes including the late review repair and
checkpoint, within the20-minute hard stop. No implicit continuation or renewal.

## 2026-10-15 04:51 UTC — PR511 internal integration

The human explicitly requested "Integrate PR 511 please." This authorizes the
integration and its evidence checkpoint, not another bounded feature run or main
promotion. Rechecked the exact PR head 5ca97617b72a32162f28826808c65542f38d27ca
and base c447c15be9f2314201750b9615fdef04af7bf5d9 on
codex/gettenberg-acquisition immediately before merge. All four final-head checks
passed (coverage, lint, and both test runs); the only hosted review thread was
resolved, with independent repair verification already recorded.

[PR #511](https://github.com/xenotaur/LCATS/pull/511) merged at 04:51:55 UTC as
8c3f9c139977e728b72c12cc3ea8dffb27a0f90d. The integrated tree equals the verified
PR-head tree; all six independently reviewed source/test/doc hashes still match.
The prior 2763-test canonical qualification applies to that identical tree.
No additional product tests were needed for this merge and evidence-only update;
LRH validation is rerun for the new control-plane records.

[Integration evidence](evidence/gettenberg-selection-20261015/integration.json)
records the exact head/base, merge and check identities. Historical sprint-stop
records retain their original pending-CI state; this entry records the subsequent
outcome. Native executions remain in_progress, WI-0005 remains proposed, and
main is untouched. No branch deletion or new implementation occurred.

A17 resource selection is now internally integrated. Remaining WI-0005 scope:
conditional refresh, strict text/container decoding, catalog receipt composition,
and qualified automatic Gutenberg routing. Further implementation needs a new
authorized run; integration alone does not renew the expired sprint grant.

## 2026-10-15 05:02 UTC — Offline decoding run grant

The human requested another bounded run after the recommendation of strict offline
text/container decoding with a 45-minute target / 60-minute hard stop. Start
05:02:55 UTC, target 05:47:55, hard stop 06:02:55. Feature freeze at 05:32:55;
remaining time is for review, repair, validation and checkpoint. Scope is WI-0005
A18/A19 only, not refresh, catalog receipt composition, route qualification,
gatherer migration or main promotion. Base c1c9a3e6f6399e421eae40c75a38efaf3f78d7ba;
child codex/gettenberg-offline-decoding targets codex/gettenberg-acquisition.

Use the approved charter adapter and LRH implementation/review procedures already
read in this session. Coordinator plus one cold independent reviewer planned;
one review assignment with up to two same-scope rechecks, at most 20 cumulative
worker minutes. Broader inherited ceilings are not targets. No recursive delegation,
new paid calls, external data downloads, CI changes, persistent policy edits or
automatic renewal. Native work item/executions stay nonterminal until main delivery.

Native readiness yes, no warnings; prior-art check in WI. Legacy gatherers perform
network decoding with replacement fallback and are migration targets, not reusable
strict offline decoding. Source/cache/model dependencies are independently reviewed
and integrated ancestors; WI-0002/0004 canonically resolved. No duplicate decoder
exists in gettenberg. Watched gates clean, persistent skip consent invalid; explicit
human grant is authority. Shared weekly meter 74%; per-run usage unavailable.
Environment: LCATS Python 3.11.9 with absolute worktree PYTHONPATH. Root/package
AGENTS and STYLE apply; control plane remains documentation/non-executable data.

### Coordinator implementation decisions before code

Public resources.decode_text accepts immutable bytes or a SourceArtifact, optional
catalog_formats tuple, and immutable DecodeOptions. Bare bytes have no invented
HTTP provenance. Artifact reads are bounded, regular-file-only and reverify hash,
length and receipt identity. Outputs are immutable DecodedText, versioned with raw
source hash, payload hash, chosen encoding/source, transformation/member details,
diagnostics and a derived identity incorporating relevant metadata/options.
No persisted decoded cache, network, filesystem extraction, boilerplate removal,
HTML asset fetching or catalog setup.

Default bounds: 32 MiB original input, 64 MiB inflated payload per stage, 1000 ZIP
entries, 64 KiB combined declaration metadata and 8192 bytes HTML declaration scan.
Bounds are positive integer caller options, not invisible truncation. Gzip output
is streamed with a one-byte overflow sentinel; reject corrupt/truncated/concatenated
streams. At most one HTTP gzip layer followed by one gzip or ZIP container. ZIP
central directory is bounded and counted before ZipFile allocates member records;
reject ZIP64/multidisk, unsafe names, symlinks/special entries, encryption and
unsupported compression. Read a single txt/html/htm/xhtml member, or an explicit
safe text member; ambiguous choices error. No filename-based encoding inference.
EPUB/PDF/audio are byte-only, not text extractors.

Encoding authority is explicit override, BOM, HTTP charset, catalog charset, HTML
meta declaration, then strict UTF-8. Without override/BOM any distinct declarations
error; unknown selected codecs or invalid bytes error. Override/BOM may supersede
conflicting lower claims with explicit diagnostics. HTML meta inspection is bounded
and parses tags without fetching assets; return markup unchanged. Plain untyped
bytes default to text/plain with an explicit diagnostic. Supported text media are
text/plain, text/html and application/xhtml+xml; compressed MIME claims describe
containers, not extracted member type. Selection's validated MIME grammar is reused
privately without changing its existing behavior. All details require offline tests,
independent review, canonical qualification and exact-head CI before integration.

### Decoding implementation checkpoint — 05:16 UTC

53 focused offline tests pass, including four executable how-to examples.
Initial tests caught binary transform codec classification and a test expectation
that size-rejected bytes had already been hashed; classification was corrected,
and the public pre-hash size-rejection contract is now explicit. No input is read
past its permitted size merely to compute an error identity.

Code inspection identified ZipExtFile truncation to declared output length;
selected compressed extents are now independently inflated, counted and CRC-checked.
A forged short size/prefix CRC regression fails explicitly, without hidden output.
ZIP central-directory record counts are checked before member-index allocation.
No extraction, download or persisted derived cache was added.

Canonical tests and cold review may run concurrently under the existing bounded
adapter; neither is waived, and both must qualify the same final source before
push/integration. Review target is the full diff including new files against
c1c9a3e6. Shared weekly meter 75% before planned dispatch. No extra assignment.

### Independent review repair — 05:22 UTC

One cold review found a P2: HTMLParser can raise AssertionError for malformed marked
sections and ValueError for excessive numeric entities within the scan bound.
Coordinator reproduced both independently. Translate only the parser boundary,
retain structured diagnostics/source hash, and test direct and http-equiv forms.
54 focused tests and the same-assignment independent recheck pass; 13 reviewed
file hashes verified. One review assignment, one recheck, under six worker minutes.
No additional delegated scope. Shared weekly meter 77%; attribution unavailable.
Canonical rerun includes the new persisted ResourceStore artifact boundary test;
source integrity, no extra requests/writes and compressed-byte preservation tested.

Process observation: a bounded byte scan does not make a standard-library parser's
exception contract safe. Keep parser errors at a narrow typed boundary and require
adversarial malformed-attribute fixtures in future LRH review packets. Independent
review found a concrete defect, rather than merely repeating the test results.

### Canonical qualification — 05:24 UTC

Final scripts/test passes 2818 tests in 69.921 seconds, including 54 focused decoder
tests, four new how-to examples and persisted acquisition→offline decoding.
Format/lint pass; LRH 0 errors / 351 existing warnings; readiness yes; diff check
and new-doc relative links/fence pairs pass. Initial 2816-test suite also passed
before the additional boundary test and independent review repair. Qualification
maps A18/A19 to reviewed source/test/doc hashes and explicit command evidence.
Source is frozen for PR/hosted review; any repair invalidates affected evidence.

### Internal PR checkpoint — 05:25 UTC

[PR #512](https://github.com/xenotaur/LCATS/pull/512) opened against
codex/gettenberg-acquisition with implementation commit a1ac41bb. Native primary
[execution](../executions/WI-GETTENBERG-0005/2026_10_15_05_24_50_WI_GETTENBERG_0005_DECODING.md)
and [review record](../executions/AD_HOC/2026_10_15_05_18_01_WI_GETTENBERG_0005_DECODING_SELFREVIEW.md)
retain the session pointer and PR/rerun backlink. Source frozen; first hosted rounds
and exact-head CI remain pending. No worker active. Roughly 23 elapsed minutes;
22 minutes to target, 37 to hard stop. Remaining scope is validation/review/repair,
then internal integration if qualified, otherwise a resumable open PR.

### Hosted portability failure — 05:28 UTC

CI uses CPython 3.11.17; local canonical environment is 3.11.9. Hosted test logs
show the unknown marked section is accepted by the newer HTMLParser, so the test's
unconditional error expectation failed. Numeric-entity cases passed. Product code
already preserves accepted markup and translates parser failures; no code change
is required. Split the version-sensitive fixture into a contract test accepting
only unchanged successful text/provenance or the documented typed error with source
hash/diagnostics/cause. Raw exceptions and rewritten text still fail. No skip or
exception suppression. Document the parser-version limitation explicitly.
This is a test-assumption repair, not a weakened decoding acceptance criterion.

### First hosted review repair — 05:32 UTC

Hosted first round found P1 test portability (already repaired and independently
rechecked) and P2 embedded ZIP end-record signatures in a valid archive comment.
Coordinator reproduced the P2; Python ZipFile also rejects that valid fixture, so
fixing only preflight would be incomplete. Bounded backward candidate scanning now
requires exact comment/directory boundaries. The stdlib index reader receives a
validated comment-free in-memory view, preserving member offsets and original bytes.
Four fixtures cover short/full misleading signatures, repeated signatures and maximum
comment length; hashes/raw artifact bytes remain unchanged. No filesystem extraction.

Both allocated same-scope independent rechecks have been consumed. The ZIP repair
will be pushed after canonical validation but left awaiting fresh independent
verification; no internal integration is authorized without that evidence. Preserve
this cap rather than quietly adding an assignment. Process recommendation: batch
CI and hosted findings before the final reserved recheck, or budget a distinct
hosted-repair verification slot. The second recheck was dispatched before hosted
review completed and proved too early. This is sequencing overhead, not a design
blocker or a reason to weaken review.

### Repaired source qualification — 05:33 UTC

Final canonical scripts/test passes 2820 tests in 79.860 seconds; 56 focused tests.
Format/lint, LRH (0 errors / 351 existing warnings), readiness and diff check pass.
The preceding portability-only rerun passed 2819 tests in 83.451 seconds. Both
hosted findings are repaired; first-round CI failures remain recorded, not erased.
Final hashes and validation are in hosted-repair.json, explicitly excluding a claim
of independent acceptance for the final ZIP changes. Push and await exact-head CI;
leave PR open, with fresh independent verification as the next bounded action.

### Bounded run checkpoint / stop — 05:38 UTC

Run finishes after approximately 35 minutes, before the 45-minute target and
60-minute hard stop. [PR #512](https://github.com/xenotaur/LCATS/pull/512) remains
open against codex/gettenberg-acquisition. Repaired-code head
caada6e8d50d343d7793226ff48edf35d9a1ec79 has all four hosted checks green:
coverage, lint and both test runs. [Checkpoint evidence](evidence/gettenberg-decoding-20261015/checkpoint.json)
retains the exact head/base/check URLs. This final evidence-only commit changes
no product, tests or docs; hashes were checked against hosted-repair.json. Its own
CI must still be verified before a later integration. Local canonical 2820 tests,
56 focused tests and exercised docs pass; no source changes after qualification.

No workers active, one review assignment, two same-scope rechecks, less than eight
cumulative worker minutes (20-minute ceiling). Shared weekly usage last observed
78% versus 74% at launch; no per-run cost attribution is available. No external
bulk downloads, persistent consent/policy edits, CI changes or main promotion.
Native records remain in_progress, WI-0005 proposed. No automatic renewal.

A18/A19 implementation is staged, not independently accepted in its final form:
the final ZIP-comment repair still needs a fresh independent check. Both hosted
threads remain open for authoritative confirmation. Exact next action: a short
review/integration grant for PR512, verify final hashes/diff and both repairs,
resolve verified threads, check current head/base/CI, then integrate internally.
Conditional refresh, catalog receipt composition, route qualification and gatherer
migration remain unattempted in this run.

Learning: the patch-version test failure and ZIP comment bug were real findings;
CI and review added distinct evidence. The avoidable delay was spending the final
recheck before the first hosted round arrived. Recommend reserving that recheck
until CI and hosted feedback can be batched, or explicitly allowing one final
repair-verification assignment within an unchanged worker-time ceiling. Do not
quietly increase the current cap or infer acceptance from green tests alone.

## 2026-10-15 06:03 UTC — PR512 review/integration grant

Human explicitly requested the review-and-integration pass for PR512, renewing
review/repair/integration authority for this PR only, not a new feature run or main
promotion. Clean head54401a99, basec1c9a3e6 on codex/gettenberg-acquisition; all four
head checks green. Native review-response rerun explicitly authorized by this new
request; link to prior in_progress review record rather than treating it as landed.
Use the previously read LRH review-response workflow under the charter adapter.

Correction to previous checkpoint: Copilot's first review arrived at05:34:29,
before the05:38 stop, and was missed by the final CI-only query. Four additional
unresolved threads concern container declarations and Unicode BOM semantics.
No integration occurred, so the gap did not land unreviewed defects. Future final
checks must fetch all review authors/threads alongside CI, never only the first
bot or recent comments. Historical evidence remains intact with this correction.

Coordinator reproduced all four issues: gzip accepted as declared ZIP; generic
UTF16 override omitted an opposing endian conflict; UTF8 BOM authorized native
UTF16 decoding; utf8-sig removed a second content U+FEFF. Repair all before one
fresh independent review of the entire repair delta, including the earlier ZIP
comment change. No delegation until fixes/fixtures are stable. Keep original bytes,
strict errors and charter lifecycle boundaries. Product/API scope unchanged.

### Independent repair review — 06:09 UTC

Fresh reviewer passed60 focused tests and additional MIME/Unicode probes, clearing
five hosted threads. Stronger ZIP comment counterexamples reproduced by coordinator:
a fully plausible fake empty EOCD hides the story, or a fake record with matching
arithmetic points at invalid directory bytes. Select the earliest structurally valid
directory in the bounded comment window, validating actual records/count and first
local-header layout before acceptance. Empty archives cannot hide prepended bytes.
Add both regressions; source remains frozen for same-scope recheck and canonical
rerun. Prior2824-test canonical pass is historical, not final-repair qualification.

### ZIP candidate validation replan — 06:18 UTC

Review exposed earlier fake EOCD/index bytes inside a stored member, including a
zero-size forged index that could hide text. Coordinator reproduced them. Signature
arithmetic and central records are not sufficient proof of a candidate directory.
Replan within the same repair scope: validate the complete candidate structure and
local header/name/extent/size agreement (including streaming data descriptors)
before enforcing unsupported-format/count policies. Two bounded-byte walks avoid
allocating a member index before acceptance. ZIP64 policy is deferred until complete
candidate layout is known, preventing unsupported-looking story bytes masking the
real archive. Genuine ZIP64 remains refused. Explicit regression fixtures preserve
all original text, including adversarial bytes. No extractor/format scope expansion.

Earlier checks passed2824 and2825 tests but predate the final structural repair.
An intermediate focused run exposed four error-precedence assertions: preserve
actual-count and ZIP64 codes; make encrypted fixture coherent in both headers;
expect invalid_container for contradictory local/index CRC/size rejected before
inflation. This is stronger early integrity validation, not skipping rejection.
Fresh reviewer checked these changes and continues same-scope verification.

### Final independent acceptance — 06:20 UTC

Reviewer cleared all six hosted threads and final same-scope repair, running64
focused tests plus independent MIME/Unicode/EOCD probes. Four final changed-file
hashes match; all other previously reviewed source/test/doc hashes unchanged.
One fresh review assignment including bounded followup, under15 worker minutes,
ended by06:19:45. No active worker. Final canonical qualification underway; no
further product edits planned. New integration-repair.json supersedes earlier
pending-repair evidence without rewriting history. Main delivery/closeout remains
outside this internal integration instruction.

### Inflation regression coverage preserved — 06:22 UTC

Coordinator extended the short-size fixture to forge BOTH local and central headers,
so early metadata disagreement cannot replace coverage of actual inflation counting.
The reviewer verified decoded_limit under100bytes and invalid_container without the
cap;64 focused tests pass, product/docs unchanged, final test hash recorded. Final
canonical run repeated because package guidance requires scripts/test after test
changes. Earlier final-product run passed2828 tests in75.923seconds; final test-only
addition is separately identified. Independent assignment including followups stayed
under17 worker minutes, no workers active. Avoid repeat canonical runs until repair
source and tests are frozen in future passes; this pass incurred that overhead.

### Final repair qualification — 06:24 UTC

Final scripts/test passes2828 tests in78.673seconds, with64 focused decoder tests.
Format265files/lint pass; LRH0errors/351existing warnings; readiness yes; diff check
passes. Four final changed-file hashes independently verified; remaining nine prior
hashes unchanged. All six hosted findings cleared by fresh independent review.
Publish fixes and native continuation record, confirm threads, then require all
checks on exact final PR head and unchanged integration base before merging.

### PR512 internally integrated — 06:29 UTC

[PR #512](https://github.com/xenotaur/LCATS/pull/512) merged at2026-10-15T06:29:16Z
as97dad982500edf343ce4069c9bf2bcee1777e129 into codex/gettenberg-acquisition. Immediately before merge, headabcb6e4ed37e751e3c67080452c98088196fe6a8
and basec1c9a3e6f6399e421eae40c75a38efaf3f78d7ba matched the qualified/authorized branches; all four
exact-head checks passed, every review author/thread was re-read, and all six
independently verified threads were resolved. No unresolved findings remain.

Integrated tree equals verified PR-head tree; all13 source/test/doc hashes match
final or unchanged prior independent review. Final canonical2828 tests and64
focused tests therefore apply unchanged. Only non-executable integration evidence
and this log are appended after merge; LRH validation/diff check rerun, full suite
not repeated without a product change. [Integration evidence](evidence/gettenberg-decoding-20261015/integration.json)
retains head/base/merge/check identities and reviewed hashes.

This review/integration pass took approximately26minutes from06:03:13, including
newly discovered repairs and CI. Main untouched; native executions remain
in_progress and WI-0005 proposed. No branches deleted, new feature run started,
external bulk download or persistent policy edit. A18/A19 now internally qualified
and integrated. Remaining WI scope: conditional refresh, catalog receipt composition
and qualified automatic routing; gatherer migration follows in its planned work.
Next feature work requires a new bounded grant.

## Conditional refresh run — 2026-10-15 06:35 UTC

Human authorized conditional refresh and selected a 60-minute target  / 90-minute
hard stop. Run gettenberg-20261015-refresh starts 06:35:29 UTC; target 07:35:29,
hard stop 08:05:29, including tools/CI/recovery. Reassess at minute 45; feature
freeze by minute 60. Scope WI-0005 A14 only: explicit refresh/plan, conditional 304,
changed 200, provenance, atomic failure safety, tests and docs. No catalog
composition, automatic routing, gatherer migration, bulk downloads or main
promotion. Existing charter adapter authorizes coordinator integration only.

Base 9fb1c767c7eeca6cdab23d3b9fcfbe171a738997 is clean and freshly fetched;
PR512 merge 97dad982 is an ancestor. Child codex/gettenberg-conditional-refresh
will target codex/gettenberg-acquisition. Readiness yes. Native execution remains
in_progress and WI proposed until main. LRH 0.2.5.dev3596+gd86755f50: watched
skills clean, persistent skip consent invalid; this explicit grant does not
alter it. Python 3.11.9 LCATS env with intended-worktree PYTHONPATH. Account usage
4% weekly at launch; per-run tokens/cost unavailable and account telemetry is
not attributable. No paid external model calls or new dependencies.

Coordinator implements; one independent reviewer planned before first push,
with final same-scope verification reserved until CI AND every hosted author's
first round arrive. Inherit six-assignment /four-total-agent /45-worker-minute
ceilings; target 20–30 worker minutes, reserve 15 for final review, max 30 per
assignment. At most two same-scope repair rechecks per assignment. Normally two
agents including coordinator; no recursive delegation. Finish early if accepted.

Pre-implementation decisions: preserve v1 receipt/hash readability and use v2
receipts for new acquisitions/validations, with previous receipt hash and separate
validation time. 304 preserves original retrieval time/body and publishes only
new receipt/reference, never relinking old body inode. Validators are syntactically
checked and bound to the exact cached final URL on every hop. Missing/invalid
validators cause unconditional GET; unsolicited304 fails. Updated representation
headers must not contradict cached decoding metadata. Changed 200 uses the existing
atomic publication path and retains old body/receipt. Refresh rechecks after the
network lock and coalesces a concurrent successful update; ordinary fetch remains
network-free on hits. No automatic age freshness or HTTP shared-cache semantics.

Acceptance: ETag/Last-Modified 304, changed 200, cold/malformed/corrupt 304, route
changes and validator isolation, no-validator fallback, repeated/history reads,
offline/plan purity, serialized updates, injected publication failures, archive
safety, v1 receipt/decoder compatibility, and exercised docs. Standards grounding:
RFC 9110 sections 8.8/13.1, RFC 9111 section 4.3.4. Preserve fail-closed integrity and
cooperative budgets; do not equate weak validation with byte identity at origin.

Loaded skill fingerprints (SHA256): lrh-implement: 48ac749cb86b8bec8a4a3af931b29d89ff4b207b30ee703bb7d6a5f784111165;
lrh-self-review: d2cc54ad32989e8c6c598d21a70c9d5b9ce2bfb35e87031caed7606124d5921c;
lrh-review-response: 42acff29a55c7d8dcc573f68b8c9de876b132ebbe831936f3c6a21239f6bcc8e,
all under /Users/centaur/.agents/skills/<name>/SKILL.md. Session selected model,
codex_app backend; runtime does not expose an enforceable per-run credit meter.

### Implementation checkpoint — 06:50 UTC

Source frozen for independent review after 152 focused tests, lint/format, doc
execution/link/fence checks and LRH validation (0 errors, 351 existing warnings).
One cold reviewer dispatched at 06:47:45, initial deadline 07:02:45; final hosted
repair verification remains reserved. No other workers. Implementation took about
12 minutes; full canonical qualification intentionally waits for stable review.

First regression failure was a test helper serializing the expanded Python record
as schema 1. Updated it to produce explicit schema 2, while a separate historical
file fixture proves v1 hash/read/decoding compatibility before and after refresh.
Added actual validation_headers distinct from merged headers so omitted vs returned
validators remain auditable. No feature expansion. Freshly fetched main is
210468236ff4db78d2d7c5218562fa2d166e6400; it is not this internal PR's base.

### Initial review repair — 06:53 UTC

Independent reviewer identified two P2 issues: accepting a validator-less 304
misapplied RFC 9111 section 4.3.4, and comparing Last-Modified wire strings rejected
equivalent dates. Coordinator verified the official RFC text, required a matching
returned validator, compared valid HTTP dates as UTC instants, and tightened
weekday syntax. Added missing-validator/date-equivalence regressions and preserved
specific representation-header and publication-fault assertions. Focused 154 tests
pass in 5.569 seconds; lint/format pass. Reviewer is verifying the consolidated repair.

Process observation: three files changed while initial review was still active,
with advance notification but without a preserved pre-repair hash snapshot. Initial
findings are grounded in inspected code/initial tests; acceptance must use final
repaired hashes. Future runs should capture a source manifest before dispatch and
wait for initial report before editing, avoiding ambiguous overlapping probes.
One same-scope recheck used; second remains reserved for hosted feedback. No scope
expansion or canonical-suite repeat yet. All executable implementation/fixtures
remain in src/tests; control-plane evidence is Markdown/JSON only.

### Pre-push qualification — 06:57 UTC

Independent acceptance complete, all 12 source/test/doc hashes match. Canonical
scripts/test passes 2849 tests in 69.672 seconds; 154 focused tests plus independent
nine-pair date/refusal probes pass. Format (267 files)/lint pass; LRH 0 errors / 351 existing
warnings. One review assignment with recheck1 used under nine worker minutes;
no active workers, final recheck reserved for all hosted feedback plus CI. Main
untouched. [Qualification](evidence/gettenberg-refresh-20261015/qualification.json)
records final source identities, acceptance mapping and review limitations.

### Hosted review repair — 07:08 UTC

PR513 opened at 06:57:42 with product commit 8ba82684; native backlinks added in
1d1dfc6b. All four exact-head checks passed. Copilot first round 07:03:19 had zero
findings; Codex first round 07:04:37 found two valid P2 boundary defects. Both were
reproduced before production edits: two new tests failed in eight subcases.

Aggregate receipt-size rejection had moved after body linking, leaving avoidable
unreachable immutable bodies. Restore serialization/size preflight before either
publication path. Persisted 304 validation_headers could lack any returned validator
even though transport would refuse such an event. Add shared validator-syntax checks
to the reader, without unbounded history traversal. Existing cache-reference failure
and historical-byte preservation remain unchanged. New regressions cover repeated
oversized resource/archive responses and empty/representation-only/malformed returned
validators in otherwise hash-consistent receipt files.

Focused 156 tests pass in 5.726 seconds; lint/format/diff check pass. Captured the full
12-file candidate manifest BEFORE final recheck dispatch at 07:08:20. Four files
changed; eight previously accepted source/test/docs are unchanged. Final planned
same-scope recheck has a 15-minute allowance, leaving total worker occupancy under
24 minutes and the run under its 90-minute hard stop. No active implementation worker,
no scope expansion; canonical qualification follows stable independent acceptance.

Account-wide weekly usage at 07:03 was 8%, versus 4% launch; not attributable per-run
telemetry. No numeric usage cap was agreed. We waited for BOTH hosted authors and
CI before spending this final recheck, avoiding the earlier decoding-run error.
Observed review gap suggests future LRH acceptance packets explicitly enumerate
writer/reader invariant parity and aggregate (not only per-field) resource budgets.

### Final independent recheck — 07:11 UTC

Recheck 2 cleared both hosted P2s. Independent 156 tests pass in 5.682 seconds; extra
resource/archive ×200/304 oversized-metadata probes preserve all prior bodies,
receipts and references and clean temporary files. Five hash-consistent invalid
validation receipts also fail offline decoding, including mixed valid/invalid
validators. All 12 hashes match the pre-dispatch manifest; eight unaffected files
match 1d1dfc6b. Both hosted authors reviewed 8ba82684, whose only delta to 1d1dfc6b is
two execution-record backlink lines. One reviewer assignment plus two rechecks used
under 13 worker minutes; no active workers. Canonical suite is running against
frozen accepted source. No further feature work or review retrigger is planned.

### Final repair qualification — 07:13 UTC

Final canonical 2851 tests pass in 68.435 seconds; 156 focused tests pass. Format,
lint, LRH validation (0 errors, 351 existing warnings), docs and diff checks pass.
Independent review cleared both hosted findings at matching source hashes. Push the
repair and require green checks on its exact head before any internal merge.
Initial evidence remains historical; hosted-repair.json records final acceptance.

### PR513 internally integrated — 07:18 UTC

[PR #513](https://github.com/xenotaur/LCATS/pull/513) merged at 2026-10-15T07:18:29Z
as 0a5ccd426b07511a535ab9172fc8418818c89da6 into codex/gettenberg-acquisition. Immediately before merging,
head 0454e6affcd1f3ed8df5594aea2780ba894b1647 and base 9fb1c767c7eeca6cdab23d3b9fcfbe171a738997 matched the authorized/qualified branches;
all four final-head checks passed and all authors/threads were re-read, with both
independently cleared threads resolved. Repairs were **pushed directly** in0454e6af.
No hosted review was manually retriggered and no finding was skipped.

Merge parents match the recorded base/head; integrated tree equals verified-head
tree and all 12 reviewed source/test/doc hashes match. Canonical 2851 tests and
156 focused tests therefore apply unchanged. Append only non-executable integration
and lifecycle evidence after merge; rerun LRH validation/diff/readiness, not the
unchanged product suite. [Integration evidence](evidence/gettenberg-refresh-20261015/integration.json)
retains identities, exact checks, author coverage, hashes and bounded-run telemetry.

Conditional refresh A14 is internally delivered. Main is untouched; all native
executions remain in_progress and WI-0005 proposed. Remaining scope is catalog
receipt composition (A15/A16), qualified automatic routing, and subsequent
migration. No new run, destructive cleanup, bulk download or policy change.

Run completed in approximately 45 minutes including reviews, two repair stages,
canonical tests, hosted CI and checkpointing, within the 60-minute target and
90-minute hard stop. One independent reviewer assignment plus two bounded rechecks
used under 13 worker minutes; no worker remains active. Shared-account weekly usage
moved 4% to 10%; per-run attribution/tokens/cost remain unavailable. The larger
allowance provided repair headroom; no extra feature was added to fill time.

Process findings: preserve a pre-dispatch source manifest and freeze until initial
review returns; qualify only stable repairs; explicitly test writer/reader invariant
parity and aggregate metadata limits; wait for all hosted authors plus CI before
using the last independent recheck. This run followed the latter three lessons after
recording the initial snapshot gap, and finished without a separate integration grant.

## Catalog receipt composition run — 2026-10-15 15:20 UTC

Human authorized the next bounded tranche after PR513: WI-0005 A15/A16, catalog
receipt composition and refresh safety. Start 15:20:21 UTC, target/feature freeze
16:20:21, hard stop16:50:21 including CI/review/checkpoint. Inherit the approved
60/90-minute grant, six assignments, four total agents, 45 worker minutes with
15 reserved for review, maximum30 per assignment and two same-scope rechecks.
Coordinator implements; one cold independent review before first push, with final
recheck reserved until all hosted authors and CI. No automatic renewal, main
promotion, live Gutenberg download, dependency/CI change or policy modification.

Fresh clean base 0afde71e7156eea30898d9ea191ae17c4874b802 includes PR513 staged
acceptance (A14) and earlier lifecycle staged acceptance. Prior-art/demand check
is present in WI0005; existing local lifecycle supplies retention, verification,
count-change approval and pinned readers. Reuse these mechanisms. Readiness yes;
watched skills clean, persistent skip consent invalid and unchanged. Explicit
charter adapter authorizes coordinator plan/integration decisions. Native records
remain in_progress and WI proposed. Weekly account usage10%, not attributable;
per-run tokens/cost unavailable. Same LCATS environment, PYTHONPATH bound to this
worktree; no environment changes. Child codex/gettenberg-catalog-receipts targets
codex/gettenberg-acquisition. Prompt identity:
PROMPT(WI-GETTENBERG-0005:WI_GETTENBERG_0005_CATALOG_RECEIPTS)[2026-10-15T15:20:33+00:00].
Idempotence found no previous execution.

Pre-implementation decision: accept SourceArtifact as typed local input to setup
and explicit rebuild; add offline update(SourceArtifact) to reuse a verified active
generation when archive identity is unchanged, otherwise prepare/verify/activate
through existing count approval. setup keeps its documented ignore-input-on-hit
behavior; rebuild always builds. Implicit rebuild preserves acquired provenance.
No network enters CatalogManager. Receipt validation is shared with decoding;
validate canonical receipt hash/schema/size, archive-kind identity, and copied
archive hash/size before preparation. Embed the complete bounded receipt in new
version2 generation manifests, capped128KiB (receipt64KiB); retain reading version1
local manifests. Reader and writer enforce the same provenance binding. Unchanged
update does not rewrite immutable generation provenance; latest validation remains
in resource receipts. A generation records the receipt used for its construction.

Acceptance: local legacy unknown provenance; acquired setup/rebuild/update;
unchanged200/304 no build; changed input count approval/recoverable candidate;
implicit rebuild retains receipt after source cache reference changes; forged,
oversized, wrong-kind and changed-body evidence fails closed; acquisition/build/
count failures preserve active catalog and pinned readers. Exercise docs with
local fixtures, focused unittest, canonical format/lint/scripts/test, LRH validation,
readiness and diff checks; independent review and four exact-head CI checks before
internal integration. Changes limited to lifecycle/provenance helper, receipt
validation reuse, tests and docs plus non-executable control-plane evidence.

### Frozen-source review — 15:52 UTC

Source frozen/fingerprinted before one cold reviewer dispatch at15:47 UTC; no
product files changed during review. Initial197 focused tests passed8.158s;
format270 files/lint and executed docs/link/fence checks pass. Reviewer completed
before15:52 with no P0/P1/P2 findings,104 offline tests and389 Gettenberg tests.
Its first broader run hit sandbox loopback-bind restrictions; the permitted
localhost-only rerun passed. Adversarial probe rejected129 malformed variants,
accepted7 schema-valid variants, and handled deeply nested metadata with structured
errors. All9 source/test/doc hashes match before/after review. Under5 worker minutes
used, two rechecks available; final verification reserved for hosted review+CI.

Full canonical scripts/test now runs on accepted frozen source. First test attempt
had one fixture keyword typo (retries versus max_retries), repaired before the
197-test qualification. A separate version-report diagnostic initially inherited
the base Python environment; corrected report confirms Python3.11.9, Black25.11.0,
Ruff0.15.0 and intended-worktree imports. All reported product tests used that
project environment. LRH0errors/351existing warnings, readinessyes. Weekly account
usage12% versus10% at launch, not attributable. No scope expansion or main change.
Loaded skill fingerprints match the prior run's recorded lrh-implement,
lrh-self-review and lrh-review-response fingerprints; installed policy untouched.

### Pre-push qualification — 15:54 UTC

Canonical scripts/test passed 2867 tests in 74.388s; all9 product hashes
remain frozen and independently accepted. Format/lint/docs/readiness/diff checks
pass; LRH0errors/351existing warnings. Qualification JSON maps A15/A16 to concrete
fixtures and preserves source identities. No implementation repair was needed
after independent review. Open the integration-target PR and await both hosted
authors and exact-head CI; main remains outside this grant.

### Hosted repair and bounded checkpoint — 16:48 UTC

PR514 opened on8b4b3e1d; native backlinks974d6f61 only changed2 record lines.
Both first hosted authors reviewed: Copilot0 findings (runtime unavailable there),
Codex1 validP2. All4 pre-repair checks passed. A lone surrogate in source_uri or
headers passed ASCII receipt canonicalization but failed strictUTF8 generation
publication after ingestion. Coordinator reproduced both failures before repair.
Preflight now rejects invalidUTF8 JSON before retention/build and on read.
Independent recheck1 cleared all20 additional surrogate probes plus16 offline
tests;9 candidate hashes match,7 unchanged. Composition17 tests pass; canonical
2868 tests pass in72.643s; format/lint pass. Evidence: hosted-repair.json.

Clock observations jumped from15:54:28 to16:43:55 during hosted-review inspection.
The available tool evidence does not establish the cause. This time counts against
the original15:20:21 start and16:50:21 hard stop; no renewal or exemption inferred.
Switched to bounded repair/checkpoint only. One assignment plus one recheck used
under7 worker minutes; no worker active. No manual hosted retrigger, main change,
bulk download, policy change or scope expansion. Side repair label was minted
after repair started; primary instruction identity predates all work.

Push qualified repair, then stop without internal merge. Final-head CI and full
head/base/review-thread verification remain for a subsequent authorized integration
pass. A15/A16 implementation is a qualified PR candidate, not staged integration
acceptance. Native executions stay in_progress and WI proposed. Original
qualification evidence remains historical; hosted-repair.json supersedes its
source hashes/test count. Shared usage last observed12% versus10% at launch;
per-run cost unavailable. Process lesson: recheck wall-clock budget immediately
after delayed tools/resumption and retain a checkpoint reserve; do not let a
clock gap silently renew the grant.

## PR514 review and integration pass — 2026-10-15 18:06 UTC

Human explicitly requested review and integration after the prior bounded run
stopped. This separate pass authorizes PR514 integration and evidence only; it
does not renew feature-development scope. Clean head bfc3598576bfbe7291e46a7e4e8e256267a6786d
and fresh integration base 0afde71e7156eea30898d9ea191ae17c4874b802 matched the qualified
candidate. All nine reviewed file hashes and the canonical 2868-test log hash
matched; the Unicode pre-retention regression passed again in0.008s.

Read all hosted reviews, issue comments and threads without recency/outdated
filters, with pagination exhausted. Copilot reported0 findings and unavailable
runtime verification; actual independent389-test coverage and canonical evidence
cover its general compatibility concern. Codex's sole P2 was independently
cleared in the preceding repair; direct source and regression recheck confirmed
it. Resolved thread PRRT_kwDOKlhIbM6s2y0u, then re-read all authors/threads and
head/base immediately before integration. All4 final-head CI checks passed.
No new source repair, agent assignment, hosted retrigger or full-suite repetition.

[PR514](https://github.com/xenotaur/LCATS/pull/514) merged at 2026-10-15T18:07:55Z as
0f36cfc16e3da18d97047daa6ae055343551571b into codex/gettenberg-acquisition. Merge parents match
recorded base/head, merge tree equals reviewed head tree and all9 file hashes
match. Existing 2868-test qualification therefore applies unchanged.
[Integration evidence](evidence/gettenberg-catalog-20261015/integration.json)
records checks, authors/threads, resolution, source identities and acceptance.

A15/A16 are now staged internally. Main remains unchanged; native execution
records stay in_progress and WI0005 stays proposed until human-approved main
delivery. Automatic routing and subsequent consumer/CLI migration remain.
The old checkpoint/qualification records remain historical; this entry supersedes
their pending-integration status. Only non-executable evidence/lifecycle notes
are added after merge, with LRH/readiness/diff validation before checkpoint push.
Watched installed skills remain clean; invalid persistent skip consent is
unchanged, and this explicit grant supplies integration authority.

Integration checkpoint validation: LRH0 errors/351 existing warnings, WI0005
prompt-ready, and diff check clean. Evidence-only checkpoint pushed on the
integration branch; no product file changed after the verified merge.

## Automatic-routing bounded run — 2026-10-15 22:44 UTC

Human explicitly authorized the proposed next run: WI0005 A22 routing
qualification, pure route planning, route-aware resource selection, tests/docs
and review. Start22:44:39 UTC; target/feature freeze23:44:39; hard stop00:14:39
UTC on2026-10-16. Qualification checkpoint by22:59:39; reassess at minute45.
Use the existing charter adapter: coordinator implementation, one cold reviewer,
maximum4 total agents/6 assignments/45 worker minutes with15 reserved for review,
maximum30 per assignment and two same-scope rechecks. Reserve the final recheck
until all hosted authors and CI. No automatic renewal or main promotion.

Fresh integration base0a4aa7a801318e0ffade7aeb1e8f3f22c9a8e5d1 includes PR514
A15/A16 staged acceptance and PR513 A14; dependency evidence is ancestral.
Child codex/gettenberg-routing targets codex/gettenberg-acquisition. Native WI0005
readiness yes; records remain in_progress/WI proposed until main delivery.
Prior-art/demand check is present in the WI; route qualification is the identified
gap, not a replacement transport. Prompt idempotence found no previous execution.
Prompt: PROMPT(WI-GETTENBERG-0005:WI_GETTENBERG_0005_ROUTING)[2026-10-15T22:46:17+00:00].
LRH0.2.5.dev3596+gd86755f50, watched skills clean, invalid persistent skip consent
unchanged; explicit charter grant governs this run. Same project environment and
worktree-bound PYTHONPATH. Shared weekly usage15% at launch, not attributable;
per-run cost/tokens unavailable. No paid model calls or dependency/CI changes.

Research official documentation and pinned upstream source first; no client URL
cascades or human-site scraping. Implement only supported mappings and explicit
unsupported diagnostics; aliases unresolved by evidence stay unresolved. Preserve
original resource identity and route version. Keep original metadata and stable
selection preferences. Network policy remains separate from route construction.
Unit tests are offline, and any operational endpoint check will be separately
bounded in requests/bytes/time and recorded before execution. No bulk ebook or
catalog download, corpus change, CLI/gatherer migration, or policy restamping.
Expected changes: private routing/public facade and small selection extension,
fixture tests, Diataxis docs, and non-executable control-plane evidence. Canonical
format/lint/scripts/test, LRH/readiness/diff checks, frozen source manifest before
independent review, both hosted rounds and exact-head CI precede internal merge.
If authoritative alias rules remain unavailable, deliver a clearly labeled subset
and remaining qualification rather than declare WI0005 complete.

Routing qualification checkpoint (before22:52 UTC): authoritative Project Gutenberg
libgutenberg pg_archive_urls.py at d2d6f250374bb2463336ad7c6d0b0d164d0642db explicitly
translates /files and /ebooks, including single-digit IDs. ebookconverter
EbookConverter.py at88e05f3e22640b61bd30444402adcd656f582c37 independently supplies
format filenames. These factual URL conventions support independently written
routing; no upstream GPL implementation is vendored/copied. The upstream helper
has an apparent template-key mismatch; we do not execute it or inherit its loose
matching/fallback behavior. Unknown aliases remain unsupported, not guessed.

Chosen API: GutenbergRoutes with required separate main_root and generated_root
(the latter points at the directory containing ebook-ID directories), independent
catalog_url default; resolve() returns request or coded diagnostic. Pure
select_routable_resource composes all route decisions with the existing MIME
selector through an explicit eligible_indices capability input. Original resource
indices, order, metadata and MIME diagnostics survive. No default mirror is
selected or operationally claimed; caller configuration plus NetworkPolicy is
required. No live endpoint probe is needed for this explicit-root tranche.


Routing candidate qualification22:59 UTC: implementation frozen before the cold
review. Seven product/test/doc hashes matched afterward. Reviewer routing_review
found no actionable findings; independently408 Gettenberg tests and changed-code
format/lint passed. Coordinator canonical2886 tests in75.963s; format272 files,
lint, LRH0 errors/351 pre-existing warnings, readiness and diff checks passed.
All113 saved RDF resources route;17 published aliases plus concrete paths covered.
All routing how-to blocks execute against a tiny local server; the receipt test
checks alias reuse without rewriting original acquisition identity. The initial
new test omitted the parser's required source_name; corrected before source freeze.
No product repair needed after review. One assignment, under3 worker minutes;
remaining rechecks reserved, including final until both hosted authors and CI.
Shared weekly usage17% (launch15%), account-wide and not attributable. Preparing
first PR push; hosted reviews/CI and internal acceptance still pending. Main,
corpus, policy consent, dependencies and CI configuration remain unchanged.

PR516 opened against codex/gettenberg-acquisition at23:00 UTC, source commit
f0cbb30f6d9764aa24211d5c9a69fdf8a9c6369f. Both native records now carry the PR and
source-commit backlinks. This evidence-only follow-up changes no reviewed source,
tests or user docs. First hosted rounds and CI are running; no retrigger.


## Routing run integration and closeout — 2026-10-15 23:07 UTC

[PR516](https://github.com/xenotaur/LCATS/pull/516) merged at23:06:12 UTC into
codex/gettenberg-acquisition as26f3828e7235ea6f388d5a4e2671b88387a16151. Immediately
before merge, fresh base0a4aa7a801318e0ffade7aeb1e8f3f22c9a8e5d1 and final
head49c2cc448b235b182e1dc0014c0e6aa669264ff4 matched the intended target. All4
final-head CI checks passed. Copilot recommended approval with0 findings; Codex
completed with has_any_findings=false and has_unresolved_findings=false. Read
all review bodies, issue comments and threads without recency/outdated filters;
all pagination exhausted,0 threads. No manual hosted retrigger or recheck.

Both hosted reviewers examined source commitf0cbb30f; the later head only added
native PR/commit backlinks and a runlog entry. All seven frozen source/test/doc
hashes matched. After merge, both expected parents and exact accepted-head tree
were verified. Canonical2886-test evidence applies unchanged; no redundant full
suite after evidence-only edits. [Integration evidence](evidence/gettenberg-routing-20261015/integration.json)
records acceptance, CI, hosted coverage, source hashes and remaining limitations.

Run used about23 minutes of its60-minute target/90-minute hard limit, one cold
review assignment under3 worker minutes, peak2 agents including coordinator.
Shared weekly account usage15% at launch,17% before hosted review,19% at closeout;
these observations are not attributable run cost. No extra scope, automatic
renewal, real ebook/archive request or mirror operational probe. Main remains
210468236ff4db78d2d7c5218562fa2d166e6400; watched-skill/consent policy untouched.
Native executions stay in_progress and WI0005 proposed. Operational default-mirror
qualification, consumer/CLI migration and later planned work remain; no whole-WI
completion claim. No active worker remains. This evidence-only integration
checkpoint receives LRH/readiness/diff validation before push.

Process observation: a bounded search of the upstream library's dedicated URL
translation module resolved the alias gap that general mirror documentation had
left open. Cross-checking converter filenames and independently implementing the
finite protocol facts avoided importing upstream code or relying on its apparent
template-key bug. Explicit endpoint roots kept route qualification separate from
live endpoint availability. One coordinator and one compact cold review were
sufficient; the unused budget did not become another work-item grant. Executable
how-to tests and unchanged-source fingerprints allowed the remaining time to be
spent on hosted/CI gates, not repetitive product checks.

## Conservative-cleanup bounded run — 2026-10-16 01:52 UTC

Human explicitly authorized WI-GETTENBERG-0006 under the proposed60-minute
target/90-minute hard stop. Start01:52:46 UTC; target/feature freeze02:52:46;
hard stop03:22:46. Reassess at minute45; no scope expansion or automatic renewal.
Coordinator implements, one cold reviewer planned; max4 total agents,6 assignments,
45 cumulative worker minutes with15 reserved for review, max30 per assignment.
Up to2 same-scope rechecks; reserve final until both hosted authors and CI.
Internal integration permitted after full gates; no main promotion.

Fresh integration base3d55a48767c097aedc800cbad9012cca099f5cd2; main remains
210468236ff4db78d2d7c5218562fa2d166e6400. Child codex/gettenberg-cleanup targets
codex/gettenberg-acquisition. WI0002 dependency canonically resolved by PR508,
main merge35f80fb53c1820ff70708df0ab049266f25dc3c7 verified ancestral. WI0006 ready.
Native prior-art/demand checks apply; no prior execution for minted prompt
PROMPT(WI-GETTENBERG-0006:WI_GETTENBERG_0006_CLEANUP)[2026-10-16T01:54:06+00:00].
Watched skills clean, persistent skip consent invalid and unchanged; explicit
human charter grant governs. Shared weekly usage19% at launch; attribution and
per-run cost unavailable. Same LCATS environment and worktree-bound PYTHONPATH.

Scope: pure text cleanup API, conservative modern/verified historical boundaries,
original-text/offset/version/diagnostic preservation, offline tests, Diataxis docs,
review and evidence. Separate byte decoding; no corpus changes, broad normalization,
CLI/caller migration, dependency/CI change, bulk download, policy change or release.
Audit existing fixtures and upstream primary evidence before choosing marker rules.
Prefer independently authored rules/fixtures; verify attribution before retaining
any external material. Existing headers wrapper and callers remain for the planned
migration item; this run delivers the tested replacement library contract.

Cleanup design checkpoint: inspected existing wrapper/tests, resolved dependency,
and primary modern60600/historical32458 publications. [Contract](gettenberg-cleanup-design.md)
records the pure str/offset API and paired-marker/context safeguards before code.
Historical THIS markers and a corroborated end notice are in scope; broad legacy
substring heuristics are not. Tests will be independently authored, with no copied
upstream code/list or story prose. Keep legacy wrapper/callers for WI0008 migration;
no existing gather-time behavior changes in this library tranche.

Cleanup candidate frozen02:06 UTC:29 focused tests pass in0.122s, all four how-to
blocks execute offline, changed Markdown fences/relative links pass. Immutable
original/offset/marker/diagnostic records preserve LF/CRLF/CR and Unicode; repeated
or malformed boundaries and context failures preserve all text. Regex construction
avoids overlapping trailing-whitespace scans; bounded subprocess tests exercise
a200000-space malformed line and100000 ordinary lines. Source/test/fixture/docs
manifest captured before cold review; no source edits during the initial review.


Cleanup review/repair checkpoint — 02:13 UTC: cold review found a P2 regex overlap
missed by the original stress case, which placed its spaces after the identifier.
Coordinator reproduced 16,000 leading spaces taking 0.763s and 64,000 exceeding a
four-second subprocess limit. This corrects the earlier candidate's incomplete
linear-scan assurance. Disjoint separator/identifier matching fixes starred markers
and the analogous historical notice. Both 200,000-space cases now run in the
bounded regression; coordinator measured the malformed marker at 0.0037s.

Same-scope recheck cleared the repair, with independent checks through 1,024,000
spaces (0.019s marker / 0.017s notice). All seven hashes matched before/after both
review intervals. One review assignment with one recheck, under seven worker
minutes; final recheck remains reserved until both hosted authors and CI.
Canonical repaired source: 2915 tests in 76.825s, format/lint pass, LRH
0 errors/351 existing warnings, readiness/diff pass. All four how-to blocks execute.
An initial format invocation without an option hit the existing Bash empty-array
issue; using supported --quiet succeeded, and canonical --check --diff passed.
No tooling workaround was committed. Shared weekly usage 19% launch, 22% at this
checkpoint; account-wide and not attributable. Preparing the PR; hosted reviews
and CI remain pending, with main/consent/corpus/legacy consumers unchanged.

PR517 opened against codex/gettenberg-acquisition at 02:15 UTC, source commit
53b4a4c073ab1cbbedae1e9eba8e5f156c66e8b9. Both native records now carry PR and source-commit
backlinks. This evidence-only follow-up changes none of the seven frozen files.
First hosted rounds and CI are running; no manual retrigger.


Hosted review repair checkpoint — 02:29 UTC: all four checks passed on f9f0f1f6,
and both first hosted rounds completed. Codex identified a malformed Unicode-space
marker that escaped candidate discovery. Copilot identified single-star outer
markers hiding an inner example and wrapped second-book markers hiding a second
narrative. Coordinator directly reproduced all three: the old result excluded
surrounding/second-book text with envelope_removed. These are valid in-scope
preservation defects, not reasons to weaken the conservative contract.

Candidate discovery now accepts a physical line's starred START/END prefix with
Unicode whitespace, one or more stars, and no requirement for a complete Gutenberg
name on that line. Full removal syntax stays strict. This deliberately increases
safe refusals; the reference documents that a narrative starred heading can cause
a no-op. New regressions cover prefix/body/footer positions, damaged outer/valid
inner pairs, and supported-plus-wrapped books across LF/CRLF/CR. Final repaired
candidate: 2918 canonical tests in 77.525s and 32 focused tests pass;
format/lint/LRH/readiness/diff pass. Source hashes frozen again. Shared weekly
usage near minute30: 23%, account-wide and not attributable (launch19%).
Publishing the repair set; final recheck is reserved until both hosted rounds and
CI are collected, then exact-source independent verification will decide whether
threads can be resolved and integration accepted. No manual hosted retrigger.


## Footer repair and verification grant — 2026-10-16 04:04 UTC

Human explicitly granted repair and verification after the interrupted run.
New bounded window: start 04:04:09 UTC, hard stop 04:34:09 UTC (00:34 EDT).
Scope: repair the verified historical license separator, strengthen fixtures,
canonical qualification, one independent recheck, review-thread disposition and
internal integration if all gates pass. No main promotion or automatic renewal.
Fresh PR517 head e6e19c146139cbe2bdf46613906cea93352b10af and integration base
3d55a48767c097aedc800cbad9012cca099f5cd2 match the clean local checkout.

Backfilled prior-run outcome: final recheck verified all three hosted repairs,
but found a P2 regression: the broadened candidate regex treats the historical
`*** START: FULL LICENSE ***` footer as an unrecognized book boundary. Coordinator
reproduced changed=False/unrecognized_marker and independently confirmed the exact
line in primary publication32458 (line78 in the inspected web rendering), followed
by its full-license heading. No narrative was lost; cleanup was refused. Both
planned rechecks were consumed; interruption crossed the old hard stop before
repair/logging. PR remained open and unaccepted. No extension was inferred.

Repair decision before edits: exclude only that exact observed license-section
separator from book-candidate detection, retaining surrounding horizontal-space
handling. Do not exempt arbitrary START-colon lines or relax book-marker grammar.
Add the separator to both historical fixtures and test retained body/offsets,
near-miss refusal and a missing license-heading refusal. The earlier Unicode,
single-star, wrapped-boundary and performance regressions remain required.

Footer repair qualification — 04:08 UTC: 2919 canonical tests pass in 76.935s,
33 focused tests pass; format/lint/LRH/readiness/diff pass. Both historical fixtures
include the observed separator. Independent recheck under the renewed grant
cleared the exact exception and confirmed earlier malformed-marker protections.
All seven hashes matched before/after review. No source edits during review;
no manual hosted retrigger. Publishing the verified repair; final-head CI and
thread disposition remain before coordinator acceptance.


## Cleanup integration and repair-grant closeout — 2026-10-16 04:13 UTC

[PR517](https://github.com/xenotaur/LCATS/pull/517) merged at 04:12:38 UTC into
codex/gettenberg-acquisition as 2378fccaf0a12d82c0cbb4813d74b8f372e1a9a2.
Fresh base 3d55a48767c097aedc800cbad9012cca099f5cd2 and accepted head
40cd36f036439575b63322acc3a91beee3a244c1 matched immediately before merge.
Both merge parents and exact accepted-head tree were verified afterward; all
seven frozen source/test/fixture/doc hashes match. Canonical 2,919 tests in
76.935s and 33 focused tests pass. All four final-head CI checks succeeded.

Both first hosted rounds were read in full, including outdated threads, without
recency filtering; all pagination exhausted. All three findings were reproduced,
repaired, independently reverified and resolved. The separate historical-footer
regression also received direct reproduction, a narrow fix, strengthened fixtures
and a clean independent recheck under the renewed human grant. No unresolved
P0-P2 finding remains. [Integration evidence](evidence/gettenberg-cleanup-20261016/integration.json)
records exact review bodies, resolved threads, CI, identities and criterion mapping.
No manual hosted retrigger was used. The final evidence-only checkpoint does not
change qualified source and receives LRH/readiness/diff checks instead of another
redundant product-suite run.

This renewed grant has used about 10 minutes of its 30-minute ceiling so far,
one independent recheck under three worker minutes, and peak two agents. No active
worker remains. Account-wide weekly usage observed at closeout: 26%; a new-grant
launch measurement was not captured, so no attributable run cost is claimed.
Watched-skill staleness remains clean; persistent skip consent remains invalid
and unchanged. Explicit human charter/repair authority governed this run.
Main remains 210468236ff4db78d2d7c5218562fa2d166e6400; no main promotion,
corpus/cache rewrite, dependency/CI change, policy restamp or legacy migration.
All three native execution records remain in_progress; WI0006 remains proposed
with staged acceptance. Native terminal closeout waits for human main delivery.

Process findings: the synthetic historical fixtures preserved the paired book
markers but omitted an observed license-section delimiter. Broader malformed-book
candidate detection therefore passed those fixtures while rejecting the real
historical envelope. Preserve complete boundary structure when substituting
synthetic narrative; document known non-book delimiters separately. The prior
final recheck found this interaction and correctly withheld acceptance. Exhausted
recheck allowance plus interruption required one explicit renewal; the narrow
repair and verification then completed without more design expansion. Record
recheck budgets separately from elapsed-time budgets, and retain a specific
resume packet (head/base, finding, reproduction, fixture gap, outstanding gates).

## Preparation run launch — 2026-10-17 01:54 UTC

Human approved the proposed unattended run. Start01:54:42 UTC, target03:54:42,
hard04:54:42. Integration base549383c0a2feb5fb8ab58d9afad7c4732186a225;
main210468236ff4db78d2d7c5218562fa2d166e6400. Clean checkout and fresh origin
confirmed. Branch codex/gettenberg-preparation; parent codex/gettenberg-acquisition.
Prompt PROMPT(WI-GETTENBERG-0007:GETTENBERG_PREPARATION)[2026-10-17T01:57:51+00:00];
idempotence found no existing execution. Prior-art check present in WI.

Preflight: LRH0.2.5.dev3596+gd86755f50, Python3.11.9, Black25.11.0, Ruff0.15.0.
Project environment /Users/centaur/anaconda3/envs/LCATS, PYTHONPATH pinned to
this checkout/src. Backend Codex, session-selected model without override.
Read root/package/tests AGENTS and STYLE; use installed lrh-implement via the
approved coordinator adapter (plan authority/integration base differ from its
ordinary human/main flow). Skill path /Users/centaur/.agents/skills/lrh-implement/SKILL.md,
SHA256 48ac749cb86b8bec8a4a3af931b29d89ff4b207b30ee703bb7d6a5f784111165.
Watched claude/codex gates clean; skip consent invalid and unchanged. Shared
weekly usage27% at launch; per-run tokens/cost unavailable. Managed checkout
requires scoped filesystem escalation; no new authority inferred from it.

Dependency mapping before implementation: WI0004 canonically resolved by PR508
merge35f80fb53c1820ff70708df0ab049266f25dc3c7. WI0005 independently accepted
acquisition/refresh/composition/routing tranches through PR516 merge
26f3828e7235ea6f388d5a4e2671b88387a16151 support explicit SourceRequest,
ResourceStore and CatalogManager composition (evidence directories
gettenberg-refresh/catalog/routing-20261015). WI0006 accepted PR517 merge
2378fccaf0a12d82c0cbb4813d74b8f372e1a9a2, cleanup qualification/integration
JSON,33 focused/2919 canonical tests and independent verification. All three
merge commits are ancestors of this base. WI0005 default operational mirror
remains unqualified; no default source is invented. Native readiness says yes
but is not used as substitute for these staged acceptance mappings.

Coordinator design decision before code: introduce small immutable collection
requirements and a read-only preparation plan; a separate execution operation
rechecks state and requires explicit setup approval. Fixed URL/local collections
need no catalog unless they explicitly request discovery/enrichment. Preparation
never refreshes a ready catalog or replaces outputs. Explicit local archive or
caller-specified archive request/policy only; offline dominates network authority.
Invalid catalog state fails closed. Dry-run returns before mutations or prompts.
CLI catalog setup/status/refresh/rebuild will compose the same operations and
expose explicit source/approval/offline/dry-run controls where implemented.

Gather integration is staged: lazy collection imports and real dry-run planning
first. Current mass_quantities parser uses legacy metadata and text APIs; do not
prepare a new catalog then silently call those APIs. Keep actual legacy gather
execution visibly documented until its consumer migration is qualified. Fix the
second import-time cache path in clean_cli by importing only inside cache clearing.
No extraction/bucket/normalization algorithm changes. Preserve remaining WI0007
criteria explicitly; this run may deliver a qualified subset.

Validation: canonical format/lint/scripts/test, LRH validate/readiness, diff check;
real tiny offline catalog fixtures, subprocess no-side-effect tests, policy and
approval matrices. One independent pre-push review planned; first hosted rounds,
exact-head CI and independent repair verification required before internal merge.
Six assignments and45 worker minutes remain;15 minutes reserved for review.

Preparation checkpoint — 02:31 UTC: implementation and23 focused behavior tests
pass. Real tiny RDF builds, HTTP-boundary acquisition, offline cached archive
reuse, invalid evidence refusal, interactive/unattended/declined setup, explicit
refresh/rebuild/count approval and subprocess pristine CLI checks are covered.
A real selected Sherlock gather produces12 expected story buckets, retains
existing output bytes on rerun, and never imports gutenbergpy. Existing algorithms
and overrides remain unchanged. Canonical validation is running.

Discovery during implementation: CLI plotting imports create a font cache even
when gathering is dry-run. Defer visualization parser/backend loading for direct
gather/catalog dispatch; retain normal visualization/help parsing otherwise.
This is a narrow prerequisite to the no-write guarantee, not a plotting refactor.
First focused failures were fixture mistakes (acquired provenance nests receipt;
patching socket before SSL class initialization breaks its import), corrected
without weakening the product assertions. The argparse refresh source requirement
was moved to the mutually-exclusive group after a direct dispatch caught its
invalid placement. No external requests or corpus changes occurred.

At minute35, shared weekly usage28% (launch27%), unattributable per-run. Full
validation includes time spent initializing the isolated plotting font cache via
the version command. Wall-clock checks include tool waits; budget is unchanged.
Independent-review scope is now frozen except for verified repairs: new planning
and catalog CLI/API, lazy gather imports, clean cache import deferral, tests and
Diataxis docs. Live metadata-dependent gather migration remains explicitly pending.

Pre-push qualification — 02:35 UTC: canonical2942 tests pass in77.120s;23 focused
and independent35 CLI/clean compatibility tests pass. Format278 files unchanged,
lint clean, LRH0errors/351existing warnings, readinessyes, diff clean. Reference
Python example runs in an empty temp directory without writes. Cold reviewer
/preparation_review found no actionable issues; all12 frozen hashes match.
Coordinator inspected the critical authority branches directly. No source changes
during review. Skill lrh-self-review reused through the integration-base adapter;
installed path /Users/centaur/.agents/skills/lrh-self-review/SKILL.md SHA256
 d2cc54ad32989e8c6c598d21a70c9d5b9ce2bfb35e87031caed7606124d5921c.
Review assignment1/6 completed under4 worker minutes;5 assignments and at least41
worker minutes remain (15 reserved). First hosted rounds and final-headCI pending.
A read-only gh lookup hit sandbox networking; one escalated retry succeeded.
No policy/credential modification. PR description corrected to distinguish
completed independent review from pending hosted reviews before publication.

Hosted qualification — 02:39 UTC: all four CI checks passed on68ac68d9; both
first hosted rounds completed. Copilot reported no code issues, with a general
request for final human review of authorization changes. The approved charter
explicitly delegates internal integration review to the coordinator; main approval
remains human and is not inferred from this review. Codex identified one P2:
nested help says cli.py setup rather than lcats catalog setup. Coordinator
reproduced the exact usage line via python -m lcats.cli catalog setup --help.
Fix: give the parent parser its final program name; add behavior regressions
for status/setup/refresh/rebuild help, ensuring no cache writes. Requalify and
use assignment2/6 for independent repair verification. No manual bot retrigger.

Repair qualified — 02:42 UTC:2943 canonical tests pass in71.502s;24 focused
pass; format/lint/LRH/readiness/diff pass. Independent assignment2 verified actual
help for all four operations with correct command prefixes and no files created,
24 focused tests, and all12 repaired hashes. No findings. Only parser program
name and its test changed in product files. Shared weekly usage31% before this
assignment (account-wide, not attributable). Two assignments used, worker occupancy
under7 cumulative minutes conservatively, peak2 agents. No manual hosted retrigger.
Publishing repair and waiting for its exact-headCI before resolving/integrating.

## Preparation run integration — 2026-10-17 02:45 UTC

[PR518](https://github.com/xenotaur/LCATS/pull/518) merged at02:44:52 UTC into
codex/gettenberg-acquisition as fed5030a60e2df42a0827a87d0e412562d865309. Accepted head
4666837158149a1087cf431b66576579a1dc33f8; fresh base549383c0a2feb5fb8ab58d9afad7c4732186a225.
All four exact-headCI checks passed, both first hosted reviews read in full,
all pagination exhausted, and the single P2 help-prefix thread resolved after
direct reproduction, repair and independent re-verification. No manual hosted
retrigger. Merge parents equal base/head, merge tree equals accepted-head tree,
and all12 independently verified product hashes match after fast-forward.
[Integration evidence](evidence/gettenberg-preparation-20261017/integration.json)
contains complete review bodies, threads, checks and criterion mapping.

Canonical2943 tests in71.502s;24 focused tests; independent initial23 focused and
35 compatibility tests; independent repaired24 focused tests all pass. Format,
lint, LRH/readiness and diff checks pass. Evidence-only integration checkpoint
gets LRH/readiness/diff/hash checks, not another redundant product test run.
WI0007 remains proposed with explicit remaining criteria; all3 native records
remain in_progress. Main remains 210468236ff4db78d2d7c5218562fa2d166e6400.
No live Gutenberg acquisition, corpus mutation, dependency removal, CI change,
persistent-consent restamp or main promotion. Watched skills remain clean;
per-clone skip consent remains invalid and unchanged.

Budget: about51 elapsed minutes at this checkpoint against120-minute target /
180-minute hard stop;2 assignments of6 used, peak2 agents, under7 cumulative
worker minutes conservatively. No active reviewer remains. Finish the scoped
tranche early; unused time is not authority to expand the run or start another WI.

Process findings: source-aware first use spans collection requirements, setup
policy and actual consumer access. The legacy parser would bypass a new catalog
setup, so explicit staged delivery prevents claiming a false end-to-end migration.
Import-side-effect subprocess tests revealed both legacy and plotting cache
initialization; ordinary in-process tests could conceal them. The first hosted
review caught a nested argparse program-name issue missed by the cold reviewer;
retain actual help-output tests as part of CLI usability qualification. One
bounded re-verification assignment repaired it without a fresh human grant.
Next coherent slice: migrate the live metadata-dependent gather access and then
wire approval/offline policy through it, preserving selection and normalization.

Final checkpoint — 02:46 UTC: evidence checkpoint1c52b177 published; local
integration checkout clean and synchronized after push. Shared weekly usage32%
at closeout versus27% at launch; this account-wide difference is not an attributed
run cost. Per-run token/cost telemetry remains unavailable. Elapsed about52 minutes;
no worker left active and no automatic continuation scheduled. Final PR description
records completed integration gates and preserves the remaining migration scope.

## Overnight live-gather launch — 2026-10-17 07:57 UTC

Start07:57:23 UTC; target09:57:23; hard10:57:23. Human explicitly approved the
proposed run. Base404c23043af7b9eeb86936a00c32194b8fbb384d clean/freshly fetched;
main210468236ff4db78d2d7c5218562fa2d166e6400. Branch codex/gettenberg-live-gather,
parent codex/gettenberg-acquisition. Prompt
PROMPT(WI-GETTENBERG-0007:GETTENBERG_GATHER_MIGRATION)[2026-10-17T07:58:51+00:00].
Idempotence clear, native readinessyes. Initial LRH status/readiness invoked one
level above package and reported absent configuration; reran from lcats/ and
confirmed watched claude/codex stalenessclean, skip consentinvalid and unchanged.
No false readiness conclusion taken from the first command. LRH unchanged
0.2.5.dev3596+gd86755f50; project Python3.11.9 and PYTHONPATH pinned to this src.
Reuse previously read STYLE, AGENTS, lrh-implement and cold-review procedures via
approved adapter. Skill hashes unchanged: implement48ac749cb86b8bec8a4a3af931b29d89ff4b207b30ee703bb7d6a5f784111165;
self-review d2cc54ad32989e8c6c598d21a70c9d5b9ce2bfb35e87031caed7606124d5921c.
Paths /Users/centaur/.agents/skills/lrh-implement/SKILL.md and lrh-self-review/SKILL.md.
Codex session-selected model, no override. Shared weekly usage32% at launch;
per-run cost/token telemetry unavailable. Filesystem escalation remains required
for this managed checkout; no policy or credential changes authorized.

Dependency mapping: prior WI0004 canonical resolution and WI0005 explicit
acquisition/routing/composition qualification remain valid. PR516 merge26f3828e
and WI0006 cleanup PR517 merge2378fcc are verified ancestors. WI0007 preparation
PR518 mergefed5030a is an ancestor with2943 canonical tests, independent review,
verified help repair, all4CI and resolved threads (preparation integration.json).
These support explicit-source migration; default mirror qualification remains
unaccepted. Six assignments/45 worker minutes remain,15 reserved for review.

Design decisions before code: add a catalog-backed gather source with stable
metadata projection and plain-text-only routable selection, strict decoding,
conservative cleanup and retained provenance. Primary titles and creator/author
roles preserve source order; missing fields skip with a reason, no header fallback
or guessed URL. Ambiguous cleanup refuses extraction while retaining originals.
Keep legacy experimental parser helpers available through local imports; the
migrated CLI path must not import gutenbergpy or initialize its cache. Inject the
new source into the existing gather_story algorithm rather than copy its extraction,
normalization or override logic. Existing outputs are reused; new outputs publish
without replacing a concurrently created file. Record expected metadata/cleanup
behavior differences, not corpus rewrites.

CLI: explicit catalog archive/URL plus explicit main/generated roots; no default
mirror. Missing required setup uses shared approval UI; --yes only setup. --offline
must cover both new resource acquisition and curated HTML caches. Thread an explicit
boolean through curated gatherers/gatherlib/downloaders instead of global policy.
Validate all selections/configuration before initialization; dry-run performs only
local inspection and never imports selected consumers. No per-story prompts,
refresh, output replacement or dependency removal. Tests use authored RDF/text,
HTTP boundary doubles and isolated output/cache roots; no live Gutenberg traffic.
Canonical checks, one cold independent review, hosted first rounds, independently
verified repairs and exact-headCI remain prerequisites to internal integration.

Checkpoint — 08:39 UTC, about42 elapsed minutes:21 authored integration tests
pass, full canonical suite running. No live Gutenberg traffic. Changed cache-dir
plumbing for curated HTML as well as new stores; otherwise mixed offline runs
would depend on an unrelated default cache. Omitted data/cache roots now resolve
at construction, preserving environment overrides after imports. This is a narrow
configuration correction needed by the live consumer tests. New provenance also
records ebook ID and catalog archive hash. Existing output reuse is explicitly
not content validation. Strict decode and ambiguous cleanup failures retain bytes.
No worker assignments used. Clock observations at08:07 and08:38 did not meet the
15-minute checkpoint cadence during the large implementation/test tool interval;
record this instrumentation lapse rather than inventing missing observations.
Remaining target about78 minutes, hard allowance138; scope unchanged.

Checkpoint — 08:43 UTC: canonical2964 tests passed in77.873 seconds before review.
Cold review assignment1 dispatched about08:41–08:42,15-minute allowance from45.
Usage35% used versus32% launch (shared, not attributable). Review snapshot diff
SHA25679138f8f6d5018d06d14e034858c4dc85e6b2ac2765ed708d83c99877d2e215d.
Reviewer found CRLF/CR incompatibility at the decoder-to-extractor boundary.
Coordinator independently reproduced real authored runs: LF/CRLF/CR all returned
success but wrote1/0/0 stories. Legacy header stripping normalized newlines; the
new byte/decoder/cleanup APIs correctly preserve them. Repair normalizes only
at heuristic extractor handoff, with original-byte and body-preservation cases.
Also adds online first-use archive+story acquisition composition coverage through
a stubbed HTTP boundary, addressing the previously offline-heavy matrix.
Earlier review freeze attempt used LRH's suggested filename rather than actual
record-execution output filename; git add failed and produced an empty diff. It
was detected before dispatch, corrected with actual path and nonempty hash.
Future orchestration should consume returned artifact paths and stop on failure.

Checkpoint — 08:46:23 UTC (about49 elapsed minutes): cold review and separately
budgeted repair verification complete. Reviewer independently confirmed LF, CRLF,
CR and mixed-line-ending extraction and byte/decoded/cleanup/provenance invariants.
No remaining findings. Charged4 minutes each conservatively:2/6 assignments,8/45
worker minutes,37 remain; no worker active. Canonical2966 tests77.335s, focused23,
format/lint and diff checks pass; LRH0errors/351warnings (same as prior tranche).
Actual CLI help and empty-directory offline planning verified;64 relative doc
links valid. Freeze product source and proceed to first hosted review/CI rounds.
Scope remains explicit-source live gathering; no main promotion or dependency
removal. Review repair is one successful cycle, no design replan required.

PR519 opened08:47 UTC against codex/gettenberg-acquisition at initial product
commit546f03de188819e57625e08e227840eccdf24f36. Native primary and self-review
records are linked and in_progress. One read-only GitHub lookup failed in the
restricted network context; exact retry under approved network access succeeded.
No mutation was blindly retried. First hosted review andCI rounds pending.

## Overnight live-gather acceptance — 2026-10-17 08:53 UTC

PR519 internally merged08:52:40 UTC at ba4b137b721b71a23f13395f49cf4585e6861bce;
accepted head 461d845ea29c5e72485071338647ed1d5596a385. First Codex review completed
without findings; Copilot reported no code issues and a general human/pending-gates
caution. Fresh exact-headCI now passes all4 checks. Coordinator accepts internal
integration under the existing human charter; this is not new human main approval.
All review/comment/thread pages read, none unresolved. Both bots reviewed product
head546f03de; later461d845e only adds control-plane evidence/links. All32 source/
test/doc hashes match the reviewed and locally validated product. Fresh base404c2304
verified before merge; parents[base,head] and tree==head verified after.

Canonical2966 tests77.335s; migration23; independent reviewer182 before repair and
184 after; format/lint/LRH0errors351warnings/readinessyes/diffchecks pass. Both
hosted first rounds are preserved with exact-headCI evidence. One successful
repair cycle,2 assignments and8 conservatively charged worker minutes, peak2
agents. No active worker, no live Gutenberg download, no main/corpus/dependency
changes. Shared weekly usage39% used at08:53 versus32% launch; not an attributed
run cost. Target09:57:23/hard10:57:23 remain unexhausted; scope completion ends
this grant early. Remaining: operational default-source qualification and WI0008
legacy/dependency migration, then human main promotion and native closeout.

Process learning: boundary-preserving components can break legacy consumer
assumptions; CRLF/CR fixture equivalence caught a false-success exclusion that
2964 green tests did not cover. Keep an independent end-to-end reviewer and
reserve a repair-verification assignment. Compact-context review plus a specific
repair recheck sufficed; no additional implementation workers were needed.
Record-execution output filenames must be consumed, not reconstructed from label
suggestions. Gate scripts should stop on command failure and store raw validation
output as JSON: ignored .log files and trailing blank lines in raw .txt evidence
otherwise interrupt publication without affecting product correctness. A tools-
version report initially omitted PYTHONPATH and inspected another editable checkout;
rerun with this worktree pinned. All actual tests used the pinned worktree.
First product/evidence commit messages omitted prompt ID; PR and native records
carry it, and the final checkpoint commit includes it without rewriting history.
CI/review evidence-only tails should be recognized by verified source hashes to
avoid unnecessary hosted retriggers while still requiring exact-current-headCI.
No process change is implemented in LRH by this experiment.

## Default-source qualification sprint — 2026-10-17 15:16 UTC

Human grant: 15-minute target / 20-minute hard maximum. Start 15:16:23; target 15:31:23; hard 15:36:23.
Base c167d74cfef5ae2d51b6c28b4c24e0d5ddc44833 freshly fetched and clean;
origin/main 210468236ff4db78d2d7c5218562fa2d166e6400. Research branch
codex/gettenberg-default-source-qualification. WI0007 readiness yes; watched
gates fresh, persistent skip consent invalid and unchanged. Shared usage 39%
used at launch. Prior PR #519 staged migration is an ancestor. Scope: separately
bounded operational check required by prior route qualification, not redoing
its proven offline mapping. Default candidate remains listed PGLAF combined
mirror; archive independent. One optional cold reviewer, four minutes maximum.
Prompt PROMPT(WI-GETTENBERG-0007:GETTENBERG_DEFAULT_ROUTE_PROBE)[2026-10-17T15:16:57+00:00].
Public robot, mirror list, mirroring and offline-catalog pages re-read; catalog
and mirror access are the documented automation routes. No human-site ebook
crawl or archive body download. Probe bounds recorded before access in charter.

### Endpoint decision and review — 2026-10-17 15:25 UTC

Six requests completed: archive/main/generated HEAD 200, robots 404 (missing
file, not a permission inference), main/generated prefix GET 206. Total bodies
8354 bytes; no archive payload. Recommend the official archive with the listed
PGLAF combined mirror for the next default-profile implementation. Keep main and
generated identities separate: observed sizes and prefix hashes differ.

Evidence JSON and the qualification memo retain the decision, exact probe inputs,
headers, bounded transfer metrics and next fixture/CLI work. No product defaults
or source changed. Coordinator checks passed for counts, body bounds/hashes,
TLS/redirect/time constraints and project-only scope. LRH validation: zero errors,
351 existing warnings; diff whitespace check passed.

Cold independent review: one assignment, two conservatively charged worker
minutes, peak two agents, no substantive findings. The reviewer confirmed local
probe and code evidence; linked policy summaries were not independently re-fetched.
Coordinator separately checked body evidence, routing source and both archive
limits. Review frozen-diff digest and limitations are in the side execution record.
Shared usage at pre-review checkpoint: 40% used versus 39% launch; this is an
account-wide observation, not attributed sprint cost.

Process finding: a short run can close an endpoint decision with six tiny probes
and a precise implementation handoff. Keep endpoint reachability, transport-client
qualification and full-catalog validation distinct; do not spend a short sprint's
budget on a large download or infer byte equivalence from common ebook IDs.
Research PR is a nonterminal checkpoint; hosted gates and integration may follow
in a separate grant. No automatic continuation, main promotion or WI closeout.

Research PR: [#520](https://github.com/xenotaur/LCATS/pull/520), targeting
`codex/gettenberg-acquisition`; research commit `eb428a73`. Native primary/side
records link to the PR and retain nonterminal status. Published at approximately
15:26 UTC, ten minutes into the grant. Final checkpoint awaits only a compact
hosted-state read; no product implementation begins in this sprint.

Final hosted snapshot at approximately 15:27 UTC: PR #520 open at `b061849f`,
first hosted review still running on research commit `eb428a73`; lint passed,
test/coverage jobs still running. No review acceptance or integration is claimed.
The final evidence-only checkpoint records that snapshot; its own CI will run
normally. Working tree was clean before this log update. Grant ends after this
checkpoint push, approximately eleven minutes elapsed, within the 15-minute
target. Next action: review/integrate #520, then implement the scoped default
profile under a new grant. No workers remain active.

## Endpoint integration sprint — 2026-10-17 17:28 UTC

Human grant: next sprint to review/integrate #520; 15-minute target, 20-minute
hard maximum. Start 17:27:56 UTC, target 17:42:56, hard stop 17:47:56. PR head
`5ca898780e92863ac98abf920ec808b66909eb8e`; fetched integration base
`c167d74cfef5ae2d51b6c28b4c24e0d5ddc44833`; main remains `210468236f`.
Gate definitions fresh; persistent skip consent invalid and unchanged. Explicit
run authority and approved coordinator adapter govern internal integration.
LRH version 0.2.5.dev3596+gd86755f50; loaded lrh-land, lrh-review-response and
lrh-confirm-fixes procedures reused under that adapter. Shared usage 41% used;
per-run credit/token attribution unavailable. One optional four-minute cold
review assignment; no implementation workers or live Gutenberg requests.

First hosted rounds landed: Codex found P2 missing retained response bytes;
Copilot found a spacing typo. Both are present, valid and feasible. Preserve
original temporary GET samples, verify against existing lengths/hashes, and
encode bytes in JSON to retain CRLF/truncated lines without text normalization.
No new source bytes are acquired or substituted. Prior exact-head CI passed all
four checks; post-repair CI and review must qualify the revised candidate.

### Review repair and verification — 17:31 UTC

Pushed repair `0147de2f`. All three base64-decoded original samples reproduce
recorded SHA-256/length values; GET bodies total 8354 bytes. Both hosted comments
are Clear-satisfied. Copilot thread was already resolved on fresh read; the
coordinator resolved only the remaining Codex thread after the one-thread routine
gate passed. No reviewer finding is dismissed or deferred. This confirmation
checkpoint will receive a cold PR-mode review and exact-head CI before merge.
No local Python format/lint/product test rerun for data/docs-only changes; those
checks are covered by required current-head hosted CI, not claimed as local runs.

### Accepted internal integration — 2026-10-17 17:37 UTC

PR [#520](https://github.com/xenotaur/LCATS/pull/520) merged into
`codex/gettenberg-acquisition` at `eb4888e950c34130ade25f833f968047c9562525`.
Accepted head `1dcdd77147e4994c936d2db737f6f369c5ec5920`; fresh base
`c167d74cfef5ae2d51b6c28b4c24e0d5ddc44833`. SHA-locked merge verified via PR
state, exact parent pair and merge tree equality. Both hosted threads resolved;
one cold current-head substitute review found no substantive issues; all four
exact-head CI checks passed. Local LRH validation: 0 errors, 351 existing warnings.
Data/docs-only scope; no new local product-test pass claimed.

Acceptance-to-evidence mapping: retained-byte criterion is covered by matching
original lengths/hashes and reviewer byte equality; policy/endpoint recommendation
is covered by dated probe metadata plus explicit limits; review and CI gates are
covered by [integration receipts](evidence/gettenberg-default-source-20261017/integration.json).
Independent reviewer encountered a later GitHub connectivity failure while reading
CI; coordinator verified CI separately. No exception was taken on acceptance.

One repair cycle, one assignment, two conservatively charged worker minutes,
peak two agents. No worker remains active. Shared usage 41% at launch and 43%
at checkpoint; account-wide values are not attributed sprint cost. Approximately
ten minutes elapsed, finishing before target; no renewal or scope expansion.
Native statuses remain nonterminal. No new Gutenberg requests, product defaults,
main promotion, corpus mutation, dependency change or persistent consent update.

Process learning: a hash demonstrates identity only when original sample bytes
remain available for audit. Retain small bounded samples with explicit encoding
and hashes in the first research checkpoint. Base64 avoids accidental CRLF or
truncated-line normalization in text tooling. Validate decoded bytes, not encoded
text. A cold reviewer checked the repaired evidence; CI ran on the unchanged
reviewed head while the coordinator waited. Final acceptance bookkeeping is
recorded after merge to avoid an endless review/evidence-commit cycle.

Next grant: implement the documented overridable default-source profile at the
CLI/preparation boundary, including smart setup approval, offline behavior,
curated-only isolation, fixture coverage and user documentation. This integration
sprint does not authorize that implementation automatically.

## Default-profile implementation sprint — 2026-10-17 19:32 UTC

Human approved 20-minute target / 30-minute hard maximum. Start 19:32:25;
target 19:52:25; hard stop 20:02:25; feature freeze 19:47:25. Fetched clean
integration base d9ca9d184ebd5ebf8a195ffd364bf87817a37292 includes qualified
PR #520 merge eb4888e9; earlier WI0007 preparation/live-gather acceptances are
ancestors. WI readiness yes; prior-art check present in WI. Branch
codex/gettenberg-default-profile; prompt
PROMPT(WI-GETTENBERG-0007:GETTENBERG_DEFAULT_PROFILE)[2026-10-17T19:32:41+00:00].
LRH implementation/self-review procedures reused under the approved adapter.
Gate definitions fresh; persistent skip consent invalid and unchanged. Usage
43% used at launch, account-wide only. No live acquisition is authorized.

Plan: one shared CLI source resolver; library preparation/routes remain explicit.
Missing source selects official catalog; neither root selects the qualified
PGLAF pair; half override fails. Explicit local archive suppresses default URL;
archive and resource configuration remain independent. Setup approval and offline
policy are unchanged; curated-only selection never resolves catalog defaults.
Dry-run exposes URLs and permitted origins without I/O. Preserve refresh/rebuild
explicit authority. Add HTTP-boundary fixture coverage, canonical checks,
Diataxis updates and one cold review; native records remain nonterminal.

### Local qualification — 19:39 UTC

Canonical suite: 2978 tests passed in 86.153 seconds. Focused preparation/live/default
suite: 59 passed. Black checked 284 files; Ruff and format passed. LRH validation
0 errors, 351 existing warnings; WI readiness yes. Python 3.11.9 / Black 25.11.0 /
Ruff 0.15.0, PATH pinned to LCATS env and PYTHONPATH to this worktree's src.
Documented gather/setup previews report identical default archive, exact roots,
origin authority and approval; neither creates the pristine cache. No live traffic.

One cold diff review dispatched at about 19:39, max six minutes, frozen diff
3830364a6544cae8107cb005d730a9426b282274495a17a462db0a4f7d68cae3.
Shared usage at dispatch checkpoint 45% used; not attributed run cost.
Scope frozen pending review. Validation commands/stdout and product hashes are
retained in evidence/gettenberg-default-profile-20261017/qualification.json.

Tooling friction: this checkout's scripts/test forwards --log to unittest, which
rejects it. Canonical scripts/test with shell log capture passed. The formatter's
empty option array fails under the host shell when paths are supplied without
options; scripts/format --quiet -- <changed paths> succeeds. No LRH or wrapper
repair is included in this product slice. Future workflow adapters should discover
supported wrapper arguments instead of assuming bundled skill examples apply.

### Independent review — 19:40 UTC

Cold reviewer found no actionable defects and independently ran 59 focused tests
in 3.902 seconds. One assignment, two conservatively charged worker minutes;
no repairs or expanded scope. Coordinator has independent canonical/CLI evidence;
no top defect to reproduce. All-collection selection is tested as dry-run and
representative mixed execution, not full execution of every built-in collection.
No archive/client live qualification is claimed. Proceed to first hosted review
and exact-head CI; no internal acceptance before those gates pass.

Implementation PR [#521](https://github.com/xenotaur/LCATS/pull/521) opened against
codex/gettenberg-acquisition at about 19:41 UTC. Product commit dca61929; native
primary and self-review records linked to the PR. This bookkeeping tail changes
no reviewed source/test/docs. Await first hosted reviews and exact-current-head CI.

### Staged acceptance and completion — 2026-10-17 19:47 UTC

PR [#521](https://github.com/xenotaur/LCATS/pull/521) internally merged at
`94c6d8e789fbb394ac4c7823b7e77b5208f40d74`. Accepted head
`b9bfc0927c77fc1ac29bb748d80ad8b4cedba7e8`, freshly checked base
`d9ca9d184ebd5ebf8a195ffd364bf87817a37292`. SHA-locked command confirmed
MERGED; parent pair and tree==accepted-head verified. Both first hosted reviews
clean; Copilot's earlier coverage-pending note superseded by final success. All
four exact-head CI checks pass. No unresolved threads; empty routine gate passed.

Canonical 2978 tests/59 focused, independent review, CLI previews, format/lint,
LRH 0 errors/351 warnings, readiness and source hashes establish staged acceptance.
Product head dca61929 is unchanged through the PR-linkage tail. Full receipts and
acceptance mapping are in evidence/gettenberg-default-profile-20261017/ and the
WI0007 staged acceptance section. Native statuses remain nonterminal.

One assignment, two conservatively charged worker minutes, peak two agents,
zero product repair cycles and no active workers. Approximately fifteen minutes
elapsed, finishing before the 20-minute target/30-minute hard limit. Shared usage
43% launch, 45% review checkpoint, 47% final; no attributable per-run cost meter.
No live Gutenberg requests, corpus rewrite, dependency removal, main promotion,
persistent consent update, scope expansion or automatic continuation.

Process findings: a qualified endpoint decision and explicit lower-level APIs
made default selection a small CLI change. Existing authored end-to-end fixtures
provided realistic cache/approval/publication coverage without live downloads.
One compact cold review and unchanged-source hosted acceptance were sufficient;
no implementation workers or second review assignment were needed. Wrapper
capability detection remains an LRH follow-up; do not patch unrelated harness
commands during a bounded feature run. Post-merge evidence avoids another product
review cycle while preserving exact accepted head/base/CI and nonterminal lifecycle.

Next bounded task: WI0008 legacy-consumer/dependency migration, starting from a
fresh inventory of remaining gutenbergpy usage. Full live-client/archive and corpus
qualification remain separately bounded; eventual main promotion is human-gated.

## WI0008 caller migration run — 2026-10-17 20:18 UTC

Human granted two-hour target / three-hour maximum. Start20:18:59 UTC; feature
freeze22:18:59; hard stop23:18:59. Fresh base003c2e08523c9360fdda3a2bfd69b42505c4c51f,
main210468236ff4db78d2d7c5218562fa2d166e6400; branch codex/gettenberg-migration.
WI readiness yes; no prior matching execution; prompt minted before implementation.
WI0003 resolved on main via #508/35f80fb5; WI0007 staged via #518/#519/#521,
latest accepted head b9bfc092 and merge94c6d8e7 with 2978 canonical tests,
59 focused tests, cold review and four CI checks. Both dependency commits are
verified ancestors of this base. See WI0007's acceptance mapping and
evidence/gettenberg-default-profile-20261017/{qualification,integration}.json.
Gate definitions fresh; persistent skip consent invalid and unchanged. Explicit
run grant governs the approved coordinator adapter. Shared usage47% used at
launch; no attributable per-run cost meter. LRH0.2.5.dev3596+gd86755f50.

Plan: remove obsolete api/cache/headers/SQL adapters after migrating real callers,
retain the supported catalog/resource/cleanup interfaces; require explicit source
for programmatic gathering. Migrate genre and read-only experiment access, preserve
classification rules and historical outputs. Replace duplicated notebook behavior
with tested libraries; archive upstream-internal diagnostics with historical-revision
instructions. Unit tests and wheel smoke checks remain offline; dependency package
installation may use the package index but no Gutenberg downloads are authorized.
No CI edits; note cache-maintenance workflow migration for WI0009. Existing prior
art/demand check remains applicable: reuse gatherers, reconciliation, catalog; link
WI-RELEASE-0037 evidence without resolving it.

### First implementation checkpoint — 20:34 UTC

One disjoint experiment assignment returned in about four minutes (charge five
worker minutes). Scope remained WI0008; no additional item. Existing catalog,
resource and cleanup contracts made the active consumer changes small; most diff
volume is removed wrappers/mock tests, thin notebook replacements and byte-identical
archive moves. Keep one coherent dependency-removal PR with a surface-by-surface
ledger rather than temporary compatibility APIs. No CI files or historical outputs
changed. New library work is URL identity parsing, shared structured story inspection
and source-group reconciliation; existing extraction/genre rules remain in use.

Canonical scripts/test: 2907 tests passed in77.489s; format281 files and lint pass.
The count falls because72 old wrapper-contract tests and obsolete debug/API mocks
were retired, with replacement behavior coverage mapped in gettenberg-migration.md.
174 focused migration checks passed before the three notebook/client checks were
added; those three passed separately and are in the final canonical count.
Experiment suite60 tests passed. All five before/after authored fixture cases match
result and story JSON; no whole-corpus equivalence claim. Static scan402 Python/
notebook surfaces: no active upstream imports; archived notebooks' bytes match Git.

Fresh temporary venv installation resolved current declared dependencies without
gutenbergpy. Initial wheel smoke passes outside checkout with no PYTHONPATH,
including catalog setup/query, genre, cleanup, source inspection, package data and
CLI previews. Rebuilding the frozen final source before accepting that evidence.
Usage50% used at checkpoint, shared account-wide, not attributable run cost.

Routine repairs: one unused test import; tutorial tar writer initially emitted PAX
metadata rejected by the bounded ingest contract (fixed to explicit USTAR); the
historical probe's top-level legacy imports broke its help/import test (moved
behind explicit measurement, preserving unsupported historical runtime boundary).
An initial no-build-isolation wheel attempt exposed the shared environment's old
packaging license parser; standard isolated PEP517 build succeeds without changing
the shared environment. One test command was initially run from repository root
instead of lcats/ and was immediately corrected; no product diagnosis inferred.

Product code/docs frozen for one cold independent review at about20:35 UTC.
Assignment2of6; up to15 worker minutes, 40 remaining before dispatch. Full diff
SHA25649976c018d4c94e5b5f02ab63de090f55cf575ab5b17f088a431c7b1b70ff0b0.
Native evidence records are being completed while code remains frozen.

### Review repair checkpoint — 20:41 UTC

Cold review found one real P2: strict source identity parsing rejected48 nested
HTML source URLs in existing O. Henry/Sherlock/Chesterton collections. Coordinator
reproduced it, widened only the official /files/<id>/ resource path shape and
added regression tests using those exact shapes. Host checks remain. A read-only
scan now accepts all1868 Gutenberg story URLs; reviewer independently confirmed.
The new notebook test's Python3.11-only cwd helper was also replaced; no claim of
a full Python3.10 environment run. Seven repair tests pass. Repair review reports
no remaining P0–P2. Three assignments,13 conservatively charged worker minutes,
peak two agents, one product repair cycle; no additional worker planned.

The baseline explicitly scopes WI0008's output comparison to side-by-side fixture
corpus/gathering. Five authored cases plus actual corpus identity coverage satisfy
that bounded migration check; broader live/full-snapshot content qualification is
still WI0010. The reviewer finding demonstrates that fixtures alone miss real
source shapes, so retain both the static corpus scan and authored behavior tests.

Final rebuilt wheel matches every packaged Python source and omits retired
modules/dependency. Fresh venv smoke and pip check pass outside checkout; no
PYTHONPATH, no gutenbergpy, no Gutenberg network. Full canonical rerun is pending.
Usage tool now reports0% weekly used after earlier47–50%; this is a changed
account snapshot, not evidence of negative or zero run cost. Do not infer an
attributable usage delta across these snapshots.

Final local rerun:2908 tests passed76.833s; format281 files, lint and LRH0errors/
351existingwarnings pass. WI readiness yes; diff check clean. Final wheel164
Python source entries match exactly; all seven repair/client tests pass. An
unbound tools-version command briefly reported the shared base environment;
repeated with the same LCATS PATH/PYTHONPATH used for all product checks. No
validation claim relies on that unbound version output. Ready for first push.

Internal PR#522 opened at product head3ed49415b900fa8bec825acf453272105860c6c0,
target codex/gettenberg-acquisition. PR-linkage/evidence tail changes no product
source. Awaiting first automatic hosted review and exact-head CI; no retrigger.

### Hosted CI hygiene repair — 20:45 UTC

Initial lint job39067928164 failed its additional nbstripout --verify step on the
three rewritten notebooks. Local canonical format/lint do not include this check.
nbstripout0.9.1 normalized only cell IDs and JSON key ordering; all cell source
hashes are unchanged. Full notebook verify and three client tests pass. No CI
configuration or archived notebooks changed. Record this as a second repair cycle
(hygiene), not a product behavior change; local2908-test result and wheel remain
applicable. Future notebook assignments should inspect workflow-only hygiene
checks before first push. Automatic first hosted review is still running.

### Late hosted review repair — 20:51 UTC

All four checks passed at b923a875 and hosted Codex completed clean on product
3ed49415. Exact-head substitute review independently passed178 focused and60
experiment tests, five comparisons, corpus identities, wheel/source/archive
hashes and notebook normalization. Assignment4 charge three worker minutes;
aggregate16/45. No merge occurred yet.

Copilot's first review then identified a real medium issue: invalid corpus paths
in KMo/genre.py returned successful empty counts. Coordinator reproduced missing
and file paths using a real catalog, then added CLI directory validation and
subprocess regressions preserving valid empty-directory behavior. This third
repair cycle is in scope; no change to generic Corpora or packaged library.
Four focused client tests pass; canonical rerun and bounded independent recheck
follow. This illustrates the value of waiting for both already-running first
hosted reviews even after one clean response and an independent clean pass.

Post-Copilot canonical result: Ran 2909 tests in 78.228s, OK. Format/lint and LRH0errors/351warnings pass.

### Integrated outcome and process findings — 20:57 UTC

PR #522 merged into codex/gettenberg-acquisition at46960f66 after final accepted
head858f6da2 passed all four CI checks. Both first hosted reviews completed;
Copilot's finding was independently reproduced, repaired, reverified and resolved.
SHA-locked merge parent pair and exact accepted tree were verified. Post-merge
checkpoint changes only control-plane evidence and links; native records stay
in_progress and WI0008 stays proposed pending human-approved main promotion.

The run finishes early, about40 minutes after20:18:59 start, because the scoped
acceptance is met. Five of six assignments,18 conservatively charged worker
minutes of45, peak two agents; three repair cycles (URL behavior, notebook hygiene,
CLI input handling). No active worker remains. Shared usage snapshots changed
47→50→0→3 percent during the run, so no defensible attributable weekly percentage
is reported. Per-run credit/token cost is unavailable. No automatic continuation.

What helped: a mature internal catalog/source API made dependency removal mostly
consumer simplification; disjoint experiment work plus targeted independent review
provided useful concurrency without broad delegation. Real-corpus identity scans
caught a fixture gap. Keep local fixture comparisons separate from full-corpus
claims. Inspect workflow-only notebook hygiene before opening future PRs. Waiting
for both already-running hosted reviews found a valid CLI boundary issue that the
local reviews missed. Use an independent targeted repair check rather than another
whole implementation pass; preserve exact-head CI and authoritative thread reads.

Next scoped item: WI0009, supported CI cache maintenance. Broader live/full-catalog
and corpus qualification remains WI0010; no such download was performed here.
A future main promotion remains human-gated. WI-RELEASE-0037 receives evidence,
not automatic closure. The current worktree remains on the integration branch.


## WI0009 CI-maintenance run — 2026-10-17 17:52 Pacific

Grant: two-hour target/three-hour maximum, UTC00:52:10–02:52:10–03:52:10 on
October18. Base0504cae5; main21046823; branch codex/gettenberg-ci-maintenance.
Readiness yes, no matching prior execution. Prompt minted before implementation.
WI0004 resolved on main35f80fb5; WI0007 independently staged at94c6d8e7; both
verified ancestors. WI0008 also staged46960f66. Existing LRH coordinator adapter
continues, native lifecycle nonterminal. Gate definitions fresh; persistent skip
consent invalid and untouched. Launch account usage4%; per-run cost unavailable.

Prior art: replace existing cache_maintenance workflow, reuse catalog_cli,
resources and lifecycle; no duplicate downloader. No sibling consumer identified.
Existing WI0009 owns this CI work; related migration/release records receive links,
not automatic closeout. Official gh cache list/delete documentation confirms JSON
IDs/key/ref and deletion by ID. Actions cache documentation confirms immutable
keys, prefix fallback to newest compatible entries and current/default branch
visibility; use explicit namespace/ref checks rather than table parsing.

Implementation plan: remove Gutenberg restore/save from ordinary test/coverage
jobs while keeping triggers, check names and canonical commands. A manual workflow
defaults to preview; setup/rebuild/refresh invoke supported catalog commands and
propagate failures. A tested dev helper supplies compatibility/input cache keys,
structured deletion plans and explicit apply operations. Separate source-resource
and derived-catalog caches preserve archive reuse across parser/schema changes.
Catalog restore fallback never crosses compatibility boundaries. Keys include
source profile, parser/schema, implementation fingerprint and activated archive
hash, plus run identity for immutable snapshots. Deletion uses a fixed namespace,
fully paginated JSON, exact ref and numeric cache IDs. No delete/download is run
against production during this task; tests use real local archives plus process/
HTTP boundary fakes. Include workflow structure/command failure checks and docs.

Validation: canonical tools/format/lint/test, notebook verify if relevant,
LRH/readiness/diff, real fixture maintenance and key tests, command subprocess
failure tests, independent cold review, first hosted reviews and exact-head CI.
No CI trigger/check weakening, corpus changes, package publication, new items,
main promotion or persistent policy update. Use established shell log redirection
because the local scripts/test wrapper does not implement LRH's generic --log.

### Implementation checkpoint — 01:08 UTC

Sixteen focused tests pass. They exercise actual tiny archive/catalog behavior,
resource-only offline bootstrap after copying partitions, count-change guarding,
workflow bash execution with success/error exits, exact-ref/prefix pagination,
partial deletion reporting and failed-save verification. Only HTTP/process
boundaries are substituted. Canonical suite is running; final rerun will qualify
the frozen revision. Format284 files and lint pass. LRH has0errors/351warnings.

Initial local failures exposed an overbroad repo-name pattern and the mistaken
assumption that resources lived directly under cache root. Fixed both. Actual
layout shares gettenberg/archives between acquisition and lifecycle; source cache
now holds resources+archives, catalog cache only active.json+generations. This
avoids duplicate archive storage and allows parser/schema misses to reuse bytes.
A save-verification read catches warning-only upload failures; missing expected
keys fail the applied job. No new linting tool or dependency was introduced.

Read-only live GitHub metadata preview found two main-ref legacy caches, selected
numeric IDs, and deleted none. Documented catalog setup preview creates no cache.
All11 workflow shell steps parse with bash -n; JSON/YAML structural tests preserve
ordinary check names/triggers. A full live maintenance rehearsal remains unrun.

Cold independent review dispatched at about01:09 UTC, assignment1/6, maximum15
worker minutes. Product/docs/workflows frozen at full diff SHA256
3c99e2902c89cdf1572d597f55e5e105e7e2780c256be9ce129c9d1f421b94b4.
Coordinator owns implementation; no implementation worker was needed because
workflow and helper interfaces are tightly coupled. Shared usage6% at review
checkpoint versus4% launch; account-wide, not attributable per-run consumption.


### Review timing and validation correction — 01:54 UTC

The first reviewer stopped at01:30:02, after its01:25 assignment deadline.
Charge22 worker minutes conservatively (planned15), including the overrun.
It completed useful product checks and16 focused tests, but explicitly reported
partial review rather than acceptance. The clock advanced unexpectedly between
observations; the cause is unverified. A prompt deadline alone did not enforce
the limit. Future orchestration should provide an external cancellable timer.
The overall hard stop remains03:52:10; no automatic extension is inferred.

Assignment2 continues the same frozen product review from01:53:05 to02:00:05
maximum (seven minutes), covering remaining workflow/action/docs semantics.
After reserving this continuation,16 worker minutes remain of45. Shared usage7%.
No product edits occurred during either review assignment.

Correction: the final suite passed2925 tests in85.804s, but inspection of the
actual final-format log found one file requiring Black after two late edits.
The earlier commentary claiming all final checks passed was inaccurate. Preserve
that failure in the evidence and rerun format/lint after applying Black. The
original16-test and full-suite results remain valid test evidence, not formatting
evidence. No validation failure is waived.


### Local acceptance — 01:56 UTC

Independent continuation completed by01:56, charged3 minutes; total25/45 worker
minutes,2/6 assignments, peak two agents. No behavioral findings. Its P2 formatting
finding matched the coordinator's directly inspected failure. Applied Black only;
AST comparison against the frozen source passed. Canonical format/lint and16
focused tests now exit0. Full canonical suite2925/85.804s remains the behavioral
qualification; no behavior changed after it. Local receipts preserve the earlier
format failure separately. All product/docs review limits remain explicit.

Internal base still0504cae5. No required-status-check rules are configured on
that branch, so CI fallback will require every reported check and treat empty
results as pending. Gate definitions are fresh; persistent consent remains
invalid and unchanged. Proceed to first hosted reviews and exact-head CI.

Internal PR [#523](https://github.com/xenotaur/LCATS/pull/523) opened at implementation
commita8416d3b. PR links backfilled in primary/self-review records. Hosted review
and exact-head CI pending; no main promotion or live maintenance is authorized.


### Hosted workflow rejection and repair — 01:59 UTC

The generic LRH CI predicate reported green atff78d679 because only lint existed
in the PR check rollup. Expected test/coverage checks were absent. A separate
workflow-run inventory exposed three failed workflow-file runs before job start:
39088343004 (coverage),39088343448 (tests),39088343856 (maintenance). This is not
acceptance: job-level env used runner.temp, a context GitHub disallows there.
Verified against the official context-availability table; YAML parsing, bash -n
and the prior cold review missed it.

Replace these roots with github.workspace/.lcats-* (available at job evaluation),
and add a regression check of allowed job-env expression contexts across all
three workflows. No new lint tool or dependency introduced. Require the expected
check inventory AND absence of failed validation runs on the final SHA, not just
a nonempty all-green check rollup. This is an LRH predicate improvement candidate.
No maintenance workflow is dispatched; checking its hosted syntax has no catalog
or cache mutation effects. Independent targeted repair review remains required.


### First hosted reviews and runtime identity repair — 02:03 UTC

Both first hosted reviews completed: Codex on a8416d3b found P2 dependency identity;
Copilot on ff78d679 reported no open issues and noted the live-operation boundary.
Coordinator verified lxml>=5.2.2 in pyproject and etree usage in rdf.py, confirming
that code-only hashing could reuse a catalog across a dependency upgrade. Include
Python/SQLite/lxml and runtime/compiled libxml versions in the catalog fingerprint.
A regression test changes external parser version metadata while leaving code and
explicit schema/parser versions fixed; source identity must remain unchanged.

Workflow repair independently accepted in assignment3, charged3 minutes, total
28/45 worker minutes and3/6 assignments. The reviewer reproduced all three old
context failures and checked44 location-specific expressions; it acknowledged
its prior context-location gap. Canonical workflow-repair suite2926/87.491s,
format/lint and LRH0errors/351warnings pass. Runtime repair validation follows.

Runtime repair canonical suite passed2927 tests in92.126s;18 focused tests, lint
and LRH0errors/351warnings pass. Ready to push both repairs and verify the final
head independently. No product changes are planned during that review.


### Exact-head review and hosted synchronization — 02:12 UTC

Assignment4 was a fresh cold PR-mode review at9608b76; no actionable findings.
Reviewer independently verified18 tests0.807s, changed-file lint/Black,11 shell
steps, repaired source hashes, trigger/job inventory and dependency fingerprint.
Charge4 minutes, cumulative32/45,4/6 assignments, peak two agents. Shared usage10%.

At02:11:33 the remote branch was9608b76 but PR REST/GraphQL metadata remained
ff78d679, including an uncached read. Exact-head push test39088847557 passed;
PR test/coverage/lint had not appeared. Cause is unverified. No stale rollup is
accepted and no review is manually retriggered. Commit the completed PR-review
record as the normal final bookkeeping tail, then recheck synchronization and
all expected checks at that new head. Product files remain unchanged.


### Integrated outcome and retrospective — 02:16 UTC

PR523 merged into codex/gettenberg-acquisition at09763715 at02:15:45 UTC, about
84 minutes after00:52:10 launch. Accepted head6a988655 passed all four checks:
push test39089256583, PR test39089259069, coverage39089259076, lint39089259063.
No failed workflow-file runs remained at that head; authoritative threads showed
zero unresolved. Both first hosted reviews completed; the one valid Codex P2 was
fixed and resolved. SHA-locked merge, exact parent pair and accepted tree verified.
Main remains unchanged. The final control-plane checkpoint follows this merge.

The final tail review completed by02:13:07 and is conservatively charged2 minutes.
Total5/6 assignments,34/45 worker minutes, peak two agents, no active workers.
Three repair topics: Black formatting, job-env context availability, parser runtime
identity. Run finishes early once checkpointing completes; no next item starts.
Shared weekly usage4%→13%; this is account-wide, not attributable per-run usage.
Token/credit cost is unavailable. First reviewer assignment overran; it was
recorded and charged rather than described as successful deadline enforcement.

Process findings for LRH:

- A nonempty green check rollup is insufficient: rejected workflow files can
  disappear from the check list. Require an expected check inventory and inspect
  failed workflow runs at the exact SHA, in addition to branch-rule semantics.
- YAML parsing and shell syntax do not validate Actions expression locations.
  The focused regression checks job-env context roots; it is not a general
  Actions validator. A future repository-approved workflow checker merits
  consideration; this run introduced no new lint tool.
- Read actual final validation exits/logs after late edits. A compressed or
  remembered summary is not evidence; preserve failed checks and their repair.
- Bound worker execution with an external cancellable timer where available;
  a prompt deadline alone did not prevent this run's overrun.
- Include external parser/runtime identity in compiled-artifact caches while
  keeping reusable source bytes independent. Hosted review found this gap.
- PR metadata can lag the branch ref. After the normal bookkeeping push the
  PR synchronized; cause remains unverified. Never use stale-head CI, and do not
  claim that a metadata mismatch alone proves a particular GitHub failure.

Next scoped item is WI-GETTENBERG-0010: completion-to-evidence mapping, executed
Diataxis examples, full-snapshot/corpus/resource qualification and a reviewable
main-promotion/closeout plan. Live/bulk work needs its own explicit resource
grant; no production cache deletion or archive download was performed here.
Native records remain in_progress and WI0009 proposed pending human main approval.

## WI0010 qualification run — 2026-10-18 05:14:34 UTC

Human renewed a two-hour target / three-hour maximum. Charter amendment records
bounds. Base ed20e9c297bf5e50e1911b84722e53f5db3edee3; main210468236ff4db78d2d7c5218562fa2d166e6400.
WI0008 merge46960f6625b22131ecfcac1764b0da10ad8fb643 and WI0009 merge09763715d62c6143e3a896ce75eda256a94f4ab3
are verified ancestors with staged acceptance/review/canonical evidence. Native
records remain nonterminal. WI0010 is prompt-ready; prior-art check present.
Reuse experiment10, existing tests and APIs, with no competing framework.

Coordinator approves the bounded plan under the charter adapter: full pinned
snapshot/accounting, cached real-source corpus comparison, exercised Diataxis
docs, fresh package independence, completion matrix and promotion/closeout plan.
Branch codex/gettenberg-qualification; expected changes docs/tests/experiment10
and control-plane evidence. Canonical checks plus explicit experiment smoke,
Black/Ruff and independent review are required. No CI changes or main merge.

Launch: shared account weekly usage14% (not attributable); per-run cost unavailable.
Project Python3.11.9, Black25.11.0, Ruff0.15.0; LRH0.2.5.dev3596+gd86755f50.
Installed targets fresh; persistent skip consent invalid, unchanged. The shared
editable environment initially resolved another checkout; commands explicitly
set this worktree's src on PYTHONPATH and verify imports. The first no-record
check returned1 and stopped the shell before mutations; this is expected absence,
not an existing execution. Continue from verified clean state. No assignments yet.

### Assignment1 — 05:19 UTC

Dispatched qualification_docs from ed20e9c, docs plus one new documentation test
only; no product/control-plane edits, commits or network. Deadline05:34 UTC,
15 worker minutes allocated,30 remain including review. Acceptance: useful tutorial
and explanation, executable offline examples and accurate existing guide links.
Coordinator owns experiment/resource/corpus work. Pinned full lifecycle build
started05:18:55; no other bulk build is concurrent.

### Qualification findings and environment recovery — 05:29 UTC

Cached corpus census:1659 mass_quantities stories, all with legacy gzip UTF-8
text. Initial cleanup:1605 accepted envelopes,54 refusals (31 comma-form banners,
17 license END markers,5 wrapped book markers,1 mismatched title). Keep refusal
and missing data separate from output equality. Investigate exact safe historical
variants before proposing any repair; never silently relax ambiguous boundaries.

Nonisolated wheel build failed because shared environment packaging lacks
packaging.licenses required by setuptools77+. The attempted install had no wheel
and made no dependency changes. Retry with declared isolated build dependencies;
do not change project requirements or suppress the failure. Helper regressions:
10 tests passed. Full catalog build remains bounded by its existing alarm/limits.

### Bounded cleanup repair decision — 05:30 UTC

Coordinator approves two observed historical spelling variants within the existing
conservative boundary contract, not a relaxation of ambiguous book markers:
recognize a leading Gutenberg eBook comma banner and ignore the exact historical
END: FULL LICENSE separator just as START: FULL LICENSE is already ignored.
Both still require the same unique matched book pair and suffix corroboration;
near matches, arbitrary prefix prose, wrapped/mismatched book markers remain refused.
Authored regressions reproduced both failures before editing. Increment cleanup
policy to v2 so provenance distinguishes changed decisions. This is a scoped
qualification-driven repair, and changes src/cleanup.py plus its tests/reference;
no dependency or catalog schema change. Re-run real corpus, focused and canonical
checks and include the repair in independent review. Preserve pre-repair evidence.

### Documentation delivery and first full-catalog result — 05:32 UTC

Assignment1 completed05:31 UTC, charged12 minutes,33/45 worker minutes remain;
1/6 assignments used, no active workers. Added offline tutorial/architecture,
corrected stale migration claims, and executed preparation/gather/migration/
reference/maintenance examples with fixture transports. Worker reports35 focused
tests passed; coordinator will independently include them in canonical validation.

Full lifecycle:78937 records,2018879 resources,109170 contributions,223 diagnostics;
440.847s setup,89,030,656 bytes process peak RSS,0 network bytes,0.0024s reuse.
These satisfy existing600s/512MiB targets. Historical full build uses the same
hash in an isolated directory and original upstream implementation, with network
blocked and a1200s alarm. Measurements are single local observations, not a
controlled speed benchmark; concurrent light qualification work is disclosed.

### Installed-wheel qualification — 05:33 UTC

Declared isolated build succeeded. A fresh venv resolved normal wheel dependencies,
then installed the repaired wheel without changing those dependencies. Outside
checkout, with PYTHONPATH unset: installed smoke passed catalog/raw-source/query,
genre, cleanup, packaged JSON and no gutenbergpy; pip check, CLI help and gather
dry-run passed. Compare every packaged Python source byte with the worktree;
record wheel/hash/count and result separately. No new Gutenberg requests occurred.

### Corpus gate failure and bounded replan — 05:37 UTC

Pre-repair full comparison completed:1605 compared,54 cleanup refusals,892
normalized-body differences and894 differences against retained corpus.884 of892
are appended suffixes;8 change an earlier body position. Two severe examples:
35401 Friend Island shrinks26080→2620 characters;50103 The Dwindling Years shrinks
31972→900 and begins with a transcriber note. The current heuristic extractor is
sensitive to retained end notices/titles/authors; merely retaining more text at
the pure-cleanup boundary does not preserve the published story downstream.
This is a genuine qualification blocker, not an acceptable unexplained difference.

Coordinator freezes additional product changes and replans this run as a reviewed
qualification checkpoint: complete full snapshot/resource evidence, classify all
corpus differences, document repair requirements and preserve the small already
verified v2 repair. WI0010's first gate remains unsatisfied; do not internally merge
this PR, promote main, resolve items or claim replacement completion. No acceptance
criterion is weakened. Broader source-aware editorial-boundary/extraction changes
need a focused repair tranche with no-body-loss regressions and rerun of this corpus.
The post-v2 comparison is already running to measure what the narrow repair changes.
Safe independent documentation/package/snapshot verification continues within grant.

### Frozen evidence and assignment2 — 05:47 UTC

All full audits completed within bounds. Snapshot:78937 public source/typed-record
reconstructions,547.627s/130,252,800-byte RSS; exact XML element/attribute inventory
matches baseline. Catalog.get reparses retained RDF, so a separate40-field
normalized-index count audit complements replay and semantic query fixtures.
English37 additional IDs all have English after another language; no old IDs lost.

After v2:1646 compared,13 refusals,902 normalized-body differences,904 retained-
corpus differences. All1659 input cache/corpus hashes match before/after. Remaining
refusals include secondary failures exposed by correcting the first failure, so
subtracting repaired category counts from54 would be incorrect. Full reports are
archived compressed verbatim with hashes; readable per-story triage remains data,
not acceptance. Source ledger binds unchanged catalog files to lifecycle evidence.

Assignment2 qualification_review: cold pre-push diff review, no edits/network/bulk
reruns. Captured4113-line diff against ed20e9c including new files. Start05:47 UTC,
deadline06:06:57,20 minutes allocated; total2/6 assignments,12 used worker minutes,
33 remain before this assignment,13 reserved afterward. Product/experiment/docs
frozen. Reviewer must verify evidence claims and the explicit unaccepted checkpoint.
Canonical2944 tests89.551s passed; final entry-point-inclusive repeat is running.

### Independent review and final local checks — recorded 06:46 UTC

Assignment2 completed at 05:53 UTC, charged 7 worker minutes conservatively;
19 of 45 cumulative worker minutes used, 2 of 6 assignments, no active workers.
Cold review found no new actionable defect and independently replayed all eight
earlier-body differences. Coordinator independently read the heading-selection
code and replayed the two severe truncations: all retained row fields matched,
including new_rejection=None. This confirms the existing qualification blocker.

Reviewer verified all manifest/source/input hashes, corpus classifications and
refusals, query differences, wheel sources and installed smoke. Its broader tests
hit sandbox loopback-bind errors; these are explicitly recorded as environment
failures. Coordinator canonical suite passed 2,944 tests in 108.968 seconds;
package and explicit 12-runner experiment format/lint passed. No new product fix
was made after evidence freeze. Preserve a reviewable unaccepted PR, await its
first hosted review rounds and record exact-head CI; do not integrate it.

### Review checkpoint PR — 06:48 UTC

Opened [PR524](https://github.com/xenotaur/LCATS/pull/524) against
codex/gettenberg-acquisition at 48733d6a, explicitly unaccepted/do-not-merge.
Backfilled both native execution records with PR identity and reviewed product
commit; both remain in_progress. No integration or main ref moved. Four expected
hosted jobs are running (push tests, PR tests, coverage, lint); first hosted review
rounds pending, with no manual retriggers. Local validation: LRH 0 errors and
351 pre-existing warnings. An attempted root-level `lrh validate --project-root`
was rejected by this CLI; the correct package-cwd `lrh validate` passed.

The 05:55 draft timestamp on the preceding record was corrected to its actual
06:46 write checkpoint; coordinator reproduction completed at 05:52 UTC. Timing
claims use observed timestamps, not an assumption that tool/session latency is
zero. The original 07:14 target / 08:14 hard stop remain unchanged.

### LRH process findings from this qualification checkpoint

- Move a bounded real-corpus replay earlier into migration acceptance. The existing
  authored end-to-end fixtures and green canonical suite did not expose the
  cleanup/extractor interaction. Fixture suites should grow from minimized,
  independently understood counterexamples, not merely assert old/new equality.
- Make measurement scope machine-readable and narrow. Public record replay
  reparses raw RDF; it does not independently verify indexed values. Index counts
  complement semantic fixtures but do not prove all values. Distinguish full build
  from audit time, retained bytes from peak disk, and old decoded cache from
  original transport bytes. This prevented several tempting overclaims.
- Separate checkpoint reviewability from work-item acceptance. A PR can contain
  valuable, tested measurement/documentation work and still be explicitly barred
  from integration. A future LRH runner should expose both states rather than
  infer acceptance from green CI or a clean code review.
- Freeze and preserve evidence when a design-level composition flaw appears.
  The coordinator completed independent unaffected checks, recorded the material
  failure and proposed repair boundaries without turning an evaluation into an
  unbounded parser rewrite. Keep original before/after reports and input hashes.
- The 2–3 hour grant is a ceiling, not a mandate to consume remaining time after
  a material acceptance blocker. Review/CI latency belongs in elapsed run time;
  do not silently renew the clock or treat it as additional worker capacity.
- Account-level weekly usage rose from 14% at launch to 24% at the 06:48 checkpoint.
  This shared-account delta is not an attributable run cost. Two assignments used
  a conservatively charged 19 worker minutes; neither count measures token cost.
  A future runner should report attributable model usage when available.

### First hosted rounds and evidence-runner repair — 06:55 UTC

Codex first review on 48733d6a completed clean at 06:51:05. Copilot first review
at 06:51:48 identified one valid runner flaw: missing/empty collections produced
completed=true with zero rows. Independently reproduced all three invalid-input
cases (missing, empty, flat-JSON-only); initial stub lacked historical source
identity and was corrected before the intended red assertions were established.
A narrow guard now records completed=false/error and raises for these cases.
Per-story comparison and every product source remain unchanged. Focused 12 tests
passed. Original full reports/source ledger remain immutable; a new runner-repair
addendum verifies the same 1,659 measured paths and records old/new runner hashes.

Review response uses PROMPT(AD_HOC:GETTENBERG_QUALIFICATION_REVIEW)[2026-10-18T06:52:49+00:00].
No prior slug record; PR/local identity match at 4df20a9b. Coordinator approves
this routine evidence-integrity repair under the pilot adapter, with no invented
human reply or persistent consent change. Before repair, exact-head inventory at
4df20a9b contained four successful expected jobs and no missing workflow runs.
Repeat canonical checks and obtain independent verification of the repair before
resolving the bot thread. The material corpus integration blocker remains open.

### Repair validation — 06:57 UTC

Canonical 2,945 tests passed in 88.062 seconds; package format/lint, explicit
12-runner Black/Ruff and LRH validation passed (0 errors, 351 existing warnings).
No product bytes changed, so installed-wheel/source-record evidence remains bound
to the same candidate. Commit/push the runner repair and associated evidence;
perform a bounded cold verification of the repair and updated provenance next.

### Assignment3 confirmation and bounded stop — 07:02 UTC

Assignment3 qualification_repair_review ran approximately 06:57–06:59 UTC with
an eight-minute ceiling; charged 3 minutes conservatively. Total 22 of 45 worker
minutes, 3 of 6 assignments, maximum two concurrent agents including coordinator.
No workers remain active. Reviewed exact head 83a772f9. Twelve focused tests passed,
then passed again with gutenbergpy imports blocked; parent-runner regression
failed all three intended assertions. Verified all measured source/report hashes,
unchanged original result bytes and exactly 1,659 retained selected paths.

Coordinator approved the one Clear-satisfied bot-thread batch under the charter;
live isResolved-only inventory included the outdated thread. GraphQL resolution
returned true. No hosted reviewer was retriggered. A native CONFIRM record captures
classification, independent evidence and the NOT READY verdict. There is no merge
command: the material corpus blocker still violates WI0010's pre-integration gate.

Integration remains ed20e9c; main remains 21046823. Product/source measurements,
installed wheel and canonical corpus remain unchanged by the runner repair. Final
bookkeeping changes are records, evidence and prose only; final-head CI is checked
after pushing and recorded in the PR body, avoiding a self-referential commit
claim. End implementation here; finish bounded verification and handoff before
the original deadline. No automatic renewal, main promotion, terminal closeout,
Gutenberg request, corpus publication or persistent consent change occurred.

Recommended next human decision: authorize the focused narrative-preservation
repair scope in gettenberg-corpus-repair-plan.md, then repair/requalify this open
checkpoint before integration. Do not approve old/new body equality blindly or
solve retained editorial text by broadly stripping narrative. WI0010 remains open.

## Bounded corpus repair run — 2026-10-18

Start 08:24:26 UTC / 01:24 Pacific; target 10:24:26, hard stop 11:24:26 UTC.
User renewed the bounded run after the focused repair was recommended. Continue
clean PR524 head de8c326a on codex/gettenberg-qualification. Original user checkout
is on unrelated xenotaur/audit/wi-genre-0078 with untracked lcats/logs; untouched.
Native WI0010 readiness is yes; its qualification acceptance remains blocked.
Prior-art demand/duplication is recorded in WI0010 and the repair plan: improve
the existing gatherer rather than vendor upstream stripping or add a dependency.

LRH 0.2.5.dev3596+gd86755f50; installed watched skills fresh, persistent consent
invalid and unchanged. This explicit run uses the approved pilot adapter. Shared
weekly usage 28% used at launch; attributable token/cost unavailable. Available
disk about 215 GiB. Existing full catalog and all historical source caches remain
available. Use LCATS environment plus this worktree's src on PYTHONPATH.

Plan: inspect all eight earlier-body changes, choose and record the smallest
narrative-safe preparation/heading boundary, add independent counterexamples,
replay all 1,659 sources, verify actual temporary publication and installed wheel,
then cold review and final-head checks. No old/new equality shortcut or broad
refusal policy. Expected edits: gatherer logic/tests, experiment runner/results,
Diataxis docs and control-plane evidence. Keep acceptance blocked unless proved.

### Budget-enforcement failure and checkpoint — 09:16 UTC / 02:16 Pacific

Assignment1 narrative_case_audit was dispatched around 08:25 UTC: read-only review
of eight earlier-body differences, 15-minute allowance, deadline 08:41 UTC. The
worker reported at about 09:15 that its deadline was already past. Coordinator's
clock check returned 09:15:41 and the worker was immediately interrupted. Agent
status confirms interrupted; no worker remains running. No implementation started.

Charge 51 worker minutes conservatively for approximately 50 minutes of elapsed
dispatch occupancy. That exceeds both the assignment limit and this run's total
45-minute worker allowance. The charter's first-exhausted-limit rule ends execution;
remaining coordinator wall-clock time is not an automatic renewal. This is a real
coordination failure, not a successful bounded assignment. The unexplained gap
must not be called active model time or attributed to a specific tool. No evidence
supports a causal explanation yet. Account weekly usage is 29% versus 28% at launch;
that shared-account delta is not attributable per-run token/cost consumption.

Preliminary findings: worker confirms opening loss for35401, footer-only new output
for50103, and substantial opening loss in the legacy output for70645. Other five
cases were described as editorial/whitespace changes, without established narrative
loss. Coordinator source inspection agrees that heading/footer interference needs
a context-aware repair and that old output is not an oracle. The eight-case audit,
chosen implementation, regression fixtures and full requalification remain undone.
The worker wrote no report file; retain these observations with that limitation.

Checkpoint only: populate the native execution, validate documentation, and push
this stop record to PR524. No product/test/experiment/cache/corpus edits; no main
or integration changes, new Gutenberg requests, policy changes or terminal closeout.
Prior test/CI results remain attached to their original heads. Do not represent
this run as implementing the repair or satisfying any new acceptance criterion.

Process recommendation for the next grant: coordinator-led implementation, with
only a short independent review delegated after the change exists. Require agents
to check time immediately on entry before work and after tool returns. A written
deadline is cooperative guidance; the coordinator must check/intervene, and a
future LRH runtime should enforce cancellation independently of model sampling.
Do not silently weaken this charter in response to the failure.
