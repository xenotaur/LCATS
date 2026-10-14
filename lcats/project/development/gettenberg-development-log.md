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
