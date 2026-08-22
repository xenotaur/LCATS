---
id: WS-KNIGHT-NOVUM-ANALYSIS
kind: planning_node
title: Knight/Novum Science-Fiction Analysis
status: proposed
stage: planned
origin: design_review
summary: Govern the experiment-local buildout of the Knight seven-feature profile, Suvin novum analysis, shared evidence layer, and versioned science-fiction.json sidecar described by PROP-LCATS-KNIGHT-NOVUM-ANALYSIS-SIDECAR.
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_design:
  - lcats/project/design/proposals/adopted/knight-novum-analysis-sidecar/00_proposal.md
  - lcats/project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md
  - lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md
  - lcats/project/design/proposals/adopted/lcats-story-bucket-layout/00_proposal.md
  - lcats/project/design/proposals/adopted/worldcon-fast-path-annotation/00_proposal.md
  - lcats/project/design/proposals/proposed/genre-evidence-sidecars/00_proposal.md
  - lcats/project/workstreams/proposed/WS-GENRE-EVIDENCE-SIDECARS.md
  - lcats/project/work_items/proposed/WI-GENRE-0004.md
work_items:
  - WI-SF-0001
  - WI-SF-0002
  - WI-SF-0003
  - WI-SF-0004
  - WI-SF-0005
  - WI-SF-0006
  - WI-SF-0007
  - WI-SF-0008
  - WI-SF-0009
  - WI-SF-0010
  - WI-SF-0011
exit_criteria:
  - All approved Phase 1 work items are resolved with no-cost tests and lrh validate passing
  - The approximately 30-story feasibility pilot completes and satisfies or explicitly fails its preregistered gates
  - The Worldcon pilot completes only after the WI-GENRE-0004 manifest, reviewed cost manifest, pinned configuration, and explicit paid-run approval are satisfied
  - Every published pilot artifact validates, has locatable evidence anchors, and matches its story hash
  - A documented decision chooses corpus integration, revision, repetition, or termination
  - Production corpus integration remains separately gated unless an approved design change adds it to this workstream
---

# Workstream: Knight/Novum Science-Fiction Analysis

## Purpose

This workstream coordinates planning for `PROP-LCATS-KNIGHT-NOVUM-ANALYSIS-SIDECAR`, which proposes a checkpointed, evidence-grounded science-fiction analysis pipeline that prepares each story once, extracts a shared theory-neutral evidence layer, and applies independent Damon Knight and Darko Suvin adjudicators before assembling a versioned `science-fiction.json` sidecar (`project/design/proposals/adopted/knight-novum-analysis-sidecar/00_proposal.md:26`).

The proposal was merged by PR #323 and adopted as a governing design on 2026-08-21. Its implementation plan says the multi-stage effort should be delivered through a new workstream and separately scoped work items rather than treated as authorization for a monolithic runtime change (`project/design/proposals/adopted/knight-novum-analysis-sidecar/00_proposal.md:466`). Runtime implementation remains blocked until the relevant planning PR has landed through the LRH lifecycle, the target work item passes readiness review, and a ready leaf work item is explicitly selected.

## Scope

- Define and version the rubric/data contracts, preparation/chunking, shared evidence, independent adjudication, sidecar/checkpoint/orchestration, and experiment-runner deliverables needed for Phase 1.
- Plan the approximately 30-story Phase 2 feasibility pilot as a gated, preregistered evaluation after Phase 1 exits.
- Plan the 100-200-story Phase 3 Worldcon pilot as dependent on the current `WI-GENRE-0004` sample output and explicit paid-run approval.
- Track a later production-integration gate as separately authorized work, not an automatic consequence of successful pilots.
- Keep runtime implementation changes, pilot outputs, paid model calls, `data/`, `corpora/`, `lcats annotate`, and `lcats promote` changes out of the initial planning PR.

## Prior Art Check

### Duplication search

- In-repo: No duplicate Knight/Suvin analysis workstream, work item, runtime package, or `science-fiction.json` sidecar was found. The merged proposal itself records that related infrastructure exists but no duplicate Knight/Suvin analysis or sidecar exists (`project/design/proposals/adopted/knight-novum-analysis-sidecar/00_proposal.md:80`). A fresh search found only the proposal and its execution records for Knight/Novum terms, while existing sidecar work is `genre.json`-specific (`project/workstreams/proposed/WS-GENRE-EVIDENCE-SIDECARS.md:40`).
- Related implementation substrate: story discovery is now canonical bucket-only and excludes sibling sidecars by accepting only `<story>/story.json` (`src/lcats/analysis/corpus/discovery.py:63`); `lcats annotate` separates checkpoint bookkeeping from materialized sidecars and can rematerialize sidecars without repeated paid calls (`src/lcats/analysis/corpus/annotate.py:8`); checkpoint writes use atomic temp-file plus replace semantics (`src/lcats/utils/checkpoint.py:302`); `genre-sidecar-v1` validates append-only assessment sidecars without reading, writing, or promotion side effects (`src/lcats/analysis/corpus/genre_sidecar.py:1`).
- Related but not duplicate ERW work: the Event-Role-World proposal defines evidence spans, SF world-model tags, and `anomaly_or_novum` (`project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md:34`), but it treats `anomaly_or_novum` as an interpretive hypothesis (`project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md:185`) and does not operationalize Knight criteria or Suvin's N/C/H conjunction.
- Sibling repos: None identified by the user or repository context.
- External libraries: No external library replaces the LCATS-specific literary-analysis, sidecar, and LRH governance work. General JSON/schema/evaluation libraries may inform future implementation, but the proposal explicitly prefers a pure-Python validator for Phase 1 (`project/design/proposals/adopted/knight-novum-analysis-sidecar/00_proposal.md:309`).
- Recommendation: Proceed by extending the existing LCATS bucket, checkpoint, structured-output, validation, and genre-sidecar patterns rather than duplicating them. Treat ERW and scene/sequel outputs as optional evidence/navigation inputs, not prerequisites.

### Demand search

- Work items: `WI-GENRE-0004` remains proposed and supplies the Worldcon sample dependency for Phase 3, not a Knight/Novum implementation item. Its current state is materially newer than the Knight/Novum proposal snapshot: a real no-cost full scan selected 146/160 target stories, estimated the gated validation run at $34.01, and left only the real Opus validation run outstanding (`project/work_items/proposed/WI-GENRE-0004.md:280`).
- Proposals: `PROP-LCATS-KNIGHT-NOVUM-ANALYSIS-SIDECAR` directly requests this workstream and work-item decomposition (`project/design/proposals/adopted/knight-novum-analysis-sidecar/00_proposal.md:466`). `PROP-GENRE-EVIDENCE-SIDECARS` and `WS-GENRE-EVIDENCE-SIDECARS` request adjacent append-only `genre.json` evidence work, not theory-specific science-fiction analysis (`project/workstreams/proposed/WS-GENRE-EVIDENCE-SIDECARS.md:46`).
- Backlog: No matching Knight, Novum, science-fiction-analysis, rubric, or linguistic-feature backlog entry was found in `project/design/backlog.md` during the prior-art search.
- Recommendation: Link this workstream to `WI-GENRE-0004` for the Phase 3 sample, and link ERW, checkpointing, bucket layout, annotation, and genre-sidecar artifacts as prior art. Do not close or rewrite related demand artifacts.

## Work Items

The following work items are created by this planning PR through `/lrh-work-item` as reviewable planning artifacts before runtime implementation begins. Each item must retain the proposal's paid-run and corpus-write gates.

- **WI-SF-0001 - Rubric/source packet and data contracts.** Define and version `knight-seven-v1`, `suvin-novum-v1`, theory-neutral evidence types, anchors, identifiers, Knight criterion states/materiality, Novum candidate and N/C/H records, estrangement profiles, provenance, failures, validation, partial-success records, and the `science-fiction-sidecar-v1` envelope. This item is blocked on the authoritative primary-source Knight and Suvin excerpts before freezing rubric text; planning can proceed but source-dependent implementation must stop.
- **WI-SF-0002 - Deterministic story preparation and chunk manifests.** Implement normalized story loading without source mutation, deterministic story hashing, stable paragraph IDs, whole-story eligibility, paragraph-aligned adaptive chunk planning, preferred chapter/section boundaries, overlap accounting, deterministic manifests, and gap-free coverage. This is an immediate no-cost Phase 1 leaf.
- **WI-SF-0003 - Shared theory-neutral evidence extraction interfaces.** Implement backend-independent interfaces and strict structured outputs for storyworld changes, scientific/technical explanations, inquiry methods, displacement, extrapolative consequences, catastrophes, character reactions, and reader-facing contrasts. Requires exact quotation anchoring, deterministic quote location, invalid-evidence quarantine, overlap de-duplication without suppressing conflicts, and optional ERW adaptation without requiring an ERW run. Depends on WI-SF-0002.
- **WI-SF-0004 - Independent Knight and Suvin adjudicators.** Implement separate Knight criterion adjudication, Suvin candidate identification and N/C/H adjudication, bounded theory-specific follow-up retrieval, deterministic Knight interval calculation, deterministic Novum conjunction/dominant/system validation, and explicit absent/ambiguous/not_assessable/pipeline-failure states. Depends on WI-SF-0001 and WI-SF-0003; source-dependent rubric implementation remains blocked until primary-source text is supplied.
- **WI-SF-0005 - Sidecar validator, checkpoints, and orchestration.** Implement typed records, pure-Python structural/semantic validation, referential-integrity checks, story-hash checks, current-pointer rules, effective-input fingerprints, per-stage checkpoint reuse/rematerialization, atomic single-writer publication, partial-success behavior, and validated `science-fiction.json` assembly. Depends on WI-SF-0002, WI-SF-0003, and WI-SF-0004.
- **WI-SF-0006 - Experiment runner and no-cost fixture suite.** Build an experiment-local runner with deterministic manifests, `--dry-run`, cost estimation, no-cost fixture mode, resume/checkpoint reuse, bounded retries/concurrency, explicit output roots, and safeguards against writes to corpus or production promotion paths. Add fixture/unit coverage for SF positives, no-novum controls, supernatural contrasts, ambiguous cognitive validation, incidental technology, multiple-novum systems, cross-chunk evidence, overlap duplicates/conflicts, malformed output, stale hashes, interrupted stages, partial Knight/Novum success, and byte-stable output. Depends on WI-SF-0005.
- **WI-SF-0007 - Phase 2 feasibility pilot preregistration.** Define the approximately 30-story deterministic sample, human annotation protocol, audit subset, repeated-run stability plan, whole-story/chunked comparisons, and predeclared gates before observing results. No paid calls. Depends on Phase 1 contracts being stable enough to write labels and thresholds.
- **WI-SF-0008 - Phase 2 feasibility pilot execution and report.** Execute the approved approximately 30-story pilot only after reviewed manifests and any paid-call approvals exist. Produce machine-readable metrics, evidence validity, agreement/recall/failure/latency/token/cost/review-time reports, and a decision on whether to revise or scale. Depends on WI-SF-0006 and WI-SF-0007.
- **WI-SF-0009 - Phase 3 Worldcon manifest and paid-run gate.** Reconcile Phase 3 with the final current Worldcon sample manifest from `WI-GENRE-0004`, freeze rubrics/prompts/schemas/code commit/backend/model/generation parameters/chunk config, and prepare reviewed sample and cost manifests. Depends on WI-GENRE-0004 and Phase 2 exit.
- **WI-SF-0010 - Phase 3 Worldcon pilot execution and report.** Run the 100-200-story pilot resumably after explicit paid-run approval, quarantine invalid output, human-audit a stratified sample, compare with Phase 2, and publish metrics, failure taxonomy, cost report, and datasheet-style documentation. Depends on WI-SF-0009.
- **WI-SF-0011 - Later corpus-integration gate design.** If Phase 3 recommends integration, design the separately authorized production path: canonical sidecar filename, survey/promotion validation, transaction-safe promotion, opt-in annotation or dedicated command, canaries, rollback, append-only evolution, and corpus-wide coverage/quality reporting. Depends on Phase 3 decision; does not implement production integration by itself.

### Dependency graph

```text
WI-SF-0001 (rubrics/contracts; primary-source gated)
  -> WI-SF-0004 (independent adjudicators)

WI-SF-0002 (preparation/chunking)
  -> WI-SF-0003 (shared evidence)
  -> WI-SF-0005 (sidecar/checkpoints/orchestration)

WI-SF-0003 -> WI-SF-0004 -> WI-SF-0005 -> WI-SF-0006

WI-SF-0007 (Phase 2 preregistration)
  + WI-SF-0006 -> WI-SF-0008 (Phase 2 pilot)

WI-GENRE-0004 final sample
  + WI-SF-0008 passed Phase 2 scale decision -> WI-SF-0009 -> WI-SF-0010

WI-SF-0010 decision -> WI-SF-0011 (separate integration gate)
```

### Parallelizable leaves

- With proposal adoption and the planning PR landed, WI-SF-0002 can begin after readiness review and explicit leaf selection; it has no primary-source dependency and no paid calls.
- WI-SF-0001 can begin as a source-packet/data-contract planning item after readiness review and explicit selection, but must not freeze Knight or Suvin rubric wording until authoritative primary-source excerpts or an approved repository source are supplied.
- WI-SF-0007 can draft sampling and evaluation scaffolding after readiness review, explicit selection, and sufficient contract vocabulary, but final gates must wait for Phase 1 contract stability.
- WI-SF-0003 can start after WI-SF-0002 without final Knight/Suvin rubric wording because it is theory-neutral by design.

## Exit Criteria

- All approved Phase 1 work items are resolved with no-cost tests and `lrh validate` passing.
- The approximately 30-story feasibility pilot completes and satisfies or explicitly fails its preregistered gates.
- The Worldcon pilot completes only after the `WI-GENRE-0004` sample dependency, reviewed cost manifest, pinned configuration, and explicit paid-run approval are satisfied.
- Every published pilot artifact validates, has locatable evidence anchors, and matches its story hash.
- A documented decision chooses corpus integration, revision/repetition, or termination.
- Production corpus integration remains separately gated unless an approved design change adds it to this workstream.

## Non-Goals

- Does not implement runtime modules, prompts, validators, runner code, pilot outputs, or corpus data changes in the workstream-planning PR.
- Does not make paid model calls or authorize a paid run.
- Does not freeze Knight's seven descriptions or Suvin's theoretical definitions from memory or secondary summaries.
- Does not require ERW or scene/sequel output as a prerequisite for Knight/Novum analysis.
- Does not modify `lcats annotate`, `lcats promote`, `data/`, or `corpora/` during Phases 1-3.
- Does not mark the workstream complete merely because core modules exist; pilot gates and the final integrate/revise/stop decision are part of closure.

## Open Questions

- What exact primary-edition wording and page references will govern `knight-seven-v1` and `suvin-novum-v1`?
- Should optional ERW evidence adaptation be included in Phase 1 after the independent pipeline baseline exists, or deferred until Phase 2/3 comparison?
- What exact criterion-level agreement and accuracy thresholds match the Worldcon paper's intended claims?
- Should `WI-SF-*` numbering be retained, or should the project owner prefer a longer `WI-SCIENCE-FICTION-*` prefix before work-item artifacts are minted?
